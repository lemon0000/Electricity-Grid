"""Unexecuted successor: align the core's fixed helper with the consumer parent."""
from pathlib import Path

ROOT=Path(__file__).absolute().parents[1]


def replace(source,pairs):
    for before,after,count in pairs:
        assert source.count(before)==count,(before,source.count(before));source=source.replace(before,after)
    return source.encode()


def core(source):
    return replace(source,[('nfc_v11_non_authoritative','nfc_v12_non_authoritative',2),
        ('staged_rts24_saved_fresh_entry_namespace_post_return_v1.py','staged_rts24_saved_fresh_entry_namespace_consumer_v2.py',1),
        ("set(plan['startup_profile'])=={'path','pin'},'two-stage startup profile'",
         "set(plan['startup_profile'])=={'path','pin'} and plan['startup_profile']['path']==str(ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v12_non_authoritative/startup_profile.json'),'two-stage startup profile'",1)])


def probe(source):return replace(source,[('nfc_v11_non_authoritative','nfc_v12_non_authoritative',1)])


def parent(source):
    raw=replace(source,[('nfc_v11_non_authoritative','nfc_v12_non_authoritative',1),
        ('lease_v38.py','lease_v39.py',1),('probe_v36.py','probe_v37.py',1),
        ("    return dict(schema='staged_saved_F_runtime_handoff_manifest_v1'","    plan=dict(schema='staged_saved_F_runtime_handoff_manifest_v1'",1),
        ('import_profile=import_profile,case=case)\n','import_profile=import_profile,case=case)\n    validate_manifest_pair(plan,code)\n    return plan\n',1)])
    return raw+b'''

def validate_manifest_pair(plan,code):
    core=load(CORE,'_paired_manifest_core')
    assert core.check_plan(canonical(plan))==plan and plan['bootstrap_pin']==pin(code)
    assert plan['case'] in ('discovery','normal')
    for key,path in (('namespace_helper',ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_consumer_v2.py'),
            ('import_helper',ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_post_return_v2.py'),('import_policy',OUT/'import_policy.json')):
        expected=dict(path=str(path),pin=pin(path.read_bytes()))
        assert plan[key]==expected and core.read_file(path,plan[key]['pin'])==path.read_bytes()
    if plan['case']=='normal':
        assert plan['startup_profile']==dict(path=str(OUT/'startup_profile.json'),pin=pin((OUT/'startup_profile.json').read_bytes()))
        assert plan['import_profile']==REFERENCE.reference()['reference']
    else:assert plan['startup_profile'] is plan['import_profile'] is None
    return plan
'''


def create():
    for before,after,fn in (
            ('experiments/staged_rts24_saved_fresh_pre_entry_lease_v38.py','experiments/staged_rts24_saved_fresh_pre_entry_lease_v39.py',core),
            ('tests/staged_rts24_saved_fresh_runtime_handoff_probe_v36.py','tests/staged_rts24_saved_fresh_runtime_handoff_probe_v37.py',probe),
            ('experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v35.py','experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v36.py',parent)):
        raw=fn((ROOT/before).read_text(encoding='utf8'));compile(raw,after,'exec',dont_inherit=True,optimize=0)
        path=ROOT/after
        if path.exists():assert path.read_bytes()==raw
        else:path.write_bytes(raw)


if __name__=='__main__':create()
