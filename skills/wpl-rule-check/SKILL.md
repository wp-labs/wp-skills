---
name: wpl-rule-check
description: 仅当请求涉及 WPL、OML、parse.wpl、WarpParse 或日志模型时使用。以用户提供的原始日志为输入，原始文档可选；缺少字段说明时按字段名、值和上下文推断后生成，并用 package 级门禁验证新 SDM 行为信封与 raw 双路输出。
---

# WPL/OML 规则技能

本技能只使用 SDM 行为事件物理载荷标准：`meta`、`event_kind=behavior`、`behavior`、`subject/object`、`carriers`、可选 `facets`、`observation`、`extensions`。旧平面字段（`roles_obj`、`facets_obj`、`source_finding_obj`、`extensions_obj`）、旧投影和旧 `interim-doris-v1` 校验不再作为生成或验证依据。

## 入口与资料

用户提供的原始日志是生成 WPL/OML 的主要输入；字段说明文档不是前置条件。先盘点并报告：

1. 用户提供的原始日志；未直接提供时，检查 `data/in_dat/<package>/gen.dat`。如用户在对话中粘贴样本且要运行 batch，将样本原文临时保存到 `data/in_dat/<package>/` 下供 source 读取；验证后清理临时副本；
2. 用户提供的产品原始文档（可选）；只使用本次提供或目标项目中明确存在的文档，不依赖本 skill 内置厂商字段说明；
3. 目标 package 的 `models/wpl/<package>/parse.wpl`、`models/oml/<package>/**/adm.oml` 和 `topology/sources/wpsrc.toml`（仅当需要在 WarpParse 项目中落盘或运行门禁时）；
4. 本 skill 随附的 SDM 标准资料：`references/new-standard.md`、`references/migration-sdm-event-behavior.md`、`references/workflow.md`、`references/wpl-oml-syntax.md`、`references/schemas/` 和 `references/contracts/`。

没有原始文档字段说明时，不因此停止或只要求用户补文档。根据字段名、JSON 类型、样本值、同一记录中字段的关联、已有 WPL/OML 和明确的 `log_type` 推断字段类型与业务含义；在结果中列出关键推断和置信度。不得把推断写成来源文档已确认的事实。缺少某一字段的业务结果证据时，仍生成规则；在标准允许的范围内使用 `unknown`，对无法安全推导的必需语义标记 `NEEDS_INPUT`。

## 场景路由

- **文档和样本建模**：使用用户提供的原始文档（若有）和样本生成 WPL，再生成新行为信封 OML。
- **只有样本**：按字段名、值和上下文推断字段类型与候选语义，标记推断后继续生成 WPL/OML。
- **已有规则审计**：先解析样本取得实际命中 rule、字段名、值和运行时类型，再检查 OML 是否消费、投影和富化是否完整。
- **OML 缺失/不合规**：先修正 WPL 的字段捕获和路由，再重建 OML；不在 OML 中猜读不存在的字段。
- **规范变更复核**：全仓搜索旧字段、旧枚举和旧 outcome 赋值，删除旧路径后只跑一次 package 门禁。

## I–N 证据链（不可跳过）

流程图中的 `I–N` 是生成 OML 前的事实来源：

1. **I/J：规则存在性与路由**：确认目标 WPL rule 与 `log_type` 唯一对应；不能用通配符或猜测规则代替。
2. **K：解析调用**：本地 `127.0.0.1` debug parse 的 `logs` 参数只接受单条原始日志；必须按输入文件的非空行逐条调用（可使用脚本内有界并发），不能把 NDJSON/多行样本拼成一次请求。本地不可用且用户允许时才调用远程服务；均不可用则标记 `NOT_RUN`。
3. **L/M：命中证据**：保存命中 rule、全部捕获字段、样本值和运行时类型；解析服务不可用时不得声称字段完整。
4. **N：OML 覆盖审计**：以单个 WPL rule 及其精确对应的 OML 为边界，逐项比对捕获字段与标准消费/私有保留，报告遗漏、重复消费、类型不符和无证据赋值；禁止用 package 字段并集相互抵消缺口。

样本足够时，即使解析服务不可用也可以生成候选 WPL/OML；将运行时字段证据标记为 `NOT_RUN`，不得声称已验证字段完整。已有 WPL/OML 时必须完成这条证据链，才能判定是否漏字段。

## 新 OML 口径

