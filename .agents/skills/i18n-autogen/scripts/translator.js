/* global Buffer, console, process, require */
/* eslint-disable @typescript-eslint/no-require-imports */
const fs = require('fs');
const crypto = require('crypto');
const http = require('http');
const https = require('https');
const { URL } = require('url');

const args = process.argv.slice(2);
const filePath = args[args.indexOf('--file') + 1];

if (!filePath || !fs.existsSync(filePath)) {
  console.error("Error: Missing input file (temp_extract.json).");
  process.exit(1);
}

// 基础配置
const BASE_CONFIG = {
  baseURL: 'http://pub.qunhequnhe.com',
  headers: {
    'Content-Type': 'application/json',
    'X-Pub-Lang-Token': 'ddf19cae-8a30-4a5a-8784-a424183402b5',
  }
};

/**
 * 通用 HTTP 请求封装
 * @param {string} apiPath - 接口路径 (如 /api/i18n/create)
 * @param {string} method - HTTP 方法 (默认 POST)
 * @param {Object} payload - 请求参数
 */
async function request(apiPath, method = 'POST', payload) {
  const url = `${BASE_CONFIG.baseURL || ''}${apiPath}`;
  const parsedUrl = new URL(url);
  const client = parsedUrl.protocol === 'https:' ? https : http;

  const options = {
    hostname: parsedUrl.hostname,
    port: parsedUrl.port,
    path: parsedUrl.pathname + parsedUrl.search,
    method: method.toUpperCase(),
    headers: {
      'Content-Type': 'application/json',
      ...BASE_CONFIG.headers, // 保留原有的 headers 配置
    },
  };

  // 如果不是 GET 或 HEAD 请求，则添加 body
  let body = null;
  if (payload && !['GET', 'HEAD'].includes(method.toUpperCase())) {
    body = JSON.stringify(payload);
    options.headers['Content-Length'] = Buffer.byteLength(body);
  }

  return new Promise((resolve, reject) => {
    const req = client.request(options, (res) => {
      let responseData = '';

      res.on('data', (chunk) => {
        responseData += chunk;
      });

      res.on('end', () => {
        const contentType = res.headers['content-type'];
        if (contentType && contentType.includes('application/json')) {
          try {
            const jsonData = JSON.parse(responseData);
            if (jsonData.c === 0 || jsonData.c === "0") {
              resolve(jsonData.d);
            } else {
              reject(new Error(`API Error: ${jsonData.m || 'Unknown error'}`));
            }
          } catch (e) {
            reject(new Error(`JSON parse error: ${e.message}`));
          }
        } else {
          resolve(responseData);
        }
      });
    });

    req.on('error', (error) => {
      reject(error);
    });

    if (body) {
      req.write(body);
    }

    req.end();
  });
}

async function translate(projectId) {
  return await request('/lang/api/entries/translate/dimension', 'POST', {
      "dimensionType": "PROJECT",
      "dimensionId": projectId,
      "useG": true
  });
}

async function packageToProject({packageId, projectId}) {
  return await request('/lang/api/entries/dimension-aggregate', 'POST', {
    sourceDimension: 'PACKAGE',
    sourceDimensionId: packageId,
    targetDimension: 'PROJECT',
    targetDimensionId: projectId,
    action: 'CREATE'
  });
}

async function createProject(name) {
  let projectId;
  try {
    projectId = await request('/lang/api/projects', 'POST', {name});
    return projectId;
  } catch (err) {
    if(err.message.includes('项目名重复')) {
      const project = await request(`/lang/api/projects/name/${name}`, 'GET');
      projectId = project.id;
    } else {
      throw err;
    }
  }
  return projectId;
}

async function createPackage(name, desc = '') {
  let packageId;
  const packages =  await request('/lang/api/packages/bynames', 'POST', {names: [name]});
  packageId = packages[0] && packages[0].id || '';
  if(!packageId) {
      packageId = await request('/lang/api/packages', 'POST', {
        name,
        desc
      });
  }
  return packageId;
}

async function getEntryListByKeys(keys) {
  const entryList = await request('/lang/api/external/entries/bykeys', 'POST', {
    keys
  });
  return entryList;
}

