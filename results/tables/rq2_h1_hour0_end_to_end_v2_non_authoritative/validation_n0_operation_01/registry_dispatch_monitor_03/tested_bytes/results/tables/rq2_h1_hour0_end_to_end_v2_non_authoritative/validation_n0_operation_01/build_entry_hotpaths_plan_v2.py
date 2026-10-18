"""Bind one fixed three-entry hotpath diagnostic before execution."""
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
base = json.loads((HERE / 'bounded_registry_plan_02.json').read_bytes())
code = dict(base['code_lease_sha256'])
scope = HERE / 'bounded_stable_read_entry_v2.py'
code[str(scope)] = sha256(scope.read_bytes()).hexdigest()
sources = dict(base['source_sha256'])
sources.update(code)
for path in (Path(__file__), HERE / 'measure_entry_hotpaths_v2.py', HERE / 'run_entry_hotpaths_bounded_v2.py',
        HERE / 'bounded_entry_v2_unit_02/request.json', HERE / 'bounded_entry_v2_unit_02/terminal.json',
        REPO / 'tests/test_h1_bounded_stable_read_entry_development_v2.py'):
    sources[str(path)] = sha256(path.read_bytes()).hexdigest()
assert all(sha256(Path(p).read_bytes()).hexdigest() == pin for p, pin in sources.items())
assert json.loads((HERE / 'bounded_entry_v2_unit_02/terminal.json').read_bytes())['exit_code'] == 0
value = dict(status='DRAFT_NONAUTHORITATIVE',
    question='Does lighter non-target routing remove new entry overhead while preserving actual bootstrap identities and both registry split bytes?',
    attempts=1, roots=0, hours=0, synthetic_jobs=0, native_calls=0,
    modes=['predecessor', 'v1', 'v2'], identity_calls_per_mode=2, registry_splits_per_mode=['training', 'holdout'],
    inner_output=str(HERE / 'entry_hotpaths_02_non_authoritative'),
    outer_output=str(HERE / 'entry_hotpaths_monitor_02'),
    basetemp='D:/h1_entry_hotpaths_02_non_authoritative',
    source_sha256=sources, code_lease_sha256=code, old_chain_sha256=base['old_chain_sha256'],
    limits=dict(wall_seconds=120, sampled_rss_bytes=768 * 1024**2, storage_bytes=128 * 1024**2),
    dag=['fixed sources and interpreter policy', 'predecessor owner and metadata lease',
        'two actual bootstrap identities and two registry splits', 'close',
        'repeat fixed operations with bounded v1 then bounded v2',
        'exact comparison and hook/handle/source/process postcheck'],
    optimization='non-target route guards; canonical target full open/read/second-fstat, light enter/first-fstat; original scientific observations unchanged',
    stop='first error or fixed cap; preserve failure; no unchanged retry or cap extension',
    order_effects='one fixed order comparison; no statistical or whole-chain runtime claim',
    whole_workflow_performance_review_complete=False, full_hour0_chain_passed=False,
    formal_execution_ready=False, formal_result=False, resource_admission=False, native_execution_authorized=False)
out = HERE / 'entry_hotpaths_plan_02.json'
with out.open('x', encoding='utf-8') as stream:
    json.dump(value, stream, indent=2)
print(json.dumps(dict(plan_sha256=sha256(out.read_bytes()).hexdigest(), source_files=len(sources), code_files=len(code))))
