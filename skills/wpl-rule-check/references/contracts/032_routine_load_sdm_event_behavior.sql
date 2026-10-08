-- sdm2_log.sdm_event_behavior 当前生产 Routine Load。
-- Kafka 中时间允许 Unix 秒或毫秒；Doris 统一转换为 DATETIME(3)。
CREATE ROUTINE LOAD sdm2_log.sdm_event_behavior_load_v1 ON sdm_event_behavior
WITH APPEND
COLUMNS(
  tenant_id_raw, occur_time_ms, event_id_raw, ingest_time_ms, parse_time_ms,
  schema_version, mapping_id, vendor, product, data_source_category,
  collector_instance_id, log_id, log_type, log_name, log_level, record_kind,
  behavior_layer, behavior_type, behavior_operation, behavior_outcome, behavior_message,
  subject_ref_id, subject_entity_type, object_ref_id, object_entity_type,
  observer_ref_id, observer_entity_type, observation_action,
  assertion_title, assertion_rule, assertion_conclusion, assertion_severity,
  subject_detail, object_detail, carriers, carrier_role, facets,
  observation_detail, extensions,
  tenant_id=trim(tenant_id_raw),
  occur_time=from_unixtime(cast(if(cast(occur_time_ms AS double) >= 100000000000,
    cast(occur_time_ms AS double) / 1000, cast(occur_time_ms AS double)) AS decimal(18,6))),
  event_id=trim(event_id_raw),
  ingest_time=if(ingest_time_ms IS NULL, cast(now(3) AS text),
    from_unixtime(cast(if(cast(ingest_time_ms AS double) >= 100000000000,
      cast(ingest_time_ms AS double) / 1000, cast(ingest_time_ms AS double)) AS decimal(18,6)))),
  parse_time=if(parse_time_ms IS NULL, cast(now(3) AS text),
    from_unixtime(cast(if(cast(parse_time_ms AS double) >= 100000000000,
      cast(parse_time_ms AS double) / 1000, cast(parse_time_ms AS double)) AS decimal(18,6))))
)
PROPERTIES(
  "desired_concurrent_number"="256",
  "max_error_number"="0", "max_filter_ratio"="0.01",
  "max_batch_interval"="60", "max_batch_rows"="20000000",
  "max_batch_size"="1073741824",
  "format"="json",
  "jsonpaths"="[\"$.meta.tenant_id\",\"$.meta.occur_time\",\"$.meta.event_id\",\"$.meta.ingest_time\",\"$.meta.parse_time\",\"$.meta.schema_version\",\"$.meta.mapping_id\",\"$.meta.data_source.vendor\",\"$.meta.data_source.product\",\"$.meta.data_source.category\",\"$.meta.data_source.instance_id\",\"$.meta.source_record.log_id\",\"$.meta.source_record.log_type\",\"$.meta.source_record.log_name\",\"$.meta.source_record.log_level\",\"$.meta.source_record.record_kind\",\"$.behavior.layer\",\"$.behavior.type\",\"$.behavior.operation\",\"$.behavior.outcome\",\"$.behavior.message\",\"$.subject.ref_id\",\"$.subject.entity_type\",\"$.object.ref_id\",\"$.object.entity_type\",\"$.observation.observer.ref_id\",\"$.observation.observer.entity_type\",\"$.observation.action\",\"$.observation.assertion.title\",\"$.observation.assertion.rule\",\"$.observation.assertion.conclusion\",\"$.observation.assertion.severity\",\"$.subject\",\"$.object\",\"$.carriers\",\"$.carriers[0].carrier_role\",\"$.facets\",\"$.observation\",\"$.extensions\"]",
  "strip_outer_array"="false", "num_as_string"="false",
  "strict_mode"="false", "timezone"="Etc/UTC",
  "exec_mem_limit"="2147483648"
)
FROM KAFKA(
  "kafka_broker_list"="kafka:9092",
  "kafka_topic"="sdm_event_behavior",
  "property.group.id"="sdm_event_behavior_load_v1_b436f3f6-04d2-4a75-b80d-dc94bafd86b3"
);
