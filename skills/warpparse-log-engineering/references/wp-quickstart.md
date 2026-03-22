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