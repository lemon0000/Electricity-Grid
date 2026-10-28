"""Finite source-derived producer bridge validation; no P1 or cold execution."""
import ast
import base64
from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path
import sys
import time

if sys.flags.optimize!=0:raise RuntimeError('unoptimized bridge validation required')
OUT=Path(__file__).absolute().parent;ROOT=OUT.parents[2]
PRIOR=ROOT/'results/tables/staged_rts24_saved_fresh_full_producer_bridge_v2_non_authoritative'
BUILDER=ROOT/'experiments/staged_rts24_saved_fresh_prebound_expectation_code_v3.py'
TEST=ROOT/'tests/test_staged_rts24_saved_fresh_prebound_expectation_code_v3.py'
CONTROLLER_TEST=ROOT/'tests/test_staged_rts24_saved_fresh_full_producer_bridge_controller_v3.py'
SCOPE=ROOT/'docs/plan/staged_deliverability_c_saved_fresh_full_producer_bridge_scope_v3.md'
CAPTURE=ROOT/'experiments/staged_rts24_saved_fresh_sampled_capture_v1.py'
MEMORY=ROOT/'experiments/staged_rts24_saved_fresh_memory_drain_v1.py'
EXE='D:/Miniconda3/envs/compute/python.exe'
CAPS=dict(register=5,unittest=10,pre_seal=5,saved=5,checkpoint=5)
PHASES=('register','unittest','pre_seal','saved')
CHECKPOINT_SHA='2f3b0532882f8050bdf2e3f236f0a9cb61b3250710c602d1da7e4e64c571b843'
INHERITED_COUNT=1195;OWN_COUNT=7;OWN_OVERLAP=2;INPUT_COUNT=1200
ARCHIVE_COUNT=162;ARCHIVE_BYTES=15020446
TOTAL_CAPS=dict(static=25,unittest=15)
FALSE_FIELDS=('producer_capability_verified','full_runtime_binding_verified','full_P1_content_verified','role_bootstrap',
    'permit_issued','run_authority','resource_admission','scientific_evidence_adopted','formal_result','actual_F','production_seal')


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def read(path):return json.loads(path.read_bytes())
def flags():return {key:False for key in FALSE_FIELDS}
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def own():return (BUILDER,TEST,CONTROLLER_TEST,SCOPE,CAPTURE,MEMORY,Path(__file__).absolute())
def output(action):return OUT/('registration.json' if action=='register' else 'checkpoint.json' if action=='checkpoint' else action+'.exit.json')
def merge_pins(target,items):
    for path,value in items.items():
        if path in target:assert target[path]==value,path
        target[path]=value


def save(path,value):
    raw=canonical(value);assert path.parent==OUT and not path.exists() and len(raw)<=1048576
    files=list(OUT.iterdir());assert all(path.is_file() for path in files) and len(files)+1<=10
    reserve=0 if path.name=='checkpoint.json' or (OUT/'checkpoint.json').exists() else 1048576
    assert len(files)+1+bool(reserve)<=10
    assert sum(path.stat().st_size for path in files)+len(raw)+reserve<=4194304
    with path.open('xb') as stream:stream.write(raw)


def predecessor_accounting():
    raw=(PRIOR/'checkpoint.json').read_bytes();assert pin(raw)['sha256']==CHECKPOINT_SHA
    cp=json.loads(raw);assert cp['accepted'] is True and cp['diagnostic_accepted'] is False and cp['accounting_complete'] is True
    assert cp['all_cumulative_total_seconds']==1106.1366582000148 and cp['prior_not_accepted_count']==41
    assert cp['all_cumulative_charged_seconds']==dict(static=536.7907461000098,pytest=366.48897970000326,unittest=202.85693240000182)
    return cp


def archive_map(paths,expected):
    keys=[str(path) for path in paths]
    assert len(keys)==len(set(keys))==len({str(path.resolve()).casefold() for path in paths})==ARCHIVE_COUNT,'archive paths must be unique'
    result={str(path):pin(path.read_bytes()) for path in paths}
    assert len(result)==ARCHIVE_COUNT and sum(value['bytes'] for value in result.values())==ARCHIVE_BYTES,'archive bounds differ'
    assert result==expected,'archive exact set or pins differ'
    return result


