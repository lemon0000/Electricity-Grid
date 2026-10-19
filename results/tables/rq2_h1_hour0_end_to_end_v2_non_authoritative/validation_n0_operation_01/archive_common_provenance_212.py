"""Preserve typed-graph and standalone provenance bytes before wiring."""
from hashlib import sha256
import json
from pathlib import Path

H=Path(__file__).resolve().parent;R=H.parents[3];D=H/'whole_workflow_optimization_01_non_authoritative'
graph=json.loads((D/'common_typed_graph_origin_205.json').read_bytes())
sources=[R/row['target'] for row in graph['files']]
for row,source in zip(graph['files'],sources,strict=True):assert sha256(source.read_bytes()).hexdigest()==row['after_sha256']
sources.extend((R/'experiments/h1_common_registry_provenance_development_v1.py',
    R/'tests/test_h1_common_registry_provenance_development_v1.py'))
label=H/'common_registry_provenance_units_211'
terminal=json.loads((label/'terminal.json').read_bytes());assert terminal['exit_code']==0 and terminal['source_unchanged']
assert terminal['observed_owned_processes_absent'] and not terminal['cleanup_errors'] and not terminal['storage_read_errors']
sources.extend(label/name for name in ('request.json','started.json','terminal.json','stdout.log'))
closed=Path('D:/h1_common_registry_provenance_211_non_authoritative/unit_code_read_lease_closed.json')
v=json.loads(closed.read_bytes());assert v['all_code_handles_closed'] and v['original_read_alias_restored']
sources.append(closed)
archive=D/'common_graph_provenance_212_preserved_non_authoritative';archive.mkdir(exist_ok=False)
copies=[]
for source in sources:
    target=archive/source.name;raw=source.read_bytes()
    with target.open('xb') as stream:stream.write(raw)
    assert target.read_bytes()==source.read_bytes()==raw
    copies.append(dict(source=str(source.relative_to(R)) if source.is_relative_to(R) else str(source),
        saved=str(target.relative_to(R)),sha256=sha256(raw).hexdigest()))
value=dict(schema='h1_common_provenance_evidence_212',status='STANDALONE_DRAFT_LAYER_ONLY',terminal=terminal,
    pytest_cases=12,pytest_seconds=.52,archive_files=copies,
    bootstrap_integration_complete=False,positive_genuine_bridge_activation_verified=False,
    common_authorized=False,new_N0_Jobs=0,real_native_calls=0,production_seal=False,official_review=False,
    full_optimized_workflow_accepted=False,whole_workflow_performance_review_complete=False,
    formal_execution_ready=False,formal_run_authority=False,formal_result=False,resource_admission=False)
out=D/'common_provenance_evidence_212.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha256(out.read_bytes()).hexdigest(),archives=len(copies))))
