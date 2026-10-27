"""Fixed no-child metadata method package, continuing the original NFC budget."""
import ast
import base64
from hashlib import sha256
import importlib.util
import io
import json
import math
from pathlib import Path
import sys
import time
import zlib

OUT=Path(__file__).absolute().parent;ROOT=OUT.parents[2]
METHOD=ROOT/'experiments/staged_rts24_saved_fresh_pin_memo_v1.py'
TEST=ROOT/'tests/test_staged_rts24_saved_fresh_pin_memo_v1.py'
SCOPE=ROOT/'docs/plan/staged_deliverability_c_saved_fresh_pin_memo_scope_v1.md'
NFC=ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v3_non_authoritative'
TRACE=ROOT/'results/tables/staged_rts24_saved_fresh_nfc_metadata_read_v1_non_authoritative'
V2=ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v2_non_authoritative'
NONE=ROOT/'results/tables/staged_rts24_saved_fresh_image_none_v2_non_authoritative'
FIRST=ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v1_non_authoritative'
PARENT=ROOT/'experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v27.py'
MODULE_PATHS=(NFC/'driver.py',V2/'driver.py',PARENT)
MAX_FILES=8;MAX_BYTES=2520018
CAPS=dict(register=1.5,unittest=.5,benchmark=4.5,saved=1.5,checkpoint=1)
LIMITS={'driver.py':65536,'registration.json':524288,'unittest_admission.json':16384,'unittest.exit.json':65536,
    'pre_seal_findings.json':16384,'benchmark.exit.json':1048576,'saved.exit.json':131072,'checkpoint.json':131072}
FALSE_FIELDS=('external_expected_truth_verified','upstream_owner_verified','parent_independently_authenticated_python_object_graph',
    'startup_tcb_authenticated','independent_root_verified','native_behavior_verified','full_runtime_binding_verified','full_P1_content_verified',
    'role_bootstrap','permit_issued','native_authorized','F_launch_admitted','actual_F','run_authority','scientific_evidence_adopted','resource_admission','formal_result','production_seal',
    'all_unselected_events_verified','candidate_adopted','production_helper_selected')


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def read(path):return json.loads(path.read_bytes())
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def flags():return {k:False for k in FALSE_FIELDS}
def pins(paths):return {str(p):pin(p.read_bytes()) for p in paths}
def packed(raw):return dict(raw_base64=base64.b64encode(raw).decode(),pin=pin(raw))
def unpack(item):
    assert type(item) is dict and set(item)=={'raw_base64','pin'} and type(item['raw_base64']) is str
    valid_pin(item['pin']);raw=base64.b64decode(item['raw_base64'],validate=True);assert pin(raw)==item['pin'];return raw
def valid_pin(value):
    assert type(value) is dict and set(value)=={'bytes','sha256'} and type(value['bytes']) is int and value['bytes']>=0
    assert type(value['sha256']) is str and len(value['sha256'])==64 and all(c in '0123456789abcdef' for c in value['sha256'])
def number(value):assert type(value) is float and math.isfinite(value) and value>=0


def archive():
    roots=[ROOT/f'results/tables/staged_rts24_saved_fresh_nfc_v{i}_non_authoritative' for i in (1,2,3)]+[TRACE]
    files=[p for folder in roots for p in folder.iterdir()];assert len(files)==22 and all(p.is_file() for p in files)
    assert sum(p.stat().st_size for p in files)==1674286 and MAX_FILES+len(files)==30 and MAX_BYTES+1674286==4194304
    return files


def root_evidence():
    raw=(TRACE/'inspection.json').read_bytes();assert sha256(raw).hexdigest()=='5181393e8b0da03d316513d7ba839ea335fe80a77159144b1685bf41534600d1'
    endpoint=json.loads(raw);assert endpoint['accepted'] and endpoint['prior_not_accepted_count']==34 and endpoint['all_cumulative_total_seconds']==776.484504500065
    assert endpoint['original_package_charged_seconds']==14.212736400011636
    return endpoint


