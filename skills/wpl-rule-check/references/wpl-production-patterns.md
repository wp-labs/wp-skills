# WPL 生产用规则模式

本文档收录真实生产环境中的 WPL 规则模式，覆盖主要日志格式。每个模式均附有样本说明和关键要点。

---

## 模式 1：纯 JSON 日志（带类型过滤）

**场景**：JSON 日志中有 type/log_type 字段区分事件类型，每种类型写一条规则。

**样本特征**：
```
{"event_type":"login","src_ip":"1.2.3.4","port":22,"user":"admin","time":"2025-01-01 12:00:00"}
```

**规则**：
```wpl
#[tag(log_desc: "产品名-登录事件日志", log_type: "login_event")]
package vendor_product {
  rule login_event {
    (
      json(
        time@time,
        chars@event_type:type,
        ip@src_ip,
        digit@port,
        chars@user,
      ) | f_chars_has(type, login)
    )
  }
}
```

**关键要点**：
- `json(time@time, ...)` 中 `type@key` 是固定语法，key 是 JSON 字段名
- `chars@event_type:type` — 提取 event_type 字段，重命名为 type（`:type` 是别名）
- `| f_chars_has(type, login)` — 过滤出 type == "login" 的记录
- 多个事件类型 → 写多条 rule，每条 rule 用不同 `f_chars_has` 过滤

---

## 模式 2：JSON 日志（@字段名简写，无显式类型）

**场景**：字段很多，类型可以自动推断时，用 `@fieldname` 简写不指定类型。

**样本特征**：
```
<128>August 19 18:54:21 2025 {"srcAddress":"10.1.1.1","destAddress":"2.2.2.2","srcPort":"80","severity":"5",...}
```

**规则**：
```wpl
#[tag(log_desc: "安恒APT探针告警日志", log_type: "das_apt_alert_log")]
package das {
  rule das_apt_alert_log_v2 {
    (
      _:pri<<,>>,
      4*_
    ),
    (
      json(
        @deviceAddress,
        @deviceName,
        ip@srcAddress,             // IP 字段显式指定类型
        ip@destAddress,
        digit@srcPort,             // 端口显式指定 digit
        digit@destPort,
        time@collectorReceiptTime, // 时间字段显式指定 time
        @severity,
        @eventId,
        array@attacker,            // 数组字段用 array
        array@victim,
      ) | f_chars_in(logType, [alert])
    )
  }
}
```

**关键要点**：
- `@fieldname` 等价于 `chars@fieldname`，仅当字段内容确实是字符串时使用
- IP、时间、端口等有语义的字段最好显式指定类型
- `array@fieldname` 提取 JSON 数组字段
- Syslog 前缀 `_:pri<<,>>` 后跟 `4*_` 跳过 4 个 syslog 头部字段，然后接 JSON 体

---

## 模式 3：Syslog + CEF + Tab 分隔 KV（复合格式）

**场景**：Syslog 格式 + CEF 头（`|` 分隔） + KV 正文（tab 分隔），需要处理 tab 换空格。

**样本特征**：
```
<14>Jan 28 23:21:42 TDA-7.localdomain CEF:0|AsiaInfo-Sec|产品名|7.0|4|事件名|2|key1='val1'\tkey2='val2'\t...
```

**规则**：
```wpl
#[tag(log_desc: "亚信安全TDA原始告警日志", log_type: "tda_origin_sec_alert_log")]
package asiainfos_tda {
  rule tda_origin_sec_alert_log {
    (
      _:pri<<,>>,
      time:log_time,
      chars:host_name,
    ),
    (
      chars:cef,
      chars:vendor,
      chars:product_name,
      chars:product_ver,
      chars:event_id,
      chars:event_name,
      chars:level,
    )\|,
    (
      chars\0 | chars_replace("\t", " ") | (
        kvarr(
          time_timestamp@Logtime,
          chars@log_type:type,
          chars@event_type,
          chars@rule_source,
          chars@rule_id,
        )\s | f_chars_has(type, 0)
      )
    )
  }
}
```

