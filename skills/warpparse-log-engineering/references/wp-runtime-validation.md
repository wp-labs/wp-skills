# WP 工程目录约定与批量验证闭环

当用户已经进入“规则如何进入运行时”、“为什么离线通过但工程不生效”、“怎么做批量回归”时，看这个文件。

## 工程目录约定

工程化时优先使用目录化规则布局，不要把 `.wpl` 直接平铺在 `models/wpl/` 顶层。

推荐结构：

```text
models/wpl/<name>/parse.wpl
models/wpl/<name>/sample.dat
models/oml/<name>.oml
topology/sources/wpsrc.toml
```

关键约束：

- `wpl-check` 可直接校验任意路径上的 WPL 文件，但 `wparse` 运行时更依赖工程目录约定。
- `wproj check` 通过，只说明配置与语法基本可读；不说明 source、OML、sink 已经把数据接到目标规则。
- 工程化时优先让一个日志类型对应一个目录，减少“离线可用、工程不生效”的错觉。

## 从规则到运行时的最小接线

一个规则真正进入运行时，至少要同时接上 4 个工件：

1. WPL：解析结构定义，位于 `models/wpl/<name>/parse.wpl`
2. OML：把数据路由到目标 package/rule，位于 `models/oml/<name>.oml`
3. source：声明输入文件或连接器，通常位于 `topology/sources/wpsrc.toml`
4. sink：声明输出位置，确保解析结果不是全部落到 `miss.dat`

推荐最小验证顺序：

```bash
wpl-check syntax models/wpl/demo/parse.wpl
wpl-check sample models/wpl/demo/parse.wpl models/wpl/demo/sample.dat
wproj check
wproj data clean
cp models/wpl/demo/sample.dat data/in_dat/demo.dat
wparse batch
wproj data stat
sed -n '1,50p' data/out_dat/miss.dat
sed -n '1,50p' data/out_dat/error.dat
sed -n '1,50p' data/out_dat/demo.json
```

说明：

- `wpl-check sample` 只适合单样本调试。
- `wparse batch` 才是运行时闭环验证。
- `miss.dat` 和 `error.dat` 用来区分“未命中”和“运行失败”。
- 结果文件要同时看字段值，而不只是看命中率。

## 标准批量回归闭环

推荐把以下流程固定成默认验证路径：

```bash
wproj data clean
# 恢复测试输入
wparse batch
wproj data stat
sed -n '1,50p' data/out_dat/miss.dat
sed -n '1,50p' data/out_dat/error.dat
sed -n '1,50p' data/out_dat/demo.json
```

每一步的目的：

- `clean`：清理旧输出，避免把旧成功结果误当成新结果
- 恢复输入：某些工程布局里清理动作会带走输入文件，批量回归前需要重新拷贝样本
- `batch`：按运行时路径真正执行
- `stat`：快速看总量、命中量、成功率
- `miss/error`：查看失败样本
- `demo.json`：确认字段值、字段名、目标输出都正确

## `wpgen sample` 的工程化注意事项

当用户想用 `wpgen sample --wpl <dir>` 批量扩样时，提前说明这几个行为：

- 它会在 `<dir>` 下查找固定文件名 `sample.dat`
- 如果缺少 `sample.dat`，当前版本可能报 `[50041] configuration error << core config`
- 默认是追加写输出，不是覆盖写

因此推荐流程是：

```bash
wproj data clean
wpgen data clean
rm -f data/in_dat/demo.dat
wpgen sample --wpl models/wpl/demo -n 10000
wparse batch
wproj data stat
```

## 常见误判

### `wpl-check` 通过，但 `wparse batch` 不生效

优先检查：

- 规则是否位于 `models/wpl/<name>/parse.wpl`
- 样本是否位于 `models/wpl/<name>/sample.dat`
- 是否存在对应的 `models/oml/<name>.oml`
- `topology/sources/wpsrc.toml` 是否把数据送进目标规则
- sink 是否把结果输出到预期文件，而不是全部落到 `miss.dat`

### 批量结果与输入条数不一致

优先检查：

- `wpgen sample` 是否向旧文件追加了数据
- `wproj data clean` 后是否重新恢复了输入
- `data/out_dat/miss.dat` 和 `data/out_dat/error.dat` 是否已有失败样本
