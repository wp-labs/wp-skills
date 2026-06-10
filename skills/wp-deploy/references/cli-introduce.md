# CLI工具介绍

## 安装
- 下载
```bash
# 下面的beta可以替换成alpha、stable或具体版本号
curl -sSf https://get.warpparse.ai/inst-x.sh | bash -s -- wparse beta
# 下载wpl-check，与其他几个工具不在同一个仓库，需要单独下载
curl -sSf https://get.warpparse.ai/inst-x.sh | bash -s -- wpl-check
```
执行命令后会自动下载并安装 `wparse`、`wpgen`、`wproj` 3个工具，并将它们的可执行文件放在 `~/bin/` 目录下。
- 设置环境变量：
    - 先验证这几个命令是否在环境变量中。
    - 不在则追加到 `~/.bashrc` 或 `~/.zshrc`。
    - 如果没有权限修改环境变量，可以在当前 shell 会话中临时添加：
    ```bash
    export PATH="$HOME/bin:$PATH"
    ```
- 验证安装：
```bash
wparse -V
wpgen -V
wproj -V
wpl-check -V
```
如果能正确输出版本号，说明安装成功。

### wpl-check 容器化验证资产

本地二进制是首选验证路径；如果需要容器化验证，通过环境变量明确镜像和版本：

```bash
export WPL_CHECK_VERSION="${WPL_CHECK_VERSION:-v0.2.0}"
export WPL_CHECK_IMAGE="${WPL_CHECK_IMAGE:-ghcr.io/wp-labs/wpl-check:${WPL_CHECK_VERSION}}"
docker pull "$WPL_CHECK_IMAGE"
```

容器化语法检查示例：

```bash
docker run --rm \
  --name wpl-check \
  -v "$(pwd):/work" \
  -w /work \
  "$WPL_CHECK_IMAGE" syntax models/wpl/<package>/parse.wpl
```

## 卸载

`wp-monitor` 已经是部署闭环的一部分，因此卸载 `wparse` 相关环境时，先停止部署组件，再删除本地二进制。默认保留数据卷、项目配置和镜像。

卸载前盘点：

```bash
which wparse wpgen wproj wpl-check || true
docker ps -a --filter "name=wp-monitor" --filter "name=victoria-metrics" --filter "name=victoria-logs" --filter "name=warp-parse" --filter "name=wpl-check"
docker images --format '{{.Repository}}:{{.Tag}}' | grep -E 'wpl-check|wp-labs/wpl-check' || true
docker compose ps 2>/dev/null || true
```

如果当前工程目录有 `docker-compose.yml`，优先停止 compose 栈：

```bash
docker compose down
```

如果没有 compose 文件，或容器是用固定名称启动的，按容器名停止并删除：

```bash
docker rm -f wp-monitor victoria-metrics victoria-logs warp-parse wpl-check 2>/dev/null || true
```

删除本地二进制：

```bash
for bin in wparse wpgen wproj wpl-check; do
  path="$(command -v "$bin" 2>/dev/null || true)"
  if [ -n "$path" ]; then
    rm -f "$path"
  fi
done
```

验证卸载结果：

```bash
command -v wparse wpgen wproj wpl-check || true
docker ps -a --filter "name=wp-monitor" --filter "name=victoria-metrics" --filter "name=victoria-logs" --filter "name=warp-parse" --filter "name=wpl-check"
```

彻底清理数据卷和镜像前必须确认用户明确要求删除数据：

```bash
docker compose down -v --rmi local
docker volume rm <metrics_volume> <logs_volume>
export WPL_CHECK_VERSION="${WPL_CHECK_VERSION:-v0.2.0}"
export WPL_CHECK_IMAGE="${WPL_CHECK_IMAGE:-ghcr.io/wp-labs/wpl-check:${WPL_CHECK_VERSION}}"
docker image rm ghcr.io/wp-labs/wp-monitor:latest victoriametrics/victoria-metrics:v1.133.0 victoriametrics/victoria-logs:v1.43.0 "$WPL_CHECK_IMAGE"
```

## wparse CLI介绍

查看帮助：

```bash
wparse --help
```

启动常驻实例：

```bash
wparse daemon --work-root "$(pwd)"
```

执行批处理：

```bash
wparse batch --work-root "$(pwd)"
```

### 常用参数

