# WarpParse 技能包

本仓库提供 WarpParse 项目使用的 AI skills，帮助用户配置处理链路、编写 WPL 解析规则和 OML 富化模型，并验证运行结果。

## 技能能力

### `wp-deploy`：工程配置、部署和观测

- 初始化 WarpParse 工程，配置 source、sink、connector 和 topology。
- 使用 `wpgen` 生成或回放测试数据。
- 配置 `wp-monitor` 和观测链路，检查解析成功、miss 和 sink 输出。
- 协助排查工程配置与运行问题。

### `wpl-rule-check`：WPL/OML 规则生成、审计和验证

- 根据用户提供的原始日志生成 WPL 规则和 OML 模型。
- 用户提供产品原始文档时，结合字段说明和枚举建模。
- 用户没有提供字段说明时，根据字段名、JSON 类型、样本值和字段关系推断；在交付结果中标记关键假设并继续生成，不要求额外准备厂商字段描述资料。
- 审计已有 WPL 的 rule 路由、捕获字段和运行时类型，并检查 OML 是否消费字段。
- 按 SDM 2.0 行为信封生成 `meta`、`behavior`、`subject/object`、`carriers`、`facets`、`observation` 和 `extensions`。
- 对已有规则保持确定性：用户要求和原规则一致时，以项目中的 WPL/OML 为基准逐字节比对；重复生成的文件也必须一致。
- 通过 package 级门禁验证 WPL/OML、行为 Schema、富化、业务/raw 双路输出和 Doris 物理投影。

该 skill 不附带厂商源字段描述文档。来源字段说明由用户按需提供；没有说明时，skill 根据样本推断并注明不确定项。缺少原始文档本身不会阻止生成。

## WPL/OML 生成流程

1. **读取输入**：使用用户提供的一条或多条原始日志。产品文档可选；如果用户提供，则一并读取字段定义、枚举和业务说明。
2. **检查项目**：在 WarpParse 项目中查看 package、已有 `parse.wpl`、对应 `adm.oml` 和当前 source 配置，确定目标 rule 与 `log_type`。
3. **分析字段**：有字段文档时按文档和样本核对；没有字段说明时，从字段名、JSON 类型、值域及字段之间的关系推断类型和用途，并将关键假设与置信度写入结果。
4. **生成 WPL**：按稳定路由生成 rule，捕获样本中需要消费或保留的字段；为业务 rule 保留 raw 旁路。
5. **解析复核**：本地 debug parse 按样本逐条运行，核对命中 rule、捕获字段、字段值和运行时类型。发现漏字段时先补 WPL。
6. **生成 OML**：将字段归一化后映射到 SDM 2.0 行为信封，按证据生成行为语义、实体、断言、facet、富化和私有扩展。没有足够结果证据时不伪造结论。
7. **确定性比对**：同一输入重复生成两次并比较文件字节；目标 rule 已存在且要求一致时，再与项目原 WPL/OML 比对。比较结果和基准 SHA-256 一并报告。
8. **运行验证**：在可用的 WarpParse 项目中执行一次 package 级门禁，并报告 `OK`、`FAIL`、`NEEDS_INPUT` 或 `NOT_RUN`。

## WPL/OML 校验步骤

在目标 WarpParse 项目根目录运行：

```bash
python3 .agents/skills/wpl-rule-check/scripts/check_pipeline.py \
  --package <package> \
  --sample data/in_dat/<package>/<sample>.dat \
  --source-file <package>/<sample>.dat \
  --clear-output --run-batch
```

如果样本是用户在对话中粘贴的，先将原始行临时保存到 `data/in_dat/<package>/`。`--source-file` 的路径相对于 `data/in_dat/`；验证完成后清理临时副本。

门禁会执行 `wpadm check`、逐条 debug parse 和一次 `wparse batch`，并检查：

- WPL/OML 静态结构及 package/rule 路由；
- 样本行数、命中 rule、捕获字段、字段值和运行时类型；
- WPL 捕获字段是否被对应 OML 消费或保留；
- SDM 行为信封 Schema、枚举、实体标识和时间戳；
- 业务输出与 raw 输出数量，以及输出和输入样本的关联；
- `sdm2_log.sdm_event_behavior` 的 Doris 列投影和 Routine Load 契约；
- `git diff --check`。

