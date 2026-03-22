# 常见日志格式规则模板

本文档提供常见日志格式的 WPL 规则模板，可直接复制使用或作为起点修改。

---

## Nginx 访问日志

### 标准 CLF 格式

**样本：**
```
192.168.1.10 - - [21/Jan/2025:01:40:02 +0800] "GET /api/user HTTP/1.1" 200 1234 "http://example.com/" "Mozilla/5.0 Chrome/90" "-"
```

**规则：**
```wpl
rule nginx_clf {
  (
    ip:client_ip,
    2*_,
    time/clf:timestamp<[,]>,
    http/request:request",
    http/status:status,
    digit:bytes,
    chars:referer",
    http/agent:user_agent",
    chars:xff"
  )
}
```

**输出字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| client_ip | ip | 客户端 IP |
| timestamp | time | 请求时间 |
| request | http/request | 请求行 |
| status | digit | 状态码 |
| bytes | digit | 响应字节数 |
| referer | chars | 来源页面 |
| user_agent | http/agent | 用户代理 |
| xff | chars | X-Forwarded-For |

---

### JSON 格式 Nginx

**样本：**
```json
{"time":"2025-01-21T01:40:02+08:00","remote_addr":"192.168.1.10","request":"GET /api HTTP/1.1","status":200}
```

**规则：**
```wpl
rule nginx_json {
  (
    json(
      time@time,
      ip@remote_addr,
      chars@request,
      digit@status
    )
  )
}
```

---

## Apache 访问日志

### Combined 格式

**样本：**
```
192.168.1.10 - admin [21/Jan/2025:01:40:02 +0800] "POST /login HTTP/1.1" 302 512 "http://example.com/" "Mozilla/5.0"
```

**规则：**
```wpl
rule apache_combined {
  (
    ip:client_ip,
    _,
    chars:user\ ,
    time/clf:timestamp<[,]>,
    http/request:request",
    http/status:status,
    digit:bytes,
    chars:referer",
    http/agent:user_agent"
  )
}
```

---

## AWS ALB 访问日志

**样本：**
```
http 2018-11-30T22:23:00.186641Z app/my-lb 192.168.1.10:2000 10.0.0.15:8080 0.01 0.02 0.01 200 200 100 200 "POST https://api.example.com/u HTTP/1.1" "Mozilla/5.0" "ECDHE" "TLSv1.3" arn:aws:elb:us:123:tg "Root=1" "api.example.com" "arn:aws:acm:cert" 1 2018-11-30T22:22:48Z "forward" "-" "-" "10.0.0.1:80" "200" "cls" "rsn" TID_x
```

**规则：**
```wpl
rule alb_access {
  (
    chars:type\ ,
    time_3339:timestamp\ ,
    chars:elb\ ,
    chars:client_ip_port\ ,
    chars:target_ip_port\ ,
    float:request_time\ ,
    float:target_time\ ,
    float:response_time\ ,
    digit:elb_status\ ,
    digit:target_status\ ,
    digit:recv_bytes\ ,
    digit:sent_bytes\ ,
    chars:request",
    chars:user_agent",
    chars:ssl_cipher",
    chars:ssl_version",
    chars:elb_arn",
    chars:trace_id",
    chars:domain",
    chars:cert_arn",
    digit:auth_latency\ ,
    time_3339:connect_time\ ,
    chars:action",
    chars:redirect_url",
    chars:error_reason",
    chars:target_group",
    chars:target_status_code",
    chars:classification\ ,
    chars:reason\0
  )
}
```

---

## Syslog 格式

### 标准 Syslog

**样本：**
```
<134>Jan 21 01:40:02 hostname sshd[1234]: Accepted password for user from 192.168.1.10 port 22
```

**规则：**
```wpl
rule syslog {
  (
    digit:priority<>,
    chars:timestamp\ ,
    chars:hostname\ ,
    chars:program,
    chars:pid<[,]>:,
    chars:message\0
  )
}
```

---

## JSON 日志

### 单行 JSON

**样本：**
```json
{"level":"INFO","time":"2025-01-21T01:40:02Z","msg":"request completed","status":200,"latency":0.05}
```

**规则：**
```wpl
rule json_log {
  (
    json(
      chars@level,
      time@time,
      chars@msg,
      digit@status,
      float@latency
    )
  )
}
```

### 嵌套 JSON

**样本：**
```json
{"timestamp":1767006286.7,"event":{"type":"request","data":{"path":"/api","method":"GET"}}}
```

**规则：**
```wpl
rule nested_json {
  (
    json(
      float@timestamp,
      chars@event/type,
      chars@event/data/path,
      chars@event/data/method
    )
  )
}
```

---

## KV 格式日志

### 空格分隔 KV

**样本：**
```
level=INFO time="2025-01-21T01:40:02Z" msg="request" status=200
```

**规则：**
```wpl
rule kv_log {
  (
    kvarr(
      chars@level,
      time@time,
      chars@msg,
      digit@status
    )
  )
}
```

### 方括号包裹 KV

**样本：**
```
[level=INFO, time="2025-01-21T01:40:02Z", msg="request", status=200]
```

**规则：**
```wpl
rule kv_bracket {
  (
    kvarr(
      chars@level,
      time@time,
      chars@msg,
      digit@status
    )<[,]>
  )
}
```

---

## CSV 格式

**样本：**
```
42,alice,2025-01-21,active
```

**规则：**
```wpl
rule csv_log {
  (
    digit:id\,
    chars:name\,
    time:date\,
    chars:status\0
  )
}
```

---

## 防火墙日志

**样本：**
```
2025-01-21T01:40:02Z ALLOW TCP 192.168.1.10:54321 -> 10.0.0.1:443
```

**规则：**
```wpl
rule firewall {
  (
    time_3339:timestamp\ ,
    chars:action\ ,
    chars:protocol\ ,
    ip:src_ip,
    chars:src_port\ ->\ ,
    ip:dst_ip,
    chars:dst_port\0
  )
}
```

---

## 使用建议

### 1. 从样本开始

```bash
# 保存样本
cat > sample.txt << 'EOF'
你的日志样本
EOF

# 创建规则
cat > rule.wpl << 'EOF'
rule parse {
  (...)
}
EOF

# 验证
wpl-check sample .
```

### 2. 逐步添加字段

1. 先解析前几个字段
2. 验证通过后再添加更多
3. 使用 `_` 跳过不需要的字段

### 3. 类型选择优先级

1. 具体类型：`ip`, `time/clf`, `http/request`
2. 通用类型：`digit`, `chars`
3. 结构类型：`json(...)`, `kvarr(...)`

### 4. 常见问题

| 问题 | 解决方案 |
|------|----------|
| 解析失败 | 检查分隔符、格式 |
| 字段类型错误 | 使用更通用的类型 |
| 残留数据 | 检查最后的 `\0` |

---

## 相关文档

- `references/wpl-authoring-routing.md` - WPL 编写入口
- wpl-rule-check skill - 规则验证工具