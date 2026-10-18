"""One admission wrapper: bind the exact input postcheck before the old monitor."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import time
import traceback
import psutil
import sys

HERE=Path(__file__).resolve().parent
plan_pin,pre_pin,wrapper_pin=sys.argv[1:]
if sha256(Path(__file__).read_bytes()).hexdigest()!=wrapper_pin:raise ValueError('exact bounded wrapper bytes required')
raw=(HERE/'source_reader_input_postcheck_plan_01.json').read_bytes()
if sha256(raw).hexdigest()!=plan_pin:raise ValueError('fixed additive plan differs')
plan=json.loads(raw)
for name,pin in plan['implementation_sha256'].items():
    if sha256(Path(name).read_bytes()).hexdigest()!=pin:raise ValueError('fixed wrapper or diagnostic differs')
pre_raw=(HERE/'source_reader_input_postcheck_01_baseline_non_authoritative/terminal.json').read_bytes()
pre=json.loads(pre_raw)
if (sha256(pre_raw).hexdigest()!=pre_pin or pre['exit_code']!=0 or pre['phase']!='baseline'
        or pre['plan_sha256']!=plan_pin or pre['relative_files_sha256']!=plan['relative_files_sha256']
        or pre['regular_input_files']!=134 or pre['locked_and_released']!=plan['relative_locks']):
    raise ValueError('exact successful pre-candidate input check required')
out=HERE/'candidate_after_input_postcheck_02_non_authoritative';out.mkdir(exist_ok=False)
command=[sys.executable,'-B',str(HERE/'run_fresh_source_reader_bounded_v1.py'),'candidate',plan['candidate_plan_sha256']]
with (out/'request.json').open('x',encoding='utf-8') as stream:
    json.dump(dict(plan_sha256=plan_pin,pre_input_postcheck_sha256=pre_pin,wrapper_sha256=wrapper_pin,
        hard_wall_seconds=150,command=command,formal_result=False,resource_admission=False),stream,indent=2)
proc=None;identity=None;owned={};errors=[];reason=None;start=time.monotonic();status=1
try:
    proc=subprocess.Popen(command,cwd=HERE.parents[3])
    identity=psutil.Process(proc.pid).create_time();owned[proc.pid]=identity
    with (out/'started.json').open('x',encoding='utf-8') as stream:
        json.dump(dict(pid=proc.pid,creation_time=identity),stream)
    try:status=proc.wait(timeout=150)
    except subprocess.TimeoutExpired:reason='wrapper_wall';status=1
except BaseException:errors.append(traceback.format_exc())
finally:
    if proc is not None and proc.poll() is None:
        try:
            current=psutil.Process(proc.pid)
            if identity is not None and current.create_time()==identity:
                for child in current.children(recursive=True):owned[child.pid]=child.create_time()
        except psutil.NoSuchProcess:pass
        except psutil.Error as error:errors.append(repr(error))
        for pid,created in reversed(tuple(owned.items())):
            try:
                current=psutil.Process(pid)
                if current.create_time()==created:current.kill()
            except psutil.NoSuchProcess:pass
            except psutil.Error as error:errors.append(repr(error))
        try:
            if proc.poll() is None:proc.kill()
            proc.wait(timeout=10)
        except BaseException:errors.append(traceback.format_exc())
    remaining=[]
    for pid,created in owned.items():
        try:
            if psutil.Process(pid).create_time()==created:remaining.append(dict(pid=pid,creation_time=created))
        except psutil.NoSuchProcess:pass
        except psutil.Error as error:errors.append(repr(error))
    result=dict(exit_code=status if not errors and reason is None and not remaining else 1,
        pre_input_postcheck_sha256=pre_pin,wrapper_sha256=wrapper_pin,
        elapsed_seconds=time.monotonic()-start,stop_reason=reason,errors=errors,
        observed_owned_processes=[dict(pid=p,creation_time=c) for p,c in owned.items()],
        observed_owned_processes_remaining=remaining,formal_result=False,resource_admission=False)
    for name in ('request.json','terminal.json'):
        path=Path(plan['candidate_monitor'])/name
        if path.is_file():result['candidate_'+name.replace('.json','')+'_sha256']=sha256(path.read_bytes()).hexdigest()
    with (out/'terminal.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps(result),flush=True)
raise SystemExit(result['exit_code'])
