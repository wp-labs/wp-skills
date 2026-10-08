# SDM 2.0 逻辑字段与物理列目录

来源：[SDM 行为日志标准](https://sdm.docs.dy-sec.com/pages/log-standard.html#mode-ref)，按 2026-09-20 官网页面内嵌机器目录 `DATA` 重新同步。本文件是 OML 建模和门禁的规范基线，不包含厂商源字段说明；用户提供原始文档时以其解释来源语义，没有字段说明时按样本字段名和值推断并标记假设。

本次官网目录统计：逻辑字段 60 个、物理列 39 个、对象类型 16 个、Facet 域 16 个、对象/Facet 类型总字段 106 个、断言字段 15 个、扩展对象 4 个。

## 逻辑字段

| 分层 | 字段路径 |
|---|---|
| meta | `meta.schema_version`、`meta.tenant_id`、`meta.event_id`、`meta.occur_time`、`meta.ingest_time`、`meta.parse_time`、`meta.mapping_id` |
| meta | `meta.data_source.vendor`、`meta.data_source.product`、`meta.data_source.category`、`meta.data_source.instance_id` |
| meta | `meta.source_record.log_id`、`meta.source_record.record_kind`、`meta.source_record.log_type`、`meta.source_record.log_level`、`meta.source_record.log_name`、`meta.source_record.raw_ref` |
| event_kind | `event_kind` |
| behavior | `behavior.layer`、`behavior.type`、`behavior.operation`、`behavior.outcome`、`behavior.message` |
| subject | `subject.ref_id`、`subject.entity_type`、`subject.<type>` |
| object | `object.ref_id`、`object.entity_type`、`object.<type>` |
| carriers | `carriers[].ref_id`、`carriers[].entity_type`、`carriers[].carrier_role`、`carriers[].<type>` |
| facets | `facets.network`、`facets.process`、`facets.file`、`facets.authorization`、`facets.peripheral`、`facets.authentication`、`facets.dns`、`facets.http`、`facets.database`、`facets.email`、`facets.application`、`facets.container`、`facets.tls`、`facets.registry`、`facets.cloud`、`facets.ics` |
| observation | `observation.observation_id`、`observation.action`、`observation.assertion`、`observation.evidence_refs[]`、`observation.observer.ref_id`、`observation.observer.entity_type`、`observation.observer.<type>` |
| extensions | `extensions.source_private`、`extensions.profiles`、`extensions.enrichments` |

`meta.schema_version` 固定为字符串 `"2.0"`；`event_kind` 固定为 `behavior`。`meta.data_source.category` 当前闭集为 `auth`、`network`、`audit`、`system`、`alert`、`other`。

## 物理列

| 物理列 | JSONPath |
|---|---|
| `tenant_id` | `meta.tenant_id` |
| `occur_time` | `meta.occur_time` |
| `event_id` | `meta.event_id` |
| `ingest_time` | `meta.ingest_time` |
| `parse_time` | `meta.parse_time` |
| `schema_version` | `meta.schema_version` |
| `mapping_id` | `meta.mapping_id` |
| `vendor` | `meta.data_source.vendor` |
| `product` | `meta.data_source.product` |
| `data_source_category` | `meta.data_source.category` |
| `collector_instance_id` | `meta.data_source.instance_id` |
| `log_id` | `meta.source_record.log_id` |
| `log_type` | `meta.source_record.log_type` |
| `log_name` | `meta.source_record.log_name` |
| `log_level` | `meta.source_record.log_level` |
| `record_kind` | `meta.source_record.record_kind` |
| `behavior_layer` | `behavior.layer` |
| `behavior_type` | `behavior.type` |
| `behavior_operation` | `behavior.operation` |
| `behavior_outcome` | `behavior.outcome` |
| `behavior_message` | `behavior.message` |
| `subject_ref_id` | `subject.ref_id` |
| `subject_entity_type` | `subject.entity_type` |
| `object_ref_id` | `object.ref_id` |
| `object_entity_type` | `object.entity_type` |
| `observer_ref_id` | `observation.observer.ref_id` |
| `observer_entity_type` | `observation.observer.entity_type` |
| `observation_action` | `observation.action` |
| `assertion_title` | `observation.assertion.title` |
| `assertion_rule` | `observation.assertion.rule` |
| `assertion_conclusion` | `observation.assertion.conclusion` |
| `assertion_severity` | `observation.assertion.severity` |
| `subject_detail` | `subject.<type>` |
| `object_detail` | `object.<type>` |
| `carriers` | `carriers[]` |
| `carrier_role` | `carriers[0].carrier_role` |
| `facets` | `facets` |
| `observation_detail` | `observation` |
| `extensions` | `extensions` |

## 官网对象类型字段

对象字段按 `entity_type` 展开到 `subject.<type>`、`object.<type>`、`carriers[].<type>` 或 `observation.observer.<type>`。官网当前登记如下：

| entity_type | 字段 |
|---|---|
| `user` | `name`、`uid`、`domain`、`groups[]`、`groups[].name`、`groups[].uid`、`groups[].type` |
| `account` | `name` |
| `host` | `id`、`name`、`ip`、`mac`、`os{name,type,version,bit,build}`、`hw_info{cores,ram_size,serial_number,vendor_name,model,bios_ver,bios_date}`、`network_interfaces[]{name,ip,mac,hostname}`、`geo{continent_name,country,province,city,country_code,latitude,longitude}`、`system{id,name}`、`organization{id,name}` |
| `endpoint` | `ip`、`port`、`mac`、`asset_id`、`asset_name`、`asset_type`、`geo{continent_name,country,province,city,country_code,latitude,longitude}`、`system{id,name}`、`organization{id,name}` |
| `process` | `name`、`pid`、`guid`、`command_line`、`integrity`、`created_time`、`terminated_time`、`working_directory`、`user{name,uid,domain,groups[]}`、`file{name,path,size,hashes{md5,sha1,sha256},internal_name,signatures{algorithm,certificate,digest,state},company_name,product,version,desc}` |
| `file` | `name`、`path`、`size`、`hashes{md5,sha1,sha256}`、`internal_name`、`signatures{algorithm,certificate,digest,state}`、`company_name`、`product`、`version`、`desc` |
| `service` | `name`、`id`、`port` |
| `domain` | `name` |
| `url` | `full`、`path`、`query` |
| `device` | `id`、`vendor`、`type`、`model`、`ip`、`serial_number` |
| `resource` | `id`、`name`、`kind`、`vendor`、`geo{continent_name,country,province,city,country_code,latitude,longitude}`、`system{id,name}`、`organization{id,name}` |
| `application` | `name`、`version`、`vendor` |
| `cloud` | `provider`、`account`、`region` |
| `container` | `id`、`name`、`image`、`namespace` |
| `certificate` | `serial`、`subject`、`issuer`、`not_after` |
| `script` | `name`、`path`、`interpreter` |

边界：

- `endpoint` 没有 `resource`；不能输出 `endpoint.resource`，资产字段使用 `endpoint.asset_id`、`endpoint.asset_name`、`endpoint.asset_type`，资产归属平铺为 `endpoint.system{id,name}`、`endpoint.organization{id,name}`。`endpoint.asset_id` 不参与 `ref_id`，且与同一资产在 host/device 上的编号保持一致；`asset_name` 不等同于 `host.name`；`asset_type` 是来源归一值，判定出实体后按需归一到 `device.type` 或 `resource.kind`。
- GeoIP 标准字段包括 `geo.continent_name`、`geo.country`、`geo.country_code`、`geo.province`、`geo.city`、`geo.latitude`、`geo.longitude`；这些字段可选，无值时省略，禁止伪造空 `{}`。
- 本次官网新增了 `application.vendor`、`device.type`、`resource.vendor`，它们现在可以按实体类型直接迁移，不再归为扩展字段。
- 资产富化只有在语义明确时写 `system`/`organization`；`asset_id` 不能无依据强行改写成 `system.id`。

## 官网 Facet 叶子路径

```text
facets.network.connection_result
facets.network.protocol
facets.network.direction
facets.network.application_protocol
facets.network.packet_metadata
facets.network.session_id
facets.network.session.start_time
facets.network.session.end_time
facets.network.session.duration_seconds
facets.network.traffic.bytes_in
facets.network.traffic.bytes_out
facets.network.traffic.total_bytes
facets.network.traffic.request_bytes
facets.network.traffic.request_packets
facets.network.traffic.response_bytes
facets.network.traffic.response_packets
facets.network.nat.original/translated.*
facets.network.source_zone
facets.network.target_zone

facets.process.ancestry[]
facets.process.injection.method
facets.process.injection.target_thread.*

facets.file
facets.file.created_time
facets.file.modified_time
facets.authorization.approvers[]
facets.authorization.level
facets.peripheral.device

facets.authentication.auth_type
facets.authentication.session.start_time
facets.authentication.session.end_time
facets.authentication.auth_result
facets.authentication.auth_failure_reason
facets.authentication.session_id

facets.dns.question.name
facets.dns.question.type
facets.dns.question.class
facets.dns.answers[]
facets.dns.answers[].name/type/class/ttl/address
facets.dns.response.code
facets.dns.header.opcode
facets.dns.header.authoritative
facets.dns.header.truncated
facets.dns.header.recursion_desired
facets.dns.packet_length
facets.dns.question_count
facets.dns.answer_count
facets.dns.authority_count
facets.dns.additional_count
facets.dns.header.query_response
facets.dns.header.recursion_available
facets.dns.header.authentic_data
facets.dns.header.checking_disabled

facets.http.request.method
facets.http.request.host
facets.http.request.user_agent
facets.http.request.referer
facets.http.request.forwarded_for[].ip
facets.http.response.status_code
facets.http.duration
facets.http.request.content_type
facets.http.request.headers
facets.http.response.headers

facets.database.name
facets.database.type
facets.database.user.name
facets.database.statement

facets.email.from
facets.email.subject
facets.email.recipients[]
facets.email.cc[]
facets.email.attachments[]
facets.email.date
facets.email.sender
facets.email.envelope_from
facets.email.message_id
facets.email.mime_version
facets.email.client.user_agent
facets.email.smtp.helo
facets.email.smtp.last_command
facets.email.smtp.last_reply_code
facets.email.smtp.last_reply_message
facets.email.smtp.transfer_depth

facets.application.name
facets.container.kubernetes.namespace
facets.container.kubernetes.pod.name
facets.container.kubernetes.pod.id
facets.container.kubernetes.cluster.id
facets.container.kubernetes.cluster.name
facets.container.kubernetes.container.id
facets.container.kubernetes.container.name
facets.tls
facets.registry.key.path
facets.registry.key.renamed_path
facets.registry.value.name
facets.registry.value.type
facets.cloud
facets.ics.function_code
facets.ics.function_name
facets.ics.address
```

官网当前已登记：

```text
observation.assertion.attack_direction
```

官网当前仍未登记：

```text
facets.file.remote_path
facets.network.nat.type
```

这两个字段出现时仍需列为官网新增候选，不能直接当作标准字段。

## 官网当前断言和扩展

断言字段：

```text
observation.assertion.title
observation.assertion.severity
observation.assertion.confidence
observation.assertion.category
observation.assertion.category_code
observation.assertion.rule
observation.assertion.attack_direction
observation.assertion.attacker[]
observation.assertion.victim[]
observation.assertion.affected[]
observation.assertion.kill_chain
observation.assertion.mitre
observation.assertion.vulnerability
observation.assertion.malware
observation.assertion.conclusion
```

扩展容器：

```text
extensions.source_private
extensions.profiles
extensions.enrichments
extensions.profiles.endpoint_asset
```

`observation.assertion.attacker[]` 和 `victim[]` 当前就是数组，不需要数组化迁移。`source_private` 只保留原始未被标准 OML 消费的字段；官网没有标准落点但有跨源价值的字段，应先列为扩展或官网新增候选。

## 与上次目录相比的变化

| 旧判断 | 官网最新判断 |
|---|---|
| `subject/object.process.id` 无目标 | 已登记 `process.pid`，可直接改名 |
| `facets.authentication.result` 无目标 | 已登记 `facets.authentication.auth_result` |
| `facets.http.request.forwarded_for_raw` 无目标 | 已登记 `forwarded_for[].ip`，需要先拆分原始链 |
| `endpoint.resource` 可承载资产 | 仍禁止使用，资产编号改写为 `endpoint.asset_id`，资产归属改写为 `endpoint.system`/`endpoint.organization` |
| `facets.network.source_zone/target_zone` 未登记 | 已登记 |
| 网络 session/traffic 统计未登记 | 仍未登记 |
| DNS count、packet length、Header 扩展字段未登记 | 已全部登记 |
| Email Date、Message-ID、SMTP 细节未登记 | 已登记 |
| HTTP duration、content type、headers 未登记 | 已登记 |
| `facets.file.created_time/modified_time` 未登记 | 已登记 |
| `application.vendor`、`device.type`、`resource.vendor` 只能扩展 | 已登记，可直接迁移 |
| 断言字段 13 个 | 当前为 15 个，新增 `kill_chain`、`attack_direction` |
