# WP 配置文件详解

本文档介绍 WarpParse 主要配置文件的结构和参数。

## 配置文件概览

| 文件 | 位置 | 用途 |
|------|------|------|
| wparse.toml | `conf/wparse.toml` | 主配置文件 |
| wpsrc.toml | `topology/sources/wpsrc.toml` | 数据源配置 |
| sinks | `topology/sinks/business.d/` 和 `infra.d/` | 输出路由配置 |
| wpgen.toml | `conf/wpgen.toml` | 数据生成配置 |

---

## wparse.toml - 主配置文件

```toml
version = "1.0"
robust  = "normal"           # debug|normal|strict

[models]
wpl       = "./models/wpl"     # WPL 规则目录
oml       = "./models/oml"     # OML 模型目录
knowledge = "./models/knowledge"  # 知识库目录

[topology]
sources = "./topology/sources"   # 数据源配置目录
sinks   = "./topology/sinks"     # 输出路由目录

[performance]
rate_limit_rps = 10000        # 限速（records/second）
parse_workers  = 2            # 解析并发 worker 数
reload_timeout_ms = 10000     # reload 超时（毫秒）

[rescue]
path = "./data/rescue"        # 救援数据目录

[log_conf]
output = "File"               # Console|File|Both
level  = "warn,ctrl=info"     # 日志级别

[log_conf.file]
path = "./data/logs"          # 日志文件目录

[stat]
[[stat.pick]]                 # 采集阶段统计
key    = "pick_stat"
target = "*"

[[stat.parse]]                # 解析阶段统计
key    = "parse_stat"
target = "*"

[[stat.sink]]                 # 下游阶段统计
key    = "sink_stat"
target = "*"
```

### 关键参数说明

| 参数 | 说明 | 推荐值 |
|------|------|--------|
| `robust` | 容错模式：debug/normal/strict | normal |
| `rate_limit_rps` | 解析速率限制 | 根据机器配置 |
| `parse_workers` | 解析线程数 | CPU 核心数 |
| `reload_timeout_ms` | 热加载超时时间 | 10000 |
| `log_conf.level` | 日志级别 | warn,ctrl=info |

### 容错模式

| 模式 | 说明 |
|------|------|
| `debug` | 调试模式，详细输出 |
| `normal` | 正常模式，平衡性能和容错 |
| `strict` | 严格模式，错误即停止 |

### 知识库配置

```toml
[models]
knowledge = "./models/knowledge"    # 知识库目录（knowdb + semantic_dict）
```

知识库目录结构：
```
models/knowledge/
├── knowdb.toml                  # 知识库表定义
├── semantic_dict.toml           # 语义词典配置
└── <table_name>/
    ├── create.sql               # 建表 SQL
    ├── insert.sql               # 插入 SQL（参数化）
    └── data.csv                 # 初始数据
```

### 语义分析配置

```toml
[semantic]
enabled = false                   # 是否启用语义分析（默认关闭，关闭可节省约 20MB 内存）
```

### Admin API 配置

```toml
[admin_api]
enabled = false                   # 是否启用管理 API
bind = "127.0.0.1:19090"         # 监听地址
request_timeout_ms = 15000       # 请求超时（毫秒）
max_body_bytes = 4096            # 最大请求体（字节）

[admin_api.tls]
enabled = false                   # TLS 默认关闭（仅 loopback）
cert_file = ""
key_file = ""

[admin_api.auth]
mode = "bearer_token"            # 认证模式
token_file = "${HOME}/.warp_parse/admin_api.token"
```

### 远端工程同步配置

```toml
[project_remote]
enabled = false                   # 是否启用远端工程同步
repo = ""                         # 远端 Git 仓库 URL
init_version = ""                 # 初始版本（空=最新 release tag）
```

---

## wpsrc.toml - 数据源配置

### 配置结构

```toml
[[sources]]
key = "source_identifier"       # 源唯一标识
connect = "connector_id"        # 连接器 ID
enable = true                   # 是否启用（可选，默认 true）
tags = ["type:access", "env:prod"]  # 标签（可选）

[sources.params]
# 连接器参数覆写
```

### 文件源示例

```toml
[[sources]]
key = "access_log"
connect = "file_src"
params = {
    base = "./logs",
    file = "access.log",
    encode = "text"
}
tags = ["type:access", "env:prod"]
```

### 文件源路径配置详解

**路径拼接规则**：`{base}/{file}`

| 参数 | 说明 | 示例 |
|------|------|------|
| `base` | 目录路径（相对于工程根目录） | `./data/in_dat` |
| `file` | 文件名（不含路径） | `nginx_access.dat` |

