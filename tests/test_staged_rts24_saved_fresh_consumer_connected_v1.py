"""Transport and connection parser faults plus 41 frozen logical regressions."""
import ast
import base64
import copy
from hashlib import sha256
import importlib.util
import json
import lzma
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).absolute().parents[1]


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


legacy=load('tests/test_staged_rts24_saved_fresh_consumer_binding_v1.py','_frozen_consumer_binding_tests')
parent=load('experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v35.py','_connected_parent')
constructor=load('experiments/staged_rts24_saved_fresh_consumer_binding_transform_v1.py','_connected_constructor')
transport=parent.TRANSPORT


def encode(raw,check=lzma.CHECK_CRC64):return base64.b85encode(lzma.compress(raw,format=lzma.FORMAT_XZ,check=check,preset=6))
def packed(code):
    calls=[node for node in ast.walk(ast.parse(code)) if type(node) is ast.Call and type(node.func) is ast.Attribute and node.func.attr=='b85decode']
    assert len(calls)==1;return calls[0].args[0].value


def run_loader(code,replacement=None,compile_error=None,exec_error=None,close_error=None):
    marker=b'\nimport os as _bootstrap_os\n';tree=ast.parse(marker+code.partition(marker)[2]);events=[]
    if replacement is not None:
        call=next(node for node in ast.walk(tree) if type(node) is ast.Call and type(node.func) is ast.Attribute and node.func.attr=='b85decode')
        call.args[0].value=replacement
    class Cookie:
        def close(self):
            events.append('close')
            if close_error is not None:raise close_error
    def evaluate(compiled,context):
        events.append('exec')
        if exec_error is not None:raise exec_error
    namespace={'__name__':'synthetic_xz_loader','exec':evaluate}
    if compile_error is not None:
        def fail(*args,**kwargs):raise compile_error
        namespace['compile']=fail
    error=None
    with patch.object(os,'add_dll_directory',return_value=Cookie()):
        try:exec(compile(tree,'<synthetic-loader>','exec'),namespace)
        except BaseException as caught:error=caught
    return namespace,events,error


