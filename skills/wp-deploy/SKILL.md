---
name: wp-deploy
description: 提供ETL引擎 wparse 相关组件的部署、卸载、配置指导。覆盖输入、输出、监控、发送测试、 以及联调与部署接线。适用场景：帮我搭一套 wparse 工程配置、添加一个输入和输出、对wparse引擎进行压测、接入wparse监控看指标和丢失数据、补 docker compose 或部署说明。
triggers:
  - 编写或修改 source 连接器
  - 编写或修改 sink 连接器
  - 编写或修改 topology/sources/wpsrc.toml
  - 编写或修改 topology/sinks/business.d 或 infra.d
  - 编写或修改 conf/wparse.toml
  - 编写或修改 conf/wpgen.toml
  - 编写或修改 wp-monitor/config/app.toml
  - 让已有 source 和 sink 接起来形成完整链路
  - 询问 wpgen 或 wp-monitor 怎么配置
  - 询问 WarpParse 怎么部署或联调
  - 卸载 wparse 相关组件
dependencies:
  optional:
    - wparse
    - wproj
    - wpgen
    - wp-monitor
  docs:
    - docs.warpparse.ai
---

# wparse 介绍
WarpParse 是一个高性能的 ELT 引擎，专注于日志数据的解析、处理和转发。它的核心组件包括：
- wparse：ELT 引擎本身
- wpgen：用于生成测试数据的工具
- wproj: 用来管理和验证项目配置的工具
- wpl-check：用于检查 WPL 规则和 OML 模型的工具
- wp-monitor：监控工具，用于监控 wparse 的运行状态和指标。

**概念介绍**
- connector：连接器，定义输入输出的类型和参数模板，位于 `connectors/source.d` 和 `connectors/sink.d`，source和sink都是连接器的具体实例。
- source/sink：数据输入输出实例，挂在 `topology/sources` 和 `topology/sinks` 下，引用 connector 定义并覆盖参数形成可用的输入输出。
- sink_group：sink的组合，表示这批sink接收同一批业务数据。
- wpl：WarpParse的规则语言，定义日志解析和字段提取逻辑，位于 `models/wpl`。
- oml：WarpParse的富化模型定义语言，定义基于解析结果的衍生字段和指标，位于 `models/oml`。
- 知识库：富化可以从外部系统查询数据的配置，知识库定义位于 `models/knowledge/`。

# WarpParse 部署配置指导

它主要处理 5 类问题：

1. 下载wparse的各类工具
2. 选择合适的 source / sink 类型并编写 connector 定义和实例
3. 编写 wparse 知识库配置。
4. 为链路补 `wpgen` 回放或压测配置
5. 为链路补 `wp-monitor` 与 `victoria-metrics` / `victoria-logs` 观测配置
6. 基于本地 examples 输出可执行的部署和启动方式

## 职责边界

### 本 skill 处理

- 解释 `connectors`、`sources`、`sink_group`、`infra` 的关系
- 选择合适的 source / sink 类型，例如 `file`、`tcp`、`kafka`、`syslog`、`http`
- 编写 `connectors/source.d/*.toml` 与 `connectors/sink.d/*.toml`
- 编写 `topology/sources/wpsrc.toml` 与 `topology/sinks/**/*.toml`
- 编写或检查 `conf/wparse.toml`
- 为 source / sink 链路补充 `wpgen` 配置
- 为链路补充 `wp-monitor`、`victoria-metrics`、`victoria-logs` 的接线方式
- 输出 `docker compose` 或最小部署步骤
- 检查 `allow_override`、目录结构、端口、依赖和接线关系是否一致

### 本 skill 不处理

- WPL 规则编写、修改、调试
- OML 富化模型编写、修改、调试
- 日志样本字段提取逻辑设计
- 纯业务字段语义判断

### 强制路由

当任务进入以下任一阶段时，**必须停止当前工作并切换到 `wpl-rule-check`skill中**：

- 用户提供原始日志样本，要求解析字段
- 用户要求编写或修改 `parse.wpl` / `rule.wpl`
- 用户要求编写或修改 `.oml`
- 用户询问某条日志该怎么取字段、怎么写 WPL/OML

切换声明格式：

```text
此任务已进入 WPL/OML 编写阶段，切换到 wpl-rule-check skill。
```


## 先检查什么

开始修改前，优先确认这些信息：

