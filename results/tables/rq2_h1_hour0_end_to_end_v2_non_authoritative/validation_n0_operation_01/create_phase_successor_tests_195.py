"""Version the relevant existing phase regressions and fault fixtures."""
from pathlib import Path

R=Path(__file__).resolve().parents[4]
pairs=(('test_h1_phase_dependency_validation_operation_development_v1.py','test_h1_phase_dependency_validation_operation_development_v2.py'),
    ('test_h1_phase_dependency_window_faults_development_v1.py','test_h1_phase_dependency_window_faults_development_v2.py'),
    ('test_h1_phase_manifest_binding_development_v3.py','test_h1_phase_manifest_binding_development_v4.py'),
    ('test_h1_phase_manifest_validation_operation_development_v1.py','test_h1_phase_manifest_validation_operation_development_v2.py'))
replacements=(('h1_phase_dependency_validation_operation_development_v1','h1_phase_dependency_validation_operation_development_v2'),
    ('h1_phase_dependency_window_faults_development_v1','h1_phase_dependency_window_faults_development_v2'),
    ('h1_phase_manifest_binding_development_v3','h1_phase_manifest_binding_development_v4'),
    ('h1_phase_manifest_validation_operation_development_v1','h1_phase_manifest_validation_operation_development_v2'))
for old,new in pairs:
    source=R/'tests'/old;target=R/'tests'/new;text=source.read_text(encoding='utf-8')
    for before,after in replacements:text=text.replace(before,after)
    with target.open('x',encoding='utf-8',newline='\n') as stream:stream.write(text)
print('Created four phase successor regression files')
