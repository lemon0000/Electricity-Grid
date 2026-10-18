"""One cause-specific cold N0 diagnostic after the measured allocation fix."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3]
base=json.loads((HERE/'fresh_n0_plan_02.json').read_bytes())
reviewed=json.loads((HERE/'bounded_registry_plan_02.json').read_bytes())
sources=dict(reviewed['source_sha256']);code=dict(reviewed['code_lease_sha256'])
for path in (Path(__file__),HERE/'run_fresh_n0_entry_v3.py',HERE/'run_fresh_n0_bounded_v3.py',
        HERE/'bounded_registry_plan_02.json',HERE/'bounded_registry_monitor_02/request.json',
        HERE/'bounded_registry_monitor_02/terminal.json',HERE/'bounded_registry_entry_02_non_authoritative/terminal.json',
        HERE/'bounded_registry_entry_02_non_authoritative/bounded_closed_receipt.json',
        HERE/'bounded_registry_entry_02_non_authoritative/bounded_entry_receipt.json',
        HERE/'bounded_entry_unit_09/request.json',HERE/'bounded_entry_unit_09/terminal.json'):
    sources[str(path)]=sha256(path.read_bytes()).hexdigest()
assert len(code)==164
assert all(sha256(Path(p).read_bytes()).hexdigest()==pin for p,pin in sources.items())
assert json.loads((HERE/'bounded_registry_entry_02_non_authoritative/terminal.json').read_bytes())['exit_code']==0
assert json.loads((HERE/'bounded_entry_unit_09/terminal.json').read_bytes())['exit_code']==0
value=dict(base)
value.update(previous_attempt='02 stopped at 600s, owned synthetic Job exit0/quiescent but N0 registration incomplete; old pins/locks intact',
    corrected_cause='exact canonical raw-reader allocation bounded by freshly observed file size, with all original stat/open/fstat/read/pathname checks unchanged',
    regression='60 actual Windows entry differential/fault cases; 115 unchanged registry-scope cases; both real registry splits byte equal',
    entry_optimization='owned composite code+bounded-read entry; existing metadata parse reuse and stock discovery unchanged',
    source_sha256=sources,code_lease_sha256=code,
    outer_output=str(HERE/'fresh_n0_monitor_03'),inner_output=str(HERE/'fresh_n0_entry_03_non_authoritative'),
    basetemp='D:/h1_registry_fresh_n0_03_non_authoritative',
    performance_basis='same configured registry paths measured 27.2660s baseline total versus 2.5637s bounded total; complete N0 runtime remains unknown and capped',
    optimizations=['164 locked code files including raw-reader/owner/entry sources','configured eight-root interpreter and stock distribution discovery',
        'locked selected METADATA parse values','fresh observed-size+1 allocations for the exact canonical raw reader',
        'per-root numerical proof with all original fresh contexts'],
    validation_entry_boundary='Windows CPython exact build; caller-frame audit events added; audit-hook transparency not claimed; no source/result cache',
    acceptance_addition='bounded entry closed receipt asserts restored hooks, owner closed, handles/streams/proxies zero; 164 held paths reopened for write without writing',
    no_scientific_module_changes_since_registry_scope_unit_04=True)
out=HERE/'fresh_n0_plan_03.json'
with out.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
print(json.dumps(dict(plan_sha256=sha256(out.read_bytes()).hexdigest(),source_files=len(sources),code_files=len(code))))
