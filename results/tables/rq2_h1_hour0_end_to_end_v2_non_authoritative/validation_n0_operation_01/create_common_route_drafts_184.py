"""Reserve the two exact consumer source graphs before Core7 definition."""
from hashlib import sha256
import json
from pathlib import Path

H=Path(__file__).resolve().parent;R=H.parents[3]
D=H/'whole_workflow_optimization_01_non_authoritative';rows=[]
for before,after in ((7,9),(8,10)):
    source=R/'experiments'/f'h1_group_n0_common_input_binding_development_v{before}.py'
    target=R/'experiments'/f'h1_group_n0_common_input_binding_development_v{after}.py'
    original=source.read_bytes();text=original.decode('utf-8')
    text=text.replace(f'h1_group_n0_common_input_binding_development_v{before}',
        f'h1_group_n0_common_input_binding_development_v{after}')
    text=text.replace('h1_group_execution_roster_development_v2','h1_group_execution_roster_development_v5')
    text+='\n# A fixed definition-time handshake; never bind from a prepare call.\n'
    text+='bootstrap._bind_common_registry_reader(sys.modules[__name__])\n'
    with target.open('x',encoding='utf-8',newline='\n') as stream:stream.write(text)
    assert source.read_bytes()==original
    rows.append(dict(source=str(source),source_sha256=sha256(original).hexdigest(),
        draft=str(target),initial_sha256=sha256(target.read_bytes()).hexdigest()))
out=D/'common_route_draft_origin_184.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:
    json.dump(dict(status='DRAFT_NONAUTHORITATIVE',origin_only_not_final_identity=True,
        implementation_complete=False,genuine_common_bridge_integrated=False,files=rows),stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),drafts=len(rows))))
