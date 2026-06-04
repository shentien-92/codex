---
name: i18n-autogen
description: 自动识别代码中的中文硬编码，通过词条接口翻译，并自动重写为 i18n 多语言国际化调用。
---

# 国际化自动转换技能 (i18n-Adaptive)

> ### 🛑 核心准则 (Mandatory Constraints)
> **在执行任何阶段前，AI 必须无条件遵守以下约束：**
> 1. **严格任务边界**：禁止添加启动脚本、修改业务逻辑、提供运行指南、添加 HTML 测试文件或执行任何启动测试。AI 的唯一职责是完成 提取 -> 翻译 -> 重写 -> 清理 的闭环。
> 2. **单例引入原则**：严禁在一个文件内多次插入相同的 import 语句。重写前必须执行 **Import 预审**，若已存在目标包，必须合并花括号成员。
> 3. **静默失败原则**：若文件翻译失败或提取异常，必须保持原样，严禁损坏原始代码。
> 4. **路径自适应**：除临时文件生成外，所有操作必须基于 `<SKILL_PATH>` 和当前项目根目录动态拼接，禁止硬编码路径。
> 5. **任务终点**：重写与清理执行完毕，输出总结表格与直达链接后，任务即宣告结束。

## 总体流程概览 (Execution Roadmap)
请 AI 严格按如下顺序推进任务，并在每个阶段开始前简要提示当前进度：
- [ ] **阶段 1**：身份感知、多模式寻径与 Token 持久化。
- [ ] **阶段 2**：框架审计与 SemVer 依赖版本精准管控。
- [ ] **阶段 3**：**上下文敏感**型文案提取（执行严格黑名单过滤）。
- [ ] **阶段 4**：调用云端接口生成 `temp_translated.json`。
- [ ] **阶段 5**：代码自动化重写（执行 **Import 预审** 与 **单例约束**）。
- [ ] **阶段 6**：鲁棒性补丁注入与临时文件清理。

## 第一阶段：身份感知与权限准备 (Pre-Flight)
1. **多模式寻径 (Crucial)**：
   - 优先执行跨平台指令：`node -e "console.log(require('fs').readdirSync('.', {recursive: true}).find(p => p.endsWith('i18n-autogen')) || '.')" `
   - 若失败，根据 Shell 类型重试：
     - Windows PowerShell/CMD: `dir /s /b /ad | findstr "i18n-autogen"`
     - Unix Bash: `find . -maxdepth 4 -name "i18n-autogen" -type d`
   - 将确定的有效路径记为 `<SKILL_PATH>`。
2. **执行探测**：运行 `node <SKILL_PATH>/scripts/detector.js`。
3. **记录元数据**：
   - `<PROJECT_NAME>`: 脚本返回的 `projectName`。
   - `<PKG_MANAGER>`: 脚本返回的 `packageManager` (npm/yarn/pnpm)。
   - `<TOKEN>`: 脚本返回的 `token`。
   - `<LDAP>`: 脚本返回的 `ldap`。
