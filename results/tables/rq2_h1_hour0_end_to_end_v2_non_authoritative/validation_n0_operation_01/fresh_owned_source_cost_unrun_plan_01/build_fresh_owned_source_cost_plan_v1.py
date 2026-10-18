"""One new-root Bootstrap2 N0/source cost diagnostic; no existing archive handles."""
import ast
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3]
prior=json.loads((HERE/'parent_source_profile_plan_03.json').read_bytes())
sources={name:sha256(Path(name).read_bytes()).hexdigest() for name in prior['source_sha256']}
code=dict(prior['code_lease_sha256'])
members=(Path(__file__),HERE/'run_fresh_owned_source_cost_bounded_v1.py',HERE/'run_n0_path_entry_v1.py',
    REPO/'tests/test_h1_hour0_n0_source_cost_development_v1.py',
    REPO/'tests/test_h1_hour0_end_to_end_development_v4.py')
for path in members:
    raw=path.read_bytes();ast.parse(raw,filename=str(path));sources[str(path)]=sha256(raw).hexdigest()
for path in members[-2:]:code[str(path)]=sources[str(path)]
source_paths={Path(name):pin for name,pin in sources.items()}
if any(source_paths.get(Path(name))!=pin for name,pin in code.items()):
    raise ValueError('code/source maps must match')
for name,pin in prior['old_chain_sha256'].items():
    if sha256(Path(name).read_bytes()).hexdigest()!=pin:raise ValueError('protected active source differs')
base='D:/h1_fresh_owned_source_cost_01_non_authoritative'
value=dict(status='DRAFT_NONAUTHORITATIVE',attempts=1,
    question='Measure actual Bootstrap2 N0 and source cost with full target code/metadata/path fixture coverage',
    pytest_target='tests/test_h1_hour0_n0_source_cost_development_v1.py::test_closed_owned_n0_original_source_cost',
    basetemp=base,path_roots=[str(REPO),str(Path(base))],
    inner_output=str(HERE/'fresh_owned_source_cost_01_non_authoritative'),
    outer_output=str(HERE/'fresh_owned_source_cost_monitor_01'),
    source_sha256=sources,code_lease_sha256=code,old_chain_sha256=prior['old_chain_sha256'],
    new_controller_roots=1,source_prefix_completed_hours=1,synthetic_jobs=1,real_native_calls=0,
    original_source_prepares=1,bootstrap_module='experiments.h1_bootstrap_integration_development_v2',
    roster_owners=0,common_owners=0,selector_Parents=0,
    test_only_code_identity_cache=['adapter','Bootstrap2'],source_data_cached=False,
    whole_workflow_performance_review_complete=False,full_hour0_chain_passed=False,formal_result=False,
    resource_admission=False,native_execution_authorized=False,
    limits=dict(wall_seconds=600,sampled_rss_bytes=768*1024**2,storage_bytes=128*1024**2),
    performance_basis='source oracle03 reuse20.4668s but repo-only paths; profile03 found3453 path fallbacks; prior600s cold target used Bootstrap4 without its identity cache, so it is a different path',
    dag=['fixed code/source closure and isolated configured interpreter',
        'code/bounded reads, metadata windows and path lease over REPO plus new own basetemp',
        'current complete_group fixture setup with adapter and Bootstrap2 identity bookends',
        'one Bootstrap2 owner and one fake N0 Windows Job through complete registration',
        'persist terminal pins, verify quiescence, close owner and all its original cleanup leases',
        'one original exact-source prepare over these new completed bytes, with full field artifact',
        'identity restore, path/code/metadata cleanup, owned new lock/PID and old36 postchecks'],
    stop_conditions=['600s hard wall, sampled process tree RSS768MiB or128MiB new artifacts',
        'first schema/source/process/cleanup failure stops; no same-config retry or cap extension',
        'no existing chain06 or chain07 directory share handles or process lifecycle action'],
    remaining_unknowns=['complete 3-arm/common/Parent/Handoff/paired/reopen costs remain unmeasured'])
for key in ('basetemp','inner_output','outer_output'):
    if Path(value[key]).exists():raise ValueError('unused diagnostic roots required')
path=HERE/'fresh_owned_source_cost_plan_01.json'
with path.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
print(json.dumps(dict(plan_sha256=sha256(path.read_bytes()).hexdigest(),limits=value['limits'],
    source_files=len(sources),code_files=len(code))))
