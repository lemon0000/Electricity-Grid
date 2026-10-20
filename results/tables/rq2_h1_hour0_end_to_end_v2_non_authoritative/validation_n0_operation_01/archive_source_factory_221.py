"""Archive the scoped callable/factory checks before typed route edits."""
from hashlib import sha256
import json
from pathlib import Path

H=Path(__file__).resolve().parent;R=H.parents[3]
D=H/'whole_workflow_optimization_01_non_authoritative'
label=H/'callable_source_factory_units_220'
terminal=json.loads((label/'terminal.json').read_bytes())
request=json.loads((label/'request.json').read_bytes())
assert terminal['exit_code']==0 and terminal['source_unchanged']
assert terminal['observed_owned_processes_absent'] and not terminal['cleanup_errors'] and not terminal['storage_read_errors']
assert '40 passed in 4.31s' in (label/'stdout.log').read_text(encoding='utf-8')
files=[label/name for name in ('request.json','started.json','terminal.json','stdout.log')]
for stem in ('h1_validation_callable_state_development_v1','h1_common_registry_factory_development_v1'):
    for relative in ('experiments/'+stem+'.py','tests/test_'+stem+'.py'):
        current=R/relative;saved=label/'tested_bytes'/relative
        raw=saved.read_bytes();assert current.read_bytes()==raw
        assert sha256(raw).hexdigest()==request['source_sha256'][str(current)]
        files.append(saved)
closed=Path('D:/h1_callable_source_factory_220_non_authoritative/unit_code_read_lease_closed.json')
value=json.loads(closed.read_bytes())
assert value['all_code_handles_closed'] and value['original_read_alias_restored']
files.append(closed)
archive=D/'source_factory_221_preserved_non_authoritative';archive.mkdir(exist_ok=False)
copies=[]
for source in files:
    raw=source.read_bytes();target=archive/source.name
    with target.open('xb') as stream:stream.write(raw)
    assert target.read_bytes()==source.read_bytes()==raw
    copies.append(dict(source=str(source.relative_to(R)) if source.is_relative_to(R) else str(source),
        saved=str(target.relative_to(R)),sha256=sha256(raw).hexdigest()))
value=dict(schema='h1_source_factory_evidence_221',terminal=terminal,archive_files=copies,
    pytest_cases=40,pytest_seconds=4.31,
    scope='Standalone callable state and source-factory definition protocol on canonical temporary modules.',
    fixed_callable_findings=['dict order','nested identity and aliases','NaN bits and multiplicity',
        'aggregate scalar and integer limits','non-owning scalar digests','code/wrapped weak references'],
    source_factory_scope=['pinned no-argument factory blueprints','literal original source CALLsites',
        'ordered one-shot stages and footers','canonical import syntax and symbols','weak minted callable observations'],
    actual_Bridge_footer_integrated=False,bootstrap_common_binder_open=False,
    positive_genuine_bridge_activation_verified=False,common_authorized=False,
    independent_findings_closed=False,new_N0_Jobs=0,real_native_calls=0,
    full_optimized_workflow_accepted=False,whole_workflow_performance_review_complete=False,
    formal_execution_ready=False,formal_run_authority=False,formal_result=False,resource_admission=False)
out=D/'source_factory_evidence_221.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:
    json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha256(out.read_bytes()).hexdigest(),archives=len(copies))))
