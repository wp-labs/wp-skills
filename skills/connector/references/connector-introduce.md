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
- instances: 表示TCP连接的实例数，默认为1，最大为16。

#### kafka Source

### SinkGroup与sink配置
sink_group格式与sink格式
```toml
[sink_group]
name = "group名称"
oml = ["匹配规则"]  # 表示这个sink_group会匹配哪些日志，匹配规则是一个OML表达式，日志满足这个OML表达式就会被路由到这个sink_group中
rule = ["规则名称"]  # 表示这个sink_group会匹配哪些日志，匹配规则是一个WPL规则名称，日志满足这个WPL规则就会被路由到这个sink_group中.rule和oml至少要有一个，rule和oml不可以同时存在。

# sink连接器实例
[[sink_group.sinks]]
name = "es_stream_load"
connect = "连接器id"    # 在connectors/sink.d/对应的连接器定义的id
tags = ["type:es"]    # 附加的tag
[sink_group.sinks.params]   # 覆盖连接器定义中的参数
```