def synthetic_record_and_stderr():
    row=json.loads((ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v10_non_authoritative/probe_normal.receipt.json').read_bytes())
    record=copy.deepcopy(row['result']['child_record']);record.update(source_bookends=7,graph_calls=38,consumer_state='CONSUMED')
    record['post_metrics']['finder_check'][0]=14;record['post_metrics']['adapter_check'][0]=12
    with legacy.fixture() as (owner,adapter,entry,leaves):legacy.prepared_live(owner);record['consumer_result']=json.loads(legacy.consume(owner))
    old=[json.loads(line) for line in base64.b64decode(row['stderr_raw_base64']).splitlines()]
    templates={value[2]:value for value in old if value[0]=='graph' and value[3]=='exit'}
    n,a='namespace','adapter'
    groups={'<before_loader_ready>':[n]*15,'before_source_bytes':[n],'before_adapter_roots':[a],
        'before_boundary_close':[a,a],'after_boundary_close':[n,a,n,a],'before_profile':[a],
        'before_finish_import':[n,a,a,n,a,n,a],'after_finish_import':[n,a,n,a,n,a,n]}
    census={};stage='<before_loader_ready>'
    for value in old:
        if value[0]=='stage':stage=value[1]
        elif value[0]=='census':census.setdefault(stage,[]).append(value)
    clock=1.;sequence=0;rows=[];start=None
    for stage in ('<before_loader_ready>',)+parent.POST.STAGES:
        if stage!='<before_loader_ready>':rows.append(['stage',stage,clock]);clock+=.01
        for value in census.get(stage,[]):
            value=copy.deepcopy(value)
            if start is None:start=clock-.001
            value[1].update(start_clock=start,snapshot_clock=clock);rows.append(value);clock+=.01
        for kind in groups.get(stage,[]):
            sequence+=1;rows.append(['graph',sequence,kind,'enter',clock]);clock+=.001
            rows.append(['graph',sequence,kind,'exit',clock,*templates[kind][5:]]);clock+=.001
    assert sequence==38
    return record,b''.join(parent.canonical(value)+b'\n' for value in rows)


class ConnectedConsumerTests(legacy.ConsumerBindingTests):
    def test_42_exact_transport_sources_code_and_command(self):
        before,raw=transport.payload(parent.CORE,parent.PROBE);code=parent.transport()
        self.assertEqual(transport.decode(packed(code),(len(raw),sha256(raw).hexdigest())),raw)
        self.assertEqual(constructor.parent((ROOT/'experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v34.py').read_text(encoding='utf8')),(ROOT/'experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v35.py').read_bytes())
        self.assertEqual(constructor.validator((ROOT/'experiments/staged_rts24_saved_fresh_live_profile_validation_v1.py').read_text(encoding='utf8')),(ROOT/'experiments/staged_rts24_saved_fresh_consumer_binding_validation_v2.py').read_bytes())
        for case in ('discovery','normal'):
            argv=[str(parent.EXE),'-P','-B','-s','-S','-c',code.decode(),'--pre-entry-lease',str(parent.OUT/('probe_'+case+'.plan.json')),'0'*64]
            self.assertLessEqual(len(subprocess.list2cmdline(argv).encode('utf-16-le'))//2,30000)
        original=json.loads((parent.OUT/'transport_preparation.json').read_bytes())
        self.assertEqual(parent.pin(base64.b64decode(original['transport_raw_base64'])),original['transport_pin'])
        self.assertFalse(original['candidate_command_admitted']);self.assertEqual(original['command_utf16_units_by_case']['discovery'],30153)

    def test_43_corruption_truncation_trailing_and_wrong_sha(self):
        code=parent.transport();value=packed(code);compressed=base64.b85decode(value);damaged=bytearray(compressed);damaged[-8]^=1
        candidates=(b' ',base64.b85encode(compressed[:-1]),base64.b85encode(bytes(damaged)),
            base64.b85encode(compressed+b'x'),base64.b85encode(compressed+compressed),encode(b'valid XZ wrong payload'),encode(b'x',lzma.CHECK_NONE))
        for candidate in candidates:
            with self.subTest(pin=parent.pin(candidate)):
                namespace,events,error=run_loader(code,candidate)
                self.assertIsNotNone(error);self.assertNotIn('exec',events);self.assertEqual(events.count('close'),1)
                self.assertTrue(all(name not in namespace for name in ('_ux','_xz','_hs','_lp','_ln')))

    def test_44_output_boundary_and_memory_failure(self):
        for size in (131072,131073):
            raw=b'x'*size;value=encode(raw);expected=(size,sha256(raw).hexdigest())
            if size==131072:self.assertEqual(transport.decode(value,expected),raw)
            else:
                with self.assertRaises(AssertionError):transport.decode(value,expected)
            namespace,events,error=run_loader(parent.transport(),value);self.assertIsNotNone(error);self.assertEqual(events,['close'])
        with self.assertRaises(lzma.LZMAError):lzma.LZMADecompressor(format=lzma.FORMAT_XZ,memlimit=1).decompress(base64.b85decode(packed(parent.transport())))
        code=parent.transport();failure=lzma.LZMAError('injected decoder memory refusal')
        with patch.object(lzma,'LZMADecompressor',side_effect=failure):
            namespace,events,error=run_loader(code)
        self.assertIs(error,failure);self.assertEqual(events,['close']);self.assertNotIn('_xz',namespace)

    def test_45_cookie_cleanup_and_primary_preservation(self):
        code=parent.transport()
        namespace,events,error=run_loader(code);self.assertIsNone(error);self.assertEqual(events,['exec','close'])
        for point in ('compile','exec'):
            primary=ValueError('injected '+point);cleanup=RuntimeError('injected cookie close')
            kwargs={point+'_error':primary,'close_error':cleanup}
            namespace,events,error=run_loader(code,**kwargs)
            self.assertIs(error,primary);self.assertIs(error.__cause__,cleanup);self.assertEqual(events.count('close'),1)
            self.assertTrue(all(name not in namespace for name in ('_ux','_xz','_hs','_lp','_ln')))

    def test_46_consumer_result_false_domain_and_types(self):
        with legacy.fixture() as (owner,adapter,entry,leaves):legacy.prepared_live(owner);value=json.loads(legacy.consume(owner))
        self.assertIs(parent.POST.validate_consumer_result(value,parent),value)
        for key in set(parent.FALSE_FIELDS)|{'producer_capability_verified','binding_members','same_live_owner','consumer_return_is_adapter'}:
            bad=copy.deepcopy(value);bad[key]=0
            with self.subTest(key=key),self.assertRaises(AssertionError):parent.POST.validate_consumer_result(bad,parent)

    def test_47_connected_graph_stage_and_lifetime_parser(self):
        record,stderr=synthetic_record_and_stderr();parsed=parent.POST.parse(parent,stderr)
        accepted=parent.POST.validate_success(record,parsed,parent)
        self.assertTrue(accepted['binding_consumer_completed']);self.assertEqual(accepted['graph_counts'],dict(namespace=25,adapter=13))
        for key,value in (('source_bookends',5),('graph_calls',30),('consumer_state','PREPARED'),('runtime_phase','LIVE')):
            bad=copy.deepcopy(record);bad[key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):parent.POST.validate_success(bad,parsed,parent)
        bad=copy.deepcopy(parsed);bad['graph_intervals']['before_final_runtime_close']=['namespace']
        with self.assertRaises(AssertionError):parent.POST.validate_success(record,bad,parent)

    def test_48_frozen_reference_and_codec_temporary_domain(self):
        source,raw=parent.REFERENCE.raw_reference();self.assertEqual(len(raw),501203)
        self.assertEqual(parent.pin(raw),source['reference']['pin']);self.assertFalse(source['resource_admission'])
        code=parent.transport();namespace,events,error=run_loader(code)
        self.assertIsNone(error);self.assertEqual(namespace['_PAYLOAD_RAW'],transport.payload(parent.CORE,parent.PROBE)[1])
        self.assertEqual(type(namespace['_PAYLOAD_CODE']),type(compile('','<unit>','exec')))
        self.assertTrue(all(name not in namespace for name in ('_ux','_xz','_hs','_lp','_ln')))
        driver=load('results/tables/staged_rts24_saved_fresh_nfc_v11_non_authoritative/driver.py','_codec_startup_fixture')
        modules={'lzma':'Lib/lzma.py','_compression':'Lib/_compression.py','_lzma':'DLLs/_lzma.pyd',
            'hashlib':'Lib/hashlib.py','_hashlib':'DLLs/_hashlib.pyd'}
        paths=[parent.RUNTIME/value for value in modules.values()]+[parent.RUNTIME/value for value in
            ('Library/bin/liblzma.dll','Library/bin/libcrypto-3-x64.dll')]
        profile=dict(module_origins=[[name,str(parent.RUNTIME/value),'unit-loader'] for name,value in modules.items()],
            disk_file_observations={str(path):parent.pin(path.read_bytes()) for path in paths},
            native_origin_boundaries=[str(path) for path in paths if path.suffix.lower() in ('.pyd','.dll')])
        self.assertTrue(driver.check_codec_startup(profile))
        for mode in ('name','origin','duplicate','hashlib_file','native'):
            bad=copy.deepcopy(profile)
            if mode=='name':bad['module_origins'][0][0]='foreign'
            elif mode=='origin':bad['module_origins'][0][1]=str(parent.RUNTIME/'Lib/hashlib.py')
            elif mode=='duplicate':bad['module_origins'].append(list(bad['module_origins'][0]))
            elif mode=='hashlib_file':bad['disk_file_observations'].pop(str(parent.RUNTIME/'Lib/hashlib.py'))
            else:bad['native_origin_boundaries']=[]
            with self.subTest(mode=mode),self.assertRaises(AssertionError):driver.check_codec_startup(bad)
