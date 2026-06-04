/* global console, require */
/* eslint-disable @typescript-eslint/no-require-imports */
const { execSync } = require('child_process');

function getChanges() {
  try {
    // 1. 尝试获取暂存区 (Staged) 改动
    let diff = execSync('git diff --cached -U3').toString();
    let files = execSync('git diff --cached --name-only').toString().trim();

    // 2. 如果暂存区为空，则获取工作区 (Unstaged) 所有未提交改动
    if (!diff || !diff.trim()) {
      diff = execSync('git diff HEAD -U3').toString();
      files = execSync('git diff HEAD --name-only').toString().trim();
    }

    if (!diff || !diff.trim()) {
      return { message: "No changes detected in the repository." };
    }

    return {
      files: files.split('\n').filter(Boolean),
      // 限制 diff 长度，防止超过 ai 的 Context 长度
      diffSummary: diff.substring(0, 4000), 
      timestamp: new Date().toISOString()
    };
  } catch {
    return { error: "Git execution failed. Ensure this is a git repo." };
  }
}

// 必须输出 JSON 字符串，供 Claude 感知
console.log(JSON.stringify(getChanges(), null, 2));
