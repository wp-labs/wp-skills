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
  - 卸载 wp-monitor / victoria-metrics / victoria-logs 观测栈
dependencies:
  optional:
    - wparse
    - wproj
    - wpgen
    - wpl-check
    - wp-monitor
  docs:
    - docs.warpparse.ai
---

# wparse 介绍
WarpParse 是一个高性能的 ELT 引擎，专注于日志数据的解析、处理和转发。它的核心组件包括：
- wparse：ELT 引擎本身
- wpgen：用于生成测试数据的工具
- wproj: 用来初始化、同步、生成和验证项目配置的工具
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

它主要处理 6 类问题：

1. 下载wparse的各类工具
2. 使用 `wproj` 初始化、同步或再生成工程配置基线
3. 选择合适的 source / sink 类型，并基于 `wproj` 生成的工程结构做必要的局部调整
4. 检查或补充 wparse 知识库配置
5. 为链路补 `wpgen` 回放或压测配置
6. 为链路补 `wp-monitor` 与 `victoria-metrics` / `victoria-logs` 观测配置
7. 基于 `wproj` 生成工程输出可执行的部署和启动方式，可参考本地 examples 解释接线

## 职责边界

### 本 skill 处理

- 解释 `connectors`、`sources`、`sink_group`、`infra` 的关系
- 选择合适的 source / sink 类型，例如 `file`、`tcp`、`kafka`、`syslog`、`http`
- 通过 `wproj init` 或 `wproj conf update` 生成或更新工程配置基线
- 基于 `wproj` 生成结果，检查或局部调整 `connectors/source.d/*.toml` 与 `connectors/sink.d/*.toml`
- 基于 `wproj` 生成结果，检查或局部调整 `topology/sources/wpsrc.toml` 与 `topology/sinks/**/*.toml`
- 检查 `conf/wparse.toml`
- 为 source / sink 链路补充 `wpgen` 配置
- 为链路补充 `wp-monitor`、`victoria-metrics`、`victoria-logs` 的接线方式
- 输出 `docker compose` 或最小部署步骤
- 检查 `allow_override`、目录结构、端口、依赖和接线关系是否一致
- 输出本次使用的 `wproj` 命令，说明如何用同一命令再生成或更新配置
- 当用户要求“给一个示例”时，在用户指定目录或临时演示目录中通过 `wproj` 创建可运行工程；仓库内 `examples/` 只作为只读参考，不作为运行目录交付
- 输出测试数据发送或回放方式时，必须使用 `wpgen` 配置和命令；不要生成自定义 Python / Node / Bash sender、`nc` 循环、`curl` 循环等替代方案
- 输出部署或联调方案时，必须默认部署 `wp-monitor` 观测栈，并给出 monitor 侧的健康、解析、miss、source/sink 检查项
- 最终总结必须包含“wp-monitor 闭环状态”：明确 `wp-monitor` 是已部署并看到数据，还是未部署导致观测闭环未完成；不能只输出业务文件落点后就结束
- 交付部署或示例工程时，必须把 `wpl-check` 作为部署要求准备好；它由 `wp-deploy` 控制安装、镜像配置和卸载生命周期，并供 `wpl-rule-check` 消费
- 卸载 `wparse` 相关组件时，必须同时处理本地二进制、`wpl-check` 验证物料和已部署的 `wp-monitor` 观测栈

### 本 skill 不处理

- WPL 规则编写、修改、调试
- OML 富化模型编写、修改、调试
- 日志样本字段提取逻辑设计
- 纯业务字段语义判断
- 在新工程中手工拼装 `conf/`、`connectors/`、`topology/`、`models/knowledge/` 等核心配置目录来替代 `wproj`
- 把已安装 skill 目录下的 `examples/` 当成用户项目目录运行，或要求用户直接修改 skill 自带示例文件
- 编写临时 sender 脚本来绕过 `wpgen` 发送测试数据
- 只给出能启动 `wparse` 的部署方案，却不部署 `wp-monitor` 观测栈
- 在没有部署或验证 `wp-monitor` 的情况下声称完整部署链路已经完成

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