**正确示例**：

```toml
# 实际路径: ./data/in_dat/nginx_access.dat
[sources.params]
base = "./data/in_dat"
file = "nginx_access.dat"
```

**常见错误**：

| 错误配置 | 问题 | 正确配置 |
|----------|------|----------|
| `file = "data/in_dat/nginx.dat"` | file 不应包含路径 | `base = "./data/in_dat"`, `file = "nginx.dat"` |
| `base = "./data/in_dat/nginx.dat"` | base 应是目录不是文件 | `base = "./data/in_dat"`, `file = "nginx.dat"` |
| `base = "data/in_dat"` | 缺少 `./` 前缀 | `base = "./data/in_dat"` |
| `base = "/abs/path"` | 绝对路径可用但不推荐 | 使用相对路径 `./data/in_dat` |

**路径验证方法**：

```bash
# 在工程根目录下验证
ls -la ./data/in_dat/nginx_access.dat

# 或拼接验证
ls -la {base}/{file}
```

### Syslog 源示例

#### UDP Syslog

```toml
[[sources]]
key = "syslog_udp"
connect = "syslog_udp_src"
params = {
    port = 1514,
    header_mode = "parse",
    prefer_newline = true
}
tags = ["protocol:syslog", "transport:udp"]
```

#### TCP Syslog（推荐用于接收 wpgen 等生成器数据）

```toml
[[sources]]
key = "syslog_tcp"
enable = true
connect = "syslog_tcp_src"
tags = ["type:demo"]

[sources.params]
addr = "0.0.0.0"       # 监听地址
port = 1514            # 监听端口
protocol = "tcp"       # 固定为 tcp
```

**TCP 源说明：**
- `addr`：监听地址，`0.0.0.0` 表示所有网卡
- `port`：监听端口，与 wpgen `tcp_sink` 输出端口一致
- `protocol`：固定为 `tcp`
- 接收原始 TCP 流，配合 `tcp_sink` 使用无需额外 header 处理

### Kafka 源示例

```toml
[[sources]]
key = "kafka_logs"
connect = "kafka_src"
params = {
    brokers = "localhost:9092",
    topic = ["access_log"],
    group_id = "wparse_group"
}
```

---

## Sink 配置 - 输出路由

### 目录结构

```
topology/sinks/
├── business.d/      # 业务组路由
│   └── *.toml
├── infra.d/         # 基础组路由
│   └── *.toml
└── defaults.toml    # 默认配置
```

### defaults.toml

```toml
[defaults]
tags = ["env:dev"]

[defaults.expect]
basis = "total_input"
mode  = "warn"
```

### 基础组示例（Monitor Sink）

```toml
# infra.d/monitor.toml
version = "2.0"

[sink_group]
name = "monitor"
batch_size = 1             # 批量大小（条），小值保证监控实时性
batch_timeout_ms = 300     # 刷新超时（毫秒）

[[sink_group.sinks]]
name = "monitor"
connect = "file_proto_sink"
params = { file = "monitor.dat" }

[sink_group.sinks.expect]
max = 1.0                  # 预期最大输出比例
```

### 业务组示例

```toml
# business.d/access.toml
version = "2.0"

[sink_group]
name = "/sink/access"
oml  = ["/oml/access*"]

[[sink_group.sinks]]
name = "access_out"
connect = "file_json_sink"
params = { base = "./out", file = "access.json" }

[[sink_group.sinks]]
name = "kafka_out"
connect = "kafka_sink"
params = { topic = "parsed_access" }
filter = "./filter.conf"   # 可选：过滤条件
```

### 路由匹配规则

| 字段 | 说明 |
|------|------|
| `oml` | OML 模型匹配（支持通配符） |
| `rule` | WPL 规则匹配 |
| `filter` | 过滤条件文件 |

### Sink 关键参数

| 参数 | 位置 | 说明 | 示例 |
|------|------|------|------|
| `batch_size` | `sink_group` | 批量大小（条），数据到达此数量或超时后刷新 | `batch_size = 1024` |
| `batch_timeout_ms` | `sink_group` | 批量刷新超时（毫秒） | `batch_timeout_ms = 300` |
| `connect` | `sinks` | 输出连接器 ID | `connect = "file_json_sink"` |
| `tags` | `sinks` | 路由标签过滤 | `tags = ["sink:json"]` |

### Expect 约束说明