- 当前项目是否已有 `connectors/source.d` / `connectors/sink.d`
- 当前项目是否已有 `topology/sources` / `topology/sinks`
- 当前项目是否已有 `conf/wparse.toml` 与 `conf/wpgen.toml`
- 是否已经存在 `wp-monitor/config/app.toml` 或等价观测配置
- 用户要补的是单个 source/sink，还是一条完整链路
- 目标类型是什么：`file`、`tcp`、`kafka`、`syslog`、`http` 等
- 需要覆盖哪些参数，是否已经在 `allow_override` 中声明
- 是否需要本地联调、压测、观测或 docker compose

## 标准工作流

### 1. 判定修改层级

先判断用户需要改哪一层：

- 只改默认参数：修改 `connectors/source.d/*.toml` 或 `connectors/sink.d/*.toml`
- 只改实例：修改 `topology/sources/wpsrc.toml` 或 `topology/sinks/**/*.toml`
- 改工程入口：修改 `conf/wparse.toml`
- 补测试流量：修改 `conf/wpgen.toml`
- 补观测：修改 `topology/sinks/infra.d/monitor.toml`、`wp-monitor/config/app.toml` 或部署文件
- 新增完整链路：同时补 connector、topology、wpgen、monitor 和部署说明
- 使用wpgen进行链路验证或压测：修改 `conf/wpgen.toml`，并说明如何启动和验证

### 2. 编写 source

source 一般分两部分：

1. connector 定义
2. source 实例

模板：

```toml
[[connectors]]
id = "file_src"
type = "file"
allow_override = ["base", "file", "encode", "instances"]

[connectors.params]
base = "data/in_dat"
file = "gen.dat"
encode = "text"
```

```toml
[[sources]]
key = "file_1"
enable = true
connect = "file_src"
tags = ["type:file"]

[sources.params]
base = "models/wpl/nginx"
file = "sample.dat"
```

检查点：

- `connect` 必须引用已存在的 source connector id
- `sources.params` 只能覆盖 `allow_override` 里的键
- `key` 要唯一

### 3. 编写 sink 与 sink_group

sink 分两部分：

1. connector 定义
2. `sink_group` 中的 sink 实例

模板：

```toml
[[connectors]]
id = "file_json_sink"
type = "file"
allow_override = ["base", "file", "sync"]

[connectors.params]
fmt = "json"
base = "./data/out_dat"
file = "default.json"
```

```toml
version = "2.0"

[sink_group]
name = "example_sink_group"
oml = ["*"]

[[sink_group.sinks]]
connect = "file_json_sink"

[sink_group.sinks.params]
base = "./data/out_dat"
file = "example.json"
```

检查点：

- `sink` 不能脱离 `sink_group` 单独存在
- `connect` 必须引用已存在的 sink connector id
- 实例覆盖参数必须在 `allow_override` 中
- `rule` 和 `oml` 至少有一个，且不能同时存在

### 4. 编写 wparse 工程入口

`conf/wparse.toml` 至少要检查：

- `models.wpl` / `models.oml`
- `topology.sources` / `topology.sinks`
- `performance` 与 `stat`
- `rescue.path`
- `log_conf`

如果用户做的是完整链路，结束前要核对：

- `conf/wparse.toml` 是否正确指向模型和拓扑目录
- source 是否真的能产出数据
- sink_group 是否能匹配到目标日志
- sink connector id 是否拼写一致
- 基础设施 sink 是否存在：`default`、`error`、`miss`、`monitor`、`residue`

### 5. 接入 wpgen

当用户需要进行链路验证或者压测时，请使用`wpgen`。

使用要点：

- `wpgen` 配置文件通常位于 `conf/wpgen.toml`
- `[output].connect` 引用 `connectors/sink.d` 中的 sink connector id
- `[output].params` 只能覆盖 `allow_override` 允许的键
- 常见链路是 `wpgen -> tcp_sink -> warp-parse tcp source`

如果任务涉及 `wpgen`，优先参考：`references/wpgen.md`

### 6. 接入 wp-monitor

当用户需要判断链路是否真的工作正常，而不是只看配置语法时，优先考虑 `wp-monitor`：

- 观察 source 输入量、解析成功率、MISS、错误和 sink 输出量
- 排查 monitor / miss / downstream 是否异常
- 给联调环境补齐指标与 miss 查询入口

使用要点：