- `wproj` 是否已安装：`wproj --version`
- 当前任务是生成新工程、同步远端配置，还是修改已有工程
- 如果是新工程，应该使用哪条 `wproj init` 命令
- 如果是同步远端配置，应该使用哪条 `wproj conf update` 命令
- 当前项目是否已有 `connectors/source.d` / `connectors/sink.d`
- 当前项目是否已有 `topology/sources` / `topology/sinks`
- 当前项目是否已有 `conf/wparse.toml` 与 `conf/wpgen.toml`
- 是否已经存在 `wp-monitor/config/app.toml` 或等价观测配置
- 用户要补的是单个 source/sink，还是一条完整链路
- 目标类型是什么：`file`、`tcp`、`kafka`、`syslog`、`http` 等
- 需要覆盖哪些参数，是否已经在 `allow_override` 中声明
- 是否需要本地联调、压测、观测或 docker compose

## 标准工作流

### 0. 先通过 wproj 建立工程配置基线

凡是“生成项目”“搭一套工程”“创建部署配置”“补完整链路”这类任务，必须先走 `wproj`，不得直接手工创建等价的核心项目配置文件。

本地初始化：

```bash
wproj init --work-root .
```

按模式初始化：

```bash
wproj init --work-root . --mode full
wproj init --work-root . --mode normal
wproj init --work-root . --mode model
wproj init --work-root . --mode conf
wproj init --work-root . --mode data
```

从远端项目源初始化：

```bash
wproj init --work-root . --repo <repo-url> --version <version>
```

生成或更新后立即检查：

```bash
wproj check --work-root . --what all --fail-fast
```

如果本地没有 `wproj`，先给出安装命令并停止生成配置；不要用手写文件绕过：

```bash
curl -sSf https://get.warpparse.ai/inst-x.sh | bash -s -- wparse beta
export PATH="$HOME/bin:$PATH"
wproj --version
```

交付时必须写明本次使用或要求用户执行的 `wproj` 命令。后续 source、sink、wpgen、monitor 的配置只能作为 `wproj` 生成基线上的局部调整，并且最后重新执行 `wproj check`。

### 1. 判定修改层级

先判断用户需要改哪一层：

- 只改默认参数：修改 `connectors/source.d/*.toml` 或 `connectors/sink.d/*.toml`
- 只改实例：修改 `topology/sources/wpsrc.toml` 或 `topology/sinks/**/*.toml`
- 改工程入口：修改 `conf/wparse.toml`
- 补测试流量：修改 `conf/wpgen.toml`
- 补观测：修改 `topology/sinks/infra.d/monitor.toml`、`wp-monitor/config/app.toml` 或部署文件
- 新增完整链路：同时补 connector、topology、wpgen、monitor 和部署说明
- 使用wpgen进行链路验证或压测：修改 `conf/wpgen.toml`，并说明如何启动和验证

如果是新工程或可由 `wproj init` / `wproj conf update` 再生成的配置，先输出并执行对应 `wproj` 命令，再做必要局部调整。

### 2. 检查和局部调整 source

source 一般分两部分：

1. connector 定义
2. source 实例

模板：

以下模板只用于审查或局部调整 `wproj` 生成结果，不用于绕过 `wproj` 手工生成新工程。

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

### 3. 检查和局部调整 sink 与 sink_group

sink 分两部分：

1. connector 定义
2. `sink_group` 中的 sink 实例

模板：

以下模板只用于审查或局部调整 `wproj` 生成结果，不用于绕过 `wproj` 手工生成新工程。

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

### 4. 检查 wparse 工程入口

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

当用户需要进行链路验证、样本回放、测试数据发送或者压测时，必须使用 `wpgen`。

使用要点：

- `wpgen` 配置文件通常位于 `conf/wpgen.toml`
- `[output].connect` 引用 `connectors/sink.d` 中的 sink connector id
- `[output].params` 只能覆盖 `allow_override` 允许的键
- 常见链路是 `wpgen -> tcp_sink -> warp-parse tcp source`
- `wproj init --mode full` 会生成 `conf/wpgen.toml`；若缺失，使用 `wpgen conf init --work-root "$(pwd)"` 生成
- 修改或生成后先检查配置：`wpgen conf check --work-root "$(pwd)"`
- 样本回放命令必须写成明确命令，例如：

```bash
wpgen sample --work-root "$(pwd)" -n 10000 -s 1000 --stat 3 -p
```

禁止项：

