"""Keep the predecessor probe and derive the exact Bootstrap5 opt-in probe."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
source=ROOT/'tests/test_h1_registry_validation_fresh_n0_development_v1.py'
target=ROOT/'tests/test_h1_registry_validation_fresh_n0_development_v2.py'
text=source.read_text(encoding='utf-8')
replacements=(
    ('Cold static successor: one real synthetic Job through N0 registration only.',
     'Cold Bootstrap5: one synthetic Job, numerical N0 registration and close.'),
    ('h1_historical_n0_verifier_development_v3','h1_historical_n0_verifier_development_v4'),
    ('h1_bootstrap_integration_development_v4','h1_bootstrap_integration_development_v5'),
    ('h1_owned_bootstrap_controller_development_v4','h1_owned_bootstrap_controller_development_v5'),
    ("    monkeypatch.setattr(m.BootstrapOwner,'_continue_bootstrap',m.BootstrapOwner._continue_registered_development)\n",''),
    ("retain_global_head=s.retain,retain_bootstrap_head=s.retain)",
     "retain_global_head=retain,retain_bootstrap_head=retain)"),
    ("        result=owner.bootstrap();trace('N0_registered')",
     "        result=owner.bootstrap(registered_development=True);trace('N0_registered')"))
counts=[]
for old,new in replacements:
    count=text.count(old);assert count>0,old;counts.append(dict(old=old,new=new,count=count))
    text=text.replace(old,new)
needle='    owner=m.BootstrapOwner(declaration,create=True,create_study=True,\n'
insert=("    retentions=[]\n"
    "    def retain(root,before,after):\n"
    "        assert m.phase_manifest.observation._CLEANUP_DIAGNOSTICS()['active_operations']==0\n"
    "        retentions.append(str(root))\n"
    "        return s.retain(root,before,after)\n")
assert text.count(needle)==1;text=text.replace(needle,insert+needle)
text += ("    receipt=owner.phase_validation_receipt()\n"
    "    assert receipt['all_segments_closed'] and receipt['lifecycle_complete']\n"
    "    assert receipt['pending_cleanup_windows']==0 and retentions\n"
    "    assert receipt['implementation_observation']=='segment_entry_exit'\n"
    "    cleanup=m.phase_manifest.observation._CLEANUP_DIAGNOSTICS()\n"
    "    assert cleanup['active_operations']==cleanup['abandoned_pending_operations']==0\n"
    "    (tmp_path/'n0_phase_segments_closed.json').write_bytes(m.encode(dict(\n"
    "        receipt=receipt,retentions=retentions,cleanup=cleanup,\n"
    "        registered_development_opt_in=True,bootstrap_callable_replaced=False,\n"
    "        current_source_header_reopen_verified=False,N0_reopen_verified=False,\n"
    "        synthetic_source_and_Job_seams=True,formal_result=False,resource_admission=False)))\n")
with target.open('x',encoding='utf-8',newline='\n') as stream:stream.write(text)
out=HERE/'whole_workflow_optimization_01_non_authoritative/bootstrap5_n0_diagnostic_origin_136.json'
value=dict(source=str(source.relative_to(ROOT)),source_sha256=sha256(source.read_bytes()).hexdigest(),
    target=str(target.relative_to(ROOT)),target_sha256=sha256(target.read_bytes()).hexdigest(),
    replacements=counts,additional_assertions='retain callbacks have no phase handles; complete phase closure and diagnostic receipt after owner close',
    formal_result=False,resource_admission=False)
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(target=str(target),sha256=value['target_sha256'])))
