# WPL 语言核心参考

本文档是 WPL 规则编写的权威参考，用于判断语法正确性、选择类型和函数。

---

## 文件结构

```wpl
package 包名 {
  rule 规则名 {
    |预处理管道|          // 可选，作用于整行
    (字段列表)
  }
}
```

带注解的完整结构：

```wpl
#[tag(log_desc:"描述文字", log_type:"规则类型")]
package vendor_product {
  rule rule_name {
    (
      // 字段定义
    )
  }
}
```

---

## 类型系统完整速查

### 基础类型

| 类型 | 标识符 | 匹配内容 | 说明 |
|------|--------|---------|------|
| 忽略 | `_` | 任意内容 | 忽略该字段，`N*_` 忽略 N 个 |
| 符号 | `symbol(xxx)` | 精确字面量 | 匹配失败则规则失败 |
| 预读符号 | `peek_symbol(xxx)` | 精确字面量 | 预读但不消费，用于分支判断 |
| 布尔 | `bool` | `true`/`false` | 布尔值 |
| 字符串 | `chars` | 任意字符串 | 最宽泛，其他类型匹配失败时降级 |
| 整数 | `digit` | 整数 | `123`, `8080` |
| 浮点 | `float` | 浮点数 | `3.14`, `0.01` |
| 序列号 | `sn` | `ABC123XYZ` | 字母+数字混合 |

### 时间类型

| 类型 | 标识符 | 样例格式 |
|------|--------|---------|
| 通用时间 | `time` | `2023-05-15 07:09:12`（多格式自动识别） |
| ISO 8601 | `time_iso` | `2023-05-15T07:09:12Z` |
| RFC 3339 | `time_3339` | `2022-03-21T12:34:56+00:00` |
| RFC 2822 | `time_2822` | `Mon, 07 Jul 2025 09:20:32 +0000` |
| CLF 时间 | `time/clf` | `06/Aug/2019:12:12:19 +0800`（Apache/Nginx） |
| Unix 时间戳 | `time_timestamp` | `1647849600` |

### 网络类型

| 类型 | 标识符 | 样例 |
|------|--------|------|
| IP 地址 | `ip` | `192.168.1.100`，`::1`（IPv4/IPv6） |
| IP 网段 | `ip_net` | `192.168.0.0/24` |
| 域名 | `domain` | `example.com` |
| 邮箱 | `email` | `user@example.com` |
| 端口 | `port` | `8080`, `443` |
| URL | `url` | `http://example.com/path` |

### 结构化类型

| 类型 | 标识符 | 说明 |
|------|--------|------|
| 键值对 | `kvarr` | `key=value` 或 `key: value` 格式，可提取子字段 |
| JSON | `json` | JSON 对象，可提取子字段 |
| 严格JSON | `exact_json` | 严格验证 JSON 格式 |
| 数组 | `array` | `[1,2,3]` 或 `["a","b"]` |
| 数字数组 | `array/digit` | 数字元素数组 |
| 字符串数组 | `array/chars` | 字符串元素数组 |

### 协议类型

| 类型 | 标识符 | 说明 |
|------|--------|------|
| HTTP 请求行 | `http/request` | `GET /path HTTP/1.1` |
| HTTP 状态码 | `http/status` | `200`, `404` |
| User-Agent | `http/agent` | **只匹配标准浏览器 UA**，非浏览器请用 `chars` |
| HTTP 方法 | `http/method` | `GET`, `POST`, `PUT` 等 |

### 编码类型

| 类型 | 标识符 | 说明 |
|------|--------|------|
| 十六进制 | `hex` | `48656c6c6f` |
| Base64 | `base64` | `aGVsbG8=` |

---

## 字段定义语法

完整语法：

```
[N*] DataType [(symbol)] [(subfields)] [:name] [[len]] [format] [sep] { | pipe }
```

