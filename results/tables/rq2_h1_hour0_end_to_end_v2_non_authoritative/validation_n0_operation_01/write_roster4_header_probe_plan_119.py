"""Section9 self-review for one bounded zero-execution public header diagnostic."""
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
D=HERE/'whole_workflow_optimization_01_non_authoritative'
old=json.loads((D/'phase_dependency_cost_comparison_plan_106.json').read_text())
paths={Path(name) for name in old['files_sha256']}
paths.update((ROOT/'experiments').glob('h1_*.py'));paths.update((ROOT/'tests').glob('*h1*.py'))
paths.update([HERE/'run_unit_bounded_v16.py',HERE/'run_unit_entry_v3.py',Path(__file__)])
assert all(path.is_file() for path in paths)
base=Path('D:/h1_roster4_header_119_non_authoritative')
assert not base.exists() and not (HERE/'workflow_roster4_header_119').exists()
command=[str(Path(sys.executable)),'-B',str(HERE/'run_unit_bounded_v16.py'),'workflow_roster4_header_119',
    '120','1024','128','--',str(HERE/'run_unit_entry_v3.py'),'-s','-p','no:faulthandler',
    '--basetemp',str(base),'tests/test_h1_roster4_live_header_development_v1.py']
value=dict(status='BOUNDED_DIAGNOSTIC_PLAN_NONAUTHORITATIVE',risk='R3',at_utc=datetime.now(timezone.utc).isoformat(),
    command=command,question='Can the new exact public Bootstrap5/Roster4 graph complete header create/inspect/guard/close/reopen without N0 or Job execution?',
    scale=dict(symbolic_profile=1,bootstrap_owners=2,roster_owners=2,roster_inspections=2,
        fixed_expected_phase_windows=6,kernel_seeds_per_window=1,phase_ordinal=0,
        maximum_internal_projects_per_window=256,maximum_internal_checks_per_window=4096,
        guard_competition_negatives=2,N0_Jobs=0,native_calls=0,retries=0,concurrency=1),
    dag=['Build one tiny synthetic static-profile declaration; install nine explicitly labelled execution denials before defining new runtimes.',
        'Construct exact Bootstrap5 and its real global/bootstrap journals with one internally held static phase segment.',
        'Construct exact Roster4 with one shared phase segment; inspect its empty registry using a second segment.',
        'Reject competing held Bootstrap guard and foreign thread without poisoning or opening another window.',
        'Close both public owners and all code/phase/journal resources.',
        'Reopen Bootstrap5 and Roster4 using the externally saved heads; inspect and compare exact view bytes; close.',
        'Save six lifecycle receipts, per-stage wall time and zero execution counters; verify source/input/process/storage terminal.'],
    optimization=dict(reuse='Only immutable phase science within a single internally owned segment; dynamic journals/registry/N0 are freshly read.',
        boundaries='No retain callback or Owned Job is permitted here. The generic new coordinator has separate actual-handle unit boundary tests117/118.',
        evidence_reused=['legacy chain07/postcheck04 remain complete and are not rerun',
            '95 old public header stopped at300s after partial reopen; not a complete baseline',
            '106 local phase window ROI29.27/41.79 percent; no whole-chain extrapolation',
            '112/114 shared-scope matching, disjointness, alias/failure/GC tests and scoped finding closure',
            '117 monitor strict final/nonfollow root tests;118 Roster definition-route negatives'],
        rejected='Do not repeat the unchanged Bootstrap4/Roster3 prefix or extend95; do not cache dynamic registry records or borrow producer credentials.'),
    budget=dict(wall_seconds=120,sampled_rss_bytes=1024**3,storage_bytes=128*1024**2,
        estimate='Six full one-seed phase windows, each bounded256 projects/4096 active checks. New public runtime/check overhead is not measured;120s is a diagnostic cap, not a completion promise.',
        uncertainty='Real public nested-check counts and runtime-seal CPU cost are the target of this first diagnostic. No full N0/Common/paired budget follows.',
        storage='New code snapshots and tiny header journals expected below32MiB; enforce128MiB total observed roots. No external input download.',
        progress='JSON at every completed semantic stage; monitor polls process/RSS/storage, stdout retains the current stage.',
        no_progress='No completed stage for120s necessarily hits the fixed overall120s wall cap; no extension or automatic retry.',
        stop='Monitor PID+creation wall/RSS/storage/observation failures; preserve terminal/tested bytes and observed cleanup. Forced termination is not an internal graceful-cleanup pass.'),
    acceptance=['test exit0 with complete create/inspect/close/reopen and exact reopened view',
        'exactly six complete internally owned phase windows, all handles closed, caches clear and guards released',
        'all nine execution-denial counters zero; no controller directory or event files created',
        'guard/thread rejection does not poison owner or leak guards',
        'all declared source/input/environment pins unchanged and observed owned PIDs absent',
        'all authority flags remain false; predefinition denial seams and unchanged execution-dispatch limitation are recorded'],
    environment=dict(interpreter=sys.executable,interpreter_sha256=sha256(Path(sys.executable).read_bytes()).hexdigest(),
        version=sys.version,platform=platform.platform(),timezone='Asia/Shanghai'),
    files_sha256={str(path):sha256(path.read_bytes()).hexdigest() for path in sorted(paths,key=str)},
    independent_public_pre_seal_review_pending=True,bounded_diagnostic_self_review_complete=True,
    whole_workflow_performance_review_complete=False,full_optimized_workflow_accepted=False,
    completed_N0_attach_positive=False,production_seal=False,official_review=False,
    formal_result=False,formal_execution_ready=False,resource_admission=False,native_execution_authorized=False)
out=D/'roster4_header_probe_plan_119.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha256(out.read_bytes()).hexdigest(),pins=len(paths))))