- 不要让 agent 生成 Python / Node / Bash sender 脚本
- 不要用 `nc`、`curl`、`while read` 循环等临时发送方式替代 `wpgen`
- 如果确实无法使用 `wpgen`，必须明确说明阻塞原因和缺少的配置或工具，不要自动降级成自定义脚本

如果任务涉及 `wpgen`，优先参考：`references/wpgen.md`

### 6. 接入 wpl-check 规则验证资产

`wpl-rule-check` 是规则编写 skill，`wpl-check` 是它执行验证时消费的运行时工具。`wpl-check` 的安装、容器镜像配置、版本选择和卸载由 `wp-deploy` 控制；`wp-deploy` 不负责写 WPL/OML，但部署或示例工程交付时必须把验证资产准备好，并说明如何验证已有规则。

本地二进制安装和版本检查：

```bash
curl -sSf https://get.warpparse.ai/inst-x.sh | bash -s -- wpl-check
export PATH="$HOME/bin:$PATH"
wpl-check -V
```

推荐版本配置：

```bash
export WPL_CHECK_VERSION="${WPL_CHECK_VERSION:-v0.2.0}"
export WPL_CHECK_IMAGE="${WPL_CHECK_IMAGE:-ghcr.io/wp-labs/wpl-check:${WPL_CHECK_VERSION}}"
```

本地验证命令：

```bash
wpl-check syntax models/wpl/<package>/parse.wpl
wpl-check sample models/wpl/<package>/parse.wpl models/wpl/<package>/sample.dat
```

容器化验证路径必须通过 `WPL_CHECK_IMAGE` 明确镜像来源；如果镜像无法拉取，说明失败证据并回退到本地二进制验证：

```bash
docker pull "$WPL_CHECK_IMAGE"
docker run --rm \
  --name wpl-check \
  -v "$(pwd):/work" \
  -w /work \
  "$WPL_CHECK_IMAGE" syntax models/wpl/<package>/parse.wpl
```

如果用户要求编写或修改 WPL/OML，必须切换到 `wpl-rule-check`；如果只是部署验证已有规则，则留在 `wp-deploy` 并使用上面的 `wpl-check` 命令。

### 7. 接入 wp-monitor

当用户需要部署、联调或判断链路是否真的工作正常，而不是只看配置语法时，必须默认部署 `wp-monitor`：

- 观察 source 输入量、解析成功率、MISS、错误和 sink 输出量
- 排查 monitor / miss / downstream 是否异常
- 给联调环境补齐指标与 miss 查询入口

使用要点：

- `wp-monitor` 依赖 `victoria-metrics` 存指标
- 如果要查看 miss 或业务日志，通常还需要 `victoria-logs`
- `wparse` 侧必须在 `infra.d/monitor.toml` 中接 `victoriametrics_sink`，不能停留在 `file_proto_sink -> monitor.dat` 的本地文件模式
- `wp-monitor/config/app.toml` 至少要提供 `vm_base_url` 和 `vlog_base_url`
- docker compose 部署至少要包含或主动启动这些服务：`victoria-metrics`、`victoria-logs`、`wp-monitor`；如果 `wparse` 也容器化，则同一个 compose 中还应包含 `warp-parse`
- 如果当前环境不能启动 `wp-monitor`，必须先实际检查 Docker 或端口等阻塞条件，并说明失败证据；不能因为当前是本地文件示例就默认跳过部署

默认部署动作：

1. 检查 Docker 是否可用：

```bash
docker compose version
docker info
```

2. 在工程目录生成或补齐 `docker-compose.yml` 和 `wp-monitor/config/app.toml`，启动观测栈：

```bash
mkdir -p wp-monitor/config
docker compose up -d victoria-metrics victoria-logs wp-monitor
```

3. 将 `topology/sinks/infra.d/monitor.toml` 从本地文件模式改为 `victoriametrics_sink`。本地运行 `wparse` 时 endpoint 使用宿主机地址：

```toml
version = "2.0"

[sink_group]
name = "monitor"
batch_size = 1
batch_timeout_ms = 300

[[sink_group.sinks]]
name = "victoriametrics"
connect = "victoriametrics_sink"

[sink_group.sinks.params]
endpoint = "http://127.0.0.1:8428"
api_path = "/api/v1/import/prometheus"
```

