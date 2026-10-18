"""One cause-specific profile; no repeated 17-prepare oracle or long-chain authority."""
import ast
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3]
value=json.loads((HERE/'parent_source_scientific_oracle_plan_03.json').read_bytes())
candidate=json.loads((HERE/'parent_source_scientific_oracle_03_non_authoritative/candidate_1.json').read_bytes())
baseline=json.loads((HERE/'parent_source_scientific_oracle_03_non_authoritative/baseline.json').read_bytes())
sources={name:sha256(Path(name).read_bytes()).hexdigest() for name in value['source_sha256']}
code=dict(value['code_lease_sha256'])
changed=[]
allowed={REPO/'experiments/h1_selector_parent_validation_operation_development_v1.py'}
for name,pin in code.items():
    actual=sha256(Path(name).read_bytes()).hexdigest()
    if actual!=pin:
        if Path(name) not in allowed:raise ValueError('unrelated code lease drift: '+name)
        changed.append(dict(path=name,before=pin,after=actual));code[name]=actual
members=(Path(__file__),HERE/'measure_parent_source_profile_v1.py',HERE/'run_parent_source_profile_bounded_v1.py',
    REPO/'tests/h1_hour0_saved_replay_v2.py',REPO/'experiments/h1_group_n0_common_input_binding_development_v2.py')
for path in members:
    raw=path.read_bytes();ast.parse(raw,filename=str(path));sources[str(path)]=sha256(raw).hexdigest()
for path in members[-2:]:code[str(path)]=sources[str(path)]
source_paths={Path(name):pin for name,pin in sources.items()}
if any(source_paths.get(Path(name))!=pin for name,pin in code.items()):
    raise ValueError('every fixed code lease and direct origin must have a matching source pin')
for name,pin in {**value['old_chain_sha256'],**value['saved_sha256']}.items():
    if sha256(Path(name).read_bytes()).hexdigest()!=pin:raise ValueError('fixed inputs changed')
value.update(question='Which actual nested source functions account for repeated work under the full-target identity fixture?',
    source_sha256=sources,code_lease_sha256=code,changed_code_pins=changed,
    attempts=1,baseline_source_prepares=1,candidate_source_prepares=0,
    source_profile_count=1,profiler_overhead_included=True,
    expected_decision_sha256=baseline['decision_sha256'],expected_audit_sha256=baseline['audit_sha256'],
    expected_complete_projection_sha256=candidate['complete_source_projection_sha256'],
    inner_output=str(HERE/'parent_source_profile_03_non_authoritative'),
    outer_output=str(HERE/'parent_source_profile_monitor_03'),
    basetemp='D:/h1_parent_source_profile_03_non_authoritative',
    changed_input_reason='profile02 rejected a direct fixture module missing from inherited source closure before arithmetic; pin both exact direct dependencies in source and code lease maps and assert map consistency before launch',
    modes=['one_profiled_original_source_prepare'],
    dag=['fixed saved inputs, code/metadata/path leases and declared pure-code identity scope',
        'canonical helper dependencies preloaded under configured paths and exact source SHA',
        'one profiled original source prepare; compare decision/audit and complete field projection',
        'save primitive/total calls, self/cumulative instrumented timings and cleanup receipts',
        'outer checks all source/saved/old-chain pins and owned PID absence'],
    stop_conditions=['180s wall, sampled tree RSS 768MiB, storage 128MiB',
        'fail on undeclared imports, path insertions, source field mismatch or cleanup drift',
        'no repeat of unchanged profile and no whole-chain runtime extrapolation'],
    limits=dict(wall_seconds=180,sampled_rss_bytes=768*1024**2,storage_bytes=128*1024**2))
path=HERE/'parent_source_profile_plan_03.json'
with path.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
print(json.dumps(dict(plan_sha256=sha256(path.read_bytes()).hexdigest(),limits=value['limits'],source_prepares=1)))
