"""Keep frozen phase kernels unchanged; version only safe failure reporting."""
from hashlib import sha256
import json
from pathlib import Path

H=Path(__file__).resolve().parent;R=H.parents[3];D=H/'whole_workflow_optimization_01_non_authoritative'
bootstrap=(R/'experiments/h1_bootstrap_integration_development_v7.py').read_text(encoding='utf-8')
helper=bootstrap[bootstrap.index('def _bind_failure_reporter():'):bootstrap.index('def digest(value):')]
rows=[]
pairs=(('h1_phase_dependency_validation_operation_development_v1.py','h1_phase_dependency_validation_operation_development_v2.py'),
    ('h1_phase_manifest_binding_development_v3.py','h1_phase_manifest_binding_development_v4.py'),
    ('h1_phase_manifest_validation_operation_development_v1.py','h1_phase_manifest_validation_operation_development_v2.py'))
substitutions=tuple((before[:-3],after[:-3]) for before,after in pairs)
for old,new in pairs:
    source=R/'experiments'/old;target=R/'experiments'/new;raw=source.read_bytes();text=raw.decode('utf-8')
    for before,after in substitutions:text=text.replace(before,after)
    if 'manifest_binding' not in old:
        point=text.index('\ndef implementation_identity(')
        text=text[:point]+'\n'+helper+text[point:]
        text=text.replace('describe_error=BaseException.__repr__;add_note=BaseException.add_note',
            'describe_error=_failure_description;add_note=_note_failure')
        text=text.replace('describe=BaseException.__repr__;annotate=BaseException.add_note',
            'describe=_failure_description;annotate=_note_failure')
    with target.open('x',encoding='utf-8',newline='\n') as stream:stream.write(text)
    assert source.read_bytes()==raw
    rows.append(dict(source=str(source),source_sha256=sha256(raw).hexdigest(),
        draft=str(target),initial_sha256=sha256(target.read_bytes()).hexdigest()))
target=R/'experiments/h1_bootstrap_integration_development_v7.py'
text=target.read_text(encoding='utf-8')
for before,after in substitutions:text=text.replace(before,after)
target.write_text(text,encoding='utf-8',newline='\n')
out=D/'safe_phase_successors_origin_191.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:
    json.dump(dict(status='DRAFT_NONAUTHORITATIVE',origin_only_not_final_identity=True,files=rows,
        numerical_algorithm_changed=False,formal_result=False,formal_run_authority=False),stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),successors=len(rows))))
