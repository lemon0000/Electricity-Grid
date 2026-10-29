"""Source-connected cleanup tests; kernel and role effects remain synthetic."""
import ast
import dis
from hashlib import sha256
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).absolute().parents[1]
CORE_TEST=ROOT/'tests/test_staged_rts24_saved_fresh_source_cleanup_v5.py'
ROLE_TEST=ROOT/'tests/test_staged_rts24_saved_fresh_full_context_role_runtime_v5.py'


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


C=load(CORE_TEST,'_binding_core_fixture')
R=load(ROLE_TEST,'_binding_role_fixture')


def call_sites(code):
    """Source-bound expression-before / call-after markers, never CALL events."""
    text='import builtins\n'+C.SOURCE.read_text(encoding='utf-8').split('\nimport builtins\n',1)[1];tree=ast.parse(text)
    if code.co_name=='commit_cleanup_binding':
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==code.co_name)
    else:
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='LocalRuntimeInputs')
        node=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==code.co_name)
    instructions=list(dis.get_instructions(code));sites=[]
    for call in ast.walk(node):
        if not isinstance(call,ast.Call):continue
        name=ast.unparse(call.func)
        if name not in ('object.__setattr__','commit_cleanup_binding','_append') and not name.startswith('spec[0]('):continue
        span=(call.lineno,call.col_offset,call.end_lineno,call.end_col_offset)
        matches=[i for i,item in enumerate(instructions) if item.opname=='CALL' and
                 (item.positions.lineno,item.positions.col_offset,item.positions.end_lineno,item.positions.end_col_offset)==span]
        assert len(matches)==1
        index=matches[0];offset=instructions[index].offset;after=instructions[index+1].offset
        before=min(item.offset for item in instructions[:index] if item.positions.lineno==call.lineno and item.positions.col_offset==call.col_offset)
        assert before<offset<after
        row=dict(source_span=span,call_offset=offset,before_marker=before,after_marker=after,before_event_domain=('line','opcode'))
        if name=='object.__setattr__':
            subject,field,value=call.args;assert isinstance(subject,ast.Name) and isinstance(field,ast.Constant)
            row.update(kind='mirror',subject=subject.id,field=field.value)
            if isinstance(value,ast.Name):row.update(value_kind='local',value=value.id)
            elif isinstance(value,ast.Constant):row.update(value_kind='constant',value=value.value)
            elif isinstance(value,ast.Call) and ast.unparse(value)=='type(boundary)' and not value.keywords:
                row.update(value_kind='pure_type_local',value='boundary')
            else:
                assert ast.unparse(value)=='runtime_seal(self)'
                row.update(value_kind='pure_runtime_seal',value=None)
        elif name in ('commit_cleanup_binding','_append'):row.update(kind='append',subject=name)
        else:
            assert ast.unparse(call.args[0])=='boundary' and ast.unparse(call.args[1])=='self'
            assert ast.unparse(call.func.func)=='spec[0]'
            row.update(kind='claim',subject='source_FunctionType_then_claim')
        sites.append(row)
    assert sites
    if code.co_name=='own_pending_boundary':assert sum(row['kind']=='claim' for row in sites)==1
    return tuple(sorted(sites,key=lambda row:row['call_offset']))