- `--work-root`：工程根目录；当前版本建议传绝对路径，例如 `"$(pwd)"`
- `-n, --max-line`：限制本次最多处理的行数
- `-w, --parse-workers`：指定解析 worker 数
- `--stat`：设置统计输出周期
- `-p, --print_stat`：打印统计信息
- `--robust`：设置异常处理策略
- `--log-profile`：覆盖日志配置
- `--wpl`：临时覆盖 WPL 规则目录

## wpgen CLI介绍
### CLI命令
格式
```bash
wpgen <COMMAND> [OPTIONS]
```
#### 常用命令
- rule   : Generate data by rule/基于规则生成数据
- sample : Generate data from sample files/基于`model/wpl`下的`sample.dat`样本文件生成数据。
- conf   : Configuration commands/配置相关命令

#### 常用参数
- --work-root：工作根目录
- --wpl：临时覆盖 WPL 目录
- -c, --conf-name：生成器配置文件名
- -n：覆盖总行数
- -s：覆盖生成速度
- -p, --print_stat：打印统计
- --stat：设置统计周期

#### conf子命令参数
- init  : Initialize generator config/初始化 `conf/wpgen.toml`
- clean : Clean generator config/清理生成器配置
- check : Check generator config/检查生成器配置

#### 标准验证命令

```bash
wpgen conf check --work-root "$(pwd)"
wpgen sample --work-root "$(pwd)" -n 10000 -s 1000 --stat 3 -p
```

生成部署或联调工作流时，测试数据发送必须走 `wpgen`。不要生成 Python / Node / Bash sender、`nc` 循环、`curl` 循环等临时脚本来替代 `wpgen`。

#### 示例
- 基于样本生成数据，生成10000行，每秒1000行，并3秒打印一次统计信息：
```bash
wpgen sample --work-root "$(pwd)" \
  -n 10000 \
  -s 1000 \
  --stat 3 \
  -p
```

### wpgen配置文件
请参考 [wpgen介绍](./wpgen.md)

## wproj CLI介绍
查看帮助
```bash
wproj --help
```

### 初始化和生成工程配置

新建或生成 WarpParse 工程配置时，先使用 `wproj` 建立配置基线，不要手工拼装 `conf/`、`connectors/`、`topology/`、`models/knowledge/` 等核心目录。

本地初始化：

```bash
wproj init --work-root .
```

指定初始化模式：

```bash
wproj init --work-root . --mode full
wproj init --work-root . --mode normal
wproj init --work-root . --mode model
wproj init --work-root . --mode conf
wproj init --work-root . --mode data
```

从远端项目源初始化，并固定目标版本：

```bash
wproj init --work-root . --repo <repo-url> --version <version>
```

初始化后立即检查：

```bash
wproj check --work-root . --what all --fail-fast
```
交付部署配置时，应记录实际执行过的 `wproj init`  命令，方便后续用同一命令再生成或升级配置。

### 批量检查工程
检查整个项目：
```bash
wproj check --work-root .
```
只检查 WPL：
```bash
wproj check --work-root . --what wpl --fail-fast
```
当前 `--what` 常见取值：
- `conf`
- `connectors`
- `sources`
- `sinks`
- `wpl`
- `oml`
- `all`

建议把 `wproj check` 作为上线前固定步骤，而不是出问题后再补执行。

### 查看模型拓扑

查看 source：
```bash
wproj model sources --work-root .
```
查看 sink：
```bash
wproj model sinks --work-root .
```
查看规则到 sink 的路由路径：
```bash
wproj model route --work-root .
```
按组过滤：
```bash
wproj model route \
  --work-root . \
  --group demo-group
```

这些命令适合在联调时回答几个直接问题：

- 当前启用了哪些 source
- 某个规则最终会流向哪些 sink
- OML 是否挂在了预期链路上

## wpl-check CLI介绍
### 常用命令

#### 语法检查

```bash
# 检查 WPL 语法
wpl-check syntax models/wpl/<package>/parse.wpl

# 检查 OML 语法（若工具支持）
wpl-check syntax models/oml/<name>.oml
```

#### 样本测试

```bash
# 运行样本测试
wpl-check sample models/wpl/<package>/parse.wpl models/wpl/<package>/sample.dat

# 详细输出（显示解析结果和失败原因）
wpl-check sample --verbose models/wpl/<package>/parse.wpl models/wpl/<package>/sample.dat

# JSON 格式输出（方便程序处理）
wpl-check sample --json models/wpl/<package>/parse.wpl models/wpl/<package>/sample.dat
```
