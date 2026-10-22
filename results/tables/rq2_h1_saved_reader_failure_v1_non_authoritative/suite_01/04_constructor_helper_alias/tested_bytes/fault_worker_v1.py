"""One fixed saved Reader fault case; no source/Job production or native solve."""
import ast
import ctypes
from ctypes import wintypes
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
sys.path.insert(0,str(REPO))
sys.path.insert(1,str(REPO/'tests'))
CASE=Path('D:/h1_outage_connected_03_non_authoritative/test_three_hour_connected_outa0')
CASES=('constructor_primary','constructor_parent_alias','constructor_parent_code',
    'constructor_helper_alias','constructor_Path_alias','post_constructor_primary',
    'final_read_sharing_error','unselected_packet_drift','final_namespace_read_result')


def pin(path):return sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_bytes())
def inventory(root):return {str(p):pin(p) for p in root.rglob('*') if p.is_file()}


def assignment_line(path,class_name,function_name,target,attribute):
    tree=ast.parse(Path(path).read_text(encoding='utf-8'))
    body=tree.body
    if class_name is not None:
        body=next(node for node in body if isinstance(node,ast.ClassDef) and node.name==class_name).body
    function=next(node for node in body if isinstance(node,ast.FunctionDef) and node.name==function_name)
    matches=[node.lineno for node in ast.walk(function) if isinstance(node,ast.Assign)
        and any(isinstance(name,ast.Name) and name.id==target for name in node.targets)
        and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Attribute)
        and node.value.func.attr==attribute]
    if len(matches)!=1:raise ValueError('exact one actual Reader landmark required')
    return matches[0]


class ReadSharingDenial:
    """Temporary read-only Windows handle; existing content is never written."""
    def __init__(self,path):
        if os.name!='nt':raise RuntimeError('Windows sharing test required')
        self.path=Path(path);self.handle=None;self.close_confirmed=False
        self.api=ctypes.WinDLL('kernel32',use_last_error=True)
        self.api.CreateFileW.argtypes=(wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,
            wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE)
        self.api.CreateFileW.restype=wintypes.HANDLE
        self.api.CloseHandle.argtypes=(wintypes.HANDLE,)
        self.api.CloseHandle.restype=wintypes.BOOL

    def open(self):
        if self.handle is not None:raise ValueError('sharing handle already open')
        # GENERIC_READ, no sharing, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL.
        handle=self.api.CreateFileW(str(self.path),0x80000000,0,None,3,0x80,None)
        if handle==wintypes.HANDLE(-1).value:raise ctypes.WinError(ctypes.get_last_error())
        self.handle=handle

    def close(self):
        if self.handle is not None:
            if not self.api.CloseHandle(self.handle):raise ctypes.WinError(ctypes.get_last_error())
            self.handle=None;self.close_confirmed=True

    def conflict_error(self):
        handle=self.api.CreateFileW(str(self.path),0x80000000,7,None,3,0x80,None)
        if handle==wintypes.HANDLE(-1).value:return ctypes.get_last_error()
        if not self.api.CloseHandle(handle):raise ctypes.WinError(ctypes.get_last_error())
        return None


class InjectedPrimary(ValueError):pass


