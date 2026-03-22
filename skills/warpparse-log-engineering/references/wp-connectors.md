# WP 连接器配置指南

本文档介绍 WarpParse 支持的数据源（Source）和输出端（Sink）连接器。

---

## Source 连接器 - 数据输入

### 内置 Source

| 类型 | 说明 | 典型场景 |
|------|------|----------|
| `file` | 文件输入 | 本地日志文件、批量处理 |
| `syslog` | Syslog 协议 | 网络设备日志、系统日志 |
| `tcp` | TCP 流 | 实时日志流、自定义协议 |

### 扩展 Source

| 类型 | 说明 | 典型场景 |
|------|------|----------|
| `kafka` | Apache Kafka | 消息队列、流处理 |

---

### file - 文件源

```toml
# connectors/source.d/file.toml
[[connectors]]
id = "file_src"
type = "file"
allow_override = ["base", "file", "encode"]

[connectors.params]
base = "./data/in_dat"
file = "input.log"
encode = "text"
```

**参数说明：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `base` | string | 文件目录 |
| `file` | string | 文件名 |
| `encode` | string | 编码：text/binary |

---

### syslog - Syslog 源

```toml
# connectors/source.d/syslog.toml
[[connectors]]
id = "syslog_udp_src"
type = "syslog"
allow_override = ["port", "header_mode", "prefer_newline"]

[connectors.params]
port = 1514
header_mode = "parse"
prefer_newline = true
```

**参数说明：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `port` | int | 监听端口 |
| `header_mode` | string | 头部解析模式 |
| `prefer_newline` | bool | 优先按换行分割 |

---

### tcp - TCP 源

```toml
# connectors/source.d/tcp.toml
[[connectors]]
id = "tcp_src"
type = "tcp"
allow_override = ["port", "framing", "prefer_newline"]

[connectors.params]
port = 19000
framing = "auto"
prefer_newline = true
```

**参数说明：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `port` | int | 监听端口 |
| `framing` | string | 分帧方式：auto/line/length |
| `prefer_newline` | bool | 优先按换行分割 |

---

### kafka - Kafka 源

```toml
# connectors/source.d/kafka.toml
[[connectors]]
id = "kafka_src"
type = "kafka"
allow_override = ["topic", "group_id", "config"]

[connectors.params]
brokers = "localhost:9092"
topic = ["access_log"]
group_id = "wparse_default_group"
```

**参数说明：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `brokers` | string | Kafka 集群地址 |
| `topic` | array | 消费主题列表 |
| `group_id` | string | 消费者组 ID |
| `config` | array | 额外配置（key=value 形式） |

**安全配置示例：**

```toml
[[sources]]
key = "kafka_secure"
connect = "kafka_src"

[sources.params]
topic = ["secure_events"]
config = [
    "security_protocol=SASL_SSL",
    "sasl_mechanisms=PLAIN",
    "sasl_username=user",
    "sasl_password=pass"
]
```

---

## Sink 连接器 - 数据输出

### 内置 Sink

| 类型 | 说明 | 典型场景 |
|------|------|----------|
| `file` | 文件输出 | 本地存储、归档 |
| `syslog` | Syslog 输出 | 日志转发 |
| `tcp` | TCP 输出 | 实时推送 |

### 扩展 Sink

| 类型 | 说明 | 典型场景 |
|------|------|----------|
| `kafka` | Kafka 输出 | 消息队列、下游消费 |
| `prometheus` | Prometheus 指标 | 监控 |
| `mysql` | MySQL 输出 | 数据库存储 |
| `doris` | Doris 输出 | 数据仓库 |

---

### file - 文件输出

```toml
# connectors/sink.d/file.toml
[[connectors]]
id = "file_json_sink"
type = "file"
allow_override = ["base", "file", "fmt"]

[connectors.params]
base = "./out"
file = "output.json"
fmt = "json"
```

**参数说明：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `base` | string | 输出目录 |
| `file` | string | 文件名 |
| `fmt` | string | 格式：json/kv/text |

---

### kafka - Kafka 输出

```toml
# connectors/sink.d/kafka.toml
[[connectors]]
id = "kafka_sink"
type = "kafka"
allow_override = ["topic", "config", "num_partitions", "replication"]

[connectors.params]
brokers = "localhost:9092"
topic = "wparse_output"
num_partitions = 1
replication = 1
```

**参数说明：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `brokers` | string | Kafka 集群地址 |
| `topic` | string | 目标主题 |
| `num_partitions` | int | 分区数（自动创建时） |
| `replication` | int | 副本数（自动创建时） |
| `config` | array | 生产者配置 |

---

### prometheus - Prometheus 指标

```toml
# connectors/sink.d/prometheus.toml
[[connectors]]
id = "prometheus_sink"
type = "prometheus"
allow_override = ["port", "path"]

[connectors.params]
port = 9100
path = "/metrics"
```

---

### mysql - MySQL 输出

```toml
# connectors/sink.d/mysql.toml
[[connectors]]
id = "mysql_sink"
type = "mysql"
allow_override = ["table", "batch_size"]

[connectors.params]
url = "mysql://user:pass@localhost:3306/db"
table = "parsed_logs"
batch_size = 1000
```

---

## 使用示例

### 完整 Source 配置

```toml
# topology/sources/wpsrc.toml

# 文件源
[[sources]]
key = "nginx_access"
connect = "file_src"
enable = true
tags = ["type:nginx", "env:prod"]
[sources.params]
base = "/var/log/nginx"
file = "access.log"

# Kafka 源
[[sources]]
key = "app_logs"
connect = "kafka_src"
enable = true
tags = ["type:app", "source:kafka"]
[sources.params]
brokers = "kafka:9092"
topic = ["app-logs"]
group_id = "wparse-prod"
```

### 完整 Sink 配置

```toml
# topology/sinks/business.d/access.toml
version = "2.0"

[sink_group]
name = "/sink/nginx"
oml = ["/oml/nginx*"]

[[sink_group.sinks]]
name = "json_file"
connect = "file_json_sink"
[sink_group.sinks.params]
base = "/data/parsed"
file = "nginx.json"

[[sink_group.sinks]]
name = "kafka_out"
connect = "kafka_sink"
[sink_group.sinks.params]
brokers = "kafka:9092"
topic = "parsed-nginx"
```

---

## 排障指南

### 连接器未找到

```bash
# 检查连接器目录
ls connectors/source.d/
ls connectors/sink.d/

# 查看解析结果
wproj sources list
wproj sinks list
```

### 覆写参数报错

- 检查 `allow_override` 白名单
- 确保参数名正确
- 查看 `wproj check` 输出

### 连接问题

```bash
# 检查配置解析
wproj sources route
wproj sinks validate

# 查看日志
tail -f data/logs/wparse.log
```

---

## 相关文档

- `docs-zh/10-user/05-connectors/01-sources/`
- `docs-zh/10-user/05-connectors/02-sinks/`