"""One bounded target-length component diagnostic, retaining every outcome."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import psutil

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
label = sys.argv[1]
if not label.replace('_','').isalnum():
    raise ValueError('fresh diagnostic label required')
out = HERE / label
base = Path('D:/') / ('h1_target_business_cost_'+label+'_non_authoritative')
if out.exists() or base.exists():
    raise ValueError('all diagnostic roots must be fresh')
out.mkdir()
prior = REPO / 'results/tables/rq2_h1_cross_hour_outage_v1_non_authoritative/connected_03/request.json'
pins = json.loads(prior.read_bytes())['sources_sha256']
assert all(sha256(Path(name).read_bytes()).hexdigest() == expected for name, expected in pins.items())
latest = HERE.parent / 'rq2_h1_constructor_window_fault_v1_non_authoritative/final_verification.json'
assert sha256(latest.read_bytes()).hexdigest() == '925f9370ad00f72d8cb0a3af7abdca26dcb8eb168f346ba9ac24b763232fcb20'
receipt = json.loads(latest.read_bytes())
assert all(sha256(Path(name).read_bytes()).hexdigest() == expected for name, expected in receipt['bindings'].items())
old_fact = HERE.parent / 'rq2_h1_phase_boundary_v1_non_authoritative/unit_04/facts/exact_due_192.json'
assert sha256(old_fact.read_bytes()).hexdigest() == '482ef4cbb986dad4818ed4bc3e7d90ee9b7cee56cbe94df4d59f0ca58e3c6c0d'
sources = [Path(__file__), HERE / 'workload_v1.py', HERE / 'design_and_budget.md', latest, old_fact,
    REPO / 'experiments/h1_exact_business_development_v1.py',
    REPO / 'experiments/h1_phase_obligation_controller_development_v1.py',
    REPO / 'tests/test_h1_exact_business_development_v1.py',
    REPO / 'tests/test_rq2_bidirectional_policy_v1.py',
    REPO / 'tests/test_rq2_continuous_recovery_controller_v1.py',
    REPO / 'tests/test_rq2_normal_h1_hour_archive_v1.py',
    REPO / 'configs/rq2_bidirectional_capacity_policy_v1.DRAFT.yaml',
    REPO / 'configs/rq2_continuous_causal_policy_v1.DRAFT.yaml',
    REPO / 'configs/rq2_finite_mechanism_protocol_candidate_v2.DRAFT.yaml']
for path in sources:
    raw = path.read_bytes()
    pins[str(path)] = sha256(raw).hexdigest()
    target = out / 'tested_bytes' / path.relative_to(REPO)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
command = [sys.executable, '-u','-B','-m','pytest','-q','-s','-p','no:cacheprovider',
    '-p','no:faulthandler','--basetemp',str(base),'--junitxml',str(out / 'junit.xml'),str(HERE / 'workload_v1.py')]


def save(name, value):
    with (out / name).open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2)
        stream.write('\n')


save('request.json',dict(command=command, sources_sha256=pins, base=str(base),
    wall_cap_seconds=90, no_worker_progress_cap_seconds=30,
    sampled_tree_rss_cap_bytes=512*1024**2, logical_storage_cap_bytes=32*1024**2,
    sample_seconds=2, detached_histories=1, business_hours=192, target_validations=2,
    repetitions_per_target=1, native_authorized=False, new_normal_jobs_authorized=False,
    reused_constructor_final_sha256=sha256(latest.read_bytes()).hexdigest(),
    reused_old_exact_due_fact_sha256=sha256(old_fact.read_bytes()).hexdigest(),
    scope='one_anchor_business_history_H168_H192_validator_and_encoding_cost', formal_result=False))
started=time.monotonic()
owned={}; images={}; cleanup=[]; peak_rss=peak_disk=0
reason=None; process=None; result={}; next_heartbeat=0
last_progress=started; progress_stamp=0
console=os.path.normcase(str(Path(os.environ['SystemRoot'])/'System32/conhost.exe'))


def live():
    values=[]
    for pid,created in tuple(owned.items()):
        try:
            item=psutil.Process(pid)
            if item.create_time()==created and item.is_running():values.append(item)
        except psutil.NoSuchProcess:pass
    return values


def disk(root):
    return sum(p.stat().st_size for p in root.rglob('*') if p.is_file()) if root.exists() else 0


try:
    with (out/'stdout.txt').open('wb') as stdout,(out/'stderr.txt').open('wb') as stderr:
        process=subprocess.Popen(command,cwd=REPO,stdout=stdout,stderr=stderr,
            env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'),
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        owned[process.pid]=psutil.Process(process.pid).create_time()
        while True:
            for item in live():
                for child in item.children(recursive=True):owned[child.pid]=child.create_time()
            rss=cpu=0; unexpected=[]
            for item in live():
                try:
                    rss+=item.memory_info().rss
                    t=item.cpu_times();cpu+=t.user+t.system
                    executable,parent=item.exe(),item.ppid()
                    images[str(item.pid)]=dict(executable=executable,parent_pid=parent,
                        create_time=item.create_time(),command=item.cmdline())
                    if item.pid!=process.pid and (os.path.normcase(executable)!=console or parent!=process.pid):
                        unexpected.append(item.pid)
                except psutil.NoSuchProcess:pass
            size=disk(out)+disk(base);now=time.monotonic();elapsed=now-started
            peak_rss,peak_disk=max(peak_rss,rss),max(peak_disk,size)
            progress=max((p.stat().st_mtime_ns for p in base.rglob('progress.json')),default=0) if base.exists() else 0
            if progress!=progress_stamp:progress_stamp,last_progress=progress,now
            row=dict(elapsed_seconds=elapsed,no_worker_progress_seconds=now-last_progress,
                rss_bytes=rss,logical_bytes=size,cpu_seconds=cpu)
            with (out/'monitor.jsonl').open('a',encoding='utf-8') as stream:stream.write(json.dumps(row)+'\n')
            if elapsed>=next_heartbeat:
                print(json.dumps(row),flush=True);next_heartbeat=elapsed+30
            reason=('wall_limit' if elapsed>90 else 'no_worker_progress_limit' if now-last_progress>30 else
                'rss_limit' if rss>512*1024**2 else 'storage_limit' if size>32*1024**2 else
                'unexpected_child_process' if unexpected else None)
            if reason or process.poll() is not None:break
            time.sleep(2)
        if reason:
            for item in reversed(live()):
                item.kill();cleanup.append(dict(pid=item.pid,action='kill_owned',reason=reason))
        process.wait(timeout=10)
        result['exit_code']=process.returncode
        root=ET.parse(out/'junit.xml').getroot()
        suites=list(root.iter('testsuite'))
        junit={key:sum(int(s.get(key,0)) for s in suites) for key in ('tests','failures','errors','skipped')}
        junit['accepted']=junit==dict(tests=1,failures=0,errors=0,skipped=0)
        result['junit']=junit
        facts=list(base.rglob('fact.json'))
        assert len(facts)==1
        result['fact']=json.loads(facts[0].read_bytes())
        retained={}
        for path in base.rglob('*.json'):
            raw=path.read_bytes();target=out/'base_artifacts'/path.relative_to(base)
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
            retained[str(path)]=dict(copy=str(target),sha256=sha256(raw).hexdigest())
        result['retained_base_json']=retained
except BaseException as error:result['error']=repr(error)
finally:
    for item in reversed(live()):
        try:item.kill();cleanup.append(dict(pid=item.pid,action='kill_owned_tail'))
        except psutil.NoSuchProcess:pass
    psutil.wait_procs(live(),timeout=5)
    changed=[name for name,expected in pins.items() if sha256(Path(name).read_bytes()).hexdigest()!=expected]
    final_size=disk(out)+disk(base)
    peak_disk=max(peak_disk,final_size)
    if reason is None and final_size>32*1024**2:reason='storage_limit_after_retention'
    result.update(reason=reason,outer_seconds=time.monotonic()-started,
        peak_sampled_tree_rss_bytes=peak_rss,peak_logical_bytes=peak_disk,
        final_logical_bytes=final_size,source_pins=len(pins),changed_sources=changed,
        observed_processes=owned,observed_images=images,observed_processes_remaining=[p.pid for p in live()],
        cleanup_events=cleanup,complete_unobserved_process_tree_proof=False,
        new_normal_jobs=0,real_native_calls=0,formal_result=False)
    save('terminal.json',result)
    print(json.dumps(dict(exit_code=result.get('exit_code'),junit=result.get('junit'),reason=reason,
        error=result.get('error'),outer_seconds=result['outer_seconds'],peak_rss_bytes=peak_rss,
        peak_logical_bytes=peak_disk,changed_sources=changed,remaining=result['observed_processes_remaining'])),flush=True)
sys.exit(0 if result.get('exit_code')==0 and result.get('junit',{}).get('accepted') and not reason
    and not result.get('error') and not changed and not result['observed_processes_remaining'] else 1)
