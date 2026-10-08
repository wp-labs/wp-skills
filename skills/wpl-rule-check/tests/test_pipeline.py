import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "check_pipeline.py"
spec = importlib.util.spec_from_file_location("check_pipeline", SCRIPT)
pipeline = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pipeline
assert spec.loader is not None
spec.loader.exec_module(pipeline)


def behavior_event():
    return {
        "meta": {
            "schema_version": "2.0",
            "tenant_id": "tenant-1",
            "event_id": "evt-1",
            "occur_time": 1788404400000,
            "ingest_time": 1788504862945,
            "parse_time": 1788504862945,
            "mapping_id": "vendor.product.log.behavior.v2",
            "data_source": {"vendor": "vendor", "product": "product", "category": "alert"},
            "source_record": {"log_type": "example"},
        },
        "event_kind": "behavior",
        "behavior": {"layer": "application", "type": "appear", "outcome": "denied"},
        "subject": {
            "entity_type": "process",
            "ref_id": "process::C:\\Windows\\System32\\cmd.exe",
            "process": {"name": "cmd.exe", "file": {"path": "C:\\Windows\\System32\\cmd.exe"}},
        },
        "object": None,
        "carriers": [{
            "ref_id": "process::C:\\Windows\\System32\\cmd.exe",
            "entity_type": "process",
            "carrier_role": "origin",
        }],
        "observation": {
            "observation_id": "evt-1",
            "observer": {"entity_type": "device", "ref_id": "device::sensor-1", "device": {"vendor": "vendor"}},
            "action": "detect",
            "assertion": {"conclusion": "block"},
            "evidence_refs": ["source_record:1"],
        },
        "extensions": {"source_private": {"vendor_code": "x"}},
    }