如果 `wparse` 也在 compose 网络内运行，endpoint 使用服务名：

```toml
endpoint = "http://victoria-metrics:8428"
```

4. 如果需要 miss 查询，确保 `miss` sink 写入 `victorialogs_sink`，本地运行时 endpoint 使用 `http://127.0.0.1:9428`，容器网络内使用 `http://victoria-logs:9428`。

标准 monitor 验证项：

```bash
docker compose ps
docker compose logs wp-monitor
curl -fsS http://localhost:8428/health
curl -fsS http://localhost:9428/health
curl -fsS http://localhost:18080
```

启动后在 `http://localhost:18080` 检查：

- source 输入量是否增长
- parse 成功数和错误数是否符合预期
- miss 是否为空或在可接受范围
- sink 输出量是否增长
- pipeline health 是否正常

最终输出必须包含下面这类结论段，不能省略：

```text
wp-monitor 闭环状态：
- 部署状态：已部署 / 未部署
- 访问地址：http://localhost:18080（如已部署）
- 数据状态：已看到 source 输入量、parse 计数、sink 输出量 / 尚未验证
- Miss 状态：0 或具体数量 / 尚未验证
- 如果未部署：必须写明实际阻塞原因，例如 Docker 不可用、端口冲突、镜像拉取失败；否则应继续部署
```

如果 `wp-monitor` 未部署或未验证，最终总结不能写“完整闭环已完成”。应写“业务链路已完成，监控闭环未完成”，并给出失败证据和补齐命令。没有实际阻塞证据时，不要停在未部署状态，继续完成部署。

如果任务涉及观测或监控联调，优先参考：`references/wp-monitor.md`

### 8. 卸载 wparse 相关组件

当用户要求“卸载 wparse”“清理 wparse 环境”“删除 WarpParse 部署”时，不能只删除二进制。因为 `wp-monitor` 已经是部署闭环的一部分，卸载必须覆盖：

1. 本地命令行工具：`wparse`、`wpgen`、`wproj`、`wpl-check`
2. 规则验证物料：`wpl-check` 临时容器、`WPL_CHECK_IMAGE` 对应镜像
3. 观测栈容器：`wp-monitor`、`victoria-metrics`、`victoria-logs`
4. 如果由同一部署启动，也要停止 `warp-parse`
5. 默认保留数据卷、项目配置和镜像；只有用户明确要求“彻底清理/删除数据/删除镜像”时才删除

卸载前先盘点：

```bash
which wparse wpgen wproj wpl-check || true
docker ps -a --filter "name=wp-monitor" --filter "name=victoria-metrics" --filter "name=victoria-logs" --filter "name=warp-parse" --filter "name=wpl-check"
docker images --format '{{.Repository}}:{{.Tag}}' | grep -E 'wpl-check|wp-labs/wpl-check' || true
docker compose ps 2>/dev/null || true
```

如果当前目录有部署用的 `docker-compose.yml`，优先按 compose 项目停止：

```bash
docker compose down
```

如果没有 compose 文件，或这些容器是用固定容器名直接启动的，按容器名停止并删除：

```bash
docker rm -f wp-monitor victoria-metrics victoria-logs warp-parse wpl-check 2>/dev/null || true
```

再删除本地二进制：

```bash
for bin in wparse wpgen wproj wpl-check; do
  path="$(command -v "$bin" 2>/dev/null || true)"
  if [ -n "$path" ]; then
    rm -f "$path"
  fi
done
```

验证卸载结果：

```bash
command -v wparse wpgen wproj wpl-check || true
docker ps -a --filter "name=wp-monitor" --filter "name=victoria-metrics" --filter "name=victoria-logs" --filter "name=warp-parse" --filter "name=wpl-check"
```

彻底清理需要用户明确确认后才能执行：

```bash
docker compose down -v --rmi local
docker volume rm <metrics_volume> <logs_volume>
export WPL_CHECK_VERSION="${WPL_CHECK_VERSION:-v0.2.0}"
export WPL_CHECK_IMAGE="${WPL_CHECK_IMAGE:-ghcr.io/wp-labs/wpl-check:${WPL_CHECK_VERSION}}"
docker image rm ghcr.io/wp-labs/wp-monitor:latest victoriametrics/victoria-metrics:v1.133.0 victoriametrics/victoria-logs:v1.43.0 "$WPL_CHECK_IMAGE"
```

