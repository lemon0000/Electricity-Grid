"""Logical ownership/binding fixtures; real HANDLE behavior is checked by cold probes."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import pickle
import tempfile
from threading import Thread,get_ident
from types import FunctionType
import unittest
from unittest import mock

ROOT=Path(__file__).absolute().parents[1]
SPEC=importlib.util.spec_from_file_location('_pre_entry_core_unit',ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v2.py')
core=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(core)


class LogicalResource:
    def __init__(self,owner):
        self.owner=owner;self.creator=(os.getpid(),get_ident(),7);self.phase='LIVE';self.pending=[(1,'live'),(2,'live')]
        self.close_calls=[0,0];self.guard=dict(self_live=True,events=[],faults=[]);self.observation={'logical':True}
        self.cleanup_code=type(self).close.__code__;self.reject=ValueError;self.unresolved=core.LocalPreEntryUnresolved;self._early=None
    def snapshot(self):
        if self.creator[:2]!=(os.getpid(),get_ident()):raise ValueError('foreign logical creator')
        return self.observation
    def close(self,owner,primary=None):
        if self.owner is not owner:raise self.reject('logical resource owner differs')
        for i in (1,0):
            if self.pending[i] is not None:self.close_calls[i]+=1;self.pending[i]=None
        self.phase='CLOSED';self.guard['self_live']=False


def fixture(sources=(),pins=None):
    owner=object.__new__(core.LocalPreEntryLease);r=LogicalResource(owner)
    owner._resource=r;owner._ownership=(r,r.creator,r.cleanup_code,FunctionType,BaseException)
    owner._sources=tuple(sources);owner._raw=core.canonical(dict(source_pins=pins or {},startup_absent=[]))
    owner._control=core.control_image();owner._bindings=core.capture_bindings()
    owner._verifier=core.check_bindings;owner._verifier_code=core.check_bindings.__code__;owner._verifier_defaults=core.check_bindings.__defaults__
    owner._entry_spec=(FunctionType,core._LocalInputs.entry.__code__,vars(core),core._LocalInputs.entry.__defaults__);owner._exact_type=core.LocalPreEntryLease
    owner._target_type=core.LocalPreEntryInputs;owner._type=type;owner._allocate=object.__new__;owner._error=ValueError
    owner._phase='LIVE';owner._failure=None;owner._commit=core.pin(core.canonical(owner._image()))
    owner._seal=core.seal_image(owner)
    owner._cleanup_seal=(id(r),id(owner._ownership),id(owner._ownership[2]),id(owner._ownership[3]),id(owner._ownership[4]),r.creator)
    return owner


def native_cleanup_fixture(failed=(),uncertain=()):
    owner=fixture();r=owner._resource;native=object.__new__(core._Resource)
    class NativeFunction:
        def __init__(self,callback):self.callback=callback;self.argtypes=[];self.restype=int
        def __call__(self,*args):return self.callback(*args)
    def close(handle):
        if handle in failed:core.C.set_last_error(5);return 0
        return 1
    def witness(handle,flags):core.C.set_last_error(5 if handle in uncertain else 6);return 0
    native.owner=owner;native.creator=r.creator;native.pending=[(101,'live'),(102,'live')];native.close_calls=[0,0]
    native.held={'CloseHandle':(NativeFunction(close),(),int),'GetHandleInformation':(NativeFunction(witness),(),int)}
    native._getpid=os.getpid;native._get_ident=get_ident;native._reject=ValueError;native._tuple=tuple
    native._WinError=core.C.WinError;native._get_error=core.C.get_last_error;native._set_error=core.C.set_last_error
    native._DWORD=core.W.DWORD;native._byref=core.C.byref;native._any=any;native._unresolved=core.LocalPreEntryUnresolved;native._early=None
    native.phase='LIVE';native.guard=dict(self_live=True,events=[],faults=[]);native.observation={'logical_native_callbacks':True}
    native.snapshot=lambda:native.observation
    owner._resource=native;owner._ownership=(native,native.creator,core._Resource.close.__code__,FunctionType,BaseException)
    owner._commit=core.pin(core.canonical(owner._image()));owner._seal=core.seal_image(owner)
    owner._cleanup_seal=(id(native),id(owner._ownership),id(owner._ownership[2]),id(owner._ownership[3]),id(owner._ownership[4]),native.creator)
    return owner


def valid_plan():
    path=ROOT/'results/tables/staged_rts24_saved_fresh_machinery_transition_v1_non_authoritative/checks_01/admission_repair.json'
    sources=json.loads(path.read_bytes())['source_pins']
    env=dict(PYTHONHASHSEED='0',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    return dict(schema='staged_saved_F_pre_entry_manifest_v1',authority='DRAFT_NONAUTHORITATIVE',nonce='0'*32,
        source_pins=sources,source_epoch=core.SOURCE_SHA,bootstrap_pin=core.pin(b'fixture'),
        executable_pin=dict(bytes=104264,sha256='4a7d81f72d979c088c653b1da12c2f2d81da66bdf8074753c6a9b154d9c86116'),
        python=core._PYTHON,environment=env,cwd=str(core.ROOT),initial_paths=list(core._PATHS),
        selected_runtime_file_observations={n:core.pin(b'') for n in core.TCB_PATHS},startup_absent=list(core.STARTUP_ABSENT),startup_profile=None,case='discovery')


class PreEntryLeaseTests(unittest.TestCase):
    def test_public_constructors_and_imported_factory_refuse(self):
        for cls in (core.LocalPreEntryLease,core.LocalPreEntryInputs):
            with self.assertRaises(TypeError):cls()
        with self.assertRaises(ValueError):core.open_local_pre_entry_lease(b'{}',{})
    def test_canonical_duplicate_truncated_and_oversize_manifest(self):
        for raw in (b'{"a":1,"a":2}',b'{',b'{ "a":1}',b'x'*131073):
            with self.subTest(raw=raw[:30]),self.assertRaises((ValueError,json.JSONDecodeError)):core.decode(raw)
    def test_fixed_development_map_and_closed_plan(self):
        plan=valid_plan();self.assertEqual(core.check_plan(core.canonical(plan)),plan)
        for field,value in [('source_epoch','0'*64),('source_pins',{}),('nonce','x'),('extra',True),('initial_paths',[str(ROOT)]),('startup_absent',[])]:
            changed=dict(plan);changed[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):core.check_plan(core.canonical(changed))
    def test_environment_injection_and_fixed_thread_count_rejected(self):
        for key,value in [('PYTHONPATH',str(ROOT)),('OMP_NUM_THREADS','2'),('PYTHONHASHSEED','random')]:
            plan=valid_plan();plan['environment'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):core.check_plan(core.canonical(plan))
    def test_discovery_cannot_masquerade_as_verified_profile(self):
        plan=valid_plan();plan['case']='normal'
        with self.assertRaises(ValueError):core.check_plan(core.canonical(plan))
        plan['startup_profile']=dict(path='test',pin=core.pin(b'{}'))
        self.assertEqual(core.check_plan(core.canonical(plan))['case'],'normal')
    def test_linear_transfer_and_source_close_never_double_closes(self):
        source=fixture();r=source._resource;target=source.transfer()
        self.assertIs(type(target),core.LocalPreEntryInputs);self.assertIs(r.owner,target);self.assertEqual(source._phase,'CONSUMED')
        source.close();self.assertEqual(r.close_calls,[0,0]);target.close();target.close();source.close()
        self.assertEqual(r.close_calls,[1,1]);self.assertEqual(target._phase,'CLOSED')
    def test_second_transfer_and_closed_entry_refuse(self):
        source=fixture();target=source.transfer()
        with self.assertRaises(ValueError):source.transfer()
        target.close()
        with self.assertRaises(ValueError):target.entry()
    def test_copy_deepcopy_and_pickle_refuse(self):
        source=fixture()
        try:
            for fn in (copy.copy,copy.deepcopy,pickle.dumps):
                with self.subTest(fn=fn),self.assertRaises(TypeError):fn(source)
        finally:source.close()
    def test_foreign_thread_refuses_and_owner_still_closes(self):
        source=fixture();errors=[]
        def foreign():
            try:source.entry()
            except BaseException as e:errors.append(e)
        thread=Thread(target=foreign);thread.start();thread.join()
        self.assertEqual(len(errors),1);source.close();self.assertEqual(source._resource.close_calls,[1,1])
    def test_verifier_global_replacement_cannot_bypass(self):
        source=fixture()
        with mock.patch.object(core,'check_bindings',lambda *a:None):
            with self.assertRaises(ValueError):source.transfer()
        source.close()
    def test_synchronized_verifier_and_checked_helper_replacement_refuses(self):
        source=fixture()
        with mock.patch.object(core,'check_bindings',lambda *a:None),mock.patch.object(core,'read_file',lambda *a,**k:b'forged'),mock.patch.object(core,'require',lambda *a:None):
            with self.assertRaises(ValueError):source.transfer()
        source.close()
    def test_held_verifier_code_and_defaults_drift_refuse(self):
        for field,value in [('__code__',(lambda *a:None).__code__),('__defaults__',())]:
            source=fixture();original=getattr(core.check_bindings,field)
            try:
                setattr(core.check_bindings,field,value)
                with self.assertRaises(ValueError):source.transfer()
            finally:setattr(core.check_bindings,field,original);source.close()
    def test_exact_target_class_global_swap_refuses(self):
        class Foreign(core._LocalInputs):pass
        source=fixture()
        with mock.patch.object(core,'LocalPreEntryInputs',Foreign):
            with self.assertRaises(ValueError):source.transfer()
        source.close()
    def test_coherent_verifier_field_swap_refuses_before_fake_runs(self):
        source=fixture();calls=[];original=(source._verifier,source._verifier_code,source._verifier_defaults)
        def fake(*args):calls.append(True)
        source._verifier=fake;source._verifier_code=fake.__code__;source._verifier_defaults=fake.__defaults__
        with self.assertRaises(ValueError):source.transfer()
        self.assertEqual(calls,[])
        source._verifier,source._verifier_code,source._verifier_defaults=original;source.close()
    def test_entry_dispatch_field_swap_cannot_run_forged_code(self):
        source=fixture();calls=[];original=source._entry_spec
        def fake(*args):calls.append(True);return lambda self:self
        source._entry_spec=(fake,original[1],original[2],original[3])
        with self.assertRaises(ValueError):source.transfer()
        self.assertEqual(calls,[]);source._entry_spec=original;source.close()
    def test_cleanup_root_swap_never_executes_unowned_code(self):
        source=fixture();calls=[];original=source._ownership
        source._ownership=(*original[:3],lambda *args:calls.append(True),original[4])
        with self.assertRaises(core.LocalPreEntryUnresolved):source.close()
        self.assertEqual(calls,[]);self.assertEqual(source._resource.close_calls,[0,0])
        source._ownership=original;source.close()
    def test_subclass_cannot_present_as_exact_source(self):
        class Foreign(core.LocalPreEntryLease):pass
        source=fixture();foreign=object.__new__(Foreign);foreign.__dict__.update(source.__dict__)
        with self.assertRaises(ValueError):foreign.entry()
        source.close()
    def test_entry_method_code_swap_cannot_bypass_transfer(self):
        source=fixture();fn=core._LocalInputs.entry;code=fn.__code__
        try:
            fn.__code__=(lambda self: self).__code__
            with self.assertRaises(ValueError):source.transfer()
        finally:fn.__code__=code;source.close()
    def test_control_path_drift_refuses_and_cleanup_preserves_error(self):
        source=fixture();original=list(core.sys.path)
        try:
            core.sys.path.append('foreign')
            with self.assertRaises(ValueError):source.entry()
            with self.assertRaises(core.LocalPreEntryUnresolved):source.close()
            self.assertEqual(source._resource.close_calls,[1,1])
        finally:core.sys.path[:]=original
    def test_original_source_bytes_drift_refuses(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.py';path.write_bytes(b'pass\n')
            with mock.patch.object(core,'ROOT',Path(folder)):
                source=fixture((('source.py',b'pass\n'),),dict({'source.py':core.pin(b'pass\n')}))
                self.assertEqual(source.source_bytes('source.py'),b'pass\n');path.write_bytes(b'fail\n')
                with self.assertRaises(ValueError):source.entry()
                with self.assertRaises(core.LocalPreEntryUnresolved):source.close()
                self.assertFalse(any(source._resource.pending))
    def test_read_reparse_and_pin_guards(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'x';path.write_bytes(b'abc')
            self.assertEqual(core.read_file(path,core.pin(b'abc')),b'abc')
            with self.assertRaises(ValueError):core.read_file(path,core.pin(b'abd'))
            with self.assertRaises(ValueError):core.read_file(path,dict(bytes=9*1024**2,sha256='0'*64))
    def test_sticky_audit_fault_refuses_even_when_caught(self):
        source=fixture();source._resource.guard['faults'].append('caught')
        with self.assertRaises(ValueError):source.entry()
        with self.assertRaises(core.LocalPreEntryUnresolved):source.close()
        self.assertFalse(any(source._resource.pending))
    def test_closed_failure_retains_primary_and_layered_secondary(self):
        source=fixture();primary=ValueError('primary');secondary=OSError('close')
        error=core.LocalPreEntryConstructionFailed(source,primary,(('process',secondary),))
        self.assertIs(error.primary,primary);self.assertIs(error.secondary[0][1],secondary)
        with self.assertRaises(TypeError):pickle.dumps(error)
        source.close()
    def test_native_close_failure_keeps_owner_and_closes_other_handle(self):
        source=native_cleanup_fixture(failed=(102,))
        with self.assertRaises(core.LocalPreEntryUnresolved) as caught:source.close()
        r=source._resource;self.assertIs(caught.exception.owner,source);self.assertEqual(r.close_calls,[1,1])
        self.assertIsNone(r.pending[0]);self.assertEqual(r.pending[1],(102,'live'));self.assertEqual(source._phase,'UNRESOLVED')
        with self.assertRaises(core.LocalPreEntryUnresolved):source.close()
        self.assertEqual(r.close_calls,[1,1])
    def test_unknown_native_close_witness_never_retries_numeric_handle(self):
        source=native_cleanup_fixture(uncertain=(102,))
        with self.assertRaises(core.LocalPreEntryUnresolved):source.close()
        r=source._resource;self.assertEqual(r.pending[1],(102,'close_issued'));self.assertIsNone(r.pending[0])
        with self.assertRaises(core.LocalPreEntryUnresolved):source.close()
        self.assertEqual(r.close_calls,[1,1])
    def test_transferred_owner_failure_stays_reachable_for_cleanup(self):
        source=fixture();target=source.transfer();r=target._resource
        target._phase='UNRESOLVED';target._failure=ValueError('postcommit')
        with self.assertRaises(core.LocalPreEntryUnresolved):target.close()
        self.assertIs(r.owner,target);self.assertEqual(r.close_calls,[1,1]);source.close()
    def test_all_permissions_and_tcb_authentication_stay_false(self):
        self.assertTrue(all(value is False for value in core.FALSE_GATES.values()))
    def test_profile_and_admission_coherent_swap_breaks_predecessor_freeze(self):
        path=ROOT/'results/tables/staged_rts24_saved_fresh_pre_entry_lease_v1_non_authoritative/driver.py'
        spec=importlib.util.spec_from_file_location('pre_entry_driver_unit',path);driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder);reg=dict(helper_pins={},source_epoch='fixture')
            (out/'registration.json').write_bytes(core.canonical(reg));registration=core.pin(core.canonical(reg))
            (out/'startup_profile.json').write_bytes(b'old-profile');(out/'profile_admission.json').write_bytes(b'old-admission')
            for name in ('unittest','discovery','profile_admission'):
                produced=driver.pins([out/'startup_profile.json',out/'profile_admission.json']) if name=='profile_admission' else {}
                record=dict(accepted=True,label=name,kind='unittest' if name=='unittest' else 'static',registration_pin=registration,
                    helper_pins={},source_epoch='fixture',produced_and_control_pins=produced)
                (out/(name+'.exit.json')).write_bytes(core.canonical(record))
            with mock.patch.object(driver,'OUT',out):
                self.assertEqual(len(driver.prerequisites('probes',reg)),3)
                (out/'startup_profile.json').write_bytes(b'new-profile');(out/'profile_admission.json').write_bytes(b'new-admission')
                with self.assertRaises(AssertionError):driver.prerequisites('probes',reg)
    def test_negative_probe_rejects_unrelated_failure(self):
        spec=importlib.util.spec_from_file_location('pre_entry_parent_unit',ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_parent_v2.py')
        parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
        record=dict({k:False for k in parent.FALSE_FIELDS},schema='staged_saved_F_pre_entry_probe_record_v1',authority='DRAFT_NONAUTHORITATIVE',
            source_epoch=parent.SOURCE_SHA,initial_finders=['_frozen_importlib.BuiltinImporter','_frozen_importlib.FrozenImporter','_frozen_importlib_external.PathFinder'],
            audit_hook_active_at_end=False,dll_directory_close_returned=True,local_pre_entry_continuity_live_at_report=False,
            status='failed',case='environment',primary=dict(type='ValueError',message='unrelated failure'),secondary=[],
            local_pre_entry_continuity_was_held_and_consumed=False,failure_phase='SELF',close_calls=None,entry_compiled_after_self=False,
            local_same_process_transfer_used=False,early_audit_blocked=[])
        with self.assertRaises(AssertionError):parent.compare_child('environment',b'',core.canonical(record)+b'\n',b'',1,None,[],[])

    def compiled_fixture(self):
        raw=(ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v2.py').read_bytes().split(b'\nimport builtins\n',1)[1]
        raw=b'import builtins\n'+raw+b'\n'+(ROOT/'tests/staged_rts24_saved_fresh_pre_entry_probe_v2.py').read_bytes()
        namespace=dict(__name__='_compiled_pre_entry_test',sys=core.sys,_RUNTIME=core._RUNTIME)
        exec(compile(raw,'<pre_entry_payload>','exec',dont_inherit=True,optimize=0),namespace)
        return namespace,raw
    def test_compiled_namespace_accepts_automatic_new_descriptor(self):
        namespace,raw=self.compiled_fixture()
        self.assertIs(type(vars(namespace['_LocalInputs'])['__new__']),staticmethod)
        namespace['check_compiled_namespace'](raw)
    def test_compiled_namespace_rejects_raw_new_function(self):
        namespace,raw=self.compiled_fixture();cls=namespace['_LocalInputs'];descriptor=vars(cls)['__new__']
        setattr(cls,'__new__',descriptor.__func__)
        with self.assertRaisesRegex(ValueError,'exact constructor descriptor required'):namespace['check_compiled_namespace'](raw)
    def test_local_entry_rejects_rewrapped_same_constructor(self):
        owner=fixture();descriptor=vars(core._LocalInputs)['__new__']
        try:
            setattr(core._LocalInputs,'__new__',staticmethod(descriptor.__func__))
            with self.assertRaisesRegex(ValueError,'pre-entry binding changed'):owner.entry()
        finally:setattr(core._LocalInputs,'__new__',descriptor);owner.close()
    def test_local_entry_rejects_constructor_code_replacement(self):
        owner=fixture();function=vars(core._LocalInputs)['__new__'].__func__;original=function.__code__
        try:
            function.__code__=(lambda *args:None).__code__
            with self.assertRaisesRegex(ValueError,'pre-entry callable changed'):owner.entry()
        finally:function.__code__=original;owner.close()


if __name__=='__main__':unittest.main()
