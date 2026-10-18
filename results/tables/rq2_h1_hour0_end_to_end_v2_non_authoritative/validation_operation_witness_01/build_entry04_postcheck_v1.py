"""Mechanical follow-up of the closed entry03 lifecycle postcheck."""
from pathlib import Path

HERE=Path(__file__).resolve().parent
source=HERE.parent/'validation_selector_incremental_01/postcheck_configured_entry_03.py'
text=source.read_text(encoding='utf-8')
replacements={
    'entry_revision_03':'entry_revision_04',
    'e5a7893d2b88812e46c8000463f8e03ba4195ac6ac189b41e68d3af43922d139':
        'd13a08fe6db35e9c5c70b8204e3fb4d0091e43a3ef483e3951a561eac0667e43',
    'assert len(members)==20':'assert len(members)==21',
    'unit_checks_07':'unit_checks_01','routing_checks_02':'routing_checks_01',
    'configured_entry_03_unit_monitor_07':'configured_entry_04_unit_monitor_01',
    'configured_entry_03_routing_monitor_02':'configured_entry_04_routing_monitor_01',
    'validation_selector_incremental_01/configured_entry_comparison_02.json':
        'validation_operation_witness_01/path_order_comparison_01.json',
    'configured_entry_03_checks_01.json':'configured_entry_04_checks_01.json',
}
for old,new in replacements.items():
    if old not in text:raise ValueError('mechanical postcheck anchor missing: '+old)
    text=text.replace(old,new)
anchor='    evidence={};boundaries={};processes={}\n'
addition='''    predecessor=read(ENTRY/'configured_predecessor_package_manifest.json')['files_sha256']
    assert set(members)==set(predecessor)|{'configured_predecessor_package_manifest.json'}
    assert all(members[name]==h for name,h in predecessor.items() if name!='interpreter_path_policy_v1.json')
    old_policy=read(ROOT/'entry_revision_03/interpreter_path_policy_v1.json')
    new_policy=read(ENTRY/'interpreter_path_policy_v1.json')
    old_policy['configured_paths'][-2:]=reversed(old_policy['configured_paths'][-2:])
    assert old_policy==new_policy
'''
if text.count(anchor)!=1:raise ValueError('postcheck insertion anchor differs')
text=text.replace(anchor,addition+anchor)
with (HERE/'postcheck_entry04_v1.py').open('x',encoding='utf-8') as stream:stream.write(text)
print('entry04 postcheck constructed')
