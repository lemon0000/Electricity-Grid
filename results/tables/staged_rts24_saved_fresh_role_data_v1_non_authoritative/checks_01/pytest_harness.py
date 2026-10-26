"""Ordinary pytest under exact optional-probe denial; never a saved role."""
import json
import os
from pathlib import Path
import sys
import builtins
import ast
from hashlib import sha256

ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
EXE=Path('D:/Miniconda3/envs/compute/python.exe')
OUTPUT_PARENT=ROOT/'results/tables/staged_rts24_saved_fresh_adoption_v1_non_authoritative'
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def read(name):return json.loads((OUT/name).read_bytes())
def save(name,value):
    path=OUT/name;raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
    assert not path.exists() and len(raw)<=1024**2;path.write_bytes(raw)

plan_name,label=sys.argv[1:];collect_only=plan_name=='--collect-only'
nodes=['tests/test_staged_rts24_saved_fresh_adoption_v1.py'] if collect_only else read(plan_name)['groups'][label]
numpy_file=EXE.parent/'Lib/site-packages/numpy/testing/_private/utils.py'
subprocess_file=EXE.parent/'Lib/subprocess.py'
expected={numpy_file:'15a67bea0d5acd4f22d345e44d065512b06d1456639de5c2d100a25276a67b8c',
    subprocess_file:'85d29b2bf0249f5436838298c9a60ee93508b1102e9ac43b001f8a7e7ae8f375'}
assert all(pin(p.read_bytes())['sha256']==sha for p,sha in expected.items())
counts=dict(optional_Popen_attempts=0,blocked_lscpu=0,unexpected_process_attempts=0,native_owner_attempts=0,
    P1_write_attempts=0,actual_F_write_attempts=0)
active=True
def norm(path):return os.path.normcase(os.path.abspath(os.fsdecode(path)))
p1=norm(ROOT/'results/tables/staged_rts24_native_v1_non_authoritative/p1_01')+os.sep
actual=norm(OUTPUT_PARENT)+os.sep
class OptionalProbeBlocked(OSError):pass