def collect_inputs():
    expected={};origins={};images={}
    def add(path,value,origin):
        path=str(Path(path).absolute())
        assert type(value) is dict and set(value)=={'bytes','sha256'} and type(value['bytes']) is int and value['bytes']>=0
        assert type(value['sha256']) is str and len(value['sha256'])==64 and all(c in '0123456789abcdef' for c in value['sha256'])
        if path in expected:assert expected[path]==value,(path,origins[path],origin)
        else:expected[path]=value;origins[path]=origin
    def take(path,sha=None):
        raw=path.read_bytes()
        if sha is not None:assert pin(raw)['sha256']==sha,path
        elif str(path) in expected:assert pin(raw)==expected[str(path)],path
        else:raise AssertionError(('missing fixed JSON binding',str(path)))
        images[str(path)]=raw;return json.loads(raw)
    def mapping(values,origin,prefix=None):
        for name,value in values.items():add((prefix/name) if prefix is not None else name,value,origin)
    current=take(NFC/'checkpoint.json','dd669b1f06ce7e5e174ebd5c9cc8f0fc6b2fcebdd6fbe84ae8b69bfd15b28731')
    mapping(current['root_map_before_checkpoint'],'NFC3 checkpoint',NFC)
    add(NFC/'checkpoint.json',pin(images[str(NFC/'checkpoint.json')]),'fixed NFC3 endpoint')
    reg=take(NFC/'registration.json');mapping(reg['input_pins'],'NFC3 input');mapping(reg['helper_pins'],'NFC3 helper');mapping(reg['source_pins'],'Source49',ROOT)
    size=take(NFC/'size_admission.json');mapping(size['input_pins'],'NFC3 size')
    cp=take(V2/'checkpoint.json','5cb9ce80769e5b4fdf36ac74a4047328ad11b36d312af9b012f7802c71f6ef4f')
    mapping(cp['root_map_before_checkpoint'],'NFC2 checkpoint',V2);add(V2/'checkpoint.json',pin(images[str(V2/'checkpoint.json')]),'fixed NFC2 endpoint')
    old=take(V2/'registration.json');mapping(old['input_pins'],'NFC2 input');mapping(old['helper_pins'],'NFC2 helper')
    mapping(take(V2/'size_admission.json')['input_pins'],'NFC2 size')
    cp=take(NONE/'checkpoint.exit.json','9e6e4592204a28697004c1d06bf0b027496954cb9e48bfcb7502a49690e950aa')
    mapping(cp['artifact_pins'],'None2 checkpoint');add(NONE/'checkpoint.exit.json',pin(images[str(NONE/'checkpoint.exit.json')]),'fixed None2 endpoint')
    nr=take(NONE/'registration.json');mapping(nr['input_pins'],'None2 input');mapping(nr['helper_pins'],'None2 helper')
    cp=take(FIRST/'checkpoint.json','f5c99fc1731a43aaa17e883c4b114ef98c2191b7f3492738906b132dd2de4b84')
    mapping(cp['root_map_before_checkpoint'],'NFC1 checkpoint',FIRST);add(FIRST/'checkpoint.json',pin(images[str(FIRST/'checkpoint.json')]),'fixed NFC1 endpoint')
    mapping(take(FIRST/'size_admission.json')['input_pins'],'NFC1 size')
    endpoint=root_evidence();mapping(endpoint['input_pins'],'trace inputs')
    add(TRACE/'inspection.json',pin((TRACE/'inspection.json').read_bytes()),'fixed trace endpoint')
    for p in archive():
        assert str(p) in expected,p
        assert pin(p.read_bytes())==expected[str(p)],p
    own=[METHOD,TEST,SCOPE,Path(__file__).absolute()]
    for p in own:add(p,pin(p.read_bytes()),'this draft prerun')
    for path,value in expected.items():assert pin(Path(path).read_bytes())==value,path
    assert len(reg['source_pins'])==49 and reg['source_epoch']=='acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875'
    return expected,origins,reg


def space(additions):
    current={p.name:p.stat().st_size for p in OUT.iterdir() if p.is_file()};assert len(current)==len(list(OUT.iterdir()))
    reserve={} if 'checkpoint.json' in current or 'checkpoint.json' in additions else {'checkpoint.json':131072}
    assert not set(additions)&set(current)
    assert len(current)+len(additions)+len(reserve)<=MAX_FILES and sum(current.values())+sum(additions.values())+sum(reserve.values())<=MAX_BYTES
