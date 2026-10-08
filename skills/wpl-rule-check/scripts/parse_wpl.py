#!/usr/bin/env python3
"""Call WarpParse debug parse per source record and save I–N evidence."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

LOCAL = "http://127.0.0.1:8081/api/debug/parse"
REMOTE = "https://station.warpparse.ai/api/debug/parse"


class ParseHTTPError(Exception):
    """An HTTP response from the parser, including its response body."""

    def __init__(self, url: str, status: int, body: str):
        self.url = url
        self.status = status
        self.body = body
        super().__init__(f"{url}: HTTP {status}: {body[:500]}")


def post(url: str, payload: dict, timeout: float):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ParseHTTPError(url, exc.code, body) from exc


def unwrap(value: Any) -> Any:
    """Unwrap common debug API envelopes without changing the raw response."""
    if isinstance(value, dict):
        for key in ("data", "result", "parsed", "output"):
            child = value.get(key)
            if isinstance(child, (dict, list)):
                return unwrap(child)
        formatted = value.get("format_json")
        if isinstance(formatted, str):
            try:
                return unwrap(json.loads(formatted))
            except json.JSONDecodeError:
                pass
    return value


def runtime_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int) and not isinstance(value, bool):
        return "digit"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "chars"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def flatten_fields(value: Any, prefix: str = "") -> dict[str, dict[str, Any]]:
    """Create a compact field/value/type inventory for I–N review."""
    fields: dict[str, dict[str, Any]] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            fields[path] = {"value": child, "runtime_type": runtime_type(child)}
            if isinstance(child, (dict, list)):
                fields.update(flatten_fields(child, path))
    elif isinstance(value, list):
        for child in value:
            fields.update(flatten_fields(child, prefix))
    return fields


def evidence_summary(result: Any) -> dict[str, Any]:
    parsed = unwrap(result)
    records = parsed if isinstance(parsed, list) else [parsed]
    hits = []
    for record in records:
        if not isinstance(record, dict):
            hits.append({"rule": None, "fields": {}, "value": record, "runtime_type": runtime_type(record)})
            continue
        rule = next((record.get(k) for k in ("rule", "rule_name", "matched_rule", "hit_rule") if record.get(k)), None)
        hits.append({"rule": rule, "fields": flatten_fields(record)})
    return {"record_count": len(records), "hits": hits}


def parse_one(wpl: str, log: str, urls: list[str], timeout: float) -> dict[str, Any]:
    """Parse exactly one source record, trying the configured endpoints."""
    payload = {"rules": wpl, "logs": log}
    failures: list[str] = []
    for url in urls:
        try:
            result = post(url, payload, timeout)
            return {"status": "OK", "endpoint": url, "response": result}
        except ParseHTTPError as exc:
            # A 4xx is a deterministic WPL/sample error. Retrying the same
            # record remotely only hides the useful parser diagnostic.
            return {"status": "FAIL", "error": str(exc)}
        except ValueError as exc:
            return {"status": "FAIL", "error": f"{url}: invalid JSON response: {exc}"}
        except (OSError, urllib.error.URLError) as exc:
            failures.append(f"{url}: {exc}")
    return {"status": "NOT_RUN", "errors": failures}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wpl", type=Path, required=True)
    parser.add_argument("--logs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--endpoint", choices=("auto", "local", "remote"), default="auto")
    parser.add_argument("--allow-remote", action="store_true")
    parser.add_argument("--timeout", type=float, default=10)
    args = parser.parse_args()

    wpl = args.wpl.read_text(encoding="utf-8")
    logs = [line for line in args.logs.read_text(encoding="utf-8").splitlines() if line.strip()]
    urls = [LOCAL] if args.endpoint == "local" else [REMOTE] if args.endpoint == "remote" else [LOCAL]
    if args.endpoint == "auto" and args.allow_remote:
        urls.append(REMOTE)
    if not logs:
        failures = ["logs file contains no non-empty records"]
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"status": "FAIL", "errors": failures}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "FAIL", "errors": failures}, ensure_ascii=False))
        return 1

    # The debug endpoint accepts one raw record per request. Sending a whole
    # newline-delimited sample as one `logs` value makes the endpoint attempt
    # to parse the second line as a continuation and return HTTP 400. Parse
    # records independently; bounded concurrency keeps I–N evidence fast.
    results: list[dict[str, Any] | None] = [None] * len(logs)
    workers = min(8, len(logs))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(parse_one, wpl, log, urls, args.timeout): index for index, log in enumerate(logs)}
        for future in as_completed(futures):
            results[futures[future]] = future.result()

    entries = [{"line_no": index + 1, "log": log, **(result or {"status": "FAIL", "error": "missing parser result"})}
               for index, (log, result) in enumerate(zip(logs, results))]
    successful = [entry for entry in entries if entry["status"] == "OK"]
    failed = [entry for entry in entries if entry["status"] == "FAIL"]
    unavailable = [entry for entry in entries if entry["status"] == "NOT_RUN"]
    hits: list[dict[str, Any]] = []
    for entry in successful:
        summary = evidence_summary(entry["response"])
        for hit in summary["hits"]:
            hits.append({"line_no": entry["line_no"], **hit})

    if failed:
        status = "FAIL"
    elif unavailable:
        # A mixed result is still NOT_RUN only when no record produced parser
        # evidence; successful records remain available in the report.
        status = "NOT_RUN" if not successful else "FAIL"
    else:
        status = "OK"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "status": status,
        "evidence": {"record_count": len(hits), "input_count": len(logs), "hits": hits},
        "records": entries,
    }
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "input_count": len(logs), "ok": len(successful), "fail": len(failed), "not_run": len(unavailable)}, ensure_ascii=False))
    return 0 if status == "OK" else (2 if status == "NOT_RUN" else 1)


if __name__ == "__main__":
    raise SystemExit(main())
