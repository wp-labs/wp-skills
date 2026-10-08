#!/usr/bin/env python3
"""Single package gate for the SDM behavior-event physical payload.

The gate intentionally performs one source-configured ``wparse batch``.  It
does not run the removed interim-doris validators or one validator per event.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SCHEMA = HERE.parent / "references" / "schemas" / "sdm-event-behavior-kafka.schema.json"
DORIS_DDL = HERE.parent / "references" / "contracts" / "031_sdm_event_behavior.sql"
DORIS_LOAD = HERE.parent / "references" / "contracts" / "032_routine_load_sdm_event_behavior.sql"
DORIS_JSONPATHS = [
    "$.meta.tenant_id", "$.meta.occur_time", "$.meta.event_id", "$.meta.ingest_time", "$.meta.parse_time",
    "$.meta.schema_version", "$.meta.mapping_id", "$.meta.data_source.vendor", "$.meta.data_source.product",
    "$.meta.data_source.category", "$.meta.data_source.instance_id", "$.meta.source_record.log_id",
    "$.meta.source_record.log_type", "$.meta.source_record.log_name", "$.meta.source_record.log_level",
    "$.meta.source_record.record_kind", "$.behavior.layer", "$.behavior.type", "$.behavior.operation",
    "$.behavior.outcome", "$.behavior.message", "$.subject.ref_id", "$.subject.entity_type",
    "$.object.ref_id", "$.object.entity_type", "$.observation.observer.ref_id",
    "$.observation.observer.entity_type", "$.observation.action", "$.observation.assertion.title",
    "$.observation.assertion.rule", "$.observation.assertion.conclusion", "$.observation.assertion.severity",
    "$.subject", "$.object", "$.carriers", "$.carriers[0].carrier_role", "$.facets", "$.observation",
    "$.extensions",
]
DORIS_VARCHAR_LIMITS = {
    "tenant_id": 128, "event_id": 128, "schema_version": 32, "mapping_id": 128,
    "vendor": 128, "product": 128, "data_source_category": 128, "collector_instance_id": 128,
    "log_id": 128, "log_type": 128, "log_name": 255, "log_level": 64, "record_kind": 32,
    "behavior_layer": 16, "behavior_type": 16, "behavior_operation": 64, "behavior_outcome": 16,
    "behavior_message": 4096, "subject_ref_id": 255, "subject_entity_type": 32,
    "object_ref_id": 255, "object_entity_type": 32, "observer_ref_id": 255,
    "observer_entity_type": 32, "observation_action": 16, "assertion_title": 1024,
    "assertion_rule": 128, "assertion_conclusion": 128, "assertion_severity": 64, "carrier_role": 64,
}
DORIS_VARIANT_COLUMNS = {"subject_detail", "object_detail", "carriers", "facets", "observation_detail", "extensions"}
DORIS_TIME_COLUMNS = {"occur_time", "ingest_time", "parse_time"}
DORIS_REQUIRED_COLUMNS = {"tenant_id", "occur_time", "event_id", "schema_version", "mapping_id"}
ALLOWED_CATEGORIES = {"auth", "network", "audit", "system", "alert"}
ALLOWED_LAYERS = {"network", "system", "application"}
ALLOWED_TYPES = {"appear", "read", "change", "disappear", "flow"}
ALLOWED_OUTCOMES = {"allowed", "denied", "success", "failed", "observed", "unknown", None}
ENTITY_TYPES = {
    "user", "account", "host", "endpoint", "process", "file", "service", "domain", "url",
    "device", "resource", "application", "cloud", "container", "certificate", "script",
}
OLD_ROOTS = {"roles_obj", "facets_obj", "source_finding_obj", "extensions_obj"}
RETAINED_TOP_LEVEL = {"attacker_entity", "victim_entity", "attacker_ip", "victim_ip", "occur_time"}
RETIRED_TOP_LEVEL = {"event_id"}
TEMP_RE = re.compile(r"__([A-Za-z_][A-Za-z0-9_]*)")
READ_RE = re.compile(r"\bread\(\s*([A-Za-z_][A-Za-z0-9_]*)")
READ_CALL_RE = re.compile(r"\bread\(\s*([^)]*)\)", re.S)
ASSIGN_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(?::[^=]+)?=")
RULE_RE = re.compile(r"\brule\s+([A-Za-z0-9_]+(?:/[A-Za-z0-9_]+)*)\s*\{")
OML_RULE_LINE_RE = re.compile(r"^\s*rule\s*:\s*(.*)$", re.M)
RULE_TARGET_RE = re.compile(r"^[A-Za-z0-9_]+/[A-Za-z0-9_./*-]+$")


def args_parser() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--package", required=True)
    p.add_argument("--sample", type=Path)
    p.add_argument("--source-config", type=Path, default=Path("topology/sources/wpsrc.toml"))
    p.add_argument("--source-file", help="file value under data/in_dat; defaults to sample's relative path")
    p.add_argument("--business", type=Path, default=Path("data/out_dat/all.json"))
    p.add_argument("--raw", type=Path, default=Path("data/out_dat/raw_log.json"))
    p.add_argument("--clear-output", action="store_true", help="remove business/raw output before batch and keep the new result")
    p.add_argument("--restore-output", action="store_true", help="restore output files after validation")
    p.add_argument("--run-batch", action="store_true")
    p.add_argument("--skip-parse", action="store_true", help="do not call debug parse; report I–N parse evidence as NOT_RUN")
    p.add_argument("--allow-remote", action="store_true")
    p.add_argument("--keep-evidence", action="store_true", help="keep transient .wpl-check parse evidence for review")
    p.add_argument("--skip-wpadm", action="store_true")
    return p.parse_args()


def rp(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def read_ndjson(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc.msg}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_no}: expected JSON object")
        records.append(value)
    return records


def run(command: list[str]) -> tuple[int, str]:
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    return result.returncode, result.stdout + result.stderr


def stage(stages: list[dict[str, Any]], name: str, status: str, detail: str = "", **extra: Any) -> None:
    item: dict[str, Any] = {"name": name, "status": status}
    if detail:
        item["detail"] = detail
    item.update(extra)
    stages.append(item)


def top_assignments(text: str) -> set[str]:
    body = text.split("\n---", 1)[1] if "\n---" in text else text
    roots: set[str] = set()
    depth = 0
    for line in body.splitlines():
        if depth == 0 and (match := ASSIGN_RE.match(line)):
            roots.add(match.group(1))
        # Braces inside quoted fmt templates are placeholders, not OML scopes.
        scope_text = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', "", line)
        depth += scope_text.count("{") - scope_text.count("}")
    return roots


def static_oml(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    roots = top_assignments(text)
    required = {
        "meta", "event_kind", "behavior", "carriers",
    }
    missing = sorted(required - roots)
    if missing:
        errors.append(f"required envelope roots missing: {missing}")
    old = sorted(OLD_ROOTS & roots)
    if old:
        errors.append(f"old envelope roots present: {old}")
    allowed = required | RETAINED_TOP_LEVEL | {"subject", "object", "facets", "observation", "extensions"}
    unexpected = sorted(name for name in roots - allowed if not name.startswith("__"))
    if unexpected:
        errors.append(f"unexpected top-level outputs: {unexpected}")
    if re.search(r"\b(?:schema_version|mapping_id|tenant_id|event_id|occur_time)\s*=", text) and "meta" not in roots:
        errors.append("identity/time fields must be nested under meta")
    if re.search(r"\b__mapping_id\b", text):
        errors.append("__mapping_id temporary is forbidden; assign meta.mapping_id directly")
    if re.search(r"\bschema_version\s*=\s*digit\(\s*1\s*\)", text):
        errors.append("old schema_version=digit(1) is forbidden; use chars(\"2.0\")")
    if re.search(r"\bdata_source\s*=.*?category\s*=\s*chars\(\s*['\"]?other['\"]?\s*\)", text, re.S):
        errors.append("data_source.category=other is forbidden")
    data_source_match = re.search(r"\bdata_source\s*=\s*object\s*\{(.*?)\n\s*\};", text, re.S)
    if data_source_match and not re.search(r"\binstance_id\s*=\s*read\(\s*__device_ip\s*\)", data_source_match.group(1)):
        errors.append("data_source.instance_id must read __device_ip")
    if not re.search(r"^\s*__device_ip\s*:\s*ip\s*=\s*read\(\s*wp_src_ip\s*\);\s*$", text, re.M):
        errors.append("__device_ip must be normalized from wp_src_ip")
    if re.search(r"\b(?:roles_obj|facets_obj|source_finding_obj|extensions_obj)\b", text):
        errors.append("legacy object names are forbidden in new OML")
    legacy_wrappers = sorted(set(re.findall(r"\blegacy_(?:roles|facets|finding|extensions|source_private)\b", text)))
    if legacy_wrappers:
        errors.append(f"legacy compatibility wrappers are forbidden: {legacy_wrappers}")
    if re.search(r"\bunmapped\s*=\s*object\s*\{", text):
        errors.append("extensions.unmapped compatibility bucket is forbidden; map each source field or use source_private")
    # source_private is only the lossless remainder. A source field already
    # consumed by the standard envelope must not be copied into it again.
    private_match = re.search(r"source_private\s*=\s*object\s*\{(.*?)\};", text, re.S)
    if private_match:
        private_fields = set(re.findall(r"=\s*read\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)", private_match.group(1)))
        outside_text = text[:private_match.start()] + text[private_match.end():]
        outside_fields: set[str] = set()
        for call in READ_CALL_RE.findall(outside_text):
            outside_fields.update(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", call))
        duplicated = sorted(private_fields & outside_fields)
        if duplicated:
            errors.append(f"source_private repeats standard-consumed source fields: {duplicated}")
    placeholders = sorted(set(re.findall(r"__no_[A-Za-z0-9_]+", text)))
    if placeholders:
        errors.append(f"placeholder temporary values are forbidden: {placeholders}")
    # Keep the leading ``__`` in both sets; otherwise every temporary read is
    # accidentally reported as undefined (the regex capture strips it).
    defined = {"__" + name for name in TEMP_RE.findall(text)}
    reads = {m.group(1) for m in READ_RE.finditer(text) if m.group(1).startswith("__")}
    undefined = sorted(reads - defined)
    if undefined:
        errors.append(f"undefined temporary reads: {undefined}")
    temporary_definitions: set[str] = set()
    temporary_uses: set[str] = set()
    for line in text.splitlines():
        definition = re.match(
            r"^\s*((?:__[A-Za-z_][A-Za-z0-9_]*\s*,\s*)*__[A-Za-z_][A-Za-z0-9_]*)(?:\s*:[^=]+)?\s*=",
            line,
        )
        rhs = line
        if definition:
            temporary_definitions.update(re.findall(r"__[A-Za-z_][A-Za-z0-9_]*", definition.group(1)))
            rhs = line[definition.end():]
        temporary_uses.update(re.findall(r"__[A-Za-z_][A-Za-z0-9_]*", rhs))
    unused_temporaries = sorted(temporary_definitions - temporary_uses)
    if unused_temporaries:
        errors.append(f"temporary values defined but never consumed: {unused_temporaries}")
    unused_query_outputs: list[str] = []
    query_re = re.compile(
        r"(?m)^\s*((?:__[A-Za-z_][A-Za-z0-9_]*\s*,\s*)*__[A-Za-z_][A-Za-z0-9_]*)\s*=\s*select\b[^;]*;"
    )
    for query in query_re.finditer(text):
        outputs = re.findall(r"__[A-Za-z_][A-Za-z0-9_]*", query.group(1))
        projected = text[query.end():]
        for output in outputs:
            if not re.search(rf"\b{re.escape(output)}\b", projected):
                unused_query_outputs.append(output)
    if unused_query_outputs:
        errors.append(f"knowledge-query outputs not projected: {sorted(set(unused_query_outputs))}")
    unmasked_ip_numbers = [
        line.strip()
        for line in text.splitlines()
        if "ip_to_biguint" in line and 'intranet_replace("202.106.0.0")' not in line
    ]
    if unmasked_ip_numbers:
        errors.append(
            "ip_to_biguint must be preceded by intranet_replace(\"202.106.0.0\"): "
            + "; ".join(unmasked_ip_numbers[:10])
        )
    normalized_ip_roles = set(re.findall(r"__(sip|dip|attacker_ip|victim_ip)\s*:\s*ip\s*=", text))
    for role in sorted(normalized_ip_roles):
        prefix = role.removesuffix("_ip")
        if not re.search(rf"__{re.escape(prefix)}_(?:country|province|city|continent|latitude|longitude)", text):
            errors.append(f"{role} is missing GeoIP enrichment query")
    return errors


def wpl_inventory(package: str) -> tuple[set[str], set[str], set[str], Path | None]:
    path = ROOT / "models" / "wpl" / package / "parse.wpl"
    if not path.exists():
        return set(), set(), set(), None
    text = path.read_text(encoding="utf-8")
    log_types = set(re.findall(r"\blog_type\s*:\s*\"([^\"]+)\"", text))
    rule_names = set(RULE_RE.findall(text))
    fields = set().union(*wpl_fields_by_rule(path).values()) if rule_names else set()
    # WPL uses this alias only to discriminate the JSON route. The original
    # log_type is projected to meta.source_record.log_type and is not a
    # private payload field.
    fields.discard("source_log_type")
    return log_types, rule_names, fields, path


def wpl_fields_by_rule(path: Path, sample_records: list[dict[str, Any]] | None = None) -> dict[str, set[str]]:
    """Return the actual captured output names for every WPL rule."""
    text = path.read_text(encoding="utf-8")
    result: dict[str, set[str]] = {}
    for match in RULE_RE.finditer(text):
        name = match.group(1)
        start = text.find("{", match.start())
        depth, index = 0, start
        while index < len(text):
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
                if depth == 0:
                    index += 1
                    break
            index += 1
        body = text[start:index]
        fields = {
            alias or source.rsplit("/", 1)[-1]
            for source, alias in re.findall(
                r"@([^,\s()<>\[\]]+?)(?:\[[^\]]+\])?(?::([A-Za-z_][A-Za-z0-9_]*))?(?=\s*[,\)])",
                body,
            )
        }
        fields.discard("source_log_type")
        # `_@*` is an anonymous wildcard capture used only to consume
        # unmodelled JSON members; it does not create a named WPL field.
        fields.discard("*")
        # ``json()`` without a field list forwards the complete JSON object.
        # Its contract therefore comes from the actual sample keys; treating
        # it as zero captured fields creates a false-positive coverage pass.
        if re.search(r"\bjson\(\s*\)", body) and sample_records:
            framework_fields = {
                "log_desc", "log_type", "raw_msg", "wp_event_id", "wp_src_key",
                "wp_src_ip", "wp_src_val", "wp_source_type",
            }
            for record in sample_records:
                fields.update(set(record) - framework_fields)
        result[name] = fields
    return result


def oml_reads_by_rule(models: list[Path]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for path in models:
        text = path.read_text(encoding="utf-8")
        reads: set[str] = set()
        for call in READ_CALL_RE.findall(text):
            reads.update(
                token for token in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", call)
                if not token.startswith("__") and token not in {"option", "is_empty"}
            )
        for targets in oml_rule_targets([path]).values():
            for target in targets:
                result.setdefault(target.partition("/")[2], set()).update(reads)
    return result


def oml_inventory(package: str) -> tuple[list[Path], set[str]]:
    root = ROOT / "models" / "oml" / package
    # ``raw_log`` is the independent one-to-one raw side route, not a
    # behavior envelope model and therefore has no behavior Schema to check.
    models = sorted(
        p for p in root.rglob("adm.oml")
        if "ignore" not in p.parts and p.parent.name != "raw_log"
    ) if root.exists() else []
    reads: set[str] = set()
    for path in models:
        text = path.read_text(encoding="utf-8")
        # Capture every source field in read(option:[a, b]) rather than only
        # the first token (``option``).  Temporary names are derived values,
        # not WPL source fields, and are intentionally excluded.
        for call in READ_CALL_RE.findall(text):
            for name in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", call):
                if not name.startswith("__") and name not in {"option"}:
                    reads.add(name)
    return models, reads


def oml_rule_targets(models: list[Path]) -> dict[Path, list[str]]:
    targets: dict[Path, list[str]] = {}
    for path in models:
        lines = path.read_text(encoding="utf-8").splitlines()
        values: list[str] = []
        in_header = False
        for line in lines:
            if line.strip() == "---":
                if in_header:
                    break
                continue
            match = OML_RULE_LINE_RE.match(line) if not in_header else None
            if match:
                in_header = True
                inline = match.group(1).strip()
                if inline and RULE_TARGET_RE.fullmatch(inline):
                    values.append(inline)
                continue
            if in_header:
                value = line.strip()
                if RULE_TARGET_RE.fullmatch(value):
                    values.append(value)
        targets[path] = list(dict.fromkeys(values))
    return targets


def numeric_or_datetime(value: Any, *, required: bool) -> bool:
    if value is None:
        return not required
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return value >= 0
    if isinstance(value, str):
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return True
        except ValueError:
            return False
    return False


def ref_id_error(where: str, node: Any) -> list[str]:
    if node is None:
        return []
    if not isinstance(node, dict):
        return [f"{where} must be object or null"]
    et, rid = node.get("entity_type"), node.get("ref_id")
    errors: list[str] = []
    if et not in ENTITY_TYPES:
        errors.append(f"{where}.entity_type invalid: {et!r}")
    if not isinstance(rid, str) or not rid.strip():
        errors.append(f"{where}.ref_id must be non-empty string")
    elif et and not rid.startswith(et + "::"):
        errors.append(f"{where}.ref_id must start with {et}::")
    typed = [name for name in ENTITY_TYPES if node.get(name) not in (None, {}, [])]
    if et and et not in typed:
        errors.append(f"{where} must contain its {et} detail object, got {typed}")
    return errors


def validate_behavior(event: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if event.get("event_kind") != "behavior":
        errors.append("event_kind must be behavior")
    if any(k in event for k in OLD_ROOTS):
        errors.append("legacy envelope root present")
    retired = sorted(RETIRED_TOP_LEVEL & event.keys())
    if retired:
        errors.append(f"retired top-level outputs present: {retired}")
    meta = event.get("meta")
    if not isinstance(meta, dict):
        return ["meta must be object", *errors]
    for name in ("schema_version", "tenant_id", "event_id", "occur_time", "mapping_id"):
        if meta.get(name) in (None, ""):
            errors.append(f"meta.{name} required")
    if meta.get("schema_version") != "2.0":
        errors.append(f"meta.schema_version must be '2.0', got {meta.get('schema_version')!r}")
    for name, required in (("occur_time", True), ("ingest_time", False), ("parse_time", False)):
        if not numeric_or_datetime(meta.get(name), required=required):
            errors.append(f"meta.{name} must be non-negative Unix milliseconds")
    category = (meta.get("data_source") or {}).get("category") if isinstance(meta.get("data_source"), dict) else None
    if category not in ALLOWED_CATEGORIES:
        errors.append(f"meta.data_source.category invalid: {category!r}")
    behavior = event.get("behavior")
    if not isinstance(behavior, dict):
        errors.append("behavior must be object")
    else:
        if behavior.get("layer") not in ALLOWED_LAYERS:
            errors.append(f"behavior.layer invalid: {behavior.get('layer')!r}")
        if behavior.get("type") not in ALLOWED_TYPES:
            errors.append(f"behavior.type invalid: {behavior.get('type')!r}")
        if behavior.get("outcome") not in ALLOWED_OUTCOMES:
            errors.append(f"behavior.outcome invalid: {behavior.get('outcome')!r}")
    errors.extend(ref_id_error("subject", event.get("subject")))
    errors.extend(ref_id_error("object", event.get("object")))
    carriers = event.get("carriers")
    if not isinstance(carriers, list):
        errors.append("carriers must be array")
    else:
        for i, carrier in enumerate(carriers):
            if not isinstance(carrier, dict):
                errors.append(f"carriers[{i}] must be object")
            else:
                rid = carrier.get("ref_id")
                et = carrier.get("entity_type")
                if not isinstance(rid, str) or not rid.strip():
                    errors.append(f"carriers[{i}].ref_id must be non-empty")
                elif et and not rid.startswith(str(et) + "::"):
                    errors.append(f"carriers[{i}].ref_id prefix mismatch")
    observation = event.get("observation")
    if observation is not None:
        if not isinstance(observation, dict):
            errors.append("observation must be object")
        else:
            refs = observation.get("evidence_refs")
            if not isinstance(refs, list) or not refs:
                errors.append("observation.evidence_refs must be non-empty array")
            action = observation.get("action")
            assertion = observation.get("assertion")
            if action in {"detect", "assess"} and not isinstance(assertion, dict):
                errors.append(f"observation.action={action} requires assertion")
            if action == "record" and assertion is not None:
                errors.append("observation.action=record must not carry assertion")
            outcome = (behavior or {}).get("outcome") if isinstance(behavior, dict) else None
            conclusion = assertion.get("conclusion") if isinstance(assertion, dict) else None
            if outcome in {"allowed", "denied"} and conclusion in (None, ""):
                errors.append(f"outcome={outcome} requires assertion.conclusion")
            if outcome == "denied" and str(conclusion).lower() not in {"deny", "denied", "block", "blocked", "drop", "reject", "丢弃", "阻断", "拒绝"}:
                errors.append(f"denied outcome conflicts with conclusion={conclusion!r}")
            if outcome == "allowed" and str(conclusion).lower() not in {"allow", "allowed", "pass", "permit", "accept", "通过", "放行", "允许"}:
                errors.append(f"allowed outcome conflicts with conclusion={conclusion!r}")
    elif isinstance(behavior, dict) and behavior.get("outcome") in {"allowed", "denied"}:
        errors.append(f"outcome={behavior.get('outcome')} requires observation.assertion.conclusion")
    extensions = event.get("extensions")
    if extensions is not None and not isinstance(extensions, dict):
        errors.append("extensions must be object")
    elif isinstance(extensions, dict):
        extra = sorted(set(extensions) - {"source_private", "profiles", "enrichments"})
        if extra:
            errors.append(f"unsupported extensions roots: {extra}")
    return errors


def validate_raw(event: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for name in ("tenant_id", "occur_time", "event_id", "raw_msg_digest"):
        if event.get(name) in (None, ""):
            errors.append(f"raw.{name} required")
    if not numeric_or_datetime(event.get("occur_time"), required=True):
        errors.append("raw.occur_time must be 13-digit Unix ms or ISO datetime")
    digest = event.get("raw_msg_digest")
    algo = str(event.get("digest_algo") or ("md5" if isinstance(digest, str) and len(digest) == 32 else "sha256")).lower()
    if algo not in {"md5", "sha256"} or not isinstance(digest, str):
        errors.append("raw digest algorithm/value invalid")
    elif len(digest) != (32 if algo == "md5" else 64) or not re.fullmatch(r"[0-9a-fA-F]+", digest):
        errors.append(f"raw digest is not {algo} hex")
    elif isinstance(event.get("raw_msg"), str) and hashlib.new(algo, event["raw_msg"].encode()).hexdigest().lower() != digest.lower():
        errors.append("raw digest does not match raw_msg")
    return errors


def jsonschema_errors(event: dict[str, Any]) -> list[str]:
    try:
        import jsonschema
    except ImportError:
        return []
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    return [e.message for e in jsonschema.Draft202012Validator(schema).iter_errors(event)]


def nested(value: Any, *keys: str) -> Any:
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def doris_time_error(column: str, value: Any, *, required: bool) -> str | None:
    if value is None:
        return f"Doris {column} is required" if required else None
    if isinstance(value, str):
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return None
        except ValueError:
            return f"Doris {column} must be a Unix seconds/milliseconds number or ISO datetime"
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return f"Doris {column} must be a Unix seconds/milliseconds number or ISO datetime"
    seconds = float(value) / 1000 if float(value) >= 100_000_000_000 else float(value)
    try:
        datetime.fromtimestamp(seconds)
    except (OverflowError, OSError, ValueError):
        return f"Doris {column} cannot convert to DATETIME(3): {value!r}"
    return None


def doris_projection_errors(event: dict[str, Any]) -> list[str]:
    """Simulate the production JSONPath projection before Doris ingestion."""
    meta = event.get("meta") if isinstance(event.get("meta"), dict) else {}
    behavior = event.get("behavior") if isinstance(event.get("behavior"), dict) else {}
    subject, obj = event.get("subject"), event.get("object")
    observation = event.get("observation")
    first_carrier = event.get("carriers", [None])
    first_carrier = first_carrier[0] if isinstance(first_carrier, list) and first_carrier else None
    values = {
        "tenant_id": meta.get("tenant_id"), "event_id": meta.get("event_id"),
        "schema_version": meta.get("schema_version"), "mapping_id": meta.get("mapping_id"),
        "vendor": nested(meta, "data_source", "vendor"), "product": nested(meta, "data_source", "product"),
        "data_source_category": nested(meta, "data_source", "category"),
        "collector_instance_id": nested(meta, "data_source", "instance_id"),
        "log_id": nested(meta, "source_record", "log_id"), "log_type": nested(meta, "source_record", "log_type"),
        "log_name": nested(meta, "source_record", "log_name"), "log_level": nested(meta, "source_record", "log_level"),
        "record_kind": nested(meta, "source_record", "record_kind"), "behavior_layer": behavior.get("layer"),
        "behavior_type": behavior.get("type"), "behavior_operation": behavior.get("operation"),
        "behavior_outcome": behavior.get("outcome"), "behavior_message": behavior.get("message"),
        "subject_ref_id": nested(subject, "ref_id"), "subject_entity_type": nested(subject, "entity_type"),
        "object_ref_id": nested(obj, "ref_id"), "object_entity_type": nested(obj, "entity_type"),
        "observer_ref_id": nested(observation, "observer", "ref_id"),
        "observer_entity_type": nested(observation, "observer", "entity_type"),
        "observation_action": nested(observation, "action"),
        "assertion_title": nested(observation, "assertion", "title"),
        "assertion_rule": nested(observation, "assertion", "rule"),
        "assertion_conclusion": nested(observation, "assertion", "conclusion"),
        "assertion_severity": nested(observation, "assertion", "severity"),
        "carrier_role": nested(first_carrier, "carrier_role"),
    }
    errors: list[str] = []
    for required in ("tenant_id", "event_id", "schema_version", "mapping_id"):
        value = values[required]
        if not isinstance(value, str) or not value.strip():
            errors.append(f"Doris {required} must be a non-empty string")
    for column, limit in DORIS_VARCHAR_LIMITS.items():
        value = values.get(column)
        if value is not None and not isinstance(value, str):
            errors.append(f"Doris {column} must be string or null")
        elif isinstance(value, str) and len(value) > limit:
            errors.append(f"Doris {column} exceeds VARCHAR({limit}): {len(value)}")
    for column, required in (("occur_time", True), ("ingest_time", False), ("parse_time", False)):
        error = doris_time_error(column, meta.get(column), required=required)
        if error:
            errors.append(error)
    for column, value in (
        ("subject_detail", subject), ("object_detail", obj), ("carriers", event.get("carriers")),
        ("facets", event.get("facets")), ("observation_detail", observation), ("extensions", event.get("extensions")),
    ):
        if value is not None:
            try:
                json.dumps(value, ensure_ascii=False)
            except (TypeError, ValueError):
                errors.append(f"Doris {column} is not JSON-serializable VARIANT data")
    return errors


def doris_contract_errors() -> list[str]:
    """Check the checked-in behavior DDL and Routine Load projection together."""
    errors: list[str] = []
    if not DORIS_DDL.exists() or not DORIS_LOAD.exists():
        return ["behavior Doris DDL/Routine Load contract is missing"]
    ddl = DORIS_DDL.read_text(encoding="utf-8")
    load = DORIS_LOAD.read_text(encoding="utf-8")
    definitions = {
        name: (kind.upper(), size, bool(not_null))
        for name, kind, size, not_null in re.findall(
            r"`([A-Za-z_][A-Za-z0-9_]*)`\s+(VARCHAR|DATETIME|VARIANT)(?:\((\d+)\))?(\s+NOT NULL)?",
            ddl,
            re.I,
        )
    }
    columns = set(definitions)
    required_columns = set(DORIS_VARCHAR_LIMITS) | {
        "occur_time", "ingest_time", "parse_time", "subject_detail", "object_detail", "carriers",
        "facets", "observation_detail", "extensions",
    }
    missing_columns = sorted(required_columns - columns)
    if missing_columns:
        errors.append(f"Doris behavior columns missing: {missing_columns}")
    for column, limit in DORIS_VARCHAR_LIMITS.items():
        if column in definitions and definitions[column][:2] != ("VARCHAR", str(limit)):
            errors.append(f"Doris {column} must be VARCHAR({limit})")
    for column in DORIS_TIME_COLUMNS:
        if column in definitions and definitions[column][:2] != ("DATETIME", "3"):
            errors.append(f"Doris {column} must be DATETIME(3)")
    for column in DORIS_VARIANT_COLUMNS:
        if column in definitions and definitions[column][0] != "VARIANT":
            errors.append(f"Doris {column} must be VARIANT")
    for column in DORIS_REQUIRED_COLUMNS:
        if column in definitions and not definitions[column][2]:
            errors.append(f"Doris {column} must be NOT NULL")
    path_match = re.search(r'"jsonpaths"\s*=\s*"((?:\\.|[^"\\])*)"', load)
    paths: list[str] = []
    if path_match:
        try:
            paths = json.loads(json.loads('"' + path_match.group(1) + '"'))
        except (json.JSONDecodeError, TypeError):
            errors.append("Routine Load jsonpaths is not valid encoded JSON")
    if paths != DORIS_JSONPATHS:
        errors.append("Routine Load JSONPath order/content does not match the 39-column production projection")
    contract_checks = {
        "production table": "CREATE TABLE IF NOT EXISTS sdm2_log.sdm_event_behavior" in ddl,
        "unique key": "UNIQUE KEY(`tenant_id`, `occur_time`, `event_id`)" in ddl,
        "production routine": "CREATE ROUTINE LOAD sdm2_log.sdm_event_behavior_load_v1 ON sdm_event_behavior" in load,
        "WITH APPEND": "WITH APPEND" in load,
        "seconds/milliseconds conversion": "100000000000" in load and "decimal(18,6)" in load.lower(),
        "Kafka topic": '"kafka_topic"="sdm_event_behavior"' in load,
        "Kafka broker": '"kafka_broker_list"="kafka:9092"' in load,
        "strict mode": '"strict_mode"="false"' in load,
        "UTC timezone": '"timezone"="Etc/UTC"' in load,
    }
    errors.extend(f"Doris contract missing {name}" for name, ok in contract_checks.items() if not ok)
    if "FROM KAFKA" not in load or '"format"="json"' not in load:
        errors.append("Routine Load must consume one behavior JSON object")
    return errors


def configure_source(config: Path, source_file: str) -> str:
    original = config.read_text(encoding="utf-8")
    pattern = re.compile(r'(key\s*=\s*"gen_file"\s*\n\s*enable\s*=\s*true.*?\[sources\.params\].*?\n\s*file\s*=\s*")[^"]*(")', re.S)
    updated, count = pattern.subn(lambda m: m.group(1) + source_file + m.group(2), original, count=1)
    if count != 1:
        raise ValueError(f"enabled gen_file source with file= not found in {config}")
    config.write_text(updated, encoding="utf-8")
    return original


def main() -> int:
    args = args_parser()
    stages: list[dict[str, Any]] = []
    sample = rp(args.sample) if args.sample else ROOT / "data" / "in_dat" / args.package / "gen.dat"
    config, business_path, raw_path = rp(args.source_config), rp(args.business), rp(args.raw)
    if not sample.exists():
        stage(stages, "sample_input", "NEEDS_INPUT", f"sample not found: {sample}")
        print(json.dumps({"profile": "wpl-rule-check-v5", "package": args.package, "stages": stages}, ensure_ascii=False, indent=2))
        return 2
    input_lines = [line for line in sample.read_text(encoding="utf-8").splitlines() if line.strip()]
    stage(stages, "sample_input", "OK", records=len(input_lines), sample=str(sample))

    if args.skip_wpadm:
        stage(stages, "wpadm", "NOT_RUN", "explicitly skipped")
    else:
        rc, output = run(["wpadm", "check", "--only-fail"])
        stage(stages, "wpadm", "OK" if rc == 0 else "FAIL", output[-2000:])
    diff_rc, diff_output = run(["git", "diff", "--check"])
    stage(stages, "git_diff_check", "OK" if diff_rc == 0 else "FAIL", diff_output[-2000:])
    doris_errors = doris_contract_errors()
    stage(stages, "doris_contract", "FAIL" if doris_errors else "OK", "; ".join(doris_errors))

    models, oml_reads = oml_inventory(args.package)
    static_errors = [(str(path), error) for path in models for error in static_oml(path)]
    stage(stages, "oml_static", "FAIL" if static_errors else ("NEEDS_INPUT" if not models else "OK"),
          "; ".join(f"{p}: {e}" for p, e in static_errors[:20]), models=len(models))
    log_types, rule_names, wpl_fields, wpl_path = wpl_inventory(args.package)
    if wpl_path is None:
        stage(stages, "wpl_inventory", "NEEDS_INPUT", f"missing {ROOT / 'models/wpl' / args.package / 'parse.wpl'}")
    else:
        stage(stages, "wpl_inventory", "OK", rule_count=len(rule_names), log_type_count=len(log_types), captured_fields=len(wpl_fields), path=str(wpl_path))
        targets = oml_rule_targets(models)
        routing_errors = []
        for model, model_targets in targets.items():
            if not model_targets:
                routing_errors.append(f"{model}: missing rule header")
                continue
            for target in model_targets:
                if "*" in target:
                    routing_errors.append(f"{model}: wildcard rule target {target!r} is forbidden; use the exact WPL rule")
                    continue
                target_package, _, target_rule = target.partition("/")
                if target_package != args.package or target_rule not in rule_names:
                    routing_errors.append(f"{model}: rule target {target!r} not found in {args.package}/parse.wpl")
        stage(stages, "rule_routing", "FAIL" if routing_errors else "OK", "; ".join(routing_errors[:20]), checked=len(targets))
        sample_records: list[dict[str, Any]] = []
        try:
            sample_records = read_ndjson(sample)
        except ValueError:
            # Non-JSON source samples cannot contribute keys to a wildcard
            # json() rule; the runtime parse stage remains authoritative.
            pass
        per_rule_fields = wpl_fields_by_rule(wpl_path, sample_records)
        per_rule_reads = oml_reads_by_rule(models)
        per_rule_missing = {
            rule: sorted(fields - per_rule_reads.get(rule, set()))
            for rule, fields in per_rule_fields.items()
            if not rule.startswith("ignore") and fields - per_rule_reads.get(rule, set())
        }
        stage(
            stages,
            "per_rule_field_coverage",
            "FAIL" if per_rule_missing else "OK",
            "; ".join(f"{rule}: {fields}" for rule, fields in sorted(per_rule_missing.items())[:30]),
            checked=len([r for r in per_rule_fields if not r.startswith("ignore")]),
        )
        missing_reads = sorted(wpl_fields - oml_reads)
        stage(stages, "oml_coverage", "OK" if not missing_reads else "NEEDS_INPUT",
              "all captured fields are consumed or explicitly documented" if not missing_reads else f"WPL fields not read by OML: {missing_reads}",
              captured=len(wpl_fields), consumed=len(wpl_fields & oml_reads))

    parse_status = "NOT_RUN"
    if not args.skip_parse and wpl_path is not None:
        evidence = ROOT / ".wpl-check" / f"parse-{args.package}.json"
        command = [sys.executable, str(HERE / "parse_wpl.py"), "--wpl", str(wpl_path), "--logs", str(sample), "--output", str(evidence)]
        if args.allow_remote:
            command.append("--allow-remote")
        rc, output = run(command)
        parse_status = "OK" if rc == 0 else ("NOT_RUN" if rc == 2 else "FAIL")
        evidence_doc: dict[str, Any] = {}
        if evidence.exists():
            try:
                evidence_doc = json.loads(evidence.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                evidence_doc = {"status": "FAIL", "error": "evidence JSON is invalid"}
        stage(
            stages,
            "wpl_debug_parse",
            parse_status,
            output[-2000:],
            evidence=str(evidence),
            evidence_summary=evidence_doc.get("evidence", {}),
        )
        if not args.keep_evidence:
            evidence.unlink(missing_ok=True)
            try:
                evidence.parent.rmdir()
            except OSError:
                pass
    else:
        stage(stages, "wpl_debug_parse", "NOT_RUN", "explicitly skipped" if args.skip_parse else "WPL is missing")

    original_source: str | None = None
    batch_status = "NOT_RUN"
    batch_completed = False
    batch_output = ""
    snapshots = {p: p.read_bytes() for p in (business_path, raw_path) if p.exists()}
    if args.run_batch:
        if args.clear_output:
            for path in (business_path, raw_path):
                if path.exists():
                    path.unlink()
        source_rel = args.source_file
        if not source_rel:
            try:
                source_rel = str(sample.relative_to(ROOT / "data" / "in_dat"))
            except ValueError:
                source_rel = sample.name
        try:
            original_source = configure_source(config, source_rel)
            rc, output = run(["wparse", "batch"])
            batch_output = output
            lowered = output.lower()
            runtime_unavailable = any(
                marker in lowered
                for marker in (
                    "allbrokersdown",
                    "all brokers down",
                    "create kafka topic failed",
                    "sink error",
                    "data distribution failed",
                    "connection refused",
                    "timed out",
                    "provider not initialized",
                    "reload provider failed",
                    "create postgres pool failed",
                    "operation not permitted",
                )
            )
            if rc == 0:
                batch_status, batch_completed = "OK", True
            elif runtime_unavailable:
                batch_status = "NOT_RUN"
            else:
                batch_status = "FAIL"
            stage(stages, "wparse_batch", batch_status, output[-3000:])
            provider_markers = ("provider not initialized", "reload provider failed", "create postgres pool failed", "operation not permitted")
            stage(stages, "enrichment_runtime", "NOT_RUN" if any(m in output.lower() for m in provider_markers) else "OK",
                  "GeoIP/asset provider unavailable" if any(m in output.lower() for m in provider_markers) else "provider initialization did not fail")
        except (OSError, ValueError) as exc:
            stage(stages, "wparse_batch", "FAIL", str(exc))
        finally:
            if original_source is not None:
                config.write_text(original_source, encoding="utf-8")
    else:
        stage(stages, "wparse_batch", "NOT_RUN", "explicitly skipped")

    business = read_ndjson(business_path)
    raw = read_ndjson(raw_path)
    ignore_count = len(re.findall(
        rf"oml proc suc! ProcMeta wpl:{re.escape(args.package)}/ignore[A-Za-z0-9_]*\b",
        batch_output,
    ))
    if batch_completed:
        count_ok = len(business) == len(raw) and len(business) + ignore_count == len(input_lines)
        stage(stages, "double_output_count", "OK" if count_ok else "FAIL",
              f"business={len(business)} raw={len(raw)} ignore={ignore_count} input={len(input_lines)}",
              business=len(business), raw=len(raw), ignore=ignore_count, input=len(input_lines))
    else:
        stage(stages, "double_output_count", "NOT_RUN", "batch did not complete; output counts are not evidence",
              business=len(business), raw=len(raw), input=len(input_lines))
    event_errors = []
    doris_output_errors = []
    for i, event in enumerate(business, 1):
        event_errors.extend(f"business:{i}: {e}" for e in [*jsonschema_errors(event), *validate_behavior(event)])
        doris_output_errors.extend(f"business:{i}: {e}" for e in doris_projection_errors(event))
    for i, event in enumerate(raw, 1):
        event_errors.extend(f"raw:{i}: {e}" for e in validate_raw(event))
    behavior_output_status = "FAIL" if event_errors else ("OK" if business else "NOT_RUN")
    stage(stages, "behavior_schema_and_projection", behavior_output_status,
          "; ".join(event_errors[:30]) or ("no business output to validate" if not business else ""),
          checked_business=len(business), checked_raw=len(raw))
    doris_output_status = "FAIL" if doris_output_errors else ("OK" if business else "NOT_RUN")
    stage(stages, "doris_output_projection", doris_output_status,
          "; ".join(doris_output_errors[:30]) or ("no business output to project" if not business else ""),
          checked_business=len(business), table="sdm2_log.sdm_event_behavior")
    if batch_completed:
        raw_messages = Counter(str(item.get("raw_msg") or "") for item in raw)
        input_counter = Counter(input_lines)
        correlation = []
        if any(raw_messages[value] > count for value, count in input_counter.items()) or any(value not in input_counter for value in raw_messages):
            correlation.append("raw_msg contains records not present in sample input")
        if sum(raw_messages.values()) + ignore_count != sum(input_counter.values()):
            correlation.append("business/raw records plus ignore count do not cover sample input")
        business_ids = Counter(str(item.get("meta", {}).get("event_id") or "") for item in business)
        raw_ids = Counter(str(item.get("event_id") or "") for item in raw)
        if business_ids != raw_ids:
            correlation.append("business meta.event_id and raw event_id multisets differ")
        stage(stages, "input_output_correlation", "FAIL" if correlation else "OK", "; ".join(correlation))
    elif args.run_batch:
        stage(stages, "input_output_correlation", "NOT_RUN", "batch did not complete")

    if args.restore_output:
        for path in (business_path, raw_path):
            if path.exists():
                path.unlink()
        for path, content in snapshots.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    report = {"profile": "wpl-rule-check-v5", "package": args.package, "stages": stages, "output": {"business": str(business_path), "raw": str(raw_path)}}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if any(item["status"] == "FAIL" for item in stages):
        return 1
    if any(item["status"] == "NEEDS_INPUT" for item in stages):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