class FaultWindow:
    """Trace only four exact code objects; profile records real lifecycle calls."""
    def __init__(self,module,label,patch,root):
        self.module,self.label,self.patch,self.root=module,label,patch,Path(root)
        self.replay_code=module.replay_prefixes.__code__
        self.constructor_code=module.history.HistoricalSnapshot.__init__.__code__
        self.packet_code=module._validate_all_packets.__code__
        self.namespace_code=module.support.observe_parent_names.__code__
        self.code_ids={id(code) for code in (self.replay_code,self.constructor_code,self.packet_code,self.namespace_code)}
        self.constructor_line=assignment_line(module.history.__file__,'HistoricalSnapshot','__init__','state','inspect')
        self.post_line=assignment_line(module.__file__,None,'replay_prefixes','state','_take_constructor_inspection')
        self.reader=None;self.inner={};self.outer=[];self.containers={}
        self.fired=False;self.namespace_calls=0;self.denial=None;self.primary=None
        self.injection_count=0;self.injection_position=None;self.instrumentation_errors=[]
        self.packet_digests=None;self.sharing_identity=None;self.namespace_seam_reads=0
        self.native_sharing_error=None
        self.packet_loop_raised=False
        self.close_calls=[];self.counts=dict(job_inspections=0,stage_inspections=0,normal_after_returns=0)
        self.after_code=None
        self.job_code=module.binding.snapshot.parent.inspect_job.__code__
        from experiments import h1_timed_stage_development_v1 as stage
        self.stage_code=stage.inspect.__code__
        self.parent_code=module.binding.snapshot.parent.SourceParent.close.__code__
        self.before_all_packet_keys=[];self.reader_closed_before_finally=None

    def retain(self,frame):
        self.reader=frame.f_locals['self']
        self.after_code=type(self.reader)._after.__code__
        self.inner={name:getattr(self.reader,name) for name in ('_journal','_anchor','_root_lease')}
        if any(value is None for value in self.inner.values()):raise AssertionError('actual three owners required')
        caller=frame.f_back
        while caller is not None and caller.f_code is not self.replay_code:caller=caller.f_back
        if caller is None:raise AssertionError('real replay frame required at constructor boundary')
        self.outer=list(caller.f_locals['leases'])
        self.containers={name:caller.f_locals[name] for name in ('captured','all_packets','seen_hours')}
        if len(self.outer)!=4:raise AssertionError('actual four outer ReadViews required')

    def inject_constructor(self):
        parent=self.module.binding.snapshot.parent.SourceParent
        self.fired=True;self.injection_count+=1
        if self.label=='constructor_primary':
            self.primary=InjectedPrimary('actual constructor after three owners')
            raise self.primary
        if self.label=='constructor_parent_alias':
            self.patch.setattr(parent,'close',lambda self:None)
        if self.label=='constructor_parent_code':
            self.patch.setattr(parent.close,'__code__',(lambda self:None).__code__)
        if self.label=='constructor_helper_alias':
            self.patch.setattr(self.module.support,'close_replay',lambda *a:None)
        if self.label=='constructor_Path_alias':
            original=Path.read_bytes
            self.patch.setattr(Path,'read_bytes',lambda path:original(path))
        try:self.module._CHECK_DEPENDENCIES()
        except BaseException as error:
            self.primary=error
            raise
        raise AssertionError('concrete dependency drift was not rejected')

    def trace(self,frame,event,arg):
        if id(frame.f_code) not in self.code_ids:return None
        try:return self._trace(frame,event,arg)
        except BaseException as error:
            if error is not self.primary:
                self.instrumentation_errors.append(type(error).__name__+': '+str(error)[:512])
            raise

    def mark(self,frame):
        self.injection_position=dict(file=frame.f_code.co_filename,function=frame.f_code.co_name,
            line=frame.f_lineno,lasti=frame.f_lasti,event='one registered trace landmark')

    def _trace(self,frame,event,arg):
        if frame.f_code is self.constructor_code and event=='line' and frame.f_lineno==self.constructor_line:
            self.retain(frame)
            if self.label.startswith('constructor_'):
                self.mark(frame);self.inject_constructor()
        if not self.fired and frame.f_code is self.replay_code and event=='line' and frame.f_lineno==self.post_line:
            if self.label=='post_constructor_primary':
                self.fired=True;self.injection_count+=1;self.mark(frame)
                self.primary=InjectedPrimary('actual post-constructor before capture take')
                raise self.primary
        if frame.f_code is self.packet_code:
            if event=='exception':self.packet_loop_raised=True
            if event=='call':
                self.before_all_packet_keys=list(frame.f_locals['packets'])
                if self.label=='unselected_packet_drift' and not self.fired:
                    packet=frame.f_locals['packets'][0][0]
                    before=self.module._packet_digest(packet)
                    object.__setattr__(packet,'input_identity','f'*64)
                    self.packet_digests=[before,self.module._packet_digest(packet)]
                    self.fired=True;self.injection_count+=1;self.mark(frame)
            if event=='return' and not self.packet_loop_raised and self.label=='final_read_sharing_error' and not self.fired:
                self.denial=ReadSharingDenial(self.root/'obligation_non_authoritative/000.terminal.json')
                info=self.denial.path.stat()
                self.sharing_identity=(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_nlink)
                self.denial.open();self.native_sharing_error=self.denial.conflict_error()
                if self.native_sharing_error!=32:raise AssertionError('expected native sharing conflict before Reader read')
                self.fired=True;self.injection_count+=1;self.mark(frame)
        if frame.f_code is self.namespace_code and event=='call':
            self.namespace_calls+=1
            if self.label=='final_namespace_read_result' and self.namespace_calls==3 and not self.fired:
                api=self.module.history.bounded.prior.hour_api
                original=api._names;parent=self.root/'source_parent_non_authoritative'
                def names(path,cap):
                    found=original(path,cap)
                    if Path(path)==parent:
                        self.namespace_seam_reads+=1
                        return found|{'injected_read_result.bin'}
                    return found
                self.patch.setattr(api,'_names',names);self.fired=True;self.injection_count+=1;self.mark(frame)
        return self.trace

    def profile(self,frame,event,arg):
        try:self._profile(frame,event,arg)
        except BaseException as error:
            self.instrumentation_errors.append('profile '+type(error).__name__+': '+str(error)[:512])

    def _profile(self,frame,event,arg):
        if event=='return' and frame.f_code is self.after_code and arg is not None:
            self.counts['normal_after_returns']+=1
        if event!='call':return
        code=frame.f_code
        if code is self.job_code:self.counts['job_inspections']+=1
        if code is self.stage_code:self.counts['stage_inspections']+=1
        if code.co_name!='close':return
        value=frame.f_locals.get('self')
        labels=[name for name,owner in self.inner.items() if value is owner]
        labels += ['outer_'+str(i) for i,owner in enumerate(self.outer) if value is owner]
        if code is self.parent_code:
            labels.append('frozen_parent' if frame.f_globals.get('__name__')==self.module.runtime.__name__ else 'dynamic_parent')
        for label in labels:self.close_calls.append(label)

    def report(self,error):
        if self.reader is None:raise AssertionError('actual partially constructed Reader was never retained')
        states={}
        for name,owner in self.inner.items():
            state=dict(type=type(owner).__module__+'.'+type(owner).__qualname__,
                closed=getattr(owner,'closed',getattr(owner,'_closed',None)))
            lease=getattr(owner,'_lease',None)
            if lease is not None:state['nested_ReadView_closed']=lease.closed
            states[name]=state
        chain=[];seen=set();item=error
        while item is not None and id(item) not in seen and len(chain)<8:
            seen.add(id(item))
            chain.append(dict(type=type(item).__name__,text=str(item)[:1024],
                notes=[str(value)[:512] for value in getattr(item,'__notes__',())]))
            item=item.__cause__ or item.__context__
        trace=[];tb=error.__traceback__
        while tb is not None and len(trace)<16:
            trace.append(dict(file=tb.tb_frame.f_code.co_filename,function=tb.tb_frame.f_code.co_name,line=tb.tb_lineno))
            tb=tb.tb_next
        result=dict(injection_reached=self.fired,injection_count=self.injection_count,
            injection_position=self.injection_position,instrumentation_errors=self.instrumentation_errors,
            exception_chain=chain,primary_error_type=type(error).__name__,
            rejection_trace=trace,primary_error_filename=str(getattr(error,'filename',None)),
            primary_error_text=str(error)[:2048],same_injected_primary_object=self.primary is error if self.primary is not None else None,
            primary_errno=getattr(error,'errno',None),primary_winerror=getattr(error,'winerror',None),
            native_sharing_conflict_code=self.native_sharing_error,
            actual_Reader_retained=True,Reader_closed=self.reader._closed,
            Reader_owner_fields_cleared=all(getattr(self.reader,name) is None for name in self.inner),
            constructor_capture_cleared=self.reader._cic_value is self.module.capture._EMPTY,
            captured_cleared=self.containers['captured']=={},all_packets_cleared=self.containers['all_packets']=={},
            seen_hours_cleared=self.containers['seen_hours']==[],outer_ReadViews_closed=[v.closed for v in self.outer],
            actual_inner_states=states,close_calls=self.close_calls,observed_replay_call_counts=self.counts,
            inner_object_ids={name:id(value) for name,value in self.inner.items()},
            outer_object_ids=[id(value) for value in self.outer],
            packet_digests_before_after=self.packet_digests,
            packet_fault_is_in_memory_reflection=self.label=='unselected_packet_drift',
            all_packet_keys_before_revalidation=self.before_all_packet_keys,namespace_observations_reached=self.namespace_calls,
            ReadView_is_identity_observation_not_OS_writer_lease=True,
            real_filesystem_content_changed=False,
            namespace_fault_is_read_result_seam=self.label=='final_namespace_read_result',
            namespace_seam_reads=self.namespace_seam_reads,retained_frame_objects=False,
            only_explicitly_cleared_containers_checked=['captured','all_packets','seen_hours'])
        assert self.fired and self.injection_count==1 and not self.instrumentation_errors
        assert result['Reader_closed'] and result['Reader_owner_fields_cleared']
        assert result['constructor_capture_cleared'] and result['captured_cleared'] and result['all_packets_cleared']
        assert result['seen_hours_cleared'] and all(result['outer_ReadViews_closed'])
        assert all(value['closed'] is True and value.get('nested_ReadView_closed',True) is True for value in states.values())
        assert [name for name in self.close_calls if name in self.inner]==list(self.inner)
        assert [name for name in self.close_calls if name.startswith('outer_')]==['outer_3','outer_2','outer_1','outer_0']
        assert self.close_calls.count('frozen_parent')==1
        dynamic_expected=1 if self.label in ('constructor_primary','constructor_helper_alias','constructor_Path_alias') else 0
        assert self.close_calls.count('dynamic_parent')==dynamic_expected
        if self.primary is not None:assert self.primary is error
        if self.label.startswith('constructor_') and self.label!='constructor_primary':
            assert type(error) is ValueError
            if self.label=='constructor_parent_alias':assert 'dependency alias changed' in str(error)
            if self.label=='constructor_parent_code':assert 'callable changed' in str(error)
            if self.label in ('constructor_helper_alias','constructor_Path_alias'):
                assert 'named runtime slot changed' in str(error)
        if self.label=='unselected_packet_drift':
            assert self.before_all_packet_keys==[0,1] and 'H1 current input drift' in str(error)
            assert any(item['function']=='validate_current' and item['file'].endswith('normal_h1_source.py') for item in trace)
        if self.label=='final_read_sharing_error':
            assert isinstance(error,PermissionError) and error.errno==13 and self.native_sharing_error==32
            assert Path(error.filename)==self.denial.path
        if self.label=='final_namespace_read_result':
            assert self.namespace_calls==3 and self.namespace_seam_reads==1
            assert 'unexpected or unbounded historical suffix name' in str(error)
        H=2 if self.label=='unselected_packet_drift' else 1
        complete=0 if self.label.startswith('constructor_') else H
        assert self.counts==dict(job_inspections=2*complete,stage_inspections=10*complete,normal_after_returns=complete)
        return result


