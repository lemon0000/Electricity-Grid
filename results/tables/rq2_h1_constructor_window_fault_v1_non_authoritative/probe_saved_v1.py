"""Two saved-prefix Readers with an actual constructor-return dependency fault."""
from hashlib import sha256
import dis
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0,str(REPO))
sys.path.insert(1,str(REPO/'tests'))

import pytest
from experiments import h1_phase_historical_batch_development_v1 as old
from src.rq2_joint_deliverability_boundary_v1 import continuous_grid_normal as model

spec = importlib.util.spec_from_file_location('saved_reader_fixture',
    HERE.parent/'rq2_h1_source_replay_cost_v1_non_authoritative/profile_saved_v1.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
CASE = fixture.CASE


def save(out,name,value):
    with (out/name).open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2)
        stream.write('\n')


def main():
    out=Path(sys.argv[1]).resolve()
    assert out.parent==HERE and out.is_dir() and sys.getprofile() is None
    started=time.perf_counter()
    before=fixture.inventory(CASE)
    expected=fixture.load(REPO/'results/tables/rq2_h1_cross_hour_outage_v1_non_authoritative/connected_03_postcheck.json')
    assert before==expected['diagnostic_case_files_sha256'] and len(before)==465
    checkpoint=fixture.load(CASE/'external_preclose_checkpoint.json')['saved_files_sha256']
    assert len(checkpoint)==444 and all(fixture.pin(path)==pin for path,pin in checkpoint.items())
    root=CASE/'normal_non_authoritative'
    directory=root/'obligation_non_authoritative'
    terminal=fixture.pin(directory/'000.terminal.json')
    expected_head=fixture.load(directory/'000.terminal.json')['parent_head']
    args=dict(expected_binding_sha256=fixture.pin(directory/'binding.json'),expected_terminal_sha256=terminal,
        completed_hours=1,expected_terminals={0:terminal},selected_hours=(0,))
    save(out,'probe_request.json',dict(root=str(root),arguments=args,historical_reader_calls=2,
        full_source_batch_calls=0,static_identity_memo=False,shared_saved_manifest_resolver=True,
        real_manifest_sources_reaudited=False,Jobs=0,native=0,formal_result=False))
    case_prefix=os.path.normcase(str(CASE))+os.sep
    activity=dict(read_opens=0,rejected_mutations=0)
    last=[0.0]
    def within(value):
        return (isinstance(value,(str,bytes,os.PathLike)) and
            (os.path.normcase(os.path.abspath(os.fsdecode(value)))+os.sep).startswith(case_prefix))
    def audit(event,values):
        mutation=False
        if event=='open' and within(values[0]):
            _,mode,flags=values
            mutation=((isinstance(mode,str) and any(c in mode for c in 'wax+')) or
                (isinstance(flags,int) and bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_APPEND|os.O_CREAT|os.O_TRUNC))))
            activity['read_opens']+=not mutation
            now=time.monotonic()
            if not mutation and now-last[0]>=10:
                last[0]=now
                (out/'source_read_activity.json').write_text(json.dumps(dict(read_opens=activity['read_opens'],
                    evidence='case_read_open_activity_only')),encoding='utf-8')
        elif event in ('os.mkdir','os.remove','os.rmdir','os.chmod','os.utime','os.truncate'):
            mutation=within(values[0])
        elif event in ('os.rename','os.link','os.symlink'):
            mutation=any(within(p) for p in values[:2])
        if mutation:
            activity['rejected_mutations']+=1
            raise RuntimeError('saved-case filesystem mutation denied')
    sys.addaudithook(audit)
    patch=pytest.MonkeyPatch()
    rows=[];error=None
    try:
        fixture.install_saved_fixture(patch)
        from experiments import h1_phase_historical_batch_development_v2 as new
        from experiments import h1_constructor_inspection_capture_development_v1 as capture
        ctor_code=old.history.HistoricalSnapshot.__init__.__code__
        view_code=old.history.prior.ReadView.__init__.__code__
        ctor_returns={i.offset for i in dis.get_instructions(ctor_code) if i.opname in ('RETURN_VALUE','RETURN_CONST')}
        view_returns={i.offset for i in dis.get_instructions(view_code) if i.opname in ('RETURN_VALUE','RETURN_CONST')}
        job_code=old.current.parent.inspect_job.__code__
        stage_code=old.current.parent.worker.hour.stage.inspect.__code__
        close_code=old.HistoricalTimedSnapshot.close.__code__
        filenames={old.__file__,new.__file__}
        original=model._dependencies
        for name,module in (('old',old),('new',new)):
            state=dict(injected=False,injection_count=0,constructor_returns=0,dependency_calls_after_injection=0,
                parent_inspect_calls=0,inspect_job_calls=0,stage_inspect_calls=0,effective_parent_close_calls=0,
                instrumentation_errors=[])
            readers=[];views=[];frames={};row={}
            def changed_dependencies():
                state['dependency_calls_after_injection']+=1
                sources,runtime=original()
                return sources,runtime+(('development_constructor_window_probe','changed'),)
            def observe_inner(frame,event,arg):
                code=frame.f_code
                if event=='call' and code.co_name=='inspect' and code.co_filename in filenames:
                    state['parent_inspect_calls']+=1
                if event=='call':
                    if code is job_code:state['inspect_job_calls']+=1
                    if code is stage_code:state['stage_inspect_calls']+=1
                    if code is close_code:state['effective_parent_close_calls']+=1
                if event!='return':
                    return
                if code is view_code and frame.f_lasti in view_returns:
                    if len(views)>=256:
                        state['instrumentation_errors'].append('bounded observed ReadView count exceeded')
                        return
                    views.append(frame.f_locals['self'])
                if code is ctor_code:
                    state['constructor_returns']+=1
                    reader=frame.f_locals['self'];accepted=frame.f_locals.get('state')
                    if frame.f_lasti not in ctor_returns:
                        state['constructor_exception_return_offset']=frame.f_lasti
                        return
                    expected_bases=(old.HistoricalTimedSnapshot,) if name=='old' else (capture.ConstructorInspectionCapture,new.HistoricalTimedSnapshot)
                    if (type(reader).__bases__!=expected_bases or state['injected'] or accepted is None or reader._closed
                            or accepted.completed_hours!=1 or accepted.attempted_hours!=1
                            or accepted.status!='ready' or accepted.head!=expected_head):
                        state['instrumentation_errors'].append('expected unique successful constructor return window')
                        return
                    if name=='new' and (reader._cic_value is not accepted or not reader._cic_constructing
                            or reader._cic_taken or reader._cic_inspecting):
                        state['instrumentation_errors'].append('actual constructor capture window differs')
                        return
                    readers.append(reader)
                    state['normal_return_offset']=frame.f_lasti
                    state['reader_mro']=[kind.__module__+'.'+kind.__qualname__ for kind in type(reader).__mro__]
                    state['effective_parent_close']=dict(module=old.HistoricalTimedSnapshot.close.__module__,
                        qualname=old.HistoricalTimedSnapshot.close.__qualname__,file=close_code.co_filename,line=close_code.co_firstlineno)
                    state['constructor_accepted_state']=dict(completed_hours=accepted.completed_hours,
                        attempted_hours=accepted.attempted_hours,status=accepted.status,head=accepted.head)
                    model._dependencies=changed_dependencies
                    state['injected']=True
                    state['injection_count']+=1
            def observe(frame,event,arg):
                # Instrumentation cannot introduce an exception at the return
                # boundary before the replay caller receives the Reader.
                try:
                    observe_inner(frame,event,arg)
                except BaseException as exception:
                    if len(state['instrumentation_errors'])<8:
                        state['instrumentation_errors'].append(type(exception).__name__+': '+str(exception))
            began=time.perf_counter()
            try:
                sys.setprofile(observe)
                proofs,frames,header,metric=module.replay_prefixes(root,**args)
                row.update(outcome='returned',proofs=proofs,metric=metric,returned_hours=sorted(frames))
            except Exception as exception:
                trace=traceback.format_exc()
                (out/f'{name}_error.txt').write_text(trace,encoding='utf-8')
                row.update(outcome='rejected',error_type=type(exception).__name__,error=str(exception))
            finally:
                sys.setprofile(None)
                model._dependencies=original
                frames.clear()
            row.update(implementation=name,seconds=time.perf_counter()-began,window=state,
                model_dependency_alias_restored=model._dependencies is original,
                observed_readers=len(readers),observed_read_views=len(views),
                observed_read_view_closed_flags=[view.closed for view in views],
                all_observed_read_views_closed=all(view.closed for view in views),
                reader_cleanup_states=[dict(reader_closed=reader._closed,
                    fields={field:dict(is_none=getattr(reader,field) is None,
                        closed=getattr(getattr(reader,field),'closed',getattr(getattr(reader,field),'_closed',None)))
                        for field in ('_journal','_anchor','_root_lease')}) for reader in readers],
                all_reader_owner_fields_cleared=all(reader._closed and all(getattr(reader,field) is None
                    for field in ('_journal','_anchor','_root_lease')) for reader in readers),
                new_capture_taken_after_call=(all(reader._cic_taken for reader in readers) if name=='new' else None),
                new_capture_slot_cleared=(all(reader._cic_value is capture._EMPTY for reader in readers) if name=='new' else None))
            assert state['injected'] and state['injection_count']==1 and state['constructor_returns']==1 and len(readers)==1
            assert not state['instrumentation_errors']
            if name=='old':assert state['dependency_calls_after_injection']>0
            assert row['model_dependency_alias_restored'] and sys.getprofile() is None
            assert state['parent_inspect_calls']<=(2 if name=='old' else 1)
            assert state['inspect_job_calls']<= (4 if name=='old' else 2)
            assert state['stage_inspect_calls']<= (20 if name=='old' else 10)
            rows.append(row)
            save(out,f'{name}_observation.json',row)
            print(json.dumps(dict(implementation=name,outcome=row['outcome'],seconds=row['seconds'],
                dependency_calls_after_injection=state['dependency_calls_after_injection'])),flush=True)
            readers.clear();views.clear()
    except BaseException:
        error=traceback.format_exc()
        (out/'error.txt').write_text(error,encoding='utf-8')
    finally:
        sys.setprofile(None)
        patch.undo()
    after=fixture.inventory(CASE)
    owned_equal=all(fixture.pin(path)==pin for path,pin in checkpoint.items())
    complete=error is None and len(rows)==2 and before==after and owned_equal
    differential=(len(rows)==2 and rows[0]['outcome']=='rejected' and rows[1]['outcome']=='returned')
    result=dict(status='DRAFT_NONAUTHORITATIVE',exit_code=0 if complete else 1,error=error,
        diagnostic_complete=complete,observations=rows,elapsed_seconds=time.perf_counter()-started,
        historical_window_old_reject_new_return=differential,
        named_dependency_fault_rejected_by_both=(len(rows)==2 and all(row['outcome']=='rejected' for row in rows)),
        full_source_batch_executed=False,full_source_batch_acceptance_proved=False,
        scientific_output_drift_proved=False,source_successor_adopted=False,
        saved_case_files=465,saved_owned_files=444,saved_case_sha256_unchanged=before==after,
        saved_owned_sha256_unchanged=owned_equal,source_activity=activity,
        complete_dynamic_closure_proved=False,unobserved_ABA_covered=False,
        overall_performance_review_complete=False,resource_admission=False,
        native_execution_authorized=False,formal_execution_ready=False,formal_result=False,
        full_192_hour_execution_verified=False,Jobs=0,real_native_calls=0)
    save(out,'probe_terminal.json',result)
    print(json.dumps(dict(exit_code=result['exit_code'],diagnostic_complete=complete,
        historical_window_old_reject_new_return=differential)),flush=True)
    return result['exit_code']


if __name__=='__main__':
    raise SystemExit(main())