def save(path,value):
    raw=canonical(value);assert path.parent==OUT and len(raw)<=LIMITS[path.name];space({path.name:len(raw)})
    with path.open('xb') as stream:stream.write(raw)


def check(reg,unit=False):
    endpoint=root_evidence();assert pin((TRACE/'inspection.json').read_bytes())==reg['predecessor_pin']
    selected=reg['unit_input_pins'] if unit else reg['input_pins']
    assert reg['unit_input_pins']=={str(p):reg['input_pins'][str(p)] for p in (METHOD,TEST,SCOPE,Path(__file__).absolute())}
    for path,value in selected.items():assert pin(Path(path).read_bytes())==value,path
    for path,item in reg['source_snapshots'].items():
        raw=unpack(item);assert pin(raw)==reg['input_pins'][path]
        if not unit:assert Path(path).read_bytes()==raw,path
    origins=trace_open(reg['input_origins']);assert set(origins)==set(reg['input_pins']) and all(type(value) is str and value for value in origins.values())
    archive();return endpoint


def spent(extra=0,kind='static'):
    result=dict(static=read(OUT/'registration.json')['charged_seconds'],unittest=0.0)
    for p in OUT.glob('*.exit.json'):row=read(p);result[row['kind']]+=row['charged_seconds']
    result[kind]+=extra;return result


def terminal(name,started,accepted,error,details,reg,kind='static'):
    charge=time.perf_counter()-started;usage=spent(charge,kind)
    accepted=accepted and charge<=CAPS[name] and usage['static']<=8.5 and usage['unittest']<=.5 and sum(usage.values())<=9
    previous=root_evidence();cumulative={**previous['all_cumulative_charged_seconds'],'static':previous['all_cumulative_charged_seconds']['static']+usage['static'],'unittest':previous['all_cumulative_charged_seconds']['unittest']+usage['unittest']}
    save(OUT/(name+'.exit.json'),dict(accepted=accepted,label=name,authority='DRAFT_NONAUTHORITATIVE',kind=kind,charged_seconds=charge,cap_seconds=CAPS[name],scope_charged_seconds=usage,
        all_cumulative_charged_seconds=cumulative,all_cumulative_total_seconds=sum(cumulative.values()),prior_not_accepted_count=34+sum(not read(p)['accepted'] for p in OUT.glob('*.exit.json'))+(not accepted),
        registration_pin=pin((OUT/'registration.json').read_bytes()),artifact_pins=pins(p for p in OUT.iterdir() if p.is_file()),error=error,details=details,unit_children_launched=0,cold_children_launched=0,**flags()))
    print(canonical(dict(accepted=accepted,label=name,charge=charge,error=error)).decode())
    if not accepted:raise SystemExit(1)


def register(started=None):
    if started is None:started=time.perf_counter()
    assert {p.name for p in OUT.iterdir()}=={'driver.py'}
    inputs,origins,source=collect_inputs();nodes=sorted('pin_memo_tests.PinMemoTests.'+n.name for n in ast.walk(ast.parse(TEST.read_bytes())) if type(n) is ast.FunctionDef and n.name.startswith('test_'));assert len(nodes)==8
    snapshots={str(p):packed(p.read_bytes()) for p in (METHOD,TEST,SCOPE,Path(__file__).absolute())}
    unit_inputs={str(p):inputs[str(p)] for p in (METHOD,TEST,SCOPE,Path(__file__).absolute())}
    value=dict(accepted=False,authority='DRAFT_NONAUTHORITATIVE',kind='static',charged_seconds=0.0,cap_seconds=1.5,
        input_pins=inputs,input_origins=trace_blob(origins),unit_input_pins=unit_inputs,source_snapshots=snapshots,source_pins=source['source_pins'],source_epoch=source['source_epoch'],unit_nodes=nodes,
        reference_source_pins={str(p):inputs[str(p)] for p in MODULE_PATHS},
        predecessor_pin=pin((TRACE/'inspection.json').read_bytes()),caps=dict(static=8.5,unittest=.5,total=9,files=8,bytes=2520018),**flags())
    charge=time.perf_counter()-started;accepted=charge<=1.5;value.update(accepted=accepted,charged_seconds=charge);save(OUT/'registration.json',value)
    print(canonical(dict(accepted=accepted,charge=charge,inputs=len(inputs),tests=8)).decode())
    if not accepted:raise SystemExit(1)