def previous():
    cp=predecessor_accounting()
    prior_root={path:value for path,value in cp['known_pins'].items() if Path(path).parent==PRIOR}
    prior_root[str(PRIOR/'checkpoint.json')]=pin((PRIOR/'checkpoint.json').read_bytes())
    assert len(prior_root)==4 and set(prior_root)=={str(path) for path in PRIOR.iterdir()}
    for path,value in prior_root.items():assert pin(Path(path).read_bytes())==value,path
    failed=load(PRIOR/'driver.py','_frozen_rejected_bridge_inputs')
    assert failed.connected_inputs.__code__.replace(co_filename=connected_inputs.__code__.co_filename,
        co_firstlineno=connected_inputs.__code__.co_firstlineno)==connected_inputs.__code__,'connected input validator drift'
    _,inputs,expected=failed.previous();assert len(inputs)==1187 and len(expected)==158
    archive=[Path(path) for path in expected]
    failed_own={str(path):cp['known_pins'][str(path)] for path in failed.own()}
    assert len(failed_own)==7
    for path,value in failed_own.items():assert pin(Path(path).read_bytes())==value,path
    registration=read(PRIOR/'registration.json')
    assert registration['accepted'] is True and registration['effective_input_count']==1192
    assert registration['input_pins']=={**inputs,**failed_own}
    unit=read(PRIOR/'unittest.exit.json');assert unit['accepted'] is False and unit['error']=='phase_cap_exceeded'
    merge_pins(inputs,failed_own);merge_pins(inputs,prior_root);assert len(inputs)==INHERITED_COUNT
    archive.extend(PRIOR.iterdir());merge_pins(expected,prior_root)
    return cp,inputs,archive_map(archive,expected)


def connected_inputs(inherited,registration):
    assert len(inherited)==1157 and pin(canonical(inherited))==registration['inherited_effective_pins_pin']
    assert len(registration['input_pins'])==360 and registration['effective_input_count']==1167,'connected registration counts differ'
    result=dict(inherited);merge_pins(result,registration['input_pins'])
    assert len(result)==1167,'connected effective set differs'
    return result


def input_maps(inherited):
    own_pins={str(path):pin(path.read_bytes()) for path in own()}
    assert len(inherited)==INHERITED_COUNT and len(own_pins)==OWN_COUNT
    assert len(set(inherited)&set(own_pins))==OWN_OVERLAP
    result=dict(inherited);merge_pins(result,own_pins)
    assert len(result)==INPUT_COUNT==INHERITED_COUNT+OWN_COUNT-OWN_OVERLAP
    return result,own_pins


def nodes():
    result=[]
    for path,module,clsname,count in ((TEST,'prebound_tests','PreboundExpectationCodeTests',4),
            (CONTROLLER_TEST,'bridge_controller_tests','BridgeControllerTests',12)):
        cls=next(node for node in ast.parse(path.read_bytes()).body if type(node) is ast.ClassDef and node.name==clsname)
        names=[node.name for node in cls.body if type(node) is ast.FunctionDef and node.name.startswith('test_')]
        assert len(names)==len(set(names))==count
        result.extend(sorted(module+'.'+clsname+'.'+name for name in names))
    return result


def check(reg):
    assert reg['accepted'] is True and reg['python_optimized'] is False
    _,inherited,archive=previous();inputs,own_pins=input_maps(inherited)
    assert reg['input_pins']==inputs and reg['effective_input_count']==INPUT_COUNT,'exact input set differs'
    assert reg['archive_pins']==archive and reg['prior_archive_files']==ARCHIVE_COUNT and reg['prior_archive_bytes']==ARCHIVE_BYTES,'exact archive differs'
    assert reg['previous_checkpoint_pin']==pin((PRIOR/'checkpoint.json').read_bytes())
    _,report=load(BUILDER,'_checked_prebound_builder').current()
    assert canonical(report)==canonical(reg['derivation']) and reg['unit_nodes']==nodes()
    assert reg['own_input_pins']==own_pins
    assert all(reg[key] is False for key in FALSE_FIELDS)
    return reg


def parse_unit(raw,reg):
    lines=raw.splitlines(keepends=True);frames=[json.loads(line) for line in lines]
    assert all(canonical(frame)+b'\n'==line for frame,line in zip(frames,lines))
    assert len(frames)==2+2*len(reg['unit_nodes']) and frames[0]==['admission',dict(nodes=reg['unit_nodes'],before_test_calls=True)]
    for index,name in enumerate(reg['unit_nodes']):assert frames[1+index*2:3+index*2]==[['test_start',name],['test_end',name]]
    assert frames[-1]==['report',dict(accepted=True,tests_run=len(reg['unit_nodes']),failures=0,errors=0,skipped=0)]
    return frames[-1][1]