- 先定义唯一 `__` 临时归一化值，再让 `meta`、对象和 observation 复用；同一来源字段不得反复推导。
- `__` 不是隐藏旧字段的手段：每个临时值必须至少被一个后续标准对象、富化查询、方向计算或辅助投影真实消费；重复定义应删除，只有读取但没有消费者必须 `FAIL`。
- `meta.mapping_id` 直接写入稳定常量；禁止再定义或读取 `__mapping_id` 临时变量。
- 顶层保留五个兼容投影字段 `attacker_entity`、`victim_entity`、`attacker_ip`、`victim_ip`、`occur_time`；顶层 `event_id` 禁止输出。事件标识仍写入 `meta.event_id`，业务时间同时写入 `meta.occur_time` 和兼容字段 `occur_time`；攻击者和受害者实体写入标准对象及 `observation.assertion.attacker[]`、`observation.assertion.victim[]`。
- 上述四个顶层兼容字段必须逐条输出，缺值时为 `chars("")`。对每个 WPL rule 先核对实际捕获字段，再追溯 OML 中 `__sip`、`__dip`、`__attacker_ip`、`__victim_ip` 等标准投影变量读取的**原始字段**；不能假定所有日志都叫 `src_ip`、`dest_ip`，也不能用这些带 `ip` 类型的临时变量给顶层兼容字段赋值。按本条日志实际存在的来源字段依次取值：`attacker_entity` 为攻击者 IP → 攻击者 host → 源 IP → 源 host → 空字符串；`victim_entity` 为受害者 IP → 受害者 host → 目的 IP → 目的 host → 空字符串；`attacker_ip` 为攻击者 IP → 源 IP → 空字符串；`victim_ip` 为受害者 IP → 目的 IP → 空字符串。每级用 `match read(原始字段) { is_empty() => 下一级或 chars(""); _ => read(原始字段); }` 处理空值，不依赖 `read(option:[...])` 判断空字符串。该兼容赋值与下文四类 IP 到标准对象、断言和富化的投影相互独立。
- 业务 `occur_time` 必须来自原始时间并转为 Unix 毫秒；`ingest_time/parse_time` 才能使用 `Now::time()`。
- `behavior.outcome` 只能由来源结果/动作证据推导。优先使用用户提供文档；没有字段说明时结合字段名、枚举值和样本值推断，并标注推断。来源 action 保留原值，不能直接复制成外层 outcome；没有足够结果证据时用 `unknown` 或报告 `NEEDS_INPUT`。
- `event_kind` 当前唯一值为 `behavior`；`observation` 是行为事件的附属判断，不独立成事件，`state` 暂不启用。`behavior.layer` 按实际观测层次取 `network/system/application`，`behavior.type` 按官网五类闭集取 `appear/read/change/disappear/flow`，`behavior.operation` 是归属该五类的具体开放动作，`behavior.message` 只描述事实。`read` 表示原地访问，`flow` 表示跨边界或改变位置；结果按处置段 `allowed/denied`、执行段 `success/failed`、记录段 `observed/unknown` 三段语义选择，不能混用。
- `category_code`、`category`、`confidence`、`default_alert_name` 是旧 `source_finding` 分类映射字段，不是 SDM2 行为或实体字段，因此新规范未明确要求时不查询或输出它们。行为语义优先依据用户提供的原始文档；文档未提供字段说明时，使用字段名、样本值和字段关联推断 `behavior.layer/type/operation`，并记录假设。若目标项目本身有精确 `log_type` 对应的 `models/knowledge/alert_cat_level/data.csv`，可作为可选补充证据；不得依赖该文件或 skill 内置厂商资料。分类标签只能约束候选语义，不能单独决定行为类型或 outcome。`entity_type` 可由用户给出的日志标题/说明推断，也可依据 `file_path`/哈希、终端地址、进程名称/路径等字段推断；具体属性用于补充实体详情和富化。`default_alert_name` 只能作为内部标题回退，不输出为断言字段。
- `references/contracts/event_operation_dictionary.json` 的版本字段只表示字典自身版本，不是事件 `meta.schema_version`；事件信封固定使用字符串 `"2.0"`。
- `data_source.category` 按官网闭集使用 `auth`、`network`、`audit`、`system`、`alert`、`other`；先根据用户提供的文档，若没有则依据字段名和样本模式推断。仍无法判断时报告 `NEEDS_INPUT`，不能伪称已确认。
- UDP/TCP 接入层提供的上报设备地址统一命名为 `device_ip`，OML 先归一化为 `__device_ip`，再写入 `meta.data_source.instance_id`；值必须是纯 IP，不加 `collector` 前缀。它表示传输来源，不得写入 `subject/object`、`attacker_ip`、`victim_ip` 或 `observation.observer`。原始日志中的 `dev_ip` 只有在文档确认其同为上报设备地址时才能复用；不能用 `sip`/`dip` 代替。
- `subject/object` 是实体角色，未知用 `null`；`ref_id` 必须稳定、非空、带实体类型前缀，允许来源路径、GUID 或哈希，不强制 OML 计算 SHA-256。
- 禁止用 `event_id`、`wp_event_id`、`log_id` 或批内序号充当实体 `ref_id`；实体来源值缺失时使用稳定的设备/产品身份兜底，不能让同一实体随事件变化。
  - `observation.assertion` 表示来源侧检测/告警结论；普通流量、访问、审计事件不得仅因存在 severity 或规则字段而制造告警断言。