- `wp-monitor` 依赖 `victoria-metrics` 存指标
- 如果要查看 miss 或业务日志，通常还需要 `victoria-logs`
- `wparse` 侧通常需要在 `infra.d/monitor.toml` 中接 `victoriametrics_sink`
- `wp-monitor/config/app.toml` 至少要提供 `vm_base_url` 和 `vlog_base_url`

如果任务涉及观测或监控联调，优先参考：`references/wp-monitor.md`

### 7. 给出部署方式

当用户要求部署或联调落地时，至少要交付下面其中一种：

- `docker compose` 启动方案
- 单机目录布局和启动命令
- 链路依赖说明：谁先启动、谁连谁、端口和落点是什么

需要明确说明：

- `warp-parse` 如何挂载 `wparse/` 目录
- `wpgen` 往哪个 sink connector 发流量
- `wp-monitor` 读哪个 `victoria-metrics` / `victoria-logs` 地址
- 哪些组件是必需，哪些只是联调增强件

## 常见类型选择

### 常见 source

- `file`：离线样本、本地文件、单机导入
- `tcp`：自定义 TCP 推送链路
- `kafka`：从 Kafka 消费数据
- `syslog`：接收标准 Syslog 数据
- `http`：通过 HTTP 接收入站数据

### 常见 sink

- `file`：本地落盘，最适合联调和验收
- `blackhole`：丢弃输出，用于测试或占位
- `tcp`：转发到下游 TCP 服务
- `syslog`：发往 Syslog 服务端
- `kafka`：写入 Kafka 主题
- `http`：推送到 Webhook / API
- `mysql` / `postgres` / `clickhouse` / `doris`：写数据库
- `elasticsearch` / `victorialogs`：写检索或日志平台

## 完成标准

编写后，必须使用wproj进行验证。

结束前至少要给出以下结果中的一种：

1. 一组完整可落地的部署配置，覆盖 connector + topology + `wparse.toml`
2. 对现有 source / sink / `wpgen` / `wp-monitor` 配置的精确修改
3. 明确指出当前链路哪里没有接上，缺少什么依赖

如果做了配置修改，还应说明：

- 改了哪些文件
- source、sink、`wpgen`、`wp-monitor` 是怎么接起来的
- 哪些参数来自默认定义，哪些参数在实例侧覆盖
- 业务数据、监控数据、miss 数据分别落到哪里
- 如果未验证，缺少哪一步环境条件

## 输出要求

优先输出：

1. 变更后的配置文件路径
2. 每个文件的作用
3. 为什么这样接线和部署
4. 启动顺序、依赖关系和验证方式


## 示例与参考

优先参考本地材料：

- `references/cli-introduce.md`：wparse、wpgen、wproj 的 CLI 使用方法和参数说明，包含了安装和卸载
- `references/knowdb-introduce.md`：知识库配置说明和示例
- `references/connector-introduce.md`：source / sink / sink_group 总览、常用参数整理
- `references/wpgen.md`：`wpgen` 配置、输出接线和压测速度模型
- `references/wp-monitor.md`：`wp-monitor` 配置、监控 sink 接入和观测依赖
- `references/warp-console-observability.md`：从 `warp-console` 提炼出的日志解析 + 观测 + 部署主线
- `examples/file_to_file/`：最小 file source -> file sink -> `wparse` 示例
- `examples/warp-observability/`：带 `wpgen`、`wp-monitor` 和观测依赖的部署示例

示例目录中的关键文件：

- `examples/file_to_file/conf/wparse.toml`
- `examples/file_to_file/connectors/source.d/file-default.toml`
- `examples/file_to_file/connectors/sink.d/file-json.toml`
- `examples/file_to_file/topology/sources/wpsrc.toml`
- `examples/file_to_file/topology/sinks/business.d/example.toml`
- `examples/warp-observability/docker-compose.yml`
- `examples/warp-observability/wparse/conf/wparse.toml`
- `examples/warp-observability/wparse/conf/wpgen.toml`
- `examples/warp-observability/wparse/topology/sinks/infra.d/monitor.toml`
- `examples/warp-observability/wp-monitor/config/app.toml`

## 其他要求
- 当卸载wparse时，需要卸载wparse的整套组件（二进制）。
- 如果需要发送数据来验证测试结果，需要给出wpgen命令。
- 当提供配置时，无论是否使用知识库，都要提供一个默认知识库配置。