def unittest_phase():
    import unittest
    started=time.perf_counter();reg=read(OUT/'registration.json');accepted=False;error=None;details={}
    try:
        assert reg['accepted'] and {p.name for p in OUT.iterdir()}=={'driver.py','registration.json'}
        check(reg,True);module=load(TEST,'pin_memo_tests');suite=unittest.defaultTestLoader.loadTestsFromModule(module)
        def nodes(s):return [n for c in s for n in nodes(c)] if isinstance(s,unittest.TestSuite) else [s.id()]
        assert nodes(suite)==reg['unit_nodes'];admission=dict(nodes=reg['unit_nodes'],before_test_calls=True,source_pins=reg['unit_input_pins'])
        save(OUT/'unittest_admission.json',admission)
        stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
        details=dict(report=dict(accepted=result.wasSuccessful() and result.testsRun==8 and not result.skipped,tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped)),
            stderr=packed(stream.getvalue().encode()),admission_pin=pin((OUT/'unittest_admission.json').read_bytes()))
        assert details['report']['accepted'];check(reg,True);accepted=True
    except BaseException as caught:error=type(caught).__name__+':'+str(caught)[:240]
    terminal('unittest',started,accepted,error,details,reg,'unittest')


def trace_blob(rows):
    raw=canonical(rows);compressed=zlib.compress(raw,9)
    return dict(encoding='zlib_canonical_json',raw_pin=pin(raw),compressed=packed(compressed))
def trace_open(value):
    assert type(value) is dict and set(value)=={'encoding','raw_pin','compressed'} and value['encoding']=='zlib_canonical_json';valid_pin(value['raw_pin'])
    compressed=unpack(value['compressed']);decoder=zlib.decompressobj();raw=decoder.decompress(compressed,4194305)
    assert len(raw)<=4194304 and decoder.eof and not decoder.unconsumed_tail and not decoder.unused_data and pin(raw)==value['raw_pin']
    rows=json.loads(raw);assert canonical(rows)==raw;return rows


def expected_trace():
    endpoint=root_evidence();compressed=base64.b64decode(endpoint['journal_zlib_base64'],validate=True);assert pin(compressed)==endpoint['journal_compressed_pin']
    decoder=zlib.decompressobj();raw=decoder.decompress(compressed,4194305)
    assert decoder.eof and not decoder.unconsumed_tail and not decoder.unused_data and pin(raw)==endpoint['journal_raw_pin']
    return [[p,n] for p,n,sha in json.loads(raw)]


def validate_unit(details,admission,reg):
    assert type(details) is dict and set(details)=={'report','stderr','admission_pin'}
    assert admission==dict(nodes=reg['unit_nodes'],before_test_calls=True,source_pins=reg['unit_input_pins']) and admission['before_test_calls'] is True
    report=details['report'];assert set(report)=={'accepted','tests_run','failures','errors','skipped'} and report['accepted'] is True
    for name,count in (('tests_run',8),('failures',0),('errors',0),('skipped',0)):assert type(report[name]) is int and report[name]==count
    stderr=unpack(details['stderr']).decode('utf-8');assert stderr.endswith('\nOK\n') and 'Ran 8 tests in ' in stderr
    for node in reg['unit_nodes']:assert node+') ... ok\n' in stderr,node
    assert details['admission_pin']==pin(canonical(admission))
    return report


