"""Bounded binding-consumer development package; zero cold/scientific calls."""
import ast
import base64
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

if sys.flags.optimize!=0:raise RuntimeError('unoptimized development checks required')

OUT=Path(__file__).absolute().parent;ROOT=OUT.parents[2]
PRIOR=ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v10_non_authoritative'
EXE='D:/Miniconda3/envs/compute/python.exe'
CORE=ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v38.py'
HELPER=ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_consumer_v2.py'
PROBE=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v36.py'
TEST=ROOT/'tests/test_staged_rts24_saved_fresh_consumer_binding_v1.py'
ORACLE=ROOT/'experiments/staged_rts24_saved_fresh_consumer_binding_source_oracle_v1.py'
SCOPE=ROOT/'docs/plan/staged_deliverability_c_saved_fresh_producer_binding_admission_scope_v1.md'
MEMORY=ROOT/'experiments/staged_rts24_saved_fresh_memory_drain_v1.py'
CAPS=dict(size=5,register=4,unittest=30,pre_seal=5,saved=5,checkpoint=4)
FALSE_FIELDS=('external_expected_truth_verified','upstream_owner_verified','parent_independently_authenticated_python_object_graph',
    'startup_tcb_authenticated','independent_root_verified','native_behavior_verified','full_runtime_binding_verified',
    'full_P1_content_verified','producer_capability_verified','role_bootstrap','permit_issued','native_authorized',
    'F_launch_admitted','actual_F','run_authority','scientific_evidence_adopted','resource_admission','formal_result','production_seal')


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def read(path):return json.loads(path.read_bytes())
def flags():return {key:False for key in FALSE_FIELDS}
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def own_inputs():return (CORE,HELPER,PROBE,TEST,ORACLE,SCOPE,MEMORY,Path(__file__).absolute())


def archive():
    paths=[ROOT/f'results/tables/staged_rts24_saved_fresh_nfc_v{index}_non_authoritative' for index in range(1,11)]
    paths.extend((ROOT/'results/tables/staged_rts24_saved_fresh_nfc_metadata_read_v1_non_authoritative',
        ROOT/'results/tables/staged_rts24_saved_fresh_pin_memo_v1_non_authoritative'))
    files=[path for folder in paths for path in folder.iterdir()]
    assert len(files)==121 and all(path.is_file() for path in files) and sum(path.stat().st_size for path in files)==10460646
    return {str(path):pin(path.read_bytes()) for path in files}


def save(path,value):
    assert path.parent==OUT and not path.exists();raw=canonical(value);assert len(raw)<=1048576
    paths=list(OUT.iterdir());assert all(p.is_file() for p in paths) and len(paths)+1<=12
    assert sum(p.stat().st_size for p in paths)+len(raw)<=4194304
    with path.open('xb') as stream:stream.write(raw)


