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
wpl     = "./models/wpl"     # WPL 规则目录
oml     = "./models/oml"     # OML 模型目录

[topology]
sources = "./topology/sources"   # 数据源配置目录
sinks   = "./topology/sinks"     # 输出路由目录

[performance]
rate_limit_rps = 10000        # 限速（records/second）
parse_workers  = 2            # 解析并发 worker 数

[rescue]
path = "./data/rescue"        # 救援数据目录

[log_conf]
output = "File"               # Console|File|Both
level  = "warn,ctrl=info"     # 日志级别

[log_conf.file]
path = "./data/logs"          # 日志文件目录

[stat]
# 统计配置
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
| `log_conf.level` | 日志级别 | warn,ctrl=info |

### 容错模式

| 模式 | 说明 |
|------|------|
| `debug` | 调试模式，详细输出 |
| `normal` | 正常模式，平衡性能和容错 |
| `strict` | 严格模式，错误即停止 |

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

### Syslog 源示例

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

### 基础组示例

```toml
# infra.d/intercept.toml
version = "2.0"

[sink_group]
name = "intercept"

[[sink_group.sinks]]
name = "intercept"
connect = "file_kv_sink"
params = { base = "./out", file = "intercept.dat" }
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

---

## wpgen.toml - 数据生成配置

```toml
[generator]
count = 10000      # 总生成条数
speed = 1000       # 生成速度（行/秒），0 表示无限制
parallel = 4       # 并行 worker 数

[output]
base = "./data/in_dat"
file = "gen.dat"
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