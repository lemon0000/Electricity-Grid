"""One metadata-only public reopen of saved external heads, with no Job retry."""
from datetime import datetime,timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
D=HERE/'whole_workflow_optimization_01_non_authoritative'
previous=D/'saved152_numerical_postcheck_plan_153.json';value=json.loads(previous.read_bytes())
paths={Path(p) for p in value['files_sha256']}
paths.update((ROOT/'tests').glob('*h1*.py'));paths.add(Path(__file__))
saved=Path('D:/h1_bootstrap5_retained_152_non_authoritative');pending=[saved];inputs=[]
while pending:
    directory=pending.pop()
    for entry in os.scandir(directory):
        info=entry.stat(follow_symlinks=False);assert not info.st_file_attributes&0x400
        if entry.is_dir(follow_symlinks=False):
            if entry.name!='scratch_non_authoritative':pending.append(Path(entry.path))
        else:inputs.append(Path(entry.path))
    assert len(inputs)<=2048
assert sum(p.stat().st_size for p in inputs)<128*1024**2
paths.update(inputs)
base=Path('D:/h1_saved152_reopen_154_non_authoritative');label='saved152_readonly_reopen_154'
assert not base.exists() and not (HERE/label).exists()
result=D/'bootstrap5_retained_n0_bounded_result_152.json';oracle=D/'saved152_numerical_postcheck_result_153.json'
paths.update((result,oracle))
value.update(schema='h1_saved152_readonly_reopen_plan_154',at_utc=datetime.now(timezone.utc).isoformat(),
    predecessor_plan_sha256=sha256(previous.read_bytes()).hexdigest(),
    command=[sys.executable,'-B',str(HERE/'run_unit_bounded_v19.py'),label,'300','1024','128','--',
        str(HERE/'run_unit_entry_v6.py'),'-s','-p','no:faulthandler','--basetemp',str(base),
        '--canonical-path-root',str(saved),'tests/test_h1_retained_n0_readonly_reopen_development_v5.py'],
    question='Can exact current Bootstrap5 independently reopen the eight externally saved callback heads, inspect pending_post_N, and close without publishing or rerunning a Job?',
    scale=dict(public_readonly_owners=1,public_inspects=1,public_closes=1,public_bootstrap_calls=0,
        new_N0_Jobs=0,native_calls=0,independent_oracle_calls=0,concurrency=1,retries=0),
    dag=['Recreate only explicit fixture source seams; pin original152 bytes and153 numerical equality evidence.',
        'Validate eight chained external retention files and exact saved result hash; take both heads from those files, never from journal suffixes.',
        'Cold-import Bootstrap5 after source seams. Restore typed saved declaration and exact saved symbolic resolver; require canonical declaration bytes equal.',
        'Open once with create=False/create_study=False and both externally retained heads; reject any retention callback.',
        'Call inspect exactly once; require pending_post_N, N0 numerical evidence audited and exact heads, retry_authorized=false and all formal flags false.',
        'Close original read-only owner, require complete phase lifecycle/active orphan0, close entry leases and verify all saved/source hashes plus observed PIDs.'],
    static_call_model=dict(replay_calls=2,registry_checks_per_replay=2,N0_prepares=4,
        fallback_full_hour_replays_per_prepare=4,fallback_within_prefix_revalidations_per_prepare=4,
        full_hour_replays=16,within_prefix_revalidations=16,contexts=64,
        basis='Unchanged __init__ and inspect each call _replay; _replay calls _registry before and in finish. One saved N0 root. No live registration scope is borrowed; fallback prepare is full-only.',
        observed_execution_counts=False),
    optimization=dict(reuse='Reuse saved152 Job and externally persisted callback heads; do not call bootstrap/reconcile/Owned Controller or rerun original body.',
        existing='Use unchanged existing path lease and original per-body metadata resolver; pure phase/implementation windows remain current.',
        known_remaining_bottleneck='Four full-only registry prepares remain. This is a bounded read-only lifecycle diagnostic, not whole-chain admission or an optimized consumer-proof claim.',
        evidence='153 original numerical oracle passed85.69s/outer90.032s,24.714s profiled body.152 Job exit0/quiet49.281s but original public return missing.136 empty current header and151 entry-failure scope already closed.'),
    budget=dict(wall_seconds=300,sampled_rss_bytes=1024**3,observed_storage_bytes=128*1024**2,
        basis='153 fixture58.6s plus146 four full-prepare-equivalent profiled costs about4x29.8s,152 header53.9s plus inspect/cleanup overhead;300s diagnostic cap with uncertainty. No new Job or extension of152 process.',
        heartbeat='Saved declaration/heads ready, owner open, public inspect complete, owner closed; PID+creation/RSS/storage monitor.',
        stop='Fixed300s, no extension or automatic retry. Partial data and observed-process cleanup retained.'),
    acceptance=['Successful public read-only state observation and complete new owner/entry closure.',
        'Both retained heads exact, no retention callback, all saved/source pins unchanged,0newJob/native.',
        'Original152 public bootstrap return/graceful cleanup remain unverified; full typed chain/formal/resource gates remain open.'],
    saved_input_files=len(inputs),files_sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in sorted(paths,key=str)})
target=D/'saved152_readonly_reopen_plan_154.json'
with target.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(target),sha256=sha256(target.read_bytes()).hexdigest(),pins=len(paths),saved=len(inputs))))