def unit_child():
    import unittest
    phase_records('unittest');reg=check(read(OUT/'registration.json'))
    suite=unittest.TestSuite()
    for path,name,cls in ((TEST,'prebound_tests','PreboundExpectationCodeTests'),(CONTROLLER_TEST,'bridge_controller_tests','BridgeControllerTests')):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(getattr(load(path,name),cls)))
    assert [test.id() for test in suite]==reg['unit_nodes']
    def emit(value):sys.stdout.buffer.write(canonical(value)+b'\n');sys.stdout.buffer.flush()
    emit(['admission',dict(nodes=reg['unit_nodes'],before_test_calls=True)])
    class Witness(unittest.TextTestResult):
        def startTest(self,test):emit(['test_start',test.id()]);super().startTest(test)
        def stopTest(self,test):super().stopTest(test);emit(['test_end',test.id()])
    result=unittest.TextTestRunner(verbosity=2,resultclass=Witness).run(suite);check(reg)
    report=dict(accepted=result.wasSuccessful() and result.testsRun==len(reg['unit_nodes']) and not result.skipped,tests_run=result.testsRun,
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


def parse_record(raw):
    def unique(items):
        result={}
        for key,value in items:
            assert key not in result,'duplicate record key'
            result[key]=value
        return result
    return json.loads(raw,object_pairs_hook=unique)


def charge_fields(row,action):
    assert row['action']==action and row['authority']=='DRAFT_NONAUTHORITATIVE'
    assert row['kind']==('unittest' if action=='unittest' else 'static') and row['cap_seconds']==CAPS[action]
    charge=row['charged_seconds'];assert type(charge) in (float,int) and math.isfinite(charge) and charge>=0
    return row


def record_fields(row,action):
    charge_fields(row,action)
    assert type(row['accepted']) is bool and all(row[key] is False for key in FALSE_FIELDS)
    if row['accepted']:assert row['error'] is None and row['charged_seconds']<=CAPS[action]
    return row


def checked_record(path,action):
    raw=path.read_bytes();row=record_fields(parse_record(raw),action)
    assert canonical(row)==raw,'record is not canonical'
    return row


def phase_records(action):
    paths={output(name).name:name for name in PHASES}
    present={path.name for path in OUT.iterdir()}
    assert present<=set(paths)|{'driver.py'} and 'driver.py' in present,'unexpected or terminal root'
    records={name:checked_record(OUT/name,phase) for name,phase in paths.items() if name in present}
    names=[name for name in PHASES if output(name).name in records]
    assert names==list(PHASES[:len(names)]),'strict phase prefix required'
    if action=='checkpoint':
        assert names and (len(names)==len(PHASES) or records[output(names[-1]).name]['accepted'] is False),'unfinished accepted prefix'
        assert all(records[output(name).name]['accepted'] is True for name in names[:-1]),'phase continued after rejection'
    else:
        assert names==list(PHASES[:PHASES.index(action)]),'predecessor phases required'
        assert all(row['accepted'] is True for row in records.values()),'rejected prefix is terminal'
    usage={kind:sum(row['charged_seconds'] for row in records.values() if row['kind']==kind) for kind in TOTAL_CAPS}
    kind='unittest' if action=='unittest' else 'static'
    assert usage[kind]+CAPS[action]<=TOTAL_CAPS[kind] and sum(usage.values())+CAPS[action]<=40,'insufficient scope budget'
    return records


def known_pins():
    result={};errors=[]
    for path in (*own(),PRIOR/'checkpoint.json',*OUT.iterdir()):
        if str(path) in result:continue
        try:result[str(path)]=pin(path.read_bytes())
        except BaseException as caught:errors.append(str(path)+':'+type(caught).__name__+':'+str(caught))
    return result,errors


def checkpoint_accounting():
    usage={kind:0. for kind in TOTAL_CAPS};errors=[];pins={};failed=[]
    expected={output(name).name:name for name in PHASES}
    for path in OUT.iterdir():
        if path.name=='driver.py':continue
        try:
            raw=path.read_bytes();pins[str(path)]=pin(raw)
            assert path.name in expected,'unknown scope record'
            row=charge_fields(parse_record(raw),expected[path.name]);usage[row['kind']]+=row['charged_seconds']
            if row.get('accepted') is False:failed.append(path.name)
            record_fields(row,expected[path.name])
            assert canonical(row)==raw,'record is not canonical; known charge retained'
        except BaseException as caught:errors.append(path.name+':'+type(caught).__name__+':'+str(caught))
    prior=None
    try:prior=predecessor_accounting()
    except BaseException as caught:errors.append('predecessor:'+type(caught).__name__+':'+str(caught))
    return dict(scope_charged_seconds=usage,scope_accounting_complete=not any(not item.startswith('predecessor:') for item in errors),
        prior_accounting_complete=prior is not None,accounting_errors=errors,charged_record_pins=pins,
        known_scope_not_accepted_records=failed,previous_cumulative=None if prior is None else prior['all_cumulative_charged_seconds'],
        previous_not_accepted_count=None if prior is None else prior['prior_not_accepted_count'])


def run(action):
    assert action in CAPS
    path=output(action);assert not path.exists() and not (OUT/'checkpoint.json').exists(),'create-only terminal scope'
    started=time.perf_counter();payload={};error=None;accepted=False
    try:
        records=phase_records(action)
        if action=='register':
            prior,inputs,archive=previous()
            for item in own():
                if item.suffix=='.py':compile(item.read_bytes(),str(item),'exec',dont_inherit=True,optimize=0)
            _,derivation=load(BUILDER,'_registration_prebound_builder').current()
            inputs,own_pins=input_maps(inputs)
            payload=dict(input_pins=inputs,effective_input_count=INPUT_COUNT,archive_pins=archive,own_input_pins=own_pins,
                prior_archive_files=ARCHIVE_COUNT,prior_archive_bytes=ARCHIVE_BYTES,
                derivation=derivation,unit_nodes=nodes(),python_optimized=False,previous_checkpoint_pin=pin((PRIOR/'checkpoint.json').read_bytes()))
        elif action=='checkpoint':
            failed=[name for name,value in records.items() if value['accepted'] is False]
            if not failed:
                assert set(records)=={'registration.json','unittest.exit.json','pre_seal.exit.json','saved.exit.json'}
                reg=check(records['registration.json']);assert canonical(saved(reg))==canonical(records['saved.exit.json']['payload'])
            else:previous()
            payload=dict(diagnostic_accepted=not failed)
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
    if action=='checkpoint':
        payload.update(checkpoint_accounting())
    if not accepted or action=='checkpoint':
        known,pin_errors=known_pins();payload.update(known_pins=known,pin_errors=pin_errors)
    charge=time.perf_counter()-started;accepted=accepted and charge<=CAPS[action]
    if charge>CAPS[action] and error is None:error='phase_cap_exceeded'
    record=dict(accepted=accepted,authority='DRAFT_NONAUTHORITATIVE',action=action,kind='unittest' if action=='unittest' else 'static',
        charged_seconds=charge,cap_seconds=CAPS[action],error=error,payload=payload,**flags())
    if action=='register' and accepted:record.update(payload)
    if action=='checkpoint':
        usage=payload['scope_charged_seconds'];usage['static']+=charge
        complete=payload['scope_accounting_complete'] and payload['prior_accounting_complete']
        accepted=accepted and complete and not payload['pin_errors'] and all(usage[kind]<=cap for kind,cap in TOTAL_CAPS.items()) and sum(usage.values())<=40
        cumulative=dict(payload['previous_cumulative']) if complete else None
        if complete:
            for kind in usage:cumulative[kind]+=usage[kind]
        diagnostic=accepted and payload.get('diagnostic_accepted') is True
        record.update(payload,accepted=accepted,diagnostic_accepted=diagnostic,error=error,
            acceptance_scope='source_derived_prebound_capture_code_only' if diagnostic else 'rejection_metadata_only',
            accounting_complete=complete,all_cumulative_charged_seconds=cumulative,all_cumulative_total_seconds=None if cumulative is None else sum(cumulative.values()),
            package_charged_seconds=sum(usage.values()),prior_not_accepted_count=None if not complete else payload['previous_not_accepted_count']+len(payload['known_scope_not_accepted_records'])+(not accepted),
            P1_reads=0,cold_calls=0,source49_modules_executed=0)
    save(path,record);print(canonical(dict(action=action,accepted=accepted,charge=charge,error=error)).decode())
    if not accepted:raise SystemExit(1)


if __name__=='__main__':
    if sys.argv[1]=='unit_child':unit_child()
    else:run(sys.argv[1])
