# SDM2 独立规则输出契约

业务输出须符合本目录 `schemas/sdm-event-behavior-kafka.schema.json`。每条事件有 `meta`、`event_kind=behavior`、`behavior` 和五个顶层兼容字段；顶层 `event_id` 禁止。`meta.event_id` 使用 WarpParse 的 `wp_event_id`，`meta.occur_time` 与顶层 `occur_time` 都是同一源业务时间换算的 Unix 毫秒整数。四个角色字段始终为字符串；没有明确攻击者/受害者或源/目的证据时为空字符串，采集主机 IP 不构成角色证据。

`carriers` 只表达真实承载关系。OML 无承载证据时写 `carriers : array = array {};`；当前 WarpParse 物理 JSON 会省略空数组，因此 Schema 允许缺少 `carriers`，有值时必须符合数组定义。无实体证据时省略可选 `subject/object`。`extensions.source_private` 只保存未被标准字段消费的来源字段。

独立最小工程的 `local-test-tenant` 只是隔离验证身份，不代表生产租户。生产规则需要由真实接入层或明确来源提供租户。
