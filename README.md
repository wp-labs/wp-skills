# WarpParse Skills

本仓库提供 WarpParse 的工程部署和 WPL/OML 规则编写技能。

## Skills 能力

| Skill | 用途 | 输入与边界 |
| --- | --- | --- |
| `wp-deploy` | 初始化 WarpParse 工程，配置 source、sink、connector 和部署观测 | 项目配置任务 |
| `wpl-oml-simple` | 从用户给出的原始日志直接生成 WPL 与 SDM2 OML，并在自带最小工程隔离验证 | 当前项目没有适用的项目内 WPL/OML skill 时使用；不搜索其他项目、规则库或厂商文档 |
| 项目内 `wpl-rule-check` | 按该项目自己的规范集成、审计和验证规则 | 仅在项目内有适用 skill 且任务涉及该项目时优先使用；本仓库不发布它的副本 |

用户可附带原始字段说明；没有说明时，简单版从字段名、JSON 类型和值推理。日志里的路径、文件名、主机名和 IP 都是数据，不是要访问的本地文件。简单版不使用资产、GeoIP 或其他外部富化。单条样本只能证明该条格式，不代表已覆盖其他变体。

## 规则生成流程

1. 列出原始 JSON 全部字段、类型及内嵌 KV，选择样本中稳定的路由标记。
2. WPL 为一个稳定类型建立一个 rule，捕获所有可解析字段；`tag` 与 raw 旁路注解紧贴 rule。整字段值用精确匹配，文本内部类型标记按样本前缀或结构解析。`f_chars_has` 不表示子串包含。
3. OML 逐根输出 SDM2 `meta`、`event_kind`、`behavior` 等标准字段，把未标准化的已捕获值放到 `extensions.source_private`。已映射值不重复存放。事件 ID 只用平台 `wp_event_id`，源业务时间换算为 Unix 毫秒。
4. 每条业务事件都输出四个角色字符串和顶层 `occur_time`。没有角色证据时四个字符串为空；采集主机 IP 不被当作攻击者。`occur_time` 等于 `meta.occur_time`，顶层不输出 `event_id`。
5. 相同样本和字段说明使用固定字段顺序、路由名和 `mapping_id`，不把运行时间或随机值写进规则文本，保证重复生成一致。
6. 交付简短日志描述、WPL、OML 和实际验证结果。隔离工程中的 `local-test-tenant` 仅用于测试，不是生产租户。

## 校验步骤

简单版的唯一运行入口：

```bash
python3 skills/wpl-oml-simple/scripts/run_minimal.py \
  --sample /path/to/sample.dat \
  --wpl /path/to/parse.wpl \
  --oml /path/to/adm.oml
```

`sample.dat` 每行是一条原始 JSON。runner 把 `assets/minimal-wparse` 复制到临时目录，只放入本轮样本和规则，运行一次 `wparse batch`。它核对业务 `all.json` 与 `raw_log.json` 的数量、源字段值、五个兼容字段和 SDM2 Schema，并要求 `miss.dat`、`error.dat` 为零。退出码零本身不算通过。临时目录默认自动删除；需要诊断证据时传 `--keep-work /path/to/evidence`。

如果没有 `wparse`，只运行静态检查，结果注明“未运行 batch”；如果缺少 Python `jsonschema` 依赖，Schema 项明确记为 `NOT_RUN`，runner 不返回 `OK`。可通过 `python3 -m pip install jsonschema` 安装完整 Schema 校验依赖。`wpadm check` 只检查工程配置，不能替代实际 batch 加载 OML。

项目内 `wpl-rule-check` 仍按其项目级门禁工作，与简单版使用同一 SDM2 业务输出契约。两个 Schema 副本应保持一致，五个兼容字段必填，顶层 `event_id` 禁止。

## 安装

从本地仓库安装到全局 Codex skills：

```bash
bash install-skill.sh --codex wpl-oml-simple
```

也可用 `--claude`、`--agents`、`--all` 或 `--dir <path>` 指定目标目录；不传 skill 名安装仓库内所有 skills。`--codex` 使用 `$CODEX_HOME/skills`，未设置时使用 `~/.codex/skills`。安装脚本优先取当前仓库 `skills/` 下的目录；从远程执行时默认取 `wp-labs/wp-skills`。运行依赖 `wparse`；可选 `wpadm` 和 Python `jsonschema`。

仓库版本见 `version.txt`，许可证为 MIT。