4. **Token 权限获取 (Crucial)**：
   - **条件判断**：若 `token` 为空或无效。
   - **交互引导**：AI 必须回复：“检测到未配置访问 Token，请前往 [https://pub.qunhequnhe.com/user-info](https://pub.qunhequnhe.com/user-info) 页面，找到并复制 **PUB_TOKEN** 的值，然后粘贴在这里：”
   - **持久化保存**：用户输入后，AI 立即执行指令：
     - `node -e "require('fs').writeFileSync('<SKILL_PATH>/.i18n_token', '用户输入的内容')"`

## 第二阶段：环境审计与依赖管控 (Environment Audit)
1. **框架与配置审计 (New)**：
   - **全局搜索**：在全项目搜索 `from '@qunhe/i18n-translate'` 或 `from '@qunhe/react-i18n-translate'`。
   - **定位配置原点**：若找到包含 `init({ packages: [...] })` 的文件，记录为 `<CONFIG_FILE>`；若未找到，则默认 `<CONFIG_FILE>` 为 `src/utils/i18n.ts`。
   - **标识记录**：检查 `package.json` 是否包含 `react` (记录 `<IS_REACT>`) 及 `@qunhe/i18n-translate` (记录 `<IS_BASE>`)。
2. **精准版本依赖管控 (SemVer Audit)**：
   - **基准线**：`@qunhe/i18n-translate` ≥ **2.3.4**；`@qunhe/react-i18n-translate` ≥ **0.0.1-alpha.13**。
   - **版本比对逻辑**：读取 `package.json`，去除版本号中的 `^` 或 `~`；针对 `alpha` 版本，AI 必须通过 `node -e` 拆分比对预发布位。
   - **执行策略**：若包缺失或版本低于基准线，执行 `${PKG_MANAGER} add [包名]@latest`（若 `<IS_REACT>` 为假，则跳过安装 react 包）；若版本已达标，**禁止执行安装或更新指令**。

## 第三阶段：扫描提取与云端翻译 (Extract & Translate)
1. **扫描策略 (Strict Rules)**
   - **文件类型**：仅扫描源码目录下的 `.ts, .tsx, .js, .jsx`，排除 `node_modules`, `dist`, `build` 及隐藏目录。
   - **文案判定准则 (New)**：仅提取**展示性字符串**。判定标准：该字符串必须位于 JSX 文本节点、HTML 属性（如 `placeholder`, `title`, `label`）或业务逻辑中的提示语（如 `message.success`）。
   - **硬性排除黑名单 (Zero Tolerance)**：
     - **技术属性**：严禁提取 `key`, `ref`, `className`, `style`, `type`, `id`, `name` (作为标识符时), `data-*`, `aria-*` 的值。
     - **代码特征**：严禁提取形如 `snake_case`, `camelCase`, `kebab-case` 的纯英文标识符（通常是 ID 或 变量名）。
     - **特定调用**：严禁提取 `console.*`, `import`, `require`, `localStorage`, `sessionStorage`, `cookie` 中的参数。
     - **排除路径/术语**：排除 URL 路径、文件扩展名（.png, .pdf）、HTTP 状态码、以及明显的常量 key（如 `SUCCESS`, `ERROR_CODE`） 。
     - **注释和特定字符串排除**：严禁提取任何注释中的文本，无论是单行注释 `//` 还是多行注释 `/* */`，并且`t()`/`translate()` 调用中的参数也排除。
   - **中文提取**：提取所有硬编码中文。若中文内嵌英文单词（如 `"设置 URL"`），作为整体提取到 `chinese` 数组。
   - **英文提取**：仅提取**首字母大写**或**带空格**的展示性短语（如 `Save Changes`, `Email Address`）。禁止提取单字且全小写的变量词（如 `list`, `index`）。如类似`<span>Save</span>`中的`Save`, `<input placeholder="Email">`中的`Email`等。提取到 `english` 数组。
   - **Emoji 拆分**：若文案包含 Emoji，必须以 Emoji 为界限拆分为多个纯文本片段，Emoji不能被放进文案中，拆分后如果有空字符串，必须删除。
2. **生成中转包**：将 `projectName`, `token`, `ldap`, `files` (含文案数组) 写入 `temp_extract.json`，其中files为 `[{path: "文件路径", chinese: ["文案1", "文案2", ...]，english:["text1","text2",...]}]` 的数组。
3. **调用接口**：运行 `node <SKILL_PATH>/scripts/translator.js --file temp_extract.json`。
   - 脚本将依次调用 词条创建接口 和 词条翻译接口。
   - 翻译结果写入 `temp_translated.json`，格式为 `{ "文件路径": [{"original": "原始文案", "key": "对应的词条key"}] }` 数组。
4. **记录中间数据**：
   - `<PROJECT_ID>`: 脚本返回的 `projectId`。
   - `<PACKAGE_ID>`: 脚本返回的 `packageId`。

## 第四阶段：代码自动化重写
1. **Import 全局预审 (Priority #1)**：
   - **执行动作**：在对任何文件执行重写前，AI 必须先对该文件所有 `import` 语句进行静态扫描。
   - **合并算法**：若目标包（如 `@qunhe/react-i18n-translate`）已存在，AI 必须通过正则 `import\s*\{([\s\S]*?)\}\s*from...` 提取现有成员，将新成员（如 `useTranslation`）合并至其 `{}` 闭包内并去重。
   - **强力约束**：**宁可不添加功能，也绝对禁止在该文件内新增第二行同名包的 import。**
2. **配置点对齐 (Configuration)**：
   - **场景 A：文件已存在**：
     - 在 `<CONFIG_FILE>` 中检查 `packages` 数组。
     - 若缺少 `agent_<PROJECT_NAME>`，必须增量添加。
     - 确保该文件导出 `i18n` 实例（供 Provider 使用）和 `translate` 方法。
   - **场景 B：文件不存在**：
     - 创建 `src/utils/i18n.ts`，写入初始化模版（含 `init` 和 `export`）
   - **i18n.ts内容模版**：
     ```typescript
      import i18nIns from '@qunhe/i18n-translate';

      i18nIns.init({
        lang: 'your project env Lang', // 此处由用户自行配置，如 'en-US' 等，不要删除，保留原样
        packages: ['agent_<PROJECT_NAME>'], // 此处填入实际获取的 agent_<PROJECT_NAME>
        resourceNamespace: window.__YOUR_RESOURCE_NAMESPACE__,
      });

      export const i18n = i18nIns;
      export const translate = i18nIns.translate;
     ```

3. **单例引入约束 (Strict Compliance)**：
    - **严禁重复声明**：在任何文件中，禁止出现两条及以上来自同一个包（如 `@qunhe/react-i18n-translate`）的 `import` 语句。
    - **合并规则**：若文件中已存在该包的 `import`，AI 必须通过修改原有的 `import` 语句来增加新成员。
    - **示例**：
      - 错误：同时存在 `import { useTranslation } ...` 和 `import { I18nextProvider } ...`
      - 正确：`import { useTranslation, I18nextProvider } from '@qunhe/react-i18n-translate';`

4. **必须执行React 入口注入**：
   - **定位入口文件**：AI 必须扫描 `src/main.tsx`, `src/index.tsx`, `src/App.tsx` 或类似含有 `render(` 或 `createRoot(` 的文件。
   - **执行注入逻辑**：
     - **Import 注入**：引入 `import { I18nextProvider } from '@qunhe/react-i18n-translate';` 检查文件。若已存在 @qunhe/react-i18n-translate，则将 I18nextProvider 添加到已有花括号中；若无，则新增一行。同时引入 `<CONFIG_FILE>` 导出的 `i18n` 实例。
     - **结构包裹**：识别根渲染语句。
       - *示例 1 (ReactDOM.render)*：`render(<App />)` -> `render(<I18nextProvider i18n={i18n}><App /></I18nextProvider>)`
       - *示例 2 (createRoot)*：`.render(<App />)` -> `.render(<I18nextProvider i18n={i18n}><App /></I18nextProvider>)`
     - **检测**：如果文件中已存在 `I18nextProvider`，则仅校验 `i18n` 实例是否正确。

5. **业务代码精准替换 (Critical)**：
   - 遍历 `temp_translated.json` 中的文件路径执行修改：
   - **针对 React 组件 (.tsx/.jsx)**：
     - **Hook 注入**：仅在检测到 JSX 返回值的组件函数顶部添加 `const [t] = useTranslation();`。
     - **Import 注入**：引入 `import { useTranslation } from '@qunhe/react-i18n-translate';`,检查文件。若已存在该包，则将 useTranslation 合并进去；严禁另起一行。
     - **语法替换**：将中文替换为 `{t('key', '默认中文')}`。
        - **JSX Text**: `<span>确认</span>` -> `<span>{t('key','确认')}</span>`; `<span>Ok</span>` -> `<span>{t('key','Ok')}</span>`.
        - **JSX Props**: `<Input placeholder="搜索" />` -> `<Input placeholder={t('key','搜索')} />`; `<Input placeholder="Email" />` -> `<Input placeholder={t('key','Email')} />`.
        - **String Lit**: `message.error("失败")` -> `message.error(t('key','失败'))`; `message.success("成功")` -> `message.success(t('key','成功'))`.
        - **Template Lit**: `` `你好${name}` `` -> `t('key', '你好')`; `` `input ${field}` `` -> `t('key', 'input')`.
   - **针对普通 TS/JS 文件**：
     - 依然使用 `import { translate }` 并替换为 `translate('key', '默认中文')`。

## 第五阶段：鲁棒性补丁与清理
1. **智能 Hook 注入补丁**：
   - 在注入 `useTranslation` 前，必须检查函数体是否已定义 `t`。
   - 禁止在循环、条件判断语句内注入 Hook。
   - 仅针对大写字母开头的 Functional Component 执行 Hook 注入。

2. **多行 Import 合并算法**：
   - 识别 `import { ... } from '@qunhe/react-i18n-translate'` 时，需支持匹配跨行（含换行符）的情况。
   - 优先使用正则 `import\s+\{([\s\S]*?)\}\s+from\s+['"]@qunhe/react-i18n-translate['"]` 提取现有变量。

3. **Context 冗余清理**：
   - 若重写后发现文件内没有任何 `t()` 或 `I18nextProvider` 的调用，必须撤销对该文件的 `import` 注入。

4. **清理临时文件**：
   - 必须删除所有临时文件，包括json和js文件，以免泄露敏感信息。
   - 为确保跨平台执行成功，AI 必须**分步**执行删除指令：
    - **若为 Windows (PowerShell/CMD)**：
     - `del temp_extract.json`
     - `del temp_translated.json`
   - **若为 Unix (Linux/macOS)**：
     - `rm temp_extract.json`
     - `rm temp_translated.json`
     
5. **任务总结**：
   - 优先表格展示执行结果。
   - 必须输出直达链接：
     - 多语言项目链接：https://pub.qunhequnhe.com/lang#/project/<PROJECT_ID>
     - 多语言包链接：https://pub.qunhequnhe.com/lang#/public/detail/<PACKAGE_ID>
