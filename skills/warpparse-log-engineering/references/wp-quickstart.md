# WP 项目从零开始配置指南

当用户问"如何从0开始配置一个 WP 解析项目"、"第一步做什么"、"完整流程是什么"时，看这个文件。

## 前置条件

- 操作系统：Linux / macOS
- 权限：能够安装软件到 `/usr/local` 或用户目录
- 网络：能访问 `get.warpparse.ai` 和 GitHub

## 第一步：安装工具链

```bash
# 安装 WarpParse 工具链
curl -sSf https://get.warpparse.ai/setup.sh | bash

# 验证安装
wproj --version
wparse --version
wpgen --version
```

**预期输出：**
```
wproj x.y.z
wparse x.y.z
wpgen x.y.z
```

## 第二步：创建工程目录

```bash
# 创建工作目录
mkdir -p ~/wp-projects/my-project
cd ~/wp-projects/my-project

# 初始化工程（完整模式）
wproj init -m full

# 检查工程结构
wproj check
```

**预期目录结构：**
```
my-project/
├── conf/
│   └── wparse.toml        # 主配置文件
├── connectors/            # 连接器配置
├── data/
│   ├── logs/              # 运行日志
│   ├── parsed/            # 解析输出
│   └── samples/           # 样本数据
├── models/
│   ├── knowledge/         # 知识库
│   ├── oml/               # OML 规则
│   └── wpl/               # WPL 规则
└── topology/              # 拓扑配置
```

## 第三步：添加日志解析规则

### 3.1 创建规则目录

```bash
# 为你的日志类型创建目录
mkdir -p models/wpl/my_log_type
```

### 3.2 准备样本数据

把 3-10 条代表性日志保存到 `models/wpl/my_log_type/sample.dat`：

```bash
cat > models/wpl/my_log_type/sample.dat << 'EOF'
# 你的日志样本
样本行1
样本行2
样本行3
EOF
```

### 3.3 编写 WPL 规则

创建 `models/wpl/my_log_type/parse.wpl`：

```wpl
package my_log_type {
  rule main {
    (
      # 根据样本填写字段
    )
  }
}
```

**注意：** 具体规则编写请切换到 `wpl-rule-check` skill。

## 第四步：配置数据路由

编辑 `conf/wparse.toml`，配置 source 和 sink：

```toml
[source]
type = "file"
path = "data/samples/input.log"

[sink]
type = "file"
path = "data/parsed/output.json"
```

## 第五步：本地验证

```bash
# 清理旧数据
wproj data clean
wpgen data clean

# 生成测试样本（如果需要）
wpgen sample -n 1000 --stat 2

# 运行解析
wparse batch --stat 2 -p

# 查看结果
wproj data stat
```

**预期输出：**
```
Total lines:     1000
Parsed:          1000
Success rate:    100.00%
Output size:     XXX KB
```

## 第六步：查看解析结果

```bash
# 查看输出文件
ls -la data/parsed/

# 查看解析日志
tail -f data/logs/wparse.log
```

## 常见问题排查

### 问题1：wproj init 失败

```bash
# 检查当前目录权限
ls -la .

# 检查工具链
which wproj
```

### 问题2：解析成功率低

```bash
# 查看错误日志
grep ERROR data/logs/wparse.log

# 检查规则语法
wpl-check syntax models/wpl/my_log_type/parse.wpl

# 用样本验证
wpl-check sample models/wpl/my_log_type/parse.wpl models/wpl/my_log_type/sample.dat
```

### 问题3：字段缺失或错误

```bash
# 检查输出格式
head -20 data/parsed/output.json

# 验证规则字段定义
cat models/wpl/my_log_type/parse.wpl
```

## 完整检查清单

| 步骤 | 命令 | 验证点 |
|------|------|--------|
| 1. 安装 | `wproj --version` | 版本号显示 |
| 2. 初始化 | `wproj check` | 无错误 |
| 3. 样本 | `cat models/wpl/*/sample.dat` | 有样本数据 |
| 4. 规则 | `wpl-check syntax` | 语法正确 |
| 5. 解析 | `wparse batch` | 无错误 |
| 6. 结果 | `wproj data stat` | 成功率 > 95% |

---

## 完整示例：Nginx 访问日志解析

以下是一个从零开始的完整 nginx 日志解析示例。

### 1. 初始化项目

```bash
# 创建项目目录
mkdir -p ~/wp-projects/nginx-demo
cd ~/wp-projects/nginx-demo

# 初始化完整项目
wproj init -m full

# 验证结构
wproj check
```

### 2. 准备 WPL 规则

```bash
# 创建 nginx 规则目录
mkdir -p models/wpl/nginx
```

创建 `models/wpl/nginx/parse.wpl`：

```wpl
package /nginx/ {
  rule access {
    (
      ip:client_ip,
      2*_,
      time/clf:timestamp<[,]>,
      http/request:request",
      http/status:status,
      digit:bytes,
      chars:referer",
      chars:user_agent",
      chars:xff"
    )
  }
}
```

创建 `models/wpl/nginx/sample.dat`（样本数据）：

