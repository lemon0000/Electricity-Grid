"""Synthetic selector adapters for complete N0/common and Handoff6 validation.

The only numeric oracle here is a tiny zero-workload, neutral-outage case:
P_ref=P_actual=0 and G1 supplies the fixed 20 MW demand. No native optimum or
canonical selector Job is claimed. Snapshot and persistence paths stay real.
"""
from contextlib import ExitStack
from base64 import b64encode
from fractions import Fraction
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest
import experiments

from experiments import h1_selector_phase_handoff_development_v6 as handoff
from tests.h1_hour0_synthetic_harness_v4 import harness,load
from tests.test_h1_timed_selector_sequence_development_v1 import factory,producer
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver
from tests.test_h1_timed_selector_sequence_development_v1 import m as sequence


# At B=0, the canonical model evaluates B-P_ref as -P_ref. Preserve
# the resulting negative-zero hex, just as the saved selector replay does.
ZERO_WORKLOAD_REFERENCE_LOCKS=(-0.,0.,20.)


def actual_parent_root(root,lane):
    return handoff.parent.preparation._path(root/('actual_'+lane+'_non_authoritative'))


def consume_zero_workload(common_owner,configuration,patch,root,trace):
    # The inherited sequence fixture caches immutable implementation identities.
    # Check full bookends and restore before returning; this is not an ABA test.
    modules=(sequence.selection.physical,sequence.selection,sequence.legacy.stage,
        sequence.legacy.bridge,sequence.legacy.configuration_api,sequence.timed.capture.legacy,
        sequence.legacy,sequence.timed,sequence.timed.capture)
    originals={module:module.implementation_identity for module in modules}
    def identity(module,fn):
        return fn(configuration.specification,configuration.limits) if module is sequence.selection else fn()
    pins={module:identity(module,fn) for module,fn in originals.items()}
    with patch.context() as scoped:
        no_solver.__wrapped__(scoped)
        result=_consume(common_owner,configuration,scoped,root,trace)
    for module,fn in originals.items():
        assert module.implementation_identity is fn and identity(module,fn)==pins[module]
    return result


