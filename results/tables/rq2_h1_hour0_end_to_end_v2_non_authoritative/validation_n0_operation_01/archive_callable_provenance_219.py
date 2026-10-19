"""Preserve standalone provenance and callable-state terminal evidence."""
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import re

H=Path(__file__).resolve().parent;R=H.parents[3]
D=H/'whole_workflow_optimization_01_non_authoritative'
A=D/'callable_provenance_219_preserved_non_authoritative'
A.mkdir(exist_ok=False)
cases=(
    ('215','common_registry_provenance_units_215','D:/h1_common_registry_provenance_215_non_authoritative',
        'h1_common_registry_provenance_development_v1',0),
    ('216','callable_state_units_216','D:/h1_callable_state_216_non_authoritative',
        'h1_validation_callable_state_development_v1',1),
    ('217','callable_state_units_217','D:/h1_callable_state_217_non_authoritative',
        'h1_validation_callable_state_development_v1',0))
rows=[]
for number,label,base,stem,expected_exit in cases:
    source=H/label;request=json.loads((source/'request.json').read_bytes())
    terminal=json.loads((source/'terminal.json').read_bytes())
    assert terminal['exit_code']==expected_exit and terminal['source_unchanged']
    assert terminal['observed_owned_processes_absent']
    if expected_exit==0:
        assert not terminal['cleanup_errors'] and not terminal['storage_read_errors'] and terminal['final_storage_observation_complete']
    output=(source/'stdout.log').read_text(encoding='utf-8')
    matches=re.findall(r'(\d+) passed in ([\d.]+)s',output);assert len(matches)==1
    files=[source/name for name in ('request.json','started.json','terminal.json','stdout.log')]
    for relative in ('experiments/'+stem+'.py','tests/test_'+stem+'.py'):
        path=source/'tested_bytes'/relative
        raw=path.read_bytes()
        assert sha256(raw).hexdigest()==request['source_sha256'][str(R/relative)]
        files.append(path)
    closed=Path(base)/'unit_code_read_lease_closed.json'
    if expected_exit==0:
        value=json.loads(closed.read_bytes())
        assert value['all_code_handles_closed'] and value['original_read_alias_restored']
        files.append(closed)
    else:assert not closed.exists()
    target=A/number;target.mkdir()
    copies=[]
    for path in files:
        raw=path.read_bytes();saved=target/path.name
        with saved.open('xb') as stream:stream.write(raw)
        assert saved.read_bytes()==path.read_bytes()==raw
        copies.append(dict(source=str(path.relative_to(R)) if path.is_relative_to(R) else str(path),
            saved=str(saved.relative_to(R)),sha256=sha256(raw).hexdigest()))
    rows.append(dict(label=label,terminal=terminal,pytest_cases=int(matches[0][0]),
        pytest_seconds=float(matches[0][1]),overall_pass=expected_exit==0,
        failed_entry_preserved=expected_exit!=0,archive_files=copies))
value=dict(schema='h1_callable_provenance_evidence_219',observed_at_utc=datetime.now(timezone.utc).isoformat(),
    scope='Standalone draft checks only; synthetic canonical temporary modules, no real bridge activation.',
    cases=rows,source_factory_provenance_complete=False,bootstrap_integration_complete=False,
    common_authorized=False,new_N0_Jobs=0,real_native_calls=0,production_seal=False,official_review=False,
    full_optimized_workflow_accepted=False,whole_workflow_performance_review_complete=False,
    formal_execution_ready=False,formal_run_authority=False,formal_result=False,resource_admission=False)
out=D/'callable_provenance_evidence_219.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:
    json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha256(out.read_bytes()).hexdigest(),
    cases=[dict(label=row['label'],overall_pass=row['overall_pass']) for row in rows])))
