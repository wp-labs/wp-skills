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