def main():
    label,out=sys.argv[1],Path(sys.argv[2]).resolve()
    if label not in CASES or not out.is_dir():raise ValueError('one registered case/output required')
    before=inventory(CASE)
    previous=load(REPO/'results/tables/rq2_h1_cross_hour_outage_v1_non_authoritative/connected_03_postcheck.json')
    assert before==previous['diagnostic_case_files_sha256'] and len(before)==465
    prefix=os.path.normcase(str(CASE))+os.sep
    activity=dict(case_read_opens=0,rejected_mutations=0);last=[0.]
    def within(path):
        return isinstance(path,(str,bytes,os.PathLike)) and (os.path.normcase(os.path.abspath(os.fsdecode(path)))+os.sep).startswith(prefix)
    def audit(event,values):
        mutation=False
        if event=='open' and within(values[0]):
            _,mode,flags=values
            mutation=(isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_APPEND|os.O_CREAT|os.O_TRUNC)))
            activity['case_read_opens']+=not mutation
            if not mutation and time.monotonic()-last[0]>10:
                last[0]=time.monotonic()
                (out/'source_read_activity.json').write_text(json.dumps(activity),encoding='utf-8')
        elif event in ('os.mkdir','os.remove','os.rmdir','os.chmod','os.utime','os.truncate'):mutation=within(values[0])
        elif event in ('os.rename','os.link','os.symlink'):mutation=any(within(p) for p in values[:2])
        if mutation:
            activity['rejected_mutations']+=1
            raise RuntimeError('saved-case write denied')
    sys.addaudithook(audit)
    spec=importlib.util.spec_from_file_location('fixed_saved_fixture',HERE.parent/'rq2_h1_source_replay_cost_v1_non_authoritative/profile_saved_v1.py')
    fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
    import pytest
    patch,drift=pytest.MonkeyPatch(),pytest.MonkeyPatch()
    started=time.perf_counter();window=None;error=None;result={};cleanup_errors=[]
    prior_trace,prior_profile=sys.gettrace(),sys.getprofile()
    try:
        fixture.install_saved_fixture(patch)
        from experiments import h1_phase_historical_batch_development_v3 as historical
        root=CASE/'normal_non_authoritative';H=2 if label=='unselected_packet_drift' else 1
        terminals={h:pin(root/f'obligation_non_authoritative/{h:03d}.terminal.json') for h in range(H)}
        window=FaultWindow(historical,label,drift,root)
        sys.setprofile(window.profile);sys.settrace(window.trace)
        try:
            historical.replay_prefixes(root,expected_binding_sha256=pin(root/'obligation_non_authoritative/binding.json'),
                expected_terminal_sha256=terminals[H-1],completed_hours=H,expected_terminals=terminals,
                selected_hours=(H-1,))
        except BaseException as caught:error=caught
        finally:
            sys.settrace(prior_trace);sys.setprofile(prior_profile)
        if error is None:raise AssertionError('fault case returned a result')
        result=window.report(error)
        result['completed_prefix_hours_requested']=H
        result['selected_hours']=[H-1]
    except BaseException:
        result['diagnostic_error']=traceback.format_exc()[-16000:]
    finally:
        sys.settrace(prior_trace);sys.setprofile(prior_profile)
        try:
            if window is not None and window.denial is not None:window.denial.close()
        except BaseException as caught:cleanup_errors.append('sharing handle: '+repr(caught)[:1024])
        try:drift.undo()
        except BaseException as caught:cleanup_errors.append('drift restore: '+repr(caught)[:1024])
        try:
            if window is not None:
                window.module._CHECK_DEPENDENCIES()
                result['guard_usable_after_fault_restored']=True
                if window.denial is not None:
                    info=window.denial.path.stat()
                    after_identity=(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_nlink)
                    assert after_identity==window.sharing_identity and window.denial.close_confirmed
                    result['read_only_sharing_handle_closed']=True
                    result['sharing_target_identity_before_after_equal']=True
        except BaseException as caught:cleanup_errors.append('restored identity check: '+repr(caught)[:1024])
        try:patch.undo()
        except BaseException as caught:cleanup_errors.append('fixture restore: '+repr(caught)[:1024])
    after=inventory(CASE)
    hooks_restored=sys.gettrace() is prior_trace and sys.getprofile() is prior_profile
    accepted=('diagnostic_error' not in result and not cleanup_errors and before==after
              and hooks_restored and result.get('guard_usable_after_fault_restored') is True
              and activity['rejected_mutations']==0)
    result.update(status='DRAFT_NONAUTHORITATIVE',case=label,exit_code=0 if accepted else 1,
        elapsed_seconds=time.perf_counter()-started,saved_case_files=465,saved_case_sha256_equal=before==after,
        activity=activity,trace_profile_overhead_included=True,
        cleanup_errors=cleanup_errors,non_solver_Win32_file_API_used=label=='final_read_sharing_error',native_solver_execution=False,
        prior_trace_and_profile_restored=hooks_restored,
        constructor_or_file_failure_matrix_exhaustive=False,arbitrary_reflection_or_ABA_covered=False,
        source_successor_adopted=False,resource_admission=False,formal_execution_ready=False,
        new_normal_jobs=0,real_native_solver_calls=0,real_native_calls=0,
        real_native_calls_scope='solver/native scientific adapter only',formal_result=False)
    with (out/'worker_terminal.json').open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps(dict(case=label,exit_code=result['exit_code'],seconds=result['elapsed_seconds'],
        counters=result.get('observed_replay_call_counts'),error=result.get('diagnostic_error'))),flush=True)
    return result['exit_code']


if __name__=='__main__':raise SystemExit(main())
