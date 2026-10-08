#!/usr/bin/env python3
"""Validate one raw sample and one WPL/OML pair in a copied local WarpParse project."""
from __future__ import annotations
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
ASSET = SKILL / 'assets/minimal-wparse'
SCHEMA = SKILL / 'references/schemas/sdm-event-behavior-kafka.schema.json'
COMPAT = {'attacker_entity', 'victim_entity', 'attacker_ip', 'victim_ip', 'occur_time'}


def records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def static_errors(sample: dict, wpl: str, oml: str) -> list[str]:
    errors = []
    fields = set(sample)
    captures = dict(re.findall(r'\b(?:chars|digit|float|ip|time_timestamp|time)@([A-Za-z_]\w*)(?::([A-Za-z_]\w*))?', wpl))
    captured = {alias or src for src, alias in captures.items()} | set(re.findall(r'\b(?:chars|digit|float|ip|time_timestamp|time):([A-Za-z_]\w*)', wpl))
    missing = fields - set(captures)
    if missing: errors.append(f'WPL missing JSON fields: {sorted(missing)}')
    if not re.search(r'#\[tag\([^\n]+\),\s*copy_event_parse\(rule:\s*"raw_log/raw_log"\)\]\s*rule\s+', wpl):
        errors.append('rule-level tag/raw annotation missing')
    if re.search(r'f_chars_has\(\s*(?:audit_log|log|message)\s*,', wpl):
        errors.append('f_chars_has cannot test a substring inside embedded text')
    roots = set(re.findall(r'^([a-z][a-z_0-9]*)\s*(?::\s*array)?\s*=', oml, re.M))
    needed = {'meta','event_kind','behavior','carriers'} | COMPAT
    if needed - roots: errors.append(f'OML missing roots: {sorted(needed-roots)}')
    if 'event_id' in roots or 'event' in roots: errors.append('forbidden OML root event/event_id')
    if 'subject = null' in oml or 'object = null' in oml or 'carriers = ()' in oml:
        errors.append('invalid OML null/array syntax')
    if re.search(r'\b\w+\s*:\s*\{', oml): errors.append('JSON-style object syntax')
    if re.search(r'\b\w+\s*=\s*__\w+\s*;', oml): errors.append('bare temporary value')
    if not re.search(r'\btype\s*=\s*chars\(', oml): errors.append('behavior.type missing')
    reads = set(re.findall(r'\bread\(\s*([A-Za-z_]\w*)\s*\)', oml))
    system = {'wp_event_id','wp_event_md5','tenant_id','raw'}
    unknown = {x for x in reads if not x.startswith('__') and x not in captured and x not in system}
    if unknown: errors.append(f'OML reads uncaptured fields: {sorted(unknown)}')
    unused = captured - reads
    if unused: errors.append(f'captured fields have no OML destination: {sorted(unused)}')
    return errors


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('sample','wpl','oml'): p.add_argument('--'+name, required=True, type=Path)
    p.add_argument('--keep-work', type=Path, help='optional explicit location to keep isolated evidence')
    args = p.parse_args()
    lines = [line for line in args.sample.read_text().splitlines() if line.strip()]
    if not lines: p.error('sample is empty')
    try: samples = [json.loads(line) for line in lines]
    except json.JSONDecodeError as exc: p.error(f'sample is not NDJSON: {exc}')
    if any(not isinstance(x,dict) for x in samples): p.error('sample lines must be JSON objects')
    wpl, oml = args.wpl.read_text(), args.oml.read_text()
    errors = [e for x in samples for e in static_errors(x,wpl,oml)]
    try:
        import jsonschema
    except ImportError:
        jsonschema = None
        print('Schema: NOT_RUN (jsonschema dependency unavailable)')
    if errors:
        print('FAIL static: ' + '; '.join(sorted(set(errors))))
        return 1
    with tempfile.TemporaryDirectory(prefix='wpl-oml-simple-') as temp:
        root = Path(temp) / 'project'
        shutil.copytree(ASSET,root)
        (root/'data/in_dat/sample.dat').write_text('\n'.join(lines)+'\n')
        pkg = re.search(r'\bpackage\s+([A-Za-z_]\w*)',wpl)
        rule = re.search(r'\brule\s+([A-Za-z_]\w*)\s*\{',wpl)
        if not pkg or not rule:
            print('FAIL: package/rule missing');return 1
        route = re.search(r'^rule\s*:\s*(\S+)',oml,re.M)
        if not route or route.group(1)!=f'{pkg.group(1)}/{rule.group(1)}':
            print('FAIL: OML rule target mismatch');return 1
        out = root/'models/wpl'/pkg.group(1);out.mkdir(parents=True,exist_ok=True)
        (out/'parse.wpl').write_text(wpl)
        out = root/'models/oml'/pkg.group(1)/rule.group(1);out.mkdir(parents=True,exist_ok=True)
        (out/'adm.oml').write_text(oml)
        name = re.search(r'^name\s*:\s*(\S+)',oml,re.M)
        if not name: print('FAIL: OML name missing');return 1
        sink = root/'topology/sinks/business.d/all.toml'
        sink.write_text(sink.read_text().replace('sample_event',name.group(1)))
        if args.keep_work:
            args.keep_work.mkdir(parents=True,exist_ok=True)
        if not shutil.which('wparse'):
            if shutil.which('wpadm'):
                r=subprocess.run(['wpadm','check','--work-root',str(root),'--what','all'],capture_output=True,text=True)
                if r.returncode: print('FAIL wpadm: '+(r.stdout+r.stderr)[-1500:]);return 1
            print('NOT_RUN: static checks passed; batch 未运行 (wparse unavailable)')
            return 2
        r=subprocess.run(['wparse','batch','--work-root',str(root),'--max-line',str(len(lines))],capture_output=True,text=True,timeout=120)
        outputs={key:root/'data/out_dat'/file for key,file in [('business','all.json'),('raw','raw_log.json'),('miss','miss.dat'),('error','error.dat')]}
        if args.keep_work: shutil.copytree(root,args.keep_work/'project',dirs_exist_ok=True)
        if r.returncode:
            print('FAIL batch: '+(r.stdout+r.stderr)[-3000:]);return 1
        try: business=records(outputs['business']);raw=records(outputs['raw'])
        except (ValueError,TypeError) as exc: print(f'FAIL output JSON: {exc}');return 1
        counts={k:(len(business) if k=='business' else len(raw) if k=='raw' else len([x for x in path.read_text().splitlines() if x.strip()]) if path.exists() else 0) for k,path in outputs.items()}
        if counts!={'business':len(lines),'raw':len(lines),'miss':0,'error':0}:
            print(f'FAIL output counts: {counts}; log: '+(r.stdout+r.stderr)[-1200:]);return 1
        if jsonschema is None:
            print(f'NOT_RUN Schema: batch counts {counts}; jsonschema dependency unavailable');return 2
        schema=json.loads(SCHEMA.read_text())
        validator=jsonschema.Draft202012Validator(schema)
        for i,event in enumerate(business):
            problems=[e.message for e in validator.iter_errors(event)]
            if event.get('occur_time')!=event.get('meta',{}).get('occur_time'):problems.append('occur_time differs from meta.occur_time')
            if any(not isinstance(event.get(k),str) for k in COMPAT-{'occur_time'}):problems.append('compat role field is not string')
            if 'event_id' in event:problems.append('top-level event_id forbidden')
            source=samples[i]
            if 'date' in source and event.get('occur_time')!=int(float(source['date'])*1000):problems.append('business time differs from sample date')
            encoded=json.dumps(event,ensure_ascii=False)
            for field,value in source.items():
                if field in {'date','log'} or value is None: continue
                if isinstance(value,(str,int,float)) and str(value) not in encoded:
                    problems.append(f'{field} value missing from business output')
            log=source.get('log')
            if isinstance(log,str):
                for key,value in re.findall(r'\b([A-Za-z_][A-Za-z_0-9]*)=([^\s]+)',log):
                    if key=='msg':
                        value=value.removeprefix('audit')
                    if value and value not in encoded:
                        problems.append(f'log {key} value missing from business output')
            if i>=len(raw) or json.loads(raw[i].get('raw_msg','null'))!=source:
                problems.append('raw output does not preserve the source JSON')
            if problems: print(f'FAIL business[{i}]: '+ '; '.join(problems));return 1
        print(f'OK batch: business={counts["business"]} raw={counts["raw"]} miss=0 error=0; Schema and time checked')
    return 0

if __name__=='__main__': sys.exit(main())
