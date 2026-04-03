---
name: wpl-rule-check
description: 给定原始日志数据，帮你解析这条日志、写出 WPL 规则和 OML 富化模型，并通过 wpl-check 验证。适用场景：粘贴一段日志说"帮我解析"/"帮我写规则"/"这个日志怎么取字段"/"OML 怎么写"/"规则匹配不上"。
triggers:
  - 提供日志样本要求解析
  - 编写或修改 WPL 规则
  - 编写或修改 OML 富化模型
  - 询问 WPL/OML 语法
  - 用 wpl-check 验证规则
  - 调试规则匹配失败
dependencies:
  optional:
    - wpl-check
    - wproj
  docs:
    - docs.warpparse.ai
    - editor.warpparse.ai
---

# WPL 规则编写与验证

这个 skill 专注于一件事：**给定日志样本，产出正确的 WPL + OML 规则，并通过验证**。

## 职责边界

### 本 skill 处理

- 分析原始日志样本，识别格式类型
- 编写 WPL 解析规则（`parse.wpl`）
- 编写 OML 富化模型（`.oml`）
- 解释 WPL/OML 语法和语义
- 用 `wpl-check` 验证规则是否正确
- 调试规则匹配失败（字段缺失、类型错误等）
- 针对特定字段提取需求调整规则

### 本 skill 不处理（路由到 `warpparse-log-engineering`）

- WarpParse 是否适合当前场景的评估
- 工程目录初始化（`wproj init`）
- source/sink/connector 配置
- 生产部署和 rollout 策略
- 监控运维和故障排查

## 工作方法

### 第一步：识别日志格式

收到样本后，先判断日志类型：

| 日志特征 | 对应 WPL 模式 |
|---------|-------------|
| 以 `{` 开头 | 纯 JSON：`json(...)` |
| `key=value` 或 `key: value` 对 | KV：`kvarr(...)` |
| 有 `\|` 分隔的固定字段 | CEF/固定分隔：多 group + `\|` |
| 以 `<数字>` 开头 | Syslog pri：`_:pri<<,>>` |
| Apache/Nginx CLF 格式 | `ip time/clf http/request http/status` |
| JSON 前有 syslog 前缀 | Syslog+JSON 复合 |
| BOM 头（`\xEF\xBB\xBF`） | 需加 `\| strip/bom \|` |

### 第二步：编写 WPL 规则

**规则结构模板（严格按此格式）：**

```wpl
#[copy_raw(name:"raw_msg")]
package 业务简称 {
  #[tag(log_desc: "产品名-事件描述", log_type: "log_type字段值")]
  rule log_type字段值 {
    (
      json(
        chars@field1,
        ip@src_ip,
        digit@port,
      )
    )
  }
}
```

**命名规定：**
- `#[copy_raw(name:"raw_msg")]` 固定写在 `package` 行正上方
- `package` = 日志来源业务简称（如 `360`、`nginx`、`sangfor_af`）
- `#[tag(log_desc:..., log_type:...)]` 写在 `rule xxx {` 行正上方，在 `package {}` 内
- `rule` = 日志的 `log_type` 字段值（如 `netconnect_audit`）

**语法要点：**
1. `json(...)` 必须包在 `(...)` 分组内
2. `\0` 是字段级分隔符，**不得独立出现在规则顶层**
3. ip → `ip`，时间 → `time`，数字 → `digit`，尽量不全用 `chars`
4. JSON 字段重命名：`chars@json_key:alias`，alias 是 OML 引用名
5. 有 type 字段区分类型时：`json(...) | f_chars_has(type_field, value)`

### 第三步：编写 OML 富化模型

**OML 头部格式（严格按此格式）：**

```oml
name : log_type字段值
rule : 业务简称/log_type字段值
---
access_ip: ip = read(wp_src_ip);
log_desc = read(log_desc);
log_type = read(log_type);
raw_msg = pipe take(raw_msg) | json_escape;

business_field1 = read(f1);
business_field2 = read(f2);
```

**语法要点：**
1. 每行结尾必须有 `;`
2. `raw_msg` 用 `take`（只能用一次），其他字段用 `read`
3. 时间字段：`read(field) | Time::to_ts_zone(8, ms)`
4. Unix 秒级时间戳字段用 `time_timestamp@field` 类型
5. **空行规则**：共用 4 个头部字段后加一个空行，业务字段之间**不加任何空行**

### 第四步：强制自测（必须通过才能输出）

**不得跳过，不得让用户自己跑：**

```bash
# 在当前工作目录创建测试文件
# 1. 语法检查
wpl-check syntax parse.wpl
# 2. 样本匹配测试
wpl-check sample parse.wpl sample.dat
```

两步均通过后，**只输出以下三项**，不输出字段解析表、建议或延伸说明：

```
数据类型：<一句话>

WPL 规则：
<代码块>

OML 规则：
<代码块>
```

如果失败，分析报错、修正规则，重新自测，直到通过。

## 常见陷阱

### WPL 陷阱

```wpl
# ❌ 错误：JSON 内不写过滤
json(chars@type, ...) | f_chars_has(type, login)   # ✅ 正确：先解析再过滤

# ❌ 错误：遗漏字段命名
ip\s digit\s chars\0    # ip/digit/chars 没有命名，OML 无法引用
# ✅ 正确
ip:src_ip\s digit:port\s chars:message\0

# ❌ 错误：http/agent 匹配非浏览器 UA
http/agent:ua           # 非浏览器 UA 会失败
# ✅ 正确
chars:ua                # 统一用 chars

# ❌ 错误：分隔符错误方向
chars,digit             # 逗号在 chars 后面，但应该写 chars\,
# ✅ 正确
chars\,digit            # 分隔符写在前一个字段后面（\, 表示逗号分隔）
```

### OML 陷阱

```oml
# ❌ 错误：遗漏分号
field1 = read(x)
field2 = read(y)   # 缺分号会报错

# ✅ 正确
field1 = read(x);
field2 = read(y);

# ❌ 错误：rule 路径不匹配 WPL
name : my_rule
rule : /mypackage/rule_name   # 必须匹配 WPL 的 package/rule

# ❌ 错误：直接读取不存在的字段
field = read(nonexistent);   # 字段不存在时返回 ignore，下游会 ignore 传播
# ✅ 正确：提供默认值
field = read(nonexistent) { _ : chars() };
```

## 输出格式

每次产出规则时，按以下格式输出：

```
### WPL 规则

\`\`\`wpl
# 规则内容
\`\`\`

### OML 富化模型

\`\`\`oml
# OML 内容
\`\`\`

### 验证命令

\`\`\`bash
# 验证命令
\`\`\`

### 解析结果说明

| 字段名 | 类型 | 来源 | 说明 |
```

## 参考文档索引

- `references/wpl-language-core.md` — WPL 完整类型表、语法、分组、管道函数
- `references/oml-language-core.md` — OML 表达式、函数、match、pipe、static blocks
- `references/wpl-production-patterns.md` — 生产用 WPL 规则模式（JSON/KV/Syslog/CEF）
- `references/oml-enrichment-patterns.md` — 生产用 OML 富化模式（标准头部、枚举映射、SQL、时间、IP）
- `references/wpl-check-workflow.md` — wpl-check CLI 工作流
