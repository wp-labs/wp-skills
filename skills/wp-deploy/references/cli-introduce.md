# CLI工具介绍

## 安装
- 下载
```bash
# 下面的beta可以替换成alpha、stable或具体版本号
curl -sSf https://get.warpparse.ai/inst-x.sh | bash -s -- wparse beta
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
```
如果能正确输出版本号，说明安装成功。

## 卸载
```bash
which wparse wpgen wproj | xargs rm -f
```
这条命令会找到 `wparse`、`wpgen` 和 `wproj` 的安装路径并删除它们的可执行文件。

## wparse CLI介绍

查看帮助：

```bash
wparse --help
```

启动常驻实例：

```bash
wparse daemon --work-root .
```

执行批处理：

```bash
wparse batch --work-root .
```

### 常用参数

- `--work-root`：工程根目录
- `-n, --max-line`：限制本次最多处理的行数
- `-w, --parse-workers`：指定解析 worker 数
- `--stat`：设置统计输出周期
- `-p, --print_stat`：打印统计信息
- `--robust`：设置异常处理策略
- `--log-profile`：覆盖日志配置
- `--wpl`：临时覆盖 WPL 规则目录

## wpgen CLI介绍
请参考 [wpgen CLI介绍](./wpgen.md)

## wproj CLI介绍
查看帮助
```bash
wproj --help
```

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