```
192.168.1.10 - - [21/Mar/2025:01:40:02 +0800] "GET /api/user HTTP/1.1" 200 1234 "http://example.com/" "Mozilla/5.0 Chrome/90" "-"
10.0.0.5 - admin [21/Mar/2025:02:15:33 +0800] "POST /login HTTP/1.1" 302 512 "http://example.com/login" "curl/7.68.0" "203.0.113.50"
172.16.0.100 - - [21/Mar/2025:03:22:11 +0800] "GET /static/logo.png HTTP/1.1" 304 0 "http://example.com/" "Mozilla/5.0 Safari/537.36" "-"
```

### 3. 验证规则

```bash
# 检查语法
wpl-check syntax models/wpl/nginx/parse.wpl

# 验证样本（注意：只验证第一条）
wpl-check sample models/wpl/nginx/parse.wpl models/wpl/nginx/sample.dat
```

**预期输出：**
```
source: ok (package /nginx/, 1 rules)

data: ok (package /nginx/ / rule access, 8 fields, XXX bytes residue)

NO:1          [ip              ] client_ip            : 192.168.1.10
NO:4          [time            ] timestamp            : 2025-03-21 01:40:02
NO:5          [http/request    ] request              : GET /api/user HTTP/1.1
NO:6          [digit           ] status               : 200
NO:7          [digit           ] bytes                : 1234
NO:8          [chars           ] referer              : http://example.com/
NO:9          [chars           ] user_agent           : Mozilla/5.0 Chrome/90
NO:10         [chars           ] xff                  : -
```

### 4. 配置数据源

编辑 `topology/sources/wpsrc.toml`：

```toml
[[sources]]
key = "nginx_access"
enable = true
connect = "file_src"
tags = ["type:nginx", "format:clf"]

[sources.params]
base = "./data/in_dat"
encode = "text"
file = "nginx_access.dat"

# 禁用其他默认源
[[sources]]
key = "syslog_1"
enable = false
connect = "syslog_tcp_src"

[[sources]]
key = "file_1"
enable = false
connect = "file_src"
```

### 5. 准备测试数据

```bash
# 创建输入目录
mkdir -p data/in_dat

# 复制样本作为测试数据
cp models/wpl/nginx/sample.dat data/in_dat/nginx_access.dat
```

### 6. 运行解析

```bash
# 清理旧数据
wproj data clean

# 运行批处理解析
wparse batch --stat 2 -p
```

**预期输出：**
```
============================ total stat ==============================

+-------+------------+----------------+---------+-------+---------+----------+-------+
| stage | name       | target         | collect | total | success | suc-rate | speed |
+====================================================================================+
| Parse | parse_stat | /nginx//access |         | 3     | 3       | 100.0%   | 0.06  |
|-------+------------+----------------+---------+-------+---------+----------+-------|
| Pick  | pick_stat  | nginx_access   |         | 3     | 3       | 100.0%   | 0.50  |
|-------+------------+----------------+---------+-------+---------+----------+-------|
| Sink  | sink_stat  | demo/json      |         | 3     | 3       | 100.0%   | 0.25  |
+-------+------------+----------------+---------+-------+---------+----------+-------+
```

### 7. 查看解析结果

```bash
# 查看输出文件
ls -la data/out_dat/

# 查看解析后的 JSON
cat data/out_dat/demo.json
```

**输出示例：**
```json
{
  "client_ip": "192.168.1.10",
  "timestamp": "2025-03-21 01:40:02",
  "request": "GET /api/user HTTP/1.1",
  "status": 200,
  "bytes": 1234,
  "referer": "http://example.com/",
  "user_agent": "Mozilla/5.0 Chrome/90",
  "xff": "-",
  "wp_src_key": "nginx_access"
}
```

### 8. 常见问题处理

**问题：wpl-check sample 有 residue**

```
data: ok (..., 578 bytes residue)
residue:
10.0.0.5 - admin [21/Mar/2025:02:15:33 +0800] ...
```

**说明：** `wpl-check sample` 只验证第一条样本，residue 是剩余样本，属于正常行为。

**问题：override not allowed**

```
Details: override not allowed
```

**解决：** 检查 `connectors/source.d/00-file_src.toml` 中的 `allow_override` 白名单，只覆写允许的参数。

**问题：No such file or directory**

```
Details: No such file or directory (os error 2)
```

**解决：** 检查 `base` 和 `file` 配置，确保路径拼接正确：
- 正确：`base = "./data/in_dat"`, `file = "nginx.dat"`
- 错误：`file = "data/in_dat/nginx.dat"`（file 不应包含路径）

## 下一步

- 接入真实数据源（Kafka、文件、Syslog 等）
- 配置多个 sink（ES、Kafka、文件等）
- 设置监控和告警
- 规划 rollout 策略

## 相关文档

- `docs-zh/10-user/01-cli/01-getting_started.md`
- `docs-zh/10-user/01-cli/02-wproj.md`
- `docs-zh/10-user/01-cli/03-wparse.md`
- `references/wpl-authoring-routing.md` - WPL 编写入口