def audit(event,args):
    if not active:return
    if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
        target=norm(args[0]);mode,flags=args[1:3]
        write=(type(mode) is str and any(c in mode for c in 'wax+')) or (type(flags) is int and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
        if write and target.startswith(p1):counts['P1_write_attempts']+=1;raise AssertionError('ordinary test attempted P1 write')
        if write and target.startswith(actual):counts['actual_F_write_attempts']+=1;raise AssertionError('ordinary test attempted actual F write')
    mutations={'os.mkdir','os.remove','os.unlink','os.rmdir','os.rename','os.replace','os.link','os.symlink',
        'os.chmod','os.chown','os.utime','os.truncate'}
    if event in mutations:
        paths=args[:2] if event in {'os.rename','os.replace','os.link','os.symlink'} else args[:1]
        for path in paths:
            if isinstance(path,(str,bytes,os.PathLike)):
                target=norm(path)
                if target==p1[:-1] or target.startswith(p1):counts['P1_write_attempts']+=1;raise AssertionError('ordinary test attempted P1 mutation')
                if target==actual[:-1] or target.startswith(actual):counts['actual_F_write_attempts']+=1;raise AssertionError('ordinary test attempted actual F mutation')
    if event=='subprocess.Popen':
        stack=[];frame=sys._getframe(1)
        while frame is not None:
            stack.append((norm(frame.f_code.co_filename),frame.f_code.co_name,frame.f_lineno));frame=frame.f_back
        exact=(norm(numpy_file),'check_support_sve',1247) in stack and (norm(numpy_file),'<module>',1253) in stack \
            and (norm(subprocess_file),'_execute_child',1534) in stack
        if tuple(args)==(None,'lscpu',None,None) and exact and counts['blocked_lscpu']==0:
            counts['optional_Popen_attempts']+=1;counts['blocked_lscpu']+=1
            raise OptionalProbeBlocked('ordinary harness blocks optional CPU probe')
        counts['unexpected_process_attempts']+=1;raise AssertionError('ordinary test requested process launch')
    if event=='os.system' or event.startswith('os.spawn'):
        counts['unexpected_process_attempts']+=1;raise AssertionError('ordinary test requested process launch')


original_import=builtins.__import__;owner_class=None;original_owner_init=None
def denied_owner(*args,**kwargs):
    counts['native_owner_attempts']+=1;raise AssertionError('ordinary test requested native owner')
def guarded_import(*args,**kwargs):
    global owner_class,original_owner_init
    result=original_import(*args,**kwargs)
    if owner_class is None:
        module=sys.modules.get('src.staged_rts24_process_guard_v1')
        if module is not None and not getattr(getattr(module,'__spec__',None),'_initializing',False) and hasattr(module,'OwnedChild'):
            owner_class=module.OwnedChild;original_owner_init=owner_class.__init__;owner_class.__init__=denied_owner
    return result

assert sys.getprofile() is None
sys.addaudithook(audit);builtins.__import__=guarded_import
sys.path.insert(0,str(ROOT))
class ObservedNodes:
    def __init__(self):self.collection=[];self.passed=[];self.failed=[];self.skipped=[];self.legacy=[];self.unexpected=[]
    def pytest_collection_modifyitems(self,session,config,items):
        if not collect_only:return
        previous=json.loads((ROOT/'results/tables/staged_rts24_saved_fresh_successor_direct_entry_v1_non_authoritative/checks_01/group_admission_03.json').read_bytes())
        old_nodes={n for group in previous['groups'].values() for n in group}
        baseline=read('baseline.json');old_pin=baseline['sources']['tests/test_staged_rts24_saved_fresh_adoption_v1.py']
        old_raw=(OUT/('code_'+old_pin['sha256']+'.snapshot')).read_bytes();assert pin(old_raw)==old_pin
        old_names={n.name for n in ast.parse(old_raw).body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
        selected=[];excluded=[]
        for item in items:
            function=getattr(item,'originalname',None) or item.name.split('[',1)[0]
            if item.nodeid in old_nodes or function.startswith('test_saved_role_data_'):selected.append(item)
            elif function in old_names:excluded.append(item);self.legacy.append(item.nodeid)
            else:self.unexpected.append(item.nodeid)
        assert not self.unexpected,'unselected new test outside declared scope'
        items[:]=selected
        if excluded:config.hook.pytest_deselected(items=excluded)
    def pytest_collection_finish(self,session):self.collection=[item.nodeid for item in session.items]
    def pytest_runtest_logreport(self,report):
        if report.failed:self.failed.append((report.nodeid,report.when))
        if report.skipped:self.skipped.append((report.nodeid,report.when))
        if report.when=='call' and report.passed:self.passed.append(report.nodeid)
observer=ObservedNodes()
try:
    import pytest
    code=pytest.main((['--collect-only'] if collect_only else [])+['-q','-s','--maxfail=1','--durations=10',*nodes,'-p','no:cacheprovider',
        '-o','tmp_path_retention_count=100000','-o','tmp_path_retention_policy=all'],plugins=[observer])
finally:
    builtins.__import__=original_import
    if owner_class is not None:owner_class.__init__=original_owner_init
    active=False
save(label+'.harness.json',dict(authority='DRAFT_NONAUTHORITATIVE',counts=counts,
    collected_nodes=observer.collection,passed_call_nodes=observer.passed,failed_phases=observer.failed,skipped_phases=observer.skipped,
    legacy_deselected_nodes=observer.legacy,unexpected_new_collection_nodes=observer.unexpected,
    requested_nodes=None if collect_only else nodes,pytest_exit_code=int(code),
    guards_installed_before_repository_import=True,numpy_SVE_forced_false=bool(counts['blocked_lscpu']),
    native_constructor_guard_installed=owner_class is not None,
    native_constructor_original_restored=owner_class is not None and owner_class.__init__ is original_owner_init,
    audit_hook_installed_until_process_exit=True,audit_active_at_observation_end=False,
    guarded_write_API_events=['open(write)','os.mkdir','os.remove/unlink','os.rmdir','os.rename/replace',
        'os.link','os.symlink','os.chmod/chown','os.utime','os.truncate'],
    production_policy_decided=False,arbitrary_native_effects_proved_absent=False,actual_saved_F_execution=False))
print('ORDINARY_HARNESS '+json.dumps(counts,sort_keys=True))
assert counts['blocked_lscpu']==counts['optional_Popen_attempts']==1
assert owner_class is not None and owner_class.__init__ is original_owner_init and builtins.__import__ is original_import
assert not any(v for k,v in counts.items() if k not in ('blocked_lscpu','optional_Popen_attempts'))
if not collect_only and int(code)==0:
    assert len(set(observer.collection))==len(observer.collection) and set(observer.collection)==set(nodes)
    assert len(set(observer.passed))==len(observer.passed) and set(observer.passed)==set(nodes)
    assert not observer.failed and not observer.skipped
raise SystemExit(int(code))
