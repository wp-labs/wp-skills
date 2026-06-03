# warp-observability 示例

这是一个面向 **source / sink 联调 + 观测验证 + 部署落地** 的完整示例。

它把 5 个角色接成了一条闭环链路：

1. `wpgen` 生成测试数据
2. `warp-parse` 通过 `tcp source` 接收并解析数据
3. 业务日志写入 `victoria-logs`
4. 运行指标写入 `victoria-metrics`
5. `wp-monitor` 统一查看指标和日志

## 目录结构

```sh
.
├── docker-compose.yml
├── wp-monitor/
│   └── config/
│       └── app.toml
└── wparse/
    ├── conf/
    │   ├── wparse.toml
    │   └── wpgen.toml
    ├── connectors/
    │   ├── source.d/
    │   └── sink.d/
    ├── models/
    └── topology/
        ├── sources/
        └── sinks/
            ├── business.d/
            ├── infra.d/
            └── defaults.toml
```

## 示例包含哪些服务

`docker-compose.yml` 中只保留了与日志解析和观测直接相关的 4 个服务：

- `warp-parse`
  - 镜像：`ghcr.io/wp-labs/warp-parse:latest`
  - 挂载：`./wparse:/app/config`
  - 入口：`wparse deamon --work-root /app/config`
  - 端口：
    - `19002`：TCP 接入端口
    - `19090`：预留的管理端口映射
- `victoria-metrics`
  - 端口：`8428`
  - 用于接收 `monitor sink` 写入的指标
- `victoria-logs`
  - 端口：`9428`
  - 用于接收业务 sink 输出的日志
- `wp-monitor`
  - 端口：`18080`
  - 统一查看指标和日志

## 数据流向

这个示例的核心链路如下：

```text
wpgen
  -> tcp_sink
  -> warp-parse tcp source
  -> parse / route
  -> victorialogs_sink -> victoria-logs
  -> victoriametrics_sink -> victoria-metrics
  -> wp-monitor
```

其中有两条输出线：

- 业务输出线：`warp-parse -> victorialogs_sink -> victoria-logs`
- 监控指标线：`warp-parse -> victoriametrics_sink -> victoria-metrics`

## 关键配置说明

### 1. source：TCP 接入

`wparse/topology/sources/wpsrc.toml`：

```toml
[[sources]]
enable = true
key = "tcp_web"
connect = "tcp_src"
params = { prefer_newline = true, port = 19002, instances = 1 }
tags = ["src:tcp"]
```

说明：

- 当前示例使用 `tcp_src` 作为入口 source
- 监听端口是 `19002`
- `prefer_newline = true`，更适合文本样本按行输入

### 2. wpgen：测试流量入口

`wparse/conf/wpgen.toml`：

```toml
[generator]
mode = "sample"
count = 3
speed = 1000
parallel = 2

[output]
name = "gen_out"
connect = "tcp_sink"
params = { port = 19002 }
```

说明：

- `wpgen` 用 sample 模式生成数据
- 输出不是写文件，而是走 `tcp_sink`
- 数据直接发到 `warp-parse` 的 `19002` 端口

### 3. wparse 工程入口

`wparse/conf/wparse.toml` 指定了标准工程结构：

- `models/wpl` 和 `models/oml`
- `topology/sources`
- `topology/sinks`

同时开启了三类统计：

- `pick_stat`
- `parse_stat`
- `sink_stat`

这也是后续 `monitor sink` 有数据可看的基础。

### 4. 业务 sink：写入 VictoriaLogs

`wparse/topology/sinks/business.d/sink.toml`：

```toml
[sink_group]
name = "all"
oml = ["*"]

[[sink_group.sinks]]
name = "victorialogs_output"
connect = "victorialogs_sink"
params = { endpoint = "http://victoria-logs:9428", insert_path = "/insert/jsonline?_msg_field=content,log", flush_interval_secs = 3 }
```

说明：

- 所有满足 `oml = ["*"]` 的数据都进入该 sink_group
- 业务日志被发往 `victoria-logs`
- `insert_path` 指定了 JSON Line 写入接口和消息字段映射

### 5. monitor sink：写入 VictoriaMetrics

`wparse/topology/sinks/infra.d/monitor.toml`：

```toml
[sink_group]
name = "monitor"

[[sink_group.sinks]]
name = "metrics_vmetrics_sink"
connect = "victoriametrics_sink"
params = { insert_url = "http://victoria-metrics:8428/api/v1/import/prometheus", flush_interval_secs = 1 }
```

说明：

- `monitor` 组负责输出运行指标
- 指标通过 `victoriametrics_sink` 写入 `victoria-metrics`
- `flush_interval_secs = 1`，适合联调时快速看到变化

### 6. wp-monitor：统一观察入口

`wp-monitor/config/app.toml`：

```toml
vm_base_url = "http://victoria-metrics:8428"
vlog_base_url = "http://victoria-logs:9428"

refresh_interval_sec = 5
default_window_min = 15
time_presets = [5, 15, 30, 60]
api_version = "v1"
log_level = "info"
```

说明：

- 指标查询走 `victoria-metrics`
- 日志 / miss 查询走 `victoria-logs`
- 页面默认每 5 秒刷新一次

## 怎么启动

在当前目录执行：

```bash
docker compose up -d
docker compose logs wp-monitor
```

启动后可访问：

- `http://localhost:18080`：`wp-monitor`
- `http://localhost:8428`：`victoria-metrics`
- `http://localhost:9428`：`victoria-logs`

## 怎么理解这个示例

这个示例不是“最小参数示例”，而是“最小可观察部署链路示例”。

它最适合回答这些问题：

- source 和 sink 都配好了，怎么做一次完整联调
- 怎么让 `wpgen` 给链路灌测试数据
- 怎么确认 `monitor sink` 已经生效
- 怎么同时看业务输出和运行指标

## 建议阅读顺序

1. `../../references/connector-introduce.md`
2. `../../references/wpgen.md`
3. `../../references/wp-monitor.md`
4. `../../references/warp-console-observability.md`
