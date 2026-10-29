"""Source-connected cleanup tests; kernel and role effects remain synthetic."""
import ast
import dis
from hashlib import sha256
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).absolute().parents[1]
CORE_TEST=ROOT/'tests/test_staged_rts24_saved_fresh_source_cleanup_v4.py'
ROLE_TEST=ROOT/'tests/test_staged_rts24_saved_fresh_full_context_role_runtime_v4.py'


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


C=load(CORE_TEST,'_binding_core_fixture')
R=load(ROLE_TEST,'_binding_role_fixture')


def call_sites(code):
    """Both opcode edges of each actual binding/mirror/claim call."""
    text='import builtins\n'+C.SOURCE.read_text(encoding='utf-8').split('\nimport builtins\n',1)[1];tree=ast.parse(text)
    if code.co_name=='commit_cleanup_binding':
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==code.co_name)
    else:
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='LocalRuntimeInputs')
        node=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==code.co_name)
    calls=[]
    for n in ast.walk(node):
        if not isinstance(n,ast.Call):continue
        name=ast.unparse(n.func)
        if name in ('object.__setattr__','commit_cleanup_binding','_append') or name.startswith('spec[0]('):
            calls.append((n.lineno,n.col_offset,n.end_lineno,n.end_col_offset))
    instructions=list(dis.get_instructions(code));sites=[]
    for index,item in enumerate(instructions):
        p=item.positions
        if item.opname=='CALL' and (p.lineno,p.col_offset,p.end_lineno,p.end_col_offset) in calls:
            sites.extend(((item.offset,'before'),(instructions[index+1].offset,'after')))
    assert sites and len(sites)==2*len(calls),(code.co_name,len(calls),sites)
    if code.co_name=='own_pending_boundary':
        claim=next(n for n in ast.walk(node) if isinstance(n,ast.Call) and ast.unparse(n.func).startswith('spec[0]('))
        span=(claim.lineno,claim.col_offset,claim.end_lineno,claim.end_col_offset)
        assert span in calls and any(i.opname=='CALL' and (i.positions.lineno,i.positions.col_offset,i.positions.end_lineno,i.positions.end_col_offset)==span for i in instructions)
    return tuple(sites)


def inject(code,offset,operation):
    error=RuntimeError('finite opcode fault');seen=[]
    def trace(frame,event,arg):
        if frame.f_code is code:
            frame.f_trace_opcodes=True
            if event=='opcode' and frame.f_lasti==offset and not seen:
                seen.append(offset);raise error
        return trace
    try:
        sys.settrace(trace)
        operation()
    except RuntimeError as caught:
        assert caught is error
    finally:sys.settrace(None)
    assert seen==[offset]
    return error


def contract():
    core=C.load_core()
    sites={name:call_sites(getattr(core.LocalRuntimeInputs,name).__code__)
           for name in ('prepare_boundary','own_pending_boundary')}
    sites['commit_cleanup_binding']=call_sites(core.commit_cleanup_binding.__code__)
    return dict(core=C.contract(),role=R.contract(),fault_sites=sites,
        exact_core_role_cleanup_join=True,actual_entry_authenticated=False,
        project_target_child_processes=0,P1_reads=0,source49_modules_executed=0,
        project_native_leaf_calls=0,run_authority=False,actual_F=False)


def live_core():
    f=C.Fixture();f.prepare()
    # Explicit synthetic completed-import/runtime state; no actual role authority.
    f.boundary._state=('CLOSED',False,0,0,0,0,True,'')
    object.__setattr__(f.owner,'_phase','LIVE');object.__setattr__(f.owner,'_consume_state','RUNNING')
    object.__setattr__(f.owner,'_seal',f.core.runtime_seal(f.owner))
    return f


