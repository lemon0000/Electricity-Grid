"""Native audit dispatch into a logical source-bound guard, never a kernel owner."""
import builtins
import importlib.util
from pathlib import Path
import sys
from types import FunctionType,MethodType,SimpleNamespace

ROOT=Path(__file__).absolute().parents[1]
HELPER=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_census1024_none_v2.py'
PROBE=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v31.py'


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


logical=load(ROOT/'tests/test_staged_rts24_saved_fresh_image_pin_v1.py','_held_image_logical_fixture')
logical.OLD=HELPER;logical.NEW=HELPER;logical.PROBE=PROBE
logical.core=load(ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v33.py','_held_image_logical_core')
STATE=dict(installed=False,active=False,module=None,guard=None,proof=None,token=None,audit=None,image=None,inject=None,getters=[])


def install():
    if STATE['installed']:return
    def hook(event,args):
        if not STATE['active']:return
        guard=STATE['guard']
        if event=='object.__getattr__' and args[0] is STATE['image']:
            STATE['getters'].append((args[1],guard._busy))
        STATE['audit'](guard,event,args,STATE['token'],STATE['proof'])
        inject=STATE['inject']
        if inject is not None:inject(event,args)
    sys.addaudithook(hook);STATE['installed']=True


def new_guard():
    assert not STATE['active']
    module=logical.helper(HELPER,'_held_native_guard')
    guard,proof,token=logical.logical_guard(module)
    return module,guard,proof,token


def gated(module,guard,proof,token,operation,inject=None):
    install();assert not STATE['active']
    STATE.update(module=module,guard=guard,proof=proof,token=token,audit=module.BootstrapImportBoundary._audit,
        image=module.BootstrapImportBoundary._image,inject=inject,getters=[])
    STATE['active']=True
    try:return operation()
    finally:
        STATE['active']=False;STATE['inject']=None;STATE['module']=STATE['guard']=STATE['proof']=STATE['token']=STATE['audit']=STATE['image']=None


def opened():sys.audit('open','D:/allowed/read-only-unit','r',0)


class NativeImageTests:
    def test_09_actual_proof_and_getter_audit_before_busy(self):
        module,g,proof,token=new_guard();image=module.BootstrapImportBoundary._image
        rows=[r for r in proof if r[0] is module.BootstrapImportBoundary and r[1]=='_image']
        self.assertEqual(len(rows),1);self.assertIs(rows[0][2],image);self.assertIs(rows[0][3][1][0],builtins.id)
        before=g._state[5];gated(module,g,proof,token,opened)
        self.assertEqual(g._state[5],before);self.assertFalse(g._busy);self.assertEqual(g._state[0],'ACTIVE')
        getters=list(STATE['getters']);self.assertTrue(getters)
        self.assertIn('__code__',[n for n,busy in getters]);self.assertIn('__defaults__',[n for n,busy in getters])
        self.assertTrue(all(not busy for n,busy in getters));self.assertFalse(STATE['active'])

    def test_10_actual_setter_trap_covers_image_in_both_busy_states(self):
        for busy in (False,True):
            for attr in ('__code__','__defaults__','__kwdefaults__'):
                module,g,proof,token=new_guard();image=module.BootstrapImportBoundary._image;value=getattr(image,attr)
                object.__setattr__(g,'_busy',busy)
                try:
                    with self.assertRaises(module.BootstrapImportRejected) as caught:
                        gated(module,g,proof,token,lambda:setattr(image,attr,value))
                    self.assertIn('helper_or_finder_function_mutation',str(caught.exception))
                    self.assertIs(getattr(image,attr),value);self.assertEqual(g._state[0],'FAULTED')
                    self.assertIs(g._first_error,caught.exception)
                finally:object.__setattr__(g,'_busy',False)

    def test_11_defaults_and_recomputed_commit_still_rejected_without_image_use(self):
        module,g,proof,token=new_guard();image=module.BootstrapImportBoundary._image;old=image.__defaults__;calls=[]
        def fake_id(value):calls.append(value);return id(value)
        image.__defaults__=(fake_id,)
        try:
            object.__setattr__(g,'_commit',module.digest(image(g)));calls.clear();commit=g._commit
            with self.assertRaises(module.BootstrapImportRejected) as caught:gated(module,g,proof,token,opened)
            self.assertIn('image_metadata',str(caught.exception));self.assertEqual(calls,[])
            self.assertEqual(g._commit,commit);self.assertEqual(g._state[0],'FAULTED')
        finally:image.__defaults__=old

    def test_12_same_code_default_clone_binding_rejected_at_entry(self):
        module,g,proof,token=new_guard();cls=module.BootstrapImportBoundary;image=cls._image
        clone=FunctionType(image.__code__,image.__globals__,image.__name__,image.__defaults__,image.__closure__)
        cls._image=clone
        try:
            with self.assertRaises(module.BootstrapImportRejected) as caught:gated(module,g,proof,token,opened)
            self.assertIn('image_metadata',str(caught.exception));self.assertEqual(g._state[0],'FAULTED')
        finally:cls._image=image

    def test_13_midcall_class_replacement_uses_held_fn_then_next_entry_rejects(self):
        for name in ('_image','_observe_machinery','_audit_entry'):
            module,g,proof,token=new_guard();cls=module.BootstrapImportBoundary;original=getattr(cls,name);calls=[];injected=[]
            def replacement(self):calls.append(self);return original(self)
            def inject(event,args):
                ready=(event=='object.__getattr__' and args[0] is STATE['image'] and not g._busy) if name=='_audit_entry' else (event=='builtins.id' and g._busy)
                if ready and not injected:
                    injected.append(True);setattr(cls,name,replacement);STATE['inject']=None
            try:
                if name=='_audit_entry':
                    with self.assertRaises(module.BootstrapImportRejected):gated(module,g,proof,token,opened,inject)
                else:
                    gated(module,g,proof,token,opened,inject)
                    self.assertEqual(g._state[0],'ACTIVE')
                    with self.assertRaises(module.BootstrapImportRejected):gated(module,g,proof,token,opened)
                self.assertEqual(injected,[True]);self.assertEqual(calls,[]);self.assertEqual(g._state[0],'FAULTED')
            finally:setattr(cls,name,original)

    def test_14_exact_type_and_sticky_cleanup_reject_before_untrusted_image(self):
        module,g,proof,token=new_guard()
        fake=SimpleNamespace(_state=g._state,_event_sets=g._event_sets,_busy=False,_creator=g._creator,
            _lock=g._lock,_owner=g._owner,_finder_bindings=(),_first_error=None)
        fake._fault=MethodType(module.BootstrapImportBoundary._fault,fake)
        with self.assertRaises(module.BootstrapImportRejected) as caught:gated(module,fake,proof,token,opened)
        self.assertIn('image_metadata',str(caught.exception))
        module,g,proof,token=new_guard();image=module.BootstrapImportBoundary._image;old=image.__defaults__;calls=[]
        def fake_id(value):calls.append(value);return id(value)
        image.__defaults__=(fake_id,);primary=OSError('caller primary')
        try:
            with self.assertRaises(module.BootstrapImportUnresolved) as caught:g.close(primary)
            failure=caught.exception;self.assertIs(failure.primary,primary);self.assertTrue(failure.cleanup)
            self.assertEqual(failure.cleanup[0][0],'bindings');self.assertEqual(calls,[])
            self.assertEqual(g._state[0],'FAULTED');self.assertFalse(g._state[1]);self.assertTrue(g._state[6])
            with self.assertRaises(module.BootstrapImportUnresolved) as again:g.close(ValueError('later'))
            self.assertIs(again.exception,failure);self.assertEqual(calls,[])
            report=module.parse(g.report_raw)
            for name in ('full_runtime_binding_verified','full_P1_content_verified','permit_issued','actual_F','run_authority','scientific_evidence_adopted','resource_admission','formal_result'):
                self.assertIs(report[name],False)
        finally:image.__defaults__=old
