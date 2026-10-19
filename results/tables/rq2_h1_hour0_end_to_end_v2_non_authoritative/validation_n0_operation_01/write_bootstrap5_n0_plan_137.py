"""Section9: one fixed-budget explicit development N0, never a formal run."""
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
D=HERE/'whole_workflow_optimization_01_non_authoritative'
previous=json.loads((D/'roster4_header_probe_plan_136.json').read_text())
paths={Path(name) for name in previous['files_sha256']};paths.add(Path(__file__))
paths.update((ROOT/'experiments').glob('h1_*.py'));paths.update((ROOT/'tests').glob('*h1*.py'))
base=Path('D:/h1_bootstrap5_n0_137_non_authoritative');label='bootstrap5_n0_registration_137'
assert not base.exists() and not (HERE/label).exists()
node='tests/test_h1_registry_validation_fresh_n0_development_v2.py::test_cold_bootstrap5_registered_development_true_n0_registration_and_close'
command=[sys.executable,'-B',str(HERE/'run_unit_bounded_v17.py'),label,'300','1024','128','--',
    str(HERE/'run_unit_entry_v4.py'),'-s','-p','no:faulthandler','--basetemp',str(base),
    '--junitxml',str(base/'registered_development_true.xml'),'-o','junit_family=legacy',node]
value=dict(schema='h1_bootstrap5_n0_bounded_plan_137',status='BOUNDED_DIAGNOSTIC_PLAN_NONAUTHORITATIVE',
    risk='R3',at_utc=datetime.now(timezone.utc).isoformat(),command=command,
    question='Does one exact Bootstrap5/Owned5 synthetic N0 reach registered pending_post_N, match the predecessor numerical oracle and close all phase resources?',
    invocation=dict(public_call='BootstrapOwner.bootstrap',kwargs=dict(registered_development=True),
        module='experiments.h1_bootstrap_integration_development_v5',
        binding='Request nodeid and JUnit path name explicit true; entry n0_invocation.json and JUnit property repeat the actual fixed True call. Both entry and test sources are pinned.'),
    scale=dict(bootstrap_owners=1,rosters=0,synthetic_N0_Jobs=1,simulated_hours=1,
        synthetic_reports=3,real_native_calls=0,registry_builds=4,registry_full_numerical_replays=4,
        registry_fresh_byte_revalidations=28,registry_context_observations=64,
        independent_predecessor_oracles=1,reopens=0,concurrency=1,retries=0),
    dag=['Reuse existing synthetic source/enrollment/registry fixtures; retain original implementation callables and no test-only global identity cache.',
        'Cold-import exact Bootstrap5 after source/Job seams; build a new source-bound symbolic declaration and fixed phase archive.',
        'Create real global/bootstrap journals and verify foreign creator cannot open registry scope.',
        'Invoke bootstrap with explicit registered_development=True; retain8 journal heads with zero phase handles at every external retention.',
        'Create Owned5 and one real short Windows Job exporting3 saved synthetic stage reports; surrounding phase memo/window is closed during Job.',
        'Register N0 through original4 numerical builds with64 byte contexts; compare complete audit payload against predecessor oracle under solver_calls_forbidden.',
        'Save fixed invocation, registry receipt/heads/report; close owner and require complete phase/implementation lifecycle and zero active/orphan counters.',
        'Close metadata/code aliases and all held handles; save terminal/source/pin/process/storage observations.'],
    optimization=dict(reused_evidence=['Legacy chain07 and independent postcheck04 are complete; do not rerun.',
        '135 independent scoped finding closure and134116-case regression.',
        '136 current real header:6 complete windows/12 raw/1304memo,94.51s test/97.031s outer; not N0.',
        '124/131/136 original per-body metadata resolver fast path and full cleanup.',
        '125 repeated implementation DAG attribution, now private segment reuse only.'],
        callback_counts='8 durable head retentions;1 external Owned Job. Outer bootstrap therefore expected10 windows after callback/Job resumptions, plus constructor1.',
        callback_internal_checks='Native Job body has6 explicit owned-check/job-check sites, each may open a fresh child read segment;17 total windows is a planning estimate, not a certified execution count.',
        hard_bounds='128 new segments per top operation/4096 per owner; each256 projects/4096 checks; kernel16 seeds/4096 handles/64 path depth.',
        limitations='Dynamic journals and N0 contexts remain fresh. No consumer foreign-registry reuse, no metadata/per-call or ABA claim. New N0 cost is not measured.',
        excluded='No native calibration, source download, production seal, run lease, formal execution, three-arm/Common/paired/reopen or whole-workflow admission.'),
    budget=dict(wall_seconds=300,sampled_rss_bytes=1024**3,observed_storage_bytes=128*1024**2,
        basis='131/136 public header body about71s across6 windows. A new single N0 is materially different and remains unknown.300s is a diagnostic cap and an attribution stop, not a completion promise or full-workflow estimate.',
        historical='Old Bootstrap4 fresh04 stopped600.609s before registration (owner-open31.735s); no unchanged repeat or cap extension.',
        heartbeat='JSON at import/owner-open/every retention/N0 registration/oracle/close; outer observes current PID+creation, descendants, sampled RSS and artifact bytes.',
        no_progress='No automatic retry. Fixed300s total cap regardless of stage; absent heartbeat alone is not a deadlock verdict.',
        stop='PID+creation monitor stops only observed owned processes on wall/RSS/storage/observer errors; retain all failed bytes. Forced stop is not internal graceful-cleanup proof.'),
    acceptance=['exit0 and real Job exit0/whole Job quiescent; exactly1 synthetic N0/no native',
        'fixed registered_development=True is explicit in invocation/JUnit metadata and unchanged public callable is used',
        '4 registry builds and64 contexts with complete produced/consumed receipts; independent predecessor audit SHA equal',
        'all retentions see0 active phase operations; complete final phase receipts, cleared memos, handles/caches/guards and active/orphan0',
        'entry code/metadata/resolver aliases restored; all pins stable and observed processes absent',
        'all formal/native/resource gates remain false; no reopened or full-chain claim'],
    environment=dict(interpreter=sys.executable,interpreter_sha256=sha256(Path(sys.executable).read_bytes()).hexdigest(),
        version=sys.version,platform=platform.platform(),timezone='Asia/Shanghai'),
    files_sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in sorted(paths,key=str)},
    current_header_result_sha256=sha256((D/'roster4_header_probe_result_136.json').read_bytes()).hexdigest(),
    bounded_diagnostic_self_review_complete=True,whole_workflow_performance_review_complete=False,
    full_optimized_workflow_accepted=False,production_seal=False,official_review=False,
    formal_result=False,formal_execution_ready=False,resource_admission=False,native_execution_authorized=False)
out=D/'bootstrap5_n0_bounded_plan_137.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha256(out.read_bytes()).hexdigest(),pins=len(paths))))
