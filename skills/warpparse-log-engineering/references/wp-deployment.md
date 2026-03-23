# WP 初始化、运行与部署

当用户问“怎么把 WarpParse 跑起来”、“怎么纳入工程”、“怎么 rollout”时，看这个文件。

这里优先给工程起步与部署框架，不虚构超出文档范围的控制面能力。

## 先给最短跑通路径

根据 `beginner_guide.md` 与 `docs-zh/10-user/01-cli/*.md`，最小起步路径是：

1. 安装 WarpParse 工具
2. 初始化工程目录
3. 生成样本数据
4. 跑通批处理解析
5. 用 `wproj data stat` 看结果

## 已知安装与拉起方式

安装脚本：

```bash
curl -sSf https://get.warpparse.ai/setup.sh | bash
```

也可参考：

- GitHub release
- Docker 镜像：`ghcr.io/wp-labs/warp-parse:latest`

Docker 只在用户明确需要容器方式时再展开。不要默认把 Docker 当成唯一部署方式。

## 工程初始化

推荐先建立独立工作目录，再初始化完整工程：

```bash
mkdir ${HOME}/wp-space
cd ${HOME}/wp-space
wproj init -m full
wproj check
```

初始化后通常包含这些目录：

- `conf/`
- `connectors/`
- `data/`
- `models/knowledge`
- `models/oml`
- `models/wpl`
- `topology/`

## 本地验证路径

在还没接真实链路前，优先使用本地文件闭环：

```bash
wproj data clean
wpgen data clean
wpgen sample -n 3000 --stat 3
wparse batch --stat 3 -p
wproj data stat
```

这个闭环适合：

- 验证工程目录是否完整
- 验证 source/sink/wpl 配置是否基本可跑
- 先看产出和统计，再接外部数据源

## 把自定义日志纳入工程

按 `beginner_guide.md` 的约定，可先把一类自定义日志放到：

- 样本：`models/wpl/<name>/sample.dat`
- 规则：`models/wpl/<name>/parse.wpl`

如果任务已经进入“如何写 `parse.wpl`”，转到 `references/wpl-authoring-routing.md`。

## 从规则到运行时的最小模板

不要把“规则能写出来”误判成“工程已经接线完成”。最小运行时模板至少包含：

1. `models/wpl/<name>/parse.wpl`
2. `models/wpl/<name>/sample.dat`
3. `models/oml/<name>.oml`
4. `topology/sources/wpsrc.toml`

如果缺少 OML 或 source/sink 路由，即使 `wpl-check` 和 `wproj check` 通过，批量数据仍可能全部落到 `miss.dat`。

推荐最小验证命令：

```bash
wproj check
wproj data clean
cp models/wpl/<name>/sample.dat data/in_dat/<name>.dat
wparse batch
wproj data stat
sed -n '1,50p' data/out_dat/miss.dat
sed -n '1,50p' data/out_dat/error.dat
```

## rollout 设计

把部署看成一个分阶段过程，而不是“规则写完就上线”：

1. 先选一类代表性日志
2. 准备样本集和预期字段
3. 本地跑通工程闭环
4. 在非阻塞链路或影子链路上验证
5. 观察解析成功率、产出质量、错误数据去向
6. 再逐步扩大范围

## 排障入口

优先使用文档已有手段：

- `wproj check`
- `wproj data stat`
- `wproj sinks validate|list|route`
- `wproj sources list|route`
- 查看 `conf/wparse.toml`
- 查看 `data/logs/` 下运行日志
- 检查 `models/wpl/<name>/parse.wpl` / `sample.dat` 是否位于目录化路径
- 检查 `models/oml/` 与 `topology/sources/` 是否已经补齐

参考文档：

- `docs-zh/10-user/01-cli/01-getting_started.md`
- `docs-zh/10-user/01-cli/02-wproj.md`
- `docs-zh/10-user/01-cli/03-wparse.md`
- `docs-zh/10-user/01-cli/04-wpgen.md`
- `docs-zh/10-user/09-FQA/troubleshooting.md`

## 交付物

一个合格的部署回答，最后至少要给出其中一种：

- 从安装到跑通的最短命令序列
- 当前环境的 rollout 清单
- 缺失信息列表，例如 source/sink 类型、拓扑位置、目标输出端
