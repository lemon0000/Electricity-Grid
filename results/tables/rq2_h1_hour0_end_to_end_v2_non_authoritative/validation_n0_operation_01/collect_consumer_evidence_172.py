"""Preserve bounded consumer development observations; no authority or gate."""
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys

H=Path(__file__).resolve().parent;R=H.parents[3]
D=H/'whole_workflow_optimization_01_non_authoritative'
CASES={
    '169':('consumer_constructor_primary_units_169','D:/h1_consumer_constructor_primary_units_169_non_authoritative',None,()),
    '170':('bootstrap6_live_header_170','D:/h1_bootstrap6_header_170_non_authoritative','bootstrap6_live_header_plan_170.json',('bootstrap6_live_header_observation.json',)),
    '171':('saved152_consumer_dag_171','D:/h1_saved152_consumer_dag_171_non_authoritative','saved152_consumer_dag_plan_171.json',('saved152_consumer_dag_observation.json','saved152_consumer_dag_timing.jsonl')),
}
number,=sys.argv[1:];label,root,plan_name,outputs=CASES[number];base=Path(root)
terminal=json.loads((H/label/'terminal.json').read_bytes())
assert terminal['exit_code']==0 and terminal['source_unchanged']
assert terminal['observed_owned_processes_absent'] and not terminal['cleanup_errors']
assert not terminal['storage_read_errors'] and terminal['final_storage_observation_complete']
stdout=(H/label/'stdout.log').read_text(encoding='utf-8');match=re.search(r'(\d+) passed in ([\d.]+)s',stdout)
assert match is not None
closed_path=base/'unit_code_read_lease_closed.json';closed=json.loads(closed_path.read_bytes())
assert closed['all_code_handles_closed'] and closed['original_read_alias_restored']
if number!='169':
    assert closed['all_metadata_handles_closed'] and closed['original_metadata_version_alias_restored']
    assert closed['all_path_handles_closed'] and closed['canonical_path_alias_restored']
    assert closed['canonical_path_state']=='closed' and closed['pending_path_handles']==0
paths=[closed_path];observations={}
for name in outputs:
    found=list(base.glob('*/'+name));assert len(found)==1
    paths.extend(found)
    if name.endswith('.json'):observations[name]=json.loads(found[0].read_bytes())
plan=json.loads((D/plan_name).read_bytes()) if plan_name else None
if plan:
    drift=[path for path,pin in plan['files_sha256'].items() if sha256(Path(path).read_bytes()).hexdigest()!=pin]
    assert not drift,drift
else:drift=[]
saved_files=None
if number=='171':
    saved=Path('D:/h1_bootstrap5_retained_152_non_authoritative')
    expected={Path(path) for path in plan['files_sha256'] if Path(path).is_relative_to(saved)}
    actual=set();pending=[saved]
    while pending:
        directory=pending.pop()
        for entry in os.scandir(directory):
            info=entry.stat(follow_symlinks=False);assert not info.st_file_attributes&0x400
            if entry.is_dir(follow_symlinks=False):
                if entry.name!='scratch_non_authoritative':pending.append(Path(entry.path))
            else:actual.add(Path(entry.path))
    assert actual==expected
    saved_files=len(actual)
archive=D/('consumer_'+number+'_preserved_non_authoritative');archive.mkdir(exist_ok=False)
copies=[]
for source in paths:
    target=archive/source.name;raw=source.read_bytes()
    with target.open('xb') as stream:stream.write(raw)
    assert source.read_bytes()==target.read_bytes()==raw
    copies.append(dict(source=str(source),saved=str(target),sha256=sha256(raw).hexdigest()))
core=['experiments/h1_bootstrap_integration_development_v6.py',
    'experiments/h1_owned_bootstrap_controller_development_v6.py',
    'experiments/h1_historical_n0_verifier_development_v5.py',
    'tests/test_h1_consumer_registry_read_development_v6.py',
    'tests/test_h1_registry_validation_operation_development_v5.py',
    'tests/test_h1_bootstrap6_live_header_development_v1.py',
    'tests/test_h1_saved152_consumer_dag_development_v5.py']
entry_summary={key:value for key,value in closed.items() if key!='files_sha256'}
value=dict(schema='h1_consumer_evidence_'+number,status='VERIFIED_SCOPED_DEVELOPMENT_OBSERVATION',
    terminal=terminal,pytest_cases=int(match[1]),pytest_seconds=float(match[2]),
    source_sha256={path:sha256((R/path).read_bytes()).hexdigest() for path in core},
    plan_sha256=sha256((D/plan_name).read_bytes()).hexdigest() if plan_name else None,
    planned_pins=len(plan['files_sha256']) if plan else None,pin_drift=drift,
    entry_closed=entry_summary,observations=observations,archive_files=copies,
    preserved_saved_file_names_and_bytes=saved_files,
    empty_directory_namespace_equality_proven=False,scratch_contents_enumerated=False,
    observations_are_data_not_consumer_credentials=True,
    new_N0_Jobs=0,real_native_calls=0,original152_public_bootstrap_return_verified=False,
    original152_graceful_cleanup_verified=False,production_seal=False,official_review=False,
    whole_workflow_performance_review_complete=False,full_optimized_workflow_accepted=False,
    formal_execution_ready=False,formal_run_authority=False,formal_result=False,
    resource_admission=False,native_execution_authorized=False)
out=D/('consumer_result_'+number+'.json')
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha256(out.read_bytes()).hexdigest(),cases=value['pytest_cases'],
    pytest_seconds=value['pytest_seconds'],outer_seconds=terminal['elapsed_seconds'],archive_files=len(copies))))
