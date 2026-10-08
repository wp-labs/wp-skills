# SDM 行为事件迁移摘要（当前唯一口径）

本摘要把日志接入要求收敛到唯一生产表 `sdm2_log.sdm_event_behavior`。历史平面列、旧 Schema 版本、旧 ref_id 公式、旧表和旧验证器均不适用。

## 目标信封

业务事件使用 `meta`、`event_kind=behavior`、`behavior`、`subject/object`、`carriers`，按需增加 `facets`、`observation`、`extensions`。一条 Kafka 消息是一个 JSON 对象，不包数组；原文由 `raw_log` 独立旁路保存并与业务事件一对一关联。

`meta.schema_version` 固定为字符串 `"2.0"`。`meta.event_id` 始终读取平台 `wp_event_id`；`meta.source_record.log_id` 读取源 `id`，缺失才回退 `wp_event_id`。Kafka 物理消息中的三个时间均为非负 Unix 毫秒整数，Routine Load 转换为 Doris `datetime(3)`。

UDP/TCP 接入层的上报设备地址统一命名为 `device_ip`，OML 使用 `__device_ip` 归一化后写入 `meta.data_source.instance_id`；值为纯 IP，不加前缀，也不得混入行为 `subject/object` 或攻击者/受害者地址。

兼容顶层保留 `attacker_entity`、`victim_entity`、`attacker_ip`、`victim_ip` 和 `occur_time`；顶层 `event_id` 停止输出。标准事件标识和时间写入 `meta.event_id`、`meta.occur_time`；攻击者和受害者同时按实体语义归入标准对象及 `observation.assertion.attacker[]`、`observation.assertion.victim[]`。

## 语义落位

- `behavior.layer` 只能是 `network`、`system`、`application`；`behavior.type` 只能是 `appear`、`read`、`change`、`disappear`、`flow`。
- 行为证据先取用户提供的产品原始文档（如果有）；没有字段说明时，根据字段名、JSON 类型、样本值和字段关系推断，并在报告中标记假设。目标项目中的 `models/knowledge/alert_cat_level/data.csv` 可按精确 `log_type` 作为可选补充证据，不是生成前置条件，也不是新模型输出模板。
- `behavior.outcome` 只能是 `allowed`、`denied`、`success`、`failed`、`observed`、`unknown`。有用户文档时依据其中结果/动作字段推导；没有字段说明时按字段名和值域推断并标注。来源 action 原值放在 assertion 或 `extensions.source_private`，不能因为日志名是告警就写死 outcome。
- `allowed/denied` 必须有 `observation.assertion.conclusion` 证据；执行本身有明确成败时才使用 `success/failed`；只有观察事实时用 `observed`；没有结果证据时用 `unknown` 或 `NEEDS_INPUT`。
- `data_source.category` 只能是 `auth`、`network`、`audit`、`system`、`alert`、`other`；优先依用户文档判断，无文档时按字段名和值域推断。证据仍不足时 `NEEDS_INPUT`，不伪称已确认。

## 实体与富化

`subject/object` 按行为语义填写，未知使用 `null`；`carriers` 只放确实承载行为的实体。用户文档明确实体类型时以文档为准；无字段说明时，可根据日志标题、字段名和值推断 `file`、`endpoint`、`process` 等类型，并标记推断。具体路径、哈希、IP、主机名和进程字段用于补充详情、稳定标识和富化。非空实体必须有稳定 `entity_type::value` ref_id，value 可为来源路径、GUID 或哈希，不强制 OML 计算 SHA-256，也不拼事件号/批次号/当前时间。

只有业务语义明确为通信或攻防地址的字段才执行 GeoIP。字段说明由用户提供时依说明判断；没有文档时可依据 `src_ip`、`dst_ip`、`attacker_ip` 等字段名和样本值推断，并在结果中标记。GeoIP 写入承载该 IP 的标准 `endpoint.geo`/`host.geo`，可使用 `continent_name`、`country_code`；无值时省略，禁止空 `{}`。官网当前没有 `endpoint.resource`，资产编号、名称、类型分别写入 `endpoint.asset_id`、`endpoint.asset_name`、`endpoint.asset_type`，其余资产信息按语义平铺写入 `endpoint.system`/`endpoint.organization`；`asset_id` 不参与 `ref_id`，`asset_name` 不等同于 `host.name`，`asset_type` 按需归一到 `device.type` 或 `resource.kind`。查询服务不可用时报告 `NOT_RUN`，不能写样例值。sip/dip 方向写 `facets.network.direction`，attacker/victim 方向写 `observation.assertion.attack_direction`。

## 迁移与门禁

官网当前机器目录已登记 `facets.network.source_zone`、`facets.network.target_zone`、`facets.network.session_id` 和 `facets.network.nat.original/translated.*`。网络会话起止时间、持续时长及请求/响应流量统计尚未登记，出现时先列为官网新增候选；认证类可使用已登记的 `facets.authentication.session.start_time/end_time`、`auth_result`、`auth_failure_reason` 和 `session_id`，不能把认证字段跨到网络会话。

1. 读取用户提供的原始文档（如有）、真实样本和现有 WPL；确认或推断 rule/log_type 路由。
2. 调用一次本地 debug parse，记录实际命中 rule、所有字段、值和运行时类型；不可用则 `NOT_RUN`。
3. 逐项审计 WPL 捕获字段是否被 OML 消费、标准化或保留在 extensions；漏字段先修 WPL/OML，不猜读。
4. 运行 `check_pipeline.py`：一次 `wpadm check`、一次 batch，检查行为 Schema、枚举、ref_id、Doris 031/032 契约、all/raw 双路数量与原文相关性。

旧规则与新规则冲突时只保留本摘要、`new-standard.md`、行为 Schema 和 contracts 中的当前定义。
