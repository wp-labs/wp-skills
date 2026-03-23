# WP 常见错误排障指南

本文档汇总 WarpParse 使用过程中的常见错误及解决方案。

---

## 错误分类

| 分类 | 说明 | 典型错误 |
|------|------|----------|
| 配置错误 | 配置文件格式或参数问题 | override not allowed |
| 路径错误 | 文件或目录不存在 | No such file or directory |
| 规则错误 | WPL 语法或匹配问题 | 解析失败、字段缺失 |
| 连接错误 | 网络或服务连接问题 | 连接超时、认证失败 |

---

## 配置错误

### override not allowed

**错误信息：**
```
[50041] validation error
  -> Details: override not allowed
```

**原因：** 参数不在连接器 `allow_override` 白名单中。

**解决步骤：**

```bash
# 1. 查看连接器定义
cat connectors/source.d/00-file_src.toml

# 输出示例：
# allow_override = ["base", "file", "encode"]

# 2. 确认只覆写白名单内的参数
```

**正确配置：**
```toml
# connectors/source.d/00-file_src.toml
allow_override = ["base", "file", "encode"]

# wpsrc.toml - 只覆写白名单参数
[[sources]]
key = "nginx_access"
connect = "file_src"

[sources.params]
base = "./data/in_dat"      # ✅ 在白名单中
file = "nginx.dat"          # ✅ 在白名单中
encode = "text"             # ✅ 在白名单中
# wpl = "models/wpl/nginx"  # ❌ 不在白名单，会报错
```

### validation error

**错误信息：**
```
[50041] validation error
  -> Want: parse/build sources
```

**排查步骤：**

```bash
# 检查配置完整性
wproj check --json --only-fail

# 检查数据源配置
wproj sources list

# 检查连接器
wproj check --what connectors
```

### `wpgen sample --wpl ...` 报 core config error

**错误信息：**
```
[50041] configuration error << core config
```

**优先检查：**

```bash
find models/wpl/kv_pairs -maxdepth 1 -type f
```

**说明：**

- `wpgen sample --wpl <dir>` 会固定查找 `<dir>/sample.dat`
- 如果缺少 `sample.dat`，当前版本可能只返回较笼统的 core config 错误

---

## 路径错误

### No such file or directory

**错误信息：**
```
[200] data error
  -> Want: open source file
  -> Details: No such file or directory (os error 2)
  -> Context: models/wpl/nginx_access/data/in_dat/nginx_access.dat
```

**原因：** 路径拼接错误，文件不存在。

**排查步骤：**

```bash
# 1. 确认当前工作目录
pwd

# 2. 理解路径拼接规则：{base}/{file}
# 错误示例中 base=models/wpl/nginx_access, file=data/in_dat/nginx_access.dat
# 实际查找: models/wpl/nginx_access/data/in_dat/nginx_access.dat ❌

# 3. 验证文件存在
ls -la ./data/in_dat/nginx_access.dat
```

**正确配置：**
```toml
# wpsrc.toml
[sources.params]
base = "./data/in_dat"          # 目录
file = "nginx_access.dat"       # 文件名
# 实际路径: ./data/in_dat/nginx_access.dat
```

### path not found

**错误信息：**
```
path not found: ./models/wpl/nginx
```

**排查：**
```bash
# 检查目录结构
ls -la models/wpl/

# 检查 WPL 规则目录配置
grep "wpl" conf/wparse.toml
```

### `wpl-check` 通过但 `wparse batch` 不生效

**现象：**

- `wpl-check syntax` 通过
- `wpl-check sample` 通过
- `wparse batch` 后数据仍进入 `miss.dat`

**优先排查：**

```bash
find models/wpl -maxdepth 2 -type f
ls -la models/oml
sed -n '1,200p' topology/sources/wpsrc.toml
sed -n '1,50p' data/out_dat/miss.dat
```

**说明：**

- 运行时优先使用 `models/wpl/<name>/parse.wpl` 与 `models/wpl/<name>/sample.dat`
- 只把规则放在 `models/wpl/<name>.wpl` 顶层时，容易出现“离线可用、工程不生效”
- 还要确认 OML、source、sink 已经把数据真正接到目标规则

---

## 规则错误

