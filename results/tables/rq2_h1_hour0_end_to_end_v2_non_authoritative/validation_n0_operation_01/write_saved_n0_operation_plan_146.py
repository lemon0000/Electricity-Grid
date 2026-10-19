"""Bound the verifier4 diagnostic DAG, reusing saved data rather than a Job."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
D = HERE / 'whole_workflow_optimization_01_non_authoritative'
old_path = D / 'saved137_candidate_diagnostic_plan_138.json'
old = json.loads(old_path.read_bytes())
paths = {Path(p) for p in old['files_sha256']}
paths.update((Path(__file__), ROOT/'tests/test_h1_saved_n0_validation_operation_profile_development_v4.py'))
base = Path('D:/h1_saved137_operation_146_non_authoritative')
label = 'saved137_operation_profile_146'
assert not base.exists() and not (HERE/label).exists()
value = dict(schema='h1_saved137_n0_operation_diagnostic_plan_146',
    status='BOUNDED_DIAGNOSTIC_PLAN_NONAUTHORITATIVE', risk='R3',
    at_utc=datetime.now(timezone.utc).isoformat(),
    predecessor_plan_sha256=sha256(old_path.read_bytes()).hexdigest(),
    command=[sys.executable, '-B', str(HERE/'run_unit_bounded_v17.py'), label, '180', '1024', '128', '--',
        str(HERE/'run_unit_entry_v4.py'), '-s', '-p', 'no:faulthandler', '--basetemp', str(base),
        'tests/test_h1_saved_n0_validation_operation_profile_development_v4.py'],
    question='What dominates the existing verifier4 four-build diagnostic DAG after the one Job has already completed?',
    scale=dict(saved_candidates=1, diagnostic_only_operations=1, prepares=4,
        initial_full_numerical_hour_replays=4, fresh_byte_revalidations=28,
        context_observations=64, public_owners=0, new_N0_Jobs=0, native_calls=0,
        concurrency=1, retries=0),
    dag=['Recreate only explicit synthetic inputs and source seams using the existing fixture.',
        'Read saved137 local terminal as untrusted candidate data, without adopting journal suffix or owner heads.',
        'Open exact existing verifier4 N0ValidationOperation with diagnostic_only=True and maximum_prepares=4.',
        'Four original begin_build/prepare/confirm_build cycles, with matching diagnostic body and complete original contexts; profile and persist each completed cycle separately.',
        'Compare every full numerical audit SHA to saved candidate; close operation, inspect diagnostic-only receipt, close entry leases.',
        'Verify source/candidate pins, terminal and observed process cleanup.'],
    reuse='Use the exact 119 saved137 files and numerical equality evidence138. No new Job, source execution, public Bootstrap registration, checkpoint adoption or owner resume.',
    prior_evidence=['137 is incomplete at300s with saved exit0/quiet51.125s Job.',
        '138 saved numerical oracle matched,28.093s profiled body/83.50s test.',
        '145 fixture scopes added272 calls but no observed benefit; extension retired with open findings, not used here.'],
    budget=dict(wall_seconds=180, sampled_rss_bytes=1024**3, observed_storage_bytes=128*1024**2,
        basis='35-52s measured input fixture plus one full and three reused prepares. The missing cost is this diagnostic question, not an admitted whole-workflow estimate.',
        heartbeat='Immediate per-prepare start/completion JSON; each finished profile persisted. PID+creation/RSS/storage monitor.',
        stop='Fixed cap, no extension or retry. Preserve partial profiles and exact observed-process cleanup on failure.'),
    acceptance=['All four audits equal saved candidate, exact counts4/28/64, original operation closed.',
        'All candidate/source pins unchanged, entry aliases/handles closed and observed PIDs absent.',
        'Diagnostic receipt cannot authenticate public registry, retained owner heads or formal results.'],
    candidate_files=old['candidate_files'], scratch_contents_enumerated=False,
    files_sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in sorted(paths, key=str)},
    bounded_diagnostic_self_review_complete=True, whole_workflow_performance_review_complete=False,
    full_optimized_workflow_accepted=False, formal_result=False, formal_execution_ready=False,
    resource_admission=False, native_execution_authorized=False)
target = D/'saved137_n0_operation_diagnostic_plan_146.json'
with target.open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(value, stream, indent=2)
    stream.write('\n')
print(json.dumps(dict(path=str(target), sha256=sha256(target.read_bytes()).hexdigest(), pins=len(paths))))
