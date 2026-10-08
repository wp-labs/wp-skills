# WPL/OML 新标准（SDM 行为事件物理载荷）

本技能只使用这一套规则。旧的 `interim-doris-v1` 平面字段、`roles_obj`、`facets_obj`、`source_finding_obj`、`extensions_obj` 和旧版投影不再作为生成或验证依据。

## 1. 物理载荷约定

业务输出是 SDM 行为事件信封，写入 Kafka/`all.json` 时：

- 顶层固定包含 `meta`、`event_kind`、`behavior`、`carriers`；按实际语义可增加 `subject`、`object`、`facets`、`observation`、`extensions`。事件标识和时间仅写入 `meta.event_id`、`meta.occur_time`，不得重复输出旧顶层辅助字段。
- `meta.schema_version` 固定使用字符串 `"2.0"`；`meta.tenant_id`、`event_id`、`mapping_id` 必填。
- `meta.occur_time`、`meta.ingest_time`、`meta.parse_time` 在 Kafka 物理消息中使用非负 Unix 毫秒整数；Routine Load 负责转换为 Doris `datetime(3)`。
- UDP/TCP 接入层提供的上报设备地址统一称为 `device_ip`：OML 用 `__device_ip` 归一化后写入 `meta.data_source.instance_id`，值为纯 IP，不加前缀。该地址是传输来源，不是行为 `subject/object`、`attacker_ip`、`victim_ip` 或 `observation.observer`；原始 `dev_ip` 仅在来源文档明确同义时才能作为输入。
- `event_id` 只使用平台 `wp_event_id`。`meta.source_record.log_id` 优先读取源 `id`，没有时回退 `wp_event_id`。
- `meta.occur_time` 使用 Unix 毫秒值，Doris 从该路径投影。
- raw 旁路独立输出到 `raw_log.json`，与每条业务事件一一对应；`raw_msg` 不复制进业务事件。

## 2. 行为信封

```text
meta
event_kind = behavior
behavior = { layer, type, operation?, outcome?, message? }
subject? / object?
carriers = []
facets? = { network?, process?, file?, authentication?, http?, ... }
observation? = { observation_id, observer, action, assertion?, evidence_refs }
extensions? = { source_private?, profiles?, enrichments? }
```

官网当前机器目录在 `facets.network` 中登记的是 `connection_result`、`protocol`、`direction`、`application_protocol`、`packet_metadata`、`session_id`、`source_zone`、`target_zone` 和 `nat.original/translated.*`。网络会话起止时间、持续时长及请求/响应流量统计尚未登记，不能直接输出为标准 facet，须先列为官网新增候选。认证类可使用已登记的 `facets.authentication.session.start_time/end_time`、`auth_result`、`auth_failure_reason` 和 `session_id`，不能因字段同名跨到网络会话。

`subject/object` 是实体引用对象；实体未知时使用 `null`，不能使用 `{}`。实体对象只能有一个与 `entity_type` 对应的 typed object（例如 `process` 对应 `process`）。

`ref_id` 只要求稳定、非空且带实体类型前缀（如 `process::...`、`endpoint::...`）。允许来源路径、厂商 GUID、哈希等稳定值；不强制 OML 计算 SHA-256，也不得把事件编号、批次序号或当前时间拼入实体身份。

Kafka Schema 中每个 `carriers[]` 项必须包含 `ref_id`、`entity_type` 和 `carrier_role`；没有承载者时使用空数组，不要为了满足格式制造载体。

攻击者和受害者只在来源存在检测判断时写入 `observation.assertion.attacker[]`、`observation.assertion.victim[]`。只有 attacker/victim 时，它们同时固定为 subject/object；四类 IP 同时存在时，subject/object 固定为 sip/dip，assertion attacker/victim 固定为 attacker/victim。四类 IP 及其富化禁止写入 carriers。普通行为事件不为满足结构而制造断言实体。

## 2.1 行为内容判定（官网口径）

`event_kind` 当前唯一写入值为 `behavior`。观察和告警判断依附于行为事件，写在 `observation`，不单独生成观察事件；`state` 暂不启用。

行为内容由 `behavior` 五个字段共同说明：

