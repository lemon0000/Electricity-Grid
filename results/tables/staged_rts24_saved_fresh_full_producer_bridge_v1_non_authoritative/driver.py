"""Finite source-derived producer bridge validation; no P1 or cold execution."""
import ast
import base64
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

if sys.flags.optimize!=0:raise RuntimeError('unoptimized bridge validation required')
OUT=Path(__file__).absolute().parent;ROOT=OUT.parents[2]
PRIOR=ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v12_non_authoritative'
BUILDER=ROOT/'experiments/staged_rts24_saved_fresh_prebound_expectation_code_v1.py'
TEST=ROOT/'tests/test_staged_rts24_saved_fresh_prebound_expectation_code_v1.py'
SCOPE=ROOT/'docs/plan/staged_deliverability_c_saved_fresh_full_producer_bridge_scope_v1.md'
CAPTURE=ROOT/'experiments/staged_rts24_saved_fresh_sampled_capture_v1.py'
MEMORY=ROOT/'experiments/staged_rts24_saved_fresh_memory_drain_v1.py'
EXE='D:/Miniconda3/envs/compute/python.exe'
CAPS=dict(register=5,unittest=10,pre_seal=5,saved=5,checkpoint=5)
FALSE_FIELDS=('producer_capability_verified','full_runtime_binding_verified','full_P1_content_verified','role_bootstrap',
    'permit_issued','run_authority','resource_admission','scientific_evidence_adopted','formal_result','actual_F','production_seal')


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def read(path):return json.loads(path.read_bytes())
def flags():return {key:False for key in FALSE_FIELDS}
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def own():return (BUILDER,TEST,SCOPE,CAPTURE,MEMORY,Path(__file__).absolute())


def save(path,value):
    raw=canonical(value);assert path.parent==OUT and not path.exists() and len(raw)<=1048576
    files=list(OUT.iterdir());assert all(path.is_file() for path in files) and len(files)+1<=10
    assert sum(path.stat().st_size for path in files)+len(raw)<=4194304
    with path.open('xb') as stream:stream.write(raw)


def previous():
    raw=(PRIOR/'checkpoint.json').read_bytes();assert pin(raw)['sha256']=='bbe4eaf6a67d5025db498bde68526c3fd2352e3a71edf05a21711505067b70de'
    cp=json.loads(raw);assert cp['accepted'] is cp['diagnostic_accepted'] is True
    assert cp['all_cumulative_total_seconds']==1088.9926936999939 and cp['prior_not_accepted_count']==39
    assert {path.name for path in PRIOR.iterdir()}==set(cp['root_map_before_checkpoint'])|{'checkpoint.json'}
    for name,value in cp['root_map_before_checkpoint'].items():assert pin((PRIOR/name).read_bytes())==value,name
    frozen=load(PRIOR/'driver.py','_frozen_connected_input_reader')
    old,_=frozen.previous();inputs=frozen.inherited_inputs(old)
    for path,value in read(PRIOR/'registration.json')['input_pins'].items():
        if path in inputs:assert inputs[path]==value,path
        inputs[path]=value
    assert len(inputs)==1167
    for path,value in inputs.items():assert pin(Path(path).read_bytes())==value,path
    for path in PRIOR.iterdir():inputs[str(path)]=pin(path.read_bytes())
    devreg=read(frozen.DEV/'registration.json')
    archive=[Path(path) for path in devreg['archive_pins']]+list(frozen.DEV.iterdir())+list(frozen.NFC11.iterdir())+list(PRIOR.iterdir())
    assert len(archive)==155 and sum(path.stat().st_size for path in archive)==14350165
    return cp,inputs,{str(path):pin(path.read_bytes()) for path in archive}


def nodes():
    cls=next(node for node in ast.parse(TEST.read_bytes()).body if type(node) is ast.ClassDef and node.name=='PreboundExpectationCodeTests')
    names=[node.name for node in cls.body if type(node) is ast.FunctionDef and node.name.startswith('test_')]
    assert len(names)==len(set(names))==4
    return sorted('prebound_tests.PreboundExpectationCodeTests.'+name for name in names)