- 官网当前机器目录已登记 `facets.network.direction`、`facets.network.source_zone`、`facets.network.target_zone`、`facets.network.session_id` 和 `facets.network.nat.original/translated.*`；`facets.network.session.start_time/end_time/duration_seconds`、`facets.network.traffic.request_*/response_*` 尚未登记，不能直接作为标准输出。认证会话可使用已登记的 `facets.authentication.session.start_time/end_time`、`auth_result`、`auth_failure_reason` 和 `session_id`；不要把认证会话字段跨到网络会话。攻击方向使用已登记的 `observation.assertion.attack_direction`，不能写回 `facets.network.direction`。
- 四类 IP 使用固定投影，不再按日志类型或其他 file/process/resource 实体临时裁决：
  - 只有 `attacker_ip/victim_ip` 时：attacker 固定写入 `subject.endpoint` 和告警的 `observation.assertion.attacker[].endpoint`；victim 固定写入 `object.endpoint` 和告警的 `observation.assertion.victim[].endpoint`。两处相同角色必须复用同一 IP、GeoIP、资产和 `ref_id`。
  - 同时存在 `sip/dip/attacker_ip/victim_ip` 时：`subject.endpoint` 固定承载 sip，`object.endpoint` 固定承载 dip；告警的 assertion attacker/victim 分别固定承载 attacker_ip/victim_ip。各自 GeoIP 与资产必须跟随对应 IP，禁止交叉复用。
  - 只有 `sip/dip` 时：sip 写入 `subject.endpoint`，dip 写入 `object.endpoint`；没有来源攻击判断时不制造 assertion attacker/victim。
  - `carriers` 禁止承载 sip、dip、attacker_ip、victim_ip 及其 GeoIP/资产；它只表达父进程、脚本引擎等真实承载关系。file/process/resource 也不得抢占上述已确定的四类 IP 主客体位置，需要保留时使用标准 facet、assertion 证据字段或有明确关系的 carrier。
- 只对语义可判断为通信或攻防地址的 IP 查询 GeoIP；有用户文档时按文档判断，没有时依据字段名和值推断并标记。GeoIP 写入上述固定角色对应的 `endpoint.geo`；可输出 `continent_name`、`country_code`、`country`、`province`、`city`、`latitude`、`longitude`，无值时不应伪造值或空对象。官网当前没有 `endpoint.resource`，资产归属需要平铺到 `endpoint.asset_id`、`endpoint.asset_name`、`endpoint.asset_type`、`endpoint.system.{id,name}` 和 `endpoint.organization.{id,name}`；`asset_id` 不参与 endpoint `ref_id`，且应与同一资产在 host/device 上的编号一致；`asset_name` 不等同于 `host.name`；`asset_type` 是资产系统来源归一值，判定出实体后才按需归一到 `device.type` 或 `resource.kind`；`system_id/system_name` 对应 system，明确的组织/部门 ID/name 对应 organization。相关终端资产快照才评估 `extensions.profiles.endpoint_asset`。查询输出变量未被最终对象消费直接 `FAIL`。
- 所有用于 GeoIP 数值查询的 `ip_to_biguint` 管线必须先执行 `intranet_replace("202.106.0.0")`，再转换数字；原始 IP 仍用于事件对象、资产查询和方向计算。不得直接对未脱敏内网 IP 执行 `ip_to_biguint`。
- 方向字段按成对角色计算：同时存在 `sip` 与 `dip` 时必须使用 `access_direct(@__sip,@__dip)|on_fail('unknown')` 输出 `facets.network.direction`；同时存在 `attacker_ip` 与 `victim_ip` 时必须使用对应两端输出 `observation.assertion.attack_direction`。两者语义不同，不能互相复制；只有单端 IP 时不能伪造方向或用另一组角色替代。
- `extensions.source_private` 只放原始字段中没有被 `meta`、`behavior`、`subject/object`、`facets` 或 `observation` 消费的字段；已用于 `occur_time`、`outcome`、对象、断言等标准投影的字段不得重复放入。空值是否输出不作为本门禁条件；普通读取直接 `read`，不要为了过滤空值批量添加 `skip_empty`。

## 资料来源边界

来源业务语义优先读取用户提供的原始文档；未提供字段说明时，以样本字段名、JSON 类型、值域和字段关联进行推断，并在报告中标记关键假设。若目标项目存在精确 `log_type` 的知识库记录，可作为可选补充证据，但不要求项目提供该知识库。本 skill 不捆绑厂商源字段说明。SDM 结构与枚举以本目录的 `contracts/` 和 `schemas/` 为准。

