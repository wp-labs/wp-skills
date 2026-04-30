# 连接器介绍
连接器是Wparse引擎接收数据，和输出数据的组件。接收数据的连接器叫做source，输出数据的连接器叫做sink。

每个连接器都分为两部分：
- 连接器定义：定义连接器的参数、连接器的类型、连接器的默认值、以及可以被连接器实例覆盖的参数。
- 连接器实例：连接器实例是连接器定义的一个具体实例，包含了连接器定义中定义的参数的具体值。

### 目录结构
wparse整体项目目录结构：
```sh
.
├── connectors/  # 连接器定义
│   ├── source.d/  # source连接器定义
│   └── sink.d/    # sink连接器定义
├── conf/         # wparse配置文件
├── models/       # wparse日志解析规则
└── topology/     # 连接器实例
    ├── sinks     # sink连接器
    │   ├── business.d/        # 业务连接器
    │   ├── defaults.toml      # sink连接器的全局默认值
    │   └── infra.d/           # 基础设施连接器实例
    └── sources/               # source连接器实例
        └── wpsrc.toml         # wparse引擎的source连接器实例
```

其中，`connectors`目录可以放在当前项目中，也可以放在当前项目的上级目录中（最多32层）。



### sink_group与sink
sink_group是一个逻辑概念，表示一类日志应该被路由到哪个sink连接器实例中。每个sink_group可以包含多个sink连接器实例，日志会被路由到sink_group中所有的sink连接器实例中。sink连接器无法脱离sink_group存在。

### 基础设施
sink连接器实例分为两类：业务连接器实例和基础设施连接器实例。业务连接器实例是用户自定义的连接器实例。
基础设施连接器包括：
```sh
.
├── default.toml    # 如果日志被规则解析了，但是没有发送到任意sink实例中，日志会被发送到这个sink实例中
├── error.toml      # 错误日志的sink实例
├── miss.toml       # 未匹配日志的sink实例
├── monitor.toml    # 监控数据的sink实例
└── residue.toml    # 急救的sink示例，当日志被解析了，但是在发送到sink实例的过程中发生了错误，日志会被发送到这个sink实例中
```

## 连接器
### 通用连接器配置
```toml
[[connectors]]
id = "连接器id"
type = "连接器类型"
allow_override = [] # 允许覆盖的参数列表

[connectors.params] # 连接器定义中的默认参数值
```

### Source通用配置
```toml
[[sources]]
enable = true           # 是否启用这个source连接器实例，默认为true。
key = "tcp_1"           # source连接器实例的唯一标识
connect = "tcp_src"     # 在connectors/source.d/对应的连接器定义的id
tags = ["type:tcp"]    # 附加的tag
```
- enable: 是否启用这个source连接器实例，默认为true。
- tags: 连接器实例的标签，可以在规则中使用这些标签来匹配日志。

#### File Source
连接器参数：
- base: 表示目录前缀。 
- file: 表示文件路径，可以包含通配符。
- encode: 内容编码，默认为text。可选值有：`text`、`base64`、`hex`。

#### TCP Source
- addr: 表示TCP监听地址。
- port: 表示TCP监听端口。
- framing: 表示TCP数据的分割方式，默认为auto。可选值有：`line`、`len`、`auto`。
    - `line`：按换行符分帧；行末的 CR/空格/Tab 会被去除
    - `len`：长度前缀（RFC 6587 octet-counting）：`<len><SP><payload>`
    - `auto`（默认）：自动选择；默认优先 `len`，当 `prefer_newline=true` 时优先按行
- tcp_recv_bytes: 表示TCP接收缓冲区大小，默认为4096字节。
- prefer_newline: 当 framing=auto 时，是否优先按行分帧。
- instances: 表示处理TCP实例的并行度，默认为1，最大为16。

