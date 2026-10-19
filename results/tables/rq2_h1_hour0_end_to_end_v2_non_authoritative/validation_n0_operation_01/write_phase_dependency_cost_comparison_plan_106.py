"""Bind a fixed unprofiled phase-data comparison before the bounded launch."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import sys

H=Path(__file__).resolve().parent
R=H.parents[3]
D=H/'whole_workflow_optimization_01_non_authoritative'
pin=lambda p:sha256(p.read_bytes()).hexdigest()
review=D/'phase_dependency_window_findings_105.json'
findings=json.loads(review.read_bytes())
assert findings['open_findings']==[]
unit=H/'phase_dependency_abi_units_103'
terminal=json.loads((unit/'terminal.json').read_bytes())
assert terminal['exit_code']==0 and terminal['source_unchanged']
assert terminal['observed_owned_processes_absent'] and not terminal['cleanup_errors']
assert '105 passed in 19.04s' in (unit/'stdout.log').read_text(encoding='utf-8')
old=json.loads((D/'phase_dependency_cost_probe_plan_96.json').read_bytes())
paths={Path(name) for name in old['files_sha256']}
paths|={p for p in (R/'experiments').glob('h1_*.py')}
paths|={Path(__file__),Path(sys.executable),review,D/'phase_dependency_window_pre_seal_input_105.json',
    H/'run_unit_bounded_v15.py',H/'run_unit_entry_v3.py',
    R/'tests/test_h1_phase_dependency_cost_comparison_development_v1.py'}
paths|={unit/n for n in ('request.json','started.json','terminal.json','stdout.log')}
for name,expected in json.loads((D/'phase_dependency_window_pre_seal_input_105.json').read_bytes())['files_sha256'].items():
    path=Path(name)
    assert pin(path)==expected
    paths.add(path)
label='phase_dependency_cost_comparison_106'
base=Path('D:/h1_phase_dep_comparison_106_non_authoritative')
assert not (H/label).exists() and not base.exists()
command=[str(Path(sys.executable)),'-B',str(H/'run_unit_bounded_v15.py'),label,'90','1024','128','--',
    str(H/'run_unit_entry_v3.py'),'-s','-p','no:faulthandler','--basetemp',str(base),
    'tests/test_h1_phase_dependency_cost_comparison_development_v1.py']
result=dict(status='BOUNDED_DIAGNOSTIC_PLAN_NONAUTHORITATIVE',risk='R3',
    at_utc=datetime.now(timezone.utc).isoformat(),command=command,
    question='Does a fully acquired, checked and closed detached phase window reduce total cost for6/16 fixed same-group requests against matched canonical verification without profiler?',
    scale=dict(request_counts=[6,16],order=['canonical','window','window','canonical'],
        initial_canonical_oracles=1,canonical_group_calls=45,held_group_projections=44,windows=4,
        bootstrap_owners=0,roster_owners=0,N0_Jobs=0,native_calls=0,adaptive_requests=False),
    dag=['ordinary immutable code/metadata entry setup shared by both arms',
        'one canonical JSON reference for training_ub ordinal0',
        'for6 then16 fixed requests: canonical batch, complete window, complete window, canonical batch',
        'each window includes constructor identity, full inventory, held file/ancestor handles, physical recheck, all projected requests, physical exit, cleanup and closed receipt',
        'all canonical JSON SHA and private legacy-shape reference SHA equal independent reference',
        'save observations; ordinary entry cleanup; terminal source/process/storage/hash readback'],
    limits=dict(wall_seconds=90,sampled_rss_bytes=1024**3,storage_bytes=128*1024**2,
        concurrency=1,retries=0,progress='per-batch JSON and outer process liveness/CPU/RSS/storage samples',
        no_progress='inspect if no batch finishes for30s; fixed90s hard cap remains',
        stop='outer observed PID+creation monitor; wall/RSS/storage caps; save terminal and cleanup; no extension'),
    optimization=dict(hypothesis='Entry/exit inventory observations plus held immutable input handles amortize repeat physical scans',
        reuse='within one fixed synchronous diagnostic window only; no cross-window value cache',
        prior_evidence='96 cProfile locates IO/identity cost; not a speed baseline. 103/104/105 tests and scoped findings cover declared failure model.',
        decision='Record observed ratios without performance assertions; if nonpositive do not adopt this cut as a speed optimization.'),
    acceptance=['single test exits0','every scientific reference hash matches',
        'every window lifecycle_complete with all handles closed, immutable bytes cleared and guard released',
        'canonical_equivalence_verified remains false in window outputs; no per-call physical freshness claim',
        'all source/input/env pins unchanged; observed owned PIDs absent; terminal cleanup and storage readable'],
    environment=dict(interpreter=str(Path(sys.executable)),interpreter_sha256=pin(Path(sys.executable)),
        version=sys.version,platform=platform.platform(),timezone='Asia/Shanghai'),
    files_sha256={str(p):pin(p) for p in sorted(paths)},
    bounded_diagnostic_self_review_complete=True,whole_workflow_performance_review_complete=False,
    full_optimized_workflow_accepted=False,completed_N0_attach_positive=False,
    production_seal=False,official_review=False,formal_result=False,formal_execution_ready=False,
    resource_admission=False,native_execution_authorized=False)
path=D/'phase_dependency_cost_comparison_plan_106.json'
with path.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
print(json.dumps(dict(path=str(path),sha256=pin(path),pins=len(paths))))