def validate_benchmark(details,baseline,require_complete=True):
    assert type(details) is dict and type(details['cases']) is list
    cases=details['cases'];assert len(cases)<=4 and [c['variant'] for c in cases]==['old','new','new','old'][:len(cases)]
    for case in cases:
        assert set(case)=={'variant','elapsed_seconds','accepted','error','read_calls','trace_equal','trace','metrics'}
        number(case['elapsed_seconds']);assert type(case['accepted']) is bool and type(case['trace_equal']) is bool
        assert case['error'] is None or type(case['error']) is str
        rows=trace_open(case['trace']);assert type(rows) is list and len(rows)<=8192
        for row in rows:assert type(row) is list and len(row)==2 and type(row[0]) is str and type(row[1]) is int and row[1]>=0
        assert type(case['read_calls']) is int and case['read_calls']==len(rows) and case['trace_equal'] is (rows==baseline)
        if case['accepted']:
            assert case['error'] is None and case['elapsed_seconds']<=2 and case['trace_equal'] and len(rows)==2496
        elif require_complete:raise AssertionError('failed benchmark case')
        metrics=case['metrics']
        if case['variant']=='old':assert metrics is None
        elif metrics is not None:
            assert set(metrics)==set(('calls','hits','misses','fallbacks','entries','resident_bytes','max_entries','max_bytes','closed','wrapped_modules','cache_closed_after_check','resident_bytes_after_check','entries_after_check'))
            for name in ('calls','hits','misses','fallbacks','entries','resident_bytes','max_entries','max_bytes','wrapped_modules','resident_bytes_after_check','entries_after_check'):assert type(metrics[name]) is int and metrics[name]>=0
            assert metrics['calls']==metrics['hits']+metrics['misses'] and metrics['fallbacks']<=metrics['misses']
            assert metrics['entries']<=metrics['misses'] and metrics['entries']<=metrics['max_entries']==2048
            assert metrics['resident_bytes']<=metrics['max_bytes']==67108864
            assert metrics['closed'] is False and metrics['cache_closed_after_check'] is True and metrics['resident_bytes_after_check']==metrics['entries_after_check']==0
            if case['accepted']:assert metrics['hits']>0 and metrics['wrapped_modules']>=2
        elif require_complete:raise AssertionError('missing pin memo recovery metrics')
    if require_complete:
        assert len(cases)==4 and set(details)==set(('cases','total_ratio_new_over_old','pair_ratios','filesystem_reads_cached','json_or_module_or_execution_code_cached','original_read_sequence_preserved','extra_read_SHA_in_trace','verification_code_reference_only'))
        assert details['filesystem_reads_cached'] is False and details['json_or_module_or_execution_code_cached'] is False and details['original_read_sequence_preserved'] is True and details['extra_read_SHA_in_trace'] is False and details['verification_code_reference_only'] is True
        old=sum(c['elapsed_seconds'] for c in cases if c['variant']=='old');new=sum(c['elapsed_seconds'] for c in cases if c['variant']=='new');assert old>0
        ratio=new/old;number(details['total_ratio_new_over_old']);assert details['total_ratio_new_over_old']==ratio
        pairs=[cases[1]['elapsed_seconds']/cases[0]['elapsed_seconds'],cases[2]['elapsed_seconds']/cases[3]['elapsed_seconds']]
        assert type(details['pair_ratios']) is list and len(details['pair_ratios'])==2
        for actual,expected in zip(details['pair_ratios'],pairs):number(actual);assert actual==expected
        return dict(unit_tests=8,read_trace_reopened=True,read_calls_each=2496,total_ratio_new_over_old=ratio,method_only=True,**flags())
    return None


