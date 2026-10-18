"""One fixed saved diagnostic, including failure/kill postchecks; no formal authority."""
from hashlib import sha256
import json
import msvcrt
from pathlib import Path
import subprocess
import sys
import time
import traceback

import psutil

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
SAVED=Path('D:/h1_chain_06_non_authoritative')
PACKAGE=HERE.parent/'validation_path_optimization_01/entry_revision_03'
mode,label,manifest_pin=sys.argv[1:]
if mode not in ('full_only','operation') or not label.startswith(mode+'_') or not label.replace('_','').isalnum():
    raise ValueError('fixed mode and unique mode-prefixed label required')
out=HERE/label;out.mkdir(exist_ok=False)
command=[sys.executable,'-I','-B',str(HERE/'measure_saved_v1.py'),mode,str(out/'attempt_non_authoritative'),manifest_pin]
limit,ram,storage_cap=300.,512*1024**2,64*1024**2
sources={};before={};owned={};events=[];errors=[];peak=storage=0;reason=None;proc=None
result=dict(formal_result=False,resource_admission=False,full_chain_passed=False)
start=time.monotonic()


def save(name,value):
    with (out/name).open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)


def pins(paths):return {str(p):sha256(p.read_bytes()).hexdigest() for p in paths}


def live(pid,created):
    try:
        p=psutil.Process(pid)
        return p if p.create_time()==created and p.is_running() else None
    except psutil.Error:return None


def observe():
    for pid,created in tuple(owned.items()):
        p=live(pid,created)
        if p is None:continue
        try:
            for child in p.children(recursive=True):owned[child.pid]=child.create_time()
        except psutil.Error:pass
    return [p for pid,created in tuple(owned.items()) if (p:=live(pid,created)) is not None]


def finish_children():
    deadline=time.monotonic()+8
    while True:
        active=observe()
        if not active:break
        for p in active:
            try:p.kill();events.append(dict(pid=p.pid,creation_time=owned[p.pid],action='kill_owned'))
            except psutil.NoSuchProcess:pass
            except psutil.Error as error:errors.append(dict(stage='kill',error=repr(error),pid=p.pid))
        psutil.wait_procs(active,timeout=min(0.5,max(0,deadline-time.monotonic())))
        if time.monotonic()>=deadline:break
    remaining=[dict(pid=p.pid,creation_time=owned[p.pid]) for p in observe()]
    result.update(observed_owned_processes=[dict(pid=p,creation_time=c) for p,c in owned.items()],
        observed_owned_processes_remaining=remaining,observed_owned_processes_absent=not remaining,
        process_cleanup_scope='PID plus creation time; repeated observed-descendant discovery',cleanup_events=events)
    if remaining:result['exit_code']=1


def lock_postcheck():
    rows=[]
    for path in sorted(SAVED.rglob('*.lock')):
        with path.open('r+b',buffering=0) as stream:
            stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
            try:rows.append(str(path))
            finally:stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
    if not rows:raise ValueError('saved execution lock inventory missing')
    return dict(all_reacquired_and_released=True,paths=rows,files=len(rows))


