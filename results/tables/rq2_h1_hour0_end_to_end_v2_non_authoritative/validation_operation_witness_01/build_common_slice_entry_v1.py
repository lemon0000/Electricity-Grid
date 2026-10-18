"""Fresh diagnostic package; preserve every checked predecessor package byte."""
from hashlib import sha256
import json
import os
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3];P=HERE.parent/'validation_path_optimization_01'
prior=P/'entry_revision_04';target=P/'entry_revision_05'
raw=(prior/'package_manifest_v1.json').read_bytes()
if sha256(raw).hexdigest()!='d13a08fe6db35e9c5c70b8204e3fb4d0091e43a3ef483e3951a561eac0667e43':
    raise ValueError('checked predecessor package differs')
members=json.loads(raw)['files_sha256']
for name,pin in members.items():
    if sha256((prior/name).read_bytes()).hexdigest()!=pin:raise ValueError('predecessor member differs')
target.mkdir(exist_ok=False)
for name in (*members,'launch_validation.py'):(target/name).write_bytes((prior/name).read_bytes())
(target/'entry04_predecessor_package_manifest.json').write_bytes(raw)

code_path=target/'code_allowlist_v3.json';code=json.loads(code_path.read_bytes())
for name in ('h1_common_validation_operation_development_v1',
        'h1_operation_historical_witness_development_v2','h1_phase_exact_source_current_development_v3',
        'h1_group_n0_common_input_binding_development_v3'):
    path=REPO/'experiments'/(name+'.py')
    code['files_sha256'][os.path.normcase(str(path))]=sha256(path.read_bytes()).hexdigest()
code_path.write_text(json.dumps(code,indent=2)+'\n',encoding='utf-8',newline='\n')
tests_path=target/'test_closure_v1.json';tests=json.loads(tests_path.read_bytes())
for name in ('h1_guarded_common_slice_helpers_development_v1','test_h1_guarded_common_slice_development_v1',
        'test_h1_group_operation_witness_development_v2','test_h1_common_validation_operation_development_v1',
        'test_h1_operation_exact_source_composition_development_v3'):
    path=REPO/'tests'/(name+'.py')
    tests['files_sha256'][path.relative_to(REPO).as_posix()]=sha256(path.read_bytes()).hexdigest()
tests_path.write_text(json.dumps(tests,indent=2)+'\n',encoding='utf-8',newline='\n')
entry_path=target/'validation_entry.py';entry=entry_path.read_text(encoding='utf-8')
anchor="    allowed={\n"
if entry.count(anchor)!=1:raise ValueError('fixed synthetic target allowlist anchor differs')
entry=entry.replace(anchor,anchor+"        'tests/test_h1_guarded_common_slice_development_v1.py',\n")
entry_path.write_text(entry,encoding='utf-8',newline='\n')
new_members={p.name:sha256(p.read_bytes()).hexdigest() for p in sorted(target.iterdir())
    if p.is_file() and p.name!='launch_validation.py'}
manifest=dict(schema='h1_configured_validation_package_development_v1',files_sha256=new_members,
    formal_result=False,formal_execution_ready=False,native_execution_authorized=False)
new_raw=(json.dumps(manifest,indent=2)+'\n').encode();new_pin=sha256(new_raw).hexdigest()
(target/'package_manifest_v1.json').write_bytes(new_raw)
launcher=target/'launch_validation.py'
text,count=re.subn(r"MANIFEST_SHA='[0-9a-f]{64}'","MANIFEST_SHA='"+new_pin+"'",launcher.read_text(encoding='utf-8'))
if count!=1:raise ValueError('fixed launcher manifest anchor differs')
launcher.write_text(text,encoding='utf-8',newline='\n')
monitor=(P/'run_bounded_configured_entry_v2.py').read_text(encoding='utf-8')
if monitor.count('entry_revision_04')!=1:raise ValueError('fixed bounded monitor anchor differs')
with (P/'run_bounded_configured_entry_v3.py').open('x',encoding='utf-8') as stream:
    stream.write(monitor.replace('entry_revision_04','entry_revision_05'))
plan=dict(schema='h1_fresh_guarded_common_slice_diagnostic_plan_v1',status='DRAFT_NONAUTHORITATIVE',
    question='Measure actual fresh three-arm common with live analytic Rref and original-source alias Handoff; compare full first common versus proof-reusing second common',
    package_manifest_sha256=new_pin,predecessor_package_sha256=sha256(raw).hexdigest(),
    changed_package_scope='add fixed four-code and five-test pins; add one zero-native slice test to existing target allowlist; preserve lease/policy/plugin bytes',
    source_file_count=len(code['files_sha256']),test_file_count=len(tests['files_sha256']),
    unit_check=dict(label='unit_checks_01',count=1,wall_seconds=120,sampled_rss_mib=512,new_artifact_mib=64),
    diagnostic=dict(label='common_slice_01',count=1,wall_seconds=600,sampled_process_tree_rss_mib=1024,new_artifact_mib=128),
    maximum_concurrency=1,
    path=['explicit fixture/source setup','3 independent N0 Windows Jobs and roster attachments',
        'CommonOwnerGenesis construction with unchanged internal replays','reference snapshot',
        'fresh live analytic Rref Parent.run and zero-workload oracle','original-source alias Handoff registration',
        'guarded operation/Parent validation','full first common','proof-reusing full second common',
        'compare old full science/compatibility audits and all execution counts','close original resources and retain report'],
    call_counts=dict(new_N0_jobs=3,new_N0_fake_stages=9,new_Rref_fake_stages=3,
        actual_jobs=0,paired_commits=0,common_calls_inside_operation=2,
        historical_prepares_inside_operation=12,full_numerical_inspections_inside_operation=24,
        context_evaluations_inside_operation=192,registry_preparations_inside_operation=24,
        original_genesis_and_setup_nested_call_counts='unchanged; actual cost unknown, bounded by total diagnostic cap'),
    optimizations=['checked CodeReadLease','checked parsed-version metadata lease; stock selection on every lookup',
        'checked canonical path lease','checked D-before-C declared roots',
        'no redundant explicit common.inspect before genesis; no redundant genesis.inspect after successful constructor',
        'no missing-Actual negative consume/Actual/paired/reopen outside this measurement question'],
    unknowns=['fresh setup and genesis time','snapshot and Rref parent time','whole common time',
        'total diagnostic may reach cap before the two common calls; this is an honest stopped diagnostic'],
    stop='Observed wall/RSS/storage cap; kill only owned diagnostic process tree; preserve source snapshots/outputs/terminal; no unchanged retry or extending cap',
    authority_scope='synthetic original-source aliases and real persisted/guard validation; alias identities are not canonical production Handoff identity',
    full_chain_performance_review_complete=False,long_chain_launch_admitted=False,
    formal_execution_ready=False,formal_result=False,resource_admission=False,native_execution_authorized=False)
with (HERE/'common_slice_plan_01.json').open('x',encoding='utf-8') as stream:json.dump(plan,stream,indent=2)
print(json.dumps(dict(package_manifest_sha256=new_pin,members=len(new_members),
    code_files=len(code['files_sha256']),test_files=len(tests['files_sha256']))))