| 维度 | 字段 | 允许值/填法 | 判定依据 |
| --- | --- | --- | --- |
| 层次 | `behavior.layer` | `network` / `system` / `application` | 按实际观测层次判定，不按厂商或产品名称推断 |
| 行为类型 | `behavior.type` | `appear` / `read` / `change` / `disappear` / `flow` | 五值闭集，表示行为性质 |
| 具体动作 | `behavior.operation` | 开放动作名，如 `login`、`query`、`write`、`connect` | 必须归属于上述五类之一；新动作不扩展模型 |
| 结果 | `behavior.outcome` | `allowed` / `denied`；`success` / `failed`；`observed` / `unknown` | 按处置、执行、记录三段语义选择，不能混用 |
| 事实描述 | `behavior.message` | 文本 | 只描述行为事实；状态描述留待后续 state 模型 |

五类行为的判定：

- `appear`：新实体从无到有，例如进程启动、文件创建、连接建立。
- `read`：数据在原地被访问，例如读文件、查库、认证；不跨边界、不改变位置。
- `change`：已有实体的内容或状态被修改，例如写文件、改配置、提权。
- `disappear`：实体从有到无，例如进程退出、文件删除、连接断开。
- `flow`：数据跨边界或改变位置，例如网络传输、下载、外传、C2 通信、横向移动。

`read` 与 `flow` 的区别是“取”还是“移”。同一事实由观测层次裁决：系统层下载可表现为 `read`，网络层传输应表现为 `flow`。

`outcome` 是所有行为共有的结果维度：

- 处置段：有守门人的放行/阻断证据时使用 `allowed` / `denied`；
- 执行段：有行为本身成败证据时使用 `success` / `failed`；
- 记录段：仅记录事实或来源无结果时使用 `observed` / `unknown`。

来源 `action` 原值不能直接复制为 `behavior.outcome`；必须依据来源明确的动作、结果或处置字段推导。

## 2.2 旧告警分类字段、行为证据与实体类型的边界

`category_code`、`category`、`confidence`、`default_alert_name` 属于旧版 `source_finding` 分类映射结果，不是 SDM2 `behavior` 五字段，也不是实体属性。新规范没有明确要求时，OML 不应查询 `alert_cat_level` 或输出这四个字段；但它们所在的知识库仍可作为**建模证据**，不能在证据审计阶段被忽略。

行为语义的证据按以下顺序收集：

1. 优先读取用户为本次任务提供的产品原始文档和字段说明。枚举原值及其解释可用于推导行为，例如明确的“已阻止/已允许”可支撑处置结果，“插入/拔出”可支撑行为类型。
2. 用户没有提供字段说明时，不要求补交文档才开始。结合字段名、JSON 运行时类型、值域、同一条样本中的字段关系和已有 WPL/OML 推断候选语义；列出关键假设和置信度。字段名相近但含义不确定时保留原值，不扩展成没有证据的结果。
3. 如果目标 WarpParse 项目中刚好存在该 `log_type` 的 `models/knowledge/alert_cat_level/data.csv`，可按精确 `log_type` 查询分类作为补充证据。该 CSV 是可选资料，不属于 skill 自带的数据，也不是模型生成的前置条件。文档、样本或本地知识记录互相矛盾时报告冲突；只有冲突会改变必需路由/语义且无法合理判断时才标记 `NEEDS_INPUT`。
4. 用真实样本值验证文档或推断出的类型与值域是否匹配。CSV 中历史 `category_code=UNKNOWN` 仅是证据标签，不是新行为字段的默认值或允许写入值。

这些证据用于计算 `behavior.layer`、`behavior.type`、`behavior.operation`，以及在有明确结果语义时计算 `behavior.outcome`。分类标签可以确认来源侧检测/类别并约束候选语义，但不能单独产生 `allowed/denied` 或 `success/failed`，也不能把任意告警直接写成某个结果；具体行为仍需字段枚举、行为描述和样本值相互印证。

`entity_type` 不要求每条样本都先采集到具体实体字段才能确定。判定顺序是：

1. 先用用户提供的日志标题、产品说明或字段文档；若说明已明确实体语义，可固定对应类型，例如明确的恶意文件检测支持 `object.entity_type=file`，终端日志支持 `subject.entity_type=endpoint`。
2. 没有原始字段说明时，根据 `file_path`/哈希、IP/主机名、进程路径/名称等字段名和值推断 `file`、`endpoint` 或 `process`，并在交付中标记为推断。字段主要用于填充详情、稳定 `ref_id` 和富化。
3. 如果样本、标题或枚举中有相互印证的类型线索，可提高推断置信度；只有实体属性缺失通常不阻断建模。不得只凭一个含义模糊的字段写出确定实体类型。