def _consume(common_owner,configuration,patch,root,trace):
    actual_roots={c.lane_id:actual_parent_root(root,c.lane_id) for c in common_owner._manifest.lanes}
    original_install=producer.install
    adapters=[]
    def install(mp,path,lane,fault=None):
        assert fault is None
        instances=original_install(mp,path,lane,fault)
        direct=producer.m.capture.GurobiDirect;presolve=direct._presolve
        adapters.append((direct,instances))
        def analytic(self,model,**kwargs):
            presolve(self,model,**kwargs)
            values={v.VarName:(20. if v.VarName=='generation[G1]' else 0.)
                    for v in self.native.variables}
            assert 'generation[G1]' in values and 'selector_deviation[G1]' in values
            if lane.role=='Rref':assert 'reference_power' in values
            for v in self.native.variables:v.X=values[v.VarName]
            objective=self.native.objective.constant+sum(c*v.X for v,c in self.native.objective.terms)
            self.native.ObjVal=self.native.ObjBound=self.native.ObjBoundC=objective
            self.result.problem.lower_bound=self.result.problem.upper_bound=objective
            for name,value in values.items():self.result.solution[0].variable[name]['Value']=value
        mp.setattr(direct,'_presolve',analytic)
        return instances
    patch.setattr(producer,'install',install)
    build=factory.__wrapped__(root,patch,None)
    context=SimpleNamespace(owner=common_owner,config=configuration,cap=2**30)
    h=harness.__wrapped__(context,build,patch,root)
    trace('selector_harness_and_reference_snapshot')
    # Canonical Handoff/bridge bytes use the declared synthetic Parent alias.
    # No route constant or callback is replaced in the real validation bridge.
    assert all(name not in sys.modules and name.rsplit('.',1)[1] not in vars(experiments) for name in (
        'experiments.h1_common_validation_operation_development_v4',
        'experiments.h1_selector_phase_handoff_development_v6',
        'experiments.h1_selector_post_negative_validation_development_v3',
        'experiments.h1_operation_historical_witness_development_v4',
        'experiments.h1_phase_exact_source_current_development_v5',
        'experiments.h1_group_n0_common_input_binding_development_v5'))
    directory=Path(handoff.__file__).parent
    bridge=load(str(directory/'h1_common_validation_operation_development_v4.py'),
        'experiments.h1_common_validation_operation_development_v4',patch)
    patch.setattr(experiments,'h1_common_validation_operation_development_v4',bridge,raising=False)
    consumer=load(str(directory/'h1_selector_phase_handoff_development_v6.py'),
        'experiments.h1_selector_phase_handoff_development_v6',patch,
        {'h1_selector_parent_controller_development_v4':h.module,
         'h1_common_validation_operation_development_v4':bridge})
    patch.setattr(experiments,'h1_selector_phase_handoff_development_v6',consumer,raising=False)
    post_negative=load(str(directory/'h1_selector_post_negative_validation_development_v3.py'),
        'experiments.h1_selector_post_negative_validation_development_v3',patch,
        {'h1_selector_parent_controller_development_v4':h.module,
         'h1_selector_parent_validation_operation_development_v4':consumer.parent_validation})
    patch.setattr(experiments,'h1_selector_post_negative_validation_development_v3',post_negative,raising=False)
    retained=[]
    actuals={}
    def retain(path,before,after):
        assert common_owner._original_operation.locked()
        assert common_owner._roster._original_operation.locked()
        assert common_owner._roster._owner._original_operation.locked()
        assert reference._guard.locked()
        assert all(p._guard.locked() and p._reference_held for p,_ in actuals.values())
        retained.append((before,after))
        return after
    options=dict(retain_head=retain,max_packet_bytes=64*1024**2,
        max_record_bytes=1024**2,max_archive_bytes=128*1024**2)
    with ExitStack() as stack:
        reference=stack.enter_context(h.module.Parent(h.root,h.raw,**h.options))
        ref=reference.run()
        trace('Rref_parent_run')
        snapshot=h.module.worker.snapshot
        def oracle(raw,receipt,locks):
            item=snapshot.rebuild(raw,expected_sha256=snapshot.io.digest(raw))
            assert item.frame.info.current.dc_baseline_mw==0
            assert sum(v for _,v in item.frame.info.current.demand_by_bus_mw)==20
            assert item.disclosure.current_state.active is None
            terminal=json.loads((Path(receipt.scientific_root)/'terminal.json').read_bytes())
            assert terminal['canonical_lock_hex']==[float(v).hex() for v in locks]
            if receipt.role=='reference':
                assert Fraction(*map(int,terminal['candidate_request_exact']))==0
            else:assert terminal['candidate_request_exact'] is None
        oracle(h.raw,ref,ZERO_WORKLOAD_REFERENCE_LOCKS)
        lane_ids=tuple(sorted(c.lane_id for c in common_owner._manifest.lanes))
        def released():
            assert not reference._guard.locked()
            assert all(not p._guard.locked() and not p._reference_held for p,_ in actuals.values())
            assert not common_owner._original_operation.locked()
            assert not common_owner._roster._original_operation.locked()
            assert not common_owner._roster._owner._original_operation.locked()
        with consumer.Handoff(common_owner,(reference,ref),dict.fromkeys(lane_ids),**options) as absent:
            with pytest.raises(ValueError,match='Actual execution missing or failed'):absent.consume()
            assert not absent.root.exists() and not retained
        released()
        trace('missing_all_Actual_rejected')
        for lane in lane_ids:
            trace('Actual_snapshot_start_'+lane)
            raw=h.module.worker.snapshot.capture_actual(common_owner,configuration,max_archive_bytes=context.cap,
                lane_id=lane,reference_root=ref.scientific_root,reference_terminal_sha256=ref.scientific_terminal_sha256,
                reference_request_sha256=ref.scientific_request_sha256,reference_max_archive_bytes=ref.max_archive_bytes)
            trace('Actual_snapshot_ready_'+lane)
            actual=stack.enter_context(h.module.Parent(actual_roots[lane],raw,**h.options,
                reference_owner=reference,reference_completion=ref))
            trace('Actual_parent_ready_'+lane)
            receipt=actual.run()
            trace('Actual_parent_returned_'+lane)
            oracle(raw,receipt,(0,20))
            dependency=json.loads(raw)['projection']['dependency']
            assert snapshot._fraction(dependency['reference_request_exact'])==0
            assert snapshot._fraction(dependency['actual_power_exact'])==0
            actuals[lane]=(actual,receipt)
            trace('Actual_'+lane)
        assert len({id(v[0]) for v in actuals.values()})==len(lane_ids)==3
        post_negative_receipts=[]
        for missing in lane_ids:
            partial=dict(actuals);partial[missing]=None
            with consumer.Handoff(common_owner,(reference,ref),partial,**options) as absent:
                with pytest.raises(ValueError,match='Actual execution missing or failed'):absent.consume()
                assert not absent.root.exists() and not retained
            released()
            revalidation=post_negative.validate_completed_bundle((reference,ref),actuals)
            assert revalidation['complete'] and revalidation['closed'] and revalidation['outer_cleanup_complete']
            assert revalidation['all_owned_guards_released'] and revalidation['all_reference_marks_cleared']
            assert revalidation['operation_registry_cleared'] and revalidation['source_window_cache_cleared']
            assert revalidation['implementation']==post_negative.implementation_identity()
            assert revalidation['declaration']['helper_identity']==revalidation['implementation']
            assert tuple(revalidation[k] for k in ('top_level_validations','parent_validations',
                'source_prepares','borrowed_source_returns'))==(4,10,2,160)
            expected_pairs=[(None,(reference,ref)),*sorted(actuals.items())]
            binding=json.loads(reference._raw)['declaration']['source_binding']
            assert revalidation['parent_sites']==[dict(root=str(parent.root),role=issued.role,lane_id=lane,
                retained_bodies=7 if lane is None else 1,snapshot_sha256=snapshot.io.digest(parent._raw),
                issued_completion_sha256=snapshot.io.digest(h.module._completion_bytes(issued)),source_binding=binding)
                for lane,(parent,issued) in expected_pairs]
            assert len(revalidation['source_windows'])==1
            window=revalidation['source_windows'][0]
            assert window['window_cache_entry_cleared'] and window['source_binding']==binding
            assert window['nested_source_requests']==160 and window['original_source_prepares']==2
            assert window['full_numerical_hour_replays']==8 and window['fresh_context_observations']==32
            signature=window['complete_source_signature_sha256']
            assert type(signature) is str and len(signature)==64 and all(c in '0123456789abcdef' for c in signature)
            assert all(old['source_windows'][0]['complete_source_signature_sha256']==signature
                for old in post_negative_receipts)
            post_negative_receipts.append(revalidation)
            assert all(revalidation['declaration'][k] is False for k in (
                'same_public_parent_guard_schedule','between_top_level_parent_validations_ABA_covered',
                'same_predecessor_per_nested_source_io_schedule','same_predecessor_failure_order',
                'cross_window_source_reuse','complete_dynamic_input_closure_proved',
                'unobserved_between_bookends_ABA_covered'))
            assert all(revalidation[k] is False for k in (
                'formal_result','resource_admission','native_execution_authorized'))
            released()
            assert common_owner.inspect()['stage']==3
            trace('missing_Actual_rejected_'+missing)
        common_owner._enter()
        try:
            common_view=snapshot._owner_view(common_owner)
            phase_identity=consumer._phase_identity(common_owner._phase)
        finally:common_owner._leave()
        with consumer.Handoff(common_owner,(reference,ref),actuals,**options) as owner:
            result=owner.consume()
            assert result['completed_hours']==1 and len(retained)==5
            validation=result['validation_receipt']
            parent_validation=result['parent_validation_receipt']
            assert parent_validation['status']=='committed' and parent_validation['complete']
            assert parent_validation['closed'] and parent_validation['outer_cleanup_complete']
            assert parent_validation['validation_checks_complete'] and parent_validation['first_failure'] is None
            assert tuple(parent_validation[k] for k in ('bundle_validations','parent_validations',
                'records_bundle_rebuilds','source_requests','source_prepares','full_numerical_hour_replays',
                'within_prefix_numerical_revalidations','reused_numerical_inspections',
                'fresh_context_observations','borrowed_source_returns'))==(13,150,4,2408,28,112,112,0,448,2408)
            assert parent_validation['source_window_cache_cleared']
            assert parent_validation['source_window_counts']==dict(bundle=13,records_bundle=1)
            assert parent_validation['parent_sites']==[
                dict(root=str(parent.root),issued_completion_sha256=snapshot.io.digest(h.module._completion_bytes(issued)),
                    pair_validation_sites=2,record_rebuild_sites=1)
                for parent,issued in [(reference,ref),*(pair for _,pair in sorted(actuals.items()))]]
            windows=parent_validation['source_windows']
            assert len(windows)==14 and all(w['closed'] and w['window_cache_entry_cleared'] for w in windows)
            assert sorted(w['nested_source_requests'] for w in windows)==[160]*13+[328]
            assert sum(w['reference_window']['logical_reference_inspects'] for w in windows)==726
            assert sum(w['reference_window']['original_reference_inspects'] for w in windows)==28
            assert all(w['reference_window']['cache_cleared'] for w in windows)
            parent_declaration=parent_validation['declaration']
            assert parent_declaration['source_schedule']=='bookended_four_Parent_synchronous_validation_window'
            assert parent_declaration['cleared_state_scope']=='window_cache_entry_only'
            assert parent_declaration['predecessor_derived_outputs_follow_original_consumer_lifetime']
            assert parent_declaration['full_source_object_graph_destroyed'] is False
            assert all(parent_declaration[k] is False for k in (
                'same_predecessor_per_nested_source_io_schedule','same_predecessor_failure_order',
                'cross_window_source_reuse','complete_dynamic_input_closure_proved',
                'unobserved_between_bookends_ABA_covered'))
            assert validation['complete'] and validation['closed'] and validation['outer_cleanup_complete']
            assert validation['validation_checks_complete'] and validation['all_arm_proofs_cleared']
            assert validation['common_calls']==22 and validation['first_failure'] is None
            assert tuple(validation[k] for k in ('full_numerical_hour_replays','within_prefix_revalidations',
                'cross_common_numerical_proof_reuses','context_evaluations'))==(24,24,1008,2112)
            assert owner.validation_receipt()==validation
            assert validation['predecessor_report_sha256']==snapshot.io.digest(common_owner._initial_report)
            assert validation['validation_report_sha256']==snapshot.io.digest(consumer.phase.encode(validation['validation_report']))
            assert validation['execution_receipt_sha256']==snapshot.io.digest(json.dumps(
                validation['operation_execution_receipt'],sort_keys=True,separators=(',',':'),
                ensure_ascii=True,allow_nan=False).encode('ascii'))
            released()
            assert all(result[k] is False for k in consumer.FLAGS)
            projection=json.loads(owner._plan.projection)
            assert {v['lane_id'] for v in projection['lanes']}==set(lane_ids)
            assert all(v['status']=='paired_committed' for v in projection['lanes'])
            assert owner._holder.inspect()==owner._plan.tickets
            assert owner._phase.heads==owner._plan.tickets[-1].after_heads
            packet=json.loads(owner._packet)
            assert set(packet)=={'schema','implementation','common','group_audit','phase_file_identity','validation_declaration',
                'parent_validation_declaration',
                'dispositions','parents','tickets','holder_records','retentions','projection','after',*consumer.FLAGS}
            assert packet['schema']==consumer.SCHEMA and packet['implementation']==owner._own
            assert packet['group_audit']==json.loads(common_owner._initial_report)
            assert all(validation[k]==value for k,value in packet['validation_declaration'].items())
            declared_parent=packet['parent_validation_declaration']
            assert {key:value for key,value in declared_parent.items() if key!='parents'}==parent_declaration
            assert declared_parent['parents']==[
                dict(root=str(parent.root),
                    issued_completion_sha256=snapshot.io.digest(h.module._completion_bytes(issued)),
                    snapshot_sha256=snapshot.io.digest(parent._raw),
                    source_binding=json.loads(parent._raw)['declaration']['source_binding'])
                for parent,issued in [(reference,ref),*(pair for _,pair in sorted(actuals.items()))]]
            assert consumer.phase.encode(packet['common'])==consumer.phase.encode(common_view)
            assert packet['phase_file_identity']==json.loads(json.dumps(phase_identity))
            assert packet['dispositions']==[dict(lane_id=lane,kind='paired_actual') for lane in lane_ids]
            assert packet['parents']==[
                dict(lane_id=lane,completion=json.loads(h.module._completion_bytes(receipt)),
                    snapshot_sha256=snapshot.io.digest(p._raw))
                for lane,(p,receipt) in [(None,(reference,ref)),*sorted(actuals.items())]]
            assert packet['tickets']==json.loads(consumer.phase.encode(
                [consumer.phase.tickets._ticket_payload(t) for t in owner._plan.tickets]))
            assert packet['holder_records']==[b64encode(raw).decode('ascii') for raw in owner._plan.holder_records]
            assert packet['retentions']==json.loads(json.dumps(owner._plan.retentions))
            assert packet['projection']==projection and packet['after']==json.loads(owner._plan.after)
            assert (owner.root/'takeover_packet.json').read_bytes()==owner._packet
            assert all(packet[k] is False for k in consumer.FLAGS)
            journal=owner.root/'journal_non_authoritative'
            head=snapshot.io.digest((journal/'header.json').read_bytes());expected=[]
            for i in range(1,6):
                raw=(journal/f'{i:020d}.json').read_bytes();row=json.loads(raw)
                assert row['sequence']==i and row['previous']==head
                after=snapshot.io.digest(raw);expected.append((head,after));head=after
            assert retained==expected
            outcome=dict(root=str(owner.root),result=result,retained_heads=retained,
                post_negative_validation_receipts=post_negative_receipts,
                synthetic_selector_parents=1+len(actuals),canonical_selector_jobs=0,
                parent_lifecycle_receipts=[h.module._WINDOWS.receipts(p) for p in [reference,*(p for p,_ in actuals.values())]],
                real_native_calls=0,formal_result=False,
                replay_inputs=dict(manifest=common_owner._manifest,binding=common_owner._binding,
                    holder_root=common_owner.holder_root,owner_root=common_owner.owner_root,
                    holder_head=owner._holder.head,phase_heads=owner._phase.heads,
                    tickets=owner._plan.tickets,projection=owner._plan.projection,after=owner._plan.after))
            trace('paired_commit_and_readback')
        released()
        for p in [reference,*(p for p,_ in actuals.values())]:
            windows=h.module._WINDOWS.receipts(p)
            assert all(w['complete'] and w['source_window_cache_cleared']
                and w['parent_implementation']==p._own
                and w['source_route_declaration']['helper_identity']==h.module.source_windows.implementation_identity()
                and w['source_route_sha256']==snapshot.io.digest(h.module.source_windows._encode(w['source_route_declaration']))
                for w in windows)
    released()
    assert len(adapters)==9
    assert all(len(instances)==1 and type(instances[0]) is direct
        and instances[0].apply_calls==instances[0].close_calls==1 for direct,instances in adapters)
    trace('selector_parents_and_handoff_closed')
    return outcome


