# warp-console 日志解析与观测示例

`warp-console` 是一个更接近真实运行环境的综合示例。对 `wp-deploy` skill 来说，不需要整套平台，只需要抽出**日志解析 + 观测 + 部署接线**这条主线即可。

本文只保留以下组件：

- `warp-parse`
- `warp-toolchain`
- `victoria-metrics`
- `victoria-logs`
- `wp-monitor`
- `wparse/` 下的 `connectors`、`topology`、`conf`、`models`

本文明确忽略以下部分：

- `station/`
- `postgres`
- `gitea`
- `gitea-init`
- `warp-station`
- 所有与 `project_remote`、仓库管理、数据库初始化有关的依赖

## 这个示例解决什么问题

和 `examples/file_to_file/` 相比，`warp-console` 不是一个单纯的 source/sink 参数样例，而是一条完整联调链路：

1. `wpgen` 生成测试数据
2. `warp-parse` 接收并解析数据
3. 业务 sink 把解析结果写入 `victoria-logs`
4. 监控 sink 把指标写入 `victoria-metrics`
5. `wp-monitor` 统一观察输入、解析、MISS 和下游输出

它适合回答这类问题：

- “source 和 sink 都配好了，怎么把整条链路跑起来？”
- “怎么给部署联调环境补一个观察面？”
- “怎么确认 monitor / miss / downstream 是不是正常？”

## 精简后的目录主线

原始目录：`/Users/zwk/src_code/wp-labs/wp-tools/warp-console`

只看这些文件：

```sh
warp-console/
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

## 关键组件说明

### 1. warp-parse

`docker-compose.yml` 中的 `warp-parse` 服务：

- 镜像：`ghcr.io/wp-labs/warp-parse:latest`
- 挂载 `./wparse:/app/config`
- 入口：`wparse deamon --work-root /app/config`
- 暴露端口：
  - `19002`：示例里给 `tcp source` 使用
  - `19090`：`admin_api`

它是整个链路的核心执行器。

### 2. wpgen

`wparse/conf/wpgen.toml` 展示的是“用 `wpgen` 向 `tcp sink` 发数据”的联调方式：

```toml
[output]
name = "gen_out"
connect = "tcp_sink"
params = { port = 19002 }
```

这个配置的意义是：

- 不直接把样本写文件
- 而是把样本当作测试流量推给 `warp-parse` 的 `tcp source`
- 更适合验证接入链路、吞吐和 monitor 指标

### 3. 业务 sink

`wparse/topology/sinks/business.d/sink.toml` 里最重要的是：

```toml
[[sink_group.sinks]]
name = "victorialogs_output"
connect = "victorialogs_sink"
params = { endpoint = "http://victoria-logs:9428", insert_path = "/insert/jsonline?_msg_field=content,log", flush_interval_secs = 3}
```

这里说明：

- 解析后的业务数据不是落本地文件
- 而是直接发往 `victoria-logs`
- `wp-monitor` 后续就可以基于它做日志观察与 miss 查看

### 4. monitor sink

`wparse/topology/sinks/infra.d/monitor.toml` 里最关键的是：

```toml
[[sink_group.sinks]]
name = "metrics_vmetrics_sink"
connect = "victoriametrics_sink"
params = { insert_url = "http://victoria-metrics:8428/api/v1/import/prometheus", flush_interval_secs = 1 }
```

这表示：

- `warp-parse` 运行指标通过 `victoriametrics_sink` 写入 `victoria-metrics`
- `wp-monitor` 读取的不是 `wparse` 本地状态，而是这条指标写入链路的数据

### 5. wp-monitor

`wp-monitor/config/app.toml` 的核心只有两项：

```toml
vm_base_url = "http://victoria-metrics:8428"
vlog_base_url = "http://victoria-logs:9428"
```

意思是：

- 指标面来自 `victoria-metrics`
- miss / 日志查询面来自 `victoria-logs`

## 运行视角下的链路图

可以把这个示例理解成：

```text
wpgen
  -> tcp_sink
  -> warp-parse tcp source
  -> parse / route
  -> victorialogs_sink -> victoria-logs
  -> victoriametrics_sink -> victoria-metrics
  -> wp-monitor
```

其中：

- 业务日志走 `victoria-logs`
- 运行指标走 `victoria-metrics`
- `wp-monitor` 同时消费这两侧的数据

## 对 wp-deploy skill 的价值

这个示例最值得复用的不是“某个具体参数”，而是**完整联调方法**：

### 适合复用的部分

- `wparse/conf/wparse.toml` 的标准工程入口组织
- `wpgen.toml` 用 sink connector 作为输出端的写法
- `infra.d/monitor.toml` 中 monitor sink 的接法
- `business.d/sink.toml` 中业务输出接到 `victoria-logs` 的写法
- `wp-monitor/config/app.toml` 的最小配置
- `docker-compose.yml` 中观测三件套的依赖关系

### 不建议直接照抄的部分

- `project_remote` 配置
- `postgres` / `gitea` / `warp-station` 相关服务
- 与 station 平台初始化相关的卷、环境变量和数据库依赖

## 建议如何落到 examples

如果用户只是问 source / sink 怎么写，优先用：

- `examples/file_to_file/`

如果用户问“怎么把链路跑起来并观察结果”，优先用：

- `examples/metrics-example/`
- `examples/warp-observability/README.md`

如果用户问“为什么要这样接 monitor / victorialogs / wpgen”，优先参考：

- `references/wpgen.md`
- `references/wp-monitor.md`
- 当前文档

## 最小裁剪建议

如果你要把 `warp-console` 裁成一个更专注的部署联调环境，推荐只保留：

```sh
.
├── docker-compose.yml
├── wp-monitor/
│   └── config/app.toml
└── wparse/
    ├── conf/
    ├── connectors/
    ├── models/
    └── topology/
```

然后删除：

- `station/`
- `postgres/`
- `initdb/`
- `.env` 中 station / gitea / pg 相关变量

这样更符合 `wp-deploy` skill 的关注范围：**接线、联调、观测、部署**。
