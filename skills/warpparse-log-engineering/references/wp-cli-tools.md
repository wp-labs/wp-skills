# WarpParse CLI 工具链

本文档介绍 WarpParse 三个核心 CLI 工具的作用和使用方法。

## 工具概览

| 工具 | 作用 | 核心功能 |
|------|------|----------|
| `wproj` | 项目管理 | 初始化、检查、数据管理、模型管理 |
| `wparse` | 解析引擎 | 批处理解析、守护进程服务 |
| `wpgen` | 数据生成 | 基于规则/样本生成测试数据 |

---

## wproj - 项目管理工具

项目管理工具，提供完整的项目生命周期管理。

### 命令概览

```bash
wproj <COMMAND>

Commands:
  init   初始化工程骨架
  check  检查项目配置和文件完整性
  data   数据管理（清理、统计、验证）
  model  模型管理（规则、源、汇、知识库）
  rule   规则工具（离线解析测试）
```

### init - 项目初始化

```bash
wproj init [OPTIONS]

Options:
  -m, --mode <MODE>  初始化模式（默认：conf）
```

**初始化模式：**

| 模式 | 说明 |
|------|------|
| `full` | 完整项目（配置+模型+数据+示例+连接器） |
| `normal` | 完整项目（配置+模型+数据+示例） |
| `model` | 仅模型文件 |
| `conf` | 仅配置文件 |
| `data` | 仅数据目录 |

**示例：**

```bash
# 初始化完整项目
wproj init -m full

# 初始化配置文件
wproj init -m conf -w /project
```

### check - 项目检查

```bash
wproj check [OPTIONS]

Options:
  -w, --work-root <DIR>   根目录（默认：.）
  --what <ITEMS>          检查项（默认：all）
  --fail-fast             首次失败即退出
  --json                  JSON 格式输出
  --only-fail             仅输出失败项
```

**检查项（--what）：**

| 值 | 说明 |
|----|------|
| `conf` | 主配置文件 |
| `connectors` | 连接器配置 |
| `sources` | 数据源配置 |
| `sinks` | 数据汇配置 |
| `wpl` | WPL 规则语法 |
| `oml` | OML 模型语法 |
| `all` | 全部检查（默认） |

**示例：**

```bash
# 全面检查
wproj check

# 仅检查规则，首次失败即退出
wproj check --what wpl --fail-fast

# JSON 输出
wproj check --json
```

### data - 数据管理

```bash
wproj data <SUBCOMMAND>

Subcommands:
  clean     清理本地输出文件
  stat      统计数据量和性能
  validate  验证数据分布和比例
```

**示例：**

```bash
# 清理输出数据
wproj data clean

# 统计数据量
wproj data stat

# 验证数据分布
wproj data validate
```

---

## wparse - 解析引擎

日志解析引擎，支持批处理和守护进程两种模式。

### 命令概览

```bash
wparse <COMMAND>

Commands:
  batch   批处理模式（读完即退）
  daemon  守护进程模式（常驻服务）
```

### 通用参数

| 参数 | 短选项 | 长选项 | 说明 |
|------|--------|--------|------|
| 解析线程数 | `-w` | `--parse-workers` | 并行解析线程 |
| 统计间隔 | - | `--stat` | 统计输出间隔（秒） |
| 打印统计 | `-p` | `--print_stat` | 周期打印统计信息 |
| 规则目录 | - | `--wpl` | WPL 规则目录覆盖 |

### batch - 批处理模式

读完数据源后自动退出，适合离线处理。

```bash
wparse batch [OPTIONS]

Options:
  -n <COUNT>           处理条数限制
  -w <WORKERS>         解析线程数
  --stat <SEC>         统计间隔（秒）
  -p                   打印统计信息
```

**示例：**

```bash
# 处理 3000 条，每 2 秒输出统计
wparse batch -n 3000 --stat 2 -p

# 多线程解析
wparse batch -w 4 --parse-workers 4
```

