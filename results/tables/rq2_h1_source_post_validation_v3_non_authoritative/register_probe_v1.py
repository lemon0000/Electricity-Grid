"""Bind the finite saved diagnostic after targeted fixes and read-only findings."""
from pathlib import Path
from hashlib import sha256
import json
import platform
import subprocess
import sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
CODE=[REPO/name for name in (
    'experiments/h1_constructor_runtime_guard_development_v1.py',
    'experiments/h1_phase_historical_batch_development_v3.py',
    'experiments/h1_phase_exact_source_batch_development_v3.py',
    'experiments/h1_constructor_source_batch_validation_development_v2.py',
    'tests/test_h1_source_post_validation_development_v3.py',
)]


def save(name,value):
    with (HERE/name).open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2);stream.write('\n')


unit=json.loads((HERE/'unit_07/terminal.json').read_bytes())
if unit['exit_code']!=0 or unit['changed']:raise ValueError('current targeted test terminal required')
for path in CODE:
    if unit['source_after'][str(path)]!=sha256(path.read_bytes()).hexdigest():
        raise ValueError('code differs from tested bytes')
previous=HERE.parent/'rq2_h1_source_callable_gap_v1_non_authoritative/final_verification.json'
proof=json.loads(previous.read_bytes())
changed=[name for name,pin in proof['bindings'].items() if sha256(Path(name).read_bytes()).hexdigest()!=pin]
if changed:raise ValueError('reused evidence changed: '+repr(changed))
save('preseal_findings_v1.json',dict(status='DRAFT_NONAUTHORITATIVE',scope='one_saved_H3_M5_batch_only',
    reviewer='/root/phase_budget_review',review_kind='read_only_non_authoritative_PRE_SEAL_findings',
    official_review_started=False,review_receipt_created=False,
    no_new_normal_path_defect_identified_for_this_finite_diagnostic=True,
    code_sha256={str(path):sha256(path.read_bytes()).hexdigest() for path in CODE},
    unit_terminal_sha256=sha256((HERE/'unit_07/terminal.json').read_bytes()).hexdigest(),
    repaired_findings=['independent helper teardown graph','exact MRO','nested finally clears all-H references',
        'combined historical retained cap','complete chronological typed packet inventory',
        'final post-all-H bookends','actual concrete Path descriptors and named global slots',
        'independent per-Reader metrics','copyreg standard cache initialized before exact layout pins',
        'independent runtime record structure seal','early retained partial Reader instance',
        'public guard state checked by independent program'],
    remaining_evidence_limits=['arbitrary reflection into private backup checkers not covered',
        'between-bookend ABA not covered','constructor failure uses actual AST and stand-in owners',
        'real saved Reader file/owner fault matrix incomplete',
        '320 MiB declared content caps exclude observed/model/allocator and RSS',
        'stage timing fields descriptive rather than scientific audit claims'],
    owner_adopted=False,formal_result=False,resource_admission=False))
paths=CODE+[HERE/name for name in ('design_and_budget.md','run_saved_validation_v3.py','oracle_saved_v3.py',
    'unit_07/request.json','unit_07/terminal.json','unit_07/pytest.xml','preseal_findings_v1.json',
    'probe_generation_record_v1.json','register_probe_v1.py')]
save('probe_budget_v1.json',dict(status='DRAFT_NONAUTHORITATIVE',purpose='bounded whole-path source diagnostic',
    hours=3,stage_slots=5,batches=1,independent_readers=2,parent_traversals=2,
    reader_prefix_hours=6,saved_job_artifact_replays=12,saved_stage_replays=60,
    extra_packet_validations=6,extra_full_packet_digests=12,
    explicit_model_dependency_snapshots=6,parent_namespace_root_listings=18,
    old_readers_rerun=0,new_normal_jobs=0,new_selectors=0,real_native_calls=0,
    wall_limit_seconds=240,no_case_read_activity_limit_seconds=90,
    sampled_tree_rss_limit_bytes=1024**3,output_logical_storage_limit_bytes=128*1024**2,
    sample_seconds=2,heartbeat_seconds=30,repetitions=1,automatic_retry=False,
    historical_content_cap_per_Reader_bytes=128*1024**2,current_rows_cap_bytes=64*1024**2,
    overlapped_declared_containers_content_cap_bytes=320*1024**2,
    content_cap_does_not_bound_observed_model_allocator_or_RSS=True,
    before_process_snapshot=subprocess.check_output(['powershell.exe','-NoProfile','-Command',
        "Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python|gurobi|cplex|ipopt|highs' } | Select-Object ProcessId,ParentProcessId,Name,CommandLine | ConvertTo-Json -Compress"],text=True),
    python=sys.version,platform=platform.platform(),
    predecessor_bindings_checked=len(proof['bindings']),predecessor_final_sha256=sha256(previous.read_bytes()).hexdigest(),
    source_sha256={str(path):sha256(path.read_bytes()).hexdigest() for path in paths},
    overall_performance_review_complete=False,long_connected_launch_admitted=False,
    resource_admission=False,formal_execution_ready=False,formal_result=False,native_execution_authorized=False))
print(json.dumps(dict(predecessor_bindings_verified=len(proof['bindings']),new_code_bindings=len(CODE),
    diagnostic_registered=True,long_or_formal_run_admitted=False)))
