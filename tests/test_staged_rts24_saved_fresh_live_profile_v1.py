"""Frozen regressions plus LIVE reference/failure checks; no scientific body runs."""
import ast
import base64
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import FunctionType,SimpleNamespace
from unittest.mock import patch
import zlib

ROOT=Path(__file__).absolute().parents[1]


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


legacy=load('tests/test_staged_rts24_saved_fresh_post_return_v2.py','_frozen_observed_tests')
constructor=load('experiments/staged_rts24_saved_fresh_live_profile_transform_v1.py','_live_constructor')
parent=load('experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v34.py','_live_parent')
core=load('experiments/staged_rts24_saved_fresh_pre_entry_lease_v37.py','_live_core')
reference=parent.REFERENCE
validation=parent.POST


def write(path,value):path.write_bytes(parent.canonical(value))
def spec(fn):return FunctionType,fn.__code__,fn.__globals__,fn.__defaults__
def clone(fn,updates):return FunctionType(fn.__code__,{**fn.__globals__,**updates},fn.__name__,fn.__defaults__,fn.__closure__)


def controller_fixture(folder,code):
    helper=ROOT/'experiments/staged_rts24_saved_fresh_live_profile_reference_v1.py'
    reg=dict(source_epoch=parent.SOURCE_SHA,transport_pin=parent.pin(code),helper_pins={str(helper):parent.pin(helper.read_bytes())})
    write(folder/'registration.json',reg);write(folder/'startup_profile.json',{});write(folder/'probe_discovery.receipt.json',{})
    admission=dict(accepted=True,authority='DRAFT_NONAUTHORITATIVE',profile_pin=parent.pin((folder/'startup_profile.json').read_bytes()),
        transport_pin=parent.pin(code),helper_pins=reg['helper_pins'],environment_pin=parent.pin(parent.canonical(parent.environment())),
        registration_pin=parent.pin((folder/'registration.json').read_bytes()),discovery_receipt_pin=parent.pin((folder/'probe_discovery.receipt.json').read_bytes()),
        reference_source=reference.reference(),**{k:False for k in parent.FALSE_FIELDS})
    body=parent.canonical(admission)
    row=dict(accepted=True,label='profile_admission',registration_pin=admission['registration_pin'],embedded_artifacts=dict(admission=dict(
        encoding='canonical_json',raw_base64=base64.b64encode(body).decode(),pin=parent.pin(body))),**{k:False for k in parent.FALSE_FIELDS})
    write(folder/'profile_admission.exit.json',row)
    plan=dict(case='normal',authority='DRAFT_NONAUTHORITATIVE',source_epoch=parent.SOURCE_SHA,source_pins=parent.source(),
        bootstrap_pin=parent.pin(code),startup_profile=dict(path=str(folder/'startup_profile.json'),pin=admission['profile_pin']),
        import_profile=admission['reference_source']['reference'])
    write(folder/'probe_normal.plan.json',plan)
    return admission,row,plan


def runtime_fixture(observed,expected):
    boundary=SimpleNamespace(_adapter=object(),_runtime_bindings=(object(),),_retention=(('held',object()),),_unit_observed=observed)
    runtime=SimpleNamespace(_phase='IMPORTING',_audit_handed_off=True,_boundary=boundary,_boundary_phase=spec(lambda owner:'CLOSED'),
        _boundary_profile=spec(lambda owner:owner._unit_observed),_raw=b'unit',source_bookend=lambda:None)
    runtime.entry=lambda:runtime
    fn=clone(core.LocalRuntimeInputs.finish_import,dict(check_plan=lambda raw:dict(import_profile=dict(path='unit-reference',pin=core.pin(expected))),
        read_file=lambda path,pin:expected,control_image=lambda:(),runtime_seal=lambda owner:('seal',)))
    return runtime,boundary,fn