try:
    diagnostic_path=HERE/'diagnostic_source_manifest_v1.json'
    diagnostic_raw=diagnostic_path.read_bytes()
    if sha256(diagnostic_raw).hexdigest()!=manifest_pin:raise ValueError('fixed diagnostic manifest differs')
    diagnostic=json.loads(diagnostic_raw)
    required={'experiments/h1_operation_historical_witness_development_v1.py':
        '8b91c8184dc934c90f324705bb05104128245594a677a7fcdf1a13daa04a7e6a',
        'tests/test_h1_operation_historical_witness_development_v1.py':
        'd6a0a9413ef43ced30f647be32747147f733a5854ede8b88e332b9c09c159b32'}
    if any(diagnostic['files_sha256'].get(name)!=h for name,h in required.items()):
        raise ValueError('diagnostic candidate is not the unit_06 validated helper/test')
    for name,h in diagnostic['files_sha256'].items():
        path=REPO/name
        if Path(name).is_absolute() or '..' in Path(name).parts or not path.is_relative_to(REPO):
            raise ValueError('relative diagnostic member required')
        if sha256(path.read_bytes()).hexdigest()!=h:raise ValueError('fixed diagnostic member differs: '+name)
        sources[str(path)]=h
    sources[str(diagnostic_path)]=manifest_pin
    manifest=(PACKAGE/'package_manifest_v1.json').read_bytes()
    if sha256(manifest).hexdigest()!='e5a7893d2b88812e46c8000463f8e03ba4195ac6ac189b41e68d3af43922d139':
        raise ValueError('fixed configured package differs')
    members=json.loads(manifest)['files_sha256']
    sources.update({str(PACKAGE/name):h for name,h in members.items()})
    sources[str(PACKAGE/'package_manifest_v1.json')]=sha256(manifest).hexdigest()
    sources.update(json.loads((PACKAGE/'code_allowlist_v3.json').read_bytes())['files_sha256'])
    sources.update({str(REPO/p):h for p,h in json.loads((PACKAGE/'test_closure_v1.json').read_bytes())['files_sha256'].items()})
    sources.update(pins((Path(__file__).resolve(),HERE/'measure_saved_v1.py',
        REPO/'experiments/h1_operation_historical_witness_development_v1.py',
        REPO/'tests/test_h1_operation_historical_witness_development_v1.py',
        REPO/'tests/test_h1_operation_saved_diagnostic_monitor_v1.py')))
    if pins(map(Path,sources))!=sources:raise ValueError('source/test/package pin differs before launch')
    before=pins(p for p in SAVED.rglob('*') if p.is_file())
    if not before:raise ValueError('saved input inventory missing')
    for name in sources:
        path=Path(name);target=out/'tested_bytes'/path.relative_to(REPO)
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(path.read_bytes())
    save('request.json',dict(command=command,wall_seconds=limit,sampled_rss_cap_bytes=ram,
        new_artifact_cap_bytes=storage_cap,storage_roots=[str(out)],source_sha256=sources,
        saved_sha256=before,diagnostic_manifest_sha256=manifest_pin,formal_result=False,resource_admission=False))
    with (out/'stdout.log').open('x',encoding='utf-8') as stream:
        proc=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT)
        process=psutil.Process(proc.pid);owned[proc.pid]=process.create_time()
        save('started.json',dict(pid=proc.pid,creation_time=owned[proc.pid]))
        deadline=time.monotonic()+limit;next_storage=0
        while proc.poll() is None:
            active=observe();rss=0
            for p in active:
                try:rss+=p.memory_info().rss
                except psutil.Error:pass
            peak=max(peak,rss);now=time.monotonic()
            if now>=next_storage:
                storage=sum(p.stat().st_size for p in out.rglob('*') if p.is_file());next_storage=now+1
            if now>deadline or rss>ram or storage>storage_cap:
                reason='wall' if now>deadline else 'rss' if rss>ram else 'storage'
                finish_children();break
            time.sleep(0.1)
        result['exit_code']=proc.wait(timeout=10)
except BaseException:
    result.update(exit_code=1,error=traceback.format_exc())
finally:
    for stage,operation in (
        ('process_cleanup',finish_children),
        ('saved_postcheck',lambda:result.update(saved_unchanged=bool(before) and pins(
            p for p in SAVED.rglob('*') if p.is_file())==before,saved_file_count=len(before))),
        ('source_postcheck',lambda:result.update(source_unchanged=bool(sources) and pins(map(Path,sources))==sources)),
        ('lock_postcheck',lambda:result.update(saved_locks=lock_postcheck())),
    ):
        try:operation()
        except BaseException:errors.append(dict(stage=stage,error=traceback.format_exc()))
    if proc is not None:
        try:result['child_exit_code']=proc.wait(timeout=1)
        except BaseException:errors.append(dict(stage='child_wait',error=traceback.format_exc()))
    try:
        inner=json.loads((out/'attempt_non_authoritative/terminal.json').read_bytes())
        result['inner_terminal_sha256']=sha256((out/'attempt_non_authoritative/terminal.json').read_bytes()).hexdigest()
        result['inner_exit_code']=inner['exit_code']
    except BaseException:
        errors.append(dict(stage='inner_terminal',error=traceback.format_exc()))
    try:storage=sum(p.stat().st_size for p in out.rglob('*') if p.is_file())
    except BaseException:errors.append(dict(stage='final_storage',error=traceback.format_exc()))
    if (errors or reason is not None or not result.get('saved_unchanged') or not result.get('source_unchanged')
            or not result.get('observed_owned_processes_absent') or result.get('inner_exit_code')!=0
            or result.get('child_exit_code')!=0 or storage>storage_cap):result['exit_code']=1
    result.update(elapsed_seconds=time.monotonic()-start,stop_reason=reason,errors=errors,
        peak_observed_process_tree_rss=peak,observed_new_artifact_bytes=storage,memory_is_sampled=True)
    try:save('terminal.json',result)
    except BaseException:result.update(exit_code=1,terminal_write_error=traceback.format_exc())
    print(json.dumps(result),flush=True)
sys.exit(0 if result.get('exit_code')==0 else 1)