`--clear-output` 会清空 `data/out_dat/all.json` 和 `data/out_dat/raw_log.json`，运行后保留本轮结果。若要在验证结束后恢复之前的输出文件，可增加 `--restore-output`。脚本会恢复 source 配置。解析服务或富化服务不可用时如实标记 `NOT_RUN`，不伪造验证结果。

| 状态 | 含义 |
| --- | --- |
| `OK` | 可运行的阻断检查全部通过 |
| `FAIL` | 规则、Schema、字段覆盖、输出数量或物理投影存在错误 |
| `NEEDS_INPUT` | 缺少原始样本，或样本和现有规则不足以判断必需路由/语义 |
| `NOT_RUN` | 运行时、解析服务或富化服务不可用，相关检查没有执行 |

在没有 WarpParse 工程或运行时的情况下，skill 仍可根据输入生成候选文件和说明；需要将未执行的项目级门禁明确标记为 `NOT_RUN`。

## 快速安装

```bash
curl -sSf https://get.warpparse.ai/inst-x.sh | bash -s -- wp-skills
```

从本地仓库安装：

```bash
git clone https://github.com/wp-labs/wp-skills.git
cd wp-skills

# 安装全部 skills
bash install-skill.sh

# 只安装规则编写 skill
bash install-skill.sh wpl-rule-check

# 安装到 Zed/Agent skills 目录
bash install-skill.sh --agents
```

默认自动检测 `~/.codex/skills`、`~/.claude/skills` 和 `~/.agents/skills`。`--codex` 安装到 `$CODEX_HOME/skills`（未设置 `CODEX_HOME` 时为 `~/.codex/skills`），也可用 `--claude`、`--agents`、`--all` 或 `--dir <path>` 指定安装位置。

## 工具依赖

| 工具 | 用途 |
| --- | --- |
| `wproj` | 初始化和管理 WarpParse 工程 |
| `wpadm` | 检查工程配置以及 WPL/OML 模型 |
| `wparse` | 逐条 debug parse 和 batch 运行 |
| `wpgen` | 生成样本、回放或注入测试数据 |
| `wp-monitor` | 查看 source、解析、miss 和 sink 状态 |

完整 WPL/OML 验证使用 `wpadm` 与 `wparse` 的 package 门禁。独立离线检查器 `wpl-check` 不替代该门禁。

## WarpParse 工程配置

新建工程时使用 `wproj` 生成标准配置：

```bash
wproj init --work-root .
wproj check --work-root . --what all --fail-fast
```

从已有远程工程初始化或同步配置：

```bash
wproj init --work-root . --repo <repo-url> --version <version>
wproj conf update --work-root . --group models --version <version>
wproj check --work-root . --what all --fail-fast
```

配置完成后可用 `wpgen` 回放测试数据：

```bash
wpgen conf check --work-root "$(pwd)"
wpgen sample --work-root "$(pwd)" -n 10000 -s 1000 --stat 3 -p
```

观测部署可使用 `warp-parse`、VictoriaMetrics、VictoriaLogs 和 `wp-monitor`。部署后检查容器状态和健康地址，并在 `wp-monitor` 页面确认 source 输入、解析成功/error、miss 和 sink 输出。

## 安装配置

- `WP_SKILLS_REF`：安装的分支或标签，默认 `main`。
- `WP_SKILLS_PLATFORM`：安装目标 `codex`、`claude-code`、`agents` 或 `auto`，默认 `auto`。
- `CODEX_HOME`：Codex 主目录；设置后 `--codex` 会安装到 `$CODEX_HOME/skills`。

## 发布

仓库发行版本记录在 `version.txt`。发布时更新版本号，提交到 `main`，创建对应的 `v<version>` 标签并推送；GitHub Actions 会检查标签和文件中的版本是否一致并创建 Release。

## 贡献

新增或更新 skill 时，维护对应的 `SKILL.md`、`skill.json`、`agents/openai.yaml`、规范参考资料和验证脚本，并同步更新本 README 中的能力与使用说明。

## 许可证

MIT