```toml
[sink_group.sinks.expect]
basis = "total_input"     # 参照基准：total_input
mode  = "warn"            # 越界行为：warn | error
ratio = 0.8               # 期望占比
tol   = 0.02              # 容忍偏差
max   = 1.0               # 最大允许比例
min   = 0.0               # 最小允许比例
```

---

## wpgen.toml - 数据生成配置

### 基本配置

```toml
[generator]
mode = "sample"        # rule | sample
count = 1000           # 总生成条数
speed = 1000           # 基准速度（行/秒），0 表示无限制
parallel = 2           # 并行 worker 数

# 输出连接器（支持任意 sink connector）
[output]
connect = "file_json_sink"    # 输出连接器 ID

[output.params]
base = "./data/in_dat"
file = "gen.dat"

[logging]
level = "debug"
output = "file"
file_path = "./data/logs"
```

### 动态速度配置（speed_profile）

支持多种速率模型模拟真实流量场景。当 `speed_profile` 存在时，`speed` 字段仅作为回退基准使用。

#### 恒定速率（Constant）

```toml
[generator.speed_profile]
type = "constant"
rate = 5000                # 恒定速率（行/秒）
```

#### 正弦波动（Sinusoidal）— 推荐用于模拟周期性业务流量

```toml
[generator.speed_profile]
type = "sinusoidal"
base = 2000                # 基准速率（行/秒）
amplitude = 1000           # 波动幅度（行/秒），峰值=base+amplitude，谷值=base-amplitude
period_secs = 60.0         # 波动周期（秒）
```

#### 阶梯变化（Stepped）— 模拟峰谷时段

```toml
[generator.speed_profile]
type = "stepped"
steps = [[30.0, 1000], [60.0, 5000], [30.0, 2000]]   # [(持续时间秒, 速率), ...]
loop_forever = true        # 是否循环
```

#### 突发模式（Burst）— 模拟流量尖刺

```toml
[generator.speed_profile]
type = "burst"
base = 1000                # 基准速率
burst_rate = 10000         # 突发峰值速率
burst_duration_ms = 500    # 突发持续时间（毫秒）
burst_probability = 0.05   # 每秒触发概率（0.0~1.0）
```

#### 渐进模式（Ramp）— 压测预热/冷却

```toml
[generator.speed_profile]
type = "ramp"
start = 100                # 起始速率
end = 10000                # 目标速率
duration_secs = 300.0      # 爬坡时长（秒）
```

#### 随机波动（RandomWalk）— 模拟自然抖动

```toml
[generator.speed_profile]
type = "random_walk"
base = 5000                # 基准速率
variance = 0.3             # 波动范围（0.0~1.0），0.3 表示 ±30%
```

#### 复合模式（Composite）— 叠加多种模型

```toml
[generator.speed_profile]
type = "composite"
combine_mode = "average"    # average | max | min | sum

[[generator.speed_profile.profiles]]
type = "sinusoidal"
base = 5000
amplitude = 2000
period_secs = 60.0

[[generator.speed_profile.profiles]]
type = "random_walk"
base = 5000
variance = 0.1
```

### 输出连接器

wpgen 输出走统一 connector 系统，`connect` 字段指定连接器 ID：

| 连接器 | 用途 | 常用参数 |
|--------|------|----------|
| `file_json_sink` | JSON 文件输出 | `base`, `file` |
| `file_proto_sink` | Proto 格式文件输出 | `base`, `file` |
| `file_raw_sink` | 原始文件输出 | `base`, `file` |
| `tcp_sink` | TCP 输出（配合 wparse TCP source） | `addr`, `port`, `framing` |

#### TCP 输出示例（配合 wparse syslog_tcp_src 实现端到端管线）

```toml
[output]
connect = "tcp_sink"

[output.params]
addr = "127.0.0.1"
port = 1514
framing = "line"           # line | len
```

---

## 常见问题

### 配置检查

```bash
# 检查所有配置
wproj check

# 仅检查配置文件
wproj check --what conf

# JSON 输出
wproj check --json
```

### 配置覆写规则

- 覆写键必须在连接器 `allow_override` 白名单中
- 超出白名单会报错
- 使用 `wproj sources list` 和 `wproj sinks list` 查看解析结果

### 日志级别调整

```toml
[log_conf]
output = "Both"
level  = "debug"           # 全部 debug
level  = "warn,ctrl=info"  # ctrl 模块 info，其他 warn
```

---

## 相关文档

- `docs-zh/10-user/02-config/01-wparse.md`
- `docs-zh/10-user/02-config/02-sources.md`
- `docs-zh/10-user/02-config/04-sinks.md`
