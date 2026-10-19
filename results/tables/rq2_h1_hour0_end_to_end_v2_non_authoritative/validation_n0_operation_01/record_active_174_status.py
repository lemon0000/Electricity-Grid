"""Time-stamped active diagnostic handoff; does not modify its frozen sources."""
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import psutil

H=Path(__file__).resolve().parent;R=H.parents[3];D=H/'whole_workflow_optimization_01_non_authoritative'
started=H/'bootstrap6_retained_n0_174/started.json';s=json.loads(started.read_bytes())
process=psutil.Process(s['pid']);assert abs(process.create_time()-s['creation_time'])<1e-6
assert 'test_h1_registry_validation_retained_n0_development_v4.py' in ' '.join(process.cmdline())
observer=process.parent();assert 'run_unit_bounded_v19.py' in ' '.join(observer.cmdline())
stamp=datetime.now().strftime('%Y-%m-%d %H:%M')
value=dict(schema='h1_active_bootstrap6_diagnostic_174',observed_at_utc=datetime.now(timezone.utc).isoformat(),
    process=dict(pid=process.pid,creation_time=process.create_time()),observer=dict(pid=observer.pid,creation_time=observer.create_time()),
    plan_sha256=sha256((D/'bootstrap6_retained_n0_bounded_plan_174.json').read_bytes()).hexdigest(),
    named_pre_seal_findings_sha256=sha256((D/'consumer_scoped_findings_173.json').read_bytes()).hexdigest(),
    state='RUNNING_NONAUTHORITATIVE_SYNTHETIC_DIAGNOSTIC',wall_cap_seconds=400,
    new_Job_limit=1,simulated_hour_limit=1,native_call_limit=0,
    completion_observed=False,public_return_verified=False,formal_result=False,formal_run_authority=False,resource_admission=False)
out=D/'active_bootstrap6_diagnostic_status_174.json'
with out.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
text=(f'{stamp} 运行更新：173独立定向PRE_SEAL findings已闭合（非official verdict/receipt）。\n'
    f'174新版本单N0合成诊断正在运行：观察PID{process.pid}、monitor PID{observer.pid}，固定400s/RSS1GiB/存储128MiB。\n'
    '仅1模拟小时/最多1合成Job/0native；当前尚无public return或完整关闭终态，不能当作成功。\n'
    '源码/测试/入口保持运行字节，retention在callback确认前落盘；终态后补保存数据oracle/reopen，不重复Job。\n'
    '旧152原public return/cleanup仍false，优化整链及正式实验仍未验收。见active_bootstrap6_diagnostic_status_174.json。\n\n')
documents=(H/'continuation_handoff_20261018.md',H/'performance_report.md',R/'docs/model_spec/blocker_register.md',
    R/'docs/plan/科研项目执行步骤.md',R/'docs/plan/H1_端到端里程碑验收_v1.md')
plan=json.loads((D/'bootstrap6_retained_n0_bounded_plan_174.json').read_bytes())
assert all(str(path) not in plan['files_sha256'] for path in documents)
for path in documents:
    raw=path.read_text(encoding='utf-8');first,rest=raw.split('\n',1)
    path.write_text(first+'\n\n'+text+rest.lstrip('\n'),encoding='utf-8',newline='\n')
print(json.dumps(dict(active=str(out),pid=process.pid,observer=observer.pid,sha256=sha256(out.read_bytes()).hexdigest())))