class CleanupBindingTests(unittest.TestCase):
    def finish_failure(self,f,error):
        with self.assertRaises(f.core.LocalRuntimeUnresolved) as caught:f.close(error)
        self.assertIs(caught.exception.primary,error)
        self.assertEqual(f.resource.close_calls,[1,1]);self.assertEqual(f.resource.phase,'CLOSED')
        before=list(f.leaf_calls)
        with self.assertRaises(f.core.LocalRuntimeUnresolved) as again:f.close()
        self.assertIs(again.exception,caught.exception);self.assertEqual(f.leaf_calls,before)
        self.assertFalse(f.resource.guard['active']);self.assertFalse(f.core._EARLY['active'])
        self.assertEqual(f.modules,{})
        return caught.exception

    def test_01_stable_anchor_and_complete_records(self):
        f=C.Fixture();anchor=f.owner._runtime_cleanup_anchor;image=f.owner._runtime_cleanup_seal
        f.prepare();self.assertIs(f.owner._runtime_cleanup_anchor,anchor)
        self.assertIs(f.owner._runtime_cleanup_seal,image)
        journal=dict(anchor)['binding_journal'];self.assertEqual(len(journal),3)
        self.assertIs(journal[1][1],journal[0]);self.assertIs(journal[2][1],journal[1])
        self.assertIs(journal[2][3][0],f.boundary);f.close()
        with self.assertRaises(ValueError):f.core.seal_runtime_cleanup(f.owner)

    def test_02_spec_every_publication_and_mirror_edge(self):
        reference=C.load_core().LocalRuntimeInputs.prepare_boundary.__code__
        for offset,edge in call_sites(reference):
            with self.subTest(offset=offset,edge=edge):
                f=C.Fixture();anchor=f.owner._runtime_cleanup_anchor
                error=inject(f.core.LocalRuntimeInputs.prepare_boundary.__code__,offset,lambda:f.prepare(False))
                self.assertIs(f.owner._runtime_cleanup_anchor,anchor);self.finish_failure(f,error)

    def test_03_object_every_publication_mirror_and_claim_edge(self):
        reference=C.load_core().LocalRuntimeInputs.own_pending_boundary.__code__
        for offset,edge in call_sites(reference):
            with self.subTest(offset=offset,edge=edge):
                f=C.Fixture();f.prepare(False);anchor=f.owner._runtime_cleanup_anchor
                error=inject(f.core.LocalRuntimeInputs.own_pending_boundary.__code__,offset,lambda:f.owner.own_pending_boundary(f.boundary))
                committed=len(dict(anchor)['binding_journal'])==3
                self.assertIs(f.owner._runtime_cleanup_anchor,anchor);self.finish_failure(f,error)
                if committed:self.assertFalse(f.boundary._state[1])

    def test_04_actual_append_before_and_after_both_generations(self):
        reference=C.load_core().commit_cleanup_binding.__code__
        for stage in ('SPEC','OBJECT'):
            for offset,edge in call_sites(reference):
                with self.subTest(stage=stage,edge=edge):
                    f=C.Fixture()
                    if stage=='OBJECT':f.prepare(False)
                    operation=(lambda:f.prepare(False)) if stage=='SPEC' else (lambda:f.owner.own_pending_boundary(f.boundary))
                    error=inject(f.core.commit_cleanup_binding.__code__,offset,operation)
                    self.finish_failure(f,error)
                    if stage=='OBJECT' and edge=='after':self.assertFalse(f.boundary._state[1])

    def test_05_corrupt_journal_cannot_suppress_native_cleanup(self):
        for case in ('empty','foreign','reorder','truncate','generation','bool_generation','shape'):
            with self.subTest(case=case):
                f=C.Fixture();f.prepare();journal=dict(f.owner._runtime_cleanup_anchor)['binding_journal']
                if case=='empty':journal.clear()
                elif case=='foreign':journal[-1]=object()
                elif case=='reorder':journal[1],journal[2]=journal[2],journal[1]
                elif case=='truncate':journal.pop()
                else:
                    row=journal[-1]
                    journal[-1]=(99 if case=='generation' else True if case=='bool_generation' else row[0],row[1],row[2],(object(),) if case=='shape' else row[3])
                failure=self.finish_failure(f,RuntimeError(case))
                self.assertIn('cleanup_roots',dict(failure.secondary))
                self.assertTrue(f.boundary._state[1]);self.assertNotEqual(f.owner._phase,'CLOSED')

    def test_06_original_boundary_survives_packet_loss(self):
        f=C.Fixture();f.prepare();object.__setattr__(f.packet,'boundary',None)
        self.finish_failure(f,RuntimeError('mirror loss'));self.assertFalse(f.boundary._state[1])

    def test_07_core_source_capture_is_closed_and_owner_specific(self):
        f=live_core();m=R.load_original();raw=C.SOURCE.read_bytes()
        cap=m._capture_core_owner_cleanup(f.owner,raw,vars(f.core))
        self.assertIs(cap.owner,f.owner);self.assertEqual(cap.packet[1],{'__builtins__':{}})
        self.assertIs(cap.packet[2],f.core.LocalRuntimeInputs.close.__defaults__)
        with self.assertRaises(ValueError):m._capture_core_owner_cleanup(f.owner,raw+b'\n',vars(f.core))
        with self.assertRaises(m.FullRoleUnavailable):m._cleanup_call(cap.packet,None)
        with self.assertRaises(TypeError):m.CoreOwnerCleanup()
        with self.assertRaises(ValueError):m._check_core_cleanup((cap.packet,cap.wrapper,cap.owner))
        for case in ('ADOPTED','ledger','journal','mirror'):
            bad=live_core()
            if case=='ADOPTED':object.__setattr__(bad.owner,'_phase','ADOPTED')
            elif case=='ledger':dict(bad.owner._runtime_cleanup_anchor)['ledger'][0]='RUNNING'
            elif case=='journal':dict(bad.owner._runtime_cleanup_anchor)['binding_journal'].pop()
            else:object.__setattr__(bad.packet,'boundary',None)
            with self.assertRaises(ValueError):m._capture_core_owner_cleanup(bad.owner,raw,vars(bad.core))
        original=f.core.run_runtime_cleanup.__defaults__
        f.core.run_runtime_cleanup.__defaults__=(None,())
        with self.assertRaises(ValueError):m._check_core_cleanup(cap)
        f.core.run_runtime_cleanup.__defaults__=original
        f.close()

    def test_08_role_source_cleanup_success_uses_original_owner(self):
        f=live_core()
        r=R.Fixture('fresh',core_binding=(f.owner,C.SOURCE.read_bytes(),vars(f.core)))
        self.assertEqual(r.m._close_once(r.session,None),())
        self.assertTrue(r.session._runtime_closed);self.assertTrue(r.session._closed)
        self.assertEqual(f.resource.close_calls,[1,1]);self.assertNotIn('owner_close',r.state['events'])
        self.assertEqual(r.m._close_once(r.session,None),());self.assertEqual(f.resource.close_calls,[1,1])

    def test_09_role_preserves_actual_core_primary_carrier(self):
        f=live_core()
        r=R.Fixture('fresh',core_binding=(f.owner,C.SOURCE.read_bytes(),vars(f.core)));primary=KeyboardInterrupt('source primary')
        self.assertEqual(r.m._close_once(r.session,primary),())
        self.assertIs(r.session._runtime_carrier,f.owner._failure)
        self.assertIs(r.session._runtime_carrier.primary,primary);self.assertTrue(r.session._runtime_closed)
        self.assertEqual(f.resource.close_calls,[1,1])

    def test_10_role_child_errors_do_not_suppress_core_finally(self):
        f=live_core()
        r=R.Fixture('parent',core_binding=(f.owner,C.SOURCE.read_bytes(),vars(f.core)))
        object.__setattr__(r.session,'_child',r.state['child']);object.__setattr__(r.session,'_child_terminal',False)
        r.state['abort_error']=RuntimeError('child abort');primary=RuntimeError('primary')
        errors=r.m._close_once(r.session,primary)
        self.assertIn('child_abort',dict(errors));self.assertTrue(r.session._runtime_closed)
        self.assertFalse(r.session._child_terminal);self.assertFalse(r.session._closed)
        self.assertEqual(f.resource.close_calls,[1,1])


    def test_11_bind_then_source_drift_rejects_before_effect_and_cleans(self):
        f=live_core();r=R.Fixture('fresh',core_binding=(f.owner,C.SOURCE.read_bytes(),vars(f.core)))
        f.core.run_runtime_cleanup.__defaults__=(None,());r.state['clock_calls']=0
        with self.assertRaises(r.m._FAILURE_TYPES) as caught:r.run('reconstruct')
        self.assertIn('captured Core function changed',str(caught.exception.primary))
        self.assertEqual(r.state['clock_calls'],0)
        self.assertNotIn('hold',r.state['events']);self.assertNotIn('replay',r.state['events'])
        self.assertEqual(f.resource.close_calls,[1,1]);self.assertEqual(f.resource.phase,'CLOSED')
        before=list(f.leaf_calls)
        with self.assertRaises(r.m._FAILURE_TYPES) as again:r.run('reconstruct')
        self.assertIs(again.exception,caught.exception);self.assertEqual(f.leaf_calls,before)


if __name__=='__main__':unittest.main()
