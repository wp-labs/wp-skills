# wp-monitor介绍
Wp-Monitor 是面向 WarpParse 数据链路的统一观察入口，用于查看链路输入、解析、MISS 是否异常、下游输出等指标。

Wp-Monitor 依赖于victoriametrics进行指标存储和查询，依赖victorialogs查看miss的数据。


## wp-monitor配置
Wp-Monitor 的配置文件的默认路径为 `./config/app.toml`，该配置文件可以使用`APP_CONFIG_PATH`环境变量指定路径。
```toml
vm_base_url = "http://victoria-metrics:8428"
vlog_base_url = "http://victoria-logs:9428"
log_level = "info"
miss_file_path = "../wp-example/data/out_dat/miss.dat"
```

- vm_base_url: victoriametrics的地址，Wp-Monitor会把指标数据发送到这个地址。
- vlog_base_url: 可选，victorialogs的地址，Wp-Monitor会从这个地址查询miss的数据。
- log_level: Wp-Monitor的日志级别，默认为info。
- miss_file_path: miss数据文件的路径,当配置了miss_file_path时，Wp-monitor展示的miss数据来源于该文件，否则来源于victoria-logs。


## docker compose示例

可以直接参考 `examples/metrics-example/docker-compose.yml`，用 `docker compose` 启动 `victoria-metrics`、`victoria-logs` 和 `wp-monitor`：

```yaml
services:
  victoria-metrics:
    container_name: victoria-metrics
    image: victoriametrics/victoria-metrics:v1.133.0
    ports:
      - "8428:8428"
    volumes:
      - metrics_data:/storage
    command:
      - --envflag.enable
      - --envflag.prefix=VM_
      - --loggerFormat=json
      - --retentionPeriod=15d
      - --storageDataPath=/storage
      - "-search.latencyOffset=0s"
    environment:
      - TZ=Asia/Shanghai
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://127.0.0.1:8428/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

  victoria-logs:
    container_name: victoria-logs
    image: victoriametrics/victoria-logs:v1.43.0
    ports:
      - "9428:9428"
    volumes:
      - logs_data:/storage
    command:
      - --envflag.enable
      - --envflag.prefix=VLOGS_
      - --http.shutdownDelay=15s
      - --httpListenAddr=:9428
      - --loggerFormat=json
      - --retentionPeriod=15d
      - --storageDataPath=/storage
    environment:
      - TZ=Asia/Shanghai
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://127.0.0.1:9428/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

  wp-monitor:
    image: ghcr.io/wp-labs/wp-monitor:latest
    container_name: wp-monitor
    restart: unless-stopped
    ports:
      - "18080:18080"
    environment:
      APP_CONFIG_PATH: /app/config/app.toml
    volumes:
      - ./wp-monitor/config:/app/config:ro

volumes:
  logs_data:
    driver: local
  metrics_data:
    driver: local
```


启动命令：

```bash
docker compose up -d
docker compose logs wp-monitor
```

启动后可通过 `http://localhost:18080` 访问 `wp-monitor` 页面。

## 部署验证清单

生成的部署或联调方案应默认主动部署 `wp-monitor`。不要只写“后续可以启动 wp-monitor”。如果当前环境不能启动 `wp-monitor`，需要先实际检查 Docker、端口、镜像拉取等阻塞条件，并明确写出失败证据；没有阻塞证据时，应继续完成部署。

默认部署动作：

```bash
docker compose version
docker info
mkdir -p wp-monitor/config
docker compose up -d victoria-metrics victoria-logs wp-monitor
```

`wproj init --mode full` 默认生成的 `topology/sinks/infra.d/monitor.toml` 可能是 `file_proto_sink -> monitor.dat`。这只是本地文件模式，不等于 `wp-monitor` 已部署。部署闭环时必须把 monitor sink 接到 `victoriametrics_sink`：

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