### daemon - 守护进程模式

常驻服务，适合生产环境。

```bash
wparse daemon [OPTIONS]

Options:
  --stat <SEC>         统计间隔（秒）
  -p                   打印统计信息
```

**示例：**

```bash
# 启动守护进程，每 5 秒输出统计
wparse daemon --stat 5 -p

# 自定义规则目录
wparse daemon --wpl /custom/rules
```

### 退出策略

| 模式 | 退出条件 |
|------|----------|
| batch | 数据源 EOF / Stop 指令 / 致命错误 |
| daemon | SIGTERM/SIGINT/SIGQUIT 信号 |

### 错误处理策略

| 错误类型 | 策略 | 说明 |
|----------|------|------|
| EOF | Terminate | 优雅结束当前源 |
| 断线/可重试 | FixRetry | 指数退避后继续 |
| 数据/业务可容忍 | Tolerant | 记录后继续 |
| 致命错误 | Throw | 触发全局停机 |

---

## wpgen - 数据生成器

基于 WPL 规则或样本文件生成测试数据。

### 命令概览

```bash
wpgen <COMMAND>

Commands:
  rule    基于规则生成数据
  sample  基于样本文件生成数据
  conf    配置管理
  data    数据管理
```

### sample - 基于样本生成

```bash
wpgen sample [OPTIONS]

Options:
  -n <COUNT>           总生成条数
  -s <SPEED>           生成速度（行/秒）
  --stat <SEC>         统计间隔（秒）
  -p                   打印统计信息
```

**示例：**

```bash
# 生成 10000 条数据
wpgen sample -n 10000 -p

# 生成 50000 条，速度 5000 行/秒
wpgen sample -n 50000 -s 5000 --stat 5 -p
```

### rule - 基于规则生成

```bash
wpgen rule [OPTIONS]

Options:
  --wpl <DIR>          WPL 规则目录
  -c <CONF>            配置文件名
  -n <COUNT>           总生成条数
  -s <SPEED>           生成速度（行/秒）
  --stat <SEC>         统计间隔（秒）
  -p                   打印统计信息
```

**示例：**

```bash
# 基于规则生成
wpgen rule --wpl nginx -c custom.toml -s 1000 --stat 2 -p
```

### conf - 配置管理

```bash
wpgen conf <SUBCOMMAND>

Subcommands:
  init   初始化生成器配置
  clean  清理生成器配置
  check  检查配置有效性
```

**示例：**

```bash
# 初始化配置
wpgen conf init -w .

# 检查配置
wpgen conf check -w .
```

### data - 数据管理

```bash
wpgen data <SUBCOMMAND>

Subcommands:
  clean  清理已生成输出数据
```

**示例：**

```bash
# 清理生成的数据
wpgen data clean -c wpgen.toml
```

### 配置文件

默认路径：`conf/wpgen.toml`

```toml
[generator]
count = 10000      # 总生成条数
speed = 1000       # 生成速度（行/秒），0 表示无限制
parallel = 4       # 并行 worker 数

[output]
# 输出配置...
```

---

## 典型工作流程

### 本地开发验证

```bash
# 1. 初始化项目
wproj init -m full

# 2. 检查配置
wproj check

# 3. 生成测试数据
wpgen sample -n 3000 -p

# 4. 运行解析
wparse batch --stat 2 -p

# 5. 查看结果
wproj data stat
```

### 清理重来

```bash
# 清理所有输出
wproj data clean
wpgen data clean

# 重新开始
wpgen sample -n 1000 -p
wparse batch -p
wproj data stat
```

### 问题排查

```bash
# 检查项目配置
wproj check --json --only-fail

# 检查规则语法
wproj check --what wpl

# 查看统计
wproj data stat
```

---

## 相关文档

- `docs-zh/10-user/01-cli/02-wproj.md`
- `docs-zh/10-user/01-cli/03-wparse.md`
- `docs-zh/10-user/01-cli/04-wpgen.md`