"""Preregister one bounded real-source arithmetic differential, without host authority."""
import ast
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3]
prior=json.loads((HERE/'parent_inspection_footprint_plan_04.json').read_bytes())
value=dict(prior)
members=[Path(__file__),HERE/'measure_parent_source_scientific_oracle_v2.py',
    HERE/'run_parent_source_scientific_oracle_bounded_v2.py',
    REPO/'experiments/h1_parent_source_n0_witness_development_v1.py',
    REPO/'experiments/h1_selector_parent_validation_operation_development_v1.py']
for path in members:ast.parse(path.read_bytes(),filename=str(path))
sources={name:sha256(Path(name).read_bytes()).hexdigest() for name in prior['source_sha256']}
sources.update({str(path):sha256(path.read_bytes()).hexdigest() for path in members})
for name,pin in {**prior['old_chain_sha256'],**prior['saved_sha256']}.items():
    if sha256(Path(name).read_bytes()).hexdigest()!=pin:raise ValueError('immutable saved/active input changed')
code=dict(prior['code_lease_sha256'])
code.update({str(path):sha256(path.read_bytes()).hexdigest() for path in members[-2:]})
value.update(question='Do genuine source/registry/historical bytes survive 16 independent full prepares, deferred fake-host activation and one reuse?',
    attempts=1,roots=0,hours=0,synthetic_jobs=0,native_calls=0,
    source_sha256=sources,code_lease_sha256=code,
    snapshot=str(Path(prior['fixture_base'])/'parent_non_authoritative/worker_non_authoritative/selector_snapshot.json'),
    inner_output=str(HERE/'parent_source_scientific_oracle_02_non_authoritative'),
    outer_output=str(HERE/'parent_source_scientific_oracle_monitor_02'),
    basetemp='D:/h1_parent_source_scientific_oracle_02_non_authoritative',expected_saved_locks=0,
    test_only_code_identity_cache=['adapter','Bootstrap2'],complete_source_fields_compared=True,baseline_source_prepares=1,candidate_source_prepares=17,early_stop_projected_seconds=540,
    modes=['real_source_arithmetic_with_explicit_fake_host_lease_and_activation'],
    live_Parent_credential_issued=False,complete_Parent_validation=False,
    whole_inspection_completion_required=False,full_Parent_optimization_admitted=False,
    changed_input_reason='plan01 first prepare projected beyond budget without full-target identity cache; use the identical adapter+Bootstrap2 code-identity bookends and compare complete source fields',
    dag=['fixed saved snapshot and original synthetic fixture',
        'one unchanged exact-source prepare as independent scientific byte oracle',
        '16 full exact-source prepares through the genuine new arithmetic witness',
        'explicit fake host activation then one numerical reuse with every original context',
        'exact decision/audit bytes, counts, cleanup and input/code/old-chain postchecks'],
    stop_conditions=['wall 600s, sampled process-tree RSS 768MiB, storage 128MiB',
        'after first candidate stop if measured remaining source work projects beyond 540s',
        'fail immediately on any scientific bytes, source pins, dispatch, counts or cleanup mismatch',
        'no repeated unchanged attempt or deadline extension'],
    limits=dict(wall_seconds=600,sampled_rss_bytes=768*1024**2,storage_bytes=128*1024**2))
path=HERE/'parent_source_scientific_oracle_plan_02.json'
with path.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
print(json.dumps(dict(plan_sha256=sha256(path.read_bytes()).hexdigest(),limits=value['limits'],
    baseline_prepares=1,candidate_prepares=17,early_stop_projected_seconds=540)))
