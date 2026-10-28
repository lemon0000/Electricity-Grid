"""Private mechanical fixtures, not an approved outer or P1 execution."""
import ast
import builtins
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import sys
from threading import Thread
import time
from types import CodeType,FunctionType,ModuleType,SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).absolute().parents[1]
PERMISSION=ROOT/'experiments/staged_rts24_saved_fresh_p1_permission_v1.py'
LIFECYCLE=ROOT/'experiments/staged_rts24_saved_fresh_retained_producer_v4.py'
RAW=PERMISSION.read_bytes();LC_RAW=LIFECYCLE.read_bytes()
UTILITY_RAW=(ROOT/'experiments/staged_rts24_saved_fresh_retained_producer_v1.py').read_bytes()


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module


permission=load('_permission_kernel','experiments/staged_rts24_saved_fresh_p1_permission_v1.py')
engine=load('_permission_lifecycle4','experiments/staged_rts24_saved_fresh_retained_producer_v4.py')
lc_transform=load('_permission_lc_transform','experiments/staged_rts24_saved_fresh_permission_lifecycle_transform_v1.py')
wire_transform=load('_permission_wire_transform','experiments/staged_rts24_saved_fresh_permission_bootstrap_transform_v1.py')
legacy_path=ROOT/'tests/test_staged_rts24_saved_fresh_retained_producer_v1.py'
legacy_raw=legacy_path.read_text(encoding='utf8')
needle='        for name,value in values.items():object.__setattr__(producer,name,value)'
assert legacy_raw.count(needle)==1
legacy_raw=legacy_raw.replace(needle,"        values['_permission_revoke']=context['permission_revoke_spec']()\n"+needle)
legacy=ModuleType('_permission_private_lifecycle_fixture');legacy.__file__=str(legacy_path)
exec(compile(legacy_raw,str(legacy_path)+'::permission_fixture','exec',dont_inherit=True,optimize=0),vars(legacy),vars(legacy))
legacy.engine=engine;legacy.RAW=LC_RAW;legacy.PROGRAM=LIFECYCLE
legacy.CORE_RAW=legacy.CORE_RAW.replace(b'from types import FunctionType',b'from types import FunctionType\nimport sys',1)
old=b"self._resource.phase='CLOSED';self._boundary.phase='CLOSED';self._namespace._phase='CLOSED'"
new=b"""self._resource.phase='CLOSED';self._boundary.phase='CLOSED';self._namespace._phase='CONSUMED'
        self._cleanup_started=True;self._failure=primary
        name=self._namespace._aliases[0]
        if self._namespace._modules.get(name) is self._namespace.module:del self._namespace._modules[name]"""
assert legacy.CORE_RAW.count(old)==1;legacy.CORE_RAW=legacy.CORE_RAW.replace(old,new)


def put(obj,**values):
    for name,value in values.items():object.__setattr__(obj,name,value)