本地运行 `wparse` 时用 `http://127.0.0.1:8428`；如果 `wparse` 也在 compose 网络内运行，使用 `http://victoria-metrics:8428`。

基础服务检查：

```bash
docker compose ps
docker compose logs wp-monitor
curl -fsS http://localhost:8428/health
curl -fsS http://localhost:9428/health
curl -fsS http://localhost:18080
```

打开 `http://localhost:18080` 后，至少检查：

- source 输入量是否增长
- parse 成功数和错误数是否符合预期
- miss 是否为空或在可接受范围
- sink 输出量是否增长
- pipeline health 是否正常

## 最终输出要求

`wp-monitor` 是部署闭环的最后一步。生成部署、联调或示例工程的最终回答，必须包含 `wp-monitor 闭环状态`，不能只输出业务文件或下游 sink 的落点。

推荐格式：

```text
wp-monitor 闭环状态：
- 部署状态：已部署 / 未部署
- 访问地址：http://localhost:18080（已部署时填写）
- 数据状态：已看到 source 输入量、parse 计数、sink 输出量 / 尚未验证
- Miss 状态：0 或具体数量 / 尚未验证
- 结论：完整闭环已完成 / 业务链路已完成，监控闭环未完成
```

如果没有部署 `wp-monitor`，最终结论必须写：

```text
业务链路已完成，监控闭环未完成。
```

并给出实际阻塞证据和补齐命令。只有在 Docker 不可用、端口冲突、镜像拉取失败等明确阻塞存在时，才允许停在未部署状态。否则应继续启动 `victoria-metrics`、`victoria-logs`、`wp-monitor`，并确认 `infra.d/monitor.toml` 已写入 `victoriametrics_sink`。

如果 `wp-monitor` 没有数据，按顺序检查：

1. `wparse/topology/sinks/infra.d/monitor.toml` 是否接入 `victoriametrics_sink`
2. `victoria-metrics` 是否健康
3. `wp-monitor/config/app.toml` 的 `vm_base_url` 是否指向正确地址
4. miss 查询是否需要 `victoria-logs` 或 `miss_file_path`

## wparse接入指标到victoriametrics

- 提供一个victoriametrics连接器`wparse/connectors/sink.d/victoriametrics.toml`,内容如下：
```toml
[[connectors]]
id = "victoriametrics_sink"
type = "victoriametrics"
allow_override = ["endpoint", "api_path", "timeout_secs","batch_size"]
[connectors.params]
endpoint = "http://victoria-metrics:8428"
api_path = "/api/v1/import/prometheus"
timeout_secs = 3
```

- 在wparse的monitor基础设施中`wparse/topology/sinks/infra.d/monitor.toml`中提供一个sink。
```toml
[[sink_group.sinks]]
name = "metrics_vmetrics_sink"
connect = "victoriametrics_sink"
[sink_group.sinks.params]
endpoint = "http://victoria-metrics:8428"
api_path = "/api/v1/import/prometheus"
```

## 接入miss日志到victorialogs中
- 提供一个victorialogs连接器,`wparse/connectors/sink.d/victorialogs.toml`内容如下：
```toml
[[connectors]]
id = "victorialogs_sink"
type = "victorialogs"
allow_override = ["endpoint", "api_path", "timestamp_field", "timeout_secs","batch_size","tags"]
[connectors.params]
endpoint = "http://victoria-logs:9428"
api_path = "/insert/jsonline"
timeout_secs = 3
```

- 在wparse的miss基础设施中`wparse/topology/sinks/infra.d/miss.toml`中提供一个sink，sink需要包含`wp_stage:miss`tag。
```toml
[[sink_group.sinks]]
name = "victorialogs_output"
connect = "victorialogs_sink"
[sink_group.sinks.params]
endpoint = "http://wp-monitor-victoria-logs:9428"
api_path = "/insert/jsonline?_msg_field=content,log"
tags = ["wp_stage:miss"]
```
