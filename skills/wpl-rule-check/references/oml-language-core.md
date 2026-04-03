# OML 语言核心参考

本文档是 OML 富化模型编写的权威参考，用于判断语法正确性、选择表达式和函数。

---

## 文件结构

```oml
name : <oml_name>
rule : <package>/<rule_name>
---
// 赋值语句，每行必须以分号结尾
field_name = expression;
field_name : type = expression;
```

- `name`：OML 模型唯一标识，建议与 WPL rule 对应
- `rule`：匹配的 WPL 规则路径，支持通配符 `*`（如 `rule : vendor/*`）
- `---`：分隔头部与正文
- 每个赋值语句必须以 `;` 结尾（最常见的语法错误）

---

## 类型系统

OML 中 8 种基本类型：

| 类型 | 标识符 | 说明 |
|------|--------|------|
| 字符串 | `chars` | 文本 |
| 整数 | `digit` | 整数 |
| 浮点 | `float` | 浮点数 |
| IP | `ip` | IPv4/IPv6 |
| 时间 | `time` | 时间对象 |
| 布尔 | `bool` | true/false |
| 对象 | `obj` | 嵌套对象 |
| 数组 | `array` | 数组 |

显式声明类型：`field : type = expression;`

---

## read vs take

| | `read` | `take` |
|--|--------|--------|
| 行为 | 克隆值，源字段保留 | 移走值，源字段删除 |
| 多次使用 | 支持 | 不支持（第二次失败） |
| 使用场景 | 字段在多处引用 | 字段只用一次 |

查找顺序：先找目标记录（dst），再找源记录（src）。

```oml
// read：可多次引用
ip_field = read(src_ip);
ip_str = read(src_ip) | to_str;    // 仍可再次读取

// take：仅用一次，通常配合 pipe
raw_msg = pipe take(raw_msg) | json_escape;
```

---

## 表达式类型

### 1. 值字面量

```oml
text = chars(hello);
count = digit(100);
addr = ip(192.168.1.1);
flag = bool(true);
```

### 2. read/take

```oml
// 基本读取
field = read(source_field);
field : ip = read(src_ip);           // 显式类型

// 优先级读取（按顺序尝试，返回第一个存在的）
field = read(option:[field1, field2, field3]);

// 默认值
field = read(source_field) { _ : chars(default) };
field = read(timestamp) { _ : Now::time() };
```

### 3. 管道表达式

```oml
// pipe 关键字可省略
result = pipe read(field) | function1 | function2(param);
result = read(field) | function1 | function2(param);
```

### 4. match 表达式

#### 值匹配

```oml
status = match read(code) {
    chars(200) => chars(success);
    chars(404) => chars(not_found);
    chars(500) => chars(server_error);
    _ => chars(unknown);
};
```

#### 函数匹配（v1.13.4+）

```oml
// 字符串函数
event_type = match read(log_line) {
    starts_with('[ERROR]') => chars(error);
    starts_with('[WARN]') => chars(warning);
    contains('exception') => chars(exception);
    ends_with('.failed') => chars(failure);
    is_empty() => chars(empty);
    iequals('success') => chars(ok);    // 大小写不敏感
    regex_match('^\d{4}-\d{2}-\d{2}') => chars(timestamped);
    _ => chars(other);
};

// 数值函数
level = match read(count) {
    gt(1000) => chars(critical);
    gt(500) => chars(high);
    gt(100) => chars(medium);
    in_range(10, 100) => chars(low);
    lt(10) => chars(minimal);
    eq(0) => chars(zero);
    _ => chars(unknown);
};
```

**match 函数参数引号规则**：
- 字符串参数必须加引号：`starts_with('[ERROR]')`
- 数值参数不加引号：`gt(100)`, `in_range(10, 20)`
- match 按从上到下顺序匹配，第一个成功的分支执行

### 5. object 表达式

```oml
user_info : obj = object {
    id = read(user_id);
    name = read(username);
    ip : ip = read(client_ip);
};
```

### 6. collect 表达式

