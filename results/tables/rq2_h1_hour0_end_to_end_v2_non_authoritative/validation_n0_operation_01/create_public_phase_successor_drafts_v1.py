"""Create fresh provisional successor files from preserved predecessor bytes."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
recipes=[
 ('h1_historical_n0_verifier_development_v3','h1_historical_n0_verifier_development_v4',[
   ('h1_historical_n0_verifier_development_v3','h1_historical_n0_verifier_development_v4'),
   ('h1_bootstrap_integration_development_v4','h1_bootstrap_integration_development_v5')]),
 ('h1_owned_bootstrap_controller_development_v4','h1_owned_bootstrap_controller_development_v5',[
   ('h1_bootstrap_integration_development_v4','h1_bootstrap_integration_development_v5')]),
 ('h1_bootstrap_integration_development_v4','h1_bootstrap_integration_development_v5',[
   ('h1_bootstrap_integration_development_v4','h1_bootstrap_integration_development_v5'),
   ('h1_owned_bootstrap_controller_development_v4','h1_owned_bootstrap_controller_development_v5'),
   ('h1_historical_n0_verifier_development_v3','h1_historical_n0_verifier_development_v4'),
   ('h1_phase_manifest_binding_development_v2','h1_phase_manifest_binding_development_v3')]),
 ('h1_group_execution_roster_development_v3','h1_group_execution_roster_development_v4',[
   ('h1_group_execution_roster_development_v3','h1_group_execution_roster_development_v4'),
   ('h1_bootstrap_integration_development_v4','h1_bootstrap_integration_development_v5'),
   ('Bootstrap4','Bootstrap5'),('verifier3','verifier4')]),
]
record=[]
for old,new,replacements in recipes:
    source=ROOT/'experiments'/(old+'.py');target=ROOT/'experiments'/(new+'.py')
    assert not target.exists(),str(target)
    raw=source.read_bytes();text=raw.decode('utf-8')
    for before,after in replacements:
        assert before in text,before
        text=text.replace(before,after)
    with target.open('x',encoding='utf-8',newline='\n') as stream:stream.write(text)
    record.append(dict(source=str(source.relative_to(ROOT)),source_sha256=sha256(raw).hexdigest(),
        target=str(target.relative_to(ROOT)),initial_draft_sha256=sha256(target.read_bytes()).hexdigest(),
        replacements=replacements))
out=HERE/'whole_workflow_optimization_01_non_authoritative'/'public_phase_successor_draft_origin_01.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:
    json.dump(dict(status='DRAFT_NONAUTHORITATIVE',mechanical_origins=record,
        semantic_integration_pending=True,formal_result=False,formal_run_authorized=False),stream,indent=2)
    stream.write('\n')
print(json.dumps(dict(created=len(record),origin=str(out))))
