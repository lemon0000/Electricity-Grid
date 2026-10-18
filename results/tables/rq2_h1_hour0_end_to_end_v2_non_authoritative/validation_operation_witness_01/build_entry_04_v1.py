"""Copy checked entry03 bytes; change only declared site-root order and package binding."""
from hashlib import sha256
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
P=HERE.parent/'validation_path_optimization_01'
prior=P/'entry_revision_03';target=P/'entry_revision_04'
raw=(prior/'package_manifest_v1.json').read_bytes()
if sha256(raw).hexdigest()!='e5a7893d2b88812e46c8000463f8e03ba4195ac6ac189b41e68d3af43922d139':
    raise ValueError('checked entry03 manifest differs')
members=json.loads(raw)['files_sha256']
for name,h in members.items():
    if sha256((prior/name).read_bytes()).hexdigest()!=h:raise ValueError('checked entry03 member differs')
if (prior/'launch_validation.py').read_bytes()!=(prior/'unit_checks_07/tested_bytes/launch_validation.py').read_bytes():
    raise ValueError('checked entry03 launcher differs')
target.mkdir(exist_ok=False)
for name in (*members,'launch_validation.py'):(target/name).write_bytes((prior/name).read_bytes())
(target/'configured_predecessor_package_manifest.json').write_bytes(raw)
policy_path=target/'interpreter_path_policy_v1.json';policy=json.loads(policy_path.read_bytes())
paths=policy['configured_paths']
if not paths[-2].startswith('C:') or not paths[-1].startswith('D:'):raise ValueError('fixed last-two roots differ')
paths[-2],paths[-1]=paths[-1],paths[-2]
policy_path.write_text(json.dumps(policy,indent=2)+'\n',encoding='utf-8',newline='\n')
new_members={p.name:sha256(p.read_bytes()).hexdigest() for p in sorted(target.iterdir())
    if p.is_file() and p.name!='launch_validation.py'}
manifest=dict(schema='h1_configured_validation_package_development_v1',files_sha256=new_members,
    formal_result=False,formal_execution_ready=False,native_execution_authorized=False)
new_raw=(json.dumps(manifest,indent=2)+'\n').encode();new_pin=sha256(new_raw).hexdigest()
(target/'package_manifest_v1.json').write_bytes(new_raw)
launcher=target/'launch_validation.py'
text,count=re.subn(r"MANIFEST_SHA='[0-9a-f]{64}'","MANIFEST_SHA='"+new_pin+"'",launcher.read_text(encoding='utf-8'))
if count!=1:raise ValueError('fixed launcher manifest binding missing')
launcher.write_text(text,encoding='utf-8',newline='\n')
monitor=P/'run_bounded_configured_entry_v1.py'
text=monitor.read_text(encoding='utf-8')
if text.count("entry_revision_03")!=1:raise ValueError('fixed monitor entry anchor differs')
with (P/'run_bounded_configured_entry_v2.py').open('x',encoding='utf-8') as stream:
    stream.write(text.replace('entry_revision_03','entry_revision_04'))
plan=dict(schema='h1_entry04_path_order_plan_development_v1',package_manifest_sha256=new_pin,
    changed_runtime_data='configured_paths last two roots only; D site-packages precedes C support',
    code_members_unchanged=True,predecessor_package_sha256=sha256(raw).hexdigest(),
    prior_raw_comparison_sha256=sha256((HERE/'path_order_comparison_01.json').read_bytes()).hexdigest(),
    checks=['original package unit suite','original twelve routing integration tests'],
    each_budget=dict(wall_seconds=120,sampled_rss_mib=512,new_artifact_mib=64),attempts_per_check=1,
    full_chain_passed=False,whole_workflow_performance_review_complete=False,long_chain_launch_admitted=False,
    formal_result=False,resource_admission=False,native_execution_authorized=False)
with (HERE/'entry04_plan_01.json').open('x',encoding='utf-8') as stream:json.dump(plan,stream,indent=2)
print(json.dumps(dict(package_manifest_sha256=new_pin,members=len(new_members))))