## 唯一验证入口

```bash
python3 .agents/skills/wpl-rule-check/scripts/check_pipeline.py \
  --package <package> \
  --sample data/in_dat/<package>/<sample>.dat \
  --source-file <package>/<sample>.dat \
  --clear-output --run-batch
```

`check_pipeline.py` 只启动一次全局 `wpadm check` 和一次 `wparse batch`，在同一进程完成 WPL/OML 静态检查、I–N 证据检查、all/raw 数量与原文相关性、新行为 Schema、枚举、ref_id、时间戳、Doris 物理投影和 diff 门禁。Doris 只校验 `sdm2_log.sdm_event_behavior`：逐条模拟当前 Routine Load 的 JSONPath 投影，检查必填列、VARCHAR 长度、秒/毫秒到 `DATETIME(3)` 的可转换性和 VARIANT 载荷；禁止再校验或引用旧 `sdm_event`。它只修改 source 的 `file` 参数指向样本；`--clear-output` 清空 `data/out_dat/all.json`、`raw_log.json` 后保留本轮结果供核对。

数量门禁按 `业务输出 + ignore 规则族命中 = 输入`、`raw = 业务输出` 校验；`ignore`、`ignore_v2`、`ignore_other` 等明确忽略路由不应被误报为解析丢失。

## 可复现生成与原规则一致性

- 同一套来源文档、样本和目标规则必须生成逐字节一致的 WPL/OML 文件。生成过程不得依赖当前时间、随机 ID、目录遍历顺序或模型的临时输出顺序；不要自动重排字段、规则、注释或格式。
- 目标规则已存在时，`models/wpl/<package>/parse.wpl` 和对应的 `models/oml/<package>/<rule>/adm.oml` 是权威基准。用户要求与原规则一致时，保留原文件内容；新生成的候选文件必须分别与基准文件 `cmp` 通过后才能交付。
- 字节一致只证明候选与基准相同，不代表基准符合当前规范。package 门禁失败时同时报告一致性结果和具体失败项，不得把旧模型称为通过；未经用户要求，不擅自改写权威基准。
- 重复生成验证要在两个独立临时目录中使用相同输入，分别保存 WPL 和 OML，再对两组文件运行 `cmp`。任何差异都算 `FAIL`；定位差异后修正生成约束并重跑，不能挑选其中一份作为结果。
- 新建规则时，WPL 字段顺序沿用来源文档定义顺序；文档没有顺序时沿用样本 JSON 键顺序。OML 按本 skill 规定的归一化、时间、富化、标准信封、扩展字段顺序输出。不得加入随机标识或生成时间。
- 运行时 `ingest_time`、`parse_time` 按标准使用 `Now::time()`，因此不同批次的事件值会变化；这不改变 WPL/OML 文件可复现要求。业务 `occur_time` 始终由原始日志时间推导。
- 报告基准文件路径、SHA-256、逐字节比对和重复生成比对结果。发现原模型与当前规范冲突时，报告差异，不得静默改写原规则来伪造一致。

默认会对样本每个非空行调用本地 debug parse 获取 I–N 证据，并在报告中保留每行命中、字段、值和运行时类型摘要；只有明确使用 `--skip-parse` 才跳过并标记 `NOT_RUN`。远程解析必须显式加 `--allow-remote`。解析证据文件默认在报告后清理，需要人工留档时加 `--keep-evidence`。本 skill 不归档或维护厂商源字段说明。

门禁状态只有：`OK`、`FAIL`、`NEEDS_INPUT`、`NOT_RUN`。数据库无命中是合法空富化；数据库不可用不得伪造资产/地理值。

## 支持资料

- 总体流程和 I–N：[`references/workflow.md`](references/workflow.md)
- 新物理行为标准：[`references/new-standard.md`](references/new-standard.md)
- 官方逻辑字段与物理列目录：[`references/sdm2-log-standard-catalog.md`](references/sdm2-log-standard-catalog.md)
- 迁移摘要：[`references/migration-sdm-event-behavior.md`](references/migration-sdm-event-behavior.md)
- WPL/OML 语法与富化：[`references/wpl-oml-syntax.md`](references/wpl-oml-syntax.md)
- Kafka 物理行为 Schema：[`references/schemas/sdm-event-behavior-kafka.schema.json`](references/schemas/sdm-event-behavior-kafka.schema.json)
- 官方行为枚举/操作、行为表 DDL/Routine Load：[`references/contracts/`](references/contracts/)
- 可复现生成和权威原规则比对：[`references/deterministic-generation.md`](references/deterministic-generation.md)
