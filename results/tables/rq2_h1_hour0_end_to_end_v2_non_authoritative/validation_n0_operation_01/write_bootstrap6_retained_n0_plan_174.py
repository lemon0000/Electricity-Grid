"""Plan one new-version synthetic public N0 lifecycle with fixed resource cap."""
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

H=Path(__file__).resolve().parent;R=H.parents[3];D=H/'whole_workflow_optimization_01_non_authoritative'
previous=D/'bootstrap5_retained_n0_bounded_plan_152.json';value=json.loads(previous.read_bytes())
paths={Path(p) for p in value['files_sha256']}
paths.update((R/'tests').glob('*h1*.py'));paths.update((R/'experiments').glob('h1_*.py'))
paths.update((Path(__file__),H/'run_unit_entry_v6.py',H/'run_unit_bounded_v19.py'))
for name in ('consumer_result_169.json','consumer_result_170.json','consumer_result_171.json',
        'consumer_pre_seal_input_173.json','bootstrap5_retained_n0_bounded_result_152.json'):
    paths.add(D/name)
base=Path('D:/h1_bootstrap6_retained_174_non_authoritative');label='bootstrap6_retained_n0_174'
assert not base.exists() and not (H/label).exists()
value.update(schema='h1_bootstrap6_retained_n0_bounded_plan_174',at_utc=datetime.now(timezone.utc).isoformat(),
    predecessor_plan_sha256=sha256(previous.read_bytes()).hexdigest(),
    command=[sys.executable,'-B',str(H/'run_unit_bounded_v19.py'),label,'400','1024','128','--',
        str(H/'run_unit_entry_v6.py'),'-s','-p','no:faulthandler','--basetemp',str(base),
        '--junitxml',str(base/'registered_development_true.xml'),'-o','junit_family=legacy',
        'tests/test_h1_registry_validation_retained_n0_development_v4.py::test_cold_bootstrap6_retained_n0_registration_and_close'],
    question='Can exact Bootstrap6/Owned6/Verifier5 return a genuine registered synthetic N0 public result, preserve its receipt and external heads, retire original proof records, and close within the new fixed400s diagnostic budget?',
    dag=['Reuse only explicit prepared source/Job synthetic seams; cold-import the current versioned graph after those definitions.',
        'Build a genuine source-bound Bootstrap6 profile and one fresh study/owner; empty constructor read uses original guard/nonce and retires its scope.',
        'Refuse foreign creator use of the original private scope route; call literal bootstrap(registered_development=True) once.',
        'Observe eight hash-linked external retention callbacks, file flush/fsync and fresh-name rename before acknowledgement; no retained heads are derived from a suffix.',
        'Run one original synthetic Windows Job, three synthetic reports, one simulated hour and zero native calls.',
        'Original producer four-build DAG:4full/28fresh/64contexts; capture actual public return and exact execution-receipt bytes immediately.',
        'Close producer scope and retire its original private records; save returned heads/report; close owner and require no pending registry capsule or original guard/nonce.',
        'Check phase/code/path/metadata closure, JUnit, pinned bytes and observed-process terminal. Run oracle/reopen later on saved records without repeating this Job.'],
    files_sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in sorted(paths,key=str)},
    numerical_oracle_is_separate_postcheck=True,matched_whole_workflow_comparison=False,
    old152_original_return_or_cleanup_reinterpreted=False,
    whole_workflow_performance_review_complete=False,full_optimized_workflow_accepted=False,
    production_seal=False,official_review=False,formal_run_authority=False)
value['scale'].update(consumer_constructor_read_scopes=1,public_inspects=0,maximum_live_or_pending_registry_records=16)
value['optimization'].update(
    reused_evidence=['Legacy chain07 body/postcheck04 complete; no rerun.',
        '152 Job exit0/quiet49.281s; original public return remains incomplete.153 original oracle and154 external-head readonly state verified; all152 bytes preserved.',
        '169 current150 targeted cases and170 genuine current empty header with complete source-preserving cleanup.',
        '171 same saved152 audit/decision bytes: baseline16full/16fresh/64contexts65.773s versus two2-build operations8full/24fresh/64contexts56.376s. Single fixed-order unprofiled local comparison.',
        '173 exact candidate independent pre-seal audit input; named findings must be closed before launch.'],
    changes_since137='New versioned Bootstrap6/Owned6/Verifier5 graph, method-bound consumer scope, explicit original record retirement and bounded close retry, primary-preserving constructor; no frozen science/config/threshold change.',
    callback_counts='Exactly one synthetic Job and expected8 retained head callbacks; observe actual complete registry and phase receipts.',
    limitations='The producer still has the original4-build numerical DAG;171 consumer improvement does not predict this public runtime or full chain. Roster5/full typed consumers, formal/native/resource gates remain open.')
value['budget'].update(wall_seconds=400,
    basis='152 last external global retention occurred at body240.666s after fixture47.073s; two remaining producer registry confirmations and public/phase cleanup were not observed before300.25s.171 same-data full/reused unprofiled prepares16.2/11.7s; remaining two reused prepares plus original metadata/closure and fixture imply roughly320-360s with uncertainty. New400s fixed diagnostic bound covers complete current-version lifecycle;152 is neither resumed nor extended.',
    historical='152 stays immutable incomplete at its original300.25s cap. This first genuine Bootstrap6 registration is required to validate current ownership/retirement semantics, not to alter152 status or scientific acceptance limits.',
    heartbeat='Fixture/import/owner open, every persisted retention, immediate actual public return/receipt and owner close; sampled PID+creation/RSS/nonfollow storage.',
    no_progress='Fixed400s, no extension or automatic retry. Quiet numeric replay is not evidence of deadlock; preserve partial terminal and use saved records for later checks.')
value['acceptance']=[
    'exit0/JUnit1passed; exactly1 synthetic N0 Job,3synthetic reports,1simulated hour,Job exit0/quiescent,0native',
    'literal True genuine public return saved before optional assertions; four builds4full/28fresh/64contexts and unchanged original scientific payload',
    'eight externally persisted callback records chained/CAS-consistent before acknowledgement, no suffix adoption',
    'producer records retired; empty constructor observation honest; pending registry capsules0, original nonceNone/guardunlocked',
    'owner/phase/code/path/metadata cleanup complete; all pins unchanged, observed PIDs absent/cleanup0',
    'separate saved-data oracle/reopen still required; no full chain, native, resource, formal or152 original success claim']
out=D/'bootstrap6_retained_n0_bounded_plan_174.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha256(out.read_bytes()).hexdigest(),pins=len(paths))))
