"""Five preregistered RAM counterexamples, with guards before repository import."""
import builtins
import json
import os
from pathlib import Path
import sys
from common import ROOT,OUT,OUTPUT_PARENT,EXE,pin,selected,save,read

assert not any(n=='src' or n.startswith(('src.','experiments.')) for n in sys.modules)
assert sys.getprofile() is None
P1=ROOT/'results/tables/staged_rts24_native_v1_non_authoritative/p1_01'
phase='repository_import';counts={};changes=[];changed=set();source=selected();audit_active=True;optional_probes=[]
numpy_source=EXE.parent/'Lib/site-packages/numpy/testing/_private/utils.py'
subprocess_source=EXE.parent/'Lib/subprocess.py'
external={str(numpy_source):dict(bytes=87751,sha256='15a67bea0d5acd4f22d345e44d065512b06d1456639de5c2d100a25276a67b8c'),
    str(subprocess_source):dict(bytes=88747,sha256='85d29b2bf0249f5436838298c9a60ee93508b1102e9ac43b001f8a7e7ae8f375')}
assert all(pin(Path(n).read_bytes())==p for n,p in external.items())
runtime=read('runtime_pin_v2.json');assert runtime['python']==sys.version and pin(EXE.read_bytes())==runtime['pin']
fields=('P1_open_attempts','process_launch_attempts','scientific_API_attempts','solver_factory_attempts',
    'native_owner_attempts','mutator_calls','unexpected_repository_writes')


def bucket(): return counts.setdefault(phase,dict.fromkeys(fields,0))
def denied(kind):
    bucket()[kind]+=1
    raise AssertionError('witness attempted '+kind)


def normalized(path): return os.path.normcase(os.path.abspath(os.fspath(path)))
root_prefix=normalized(ROOT)+os.sep;p1_prefix=normalized(P1)+os.sep;out_prefix=normalized(OUT)+os.sep


class OptionalProbeBlocked(OSError): pass


def audit(event,args):
    if not audit_active: return
    if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
        path=normalized(os.fsdecode(args[0]))
        if path==p1_prefix[:-1] or path.startswith(p1_prefix): denied('P1_open_attempts')
        mode=args[1];flags=args[2]
        write=(type(mode) is str and any(c in mode for c in 'wax+')) or (type(flags) is int and bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)))
        if write and path.startswith(root_prefix) and not path.startswith(out_prefix): denied('unexpected_repository_writes')
    if event=='subprocess.Popen':
        stack=[];frame=sys._getframe(1)
        while frame is not None:
            stack.append((normalized(frame.f_code.co_filename),frame.f_code.co_name,frame.f_lineno));frame=frame.f_back
        exact=(normalized(numpy_source),'check_support_sve',1247) in stack \
            and (normalized(numpy_source),'<module>',1253) in stack \
            and (normalized(subprocess_source),'_execute_child',1534) in stack
        if phase=='repository_import' and tuple(args)==(None,'lscpu',None,None) and exact and not optional_probes:
            bucket()['process_launch_attempts']+=1
            optional_probes.append(dict(executable=None,argv='lscpu',cwd=None,environment_is_none=True,
                numpy_function_line=1247,numpy_module_line=1253,subprocess_audit_line=1534,
                blocked_at_python_audit_point=True))
            raise OptionalProbeBlocked('diagnostic blocks optional lscpu CPU-feature probe')
        denied('process_launch_attempts')
    if event=='os.system' or event.startswith('os.spawn'): denied('process_launch_attempts')


scientific_names={'compile_problem','import_snapshot','make_model','call_highs','snapshot_from_raw',
    'capture','hold','bookend','replay','_replay','replay_prefix','replay_point','reopen',
    'create_session','begin_step','commit_step','finish','put','publish'}


def profile(frame,event,arg):
    if event!='call': return
    filename=frame.f_code.co_filename.casefold()
    if filename.startswith(str(ROOT).casefold()):
        if frame.f_code.co_name in scientific_names: denied('scientific_API_attempts')
        if frame.f_code.co_qualname.endswith('OwnedChild.__init__'): denied('native_owner_attempts')


def replace(module,name,value):
    key=(id(module),name)
    if key not in changed:
        changes.append((module,name,getattr(module,name)));changed.add(key)
    setattr(module,name,value)


def solver_denied(*args,**kwargs): denied('solver_factory_attempts')
original_import=builtins.__import__


def guarded_import(*args,**kwargs):
    result=original_import(*args,**kwargs)
    for name,attribute in (('highspy','Highs'),('pyomo.environ','SolverFactory')):
        module=sys.modules.get(name)
        if module is not None and not getattr(getattr(module,'__spec__',None),'_initializing',False) and hasattr(module,attribute):
            replace(module,attribute,solver_denied)
    return result


