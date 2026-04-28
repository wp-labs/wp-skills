---
name: connector
description: 编写和修改 WarpParse 的 source/sink 连接器配置，包括 connectors/source.d、connectors/sink.d、topology/sources、topology/sinks 的接线关系，依据现有示例和参考文档产出可落地配置。适用场景：让我加一个 file source、补一个 kafka sink、这个 sink_group 怎么写、source 和 sink 怎么接起来、帮我检查 connector 参数是否合理。
triggers:
  - 编写或修改 source 连接器
  - 编写或修改 sink 连接器
  - 编写或修改 topology/sources/wpsrc.toml
  - 编写或修改 topology/sinks/business.d 或 infra.d
  - 询问 source/sink 参数含义
  - 让已有 source 和 sink 接起来形成完整链路
  - 检查 connector 配置是否正确
dependencies:
  optional:
    - wparse
    - wproj
  docs:
    - docs.warpparse.ai
---

# WarpParse Connector 配置

这个 skill 专注于一件事：**把 source、sink、sink_group 和 connectors 配置正确接起来，并尽量落成可运行的工程配置**。

它主要处理 4 类问题：

1. 选择合适的 source / sink 类型
2. 编写 `connectors/source.d/*.toml` 与 `connectors/sink.d/*.toml`
3. 编写 `topology/sources/wpsrc.toml` 与 `topology/sinks/**/*.toml`
4. 基于示例检查参数、目录和接线关系是否一致

## 职责边界

### 本 skill 处理

- 解释 source / sink / sink_group / connector 的关系
- 选择合适的 source 类型，例如 `file`、`tcp`、`kafka`、`syslog`、`http`
- 选择合适的 sink 类型，例如 `file`、`blackhole`、`syslog`、`tcp`、`kafka`、`http`
- 编写连接器定义文件
- 编写 source 实例与 sink_group 配置
- 检查 `allow_override` 与实例参数是否匹配
- 用本地示例目录对照接线方式和目录结构
- 在不涉及规则语义的前提下，帮助用户把一条数据链路从 source 接到 sink

### 本 skill 不处理

- WPL 规则编写、修改、调试
- OML 富化模型编写、修改、调试
- 日志样本字段提取逻辑设计
- 生产部署策略、监控体系、整体工程选型

### 强制路由

当任务进入以下任一阶段时，**必须停止当前工作并切换到 `wpl-rule-check`**：

- 用户提供原始日志样本，要求解析字段
- 用户要求编写或修改 `parse.wpl` / `rule.wpl`
- 用户要求编写或修改 `.oml`
- 用户询问某条日志该怎么取字段、怎么写 WPL/OML

切换声明格式：

```
此任务已进入 WPL/OML 编写阶段，切换到 wpl-rule-check skill。
```

## 工作原则

1. 先看现有工程结构，再写配置，不猜目录。
2. 先找现有连接器定义和示例，再决定是否新增类型。
3. 参数说明以本地 example 为准，文档只作为辅助解释。
4. `connectors.params` 定义默认值，实例侧只覆盖 `allow_override` 允许的参数。
5. `source` 独立存在；`sink` 必须挂在 `sink_group` 下。
6. 能复用已有连接器定义时，不新造一套命名。

## 先检查什么

开始修改前，优先确认这些信息：

- 当前项目是否已有 `connectors/source.d` / `connectors/sink.d`
- 当前项目是否已有 `topology/sources` / `topology/sinks`
- 用户要新增的是 source、sink，还是两端完整链路
- 目标类型是什么：`file`、`tcp`、`kafka`、`syslog`、`http` 等
- 需要覆盖哪些参数，是否已经在 `allow_override` 中声明
- 是否已有可复用的连接器 id

## 标准工作流

### 1. 判定修改层级

先判断用户需要改哪一层：

- 只改默认参数：修改 `connectors/source.d/*.toml` 或 `connectors/sink.d/*.toml`
- 只改具体实例：修改 `topology/sources/wpsrc.toml` 或 `topology/sinks/**/*.toml`
- 新增完整链路：同时补 connector 定义和 topology 配置

### 2. 编写 source

source 一般分两部分：

1. 连接器定义
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

### 3. 编写 sink

sink 也分两部分：

1. 连接器定义
2. sink_group 中的 sink 实例

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

### 4. 做链路核对

如果用户是在做完整链路，而不是单独一个 connector，结束前要核对：

- `conf/wparse.toml` 是否正确指向 `models`、`topology/sources`、`topology/sinks`
- source 是否真的能产出数据
- sink_group 是否能匹配到目标日志
- sink connector id 是否拼写一致
- 基础设施 sink 是否存在：`default`、`error`、`miss`、`monitor`、`residue`

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

结束前至少要给出以下结果中的一种：

1. 一组完整可落地的 connector + topology 配置
2. 对现有 source / sink 配置的精确修改
3. 明确指出当前配置哪里没有接上

如果做了配置修改，还应说明：

- 改了哪些文件
- source 和 sink 是怎么接起来的
- 哪些参数来自默认定义，哪些参数在实例侧覆盖

## 输出要求

优先输出：

1. 变更后的配置文件路径
2. 每个文件的作用
3. 为什么这样接线
4. 如果未验证，明确说明缺少哪一步验证条件

## 示例与参考

优先参考本地材料：

- `references/connector-introduce.md`：source / sink / sink_group 总览、常用参数整理
- `examples/file_to_file/`：最小 file source -> file sink 示例

示例目录中的关键文件：

- `examples/file_to_file/connectors/source.d/file-default.toml`
- `examples/file_to_file/connectors/sink.d/file-json.toml`
- `examples/file_to_file/topology/sources/wpsrc.toml`
- `examples/file_to_file/topology/sinks/business.d/example.toml`
- `examples/file_to_file/topology/sinks/defaults.toml`
- `examples/file_to_file/conf/wparse.toml`

## 不要做的事

- 不要把 sink 写成和 source 一样直接挂在 topology 根下
- 不要在实例里覆盖未出现在 `allow_override` 的参数
- 不要只写 connector 定义，不补实例接线就声称完成
- 不要只写 sink，不补 `sink_group`
- 不要把文档中的历史字段当成最终事实，优先以 example 为准
