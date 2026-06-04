# Confluence Storage Format 可用宏参考

撰写 Confluence 页面正文时，可以使用以下宏来丰富内容展示。

## code

格式化代码块，支持语法高亮。

```xml
<ac:structured-macro ac:name="code" ac:schema-version="1">
    <ac:parameter ac:name="language">java</ac:parameter>
    <ac:plain-text-body>
      <![CDATA[public class Test {
          public static void main(String[] args) {
              System.out.println("hello");
          }
      }]]>
    </ac:plain-text-body>
</ac:structured-macro>
```

## drawio

嵌入 draw.io 图表（流程图、架构图、UML、ER 图等）。

```xml
<ac:structured-macro ac:name="drawio" ac:schema-version="1">
    <ac:parameter ac:name="border">true</ac:parameter>
    <ac:parameter ac:name="diagramName">test.drawio</ac:parameter>
    <ac:parameter ac:name="simpleViewer">false</ac:parameter>
    <ac:parameter ac:name="links">auto</ac:parameter>
    <ac:parameter ac:name="tbstyle">top</ac:parameter>
    <ac:parameter ac:name="lbox">true</ac:parameter>
    <ac:parameter ac:name="diagramWidth">auto</ac:parameter>
    <ac:parameter ac:name="revision">1</ac:parameter>
</ac:structured-macro>
```

- `diagramName`：drawio 附件文件名
- `revision`：附件版本号（首次上传为 1）

## emoticon

插入表情符号。

```xml
<ac:emoticon ac:name="smile" />
<ac:emoticon ac:name="sad" />
<ac:emoticon ac:name="cheeky" />
<ac:emoticon ac:name="laugh" />
<ac:emoticon ac:name="wink" />
<ac:emoticon ac:name="thumbs-up" />
<ac:emoticon ac:name="thumbs-down" />
<ac:emoticon ac:name="information" />
<ac:emoticon ac:name="tick" />
<ac:emoticon ac:name="cross" />
<ac:emoticon ac:name="warning" />
<ac:emoticon ac:name="plus" />
<ac:emoticon ac:name="minus" />
<ac:emoticon ac:name="question" />
<ac:emoticon ac:name="light-on" />
<ac:emoticon ac:name="light-off" />
<ac:emoticon ac:name="yellow-star" />
<ac:emoticon ac:name="red-star" />
<ac:emoticon ac:name="green-star" />
<ac:emoticon ac:name="blue-star" />
```

## expand

可展开/折叠的文本块。

```xml
<ac:structured-macro ac:name="expand" ac:schema-version="1">
    <ac:parameter ac:name="title">Click here to expand</ac:parameter>
    <ac:rich-text-body>
      <p>content here</p>
    </ac:rich-text-body>
</ac:structured-macro>
```

## image

显示图片（来自附件或 URL）。

```xml
<!-- 来自附件 -->
<ac:image ac:height="250">
  <ri:attachment ri:filename="some.png"/>
</ac:image>

<!-- 来自 URL -->
<ac:image ac:height="250">
  <ri:url ri:value="https://some.com/some.png"/>
</ac:image>
```

## info

蓝色背景的信息提示框。

```xml
<ac:structured-macro ac:name="info" ac:schema-version="1">
    <ac:parameter ac:name="title">Optional title here</ac:parameter>
    <ac:rich-text-body>
      <p>info here</p>
    </ac:rich-text-body>
</ac:structured-macro>
```

## kaptain-issue

显示 Kaptain 事项状态。

```xml
<ac:structured-macro ac:name="kaptain-issue" ac:schema-version="1">
    <ac:parameter ac:name="issueKey">DEVOPS-9658</ac:parameter>
    <ac:parameter ac:name="autoLink">false</ac:parameter>
</ac:structured-macro>
```

## mention

@提及用户。需要用户的 userKey，可通过 `confluence users search <user>` 获取。

```xml
<ac:link>
  <ri:user ri:userkey="2c9680f7405147ee0140514c26120003"/>
</ac:link>
```

- `ri:userkey`：用户唯一标识（即 `confluence users search` 输出的"用户 Key"）

多个用户提及示例：

```xml
<p>请 <ac:link><ri:user ri:userkey="abc123"/></ac:link> 和 <ac:link><ri:user ri:userkey="def456"/></ac:link> 审阅此文档。</p>
```

## mermaid-macro

使用 Mermaid 语法创建图表。

```xml
<ac:structured-macro ac:name="mermaid-macro" ac:schema-version="1">
  <ac:plain-text-body>
    <![CDATA[flowchart TD
      A[Christmas] -->|Get money| B(Go shopping)
      B --> C{Let me think}
      C -->|One| D[Laptop]
      C -->|Two| E[iPhone]
      C -->|Three| F[fa:fa-car Car]
    ]]>
  </ac:plain-text-body>
</ac:structured-macro>
```

## note

黄色背景的备注框。

```xml
<ac:structured-macro ac:name="note" ac:schema-version="1">
    <ac:parameter ac:name="title">Optional title here</ac:parameter>
    <ac:rich-text-body>
      <p>note here</p>
    </ac:rich-text-body>
</ac:structured-macro>
```

## panel

自定义面板，用于突出显示内容。

```xml
<ac:structured-macro ac:name="panel" ac:schema-version="1">
    <ac:rich-text-body>
      <p>content here</p>
    </ac:rich-text-body>
</ac:structured-macro>
```

## status

状态标签，可用颜色：Blue、Grey、Green、Red、Yellow。

```xml
<ac:structured-macro ac:name="status">
  <ac:parameter ac:name="colour">Green</ac:parameter>
  <ac:parameter ac:name="title">COMPLETED</ac:parameter>
</ac:structured-macro>
```

## table

HTML 表格。

```xml
<table>
    <colgroup>
      <col />
      <col />
      <col />
    </colgroup>
    <tbody>
      <tr>
          <th>header 1</th>
          <th>header 2</th>
          <th>header 3</th>
      </tr>
      <tr>
          <td>foo</td>
          <td>1</td>
          <td>3</td>
      </tr>
      <tr>
          <td>bar</td>
          <td>2</td>
          <td>4</td>
      </tr>
    </tbody>
</table>
```

## task-list

带复选框的任务列表。

```xml
<ac:task-list>
    <ac:task>
      <ac:task-id>1</ac:task-id>
      <ac:task-status>incomplete</ac:task-status>
      <ac:task-body><span class="placeholder-inline-tasks">this is an unchecked todo</span></ac:task-body>
    </ac:task>
    <ac:task>
      <ac:task-id>2</ac:task-id>
      <ac:task-status>complete</ac:task-status>
      <ac:task-body><span class="placeholder-inline-tasks">this is a checked todo</span></ac:task-body>
    </ac:task>
</ac:task-list>
```

## tip

绿色背景的提示框。

```xml
<ac:structured-macro ac:name="tip" ac:schema-version="1">
    <ac:parameter ac:name="title">Optional title here</ac:parameter>
    <ac:rich-text-body>
      <p>tip here</p>
    </ac:rich-text-body>
</ac:structured-macro>
```

## toc

根据页面标题自动生成目录。

```xml
<ac:structured-macro ac:name="toc" ac:schema-version="1" />
```

## warning

红色背景的警告框。

```xml
<ac:structured-macro ac:name="warning" ac:schema-version="1">
    <ac:parameter ac:name="title">Optional title here</ac:parameter>
    <ac:rich-text-body>
      <p>warning here</p>
    </ac:rich-text-body>
</ac:structured-macro>
```
