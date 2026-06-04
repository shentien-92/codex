/* global console, process, require */
/* eslint-disable @typescript-eslint/no-require-imports */
const fs = require('fs');
const path = require('path');

const args = process.argv.slice(2);
const type = args[args.indexOf('--type') + 1];
const filePath = args[args.indexOf('--file') + 1];

const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
const root = process.cwd();

if (type === 'readme') {
  // 直接写入 ai 重构后的全量内容，实现“智能更新”
  const p = path.join(root, 'README.md');
  fs.writeFileSync(p, data.fullReadme.trim() + '\n');
  console.log("README Synchronized (Content Reconstructed).");
} 
else if (type === 'changelog') {
  const p = path.join(root, 'CHANGELOG.md');
  const entry = `\n## [${new Date().toISOString().split('T')[0]}]\n- ${data.changelogEntry}\n`;
  let c = fs.existsSync(p) ? fs.readFileSync(p, 'utf8') : '# Changelog\n';
  // 依然保持在顶部增量插入
  fs.writeFileSync(p, c.replace(/(^# .*?\n)/, `$1${entry}`));
  console.log("Changelog Updated.");
}