def check(reg):
    assert reg['accepted'] is True and reg['python_optimized'] is False
    for path,value in reg['input_pins'].items():assert pin(Path(path).read_bytes())==value,path
    for path,value in reg['archive_pins'].items():assert pin(Path(path).read_bytes())==value,path
    _,report=load(BUILDER,'_checked_prebound_builder').current()
    assert canonical(report)==canonical(reg['derivation']) and reg['unit_nodes']==nodes()
    assert reg['own_input_pins']=={str(path):pin(path.read_bytes()) for path in own()}
    assert all(reg[key] is False for key in FALSE_FIELDS)
    return reg


def parse_unit(raw,reg):
    lines=raw.splitlines(keepends=True);frames=[json.loads(line) for line in lines]
    assert all(canonical(frame)+b'\n'==line for frame,line in zip(frames,lines))
    assert len(frames)==10 and frames[0]==['admission',dict(nodes=reg['unit_nodes'],before_test_calls=True)]
    for index,name in enumerate(reg['unit_nodes']):assert frames[1+index*2:3+index*2]==[['test_start',name],['test_end',name]]
    assert frames[-1]==['report',dict(accepted=True,tests_run=4,failures=0,errors=0,skipped=0)]
    return frames[-1][1]


def unit_child():
    import unittest
    reg=check(read(OUT/'registration.json'));module=load(TEST,'prebound_tests')
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(module.PreboundExpectationCodeTests)
    assert [test.id() for test in suite]==reg['unit_nodes']
    def emit(value):sys.stdout.buffer.write(canonical(value)+b'\n');sys.stdout.buffer.flush()
    emit(['admission',dict(nodes=reg['unit_nodes'],before_test_calls=True)])
    class Witness(unittest.TextTestResult):
        def startTest(self,test):emit(['test_start',test.id()]);super().startTest(test)
        def stopTest(self,test):super().stopTest(test);emit(['test_end',test.id()])
    result=unittest.TextTestRunner(verbosity=2,resultclass=Witness).run(suite);check(reg)
    report=dict(accepted=result.wasSuccessful() and result.testsRun==4 and not result.skipped,tests_run=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped))
    emit(['report',report]);raise SystemExit(0 if report['accepted'] else 1)


def saved(reg):
    row=read(OUT/'unittest.exit.json');assert row['accepted'] is True;payload=row['payload']
    stdout=base64.b64decode(payload['stdout_raw_base64'],validate=True);stderr=base64.b64decode(payload['stderr_raw_base64'],validate=True)
    assert pin(stdout)==payload['stdout_pin'] and pin(stderr)==payload['stderr_pin']
    report=parse_unit(stdout,reg);obs=payload['observation'];drain=obs['bounded_drain']
    assert payload['returncode']==0 and payload['capture_error'] is None and obs['handle_closed'] and not obs['cleanup']
    assert drain['pipes_closed'] and drain['reader_threads_terminal'] and not drain['killed'] and not drain['reader_errors'] and not drain['cleanup']
    assert not drain['stdout_truncated'] and not drain['stderr_truncated']
    load(MEMORY,'_saved_bridge_memory').validate_guard(drain['memory_guard'])
    return dict(accepted=True,unit_exit_pin=pin((OUT/'unittest.exit.json').read_bytes()),unit_report=report,
        derivation_pin=pin(canonical(reg['derivation'])),P1_reads=0,cold_calls=0,source49_modules_executed=0,**flags())