#### kafka Source
- brokers: 表示Kafka集群地址，格式为 `host:port`，多个broker可用逗号分隔。
- topic: 表示要消费的主题列表，如果kafka中不存在则会自动创建。
- group_id: 表示消费者组ID，默认为 `wparse_default_group`。
- config: 表示额外的Kafka客户端配置。是一个字符串数组，每个配置的格式为 `key=value` ，常用于偏移量策略、TLS/SASL认证等配置。
- instances: 表示处理Kafka实例的并行度，默认为1，最大为16。


#### Syslog Source
- addr: 表示Syslog监听地址。
- port: 表示Syslog监听端口。
- protocol: 表示传输协议。可选值有：`udp`、`tcp`。
- header_mode: 表示Syslog头部处理方式，默认为 `parse`。可选值有：`strip`、`parse`、`keep`。
    - `strip`：仅剥离头部，不注入标签
    - `parse`：解析头部并注入标签，同时剥离头部
    - `keep`：保留头部，原样透传
- fast_strip: 表示是否启用快速剥离模式，主要用于性能优化。
- tcp_recv_bytes: 表示TCP模式下的接收缓冲区大小。
- udp_recv_buffer: 表示UDP模式下的接收缓冲区大小。
- instances: 表示处理Syslog实例的并行度，默认为1，最大为16。

#### HTTP Source
连接器参数：
- port: 表示HTTP监听端口。
- path: 表示HTTP监听路径。多个HTTP Source可以共用同一个端口，但路径不能重复。

请求参数：
- fmt: 表示请求体格式，可通过请求参数 `fmt` 或请求头 `Content-Type` 指定。可选值有：`json`、`ndjson`。
- compression: 表示请求体压缩方式，可通过请求参数 `compression` 或请求头 `Content-Encoding` 指定，常见值为 `gzip` 或不压缩。


### SinkGroup与sink配置
sink_group格式与sink格式
```toml
[sink_group]
name = "group名称"
oml = ["/oml/normal/*"]
rule = ["/Nginx/*"]

# sink连接器实例
[[sink_group.sinks]]
name = "es_stream_load"
connect = "连接器id"    # 在connectors/sink.d/对应的连接器定义的id
tags = ["type:es"]    # 附加的tag
[sink_group.sinks.params]   # 覆盖连接器定义中的参数
```
sink_group参数：
- name: sink_group名称。
- oml: sink_group会匹配oml name(富化后的数据)。
- rule: sink_group会匹配wpl 的 `package名/rule名`，匹配规则支持`*`。`rule` 和 `oml` 至少要有一个，且不能同时存在。
- batch_timeout_ms: 表示批量发送的超时时间，单位为毫秒。当达到这个时间时，当前批次的数据会被立即发送，无论批次大小是否已满。默认为1000毫秒。
- parallel: 表示这个sink_group中每个sink连接器实例的并行度，默认为1，最大为16。如果有n个sink连接器实例，并行度为p，那么这个sink_group的总并行度就是n*p。

sink通用参数：
- name: sink实例名称，在同一个sink_group中应保持唯一。
- connect: 在 `connectors/sink.d/` 中引用的连接器定义id。
- tags: sink实例附加的tag。
- params: 用于覆盖连接器定义中允许覆盖的参数.
- batch_size: 表示批量处理大小（缓冲区大小）。

#### Blackhole Sink
- 无参数。表示直接丢弃数据，常用于测试或占位。

#### File Sink
连接器参数：
- fmt: 表示输出格式，常见值有：`json`、`csv`、`kv`、`show`、`raw`、`proto-text`。
- base: 表示输出目录。
- file: 表示输出文件名。

#### Syslog Sink
- addr: 表示Syslog服务端地址。
- port: 表示Syslog服务端端口。
- protocol: 表示传输协议。可选值有：`udp`、`tcp`。

#### TCP Sink
- addr: 表示TCP服务端地址。
- port: 表示TCP服务端端口。
- framing: 表示发送数据的分帧方式。可选值有：`line`、`len`。
    - `line`：在每条消息末尾追加换行符
    - `len`：按长度前缀发送，格式为 `<len><SP><payload>`