| 部分 | 说明 | 示例 |
|------|------|------|
| `N*` | 重复 N 次 | `3*_` 忽略3个，`kvarr` 自动循环 |
| `DataType` | 数据类型 | `digit`, `ip`, `json` |
| `(symbol)` | symbol 的内容 | `symbol(GET)` |
| `(subfields)` | json/kvarr 子字段 | `json(chars@name, digit@age)` |
| `:name` | 字段命名（OML 引用必须） | `:status`, `:src_ip` |
| `[len]` | 长度限制 | `[100]` |
| `format` | 格式控制 | `<[,]>`, `"`, `^10` |
| `sep` | 分隔符 | `\,`, `\;`, `\0` |
| `\| pipe` | 管道函数 | `\|f_chars_has(type, login)` |

---

## 格式控制

| 格式 | 语法 | 说明 | 示例 |
|------|------|------|------|
| 范围定界 | `<beg,end>` | 以指定字符为起止 | `<[,]>` 方括号内（CLF 时间专用） |
| 引号 | `"` | 双引号包裹 | `chars:ua"` — **双引号字段唯一正确写法，禁止写成 `<",">`** |
| 字符计数 | `^N` | 固定 N 个字符 | `^10` |

---

## 分隔符

**写法**：分隔符写在该字段**后面**，表示"读完这个字段后，遇到此字符继续"。

| 分隔符 | 语法 | 优先级 | 说明 |
|--------|------|--------|------|
| 逗号 | `\,` | 字段级 (3) | |
| 分号 | `\;` | 字段级 (3) | |
| 冒号 | `\:` | 字段级 (3) | |
| 空格 | `\s` | 字段级 (3) | 默认已是空格，通常不需要写 |
| 行尾 | `\0` | 字段级 (3) | 读到行尾，**仅用于中间字段**（如 `chars\0 \| chars_replace(...)`），最后字段不需要 |
| 组分隔 | `(...)\sep` | 组级 (2) | 作用于整个组内所有字段 |

优先级：**字段级(3) > 组级(2) > 上游继承(1)**

**关键规则：空格是默认分隔符，不需要显式写 `\s`。**
只有在分隔符不是空格时，才需要显式写出（`\,`、`\;`、`\|`、`\0` 等）。

```
数据以空格分隔 → 不写任何分隔符（默认）
数据以逗号分隔 → 写 \,
数据以分号分隔 → 写 \;
非空格分隔的整个组 → (a, b, c)\|  或  (a, b, c)\,
中间字段需要吞掉整行再处理 → 写 \0（如 chars\0 | chars_replace(...)）
最后一个字段 → 不写任何分隔符，自然读到行尾
```

---

## 分组元信息

| 元信息 | 语法 | 匹配行为 |
|--------|------|---------|
| 顺序（默认） | `(a, b, c)` 或 `seq(a, b, c)` | 按顺序依次匹配全部 |
| 择一 | `alt(a, b, c)` | 尝试每个，第一个成功为准 |
| 可选 | `opt(a)` | 失败不报错，继续匹配后续 |
| 尽可能多 | `some_of(a, b, c)` | 循环匹配，至少成功一次 |

---

## JSON 子字段语法

```wpl
json(type@key, type@key, ...)
```

- `type@key`：从 JSON 中提取名为 `key` 的字段，类型为 `type`
- 嵌套路径：`chars@user/name`（提取 `user.name`）
- 可选字段：`opt(chars)@email`（email 不存在时不报错）
- 字段命名：提取出的字段自动以 key 为名，或加 `:alias` 重命名

```wpl
// 实际示例
json(
    time@event_time,           // 提取 event_time 字段，类型 time
    chars@log_type:type,       // 提取 log_type，重命名为 type
    ip@src_ip,                 // 提取 src_ip，类型 ip
    digit@port,                // 提取 port，类型 digit
    opt(chars)@user_name,      // 可选字段
)
```

**注意**：JSON 对象本身用 `json(...)` 语法，**不是** `json:field_name`。

---

## KV 子字段语法

