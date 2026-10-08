-- sdm2_log.sdm_event_behavior 当前生产表。
-- 设计原则：物理镜像 SDM 2.0 行为信封，不兼容历史平面事件表。
-- 身份与枚举拆标量；typed object 细节留 VARIANT；原文经 event_id 关联 raw_log，本表不存原文。
-- 保留策略：MONTH 分区，start=-80 / end=3（审计级，与 DORIS_RETENTION_DAYS 天级参数无关，
-- raw_log 的保留期必须在部署时与本月数对齐；该值属于部署参数，不在事件 OML 中写死。
-- 依赖：T0 硬门槛满足（逻辑契约终稿 + schema/registry 版本固定）后方可 apply。
CREATE TABLE IF NOT EXISTS sdm2_log.sdm_event_behavior (
  -- meta 身份（key 前缀）
  `tenant_id` VARCHAR(128) NOT NULL COMMENT 'meta.tenant_id',
  `occur_time` DATETIME(3) NOT NULL COMMENT 'meta.occur_time，UTC',
  `event_id` VARCHAR(128) NOT NULL COMMENT 'meta.event_id；raw_log 关联键',
  `ingest_time` DATETIME(3) NULL COMMENT 'meta.ingest_time',
  `parse_time` DATETIME(3) NULL COMMENT 'meta.parse_time',
  `schema_version` VARCHAR(32) NOT NULL COMMENT 'meta.schema_version，当前写入 2.0；语义变更兜底',
  `mapping_id` VARCHAR(128) NOT NULL COMMENT 'meta.mapping_id，不可变映射身份',
  `vendor` VARCHAR(128) NULL COMMENT 'meta.data_source.vendor',
  `product` VARCHAR(128) NULL COMMENT 'meta.data_source.product',
  `data_source_category` VARCHAR(128) NULL COMMENT 'meta.data_source.category',
  `collector_instance_id` VARCHAR(128) NULL COMMENT 'meta.data_source.instance_id，采集器实例',
  `log_id` VARCHAR(128) NULL COMMENT 'meta.source_record.log_id',
  `log_type` VARCHAR(128) NULL COMMENT 'meta.source_record.log_type',
  `log_name` VARCHAR(255) NULL COMMENT 'meta.source_record.log_name',
  `log_level` VARCHAR(64) NULL COMMENT 'meta.source_record.log_level，原始日志等级；不是检测严重度',
  `record_kind` VARCHAR(32) NULL COMMENT 'meta.source_record.record_kind，兼容路由值',
  -- behavior
  `behavior_layer` VARCHAR(16) NULL COMMENT 'behavior.layer: network/system/application',
  `behavior_type` VARCHAR(16) NULL COMMENT 'behavior.type 五类闭集',
  `behavior_operation` VARCHAR(64) NULL COMMENT 'behavior.operation 开放动作名',
  `behavior_outcome` VARCHAR(16) NULL COMMENT 'behavior.outcome 三段语义',
  `behavior_message` VARCHAR(4096) NULL COMMENT 'behavior.message',
  -- 角色身份标量（索引与实体事件的锚点）
  `subject_ref_id` VARCHAR(255) NULL COMMENT 'subject.ref_id，{entity_type}::{自然键}',
  `subject_entity_type` VARCHAR(32) NULL COMMENT 'subject.entity_type',
  `object_ref_id` VARCHAR(255) NULL COMMENT 'object.ref_id',
  `object_entity_type` VARCHAR(32) NULL COMMENT 'object.entity_type',
  `observer_ref_id` VARCHAR(255) NULL COMMENT 'observation.observer.ref_id，可空',
  `observer_entity_type` VARCHAR(32) NULL COMMENT 'observation.observer.entity_type，可空',
  `observation_action` VARCHAR(16) NULL COMMENT 'observation.action: record/detect/assess',
  -- 断言标量（record 事件为空）
  `assertion_title` VARCHAR(1024) NULL COMMENT 'observation.assertion.title',
  `assertion_rule` VARCHAR(128) NULL COMMENT 'observation.assertion.rule',
  `assertion_conclusion` VARCHAR(128) NULL COMMENT 'observation.assertion.conclusion，来源处置结论',
  `assertion_severity` VARCHAR(64) NULL COMMENT 'observation.assertion.severity，检测严重度；与 log_level 分轨',
  `subject_detail` VARIANT COMMENT 'subject 的 typed object（process/file/endpoint/…）',
  `object_detail` VARIANT COMMENT 'object 的 typed object',
  `carriers` VARIANT COMMENT 'carriers[]，含 carrier_role',
  `carrier_role` VARCHAR(64) NULL COMMENT 'carriers[0].carrier_role 非权威查询优化投影；逻辑契约不定义 carriers[] 顺序，多承载者检索读 carriers VARIANT；D6 触发（10m VARIANT 路径过滤 305ms>200ms）；写侧 jsonpaths 直取',
  `facets` VARIANT COMMENT '领域行为上下文（network/dns/http/process.ancestry/…）',
  `observation_detail` VARIANT COMMENT 'observation 其余：observer typed object、observed_at、evidence_refs',
  `extensions` VARIANT COMMENT 'extensions：source_private/profiles/enrichments',
  INDEX `idx_behavior_type` (`behavior_type`) USING INVERTED COMMENT '五类过滤',
  INDEX `idx_behavior_outcome` (`behavior_outcome`) USING INVERTED COMMENT 'outcome 过滤',
  INDEX `idx_behavior_layer` (`behavior_layer`) USING INVERTED COMMENT 'layer 过滤',
  INDEX `idx_record_kind` (`record_kind`) USING INVERTED COMMENT 'finding/activity 过滤',
  INDEX `idx_log_type` (`log_type`) USING INVERTED COMMENT '来源日志类型',
  INDEX `idx_mapping_id` (`mapping_id`) USING INVERTED COMMENT '映射身份',
  INDEX `idx_subject_ref_id` (`subject_ref_id`) USING INVERTED COMMENT '主体实体索引锚点',
  INDEX `idx_object_ref_id` (`object_ref_id`) USING INVERTED COMMENT '客体实体索引锚点',
  INDEX `idx_subject_entity_type` (`subject_entity_type`) USING INVERTED COMMENT '主体类型',
  INDEX `idx_object_entity_type` (`object_entity_type`) USING INVERTED COMMENT '客体类型',
  INDEX `idx_observer_ref_id` (`observer_ref_id`) USING INVERTED COMMENT '观察者',
  INDEX `idx_assertion_rule` (`assertion_rule`) USING INVERTED COMMENT '规则检索',
  INDEX `idx_assertion_conclusion` (`assertion_conclusion`) USING INVERTED COMMENT '处置结论',
  INDEX `idx_carrier_role` (`carrier_role`) USING INVERTED COMMENT '承载角色过滤（D6 投影）',
  INDEX `idx_vendor` (`vendor`) USING INVERTED COMMENT '来源厂商'
)
UNIQUE KEY(`tenant_id`, `occur_time`, `event_id`)
PARTITION BY RANGE(`occur_time`)()
DISTRIBUTED BY HASH(`tenant_id`, `event_id`) BUCKETS 8
PROPERTIES (
  "replication_num" = "1",
  "dynamic_partition.enable" = "true",
  "dynamic_partition.time_unit" = "MONTH",
  "dynamic_partition.start" = "-80",
  "dynamic_partition.end" = "3",
  "dynamic_partition.prefix" = "p",
  "dynamic_partition.buckets" = "8",
  "bloom_filter_columns" = "tenant_id,event_id,log_id",
  "enable_unique_key_merge_on_write" = "true"
);