本地 `alert_cat_level/data.csv` 中的 `alert_cat_level1/2_name`、`category_code/category` 可作为可选联合证据。缺少该文件不影响生成；单独的分类值或 `virus_type` 在实体语义仍有歧义时，不得强行选择实体类型。

来源分类确需保留时，使用 `extensions.source_private` 保存原始值；已用于标准时间、结果、对象、断言或行为映射的字段不重复保存。只有新规范明确声明的断言字段才能进入 `observation.assertion`，`default_alert_name` 不作为最终断言字段输出。

## 3. 语义与枚举

- `behavior.layer`：`network`、`system`、`application`。
- `behavior.type`：`appear`、`read`、`change`、`disappear`、`flow`。
- `behavior.outcome`：`allowed`、`denied`、`success`、`failed`、`observed`、`unknown`。
- `allowed/denied` 必须有来源处置证据（通常是 `observation.assertion.conclusion`）；`success/failed` 必须有动作本身成败证据；只有检测或记录事实时使用 `observed`；没有来源结果时使用 `unknown`。
- `observation.action` 表示来源产品行为（如 `detect`、`assess`、`record`），不能直接复制到 `behavior.outcome`。
- `data_source.category` 只允许 `auth`、`network`、`audit`、`system`、`alert`、`other`；有用户文档时依文档判断，无文档时按字段名和值域推断。推断仍无可靠依据时报告 `NEEDS_INPUT`，不伪称已确认。
- 分类判定只看日志本身：认证/登录/授权/会话用 `auth`；连接、流量、HTTP 访问用 `network`；进程、文件、配置、操作审计用 `audit`；内核、服务、系统状态用 `system`；来源侧检测或告警结论用 `alert`。根据文档（如有）、字段名和样本推断；证据确实不足时报告 `NEEDS_INPUT`，不能为了通过校验伪填 `other`。
- `source_finding` 不再写入行为信封；来源告警结论进入 `observation.assertion`，原始私有枚举进入 `extensions.source_private`。

## 4. OML 富化归档

固定顺序：

1. `__` 临时值与枚举归一化；
2. 从原始业务时间计算 `occur_time`，从 `Now::time()` 计算接入/解析时间；
3. 对有证据的通信或攻防 IP 做 GeoIP 查询；GeoIP 写入承载该 IP 的实体 `endpoint.geo` 或 `host.geo`，可使用 `continent_name`、`country_code`，无值时省略且禁止空对象。官网当前没有 `endpoint.resource`：资产编号、名称、类型分别写入 `endpoint.asset_id`、`endpoint.asset_name`、`endpoint.asset_type`，其余资产信息按语义平铺写入 `endpoint.system`/`endpoint.organization`；`asset_id` 不参与 `ref_id`，`asset_name` 不等同于 `host.name`，`asset_type` 按需归一到 `device.type` 或 `resource.kind`。数据库不可用标记 `NOT_RUN`，合法无命中则省略结果，不能写假值；通信方向使用 `facets.network.direction`，攻击方向使用 `observation.assertion.attack_direction`；
4. 顶层热查询字段（如有注册列）；
5. `subject/object/observer/carriers` 实体；
6. `facets` 行为细节；
7. `observation.assertion` 来源检测；
8. `extensions` 私有字段和富化结果。

同一来源值先归一化到唯一 `__` 临时变量，顶层和对象都 `read` 该变量。没有证据的成员直接省略；尽量不用 `skip_empty`，不能用空对象或占位字段掩盖缺失。

## 5. WPL 规则边界

WPL 只用文档明确的稳定字段和值区分规则。不得为了“提高命中率”擅自增加 `dev_id`、`index`、`f_has`、`f_not_has` 或字段存在性判断。未知字段先按 `chars`，时间/IP/端口/数组按实际类型解析；源文档中的枚举必须完整保留。

## 6. 资料来源

来源业务语义以用户为本次任务提供的原始文档为准；没有文档时从样本、字段名、值域和现有规则推断并标注假设。SDM 结构与枚举读取本目录的 `contracts/`、`schemas/` 和官方目录快照。`event_operation_dictionary.json` 的 `schema_version` 是字典版本，不改变事件信封的 `meta.schema_version="2.0"`。本技能不捆绑厂商源字段说明文档。