def previous():
    raw=(PRIOR/'checkpoint.json').read_bytes()
    assert pin(raw)['sha256']=='8abd5d04628ee39cb93dc31f4e4eb307ecf9f49f99b80063d77d903e0a24bd65'
    cp=json.loads(raw);assert cp['accepted'] is cp['diagnostic_accepted'] is True
    assert cp['all_cumulative_total_seconds']==977.1529690999844 and cp['prior_not_accepted_count']==38
    assert {p.name for p in PRIOR.iterdir()}==set(cp['root_map_before_checkpoint'])|{'checkpoint.json'}
    for name,value in cp['root_map_before_checkpoint'].items():assert pin((PRIOR/name).read_bytes())==value,name
    assert len(list(PRIOR.iterdir()))==16 and sum(p.stat().st_size for p in PRIOR.iterdir())==1824018
    predecessor=load(PRIOR/'driver.py','_consumer_predecessor')
    old=read(ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v3_non_authoritative/registration.json')
    inherited=predecessor.inherited_inputs(old);reg=read(PRIOR/'registration.json')
    for path,value in reg['input_pins'].items():
        if path in inherited:assert inherited[path]==value,path
        inherited[path]=value
    assert len(inherited)==reg['effective_input_count']==1124
    for path,value in inherited.items():assert pin(Path(path).read_bytes())==value,path
    return cp,inherited,reg


def nodes():
    prior=load(PRIOR/'driver.py','_consumer_frozen_nodes').nodes()
    new=next(node for node in ast.parse(TEST.read_bytes()).body if type(node) is ast.ClassDef and node.name=='ConsumerBindingTests')
    names=[value.rsplit('.',1)[1] for value in prior]+[node.name for node in new.body if type(node) is ast.FunctionDef and node.name.startswith('test_')]
    assert len(names)==len(set(names))==41
    return sorted('consumer_binding_tests.ConsumerBindingTests.'+name for name in names)


def migration():
    oldcore=(ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v37.py').read_text(encoding='utf8').replace('nfc_v10_non_authoritative','nfc_v11_non_authoritative')
    before=ast.parse(oldcore);after=ast.parse(CORE.read_bytes())
    old={node.name:node for node in before.body if isinstance(node,(ast.FunctionDef,ast.ClassDef))}
    new={node.name:node for node in after.body if isinstance(node,(ast.FunctionDef,ast.ClassDef))}
    changed={'capture_bindings','check_bindings','check_compiled_namespace','runtime_seal','LocalPreEntryInputs','LocalRuntimeInputs'}
    assert set(new)-set(old)=={'held_consumer_helper'} and set(old)<=set(new)
    for name,node in old.items():
        if name not in changed:assert ast.dump(node,include_attributes=False)==ast.dump(new[name],include_attributes=False),name
    def image(value):return ast.dump(value,include_attributes=False)
    def clone(value):return ast.parse(ast.unparse(value)).body[0]
    receiver=clone(new['LocalPreEntryInputs'])
    calls=[node for node in ast.walk(receiver) if type(node) is ast.Call and type(node.func) is ast.Name
        and node.func.id=='dict' and any(key.arg=='_control_after_import' for key in node.keywords)]
    assert len(calls)==1
    additions=[key for key in calls[0].keywords if key.arg in ('_consumer_plan','_consume_state')]
    assert [key.arg for key in additions]==['_consumer_plan','_consume_state'] and all(type(key.value) is ast.Constant and key.value.value is None for key in additions)
    calls[0].keywords=[key for key in calls[0].keywords if key not in additions]
    assert image(receiver)==image(old['LocalPreEntryInputs'])
    runtime=clone(new['LocalRuntimeInputs']);methods={node.name:node for node in runtime.body if type(node) is ast.FunctionDef}
    prior_methods={node.name:node for node in old['LocalRuntimeInputs'].body if type(node) is ast.FunctionDef}
    assert set(methods)-set(prior_methods)=={'prepare_consumer','consume_once'}
    for name,node in prior_methods.items():
        if name!='entry':assert image(node)==image(methods[name]),name
    extra=[node for node in methods['entry'].body if type(node) is ast.If and '_consumer_plan' in ast.unparse(node.test)]
    assert len(extra)==1;methods['entry'].body.remove(extra[0]);assert image(methods['entry'])==image(prior_methods['entry'])
    slots=next(node for node in runtime.body if type(node) is ast.Assign and any(type(target) is ast.Name and target.id=='__slots__' for target in node.targets))
    added_slots=[node.value for node in slots.value.elts if node.value in ('_consumer_plan','_consume_state')]
    assert added_slots==['_consumer_plan','_consume_state']
    slots.value.elts=[node for node in slots.value.elts if node.value not in added_slots]
    runtime.body=[node for node in runtime.body if not (type(node) is ast.FunctionDef and node.name in ('prepare_consumer','consume_once'))]
    assert image(runtime)==image(old['LocalRuntimeInputs'])
    assert image(ast.Module(body=[node for node in before.body if not isinstance(node,(ast.FunctionDef,ast.ClassDef))],type_ignores=[]))==image(ast.Module(body=[node for node in after.body if not isinstance(node,(ast.FunctionDef,ast.ClassDef))],type_ignores=[]))
    oldhelper=ast.parse((ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_post_return_v1.py').read_bytes())
    newhelper=ast.parse(HELPER.read_bytes());declarations={node.name:node for node in newhelper.body if isinstance(node,(ast.FunctionDef,ast.ClassDef))}
    for node in oldhelper.body:
        if isinstance(node,(ast.FunctionDef,ast.ClassDef)):assert ast.dump(node,include_attributes=False)==ast.dump(declarations[node.name],include_attributes=False),node.name
    added_helpers={'consumer_root','consumer_helper_checker','prepare_consumer_plan','build_consumer_plan','verify_consumer_plan','invoke_consumer_plan'}
    filtered=[node for node in newhelper.body if not (type(node) is ast.FunctionDef and node.name in added_helpers)]
    assert image(ast.Module(body=filtered,type_ignores=[]))==image(oldhelper)
    source=(ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v35.py').read_text(encoding='utf8')
    replacements=(('nfc_v10_non_authoritative','nfc_v11_non_authoritative'),
        ('observed=None\n','observed=None;consumer_result=None\n'),
        ('            adapter,adapter_bindings,retention=bs_helper.load_bootstrap_adapter(runtime,boundary)\n',
         "            adapter,adapter_bindings,retention=bs_helper.load_bootstrap_adapter(runtime,boundary)\n            phase='CONSUMER_PREPARATION';runtime.prepare_consumer()\n"),
        ("            runtime.entry();observed=runtime._phase;was_live=observed=='LIVE';bs_helper.trace_import_stage(runtime,'after_finish_import')\n",
         "            runtime.entry();observed=runtime._phase;was_live=observed=='LIVE';bs_helper.trace_import_stage(runtime,'after_finish_import')\n            phase='CONSUMER';consumer_result=runtime.consume_once('expectation_binding',b'{\"consumer\":\"expectation_binding\",\"v\":1}')\n"),
        ("        runtime_phase_before_close=observed,post_metrics=None if bs_helper is None else bs_helper._POST_METRICS,\n",
         "        runtime_phase_before_close=observed,post_metrics=None if bs_helper is None else bs_helper._POST_METRICS,\n        consumer_result=None if consumer_result is None else json.loads(consumer_result),consumer_state=None if runtime is None else runtime._consume_state,\n"))
    for before_text,after_text in replacements:
        assert source.count(before_text)==1,before_text;source=source.replace(before_text,after_text,1)
    assert source.encode()==PROBE.read_bytes()
    for path in (CORE,HELPER,PROBE,TEST,ORACLE,Path(__file__).absolute()):compile(path.read_bytes(),str(path),'exec',dont_inherit=True,optimize=0)
    return dict(source49_unchanged=True,old_namespace_methods_ast_unchanged=True,old_core_scope_unchanged_outside_declared_set=True,
        changed_core_declarations=sorted(changed),new_core_declarations=['held_consumer_helper'],cold_calls=0,P1_calls=0,scientific_calls=0)


def check(reg):
    assert reg['accepted'] is True and reg['authority']=='DRAFT_NONAUTHORITATIVE'
    assert reg['python_optimized'] is False
    for path,value in reg['input_pins'].items():assert pin(Path(path).read_bytes())==value,path
    for key in FALSE_FIELDS:assert reg[key] is False
    size=read(OUT/'size.exit.json');assert size['accepted'] is True
    expected={**size['payload']['input_pins'],str(OUT/'size.exit.json'):pin((OUT/'size.exit.json').read_bytes())}
    assert reg['input_pins']==expected and reg['effective_input_count']==len(expected)
    assert reg['own_input_pins']=={str(path):pin(path.read_bytes()) for path in own_inputs()}
    assert reg['archive_pins']==archive()
    oracle=load(ORACLE,'_consumer_checked_source_oracle').inspect()
    assert canonical(oracle)==canonical(reg['source_oracle']) and migration()==reg['migration'] and nodes()==reg['unit_nodes']
    return reg


def parse_unit(raw,reg):
    lines=raw.splitlines(keepends=True);frames=[json.loads(line) for line in lines]
    assert all(canonical(frame)+b'\n'==line for frame,line in zip(frames,lines))
    assert len(frames)==84 and frames[0]==['admission',dict(nodes=reg['unit_nodes'],before_test_calls=True)]
    for index,name in enumerate(reg['unit_nodes']):assert frames[1+2*index:3+2*index]==[['test_start',name],['test_end',name]]
    tag,report=frames[-1];assert tag=='report' and set(report)=={'accepted','tests_run','failures','errors','skipped'}
    assert report['accepted'] is True and report['tests_run']==41 and report['failures']==report['errors']==report['skipped']==0
    return report


def unit_child():
    import unittest
    reg=check(read(OUT/'registration.json'));module=load(TEST,'consumer_binding_tests')
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(module.ConsumerBindingTests)
    assert [test.id() for test in suite]==reg['unit_nodes']
    def emit(row):sys.stdout.buffer.write(canonical(row)+b'\n');sys.stdout.buffer.flush()
    emit(['admission',dict(nodes=reg['unit_nodes'],before_test_calls=True)])
    class Witness(unittest.TextTestResult):
        def startTest(self,test):emit(['test_start',test.id()]);super().startTest(test)
        def stopTest(self,test):super().stopTest(test);emit(['test_end',test.id()])
    result=unittest.TextTestRunner(verbosity=2,resultclass=Witness).run(suite);check(reg)
    report=dict(accepted=result.wasSuccessful() and result.testsRun==41 and not result.skipped,
        tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped))
    emit(['report',report]);raise SystemExit(0 if report['accepted'] else 1)


def unit(reg):
    memory=load(MEMORY,'_consumer_unit_memory');process=None;closed=False;rc=None;out=err=b'';why=None;observed=None
    try:
        process=subprocess.Popen([EXE,'-B','-s',str(Path(__file__).absolute()),'unit_child'],executable=EXE,cwd=ROOT,
            stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        rc,out,err,why,observed=memory.drain(process,25.)
    finally:
        if process is not None:
            if process.poll() is None:process.kill();process.wait(timeout=1.)
            handle=int(process._handle);process._handle.Close()
            api=memory.C.WinDLL('kernel32',use_last_error=True).GetHandleInformation
            api.argtypes=[memory.W.HANDLE,memory.C.POINTER(memory.W.DWORD)];api.restype=memory.W.BOOL
            value=memory.W.DWORD();memory.C.set_last_error(0)
            closed=process._handle.closed and not api(memory.W.HANDLE(handle),memory.C.byref(value)) and memory.C.get_last_error()==6
    payload=dict(returncode=rc,drain_reason=why,process_handle_closed=closed,drain=observed,
        stdout_raw_base64=base64.b64encode(out).decode(),stderr_raw_base64=base64.b64encode(err).decode(),stdout_pin=pin(out),stderr_pin=pin(err))
    try:
        assert rc==0 and why is None and closed
        assert observed['pipes_closed'] and observed['reader_threads_terminal'] and not observed['cleanup'] and not observed['reader_errors']
        assert not observed['killed'] and not observed['stdout_truncated'] and not observed['stderr_truncated']
        memory.validate_guard(observed['memory_guard']);payload['unit_report']=parse_unit(out,reg)
        payload['accepted']=True
    except BaseException as error:payload.update(accepted=False,validation_error=type(error).__name__+':'+str(error))
    return payload


def saved(reg):
    row=read(OUT/'unittest.exit.json');payload=row['payload'];assert row['accepted'] is True
    out=base64.b64decode(payload['stdout_raw_base64'],validate=True);err=base64.b64decode(payload['stderr_raw_base64'],validate=True)
    assert pin(out)==payload['stdout_pin'] and pin(err)==payload['stderr_pin']
    assert parse_unit(out,reg)==payload['unit_report'] and payload['process_handle_closed'] is True
    load(MEMORY,'_consumer_saved_memory').validate_guard(payload['drain']['memory_guard'])
    return dict(accepted=True,unit_exit_pin=pin((OUT/'unittest.exit.json').read_bytes()),unit_report=payload['unit_report'],
        source_oracle_pin=pin(canonical(reg['source_oracle'])),migration=reg['migration'],cold_calls=0,P1_calls=0,scientific_calls=0,**flags())


def run(action):
    started=time.perf_counter();target=OUT/('registration.json' if action=='register' else action+'.exit.json')
    assert action in CAPS and not target.exists();kind='unittest' if action=='unittest' else 'static'
    payload={};accepted=False;error=None
    try:
        if action=='size':
            prior,inherited,old=previous();oracle=load(ORACLE,'_consumer_source_oracle').inspect()
            inputs={**inherited,**{str(path):pin(path.read_bytes()) for path in own_inputs()},
                str(PRIOR/'checkpoint.json'):pin((PRIOR/'checkpoint.json').read_bytes()),str(PRIOR/'registration.json'):pin((PRIOR/'registration.json').read_bytes())}
            payload=dict(input_pins=inputs,effective_input_count=len(inputs),own_input_pins={str(path):pin(path.read_bytes()) for path in own_inputs()},
                source_oracle=oracle,migration=migration(),unit_nodes=nodes(),prior_checkpoint_pin=pin((PRIOR/'checkpoint.json').read_bytes()),
                archive_pins=archive(),python_optimized=False,prior_archive_files=121,prior_archive_bytes=10460646)
        elif action=='register':
            row=read(OUT/'size.exit.json');assert row['accepted'] is True;payload={**row['payload']}
            payload['input_pins']={**payload['input_pins'],str(OUT/'size.exit.json'):pin((OUT/'size.exit.json').read_bytes())}
            payload['effective_input_count']=len(payload['input_pins'])
            for path,value in payload['input_pins'].items():assert pin(Path(path).read_bytes())==value,path
            assert canonical(load(ORACLE,'_consumer_registration_oracle').inspect())==canonical(payload['source_oracle'])
        elif action=='checkpoint':
            records={path.name:read(path) for path in OUT.glob('*.exit.json')}
            if (OUT/'registration.json').exists():records['registration.json']=read(OUT/'registration.json')
            failed=[name for name,row in records.items() if row['accepted'] is False]
            prior,inherited,old=previous()
            if not failed:
                reg=check(records['registration.json']);assert set(records)=={'size.exit.json','registration.json','unittest.exit.json','pre_seal.exit.json','saved.exit.json'}
                assert canonical(records['saved.exit.json']['payload'])==canonical(saved(reg))
            usage={name:sum(row['charged_seconds'] for row in records.values() if row['kind']==name) for name in ('static','unittest')}
            payload=dict(diagnostic_accepted=not failed,acceptance_scope='logical_binding_consumer_development_only' if not failed else 'rejection_metadata_only',
                scope_charged_seconds=usage,prior_all_cumulative_charged_seconds=prior['all_cumulative_charged_seconds'],
                prior_not_accepted_count=38+len(failed),failed_records=failed,prior_archive_files=121,prior_archive_bytes=10460646,
                artifact_pins={str(path):pin(path.read_bytes()) for path in OUT.iterdir()},cold_calls=0,P1_calls=0,scientific_calls=0)
        else:
            reg=check(read(OUT/'registration.json'))
            if action=='unittest':payload=unit(reg);assert payload['accepted'] is True
            elif action=='pre_seal':
                raw=sys.stdin.buffer.read(32769);assert len(raw)<=32768;finding=json.loads(raw);assert canonical(finding)==raw
                assert finding['must_fix_open']==[] and finding['official_review'] is False
                assert finding['registration_pin']==pin((OUT/'registration.json').read_bytes())
                assert finding['unit_exit_pin']==pin((OUT/'unittest.exit.json').read_bytes())
                assert finding['own_input_pins']==reg['own_input_pins'] and finding['verified_input_count']==reg['effective_input_count']
                assert read(OUT/'unittest.exit.json')['accepted'] is True
                payload=dict(accepted=True,findings=finding,**flags())
            else:
                assert read(OUT/'pre_seal.exit.json')['accepted'] is True;payload=saved(reg)
            check(reg)
        accepted=True
    except BaseException as caught:error=type(caught).__name__+':'+str(caught)
    charge=time.perf_counter()-started;accepted=accepted and charge<=CAPS[action]
    record=dict(accepted=accepted,authority='DRAFT_NONAUTHORITATIVE',action=action,kind=kind,charged_seconds=charge,cap_seconds=CAPS[action],error=error,payload=payload,**flags())
    if action=='register' and accepted:record.update(payload)
    if action=='checkpoint':
        usage=payload['scope_charged_seconds'];usage['static']+=charge
        cumulative={**payload['prior_all_cumulative_charged_seconds']}
        for key in usage:cumulative[key]+=usage[key]
        record.update(payload,all_cumulative_charged_seconds=cumulative,all_cumulative_total_seconds=sum(cumulative.values()),
            package_charged_seconds=sum(usage.values()))
        record['accepted']=accepted=accepted and usage['static']<=60 and usage['unittest']<=30 and sum(usage.values())<=90
        record['prior_not_accepted_count']+=not accepted
        target=OUT/'checkpoint.json'
    save(target,record)
    print(canonical(dict(action=action,accepted=accepted,charge=charge,error=error)).decode())
    if not accepted:raise SystemExit(1)


if __name__=='__main__':
    if sys.argv[1]=='unit_child':unit_child()
    else:run(sys.argv[1])