class PermissionLifecycleTests(legacy.RetainedProducerTests):
    def setUp(self):
        super().setUp()
        owner=self.owner;ns=owner._namespace;resource=owner._resource
        owner._cleanup_started=False;owner._failure=None;resource.owner=owner
        owner._source=SimpleNamespace(_phase='CONSUMED',_successor=owner,_resource=resource)
        ns._inputs=owner._source;ns._runtime_peer=owner;ns._modules=sys.modules
        ns._reference_registered=False;ns._aliases=('experiments.staged_rts24_saved_fresh_adoption_v1','_saved_F_entry_reference_v1')
        ns.reference=ModuleType('_private_permission_reference')
        owner._boundary._state=('CLOSED',False);owner._boundary.phase='CLOSED'
        # Only this explicit private fixture has an OUTER_BOUND mechanical row.
        # The exported source program below remains unconditionally DISABLED.
        self.permission=permission.allocate(type(owner));state=self.permission
        put(state,owner=owner,boundary=owner._boundary,guard_phase='INSTALLED_DENY',phase='OUTER_BOUND')
        external=object.__new__(permission.ExternalAuthorization)
        put(external,creator=permission.creator(),scope='saved_P1_readonly_diagnostic',source_epoch=permission.SOURCE_EPOCH,deadline=time.monotonic()+30.0)
        state.registry['external']=external
        allowed=frozenset(os.path.normcase(str(path)) for path in (permission.P1/'synthetic.bin',permission.ANCHOR,permission.EXE,permission.INHERITED,*permission.FIXTURE_INPUTS))
        owner._consume_state='PREPARED';owner._seal=self.core.runtime_seal(owner)
        admission=permission.mechanical_issue(state,owner,owner._consumer_plan,self.producer._snapshot,time.monotonic()+20.0,allowed,external)
        permission.mechanical_verify(state,admission,owner,owner._consumer_plan,self.producer._snapshot,'claim')
        owner._consume_state='RUNNING';owner._seal=self.core.runtime_seal(owner)
        self.token=admission;self.context['_P1_AUTHORITY']=admission
        self.permission_events=[]
        def logical_gate(owner,admission,plan,snapshot,stage):
            self.permission_events.append(stage)
            if stage=='retire':return permission.retire(state,admission)
            return permission.mechanical_verify(state,admission,owner,plan,snapshot,stage)
        self.context['permission_call']=logical_gate
        packet=self.context['revoke_window'].__code__,{'__builtins__':{}},(state,object.__setattr__)
        put(self.producer,_authority=admission,_permission_revoke=packet)
        self.context['commit'](self.producer)

    def reset_read_window(self):
        put(self.permission,guard_phase='READ_WINDOW',phase='CLAIMED',deadline=time.monotonic()+20.0)
        self.permission.faults.clear()

    def real_gate(self,spec):
        context=dict(self.context);context['_P1_PERMISSION_RAW']=RAW;context['_P1_PERMISSION_PROGRAM']=spec
        context['_P1_PERMISSION_CODE']=next(code for code in compile(RAW,str(PERMISSION),'exec',dont_inherit=True,optimize=0).co_consts
            if type(code) is CodeType and code.co_name=='program_dispatch')
        return FunctionType(engine.permission_call.__code__,context)

    def test_32_exported_program_rejects_none_tokens_callbacks_and_forged_mode(self):
        spec=permission.source_program(RAW,type(self.owner),UTILITY_RAW)
        call=FunctionType(spec[0],spec[1]);state=spec[2][2]
        for mode in ('DISABLED','OUTER_BOUND','ISSUED','CLAIMED'):
            put(state,phase=mode)
            for operation in ('issue','verify','claim'):
                with self.subTest(mode=mode,operation=operation),self.assertRaises(PermissionError):
                    call(spec[2],operation,(object(),True,lambda:True))
        self.assertEqual(state.counters['allowed'],0);self.assertIsNone(state.admission)
        for value in (None,object(),True,{}):
            with self.subTest(value=type(value).__name__),self.assertRaises((TypeError,ValueError)):
                self.real_gate(value)(self.owner,self.token,self.owner._consumer_plan,self.producer._snapshot,'prepare')

    def test_33_arbitrary_dispatcher_or_builtin_replacement_is_never_called(self):
        calls=[]
        def fake(*args):calls.append(args);return True
        bad=fake.__code__,dict(FunctionType=FunctionType,__builtins__=dict(vars(builtins))),(None,None,None)
        with self.assertRaisesRegex(ValueError,'fixed permission dispatcher'):self.real_gate(bad)(None,None,None,None,'prepare')
        spec=permission.source_program(RAW,type(self.owner),UTILITY_RAW)
        broken=dict(spec[1]);broken['FunctionType']=fake
        with self.assertRaises(ValueError):self.real_gate((spec[0],broken,spec[2]))(None,None,None,None,'prepare')
        self.assertEqual(calls,[])
        with self.assertRaises(PermissionError):self.real_gate(spec)(self.owner,self.token,self.owner._consumer_plan,self.producer._snapshot,'prepare')

    def test_34_private_full_lifecycle_retires_before_physical_close(self):
        seen=[];self.owner.close_callback=lambda:seen.append((self.permission.phase,self.permission.guard_phase))
        self.run_producer();self.invoke('G2');self.invoke('G3');self.invoke('close')
        self.assertEqual(seen,[('RETIRED','DENY')]);self.assertIn('entry',self.permission_events)
        self.assertIsNone(self.producer._permission_revoke)
        self.assertEqual(self.permission_events.count('retire'),1);permission.close_guard(self.permission)
        self.assertEqual(self.permission.guard_phase,'CLOSED')
        self.assertIsNone(self.permission.owner);self.assertIsNone(self.permission.snapshot)

    def test_35_expired_or_revoked_entry_does_zero_capture_and_closes_once(self):
        with patch.object(permission.time,'monotonic',return_value=self.permission.deadline+1.0):
            failure=self.failure(self.run_producer)
        self.assertIn('unexpired',str(failure.primary));self.assertEqual(self.state['capture_calls'],0)
        self.assertEqual(self.permission.guard_phase,'DENY');self.assertEqual(self.owner.close_calls,1)

    def test_36_guard_revocation_during_capture_prevents_next_read(self):
        self.state['capture_callback']=lambda:put(self.permission,guard_phase='DENY')
        self.failure(self.run_producer)
        self.assertEqual(self.state['capture_calls'],1);self.assertEqual(self.state['hold_calls'],0)
        self.assertEqual(self.permission.phase,'RETIRED');self.assertEqual(self.owner.close_calls,1)

    def test_37_wrong_owner_plan_snapshot_clone_and_thread_fail_closed(self):
        args=[self.permission,self.token,self.owner,self.owner._consumer_plan,self.producer._snapshot,'entry']
        for index in (1,2,3,4):
            bad=list(args);bad[index]=object()
            with self.subTest(index=index),self.assertRaises(ValueError):permission.mechanical_verify(*bad)
        errors=[]
        def foreign():
            try:permission.mechanical_verify(*args)
            except BaseException as error:errors.append(error)
        thread=Thread(target=foreign);thread.start();thread.join(1.0)
        self.assertFalse(thread.is_alive());self.assertEqual(len(errors),1)
        self.assertEqual(self.permission.guard_phase,'READ_WINDOW');self.assertEqual(self.owner.close_calls,0)

    def test_38_domain_reads_are_phase_specific_and_writes_processes_always_deny(self):
        source=os.path.normcase(str(ROOT/'src/staged_rts24_saved_fresh_adoption_v1.py'))
        put(self.permission,construction=frozenset((source,)))
        for path in (permission.P1/'synthetic.bin',permission.ANCHOR,permission.EXE,permission.INHERITED,*permission.FIXTURE_INPUTS):
            self.reset_read_window();put(self.permission,guard_phase='INSTALLED_DENY')
            with self.subTest(path=str(path)),self.assertRaises(permission.PermissionUnavailable):
                permission.guard_event(self.permission,'open',(str(path),'r',0))
            self.reset_read_window();permission.guard_event(self.permission,'open',(str(path),'r',0))
        permission.guard_event(self.permission,'open',(source,'r',0))
        permission.guard_event(self.permission,'open',(str(permission.RUNTIME/'Lib/json/__init__.py'),'r',0))
        for event,args in (('open',(str(ROOT/'unlisted.bin'),'r',0)),('open',(str(permission.P1/'synthetic.bin'),'w',os.O_WRONLY)),
                ('open',(str(ROOT/'configs/not_a_fixed_fixture.yaml'),'r',0)),
                ('open',(0,'r',0)),('subprocess.Popen',('python',[],None,None)),('os.rename',('a','b')),
                ('os.scandir',(str(permission.P1),))):
            self.reset_read_window()
            if event=='os.scandir':put(self.permission,guard_phase='DENY')
            with self.subTest(event=event),self.assertRaises(permission.PermissionUnavailable):permission.guard_event(self.permission,event,args)

    def test_39_retirement_proof_fault_cannot_leave_read_window(self):
        original=self.context['permission_call']
        def damaged(*args):
            if args[-1]=='retire':raise ValueError('verifier proof drift')
            return original(*args)
        self.context['permission_call']=damaged
        primary=LookupError('capture failure');self.state['capture_error']=primary
        failure=self.failure(self.run_producer)
        self.assertIs(failure.primary,primary);self.assertEqual(self.permission.guard_phase,'DENY')
        self.assertTrue(any(label=='permission_retirement' for label,_ in failure.secondary));self.assertEqual(self.owner.close_calls,1)
        permission.close_guard(self.permission)
        self.assertEqual(self.permission.phase,'UNRESOLVED');self.assertEqual(self.permission.guard_phase,'CLOSED')

    def test_40_claim_and_retirement_failure_keeps_original_primary_and_zero_slot(self):
        primary=LookupError('claim denied');secondary=OSError('retire damaged')
        def broken(*args):raise secondary if args[-1]=='retire' else primary
        self.context['permission_call']=broken;self.owner._consume_state='PREPARED'
        with self.assertRaises(LookupError) as caught:self.context['claim_permission'](self.producer)
        self.assertIs(caught.exception,primary);self.assertIsInstance(primary.__cause__,BaseExceptionGroup)
        self.assertIn(secondary,primary.__cause__.exceptions);self.assertEqual(self.permission.guard_phase,'DENY')
        self.assertNotIn(id(self.producer),self.context['_LOCKS']);self.assertEqual(self.owner._consume_state,'PREPARED')
        self.assertEqual(self.owner.close_calls,0)

    def test_41_unclaimed_commit_or_lock_failure_retires_exact_row(self):
        self.owner._consume_state='PREPARED';primary=ValueError('pre-slot commit/lock failure')
        with self.assertRaises(ValueError) as caught:self.context['cancel_unclaimed'](self.producer,primary)
        self.assertIs(caught.exception,primary);self.assertNotIn(id(self.producer),self.context['_LOCKS'])
        self.assertEqual(self.owner._consume_state,'PREPARED');self.assertEqual(self.owner.close_calls,0)
        self.assertEqual(self.permission.guard_phase,'DENY');self.assertEqual(self.permission.phase,'RETIRED')

    def test_42_close_guard_before_owner_terminal_keeps_deny(self):
        with self.assertRaises(ValueError):permission.close_guard(self.permission)
        self.assertEqual(self.permission.guard_phase,'DENY');self.assertEqual(self.owner.close_calls,0)
        self.state['capture_error']=LookupError('finish fixture');self.failure(self.run_producer)
        permission.close_guard(self.permission);self.assertEqual(self.permission.guard_phase,'CLOSED')

    def test_43_exact_wiring_preserves_runtime_methods_and_guard_order(self):
        lc_transform.current();wire_transform.current()
        def methods(path):
            unit=compile((ROOT/path).read_bytes(),'<same_runtime>','exec',dont_inherit=True,optimize=0)
            cls=next(code for code in unit.co_consts if type(code) is CodeType and code.co_name=='LocalRuntimeInputs')
            return {code.co_name:code for code in cls.co_consts if type(code) is CodeType}
        self.assertEqual(methods('experiments/staged_rts24_saved_fresh_pre_entry_lease_v41.py'),methods('experiments/staged_rts24_saved_fresh_pre_entry_lease_v42.py'))
        raw=(ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v40.py').read_text(encoding='utf8')
        self.assertLess(raw.index('boundary=bs_helper.open_bootstrap_import_boundary'),raw.index("'install_guard',(boundary,)"))
        self.assertLess(raw.index("'install_guard',(boundary,)"),raw.index('runtime.handoff_audit()'))
        self.assertLess(raw.index("'held_runtime_final_close'"),raw.index("'close_guard',()"))

    def test_44_B_S_optional_process_precedes_new_guard(self):
        callbacks=[];attempts=[]
        class OptionalDenied(Exception):pass
        def bs(event,args):
            if event=='subprocess.Popen':attempts.append(event);raise OptionalDenied()
        callbacks.append(bs)
        def emit(event,*args):
            for callback in callbacks:callback(event,args)
        state=permission.allocate(type(self.owner));put(state,owner=self.owner)
        self.owner._phase='IMPORTING';self.owner._audit_handed_off=False
        self.owner._resource.guard={'active':True};self.owner._boundary._state=('ACTIVE_B3',True)
        self.owner._boundary._creator=self.owner._creator[:2]
        with (patch.object(permission.sys,'addaudithook',callbacks.append),patch.object(permission.sys,'audit',emit)):
            permission.install_guard(state,self.owner._boundary)
            self.assertEqual(len(callbacks),2);self.assertEqual(state.sentinel,1)
            with self.assertRaises(OptionalDenied):emit('subprocess.Popen','synthetic',[],None,None)
        self.assertEqual(attempts,['subprocess.Popen']);self.assertEqual(state.counters['processes'],0)
        self.owner._phase='CLOSED';self.owner._resource.phase='CLOSED';permission.close_guard(state)

    def test_45_original_revoke_packet_survives_permission_source_pin_drift(self):
        context=dict(self.context);context['_P1_PERMISSION_RAW']=b'corrupt'
        self.context['permission_call']=FunctionType(engine.permission_call.__code__,context)
        failure=self.failure(self.run_producer)
        self.assertIn('fixed permission source',str(failure.primary));self.assertEqual(self.permission.guard_phase,'DENY')
        self.assertEqual(self.owner.close_calls,1);self.assertEqual(self.state['capture_calls'],0)

    def fresh_claim_fixture(self):
        put(self.permission,phase='ISSUED',guard_phase='READ_WINDOW')
        self.owner._consume_state='PREPARED';self.owner._seal=self.core.runtime_seal(self.owner)
        put(self.producer,_claimed=False);self.context['commit'](self.producer)
        self.permission_events.clear()

    def assert_cancelled_claim(self):
        self.assertEqual(self.permission_events,['claim','retire'])
        self.assertEqual(self.owner._consume_state,'PREPARED');self.assertEqual(self.owner.close_calls,0)
        self.assertEqual(self.permission.phase,'RETIRED');self.assertEqual(self.permission.guard_phase,'DENY')
        self.assertNotIn(id(self.producer),self.context['_LOCKS'])
        node=next(node for node in ast.parse(LC_RAW).body if type(node) is ast.FunctionDef and node.name=='prepare')
        self.assertIsInstance(node.body[-1],ast.Return)
        self.assertEqual(node.body[-1].value.func.id,'claim_runtime_slot')

    def test_46_real_slot_claim_flow_commit_failure_retires_without_slot(self):
        self.fresh_claim_fixture();primary=LookupError('first pre-slot commit')
        def broken(*args,**kwargs):raise primary
        with patch.dict(self.context,commit=broken):
            with self.assertRaises(LookupError) as caught:self.context['claim_runtime_slot'](self.producer)
        self.assertIs(caught.exception,primary);self.assert_cancelled_claim()

    def test_47_real_slot_claim_flow_lock_failure_retires_without_slot(self):
        self.fresh_claim_fixture();lock=self.context['_CLAIM_LOCK'];self.assertTrue(lock.acquire(False))
        try:
            with self.assertRaisesRegex(ValueError,'claim is already in progress'):self.context['claim_runtime_slot'](self.producer)
        finally:lock.release()
        self.assert_cancelled_claim()

    def test_48_mutated_source_is_rejected_before_its_effect(self):
        changed=RAW+b'\nimport builtins\nbuiltins._P1_PERMISSION_RAW_EFFECT=True\n'
        with patch.object(builtins,'_P1_PERMISSION_RAW_EFFECT',False,create=True):
            with self.assertRaisesRegex(ValueError,'exact loader-held permission source'):
                permission.source_program(changed,type(self.owner),UTILITY_RAW)
            self.assertIs(builtins._P1_PERMISSION_RAW_EFFECT,False)


if __name__=='__main__':unittest.main()
