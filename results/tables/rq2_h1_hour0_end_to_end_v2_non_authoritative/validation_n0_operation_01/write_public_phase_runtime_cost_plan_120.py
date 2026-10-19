"""One zero-owner bounded profile to explain the incomplete header119 cost."""
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
D=HERE/'whole_workflow_optimization_01_non_authoritative'
prior=D/'roster4_header_probe_plan_119.json';old=json.loads(prior.read_text())
paths={Path(p) for p in old['files_sha256']}
paths.update([Path(__file__),ROOT/'tests/test_h1_public_phase_runtime_cost_development_v1.py'])
base=Path('D:/h1_public_phase_runtime_120_non_authoritative')
assert not base.exists() and not (HERE/'public_phase_runtime_cost_120').exists()
command=list(old['command']);command[3]='public_phase_runtime_cost_120';command[4]='60'
command[command.index('--basetemp')+1]=str(base);command[-1]='tests/test_h1_public_phase_runtime_cost_development_v1.py'
value=dict(status='BOUNDED_DIAGNOSTIC_PLAN_NONAUTHORITATIVE',risk='R3',at_utc=datetime.now(timezone.utc).isoformat(),
    question='Which runtime seal/configuration/check component dominates CPU after public header119 stopped at120s?',
    command=command,scale=dict(public_owners=0,rosters=0,N0_Jobs=0,native_calls=0,
        detached_data_windows=2,one_kernel_seed_per_window=True,
        direct_component_batches=6,calls_per_direct_batch=32,held_kernel_receipts=8,shared_active_checks=8,concurrency=1,retries=0),
    dag=['Import the exact new graph without creating an owner or adding execution denial seams.',
        'Profile32 calls each to Bootstrap5/Roster4/shared/binding3/kernel runtime checks and configuration.binding.',
        'Acquire one genuine kernel window, one seed, profile8 receipts and close.',
        'Acquire one genuine shared-data scope, one seed, profile8 active checks and close.',
        'Save cProfile statistics, complete internal receipts and process/source/storage terminal.'],
    optimization=dict(evidence_reused='119 showed Bootstrap constructor29.541s and no Roster return before120s;1341 planned pins unchanged. Reuse phase106/109/112/114 science and faults.',
        target='Attribute repeated runtime graph inventory verification and configuration identity cost before changing observation frequency.',
        non_claim='Profiler component times are not a matched unprofiled baseline or an end-to-end speed estimate. Do not repeat the unchanged119 prefix.'),
    limits=dict(wall_seconds=60,sampled_rss_bytes=1024**3,storage_bytes=128*1024**2,
        heartbeat='Per completed component JSON; outer process and storage observation.',
        no_progress='Fixed60s total cap; no extension or automatic retry.',
        stop='Exact observed PID+creation monitor wall/RSS/storage/observation failures; preserve failed bytes and terminal.'),
    acceptance=['Exit0; all eight fixed component batches saved.',
        'Both genuine static-data windows complete, all actual handles closed, caches clear, guards released, active/orphan0.',
        'No public owner/N0/Job/native; no authority; all planned pins unchanged and observed processes absent.'],
    environment=old['environment'],files_sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in sorted(paths,key=str)},
    bounded_diagnostic_self_review_complete=True,whole_workflow_performance_review_complete=False,
    full_optimized_workflow_accepted=False,production_seal=False,official_review=False,
    formal_result=False,formal_execution_ready=False,resource_admission=False,native_execution_authorized=False)
out=D/'public_phase_runtime_cost_plan_120.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha256(out.read_bytes()).hexdigest(),pins=len(paths))))