def verify_evidence(reg,next_phase=None):
    names={p.name for p in OUT.iterdir()};assert names<=set(LIMITS) and 'checkpoint.json' not in names
    expected={'driver.py','registration.json'};records=[];failed=not reg['accepted'];usage=dict(static=reg['charged_seconds'],unittest=0.0)
    number(reg['charged_seconds']);assert type(reg['accepted']) is bool
    assert reg['authority']=='DRAFT_NONAUTHORITATIVE'
    for name in FALSE_FIELDS:assert reg[name] is False
    if failed:assert names==expected;return dict(diagnostic_accepted=False,failures=1,usage=usage,summary=None)
    endpoint=root_evidence();summary=None;baseline=None
    for name in ('unittest','benchmark','saved'):
        if name=='unittest' and 'unittest_admission.json' in names:expected.add('unittest_admission.json')
        if name=='benchmark' and 'pre_seal_findings.json' in names:
            assert records and records[-1]['accepted'];findings=read(OUT/'pre_seal_findings.json')
            assert findings['must_fix_open']==[] and findings['official_review'] is False
            assert findings['registration_pin']==pin((OUT/'registration.json').read_bytes()) and findings['unittest_exit_pin']==pin((OUT/'unittest.exit.json').read_bytes()) and findings['method_pin']==pin(METHOD.read_bytes())
            expected.add('pre_seal_findings.json')
        path=OUT/(name+'.exit.json')
        if not path.exists():break
        assert not failed
        if name=='benchmark':assert 'pre_seal_findings.json' in expected
        row=read(path);number(row['charged_seconds']);assert type(row['accepted']) is bool
        keys={'accepted','label','authority','kind','charged_seconds','cap_seconds','scope_charged_seconds','all_cumulative_charged_seconds','all_cumulative_total_seconds','prior_not_accepted_count','registration_pin','artifact_pins','error','details','unit_children_launched','cold_children_launched'}|set(FALSE_FIELDS)
        assert set(row)==keys and row['label']==name and row['authority']=='DRAFT_NONAUTHORITATIVE' and row['cap_seconds']==CAPS[name]
        assert row['kind']==('unittest' if name=='unittest' else 'static')
        assert row['error'] is None or type(row['error']) is str
        assert row['registration_pin']==pin((OUT/'registration.json').read_bytes())
        assert set(row['artifact_pins'])=={str(OUT/p) for p in expected}
        for p,value in row['artifact_pins'].items():valid_pin(value);assert pin(Path(p).read_bytes())==value,p
        for field in FALSE_FIELDS:assert row[field] is False
        for field in ('unit_children_launched','cold_children_launched'):assert type(row[field]) is int and row[field]==0
        usage[row['kind']]+=row['charged_seconds'];assert set(row['scope_charged_seconds'])==set(usage)
        for field,value in usage.items():number(row['scope_charged_seconds'][field]);assert abs(row['scope_charged_seconds'][field]-value)<1e-9
        cumulative={**endpoint['all_cumulative_charged_seconds'],'static':endpoint['all_cumulative_charged_seconds']['static']+usage['static'],'unittest':endpoint['all_cumulative_charged_seconds']['unittest']+usage['unittest']}
        assert row['all_cumulative_charged_seconds']==cumulative and row['all_cumulative_total_seconds']==sum(cumulative.values())
        assert type(row['prior_not_accepted_count']) is int and row['prior_not_accepted_count']==34+int(not row['accepted'])
        if row['accepted']:assert row['error'] is None and row['charged_seconds']<=CAPS[name]
        if name=='unittest':
            if row['accepted']:
                assert 'unittest_admission.json' in expected;validate_unit(row['details'],read(OUT/'unittest_admission.json'),reg)
            elif 'stderr' in row['details']:unpack(row['details']['stderr'])
        elif name=='benchmark':
            baseline=expected_trace();assert len(baseline)==2496
            summary=validate_benchmark(row['details'],baseline,row['accepted'])
        elif row['accepted']:assert row['details']==summary and summary is not None
        records.append(row);expected.add(path.name);failed=not row['accepted']
    assert names==expected
    diagnostic=not failed and len(records)==3
    if not diagnostic and not failed:
        assert next_phase in ('benchmark','saved') and len(records)==(1 if next_phase=='benchmark' else 2)
    return dict(diagnostic_accepted=diagnostic,failures=int(failed),usage=usage,summary=summary)


