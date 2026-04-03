# OML 富化模式

---

## 模式 1：标准头部块（每个 OML 必须包含）

```oml
name : rule_name
rule : package/rule_name
---
access_ip: ip = read(wp_src_ip);
log_desc = read(log_desc);
log_type = read(log_type);
raw_msg = pipe take(raw_msg) | json_escape;

// ===== 业务字段紧跟，业务字段之间不加空行 =====
```

**空行规则**：
- 共用 4 个头部字段后加**一个**空行
- 业务字段之间**不加任何空行**

---

## 模式 2：时间字段转毫秒时间戳

```oml
// 从日志字段转换（UTC+8）
occur_time = pipe read(event_time) | Time::to_ts_zone(8, ms);

// Unix 秒级时间戳字段（time_timestamp 类型）
occur_time = pipe read(Logtime) | Time::to_ts_zone(0, ms);

// 先读为中间变量再转换
start_time_raw = read(startTime);
start_ts = pipe @start_time_raw | Time::to_ts_zone(8, ms);
```

---

## 模式 3：枚举值映射（match）

```oml
// 数字枚举
attack_direction = match read(option:[attack_direction]) {
    digit(0) => chars(外网->内网);
    digit(1) => chars(内网->外网);
    _ => chars(未知);
};

// 字符串枚举
event_type = match read(option:[event_type]) {
    chars(1) => chars(入侵检测);
    chars(2) => chars(病毒检测);
    chars(3) => chars(威胁情报);
    _ => chars(其他);
};

// 透传原值兜底
trans_layer_protocol = match read(option:[transProtocol]) {
    chars(tcp) => chars(TCP);
    chars(udp) => chars(UDP);
    _ => read(transProtocol);
};
```

**关键要点**：
- `option:[field]` 字段不存在时不报错
- 值匹配语法：`chars(val)` 或 `digit(val)`，值不加引号
- `_` 兜底分支

---

## 模式 4：多字段优先级读取（option）

```oml
// 尝试 dst_ip，不存在则尝试 src_ip
alert_ip = read(option:[dst_ip, src_ip]);

// 多个候选字段
alert_desc = read(option:[alarmDesc, message, desc]);
```

---

## 完整 OML 示例

```oml
name : vendor_product_alert
rule : vendor_product/alert_rule
---
access_ip: ip = read(wp_src_ip);
log_desc = read(log_desc);
log_type = read(log_type);
raw_msg = pipe take(raw_msg) | json_escape;

occur_time = pipe read(event_time) | Time::to_ts_zone(8, ms);
sip: ip = read(src_ip);
dip: ip = read(dst_ip);
sport = read(src_port);
dport = read(dst_port);
trans_layer_protocol = read(protocol);
alert_name = read(alert_name);
severity = read(severity);
attack_direction = match read(option:[direction]) {
    chars(inbound) => chars(外网->内网);
    chars(outbound) => chars(内网->外网);
    _ => chars(未知);
};
```

---

## 常见错误

| 错误写法 | 正确写法 | 说明 |
|---------|---------|------|
| `field = read(x)` 无分号 | `field = read(x);` | 每行必须有分号 |
| `rule : rule_name` | `rule : package/rule_name` | rule 必须含 package 路径 |
| `match read(x) { 200 => ... }` | `match read(x) { digit(200) => ... }` | match 值必须有类型 |
| 业务字段间加空行 | 业务字段间不加空行 | 只有头部 4 字段后加一个空行 |