async function entryToPackage(entryIds, packageId) {
 return await request('/lang/api/entries/aggregate', 'POST', {
    "entryId": entryIds,
    "dimensionId": packageId,
    "dimensionType": "PACKAGE",
    "dimensionAction": "CREATE"
  });
}

async function createEntry(entryList, ldap, projectName){
  const [packageId, projectId] = await Promise.all([
    createPackage(`agent_${projectName}`,`created by agent for project ${projectName}`),
    createProject(`agent_${projectName}`),
  ]);
  
  const existEntryList = await getEntryListByKeys(entryList.map(item => item.key));
  const existKeySet = new Set(existEntryList.map(item => item.key));

  const entryIds = existEntryList.map(item => item.id);

  const createEntryList = entryList.filter(item => !existKeySet.has(item.key));
  if(createEntryList.length !== 0) {
    const newEntryIds = await request('/lang/api/external/entries', 'POST', {
      user: {ldap:ldap, name:ldap},
      translations: createEntryList.map(item => ({
        ...(item.type === 'zh_CN' ? {zh: item.origin} : {en: item.origin}),
        key: item.key,
        translationType: 1
      })),
      dimensionType:'PACKAGE',
      dimensionId: packageId
    });
    entryIds.push(...(newEntryIds || []));
  }
  
  if(existEntryList.length !== 0) {
    await entryToPackage(entryIds, packageId);
  }

  await packageToProject({packageId, projectId});

  await translate(projectId);

  console.log(`✅ create lang entry success! 📦Package ID: ${packageId}, 📁Project ID: ${projectId}`);
}

/**
 * 生成唯一 Key
 */
function generateKey(projectName, text) {
  const hash = crypto.createHash('md5').update(text).digest('hex').slice(0, 8);
  return `${projectName}-${hash}`;
}

async function run() {
  const input = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  const { projectName, ldap, files, token } = input;
  const resultData = {};

  BASE_CONFIG.headers['pub-token'] = token;

  // --- 第一步：全局去重收集 ---
  // 使用 Map 存储：key 为 "文案内容"，value 为 { key, origin }
  const uniqueTermsMap = new Map();

  for (const file of files) {
    // 提取硬编码的中文文本
    const chineseTexts = file.chinese || [];
    const englishTexts = file.english || [];
    for (const text of chineseTexts) {
      if (!uniqueTermsMap.has(text)) {
        uniqueTermsMap.set(text, {
          key: generateKey(projectName, text),
          origin: text,
          creator: ldap, // 这里的参数可以根据接口需求添加
          type:'zh_CN'
        });
      }
    }
    for (const text of englishTexts) {
      if (!uniqueTermsMap.has(text)) {
        uniqueTermsMap.set(text, {
          key: generateKey(projectName, text),
          origin: text,
          creator: ldap, // 这里的参数可以根据接口需求添加
          type:'en_US'
        });
      }
    }
  }

  // 将 Map 转为数组供接口调用
  const allUniqueItems = Array.from(uniqueTermsMap.values());

  console.log(`🚀 Total unique terms found: ${allUniqueItems.length}`);

  try {
    // 第二步：创建词条
    await createEntry(allUniqueItems, ldap, projectName);
  } catch (err) {
    console.error(`❌ Global API Error:`, err.message);
  }

  // --- 第三步：映射回原文件结构 ---
  // 此时 AI 重构代码仍需要按文件知道哪些词条该换成哪个 key
  for (const file of files) {
    // 提取硬编码的中文文本用于生成映射
    const chineseTexts = file.chinese || [];
    const englishTexts = file.english || [];
    resultData[file.path] = [
        ...chineseTexts.map(text => {
        const term = uniqueTermsMap.get(text);
        return {
          original: text,
          key: term.key,
          locale: 'zh_CN'
        };
      }),
      ...englishTexts.map(text => {
        const term = uniqueTermsMap.get(text);
        return {
          original: text,
          key: term.key,
          locale: 'en_US'
        };
      }) || []
    ];
  }

  // 输出最终映射文件
  fs.writeFileSync('temp_translated.json', JSON.stringify(resultData, null, 2));
  console.log("\n✅ Success: temp_translated.json generated with unique terms.");
}

run();
