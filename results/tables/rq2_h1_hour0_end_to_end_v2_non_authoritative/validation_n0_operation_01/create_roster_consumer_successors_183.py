"""Create fresh versioned drafts without changing the observed Core6 graph."""
from hashlib import sha256
import json
from pathlib import Path

H=Path(__file__).resolve().parent;R=H.parents[3]
D=H/'whole_workflow_optimization_01_non_authoritative'
pairs=(
    ('h1_bootstrap_integration_development_v6.py','h1_bootstrap_integration_development_v7.py'),
    ('h1_owned_bootstrap_controller_development_v6.py','h1_owned_bootstrap_controller_development_v7.py'),
    ('h1_historical_n0_verifier_development_v5.py','h1_historical_n0_verifier_development_v6.py'),
    ('h1_group_execution_roster_development_v4.py','h1_group_execution_roster_development_v5.py'),
)
rows=[]
for old,new in pairs:
    source=R/'experiments'/old;target=R/'experiments'/new
    raw=source.read_bytes();text=raw.decode('utf-8')
    for before,after in (
        ('h1_bootstrap_integration_development_v6','h1_bootstrap_integration_development_v7'),
        ('h1_owned_bootstrap_controller_development_v6','h1_owned_bootstrap_controller_development_v7'),
        ('h1_historical_n0_verifier_development_v5','h1_historical_n0_verifier_development_v6'),
        ('h1_group_execution_roster_development_v4','h1_group_execution_roster_development_v5'),
        ('Bootstrap6','Bootstrap7'),('Roster4','Roster5')):
        text=text.replace(before,after)
    if 'roster' in old:
        text=text.replace('h1_bootstrap_integration_development_v5','h1_bootstrap_integration_development_v7')
        text=text.replace('Bootstrap5','Bootstrap7').replace('verifier4','verifier6')
    with target.open('x',encoding='utf-8',newline='\n') as stream:stream.write(text)
    assert source.read_bytes()==raw
    rows.append(dict(source=str(source),source_sha256=sha256(raw).hexdigest(),
        draft=str(target),initial_sha256=sha256(target.read_bytes()).hexdigest()))
value=dict(schema='h1_roster_consumer_successors_origin_183',status='DRAFT_NONAUTHORITATIVE',
    sole_writer='root',origin_only_not_final_identity=True,files=rows,
    production_seal=False,official_review=False,formal_result=False,formal_run_authority=False)
out=D/'roster_consumer_successors_origin_183.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:
    json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha256(out.read_bytes()).hexdigest(),drafts=len(rows))))