class PipelineValidationTests(unittest.TestCase):
    def test_behavior_accepts_kafka_unix_ms_and_complete_carrier(self):
        event = behavior_event()
        self.assertEqual(pipeline.validate_behavior(event), [])
        self.assertEqual(pipeline.jsonschema_errors(event), [])

    def test_event_id_top_level_projection_is_rejected(self):
        event = behavior_event()
        event["event_id"] = "evt-1"
        self.assertTrue(any("retired top-level" in error for error in pipeline.validate_behavior(event)))

    def test_legacy_roots_and_other_category_are_rejected(self):
        event = behavior_event()
        event["roles_obj"] = {}
        event["meta"]["data_source"]["category"] = "other"
        errors = pipeline.validate_behavior(event)
        self.assertTrue(any("legacy envelope root" in e for e in errors))
        self.assertTrue(any("category invalid" in e for e in errors))

    def test_control_outcome_requires_assertion(self):
        event = behavior_event()
        event.pop("observation")
        errors = pipeline.validate_behavior(event)
        self.assertTrue(any("requires observation.assertion.conclusion" in e for e in errors))

    def test_raw_digest_and_unix_ms(self):
        raw_msg = '{"id":"1"}'
        raw = {
            "tenant_id": "tenant-1",
            "occur_time": 1788404400000,
            "event_id": "evt-1",
            "raw_msg": raw_msg,
            "raw_msg_digest": hashlib.md5(raw_msg.encode()).hexdigest(),
            "digest_algo": "md5",
        }
        self.assertEqual(pipeline.validate_raw(raw), [])

    def test_doris_contract_and_output_projection(self):
        event = behavior_event()
        self.assertEqual(pipeline.doris_contract_errors(), [])
        self.assertEqual(pipeline.doris_projection_errors(event), [])
        event["meta"]["occur_time"] = 1788404400
        self.assertEqual(pipeline.doris_projection_errors(event), [])

    def test_doris_projection_rejects_required_and_varchar_errors(self):
        event = behavior_event()
        event["meta"]["tenant_id"] = " "
        event["behavior"]["message"] = "x" * 4097
        errors = pipeline.doris_projection_errors(event)
        self.assertTrue(any("tenant_id must be a non-empty string" in e for e in errors))
        self.assertTrue(any("behavior_message exceeds VARCHAR(4096)" in e for e in errors))
        event["meta"]["tenant_id"] = "tenant"
        event["behavior"]["message"] = "ok"
        event["meta"]["occur_time"] = "2026-09-07T00:00:00Z"
        self.assertEqual(pipeline.doris_projection_errors(event), [])

    def test_static_oml_requires_behavior_envelope(self):
        path = Path(self.id().replace("/", "_") + ".oml")
        try:
            path.write_text(
                "__device_ip: ip = read(wp_src_ip);\n"
                "meta = object {\n"
                "  schema_version = chars(\\\"2.0\\\");\n"
                "  data_source = object { instance_id = read(__device_ip); };\n"
                "};\n"
                "event_kind = chars(behavior);\n"
                "behavior = (layer = chars(application));\n"
                "subject = ();\n"
                "object = ();\n"
                "carriers = ();\n",
                encoding="utf-8",
            )
            self.assertEqual(pipeline.static_oml(path), [])
        finally:
            path.unlink(missing_ok=True)

    def test_static_oml_rejects_unprojected_knowledge_results(self):
        path = Path(self.id().replace("/", "_") + ".oml")
        try:
            path.write_text(
                "__country, __city = select country, city from geo.ip_geo;\n"
                "meta = (schema_version = chars(\"2.0\"));\n"
                "event_kind = chars(behavior);\n"
                "behavior = (layer = chars(application));\n"
                "carriers = ();\n"
                "extensions = (country = read(__country));\n",
                encoding="utf-8",
            )
            errors = pipeline.static_oml(path)
            self.assertTrue(any("__city" in error and "not projected" in error for error in errors))
        finally:
            path.unlink(missing_ok=True)

    def test_static_oml_requires_both_enrichments_for_normalized_ip_role(self):
        path = Path(self.id().replace("/", "_") + ".oml")
        try:
            path.write_text(
                "__sip: ip = read(sip);\n"
                "meta = (schema_version = chars(\"2.0\"));\n"
                "event_kind = chars(behavior);\n"
                "behavior = (layer = chars(network));\n"
                "carriers = ();\n",
                encoding="utf-8",
            )
            errors = pipeline.static_oml(path)
            self.assertTrue(any("sip is missing GeoIP" in error for error in errors))
        finally:
            path.unlink(missing_ok=True)

    def test_static_oml_requires_intranet_mask_before_ip_number(self):
        path = Path(self.id().replace("/", "_") + ".oml")
        try:
            path.write_text(
                "__sip: ip = read(sip);\n"
                "__sip_num = pipe @__sip | ip_to_biguint;\n"
                "meta = (schema_version = chars(\"2.0\"));\n"
                "event_kind = chars(behavior);\n"
                "behavior = (layer = chars(network));\n"
                "carriers = ();\n",
                encoding="utf-8",
            )
            errors = pipeline.static_oml(path)
            self.assertTrue(any("ip_to_biguint must be preceded" in error for error in errors))
        finally:
            path.unlink(missing_ok=True)

    def test_static_oml_rejects_mapping_temp_and_event_id_top_level_projection(self):
        path = Path(self.id().replace("/", "_") + ".oml")
        try:
            path.write_text(
                "__mapping_id = chars(example.mapping.v2);\n"
                "attacker_entity = chars(\"\");\n"
                "victim_entity = chars(\"\");\n"
                "attacker_ip = chars(\"\");\n"
                "victim_ip = chars(\"\");\n"
                "event_id = chars(\"\");\n"
                "extensions = object {\n"
                "};\n"
                "meta = (schema_version = chars(\"2.0\"));\n"
                "event_kind = chars(behavior);\n"
                "behavior = (layer = chars(network));\n"
                "carriers = ();\n",
                encoding="utf-8",
            )
            errors = pipeline.static_oml(path)
            self.assertTrue(any("__mapping_id temporary is forbidden" in error for error in errors))
            self.assertTrue(any("unexpected top-level outputs" in error for error in errors))
        finally:
            path.unlink(missing_ok=True)

    def test_static_oml_accepts_retained_top_level_projection_block(self):
        path = Path(self.id().replace("/", "_") + ".oml")
        try:
            path.write_text(
                "__empty_chars = chars(\"\");\n"
                "extensions = object {\n"
                "};\n"
                "attacker_entity = read(option:[__empty_chars]);\n"
                "victim_entity = read(option:[__empty_chars]);\n"
                "attacker_ip = read(option:[__empty_chars]);\n"
                "victim_ip = read(option:[__empty_chars]);\n"
                "meta = (schema_version = chars(\"2.0\"));\n"
                "event_kind = chars(behavior);\n"
                "behavior = (layer = chars(network));\n"
                "carriers = ();\n",
                encoding="utf-8",
            )
            errors = pipeline.static_oml(path)
            self.assertFalse(any("unexpected top-level outputs" in error for error in errors))
        finally:
            path.unlink(missing_ok=True)

    def test_static_oml_rejects_source_private_duplicates(self):
        path = Path(self.id().replace("/", "_") + ".oml")
        try:
            path.write_text(
                "__time = read(time);\n"
                "meta = (schema_version = chars(\"2.0\"));\n"
                "event_kind = chars(behavior);\n"
                "behavior = (layer = chars(application));\n"
                "carriers = ();\n"
                "extensions = object { source_private = object { time = read(time); raw = read(raw); }; };\n",
                encoding="utf-8",
            )
            errors = pipeline.static_oml(path)
            self.assertTrue(any("source_private repeats standard-consumed" in error for error in errors))
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