### wpl-check sample 有 residue

**现象：**
```
data: ok (package nginx, 10 fields, 578 bytes residue)

residue:
10.0.0.5 - admin [21/Mar/2025:02:15:33 +0800] "POST /login HTTP/1.1" ...
```

**说明：** 这是**正常行为**，`wpl-check sample` 只验证第一条样本。

**验证多样本：**
```bash
# 方法一：单样本文件
wpl-check sample parse.wpl single_sample.dat

# 方法二：批量解析（推荐）
wparse batch --stat 2 -p
wproj data stat
```

### 解析成功率低

**现象：**
```
Success rate: 45.00%
```

**排查步骤：**

```bash
# 1. 查看错误日志
grep ERROR data/logs/wparse.log

# 2. 检查未解析数据
cat data/out_dat/miss.dat

# 3. 检查残差数据
cat data/out_dat/residue.dat

# 4. 验证规则语法
wpl-check syntax models/wpl/nginx/parse.wpl

# 5. 用样本验证
wpl-check sample models/wpl/nginx/parse.wpl models/wpl/nginx/sample.dat
```

**常见原因：**

| 原因 | 现象 | 解决 |
|------|------|------|
| 规则不匹配 | 全部失败 | 对照样本修改规则 |
| 格式漂移 | 部分失败 | 增加变体规则 |
| 分隔符错误 | 字段错位 | 检查分隔符定义 |
| 类型不匹配 | 特定字段失败 | 使用更通用的类型（如 `chars`） |

### 字段缺失

**现象：** 输出 JSON 缺少预期字段

**排查：**
```bash
# 查看输出格式
head -5 data/out_dat/demo.json | jq .

# 检查规则字段定义
cat models/wpl/nginx/parse.wpl
```

### 批量结果与输入不一致

**现象：**

- 输入条数看起来不对
- 命中率和预期差很多
- 输出混入旧数据

**排查：**
```bash
wproj data clean
wpgen data clean
ls -la data/in_dat
ls -la data/out_dat
sed -n '1,20p' data/out_dat/miss.dat
```

**常见原因：**

- `wpgen sample` 默认向旧文件追加写入
- 清理后没有重新恢复输入文件
- 只看 `wproj data stat`，没有检查 `miss.dat` 和 `error.dat`

---

## 连接错误

### Kafka 连接失败

**错误信息：**
```
Failed to connect to brokers: localhost:9092
```

**排查：**
```bash
# 检查 Kafka 可达性
nc -zv kafka-host 9092

# 检查配置
cat connectors/source.d/01-kafka_src.toml

# 测试消费
kafka-console-consumer --bootstrap-server localhost:9092 --topic test --from-beginning
```

### Syslog 端口占用

**错误信息：**
```
Address already in use (os error 98)
```

**排查：**
```bash
# 检查端口占用
lsof -i :1514

# 停止占用进程或更换端口
```

---

## 性能问题

### 解析速度慢

**排查：**
```bash
# 1. 检查统计
wproj data stat

# 2. 调整并发
wparse batch -w 4 --stat 2 -p

# 3. 检查 CPU 使用
top -pid $(pgrep wparse)
```

### 内存占用高

**排查：**
```bash
# 检查内存使用
ps aux | grep wparse

# 减少批量大小或增加限速
wparse batch --rate-limit 5000
```

---

## 快速诊断清单

```bash
# 1. 项目检查
wproj check

# 2. 配置验证
wproj check --what conf

# 3. 规则语法
wpl-check syntax models/wpl/*/parse.wpl

# 4. 样本验证
wpl-check sample models/wpl/nginx/parse.wpl models/wpl/nginx/sample.dat

# 5. 批量运行
wparse batch

# 6. 查看失败样本
sed -n '1,50p' data/out_dat/miss.dat
sed -n '1,50p' data/out_dat/error.dat

# 7. 查看日志和统计
tail -100 data/logs/wparse.log
wproj data stat
```

---

## 相关文档

- `references/wp-cli-tools.md` - CLI 工具使用
- `references/wp-config-reference.md` - 配置文件详解
- `references/wp-connectors.md` - 连接器配置
- `references/wp-runtime-validation.md` - 工程目录约定与批量验证
