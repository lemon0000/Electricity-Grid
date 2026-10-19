"""Explicit saved174 diagnostic plans, without inherited invocation scalars."""
from datetime import datetime,timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

H=Path(__file__).resolve().parent;R=H.parents[3];D=H/'whole_workflow_optimization_01_non_authoritative'
producer=D/'bootstrap6_retained_n0_bounded_result_174.json';v=json.loads(producer.read_bytes())
assert v['public_development_N0_return_and_close_verified'] and v['terminal']['observed_owned_processes_absent']
saved=Path('D:/h1_bootstrap6_retained_174_non_authoritative');files=[];pending=[saved]
while pending:
    directory=pending.pop()
    for entry in os.scandir(directory):
        info=entry.stat(follow_symlinks=False);assert not info.st_file_attributes&0x400
        if entry.is_dir(follow_symlinks=False):
            if entry.name!='scratch_non_authoritative':pending.append(Path(entry.path))
        else:files.append(Path(entry.path))
    assert len(files)<=2048
assert sum(p.stat().st_size for p in files)<128*1024**2
previous=json.loads((D/'bootstrap6_retained_n0_bounded_plan_174.json').read_bytes())
paths={Path(path) for path in previous['files_sha256']}
paths.update((R/'tests').glob('*h1*.py'));paths.update(files)
paths.update((Path(__file__),H/'create_saved174_postchecks_175.py',H/'write_retained_n0_result_174.py',producer,
    D/'bootstrap6_plan_metadata_mismatch_175.json',D/'consumer_scoped_findings_173.json'))
for number,label,test,seconds,invocation in (
    ('176','saved174_numerical_oracle_176','tests/test_h1_saved_bootstrap6_n0_candidate_profile_development_v1.py',120,
        dict(module='experiments.h1_historical_n0_verifier_development_v1',public_call='prepare',completed_hours=1,public_owner=False)),
    ('177','saved174_readonly_reopen_177','tests/test_h1_retained_n0_readonly_reopen_development_v6.py',240,
        dict(module='experiments.h1_bootstrap_integration_development_v6',public_call='BootstrapOwner constructor,inspect,close',create=False,create_study=False,public_inspects=1))):
    base=Path('D:/h1_'+label+'_non_authoritative');assert not base.exists() and not (H/label).exists()
    command=[sys.executable,'-B',str(H/'run_unit_bounded_v19.py'),label,str(seconds),'1024','128','--',
        str(H/'run_unit_entry_v6.py'),'-s','-p','no:faulthandler','--basetemp',str(base),
        '--canonical-path-root',str(saved),test]
    numeric=number=='176'
    value=dict(schema='h1_saved174_postcheck_plan_'+number,status='BOUNDED_DIAGNOSTIC_PLAN_NONAUTHORITATIVE',
        at_utc=datetime.now(timezone.utc).isoformat(),risk='R3',command=command,invocation=invocation,
        question='Does the original numerical oracle match actual174 audit bytes without another Job?' if numeric else
            'Does genuine Bootstrap6 reopen exact externally retained174 heads, perform two method-bound numerical read scopes, inspect pending_post_N and close?',
        scale=dict(saved_roots=1,public_owners=0 if numeric else 1,public_inspects=0 if numeric else 1,
            new_N0_Jobs=0,native_calls=0,concurrency=1,retries=0),
        dag=['Reuse original explicit fixture seams only; pin actual174 result and all saved file names/bytes.',
            'Original numerical oracle only; compare its audit to the actual retained local candidate.' if numeric else
            'Validate all8 external retention records and canonical typed declaration; never derive heads from journal suffixes.',
            'Record one profiled original oracle and exact scientific audit bytes.' if numeric else
            'Cold-import exact current Bootstrap6, constructor with both externally retained heads/create=False/create_study=False, no retention callback.',
            'No public owner is opened.' if numeric else
            'Call public inspect once; require pending_post_N and8full/24fresh/64contexts across two independent original consumer scopes, then close.',
            'Restore entry leases/aliases; verify plan pins, saved file set and observed-process terminal.'],
        expected_registry_counts=None if numeric else dict(full=8,fresh=24,contexts=64,scopes=2),
        optimization=dict(reuse='Reuse174 completed synthetic Job and retained actual data; no Job retry or source/header relabelling.',
            existing='Unchanged entry6 path lease and original per-body metadata resolver; no145 fixture extension.',
            evidence='169150 cases,170 genuine current empty header,171 saved152 oracle-equal DAG,174 actual public return/close with preserved metadata exception.',
            limitation='Original oracle is an independent observation using the same algorithm family, not a new independent scientific algorithm.' if numeric else
            'Single current saved lifecycle, not a matched whole-chain runtime comparison; outer consumer receipts are diagnostic data, not credentials.'),
        budget=dict(wall_seconds=seconds,sampled_rss_bytes=1024**3,observed_storage_bytes=128*1024**2,
            basis='153 one original oracle85.69s/90.032s outer;174 fixture58.858s and171 full prep16.2s raw/old oracle24.7s profiled;120s fixed cap.' if numeric else
            '154 prior Bootstrap5 saved reopen172.09s/176.594s outer; current two scopes reuse half the full calls while retaining64contexts. Current fixture58.858s;240s fixed uncertainty cap.',
            heartbeat='Fixture and oracle observation, sampled PID/RSS/nonfollow storage.' if numeric else
            'Saved declaration/heads ready, owner open, public inspect, owner close; sampled PID/RSS/nonfollow storage.',
            stop='Fixed bound, no extension/automatic retry. Preserve partial output and observed-process cleanup; no scientific infeasibility inference.'),
        acceptance=['exit0, preserved original numerical audit equality' if numeric else
            'exit0, actual pending_post_N, external heads exact, no retention callback and complete2scope/phase closure',
            'Original source/config/scientific thresholds and saved file names+bytes unchanged; observed PIDs absent/cleanup0.',
            '174 stale plan module/header references remain documented in175; no retrospective exact-plan match, formal or full-chain claim.'],
        producer_result_sha256=sha256(producer.read_bytes()).hexdigest(),
        producer_plan_metadata_exception_sha256=sha256((D/'bootstrap6_plan_metadata_mismatch_175.json').read_bytes()).hexdigest(),
        current_header_result_sha256=sha256((D/'consumer_result_170.json').read_bytes()).hexdigest(),
        saved_input_files=len(files),files_sha256={str(path):sha256(path.read_bytes()).hexdigest() for path in sorted(paths,key=str)},
        production_seal=False,official_review=False,full_optimized_workflow_accepted=False,
        whole_workflow_performance_review_complete=False,formal_execution_ready=False,formal_run_authority=False,
        formal_result=False,resource_admission=False,native_execution_authorized=False)
    out=D/('saved174_postcheck_plan_'+number+'.json')
    with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
    print(json.dumps(dict(path=str(out),sha256=sha256(out.read_bytes()).hexdigest(),pins=len(paths),saved_inputs=len(files))))
