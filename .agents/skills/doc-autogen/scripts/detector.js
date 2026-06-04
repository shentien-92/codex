/* global console, process, require */
/* eslint-disable @typescript-eslint/no-require-imports */
const fs = require('fs');
const path = require('path');
const root = process.cwd();

const readmePath = path.join(root, 'README.md');
const changelogPath = path.join(root, 'CHANGELOG.md');

function getDocStatus() {
  let readmeStats = { exists: false, isEmpty: true, hasTutorial: false };
  
  if (fs.existsSync(readmePath)) {
    const content = fs.readFileSync(readmePath, 'utf8').trim();
    readmeStats.exists = true;
    readmeStats.isEmpty = content.length < 20;
    // 检查是否有教程标志性标题
    readmeStats.hasTutorial = /#+|Usage|Install|使用|安装|快速开始/i.test(content);
  }

  return {
    readme: readmeStats,
    hasChangelog: fs.existsSync(changelogPath),
    cwd: root
  };
}

console.log(JSON.stringify(getDocStatus(), null, 2));