```oml
// 收集多个字段为数组
ports : array = collect read(keys:[sport, dport]);

// 通配符收集
cpu_metrics : array = collect read(keys:[cpu_*]);
```

### 7. fmt 表达式

```oml
// 字符串格式化，{} 占位符按位置填充
message = fmt("{}:{}", @src_ip, @src_port);
desc = fmt("用户 {} 从 {} 登录", @username, @src_ip);
```

### 8. SQL 表达式（资产富化）

```oml
// 单字段结果
asset_type = select asset_type from asset_enrichment where ip = @alert_ip;

// 多字段结果（目标字段用逗号分隔）
sip_asset_id, sip_asset_type, sip_name = select asset_id, asset_type, asset_name from asset_enrichment where ip = @sip;

// IP 范围查询（先转整数）
victim_ip_int = read(victim_ip) | ip4_to_int;
victim_org = select org_name from asset_network where ip_start_int <= @victim_ip_int and ip_end_int >= @victim_ip_int;
```

---

## 内置函数

| 函数 | 返回类型 | 说明 |
|------|---------|------|
| `Now::time()` | `time` | 当前时间 |
| `Now::date()` | `digit` | 当前日期（YYYYMMDD） |
| `Now::hour()` | `digit` | 当前时间精确到小时（YYYYMMDDHH） |

```oml
collect_time_tmp = Now::time();
collect_time = pipe @collect_time_tmp | Time::to_ts_ms;
```

---

## 管道函数速查

### 时间函数

| 函数 | 说明 | 输出 |
|------|------|------|
| `Time::to_ts` | Unix 时间戳（秒），UTC+8 | `digit` |
| `Time::to_ts_ms` | Unix 时间戳（毫秒），UTC+8 | `digit` |
| `Time::to_ts_us` | Unix 时间戳（微秒），UTC+8 | `digit` |
| `Time::to_ts_zone(offset, unit)` | 指定时区时间戳 | `digit` |

```oml
// 最常用：UTC+8 毫秒时间戳
ts = read(event_time) | Time::to_ts_zone(8, ms);

// UTC 时间戳（秒）
utc_ts = read(event_time) | Time::to_ts_zone(0, s);

// 系统采集时间
collect_time_tmp = Now::time();
collect_time = pipe @collect_time_tmp | Time::to_ts_ms;
```

### 编码函数

| 函数 | 说明 |
|------|------|
| `base64_encode` | Base64 编码 |
| `base64_decode` | Base64 解码（默认 UTF-8） |
| `base64_decode(Gbk)` | GBK 编码的 Base64 解码 |

### 转义函数

| 函数 | 说明 |
|------|------|
| `json_escape` | JSON 转义（存储 raw_msg 时使用） |
| `json_unescape` | JSON 反转义 |
| `html_escape` | HTML 转义 |
| `html_unescape` | HTML 反转义 |

### 数据访问函数

| 函数 | 说明 |
|------|------|
| `nth(index)` | 数组第 index 个元素（从 0 开始） |
| `get(key)` | 对象中名为 key 的字段 |
| `url(domain/host/path/uri/params)` | 提取 URL 各部分 |
| `path(name/path)` | 提取文件路径中的文件名或目录 |
| `sxf_get(field)` | 提取特殊格式文本中的字段 |

### 转换函数

| 函数 | 说明 |
|------|------|
| `to_str` | 转字符串 |
| `to_json` | 转 JSON 字符串 |
| `ip4_to_int` | IPv4 转整数（用于 IP 范围查询） |

### 控制函数

| 函数 | 说明 |
|------|------|
| `skip_empty` | 值为空时跳过此字段输出 |
| `map_to(value)` | 非 ignore 时替换为指定值（字符串需引号，数值不需要） |
| `starts_with('prefix')` | pipe 过滤：以前缀开头则保留，否则变 ignore |
| `skip_empty` | 值为空（`""`/`0`/`[]`）时输出 ignore |

---

## static 块

用于声明模型级常量，仅初始化一次：