def benchmark():
    started=time.perf_counter();reg=read(OUT/'registration.json');accepted=False;error=None;details=dict(cases=[])
    original=Path.read_bytes
    try:
        assert {p.name for p in OUT.iterdir()}=={'driver.py','registration.json','unittest_admission.json','unittest.exit.json','pre_seal_findings.json'}
        unit=read(OUT/'unittest.exit.json');assert unit['accepted'];summary=read(OUT/'pre_seal_findings.json')
        assert summary['must_fix_open']==[] and summary['official_review'] is False and summary['registration_pin']==pin((OUT/'registration.json').read_bytes())
        assert summary['unittest_exit_pin']==pin((OUT/'unittest.exit.json').read_bytes()) and summary['method_pin']==pin(METHOD.read_bytes())
        verify_evidence(reg,next_phase='benchmark')
        check(reg);method=load(METHOD,'_live_pin_memo_method')
        refs={}
        for p in MODULE_PATHS:
            raw=p.read_bytes();assert pin(raw)==reg['reference_source_pins'][str(p)]==reg['input_pins'][str(p)]
            refs[str(p)]=method.function_references(raw,str(p))
        frozen_reg=read(NFC/'registration.json');frozen_trace=read(TRACE/'inspection.json')
        compressed=base64.b64decode(frozen_trace['journal_zlib_base64'],validate=True);assert pin(compressed)==frozen_trace['journal_compressed_pin']
        decoder=zlib.decompressobj();raw=decoder.decompress(compressed,4194305);assert decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail and pin(raw)==frozen_trace['journal_raw_pin']
        expected_trace=[[p,n] for p,n,sha in json.loads(raw)];assert len(expected_trace)==2496
        for path,size in expected_trace:assert path in reg['input_pins'] and reg['input_pins'][path]['bytes']==size
        frozen_reg_pin=pin(canonical(frozen_reg))
        for index,variant in enumerate(('old','new','new','old')):
            assert time.perf_counter()-started<4.5
            module=load(NFC/'driver.py','_pin_memo_metadata_'+str(index));rows=[];clock=time.perf_counter();failure=None;session=None
            def traced(path):
                assert time.perf_counter()-clock<2,'single metadata check cap'
                value=original(path);assert len(rows)<8192;rows.append([str(path.absolute()),len(value)]);return value
            Path.read_bytes=traced
            try:
                if variant=='new':
                    with method.MetadataPinSession(refs) as session:session.attach(module).check(frozen_reg)
                else:module.check(frozen_reg)
            except BaseException as caught:failure=type(caught).__name__+':'+str(caught)[:200]
            finally:Path.read_bytes=original
            elapsed=time.perf_counter()-clock
            metrics=None if session is None or session._last_metrics is None else {**session._last_metrics,'cache_closed_after_check':session.memo.metrics()['closed'],'resident_bytes_after_check':session.memo.metrics()['resident_bytes'],'entries_after_check':session.memo.metrics()['entries']}
            assert pin(canonical(frozen_reg))==frozen_reg_pin
            case=dict(variant=variant,elapsed_seconds=elapsed,accepted=failure is None and elapsed<=2,error=failure,read_calls=len(rows),trace_equal=rows==expected_trace,trace=trace_blob(rows),metrics=metrics)
            details['cases'].append(case);assert case['accepted'] and case['trace_equal']
        check(reg);assert Path.read_bytes is original
        old=sum(c['elapsed_seconds'] for c in details['cases'] if c['variant']=='old');new=sum(c['elapsed_seconds'] for c in details['cases'] if c['variant']=='new')
        details.update(total_ratio_new_over_old=new/old,pair_ratios=[details['cases'][1]['elapsed_seconds']/details['cases'][0]['elapsed_seconds'],details['cases'][2]['elapsed_seconds']/details['cases'][3]['elapsed_seconds']],
            filesystem_reads_cached=False,json_or_module_or_execution_code_cached=False,original_read_sequence_preserved=True,extra_read_SHA_in_trace=False,verification_code_reference_only=True)
        accepted=True
    except BaseException as caught:error=type(caught).__name__+':'+str(caught)[:240]
    finally:Path.read_bytes=original
    terminal('benchmark',started,accepted,error,details,reg)