def reopen_paired(outcome,trace):
    """After all original owners close, replay saved tickets and scientific carry."""
    phase=handoff.phase
    saved=outcome['replay_inputs'];manifest=saved['manifest']
    def deny_retention(*args):raise AssertionError('read-only replay must not retain new events')
    with phase.tickets.TicketHolder(saved['holder_root'],owner_root=saved['owner_root'],
            max_tickets=manifest.max_events,max_ticket_bytes=manifest.max_event_bytes,
            max_total_ticket_bytes=manifest.max_archive_bytes,create=False,
            expected_head=saved['holder_head'],retain_head=deny_retention) as holder:
        assert holder.inspect()==saved['tickets']
        with phase.DevelopmentOwner(saved['owner_root'],manifest,saved['binding'],holder=holder,
                create=False,expected_heads=saved['phase_heads']) as owner:
            report=owner.inspect(expected_heads=saved['phase_heads'])
            with phase.closing(owner._connect()) as db:rows=owner._rows(db)
            replay,state,states=owner._restore(rows)
            assert replay==report and report.completed_hours==1
            assert not (report.pending_intent or report.pending_attempt or report.recovery_required or report.conflicted_keys)
            assert phase.encode(state.scientific)==saved['after']
            assert phase.encode(json.loads(rows[-1][3])['projection'])==saved['projection']
            assert rows==[t.event for t in saved['tickets']]
            assert owner.heads==saved['phase_heads'] and holder.head==saved['holder_head']
            result=dict(completed_hours=report.completed_hours,phase_heads=owner.heads,holder_head=holder.head,
                projection_sha256=phase.digest(json.loads(saved['projection'])),
                carry_sha256=phase.digest(state.scientific),state=state.scientific,
                paired_lanes=3,replayed_from_saved_records=True,formal_result=False)
    trace('paired_owner_reopen_replay_and_close')
    return result