```oml
name : rule_with_static
rule : vendor/rule
---
static {
    error_template = object {
        id = chars(E001);
        desc = chars("错误描述模板");
    };
    warn_template = object {
        id = chars(W001);
        desc = chars("警告描述模板");
    };
}

Content = read(Content);

target_tpl = match Content {
    starts_with("ERROR") => error_template;
    starts_with("WARN") => warn_template;
    _ => error_template;
};

EventId = target_tpl | get(id);
EventDesc = target_tpl | get(desc);
```

**限制**：
- static 中不能调用 `read()`/`take()`（依赖运行时输入的函数）
- static 变量仅在当前模型内可见

---

## 通配符与批量处理

```oml
// 批量取走所有字段
* = take();

// 批量取走特定前缀的字段
alert* = take();

// 收集通配符字段到数组
cpu_metrics = collect read(keys:[cpu_*]);
```

---

## 参数化读取

```oml
// option：优先级读取，按顺序尝试，返回第一个存在的值
alert_ip = read(option:[dst_ip, clientip, wp_src_ip]);

// keys：收集多个字段为数组
ports = collect read(keys:[sport, dport, port]);

// 路径读取
username = read(/user/info/name);
```

---

## 常用语法模式

### 标准头部块（每个 OML 必须包含）

```oml
name : rule_name
rule : package/rule_name
---
access_ip: ip = read(wp_src_ip);
log_desc = read(log_desc);
log_type = read(log_type);
raw_msg = pipe take(raw_msg) | json_escape;

// 业务字段紧跟此处，字段之间不加空行
field1 = read(f1);
field2 = read(f2);
```

**空行规则**：共用 4 字段后加一个空行，业务字段之间不加任何空行。

### 时间字段转时间戳

```oml
// 从日志字段转换
occur_time = read(event_time) | Time::to_ts_zone(8, ms);

// 时间字段作为中间变量
start_time_tmp = read(start_time);
start_ts = pipe @start_time_tmp | Time::to_ts_zone(8, ms);
```

### 枚举映射

```oml
platform = match read(option:[plat_id]) {
    chars(1) => chars(Windows);
    chars(2) => chars(Linux);
    chars(3) => chars(MacOS);
    _ => chars(Unknown);
};
```

### IP 转整数（用于范围查询）

```oml
src_ip_int = read(src_ip) | ip4_to_int;
src_org = select org_name from asset_network where ip_start_int <= @src_ip_int and ip_end_int >= @src_ip_int;
```

### 资产富化

```oml
alert_ip = read(option:[dst_ip, src_ip]);
asset_type, asset_name = select asset_type, asset_name from asset_enrichment where ip = @alert_ip;
```

---

## 易错点

### 1. 分号缺失（最常见错误）

```oml
// ❌ 错误
field1 = read(x)
field2 = read(y)

// ✅ 正确
field1 = read(x);
field2 = read(y);
```

### 2. rule 路径不匹配 WPL

```oml
// WPL 中定义：package vendor { rule login_event { ... } }
// OML 中 rule 必须匹配

// ❌ 错误
rule : login_event

// ✅ 正确
rule : vendor/login_event
```

### 3. ignore 传播

```oml
// 如果 src_ip 不存在，read 返回 ignore
// ignore 会在后续管道中继续传播，最终该字段不输出
src_ip = read(src_ip);

// 需要提供默认值时
src_ip = read(src_ip) { _ : ip(0.0.0.0) };
```

### 4. take 后不能再次读取

```oml
// ❌ 错误：take 后再读
raw = take(raw_msg);
raw2 = read(raw_msg);    // raw_msg 已被移走，返回 ignore

// ✅ 正确：只 take 一次
raw_msg = pipe take(raw_msg) | json_escape;
```

### 5. match 函数参数引号

```oml
// ❌ 错误：字符串不加引号
starts_with([ERROR])

// ❌ 错误：数值加引号
gt('100')

// ✅ 正确
starts_with('[ERROR]')
gt(100)
```

### 6. @ref 语法

```oml
// @ 引用语法：引用已定义的目标字段
collect_time_tmp = Now::time();
collect_time = pipe @collect_time_tmp | Time::to_ts_ms;
//                  ^ 引用 collect_time_tmp 这个已定义的字段
```