def close_runtime(runtime,primary=None,boundary_failure=False):
    def cleanup(resource,owner,primary=None):resource.pending=[False,False];resource.phase='CLOSED'
    resource=SimpleNamespace(creator=('unit',1),pending=[True,True],phase='LIVE',guard={'active':True},_early=None)
    ownership=(None,None,cleanup.__code__,object(),BaseException)
    runtime._cleanup_started=False;runtime._failure=None;runtime._resource=resource;runtime._ownership=ownership
    runtime._cleanup_seal=(id(resource),id(ownership),id(ownership[2]),id(ownership[3]),id(ownership[4]),resource.creator)
    runtime._namespace_specs=(None,None,spec(lambda namespace,owner:None));runtime._namespace=SimpleNamespace()
    # The held native cleanup runner executes code without a closure.
    if boundary_failure:
        def fail(owner,primary=None):raise ValueError('injected_live_close_failure')
        runtime._boundary_finish=spec(fail)
    else:runtime._boundary_finish=spec(lambda owner,primary=None:None)
    core.LocalRuntimeInputs.close(runtime,primary)
    return resource


class LiveProfileTests(legacy.PostReturnTests):
    def test_22_exact_successors_and_frozen_reference(self):
        for name,before,after in (
            ('core','experiments/staged_rts24_saved_fresh_pre_entry_lease_v36.py','experiments/staged_rts24_saved_fresh_pre_entry_lease_v37.py'),
            ('probe','tests/staged_rts24_saved_fresh_runtime_handoff_probe_v34.py','tests/staged_rts24_saved_fresh_runtime_handoff_probe_v35.py'),
            ('parent','experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v33.py','experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v34.py'),
            ('validator','experiments/staged_rts24_saved_fresh_post_return_validation_v1.py','experiments/staged_rts24_saved_fresh_live_profile_validation_v1.py')):
            self.assertEqual(getattr(constructor,name)((ROOT/before).read_text(encoding='utf-8')),(ROOT/after).read_bytes())
        driver=load('results/tables/staged_rts24_saved_fresh_nfc_v10_non_authoritative/driver.py','_live_unit_commands')
        cases=driver.command_units_by_case(parent.transport())
        self.assertEqual(set(cases),{'discovery','normal'});self.assertEqual(cases['discovery']-cases['normal'],3);self.assertLessEqual(max(cases.values()),30000)
        source,raw=reference.raw_reference();self.assertEqual(len(raw),501203)
        self.assertEqual(source['reference']['pin'],parent.pin(raw));self.assertFalse(source['external_expected_truth_verified'])
        original=Path.read_bytes
        def missing(path):
            if path==Path(source['reference']['path']):raise FileNotFoundError('unit missing reference')
            return original(path)
        with patch.object(Path,'read_bytes',missing):
            with self.assertRaises(FileNotFoundError):reference.reference()
        def mutation(path):
            value=original(path)
            return value[:-1]+bytes([value[-1]^1]) if path==Path(source['reference']['path']) else value
        with patch.object(Path,'read_bytes',mutation):
            with self.assertRaises(AssertionError):reference.reference()
        checkpoint=load('experiments/staged_rts24_saved_fresh_live_profile_checkpoint_v1.py','_live_unit_checkpoint')
        expected=dict(import_profile_pin=source['reference']['pin'],expected_import_profile_pin=source['reference']['pin'],
            frozen_nfc9_import_profile_exact_match=True,reference_source=source,reference_context_pin=parent.pin(b'unit context'),
            memory_observation=dict(error=None),run_authority=False)
        fake=SimpleNamespace(reopen=driver.reopen,saved_report=lambda parent,receipt:expected)
        self.assertEqual(checkpoint.verified_saved_replay(fake,None,None,dict(embedded_artifacts=driver.packed(dict(report=expected)))),expected)
        for key in expected:
            changed=copy.deepcopy(expected);changed[key]=None
            with self.assertRaisesRegex(AssertionError,'complete saved replay'):checkpoint.verified_saved_replay(fake,None,None,dict(embedded_artifacts=driver.packed(dict(report=changed))))
        changed=copy.deepcopy(expected);changed['run_authority']=0
        with self.assertRaises(AssertionError):checkpoint.verified_saved_replay(fake,None,None,dict(embedded_artifacts=driver.packed(dict(report=changed))))

    def test_23_admission_manifest_and_reference_bookends(self):
        with tempfile.TemporaryDirectory(prefix='saved_F_live_unit_') as tmp,patch.object(parent,'OUT',Path(tmp)):
            folder=Path(tmp);code=b'synthetic transport';admitted,row,plan=controller_fixture(folder,code)
            raw=parent.canonical(plan);before=reference.context(parent,code,plan,raw)
            self.assertEqual(before,reference.context(parent,code,plan,raw))
            for mode in ('path','pin','transport','source'):
                bad=copy.deepcopy(plan)
                if mode=='path':bad['import_profile']['path']=str(folder/'own-profile.json')
                elif mode=='pin':bad['import_profile']['pin']['sha256']='0'*64
                elif mode=='transport':bad['bootstrap_pin']=parent.pin(b'changed')
                else:bad['source_epoch']='0'*64
                write(folder/'probe_normal.plan.json',bad)
                with self.assertRaises(AssertionError):reference.context(parent,code,bad,parent.canonical(bad))
            write(folder/'probe_normal.plan.json',plan)
            for mode in ('reference','authority','extra'):
                bad=copy.deepcopy(admitted)
                if mode=='reference':bad['reference_source']['reference']['pin']['sha256']='0'*64
                elif mode=='authority':bad['run_authority']=True
                else:bad['extra']=False
                body=parent.canonical(bad);exit=copy.deepcopy(row);exit['embedded_artifacts']['admission'].update(raw_base64=base64.b64encode(body).decode(),pin=parent.pin(body))
                write(folder/'profile_admission.exit.json',exit)
                with self.assertRaises(AssertionError):reference.admission(parent,code)
            write(folder/'profile_admission.exit.json',row)
            write(folder/'registration.json',dict(changed=True))
            with self.assertRaises(AssertionError):reference.context(parent,code,plan,raw)

    def test_24_live_commit_profile_mismatch_and_cleanup_failures(self):
        expected=b'unit raw profile';runtime,boundary,fn=runtime_fixture(expected,expected)
        self.assertEqual(fn(runtime,boundary._adapter,boundary._runtime_bindings,boundary._retention),expected)
        self.assertEqual(runtime._phase,'LIVE');self.assertTrue(runtime._import_profile_matched)
        resource=close_runtime(runtime);self.assertEqual(runtime._phase,'CLOSED');self.assertEqual(resource.phase,'CLOSED')
        runtime,boundary,fn=runtime_fixture(b'other raw profile',expected)
        with self.assertRaisesRegex(ValueError,'independent B_S profile differs') as mismatch:fn(runtime,boundary._adapter,boundary._runtime_bindings,boundary._retention)
        self.assertEqual(runtime._phase,'IMPORTING')
        with self.assertRaises(core.LocalRuntimeUnresolved) as closed:close_runtime(runtime,mismatch.exception)
        self.assertIs(closed.exception.primary,mismatch.exception);self.assertEqual(runtime._phase,'UNRESOLVED');self.assertEqual(runtime._resource.phase,'CLOSED')
        runtime,boundary,fn=runtime_fixture(expected,expected);calls=[]
        def entry():
            calls.append(1)
            if len(calls)>1:raise ValueError('injected_after_live_commit')
            return runtime
        runtime.entry=entry
        with self.assertRaisesRegex(ValueError,'after_live_commit') as primary:fn(runtime,boundary._adapter,boundary._runtime_bindings,boundary._retention)
        self.assertEqual(runtime._phase,'LIVE');runtime.entry=lambda:runtime
        with self.assertRaises(core.LocalRuntimeUnresolved):close_runtime(runtime,primary.exception)
        self.assertEqual(runtime._phase,'UNRESOLVED');self.assertEqual(runtime._resource.phase,'CLOSED')
        runtime,boundary,fn=runtime_fixture(expected,expected);fn(runtime,boundary._adapter,boundary._runtime_bindings,boundary._retention)
        with self.assertRaises(core.LocalRuntimeUnresolved) as cleanup:close_runtime(runtime,boundary_failure=True)
        self.assertEqual(runtime._phase,'UNRESOLVED');self.assertEqual(runtime._resource.phase,'CLOSED');self.assertEqual(cleanup.exception.secondary[0][0],'import_boundary')
        probe=ast.parse((ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v35.py').read_bytes())
        main=next(n for n in probe.body if type(n) is ast.FunctionDef and n.name=='_probe_main')
        statement=next(n for n in ast.walk(main) if type(n) is ast.Expr and type(n.value) is ast.Call and type(n.value.func) is ast.Name and n.value.func.id=='require' and any(type(c) is ast.Constant and c.value=='runtime profile/phase differs' for c in ast.walk(n)))
        context=dict(require=core.require,runtime=SimpleNamespace(finish_import=lambda *args:expected),adapter=None,adapter_bindings=None,retention=None,observed_profile=b'different first profile')
        with self.assertRaisesRegex(ValueError,'runtime profile/phase differs'):exec(compile(ast.Module(body=[statement],type_ignores=[]),'<held-profile-comparison>','exec'),context)

    def test_25_parent_live_raw_profile_and_false_claim_rejection(self):
        origin=ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v9_non_authoritative'
        receipt=json.loads((origin/'probe_import_discovery.receipt.json').read_bytes());record=json.loads(base64.b64decode(receipt['stdout_raw_base64']));stderr=base64.b64decode(receipt['stderr_raw_base64'])
        record.update(case='normal',runtime_phase_before_close='LIVE',runtime_was_live=True)
        source,expected=reference.raw_reference();profile=json.loads(expected)
        with tempfile.TemporaryDirectory(prefix='saved_F_live_raw_') as tmp,patch.object(parent,'OUT',Path(tmp)):
            folder=Path(tmp);code=b'unit transport';_,_,plan=controller_fixture(folder,code)
            argv=['synthetic-live',str(folder/'probe_normal.plan.json'),parent.pin(parent.canonical(plan))['sha256']]
            record['kernel_identity']['command_line_sha']=parent.pin(subprocess.list2cmdline(argv).encode())
            identity=dict(pid=record['kernel_identity']['pid'],creation=record['kernel_identity']['process_creation_filetime'])
            def compare(value):return validation.compare(parent,'normal',code,parent.canonical(value)+b'\n',stderr,0,identity,argv,[])
            result=compare(record);self.assertTrue(result['post_return_terminal_complete'])
            self.assertTrue(result['profile_comparison']['frozen_nfc9_import_profile_exact_match'])
            for field in ('modules','cache','paths','finder_types'):
                changed=copy.deepcopy(profile)
                if field=='modules':changed[field][0][2]='unit.changed'
                elif field=='cache':changed[field][0][1]='unit.changed'
                else:changed[field]=list(reversed(changed[field]))
                difference=reference.compare_profile(changed);self.assertFalse(difference['frozen_nfc9_import_profile_exact_match']);self.assertIn(field,difference['differing_fields'])
                raw=parent.canonical(changed);bad=copy.deepcopy(record);bad['import_profile']=dict(encoding='zlib_base64',raw_pin=parent.pin(raw),data=base64.b64encode(zlib.compress(raw)).decode())
                with self.assertRaises(AssertionError):compare(bad)
            for key,value in (('runtime_phase_before_close','OBSERVED'),('runtime_was_live',False),('resource_phase','UNRESOLVED')):
                bad=copy.deepcopy(record);bad[key]=value
                with self.assertRaises(AssertionError):compare(bad)
            bad=copy.deepcopy(record);bad['claimed_match']=True
            with self.assertRaises(AssertionError):compare(bad)