卸载结果必须明确说明：

- 删除了哪些二进制
- 停止并删除了哪些容器，包括 `wpl-check`、`wp-monitor`、`victoria-metrics`、`victoria-logs`
- 是否保留或删除了 `WPL_CHECK_IMAGE` 对应镜像
- 是否保留了 metrics/logs 数据卷
- 是否保留了项目配置、镜像和业务输出文件

### 9. 给出部署方式

当用户要求部署或联调落地时，至少要交付下面其中一种：

- `docker compose` 启动方案
- 单机目录布局和启动命令
- 链路依赖说明：谁先启动、谁连谁、端口和落点是什么

需要明确说明：

- `warp-parse` 如何挂载 `wparse/` 目录
- `wpgen` 使用哪个 `conf/wpgen.toml`，往哪个 sink connector 发流量，以及确切运行命令
- `wp-monitor` 读哪个 `victoria-metrics` / `victoria-logs` 地址
- `wp-monitor` 页面或日志中要检查哪些指标、miss、source/sink 状态
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

生成或修改项目配置后，必须使用 `wproj` 进行验证。

结束前至少要给出以下结果中的一种：

1. 一组由 `wproj` 初始化、同步或更新得到的完整可落地部署配置，覆盖 connector + topology + `wparse.toml`
2. 对现有 source / sink / `wpgen` / `wp-monitor` 配置的精确修改
3. 明确指出当前链路哪里没有接上，缺少什么依赖

如果做了配置修改，还应说明：

- 改了哪些文件
- 用了哪条 `wproj init` 或 `wproj conf update` 命令生成/更新配置
- 如何用同一条 `wproj` 命令再生成或更新配置
- `wproj check --work-root . --what all --fail-fast` 是否通过
- source、sink、`wpgen`、`wp-monitor` 是怎么接起来的
- 测试数据是否通过 `wpgen` 发送或回放；如果没有，缺少什么条件
- `wp-monitor` 是否已接入并看到数据；如果没有，必须明确写“观测闭环未完成”，并列出缺少什么依赖或启动条件
- 哪些参数来自默认定义，哪些参数在实例侧覆盖
- 业务数据、监控数据、miss 数据分别落到哪里
- 如果未验证，缺少哪一步环境条件

## 输出要求

优先输出：

1. 变更后的配置文件路径
2. 使用过或需要执行的 `wproj` 生成、更新、验证命令
3. 使用过或需要执行的 `wpgen` 配置检查和样本回放命令
4. `wp-monitor` 启动方式和 monitor 验证项
5. `wp-monitor 闭环状态`：部署状态、访问地址、数据状态、miss 状态、未完成原因
6. 每个文件的作用
7. 为什么这样接线和部署
8. 启动顺序、依赖关系和验证方式


## 示例与参考

优先参考本地材料：

- `references/cli-introduce.md`：wparse、wpgen、wproj 的 CLI 使用方法和参数说明，包含了安装和卸载
- `references/knowdb-introduce.md`：知识库配置说明和示例
- `references/connector-introduce.md`：source / sink / sink_group 总览、常用参数整理
- `references/wpgen.md`：`wpgen` 配置、输出接线和压测速度模型
- `references/wp-monitor.md`：`wp-monitor` 配置、监控 sink 接入和观测依赖
- `references/warp-console-observability.md`：从 `warp-console` 提炼出的日志解析 + 观测 + 部署主线
- `examples/file_to_file/`：最小 file source -> file sink -> `wparse` 只读参考示例
- `examples/warp-observability/`：带 `wpgen`、`wp-monitor` 和观测依赖的只读参考示例

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
- 当卸载wparse时，需要卸载wparse的整套组件：二进制 + `wpl-check` 验证物料 + `wp-monitor` 观测栈容器；数据卷和镜像默认保留，除非用户明确要求彻底清理。
- 如果需要发送数据来验证测试结果，必须给出 `wpgen` 命令，不要生成自定义 sender 脚本。
- 如果给出部署或联调方案，必须包含 `wp-monitor` 配置或启动说明，以及 monitor 侧验证项。
- 当提供配置时，无论是否使用知识库，都要提供一个默认知识库配置。
