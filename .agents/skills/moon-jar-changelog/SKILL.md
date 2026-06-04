---
name: moon-jar-changelog
description: 二方包变更收集与变更日志生成 - 收集变更、按 Keep a Changelog 分类、生成并提交 CHANGELOG
allowed-tools: Bash(npx -y @qunhe/moon-cli@latest *)
---

# 二方包变更收集与变更日志生成

本技能专注于二方包发版中的**收集变更**和**生成并提交变更日志**两个步骤，确保变更日志先于发版提交。

## Step 1：收集变更

### 确定基准版本

基准版本按以下优先级确定：

1. **用户明确提供的基准/版本**（最高优先级）
2. 远程分支上的上一个版本（`git describe --tags --abbrev=0 origin/<分支>`）
3. 分支创建点的标签（`git describe --tags --abbrev=0 <fork-point-commit>`）
4. 分支基准提交中 `pom.xml` 的 `<scm><tag>` 值

**获取远程基准：**
```bash
git fetch --tags origin
```

**Master 发版 - 获取上一标签：**
```bash
git describe --tags --abbrev=0 origin/master
```

**Release 分支发版 - 获取上一标签：**
```bash
git describe --tags --abbrev=0 origin/release/<分支名>
```

### 收集变更

```bash
# 获取提交列表
git log --oneline <基准版本>..HEAD

# 获取变更文件统计
git diff --name-status <基准版本>...HEAD
git diff --stat <基准版本>...HEAD
```

### 按 Keep a Changelog 分类

将变更分为以下类别：
- **Added**（新增）- 新功能
- **Changed**（变更）- 功能变更
- **Deprecated**（已废弃）- 即将移除的功能
- **Removed**（已移除）- 已移除的功能
- **Fixed**（已修复）- bug 修复
- **Security**（安全）- 安全相关

### 特殊情况：仅元数据发版

如果分支仅包含版本号或变更日志元数据更新（无实际代码 diff），需明确声明为：
> 仅元数据发版更新

不添加虚假的功能变更条目。

---

## Step 2：生成并提交变更日志

### 生成变更日志条目（如果现有仓库已有变更日志，则保持与现有仓库变更日志风格一致）

**展示给用户时需包含基准声明：**
```markdown
baseline: <原始基准版本>
range: <基准>...<当前分支>

---

## [<目标版本>] - <YYYY-MM-DD>

### 提交记录
- <短 SHA> <提交消息>
- ...

### Added
- ...

### Changed
- ...

### Fixed
- ...
```

**最终写入 CHANGELOG.md 时省略 Compare 块（baseline/range），仅保留版本条目。**

### 确认与提交

1. 将变更日志展示给用户确认
2. 用户确认后，更新 `CHANGELOG.md` 顶部（写入时省略 `baseline/range` 元数据）
3. 提交变更日志：

```bash
git add CHANGELOG.md
git commit -m "[changelog] bump version to <版本>"
git push
```

---

## 变更日志质量标准

- 每一条目**无需阅读 git 日志即可理解**
- **不将提交哈希**作为最终内容转储
- **仅包含来自 diff 的已确认变更**，不虚构内容
- 保持与现有仓库变更日志风格一致
- 聚焦于**用户可见的行为变更**、**影响/风险范围**、**可用的测试证据**

---

## 参考

- Keep a Changelog 规范：[https://keepachangelog.com/zh-CN/1.1.0/](https://keepachangelog.com/zh-CN/1.1.0/)
