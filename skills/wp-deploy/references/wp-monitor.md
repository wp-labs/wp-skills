# wp-monitor介绍
Wp-Monitor 是面向 WarpParse 数据链路的统一观察入口，用于查看链路输入、解析、MISS 是否异常、下游输出等指标。

Wp-Monitor 依赖于victoriametrics进行指标存储和查询，依赖victorialogs查看miss的数据。

## wp-monitor配置
```toml
vm_base_url = "http://victoria-metrics:8428"
vlog_base_url = "http://victoria-logs:9428"
log_level = "info"
```

- vm_base_url: victoriametrics的地址，Wp-Monitor会把指标数据发送到这个地址。
- vlog_base_url: 可选，victorialogs的地址，Wp-Monitor会从这个地址查询miss的数据。
- log_level: Wp-Monitor的日志级别，默认为info。

在示例工程中，`app.toml` 还包含如下常见字段：

```toml
vm_base_url = "http://victoria-metrics:8428"
vlog_base_url = "http://victoria-logs:9428"

api_version = "v1"
log_level = "info"
refresh_interval_sec = 5
default_window_min = 15
time_presets = [5, 15, 30, 60]
```

- api_version: API版本，示例中为 `v1`。
- refresh_interval_sec: 页面刷新间隔，单位为秒。
- default_window_min: 默认时间窗口，单位为分钟。
- time_presets: 页面预设时间窗口列表，单位为分钟。

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
    image: ghcr.io/wp-labs/wp-monitor:0.4.1-alpha
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

建议的目录结构：

```sh
.
├── docker-compose.yml
└── wp-monitor/
    └── config/
        └── app.toml
```

对应的 `wp-monitor/config/app.toml` 可写为：

```toml
vm_base_url = "http://victoria-metrics:8428"
vlog_base_url = "http://victoria-logs:9428"

api_version = "v1"
log_level = "info"
refresh_interval_sec = 5
default_window_min = 15
time_presets = [5, 15, 30, 60]
```

启动命令：

```bash
docker compose up -d
docker compose logs wp-monitor
```

启动后可通过 `http://localhost:18080` 访问 `wp-monitor` 页面。

## wparse将指标接入到victoriametrics
在wparse的基础设施`infra.d/monitor.toml`中提供一个sink。
```toml
[[sink_group.sinks]]
name = "metrics_vmetrics_sink"
connect = "victoriametrics_sink"
[sink_group.sinks.params]
insert_url = "http://victoria-metrics:8428/api/v1/import/prometheus"
flush_interval_secs = 1
```

如果还需要在 `wp-monitor` 中查看 miss 数据，通常还需要给业务或基础设施链路接入 `victorialogs_sink`，并保证 `vlog_base_url` 指向可访问的 VictoriaLogs 地址。

