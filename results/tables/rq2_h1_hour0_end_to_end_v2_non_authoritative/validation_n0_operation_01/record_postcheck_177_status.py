"""Time-stamped handoff for saved174 replay; preserve prior status snapshots."""
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import psutil

H=Path(__file__).resolve().parent;R=H.parents[3];D=H/'whole_workflow_optimization_01_non_authoritative'
started=json.loads((H/'saved174_readonly_reopen_177/started.json').read_bytes())
proc=psutil.Process(started['pid']);assert abs(proc.create_time()-started['creation_time'])<1e-6
assert 'test_h1_retained_n0_readonly_reopen_development_v6.py' in ' '.join(proc.cmdline())
value=dict(schema='h1_saved174_reopen_active_status_177',at_utc=datetime.now(timezone.utc).isoformat(),
    observed_process=dict(pid=proc.pid,creation_time=proc.create_time()),
    producer_actual_public_return_and_close=True,original_numerical_oracle=True,reopen_complete=False,
    producer_exact_plan_invocation_metadata_matched=False,
    producer_result_sha256=sha256((D/'bootstrap6_retained_n0_bounded_result_174.json').read_bytes()).hexdigest(),
    oracle_result_sha256=sha256((D/'saved174_postcheck_result_176.json').read_bytes()).hexdigest(),
    producer_plan_exception_sha256=sha256((D/'bootstrap6_plan_metadata_mismatch_175.json').read_bytes()).hexdigest(),
    new_Jobs=0,native_calls=0,formal_result=False,formal_run_authority=False,resource_admission=False)
out=D/'saved174_reopen_active_status_177.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
stamp=datetime.now().strftime('%Y-%m-%d %H:%M')
text=(f'{stamp} 运行更新：174实际Bootstrap6单N0 public return/receipt/owner close已通过，exit0/1passed351.02s/outer356.813s。\n'
    '原Job exit0/quiescent50.453s，8retention/4full28fresh64contexts/17phase段关闭，pending0/1380pins无漂移/10locks可重取。\n'
    '175明确保留plan中的旧v5 module与旧136 header引用，exact_planned_invocation_metadata_matched=false；原plan/result不改、不重跑Job。\n'
    '176保存174数据的原数值oracle通过80.01s/outer86.578s，1542pins及154保存文件名/bytes不变，新增Job/native=0。\n'
    f'177真实Bootstrap6数值consumer只读重开正在运行，观察PID{proc.pid}，固定240s预算；尚无reopen终态。\n'
    'v4测试failure-secondary repr保护仍有限，成功174未走该分支；后继test修复待做。Roster5/完整优化整链和正式实验未验收。\n\n')
documents=(H/'continuation_handoff_20261018.md',H/'performance_report.md',R/'docs/model_spec/blocker_register.md',
    R/'docs/plan/科研项目执行步骤.md',R/'docs/plan/H1_端到端里程碑验收_v1.md')
plan=json.loads((D/'saved174_postcheck_plan_177.json').read_bytes())
assert all(str(path) not in plan['files_sha256'] for path in documents)
for path in documents:
    raw=path.read_text(encoding='utf-8');first,rest=raw.split('\n',1)
    path.write_text(first+'\n\n'+text+rest.lstrip('\n'),encoding='utf-8',newline='\n')
print(json.dumps(dict(path=str(out),pid=proc.pid,sha256=sha256(out.read_bytes()).hexdigest())))
