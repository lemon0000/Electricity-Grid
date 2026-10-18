"""Repair the unsealed diagnostic draft; prior checked bytes remain archived."""
from hashlib import sha256
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3]
P=HERE.parent/'validation_path_optimization_01';entry=P/'entry_revision_05'
manifest_path=entry/'package_manifest_v1.json';old=manifest_path.read_bytes()
if sha256(old).hexdigest()!='994dd1abf1d8b703286ce627f3f0eeaacd20972bc11f2ea6b29dd1c5d17345bb':
    raise ValueError('pre-review diagnostic draft differs')
for name,pin in json.loads(old)['files_sha256'].items():
    if name!='validation_entry.py' and sha256((entry/name).read_bytes()).hexdigest()!=pin:raise ValueError('pre-review member drift')
# unit_checks_02/tested_bytes contains the complete prior package/code/tests.
if (entry/'unit_checks_02/tested_bytes/package_manifest_v1.json').read_bytes()!=old:
    raise ValueError('prior draft evidence is not preserved')
(entry/'slice_review_round2_package_manifest.json').write_bytes(old)
tests_path=entry/'test_closure_v1.json';tests=json.loads(tests_path.read_bytes())
for name in ('h1_guarded_common_slice_helpers_development_v1','test_h1_guarded_common_slice_development_v1',
        'test_h1_common_slice_monitor_development_v1'):
    path=REPO/'tests'/(name+'.py')
    tests['files_sha256'][path.relative_to(REPO).as_posix()]=sha256(path.read_bytes()).hexdigest()
tests_path.write_text(json.dumps(tests,indent=2)+'\n',encoding='utf-8',newline='\n')
members={p.name:sha256(p.read_bytes()).hexdigest() for p in sorted(entry.iterdir())
    if p.is_file() and p.name not in ('package_manifest_v1.json','launch_validation.py')}
new=dict(schema='h1_configured_validation_package_development_v1',files_sha256=members,
    formal_result=False,formal_execution_ready=False,native_execution_authorized=False)
raw=(json.dumps(new,indent=2)+'\n').encode();pin=sha256(raw).hexdigest()
manifest_path.write_bytes(raw)
launcher=entry/'launch_validation.py'
text,count=re.subn(r"MANIFEST_SHA='[0-9a-f]{64}'","MANIFEST_SHA='"+pin+"'",launcher.read_text(encoding='utf-8'))
if count!=1:raise ValueError('one launcher binding required')
launcher.write_text(text,encoding='utf-8',newline='\n')
plan=json.loads((HERE/'common_slice_plan_02.json').read_bytes())
plan.update(package_manifest_sha256=pin,pre_review_draft_sha256=sha256(old).hexdigest(),
    test_file_count=len(tests['files_sha256']),monitor='run_bounded_configured_entry_v4.py',
    monitor_sha256=sha256((P/'run_bounded_configured_entry_v4.py').read_bytes()).hexdigest(),
    static_identity_cache_installed=False,
    identity_policy='Bootstrap/solver originals retained with full bookends; refuse all nine selector factory identity-cache assignments before original-source aliases are defined',
    unit_check=dict(label='unit_checks_03',count=1,wall_seconds=120,sampled_rss_mib=512,new_artifact_mib=64),
    exact_diagnostic_role=['pytest','parse_path','common_slice_01','tests/test_h1_guarded_common_slice_development_v1.py'],
    shared_scientific_fields=['phase_manifest_candidate','canonical_arm','canonical_source_binding',
        'common_scientific_payload','common_scientific_identity'],
    per_arm_equal_fields='all old arm audit fields except verification_execution; exact_current_audit compared through full predecessor_compatibility.payload',
    intentional_differences=['successor schema/implementation identities','separate actual execution receipts'],
    cleanup_scope='repeat discovery/kill/wait for observed PID plus creation-time descendants; exact direct-child Popen handle fallback; original synthetic N0 Job observations independently checked',
    storage_policy='full terminal scan plus exact terminal own bytes; errors/overflow fail closed; no sampling-only success',
    wall_scope='monitor CLI through source snapshots, child monitoring and postcheck; bounded cleanup may add up to eight seconds',
    replaced_pre_review_findings=['F1 static identity caches','F2 incomplete process cleanup','F3 final storage','F4 exact argv and comparison wording'])
plan.update(short_basetemp='D:/h1_cs01_non_authoritative',storage_roots=3,heartbeat='faulthandler stack sample every60s; stage timing JSONL',initial_import_guard='four selector/Handoff/helper modules must be absent before any fixture setup',monitor_helper_tests='slice_monitor_unit_04:14 passed',scope_of_absence='observed PID set only; any discovery error fails and complete-tree absence is not claimed')
with (HERE/'common_slice_plan_03.json').open('x',encoding='utf-8') as stream:json.dump(plan,stream,indent=2)
print(json.dumps(dict(package_manifest_sha256=pin,members=len(members),test_files=len(tests['files_sha256']))))
