# WPL/OML 通用语法

```wpl
package source_kind {
    #[tag(log_desc: "来源日志描述", log_type: "source_kind_event"), copy_event_parse(rule: "raw_log/raw_log")]
    rule event {
        (json(time_timestamp@event_time, chars@message, chars@event_type)
         | f_chars_has(event_type, expected_type))
    }
}
```

`f_chars_has` 判断整个字段精确相等。若类型标记位于 `message` 文本内部，用 `take(message) | starts_with('有证据的前缀')` 或按样本结构拆解；不要把特定来源的字段名或标记套给其他日志。JSON 需捕获全部可解析字段，嵌套 KV 继续拆解。捕获名要与 OML `read` 一致。

```oml
name : source_kind_event
rule : source_kind/event
---
__now = Now::time();
__occur_time = pipe read(event_time) | Time::to_ts_zone(8, ms);
meta = object {
    schema_version = chars("2.0");
    tenant_id = chars("local-test-tenant");
    event_id = read(wp_event_id);
    occur_time = read(__occur_time);
    ingest_time = read(__now);
    parse_time = read(__now);
    mapping_id = chars("source_kind_event_v1");
};
event_kind = chars(behavior);
behavior = object { layer = chars(system); type = chars(read); };
carriers : array = array {};
attacker_entity = chars("");
victim_entity = chars("");
attacker_ip = chars("");
victim_ip = chars("");
occur_time = read(__occur_time);
```

示例只说明语法；实际租户和行为由来源决定。`object` 成员用 `=`；临时值使用 `read(__name)`；没有角色证据时四个兼容字符串为空。顶层 `event_id` 禁止。`wpadm check --what oml` 不证明实际 OML 可加载，须以 `wparse batch` 和四路输出为准。