- max_backoff: 表示是否启用基于内核发送队列的退避控制。

#### Kafka Sink
- brokers: 表示Kafka集群地址，格式为 `host:port`，多个broker可用逗号分隔。
- topic: 表示目标主题，不存在则创建。
- num_partitions: 表示自动创建主题时的分区数，默认为 `1`。
- replication: 表示自动创建主题时的副本数，默认为 `1`。
- config: 表示额外的Kafka生产者配置。是一个字符串数组，每个配置的格式为 `key=value`。

#### Prometheus Sink
- endpoint: 表示Prometheus指标暴露地址，格式为 `host:port`。
- source_key_format: 表示从source key中提取标签的正则表达式。
- sink_key_format: 表示从sink key中提取标签的正则表达式。

#### MySQL Sink
- endpoint: 表示MySQL地址，格式为 `host:port`。
- username: 表示MySQL用户名。
- password: 表示MySQL密码。
- database: 表示目标数据库名。
- table: 表示目标表名。
- columns: 表示写入字段列表。
- batch: 表示批量写入条数。
- batch_size: 表示批量处理大小。

#### Doris Sink
- endpoint: 表示Doris写入地址，示例中使用BE的HTTP端口。
- user: 表示Doris用户名。
- password: 表示Doris密码。
- database: 表示目标数据库名。
- table: 表示目标表名。
- timeout_secs: 表示单次请求超时时间。
- max_retries: 表示写入失败后的最大重试次数。
- batch_size: 表示批量写入大小。
- headers: 是一个对象，表示额外的Stream Load请求头配置。

#### Postgres Sink
- endpoint: 表示Postgres地址，格式为 `host:port`。
- username: 表示Postgres用户名。
- password: 表示Postgres密码。
- database: 表示目标数据库名。
- table: 表示目标表名。
- columns: 表示写入字段列表。
- batch: 表示批量写入条数。
- batch_size: 表示批量处理大小。

#### VictoriaLogs Sink
- endpoint: 表示VictoriaLogs服务地址。
- insert_path: 表示写入路径。
- flush_interval_secs: 表示刷新间隔，单位为秒。
- create_time_field: 表示用于提取事件时间的字段名。
- batch_size: 表示批量写入大小。

#### VictoriaMetrics Sink
- insert_url: 表示VictoriaMetrics写入地址。
- flush_interval_secs: 表示刷新间隔，单位为秒。

#### Elasticsearch Sink
- protocol: 表示连接协议。可选值有：`http`、`https`。
- host: 表示Elasticsearch主机地址。
- port: 表示Elasticsearch端口。
- username: 表示Elasticsearch用户名。
- password: 表示Elasticsearch密码。
- index: 表示目标索引名。
- timeout_secs: 表示单次请求超时时间。
- max_retries: 表示写入失败后的最大重试次数。
- batch_size: 表示批量写入大小。

#### ClickHouse Sink
- endpoint: 表示ClickHouse地址，格式为 `http://host:port` 或 `https://host:port`。
- username: 表示ClickHouse用户名。
- password: 表示ClickHouse密码。
- database: 表示目标数据库名。
- table: 表示目标表名。
- timeout_secs: 表示单次请求超时时间。
- max_retries: 表示写入失败后的最大重试次数。
- batch_size: 表示批量写入大小。

#### HTTP Sink
- endpoint: 表示HTTP写入地址。
- username: 表示HTTP Basic认证用户名。
- password: 表示HTTP Basic认证密码。
- fmt: 表示输出格式。可选值通常有：`json`、`ndjson`、`csv`、`kv`、`raw`、`proto-text`。
- compression: 表示请求体压缩方式。可选值有：`none`、`gzip`。
- timeout_secs: 表示单次请求超时时间。
- max_retries: 表示请求失败后的最大重试次数。
- batch_size: 表示批量发送大小。
- headers: 表示自定义HTTP请求头，是一个对象。