rows=[];restored=False;primary=None;bucket()
sys.addaudithook(audit);sys.setprofile(profile);builtins.__import__=guarded_import
try:
    sys.path.insert(0,str(ROOT))
    from experiments import staged_rts24_saved_fresh_adoption_v1 as entry
    from src import staged_rts24_saved_fresh_adoption_v1 as adapter
    phase='post_import';bucket()
    def scientific_denied(*args,**kwargs): denied('scientific_API_attempts')
    for module,name in ((adapter,'replay'),(adapter.prefix,'replay_prefix'),(adapter.journal,'reopen'),
        (adapter.prefix.point.numeric,'compile_problem'),(adapter.prefix.point.numeric,'import_snapshot'),
        (adapter.prefix.point.backend,'make_model'),(adapter.prefix.point.backend,'call_highs'),
        (adapter.prefix.point.backend,'snapshot_from_raw'),(adapter.codec.EvidenceStore,'put'),
        (adapter.codec,'publish'),(adapter.journal,'publish')):
        replace(module,name,scientific_denied)
    for name in ('create_session','begin_step','commit_step','finish'): replace(adapter.journal,name,scientific_denied)
    baseline=entry._expectation_adapter(source)
    assert len(baseline[1])==10
    cases=[('codec.parse',adapter.codec,'parse'),('adapter._replay',adapter,'_replay'),
        ('core.digest',adapter.core,'digest'),('adapter.HeldInput',adapter,'HeldInput'),
        ('adapter.METRIC_FIELDS',adapter,'METRIC_FIELDS')]
    for label,module,name in cases:
        phase=label;bucket();original=getattr(module,name);namespace=vars(module)
        def mutation(*args,**kwargs): denied('mutator_calls')
        if name=='HeldInput':
            class ForeignHeldInput:
                def __new__(cls,*args,**kwargs): denied('mutator_calls')
            replacement=ForeignHeldInput
        elif name=='METRIC_FIELDS': replacement=original+('witness_only_field',)
        else: replacement=mutation
        accepted=False
        try:
            setattr(module,name,replacement)
            binding=entry._expectation_adapter(source)
            assert getattr(module,name) is replacement and vars(module) is namespace
            assert binding[0] is adapter and len(binding[1])==10
            accepted=True
        finally:
            setattr(module,name,original)
        assert accepted and getattr(module,name) is original and vars(module) is namespace
        assert not any(bucket().values())
        rows.append(dict(symbol=label,expected='preparation_binding_accepts',accepted=True,
            replacement_called=False,original_object_restored=True,module_globals_identity_unchanged=True))
    phase='restoration';bucket()
except BaseException as error:
    primary=error
finally:
    for module,name,original in reversed(changes): setattr(module,name,original)
    builtins.__import__=original_import;sys.setprofile(None)
    restored=all(getattr(module,name) is original for module,name,original in changes)
    audit_active=False
try:
    assert restored and builtins.__import__ is original_import and sys.getprofile() is None and audit_active is False
    assert len(rows)==5 and len(optional_probes)==1
    assert sum(row['process_launch_attempts'] for row in counts.values())==1
    assert not any(value for row in counts.values() for name,value in row.items() if name!='process_launch_attempts')
    assert selected()==source and not OUTPUT_PARENT.exists()
    assert all(pin(Path(n).read_bytes())==p for n,p in external.items())
except BaseException as error:
    if primary is None: primary=error
value=dict(authority='DRAFT_NONAUTHORITATIVE',source_pins=source,cases=rows,
    phase_counts=counts,import_guards_installed_before_repository_import=True,
    declared_scientific_API_names=sorted(scientific_names),replacement_import_profile_originals_restored=restored,
    audit_hook_installed_until_process_exit=True,audit_hook_active_at_observation_end=audit_active,
    counters_cover_declared_APIs_not_arbitrary_native_effects=True,
    declared_python_audit_P1_open_attempts=sum(row['P1_open_attempts'] for row in counts.values()),
    declared_subprocess_Popen_attempts=sum(row['process_launch_attempts'] for row in counts.values()),
    blocked_lscpu_fallbacks=len(optional_probes),optional_probes=optional_probes,external_source_pins=external,
    numpy_sve_support_forced_false_by_instrumentation=bool(optional_probes),
    all_preregistered_acceptances_established=primary is None and len(rows)==5,
    failure=None if primary is None else dict(type=type(primary).__name__,message=str(primary)[:256]),
    full_runtime_closure_proved=False,production_guard_bypassed=False,actual_saved_F_execution=False,
    F_launch_admitted=False,scientific_evidence_adopted=False,resource_admission=False,formal_result=False)
save('global_binding_witness_v2.json' if primary is None else 'failed_witness_06.json',value)
if primary is not None: raise primary
print(json.dumps(dict(cases=len(rows),all_preregistered_acceptances_established=True,
    declared_subprocess_Popen_attempts=1,blocked_lscpu_fallbacks=1,original_objects_restored=restored,
    declared_python_audit_P1_open_attempts=0,audit_hook_active_at_observation_end=False,
    actual_saved_F_execution=False)))