def saved():
    started=time.perf_counter();reg=read(OUT/'registration.json');accepted=False;error=None;details={}
    try:
        check(reg);unit=read(OUT/'unittest.exit.json');bench=read(OUT/'benchmark.exit.json');assert unit['accepted'] and bench['accepted']
        verified=verify_evidence(reg,next_phase='saved');assert verified['summary'] is not None
        origins=trace_open(reg['input_origins']);assert set(origins)==set(reg['input_pins']) and all(type(value) is str and value for value in origins.values())
        assert unit['details']['report']==dict(accepted=True,tests_run=8,failures=0,errors=0,skipped=0)
        assert unpack(unit['details']['stderr']).endswith(b'OK\n')
        assert pin((OUT/'unittest_admission.json').read_bytes())==unit['details']['admission_pin']
        cases=bench['details']['cases'];assert [c['variant'] for c in cases]==['old','new','new','old']
        baseline=trace_open(cases[0]['trace']);assert len(baseline)==2496
        for case in cases:
            assert case['accepted'] and case['trace_equal'] and trace_open(case['trace'])==baseline
            if case['variant']=='new':
                m=case['metrics'];assert m['hits']>0 and m['cache_closed_after_check'] and m['resident_bytes_after_check']==0
                assert m['calls']==m['hits']+m['misses'] and m['resident_bytes']<=67108864 and m['entries']<=2048
        ratio=sum(c['elapsed_seconds'] for c in cases if c['variant']=='new')/sum(c['elapsed_seconds'] for c in cases if c['variant']=='old')
        assert ratio==bench['details']['total_ratio_new_over_old'];details=verified['summary'];accepted=True
    except BaseException as caught:error=type(caught).__name__+':'+str(caught)[:240]
    terminal('saved',started,accepted,error,details,reg)


def checkpoint():
    started=time.perf_counter();assert not (OUT/'checkpoint.json').exists();endpoint=root_evidence();reg=read(OUT/'registration.json')
    if reg['accepted']:check(reg)
    else:
        for path,value in reg['input_pins'].items():assert pin(Path(path).read_bytes())==value,path
    verified=verify_evidence(reg);usage=verified['usage']
    charge=time.perf_counter()-started;usage['static']+=charge
    failures=verified['failures'];diagnostic=verified['diagnostic_accepted']
    accepted=charge<=1 and usage['static']<=8.5 and usage['unittest']<=.5 and sum(usage.values())<=9
    cumulative={**endpoint['all_cumulative_charged_seconds'],'static':endpoint['all_cumulative_charged_seconds']['static']+usage['static'],'unittest':endpoint['all_cumulative_charged_seconds']['unittest']+usage['unittest']}
    package_static=endpoint['original_package_static_seconds']+usage['static'];package_unit=endpoint['original_package_unittest_seconds']+usage['unittest'];assert package_static<=22 and package_unit<=8 and package_static+package_unit<=30
    save(OUT/'checkpoint.json',dict(accepted=accepted,diagnostic_accepted=diagnostic,acceptance_scope='metadata_pin_method_only' if diagnostic else 'rejection_metadata_only',authority='DRAFT_NONAUTHORITATIVE',kind='static',charged_seconds=charge,cap_seconds=1,
        scope_charged_seconds=usage,all_cumulative_charged_seconds=cumulative,all_cumulative_total_seconds=sum(cumulative.values()),prior_not_accepted_count=34+failures+(not accepted),
        original_package_static_seconds=package_static,original_package_unittest_seconds=package_unit,original_package_charged_seconds=package_static+package_unit,
        artifact_pins=pins(p for p in OUT.iterdir() if p.is_file()),predecessor_pin=pin((TRACE/'inspection.json').read_bytes()),source_epoch=read(NFC/'registration.json')['source_epoch'],replayed_summary=verified['summary'],unit_children_launched=0,cold_children_launched=0,**flags()))
    print(canonical(dict(accepted=accepted,diagnostic_accepted=diagnostic,charge=charge,scope=usage,total=sum(cumulative.values()),package_total=package_static+package_unit,not_accepted=34+failures+(not accepted))).decode())
    if not accepted:raise SystemExit(1)


if __name__=='__main__':
    methods=dict(register=register,unittest=unittest_phase,benchmark=benchmark,saved=saved,checkpoint=checkpoint)
    assert len(sys.argv)==2 and sys.argv[1] in methods
    if sys.argv[1]=='register':
        started=time.perf_counter();prerun=pins([METHOD,TEST,SCOPE,Path(__file__).absolute()])
        try:register(started)
        except BaseException as error:
            if not (OUT/'registration.json').exists():
                save(OUT/'registration.json',dict(accepted=False,authority='DRAFT_NONAUTHORITATIVE',kind='static',charged_seconds=time.perf_counter()-started,input_pins=prerun,error=repr(error),**flags()))
            raise
    else:methods[sys.argv[1]]()
