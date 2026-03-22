# WP 监控运维指南

本文档介绍 WarpParse 生产环境的监控、运维和故障排查。

---

## 监控指标

### 内置统计

WarpParse 提供三个阶段的统计：

| 阶段 | 说明 | 配置 |
|------|------|------|
| pick | 数据采集 | `[[stat.pick]]` |
| parse | 解析处理 | `[[stat.parse]]` |
| sink | 输出写入 | `[[stat.sink]]` |

**启用统计：**

```toml
# conf/wparse.toml
[stat]

[[stat.pick]]
key    = "pick_stat"
target = "*"

[[stat.parse]]
key    = "parse_stat"
target = "*"

[[stat.sink]]
key    = "sink_stat"
target = "*"
```

### Prometheus 指标

```toml
# 输出到 Prometheus
[[sink_group.sinks]]
name = "prometheus"
connect = "prometheus_sink"
params = {
    port = 9100,
    path = "/metrics"
}
```

**关键指标：**

| 指标 | 说明 |
|------|------|
| 解析速率 | records/second |
| 成功率 | 成功解析/总输入 |
| 延迟 | 解析耗时 |
| 错误数 | 解析失败计数 |

---

## 日志管理

### 日志配置

```toml
# conf/wparse.toml
[log_conf]
output = "File"               # Console|File|Both
level  = "warn,ctrl=info"     # 日志级别

[log_conf.file]
path = "./data/logs"          # 日志目录
```

### 日志级别

| 级别 | 说明 |
|------|------|
| `error` | 错误信息 |
| `warn` | 警告信息（推荐生产） |
| `info` | 运行信息 |
| `debug` | 调试信息 |
| `trace` | 详细追踪 |

### 模块级别控制

```toml
# 不同模块不同级别
level = "warn,ctrl=info,dfx=info,parser=debug"
```

### 日志轮转

- 默认：10MB/文件，保留 10 份
- 自动 gzip 压缩
- 文件名：`wparse.log`

---

## 健康检查

### 进程状态

```bash
# 检查进程
ps aux | grep wparse

# 检查端口（daemon 模式）
netstat -tlnp | grep wparse

# 检查资源
top -p $(pgrep wparse)
```

### 数据检查

```bash
# 检查输入输出
wproj data stat

# 验证数据分布
wproj data validate

# 检查配置
wproj check
```

### 自定义健康检查脚本

```bash
#!/bin/bash
# health_check.sh

# 检查进程
if ! pgrep -x wparse > /dev/null; then
    echo "ERROR: wparse not running"
    exit 1
fi

# 检查日志更新
LAST_LOG=$(find data/logs -name "*.log" -mmin -5)
if [ -z "$LAST_LOG" ]; then
    echo "WARN: No recent log activity"
fi

# 检查解析率
STAT=$(wproj data stat --json 2>/dev/null)
RATE=$(echo "$STAT" | jq '.success_rate // 0')
if [ $(echo "$RATE < 95" | bc) -eq 1 ]; then
    echo "WARN: Low success rate: $RATE%"
fi

echo "OK"
```

---

## 故障排查

### 常见问题

#### 1. 解析失败率高

**症状：** 成功率低于 95%

**排查：**
```bash
# 查看错误日志
grep ERROR data/logs/wparse.log

# 检查 residue 数据
ls -la data/residue/

# 验证规则
wpl-check syntax models/wpl/*/parse.wpl
```

**解决：**
- 更新 WPL 规则匹配新格式
- 检查样本是否覆盖所有格式
- 添加容错字段

#### 2. 内存占用高

**症状：** 内存持续增长

**排查：**
```bash
# 查看内存
top -p $(pgrep wparse)

# 检查队列积压
grep "queue" data/logs/wparse.log
```

**解决：**
- 降低 `rate_limit_rps`
- 减少 `parse_workers`
- 检查 sink 是否阻塞

#### 3. 输出延迟

**症状：** 数据输出延迟大

**排查：**
```bash
# 检查各阶段耗时
grep "latency" data/logs/wparse.log

# 检查下游连接
wproj sinks validate
```

**解决：**
- 检查下游系统状态
- 增加输出并发
- 调整批量写入参数

#### 4. 连接断开

**症状：** Kafka/TCP 连接断开

**排查：**
```bash
# 检查连接状态
grep "disconnect\|reconnect" data/logs/wparse.log

# 测试连接
wproj sources route
```

**解决：**
- 检查网络
- 调整超时参数
- 检查认证配置

---

## 运维操作

### 启动服务

```bash
# 批处理模式
wparse batch --stat 5 -p

# 守护进程模式
wparse daemon --stat 5 -p

# 后台运行
nohup wparse daemon --stat 5 -p > /dev/null 2>&1 &
```

### 优雅停止

```bash
# 发送 SIGTERM
kill -TERM $(pgrep wparse)

# 等待进程结束
wait $(pgrep wparse)
```

### 配置热更新

```bash
# 检查新配置
wproj check

# 重启服务
kill -HUP $(pgrep wparse)
```

### 数据清理

```bash
# 清理输出数据
wproj data clean

# 清理生成数据
wpgen data clean

# 清理日志（手动）
rm -f data/logs/*.log.*
```

---

## 性能调优

### 解析性能

```toml
# conf/wparse.toml
[performance]
rate_limit_rps = 50000    # 提高限速
parse_workers  = 8        # 增加并发
```

### 内存优化

```toml
[performance]
batch_size = 10000        # 批量大小
queue_size = 100000       # 队列大小
```

### 输出优化

```toml
# Kafka 输出优化
[sink_group.sinks.params]
config = [
    "compression.type=snappy",
    "linger.ms=5",
    "batch.size=32768"
]
```

---

## 告警配置

### 关键告警项

| 告警项 | 阈值 | 说明 |
|--------|------|------|
| 进程停止 | N/A | wparse 进程不存在 |
| 成功率低 | < 95% | 解析成功率 |
| 延迟高 | > 10s | 处理延迟 |
| 内存高 | > 80% | 内存使用率 |
| 错误激增 | > 100/min | 错误数量 |

### Prometheus 告警规则

```yaml
groups:
  - name: wparse
    rules:
      - alert: WparseDown
        expr: up{job="wparse"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Wparse process down"

      - alert: LowSuccessRate
        expr: wparse_success_rate < 0.95
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Low parse success rate"
```

---

## 备份恢复

### 配置备份

```bash
# 备份配置
tar -czvf wparse-config-$(date +%Y%m%d).tar.gz \
    conf/ topology/ models/wpl/ models/oml/
```

### 规则版本管理

```bash
# Git 管理规则
cd models/wpl
git init
git add *.wpl
git commit -m "Update rules"
```

---

## 相关文档

- `docs-zh/10-user/02-config/08-logging.md`
- `docs-zh/10-user/09-FQA/troubleshooting.md`