def inject(code,site,edge,operation,state):
    error=RuntimeError('finite expression/call boundary fault');seen=[];before=[]
    def snapshot(frame):
        local=frame.f_locals
        if site['kind']=='append':
            journal=local['journal'] if site['subject']=='_append' else dict(local['self']._runtime_cleanup_anchor)['binding_journal']
            return dict(read=lambda:(len(journal),journal[-1]),old=(len(journal),journal[-1]))
        if site['kind']=='claim':return dict(read=lambda:state.get('claim_calls',0),old=state.get('claim_calls',0))
        subject=local[site['subject']];field=site['field'];kind=site['value_kind']
        expected=local[site['value']] if kind=='local' else type(local[site['value']]) if kind=='pure_type_local' else site['value']
        return dict(read=lambda:object.__getattribute__(subject,field),old=object.__getattribute__(subject,field),expected=expected)
    def trace(frame,event,arg):
        if frame.f_code is code:
            frame.f_trace_opcodes=True
            if event in ('line','opcode'):
                if frame.f_lasti==site['before_marker'] and not before:
                    before.append(snapshot(frame))
                    if edge=='before':seen.append((event,frame.f_lasti));raise error
                if edge=='after' and frame.f_lasti==site['after_marker'] and not seen:
                    assert before;seen.append((event,frame.f_lasti));raise error
        return trace
    try:
        sys.settrace(trace);operation()
    except RuntimeError as caught:assert caught is error
    finally:sys.settrace(None)
    assert len(seen)==len(before)==1,(site,edge,seen)
    witness=before[0];actual=witness['read']();old=witness['old']
    if edge=='before':
        if site['kind'] in ('append','claim'):assert actual==old
        else:assert actual is old
    elif site['kind']=='append':assert actual[0]==old[0]+1 and actual[1][0]==old[0] and actual[1][1] is old[1]
    elif site['kind']=='claim':assert actual==old+1
    elif site['value_kind']=='pure_runtime_seal':assert actual is not old and type(actual) is tuple
    elif site['value_kind']=='constant':assert type(actual) is type(witness['expected']) and actual==witness['expected']
    else:assert actual is witness['expected']
    return error


def contract():
    core=C.load_core()
    sites={name:call_sites(getattr(core.LocalRuntimeInputs,name).__code__)
           for name in ('prepare_boundary','own_pending_boundary')}
    sites['commit_cleanup_binding']=call_sites(core.commit_cleanup_binding.__code__)
    assert tuple(len(sites[name]) for name in ('prepare_boundary','own_pending_boundary','commit_cleanup_binding'))==(11,11,1)
    return dict(core=C.contract(),role=R.contract(),fault_sites=sites,fault_cases=48,locator_domain='expression_before_call_after',
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
        for site in call_sites(reference):
            for edge in ('before','after'):
                with self.subTest(call=site['call_offset'],edge=edge):
                    f=C.Fixture();anchor=f.owner._runtime_cleanup_anchor
                    error=inject(f.core.LocalRuntimeInputs.prepare_boundary.__code__,site,edge,lambda:f.prepare(False),f.state)
                    self.assertIs(f.owner._runtime_cleanup_anchor,anchor);self.finish_failure(f,error)

    def test_03_object_every_publication_mirror_and_claim_edge(self):
        reference=C.load_core().LocalRuntimeInputs.own_pending_boundary.__code__
        for site in call_sites(reference):
            for edge in ('before','after'):
                with self.subTest(call=site['call_offset'],edge=edge):
                    f=C.Fixture();f.prepare(False);anchor=f.owner._runtime_cleanup_anchor
                    error=inject(f.core.LocalRuntimeInputs.own_pending_boundary.__code__,site,edge,lambda:f.owner.own_pending_boundary(f.boundary),f.state)
                    committed=len(dict(anchor)['binding_journal'])==3
                    self.assertIs(f.owner._runtime_cleanup_anchor,anchor);self.finish_failure(f,error)
                    if committed:self.assertFalse(f.boundary._state[1])

    def test_04_actual_append_before_and_after_both_generations(self):
        reference=C.load_core().commit_cleanup_binding.__code__
        for stage in ('SPEC','OBJECT'):
            for site in call_sites(reference):
                for edge in ('before','after'):
                    with self.subTest(stage=stage,call=site['call_offset'],edge=edge):
                        f=C.Fixture()
                        if stage=='OBJECT':f.prepare(False)
                        operation=(lambda:f.prepare(False)) if stage=='SPEC' else (lambda:f.owner.own_pending_boundary(f.boundary))
                        error=inject(f.core.commit_cleanup_binding.__code__,site,edge,operation,f.state)
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