```wpl
kvarr(type@key, type@key, ...)
```

```wpl
// 空格分隔的 KV（src_ip=1.1.1.1 dst_ip=2.2.2.2 port=80）
kvarr(
    ip@src_ip,
    ip@dst_ip,
    digit@port,
)\s
```

KV 不指定子字段时，自动提取所有键值对：

```wpl
kvarr\s    // 提取所有 KV，以空格为 KV 对分隔符
```

---

## 注解

### tag 注解（每条规则必须加）

```wpl
#[tag(log_desc:"日志描述", log_type:"规则类型标识")]
```

- `log_desc`：日志的中文或英文描述
- `log_type`：规则类型标识，OML 中用 `read(log_type)` 引用

### copy_raw 注解

```wpl
#[copy_raw(name:"raw_msg")]    // 将原始日志行复制到 raw_msg 字段
```

原始字符串（避免转义）：

```wpl
#[tag(path:r#"C:\Program Files\App"#)]
```

---

## 预处理管道（整行处理）

写在规则体最前面，作用于整行原始输入：

| 函数 | 语法 | 说明 |
|------|------|------|
| BOM 去除 | `\| strip/bom \|` | 去掉文件 BOM 头 `\xEF\xBB\xBF` |
| Base64 解码 | `\| decode/base64 \|` | 对整行 Base64 解码 |
| 十六进制解码 | `\| decode/hex \|` | 对整行十六进制解码 |
| 引号/转义还原 | `\| unquote/unescape \|` | 移除外层引号并还原转义序列 |
| 自定义扩展 | `\| plg_pipe/name \|` | 自定义预处理插件 |

---

## 字段级管道函数

写在字段定义后，作用于该字段的值：

### 选择器函数

| 函数 | 说明 |
|------|------|
| `\|take(name)\|` | 选择指定字段为活跃字段 |
| `\|last()\|` | 选择最后一个字段为活跃字段 |

### 字段集检查函数（f_ 前缀，最常用）

| 函数 | 说明 | 示例 |
|------|------|------|
| `\|f_has(name)\|` | 检查字段是否存在 | `\|f_has(status)\|` |
| `\|f_chars_has(name, val)\|` | 字段值等于字符串 | `\|f_chars_has(type, login)\|` |
| `\|f_chars_not_has(name, val)\|` | 字段值不等于字符串 | `\|f_chars_not_has(level, error)\|` |
| `\|f_chars_in(name, [a,b,c])\|` | 字段值在列表中 | `\|f_chars_in(method, [GET,POST])\|` |
| `\|f_digit_has(name, num)\|` | 字段值等于数字 | `\|f_digit_has(code, 200)\|` |
| `\|f_digit_in(name, [200,201])\|` | 字段值在数字列表中 | |
| `\|f_ip_in(name, [1.1.1.1])\|` | IP 在列表中 | |

### 活跃字段检查函数（配合 take）

| 函数 | 说明 |
|------|------|
| `\|has()\|` | 活跃字段存在 |
| `\|chars_has(val)\|` | 活跃字段等于字符串 |
| `\|chars_not_has(val)\|` | 活跃字段不等于字符串 |
| `\|chars_in([a,b,c])\|` | 活跃字段值在列表中 |
| `\|digit_has(num)\|` | 活跃字段等于数字 |
| `\|digit_in([200,201])\|` | 活跃字段在数字列表中 |

### 转换函数

| 函数 | 说明 |
|------|------|
| `\|json_unescape()\|` | JSON 反转义 |
| `\|base64_decode()\|` | Base64 解码 |
| `\|chars_replace("old","new")\|` | 字符串替换 |

---

## 常用完整示例

### 纯 JSON 日志

```wpl
#[tag(log_desc:"产品名称-事件描述", log_type:"event_type")]
package vendor_product {
  rule rule_name {
    (
      json(
        time@event_time,
        chars@event_type:type,
        ip@src_ip,
        digit@src_port,
        chars@user_name,
      ) | f_chars_has(type, specific_value)
    )
  }
}
```

