/* global __dirname, console, process, require */
/* eslint-disable @typescript-eslint/no-require-imports */
const fs = require('fs');
const path = require('path');
const os = require('os');

const root = process.cwd();
const TOKEN_FILE = path.join(__dirname, '../.i18n_token');

function getUserInfo() {
  const configPath = path.join(os.homedir(), '.def/core/config.json');
  if (fs.existsSync(configPath)) {
    try {
      const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
      return {
        ldap: config.user && config.user.ldapId || null,
        token: config.pubToken || null,
      };
    } catch {
      return null;
    }
  } else {
    if (fs.existsSync(TOKEN_FILE)) {
      return {
        ldap: null,
        token: fs.readFileSync(TOKEN_FILE, 'utf8').trim(),
      };
    }
    return {
        ldap: null,
        token: null,
    };
  }
}

function getProjectName() {
  let name = '';
  try {
    const pkg = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
    name = pkg.name && pkg.name.split('/').pop(); // 去掉 @scope/
  } catch {
    // Fall back to the current directory name when package.json is absent or invalid.
  }
  // 兜底：如果 pkg 无 name 或报错，取当前目录名
  return name || path.basename(root);
}

/**
 * 探测使用的包管理器
 */
function getPackageManager() {
  if (fs.existsSync(path.join(root, 'pnpm-lock.yaml'))) return 'pnpm';
  if (fs.existsSync(path.join(root, 'yarn.lock'))) return 'yarn';
  if (fs.existsSync(path.join(root, 'package-lock.json'))) return 'npm';
  return 'npm'; // 默认优先使用 npm
}

const userInfo = getUserInfo();
console.log(JSON.stringify({
  projectName: getProjectName(),
  packageManager: getPackageManager(),
  ldap: userInfo.ldap || 'unknown',
  token: userInfo.token,
  cwd: root
}));