def run(action):
    started=time.perf_counter();assert action in CAPS
    path=OUT/('registration.json' if action=='register' else 'checkpoint.json' if action=='checkpoint' else action+'.exit.json')
    assert not path.exists();payload={};error=None;accepted=False
    try:
        if action=='register':
            prior,inputs,archive=previous()
            for item in own():
                if item.suffix=='.py':compile(item.read_bytes(),str(item),'exec',dont_inherit=True,optimize=0)
            _,derivation=load(BUILDER,'_registration_prebound_builder').current()
            inputs.update({str(item):pin(item.read_bytes()) for item in own()})
            payload=dict(input_pins=inputs,effective_input_count=len(inputs),archive_pins=archive,own_input_pins={str(item):pin(item.read_bytes()) for item in own()},
                derivation=derivation,unit_nodes=nodes(),python_optimized=False,previous_checkpoint_pin=pin((PRIOR/'checkpoint.json').read_bytes()))
        elif action=='checkpoint':
            prior,_,_=previous();records={item.name:read(item) for item in OUT.glob('*.exit.json')}
            if (OUT/'registration.json').exists():records['registration.json']=read(OUT/'registration.json')
            failed=[name for name,value in records.items() if value['accepted'] is False]
            if not failed:
                assert set(records)=={'registration.json','unittest.exit.json','pre_seal.exit.json','saved.exit.json'}
                reg=check(records['registration.json']);assert canonical(saved(reg))==canonical(records['saved.exit.json']['payload'])
            payload=dict(diagnostic_accepted=not failed,acceptance_scope='source_derived_prebound_capture_code_only' if not failed else 'rejection_metadata_only',
                scope_charged_seconds={kind:sum(value['charged_seconds'] for value in records.values() if value['kind']==kind) for kind in ('static','unittest')},
                previous_cumulative=prior['all_cumulative_charged_seconds'],prior_not_accepted_count=39+len(failed),
                artifact_pins={str(item):pin(item.read_bytes()) for item in OUT.iterdir()},P1_reads=0,cold_calls=0,source49_modules_executed=0)
        else:
            reg=check(read(OUT/'registration.json'))
            if action=='unittest':
                capture=load(CAPTURE,'_bridge_sampled_capture')
                rc,out,err,why,obs=capture.bounded([EXE,'-B','-s',str(Path(__file__).absolute()),'unit_child'],8.)
                payload=dict(returncode=rc,capture_error=why,observation=obs,stdout_raw_base64=base64.b64encode(out).decode(),stderr_raw_base64=base64.b64encode(err).decode(),stdout_pin=pin(out),stderr_pin=pin(err))
                assert rc==0 and why is None and obs['handle_closed'] and not obs['cleanup'];payload['unit_report']=parse_unit(out,reg)
            elif action=='pre_seal':
                raw=sys.stdin.buffer.read(32769);assert len(raw)<=32768;finding=json.loads(raw);assert canonical(finding)==raw
                assert finding['must_fix_open']==[] and finding['official_review'] is False
                assert finding['registration_pin']==pin((OUT/'registration.json').read_bytes()) and finding['unit_exit_pin']==pin((OUT/'unittest.exit.json').read_bytes())
                assert finding['own_input_pins']==reg['own_input_pins'] and finding['verified_input_count']==reg['effective_input_count']
                assert read(OUT/'unittest.exit.json')['accepted'] is True;payload=dict(findings=finding)
            else:
                assert read(OUT/'pre_seal.exit.json')['accepted'] is True;payload=saved(reg)
            check(reg)
        accepted=True
    except BaseException as caught:error=type(caught).__name__+':'+str(caught)
    charge=time.perf_counter()-started;accepted=accepted and charge<=CAPS[action]
    record=dict(accepted=accepted,authority='DRAFT_NONAUTHORITATIVE',action=action,kind='unittest' if action=='unittest' else 'static',
        charged_seconds=charge,cap_seconds=CAPS[action],error=error,payload=payload,**flags())
    if action=='register' and accepted:record.update(payload)
    if action=='checkpoint':
        usage=payload['scope_charged_seconds'];usage['static']+=charge
        cumulative={**payload['previous_cumulative']}
        for kind in usage:cumulative[kind]+=usage[kind]
        accepted=accepted and usage['static']<=25 and usage['unittest']<=15 and sum(usage.values())<=40
        record.update(payload,accepted=accepted,all_cumulative_charged_seconds=cumulative,all_cumulative_total_seconds=sum(cumulative.values()),
            package_charged_seconds=sum(usage.values()),prior_not_accepted_count=payload['prior_not_accepted_count']+(not accepted))
    save(path,record);print(canonical(dict(action=action,accepted=accepted,charge=charge,error=error)).decode())
    if not accepted:raise SystemExit(1)


if __name__=='__main__':
    if sys.argv[1]=='unit_child':unit_child()
    else:run(sys.argv[1])
