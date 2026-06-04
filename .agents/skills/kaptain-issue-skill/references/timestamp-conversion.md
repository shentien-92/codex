# 时间戳转换规则

Kaptain API 返回的时间字段通常是 **毫秒级 Unix 时间戳**（如 `1775204796000`），需要转换为北京时间（UTC+8）展示。

## 核心规则

**禁止手动计算或心算转换。** 遇到需要展示或计算时间戳的场景，必须使用 Bash 工具执行以下方法之一：

## 转换方法

### 方法一：Perl（推荐，跨平台）

```bash
perl -e 'use POSIX qw(strftime); print strftime("%Y-%m-%d %H:%M:%S", localtime(<时间戳秒数> + 8*3600))'
# 例如: perl -e 'use POSIX qw(strftime); print strftime("%Y-%m-%d %H:%M:%S", localtime(1775204796 + 8*3600))' → 2026-04-01 15:46:36
```

### 方法二：date 命令（系统相关）

**Linux / GNU 环境：**
```bash
date -d @<时间戳秒数> "+%Y-%m-%d %H:%M:%S"
# 或设置时区: TZ='Asia/Shanghai' date -d @<时间戳秒数> "+%Y-%m-%d %H:%M:%S"
```

**macOS / BSD 环境：**
```bash
date -r <时间戳秒数> "+%Y-%m-%d %H:%M:%S"
```

## 注意事项

- Kaptain 时间戳为毫秒，传给 `date` 时需要先除以 1000 去掉后三位
- 例如：`1775204796000`（毫秒）→ `1775204796`（秒）
- 常见时间字段：`createTime`、`updateTime`、`deployTime`、`presentTestTime`、`startTime`、`endTime`、`deployDate` 等
- 展示时间时统一格式为 `YYYY-MM-DD HH:mm:ss`（含时分秒）或 `YYYY-MM-DD`（仅日期）
- 如需要一次性批量转换多个时间戳，可调用 Bash 循环处理

## 适用场景

- 查询迭代详情展示时间
- 查询事项详情展示时间
- 创建/更新迭代需要基于现有迭代时间计算
- 任何涉及 Kaptain API 时间字段的展示或计算