### JSON with BOM

```wpl
#[tag(log_desc:"...", log_type:"...")]
package vendor {
  rule rule_with_bom {
    | strip/bom |
    (
      json(time@ts, chars@msg)
    )
  }
}
```

### Syslog + JSON

```wpl
#[tag(log_desc:"...", log_type:"...")]
package vendor {
  rule syslog_json {
    | strip/bom |
    (
      _:pri<<,>>,       // syslog priority
      5*_,              // skip 5 syslog header fields
      symbol(prog-name),
      _,
      json(time@ts, chars@event)
    )
  }
}
```

### CLF 访问日志

```wpl
#[copy_raw(name:"raw_msg")]
package nginx {
  #[tag(log_desc:"Nginx 访问日志", log_type:"nginx_access")]
  rule nginx_access {
    (
      ip:src_ip,
      2*_,                      // 合并跳过 ident 和 authuser 两个字段
      time/clf:access_time<[,]>,
      http/request:request",
      http/status:status,
      digit:body_bytes_sent,
      chars:referer",
      chars:user_agent",        // 注意：用 chars 不用 http/agent
      chars:x_forwarded_for"
    )
  }
}
```

**关键点：**
- 字段之间空格分隔，**不需要写 `\s`**（空格是默认分隔符）
- `2*_` 合并跳过连续的 ident 和 authuser 两个字段
- `time/clf:t<[,]>` — CLF 时间用方括号包裹，必须加 `<[,]>`
- `http/request:req"` — HTTP 请求行用双引号包裹
- `chars:ua"` — UA 字段用 `chars` + `"` 引号格式，**不用 `http/agent`**（非标准浏览器 UA 会失败）

### KV 日志

```wpl
#[tag(log_desc:"...", log_type:"...")]
package vendor {
  rule kv_log {
    (
      chars\0 | chars_replace("\t", " ") | (
        kvarr(
          chars@hostname,
          ip@src_ip,
          digit@port,
          chars@event_type:type,
        )\s | f_chars_has(type, target_value)
      )
    )
  }
}
```

### 多变体 alt

```wpl
#[tag(log_desc:"...", log_type:"...")]
package vendor {
  rule multi_format {
    alt(
      (json(chars@format:type, ...) | f_chars_has(type, format_a)),
      (json(chars@format:type, ...) | f_chars_has(type, format_b))
    )
  }
}
```

---

## 分隔符易错点

```wpl
// ✅ 正确：空格分隔的字段不需要写 \s
(
    ip:src_ip,
    digit:port,
    chars:message
)

// ❌ 多余：写了 \s 但空格是默认的
ip:src_ip\s digit:port\s chars:message   // \s 是冗余的，最后字段也不加 \0

// ✅ 正确：只在非空格分隔时显式写分隔符
(chars:a, digit:b)\,    // 逗号分隔的组
kvarr(...)\s            // KV 以空格为对分隔符（kvarr 需要显式指定）

// ❌ 错误：把分隔符写在后面字段前面
ip \s digit       // 分隔符位置错了
// ✅ 正确：分隔符写在当前字段后面
ip\, digit\, chars    // 逗号分隔，最后字段不加 \0

// ❌ 错误：CLF 时间没有用 <[,]> 包裹
time/clf:t
// ✅ 正确
time/clf:t<[,]>

// ✅ N*_ 合并跳过连续字段
2*_        // 跳过 2 个字段（等同于 _, _）
5*_        // 跳过 5 个字段（syslog 头部常用）

// ❌ 错误：最后一个字段加 \0
chars:traceability_id\0    // 最后字段不需要 \0，自然读到行尾

// ✅ 正确：最后字段直接写，不加分隔符
chars:traceability_id

// ✅ \0 的正确用法：中间字段读到行尾后整体处理
chars\0 | chars_replace("\t", " ") | (kvarr(...)\s)
```