**关键要点**：
- 三个分组：syslog 前缀、CEF 头、KV 正文，**每组逗号分隔，最后一组无逗号**
- `(...)\ |` — 组级分隔符 `\|`，表示各字段以 `|` 分隔
- `chars\0 | chars_replace("\t", " ")` — 读整行，把 tab 替换为空格，再处理 KV
- `kvarr(...)\s | f_chars_has(type, 0)` — KV 以空格为对分隔符，过滤 log_type=0
- `time_timestamp@Logtime` — Unix 时间戳类型

---

## 模式 4：纯 JSON，大量字段，带 BOM

**场景**：JSON 日志带 BOM 头，字段很多。

**规则**：
```wpl
#[tag(log_desc: "...", log_type: "...")]
package vendor {
  rule rule_with_bom {
    | strip/bom |
    (
      json(
        time@event_time,
        chars@event_type:type,
        ip@src_ip,
        ip@dst_ip,
        digit@src_port,
        digit@dst_port,
        chars@threat_name,
      ) | f_chars_has(type, target_type)
    )
  }
}
```

**关键要点**：
- `| strip/bom |` 必须是第一条预处理管道
- BOM 不去掉，JSON 解析会失败

---

## 模式 5：Syslog + JSON（Cloudwalker/WebShell 格式）

**场景**：Syslog 前缀（priority + header） + 特定 symbol 标识 + JSON 体。

**样本特征**：
```
<14>Jul  1 09:00:00 hostname cloudwalker-webshell: {"event_create_time":"2025-07-01","file_path":"/www/..."}
```

**规则**：
```wpl
#[tag(log_desc: "云鸟Webshell检测日志", log_type: "cloudwalker_webshell")]
package aliyun_aqishi {
  rule cloudwalker_webshell {
    | strip/bom |
    (
      _:pri<<,>>,
      5*_,
      symbol(cloudwalker-webshell),
      _,
      json(
        time@event_create_time,
        chars@file_path,
        ip@server_ip,
        chars@threat_type:type,
      ) | f_chars_has(type, webshell)
    )
  }
}
```

**关键要点**：
- `_:pri<<,>>` — 匹配 `<14>` 格式的 syslog priority
- `5*_` — 跳过 5 个空格分隔字段（时间月、日、时间、hostname 等）
- `symbol(cloudwalker-webshell)` — 精确匹配 symbol，匹配失败则整条规则失败
- `_` — 跳过 symbol 后的冒号或空格
- 然后才是 JSON 体

---

## 模式 6：CLF 访问日志（Apache/Nginx）

**场景**：经典的 Apache Combined Log Format。

**样本特征**：
```
192.168.1.1 - frank [06/Aug/2019:12:12:19 +0800] "GET /index.html HTTP/1.1" 200 1234 "http://referer.com" "Mozilla/5.0..."
```

**规则**：
```wpl
#[copy_raw(name:"raw_msg")]
package nginx {
  #[tag(log_desc: "Nginx 访问日志", log_type: "nginx_access")]
  rule nginx_access {
    (
      ip:src_ip,
      2*_,
      time/clf:access_time<[,]>,
      http/request:request",
      http/status:status,
      digit:body_bytes_sent,
      chars:referer",
      chars:user_agent",
      chars:x_forwarded_for"
    )
  }
}
```

**关键要点**：
- 字段之间空格分隔，**不需要写 `\s`**（空格是默认分隔符）
- `2*_` — 合并跳过 ident 和 authuser 两个字段（等同于 `_, _`）
- `time/clf:access_time<[,]>` — CLF 时间用方括号包裹，必须加 `<[,]>`
- `http/request:request"` — HTTP 请求行用双引号包裹
- `chars:user_agent"` — UA 字段用 `chars` + `"` 引号格式，**不用 `http/agent`**（非浏览器 UA 会失败）

---

## 模式 7：KV 日志（等号分隔，空格为对分隔符）

**场景**：`key=value key=value ...` 格式，有时带引号。

**样本特征**：
```
src_ip=1.1.1.1 dst_ip=2.2.2.2 sport=80 dport=443 action=allow protocol=TCP
```

