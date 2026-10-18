"""One bounded N0 check after an exact diagnosed registry-lifetime repair."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
value=json.loads((HERE/'fresh_n0_plan_03.json').read_bytes())
changed={'h1_historical_n0_verifier_development_v3.py','test_h1_registry_validation_operation_development_v1.py'}
for group in ('source_sha256','code_lease_sha256'):
    for name in value[group]:
        if Path(name).name in changed:value[group][name]=sha256(Path(name).read_bytes()).hexdigest()
code=value['code_lease_sha256']
old=HERE/'bounded_stable_read_entry_v1.py'
for name in tuple(code):
    if Path(name)==old:del code[name]
new=HERE/'bounded_stable_read_entry_v2.py'
code[str(new)]=sha256(new.read_bytes()).hexdigest()
sources=value['source_sha256'];sources.update(code)
for path in (Path(__file__),HERE/'run_fresh_n0_entry_v4.py',HERE/'run_fresh_n0_bounded_v4.py',
        REPO/'tests/test_h1_registry_runtime_store_binding_development_v1.py',
        REPO/'tests/test_h1_registry_dispatch_probe_development_v1.py',
        REPO/'tests/test_h1_bounded_stable_read_entry_development_v2.py',
        HERE/'registry_runtime_unit_02/request.json',HERE/'registry_runtime_unit_02/terminal.json',
        HERE/'bounded_entry_v2_unit_02/request.json',HERE/'bounded_entry_v2_unit_02/terminal.json',
        HERE/'registry_dispatch_monitor_03/terminal.json',
        HERE/'registry_dispatch_03_non_authoritative/bounded_closed_receipt.json',
        Path('D:/h1_registry_dispatch_03_non_authoritative/test_definition_dispatch_check0/dispatch_diagnostic.json'),
        HERE/'registry_sources_03_non_authoritative/patch_manifest.json',
        HERE/'registry_rebuild_check_03_non_authoritative/terminal.json',
        HERE/'bounded_common_arm_monitor_02/terminal.json',
        HERE/'bounded_common_arm_02_non_authoritative/metadata_receipt.json'):
    sources[str(path)]=sha256(path.read_bytes()).hexdigest()
assert len(code)==164
assert all(sha256(Path(p).read_bytes()).hexdigest()==pin for p,pin in sources.items())
for name in ('registry_runtime_unit_02/terminal.json','bounded_entry_v2_unit_02/terminal.json',
        'registry_dispatch_monitor_03/terminal.json','registry_rebuild_check_03_non_authoritative/terminal.json'):
    assert json.loads((HERE/name).read_bytes())['exit_code']==0
value.update(previous_attempt='03 exit1/513.594s: only static registry membership row changed after genuine owner acquired two locks; all source pins and cleanup preserved',
    corrected_cause='definition-time identity now fixes original registry set/module/lock; private operation resource records preserve complete runtime membership and original owner leases at every check',
    regression='126 registry/runtime/fault cases; 78 entry cases; real owner open/close checkpoint guard passes; deterministic three-source closure',
    entry_optimization='bounded entry v2 full/light routing; configured metadata windows retain live stock discovery',
    outer_output=str(HERE/'fresh_n0_monitor_04'),inner_output=str(HERE/'fresh_n0_entry_04_non_authoritative'),
    basetemp='D:/h1_registry_fresh_n0_04_non_authoritative',
    performance_basis='cold03 setup8.683s/owner-open32.819s/total-failure513.594s; configured identity v2 mean.237937s vs v1.292378s; complete new N0 remains unknown and capped600s',
    scope='cause-specific one-root one-hour synthetic diagnostic only; not whole-workflow performance admission',
    dag=['source closure and isolated configured paths','code/bounded-read and metadata owner before project imports',
        'original fresh source fixture without identity cache','new symbolic profile with unchanged science',
        'real owner and foreign-thread scope rejection','one owned synthetic Windows Job',
        'four N0 builds with 4 full+28 fresh and64contexts','old independent scientific oracle',
        'save execution receipt and retained heads','owner close','hooks/164codepaths/source/old-chain/10locks/PIDs postcheck'],
    acceptance_addition='original test unchanged: requires genuine Job exit0/quiescent, all four build receipts and oracle equality, not only successful process startup',
    stop='600s/1GiB sampled tree RSS/128MiB artifacts, first error/cap stop and preserve; no cap extension or unchanged retry',
    no_scientific_module_changes_since_registry_scope_unit_04=False,
    whole_workflow_performance_review_complete=False)
out=HERE/'fresh_n0_plan_04.json'
with out.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
print(json.dumps(dict(plan_sha256=sha256(out.read_bytes()).hexdigest(),source_files=len(sources),code_files=len(code))))