**规则**：
```wpl
#[tag(log_desc: "防火墙流量日志", log_type: "fw_traffic")]
package vendor_fw {
  rule traffic_log {
    (
      kvarr(
        ip@src_ip,
        ip@dst_ip,
        digit@sport,
        digit@dport,
        chars@action,
        chars@protocol,
      )\s
    )
  }
}
```

**关键要点**：
- `kvarr(...)\s` — KV 对之间用空格分隔
- 不需要预先处理，kvarr 自动识别 `=` 或 `:` 作为键值分隔符
- 如果有 tab 需替换：`chars\0 | chars_replace("\t", " ") | (kvarr(...)\s)`

---

## 模式 8：多变体 alt 分支

**场景**：同一个 JSON 日志中，根据不同 type 字段解析成不同的字段集合。

**样本特征**：
```
{"log_type":"1","field_a":"val"}  或  {"log_type":"2","field_b":"val"}
```

**规则**：
```wpl
#[tag(log_desc: "...", log_type: "type_a_or_b")]
package vendor {
  rule type_a {
    (
      json(
        chars@log_type:type,
        chars@field_a,
        ip@src_ip,
      ) | f_chars_has(type, 1)
    )
  }

  rule type_b {
    (
      json(
        chars@log_type:type,
        chars@field_b,
        digit@count,
      ) | f_chars_has(type, 2)
    )
  }
}
```

**关键要点**：
- 多变体用多条 rule，每条 rule 对应一种类型
- 不建议在同一 rule 内用 `alt` 处理完全不同字段集的变体（字段冲突）
- 若只是部分字段可选，用 `opt(type)@fieldname`

---

## 模式 9：f_chars_in 多值过滤

**场景**：一条规则匹配多个 type 值。

**规则**：
```wpl
rule multi_type_events {
  (
    json(
      chars@logType:type,
      time@ts,
      ip@srcAddress,
    ) | f_chars_in(type, [alert, warning, notice])
  )
}
```

**关键要点**：
- `f_chars_in(field, [val1, val2, val3])` — 值列表用方括号，逗号分隔，无引号
- 适合一条规则覆盖多个相似事件类型

---

## 模式 10：Base64 编码正文

**场景**：日志正文经过 Base64 编码。

**规则**：
```wpl
#[tag(log_desc: "...", log_type: "...")]
package vendor {
  rule base64_payload {
    | decode/base64 |
    (
      json(chars@user, chars@action, time@ts)
    )
  }
}
```

**关键要点**：
- `| decode/base64 |` 作用于整行，在字段解析之前执行
- 解码失败会导致规则失败，需确认样本确实是 Base64

---

## 模式 11：chars_replace 预处理 + KV

**场景**：KV 正文用 tab 分隔，需先替换为空格才能用 kvarr 解析。

```wpl
rule tab_kv_log {
  (
    chars\0 | chars_replace("\t", " ") | (
      kvarr(
        chars@key1,
        ip@src_ip,
        digit@port,
      )\s
    )
  )
}
```

**关键要点**：
- `chars\0` — 读取整行到行尾
- `| chars_replace("\t", " ")` — 字段级 pipe，把 tab 替换为空格
- `| (kvarr(...)\s)` — 再把替换后的字符串作为 KV 解析

---

## 常见错误对比

| 错误写法 | 正确写法 | 说明 |
|---------|---------|------|
| `json.field_name` | `json(chars@field_name)` | JSON 子字段不用点号 |
| `kvarr.key` | `kvarr(chars@key)` | KV 子字段不用点号 |
| `f_chars_has(type, "login")` | `f_chars_has(type, login)` | 过滤值不加引号 |
| `ip time chars` | `ip:src_ip, time:ts, chars:msg` | 字段必须命名；空格分隔不写 `\s`；最后字段不写 `\0` |
| `http/agent:ua` | `chars:ua` | 非浏览器 UA 用 chars |
| `time/clf:t` | `time/clf:t<[,]>` | CLF 时间用方括号包裹 |
| `json(chars@type) \| f_chars_has(type)` | `json(chars@type:type) \| f_chars_has(type, target)` | filter 需要值 |
| `kvarr\| f_chars_has(k, v)` | `kvarr\s \| f_chars_has(k, v)` | kvarr 需要分隔符 |
