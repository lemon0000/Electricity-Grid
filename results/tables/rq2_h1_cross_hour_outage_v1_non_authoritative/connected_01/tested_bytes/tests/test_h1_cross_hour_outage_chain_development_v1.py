"""Three-hour toy outage/repair, one lane timeout, then missing next source."""
from contextlib import closing
from dataclasses import asdict, replace
from fractions import Fraction as Q
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import time

import pytest
from pyomo.environ import Var, value

from tests import h1_cross_hour_outage_fixture_v1 as case
from tests.test_h1_cross_hour_owner_development_v1 import (
    environment, supplied, no_solver, synthetic_reports, saved, spec, real, static_code_identities)

m,prior=case.m,case.prior


@pytest.fixture
def outage_environment(environment,monkeypatch):
    return case.install_case(environment,monkeypatch)


@pytest.mark.parametrize('hour',range(3))
def test_two_unit_normal_candidates_match_every_canonical_stage(outage_environment,synthetic_reports,hour):
    packet,_=case.packets(outage_environment)[hour]
    api=m.normal.base.old.replay.native.model_api
    locks=()
    for raw in case.normal_reports(packet,synthetic_reports):
        request=api.H1StageRequest(packet.inputs,locks)
        model=api.build_h1_stage_model(request,expected_identity=api.h1_stage_identity(request))
        assignment={name:float.fromhex(number) for name,number in json.loads(raw)['assignment']}
        assert set(assignment)=={v.name for v in model.component_data_objects(Var)}
        for name,number in assignment.items():model.find_component(name).set_value(number,skip_validation=True)
        capture=m.saved.selection.native.capture
        assert capture._constraint_violation(model)<=1e-9
        assert capture._integrality_violation(model)<=1e-9
        assert all((v.lb is None or v.value>=value(v.lb)-1e-9) and
                   (v.ub is None or v.value<=value(v.ub)+1e-9) for v in model.component_data_objects(Var))
        locks+=(float(value(model.objective)),)
    assert locks==(60.,1.,1.,30.,15.)


def _capture(frame,action,before,lane,power):
    selection=m.saved.selection
    cfg=prior.manifest()
    chosen=cfg.reference_selector if lane.role=='Rref' else cfg.actual_selector
    key=selection.input_identity(frame,action,before,lane=lane,power=power)
    records=[];locks=()
    for index,label in enumerate(selection.stage_labels(frame,lane)):
        def builder():return selection.build_development_stage(frame,action,before,lane=lane,power=power,
            index=index,frozen=locks,expected_identity=key)
        raw=selection.native.capture._solve(builder,cfg.solver_specification,prior.producer_budget(),
            f'{selection.SCHEMA}:{lane.role}:{index}:{label}')
        records.append(selection.encode_development_record(frame,action,before,raw,index=index,frozen=locks,
            lane=lane,power=power,selector=chosen,specification=cfg.solver_specification,limits=cfg.replay_limits))
        if not raw.optimal:break
        locks+=(raw.objective,)
    report=selection.replay_development_records(frame,action,before,tuple(records),lane=lane,power=power,
        selector=chosen,specification=cfg.solver_specification,limits=cfg.replay_limits,
        expected_identity=key,expected_policy_identity=before.policy_identity,
        expected_report_sha256=tuple(sha256(r).hexdigest() for r in records))
    return report,records


def test_three_hour_analytic_outage_repair_and_timeout_oracle(tmp_path,outage_environment,monkeypatch,static_code_identities):
    began=time.perf_counter()
    selection,physical,business=m.saved.selection,m.saved.source.physical,m.saved.business
    packets=case.packets(outage_environment)
    frames=[physical._frame(p,after) for p,after in packets]
    origin=outage_environment[2]
    prefix=m.saved.source.registry.prepare(split='training',raw_start=0,hours=3,outage_seed=origin.outage_seed,
        expected_registry_identity='c'*64)
    views=[m.saved.source.registry.decision_view(a) for a in prefix.actions]
    assert views[0]['active']==views[1]['active']=={'kind':'generator','uid':'G1'}
    assert prefix.origin.active.observed_start_hour is None
    assert views[1]['started'] is views[1]['ended'] is None
    assert views[0]['repair_cap_exact'] is views[1]['repair_cap_exact'] is None
    assert views[2]['active'] is views[2]['started'] is None
    assert views[2]['ended']=={'kind':'generator','uid':'G1'} and views[2]['repair_cap_exact']==['24','1']
    assert all(dict(frame.info.current.generator_available)=={'G1':True,'G2':True} for frame in frames)
    assert all(frame.info.normal.generation_mw==(('G1',30.),('G2',15.)) for frame in frames)
    cfg=prior.manifest()
    selected={};carries={};halted=set();quantities=[]
    lanes=[('reference',m.saved.RREF)]+[(c.lane_id,c.lane) for c in cfg.lanes]
    for key,lane in lanes:
        chosen=cfg.reference_selector if lane.role=='Rref' else cfg.actual_selector
        selected[key]=selection.initialize_development_selection(frames[0],prefix.origin,lane=lane,
            selector=chosen,specification=cfg.solver_specification,limits=cfg.replay_limits,chronology_origin=True)
    for config in cfg.lanes:
        carries[config.lane_id]=prior.biz.origin(config.lane.arm,mechanism=config.mechanism)
    calls=case.install_selectors(monkeypatch)
    repair_before=None
    for hour,(frame,action) in enumerate(zip(frames,prefix.actions,strict=True)):
        if hour==2:repair_before=selected['reference'].physical_carry
        ref,_=_capture(frame,action,selected['reference'],m.saved.RREF,None)
        assert ref.next_candidate is not None,(hour,ref.errors)
        assert Q(*map(int,ref.candidate_request_exact))==(Q(5) if hour<2 else Q(0))
        selected['reference']=ref.next_candidate
        for config in cfg.lanes:
            key=config.lane_id
            if key in halted:continue
            item=business.current(relative_hour=hour,mechanism=config.mechanism,workload=Q(1,10),
                source_cfe_at_alpha_one=Q(3,5) if hour<2 else Q(1,5),grid_request_mw=Q(5) if hour<2 else Q(0))
            candidate=business.prepare_development(carries[key],item,expected_current_identity=item.identity)
            assert candidate.next_candidate is not None
            power=physical.RelativeDcPower(hour,str(candidate.actual_power_mw.numerator),
                str(candidate.actual_power_mw.denominator),'mechanism_assumption')
            actual,records=_capture(frame,action,selected[key],config.lane,power)
            if key=='cfe' and hour==1:
                assert actual.next_candidate is None and len(records)==1
                raw=json.loads(records[0])['raw']
                termination=case.TerminationCondition.maxTimeLimit
                assert raw['solver_records'][0][1]==[type(termination).__module__+'.'+type(termination).__name__,repr(termination)]
                assert not raw['optimal'] and raw['solution_count']==1
                halted.add(key)
            else:
                assert actual.next_candidate is not None
                carries[key]=candidate.next_candidate;selected[key]=actual.next_candidate
                a=carries[key].cursor.records[-1].response.action
                assert a.grid_served+a.cfe_served<=Q(1,20)
                assert a.grid_served+a.cfe_served+a.recovery<=Q(1,2)
                assert a.recovery<=Q(9,100)
                if key!='network':assert a.recovery<=item.allocation.compatible_surplus
                quantities.append(dict(hour=hour,lane=key,q=str(a.grid_served+a.cfe_served),
                    r=str(a.recovery),power_mw=str(candidate.actual_power_mw)))
    assert len(calls)==34 and [row['index'] for row in calls if row['timeout']]==[17]
    assert all(row['generation']==[0.,40.] for row in calls[:7])
    assert all(row['generation']==[0.,35.] for row in calls[7:10])
    assert all(row['generation']==[0.,40.] for row in calls[10:18])
    assert all(row['generation']==[0.,35.] for row in calls[18:21])
    assert all(row['generation']==[0.,40.] for row in calls[21:24])
    assert all(row['generation']==[24.,21.] for row in calls[24:28])
    assert all(row['generation']==[24.,36.] for row in calls[28:31])
    assert all(row['generation']==[24.,32.76470588225] for row in calls[31:34])
    assert len(quantities)==7 and halted=={'cfe'}
    assert selected['cfe'].physical_carry.completed_hours==len(carries['cfe'].cursor.records)==1
    for key in ('joint','network'):assert selected[key].physical_carry.completed_hours==len(carries[key].cursor.records)==3
    debt={key:carry.cursor.execution.tracks[0][1].ledger.debt for key,carry in carries.items()}
    assert debt=={'cfe':Q(1,50),'joint':Q(29,1000),'network':Q(7,20_000_000_000_000)}
    # A balanced repair dispatch one MW above the real cap is rejected.
    power=physical.RelativeDcPower(2,'25','1','mechanism_assumption')
    key=physical.development_step_identity(frames[2],prefix.actions[2],repair_before,power,lane=m.saved.RREF)
    model=physical.build_development_model(frames[2],prefix.actions[2],repair_before,power,
        lane=m.saved.RREF,expected_identity=key)
    vals={v.name:0. for v in model.component_data_objects(Var)}
    vals.update({'generation[G1]':25.,'generation[G2]':20.})
    rejected=physical.audit_development_assignment(frames[2],prefix.actions[2],repair_before,power,vals,
        lane=m.saved.RREF,expected_identity=key)
    assert not rejected.physical_assignment_valid and rejected.next_carry is None
    (tmp_path/'outage_kernel_oracle.json').write_text(json.dumps(dict(
        status='DRAFT_NONAUTHORITATIVE',seconds=time.perf_counter()-began,normal_stages_per_hour=5,
        source_actions=views,selector_calls=calls,paired_lane_hours=7,quantities=quantities,
        debts={key:str(q) for key,q in debt.items()},repair_cap_exceedance_rejected=True,
        timeout_is_unresolved=True,new_jobs=0,real_native_calls=0,formal_result=False),indent=2)+'\n',encoding='utf-8')


def test_missing_next_source_is_not_substituted(outage_environment):
    upstream,config,origin,_=outage_environment
    declaration=replace(origin,power_raw_hour=3,workload_raw_hour=3)
    with pytest.raises(ValueError,match='^window not contained in one verified same-split source chain$'):
        m.saved.source.source.load_pinned_current(declaration,upstream,config_path=config)


def test_three_hour_connected_outage_repair_lane_stop_and_missing_source(
        tmp_path,outage_environment,real,synthetic_reports,monkeypatch,static_code_identities):
    trace=lambda label,**kw:prior.trace(tmp_path,label,**kw)
    trace('start',synthetic_hours=3,lanes=3,formal_result=False)
    packets=case.packets(outage_environment)
    normal=case.controller(tmp_path/'normal_non_authoritative',outage_environment,real,monkeypatch)
    holder=owner=None
    try:
        case.install_launcher(monkeypatch,tmp_path,case.normal_reports(packets[0][0],synthetic_reports),0)
        assert normal.bootstrap_development().completed_hours==1
        trace('N0_terminal')
        first=normal.last_obligation_observation
        cfg=replace(prior.manifest(),accounting_period_id='synthetic-three-hour-outage-single-episode')
        binding=m.saved.SourceBinding(str(normal._lease.root),first.header_sha256,'c'*64,first.terminal_sha256)
        owner_root=tmp_path/'owner_non_authoritative';holder_root=tmp_path/'holder_non_authoritative'
        holder_args=dict(owner_root=owner_root,max_tickets=cfg.max_events,max_ticket_bytes=cfg.max_event_bytes,
            max_total_ticket_bytes=cfg.max_archive_bytes,retain_head=lambda *a:a[2])
        holder=m.saved.tickets.TicketHolder(holder_root,create=True,**holder_args)
        owner=m.DevelopmentOwner(owner_root,cfg,binding,holder=holder,create=True,controller=normal)
        calls=case.install_selectors(monkeypatch)
        producer=m.PhaseSelectorProducer(prior.producer_budget())
        states=[]
        for hour in range(3):
            if hour:case.install_launcher(monkeypatch,tmp_path,case.normal_reports(packets[hour][0],synthetic_reports),hour)
            report=owner.run_next_development(expected_heads=owner.heads,selector_producer=producer)
            assert report.completed_hours==hour+1 and not report.pending_attempt and not report.pending_intent
            state=owner.last_candidate_state;states.append(state)
            assert state.reference.physical_carry.completed_hours==hour+1
            assert dict(state.lanes)['cfe'].halted==(hour>=1)
            assert all(not dict(state.lanes)[key].halted for key in ('joint','network'))
            trace('hour'+str(hour)+'_paired',batch_observations=len(owner.batch_observations))
        assert len(calls)==34 and [row['index'] for row in calls if row['timeout']]==[17]
        assert all(row['generation']==[24.,21.] for row in calls[24:28])
        assert all(row['generation']==[24.,36.] for row in calls[28:31])
        assert all(row['generation']==[24.,32.76470588225] for row in calls[31:34])
        lanes=dict(states[-1].lanes)
        for state in states[1:]:
            assert dict(state.lanes)['cfe'].business==dict(states[0].lanes)['cfe'].business
            assert dict(state.lanes)['cfe'].actual==dict(states[0].lanes)['cfe'].actual
        debts={key:lane.business.cursor.execution.tracks[0][1].ledger.debt for key,lane in lanes.items()}
        assert debts=={'cfe':Q(1,50),'joint':Q(29,1000),'network':Q(7,20_000_000_000_000)}
        assert lanes['cfe'].reason=='actual_unresolved' and len(lanes['cfe'].business.cursor.records)==1
        assert lanes['cfe'].actual.physical_carry.completed_hours==1
        for key in ('joint','network'):
            assert len(lanes[key].business.cursor.records)==lanes[key].actual.physical_carry.completed_hours==3
        for key,lane in lanes.items():
            for hour,record in enumerate(lane.business.cursor.records):
                a=record.response.action
                assert a.grid_served+a.cfe_served<=Q(1,20)
                assert a.grid_served+a.cfe_served+a.recovery<=Q(1,2)
                assert a.recovery<=Q(9,100)
                if key!='network':
                    source=Q(3,5) if hour<2 else Q(1,5)
                    surplus=m.saved.business.cfe.allocate(Q(1,10),source,Q(1,2)).compatible_surplus
                    assert a.recovery<=surplus
        source_before=(normal._parent._journal.head,normal._obligation_previous,normal._clock_index)
        calls_before=len(calls)
        with pytest.raises(ValueError,match='^window not contained in one verified same-split source chain$') as missing:
            owner.run_next_development(expected_heads=owner.heads,selector_producer=producer)
        assert owner.poisoned and len(calls)==calls_before
        assert source_before==(normal._parent._journal.head,normal._obligation_previous,normal._clock_index)
        assert not (Path(binding.root)/'job_003_non_authoritative').exists()
        assert not (Path(binding.root)/'clock_bridge_non_authoritative/003').exists()
        assert not (Path(binding.root)/'source_parent_non_authoritative/hour_003_non_authoritative').exists()
        assert not list((Path(binding.root)/'obligation_non_authoritative').glob('003.*'))
        assert normal.last_obligation_observation.relative_hour==2 and normal._clock_index==3
        # A failed next-source attempt deliberately poisons the live owner.
        # Observe its saved journal through a separate read-only connection;
        # the fresh owner below validates and replays the complete journal.
        with closing(sqlite3.connect(owner.path.as_uri()+'?mode=ro',uri=True)) as db:
            rows=db.execute('SELECT seq,predecessor,kind,body,head FROM events ORDER BY seq').fetchall()
        assert [row[2] for row in rows]==['intent','outcome','attempt','intent','outcome','attempt','intent','outcome','attempt']
        assert json.loads(rows[-1][3])['hour']==3
        assert [json.loads(row[3])['source_audit']['source_cfe_at_alpha_one_exact']
                for row in rows if row[2]=='intent']==[['3','5'],['3','5'],['1','5']]
        assert sum(json.loads(row[3])['projection']['lanes'][i]['paired_committed']
            for row in rows if row[2]=='outcome' for i in range(3))==7
        trace('missing_source_stopped',error_type=type(missing.value).__name__,error=str(missing.value))
        heads,holder_head=owner.heads,holder.head
        scientific=states[-1].scientific
        observations=list(owner.batch_observations);timings=list(owner.stage_timings)
        declaration=normal._parent._declaration;parent_identity=normal._parent.identity
        anchor=normal._parent._anchor.inspect().record_sha256
        last_terminal=normal.last_obligation_observation.terminal_sha256
        jobs=[json.loads((Path(binding.root)/f'job_{h:03d}_non_authoritative/observation.json').read_bytes()) for h in range(3)]
        assert len({job['pid'] for job in jobs})==3 and all(job['exit_code']==0 and job['whole_job_quiescent'] for job in jobs)
        leases=(normal._lease,normal._clock_lease,normal._obligation_lease,normal._parent._root_lease,
            normal._parent._journal._lease,normal._parent._anchor._lease,owner._lease_object,holder._lease_object)
        streams=tuple(lease.stream for lease in leases)
        def files():return {str(p):sha256(p.read_bytes()).hexdigest() for r in (Path(binding.root),owner_root,holder_root)
            for p in r.rglob('*') if p.is_file()}
        owner.close();owner=None;holder.close();holder=None;normal.close()
        assert all(stream.closed for stream in streams)
        assert all(lease.stream is None and not lease.locked for lease in leases)
        before=files();trace('closed_before_reopen')
        holder=m.saved.tickets.TicketHolder(holder_root,expected_head=holder_head,**holder_args)
        owner=m.DevelopmentOwner(owner_root,cfg,binding,holder=holder,expected_heads=heads)
        assert owner.last_candidate_state.scientific==scientific
        inspected=owner.inspect(expected_heads=heads)
        assert inspected.completed_hours==3 and inspected.pending_attempt and not inspected.pending_intent
        assert not inspected.continuation_available and not inspected.episode_terminal
        observations.extend(owner.batch_observations)
        assert len(observations)==32 and sum(row['completed_hours'] for row in observations)==64
        assert sum(row['parent_inspect_traversals'] for row in observations)==64
        assert sum(row['parent_inspect_traversals']*row['completed_hours'] for row in observations)==128
        proof=m.saved.source.historical.inspect(binding.root,expected_binding_sha256=binding.binding_sha256,
            expected_terminal_sha256=last_terminal,completed_hours=3)
        assert proof['historical_job_clock_prefix_verified']
        snapshot=m.normal.binding.snapshot.open_snapshot(declaration,expected_parent_identity=parent_identity,
            expected_anchor_record=anchor)
        try:assert snapshot.inspect().completed_hours==3
        finally:snapshot.close()
        assert not owner._live_controller
        reopen_leases=(owner._lease_object,holder._lease_object)
        reopen_streams=tuple(lease.stream for lease in reopen_leases)
        owner.close();owner=None;holder.close();holder=None
        assert all(stream.closed for stream in (*streams,*reopen_streams))
        assert all(lease.stream is None and not lease.locked for lease in (*leases,*reopen_leases))
        assert files()==before
        result=dict(status='DRAFT_NONAUTHORITATIVE',synthetic_hours=3,lanes=3,paired_lane_hours=7,
            normal_jobs=3,normal_stages=15,selector_stages=34,selector_timeout_call=17,
            normal_job_observations=jobs,selector_calls=calls,batch_observations=observations,owner_stage_timings=timings,
            state=scientific,debts={key:str(q) for key,q in debts.items()},
            missing_source=dict(relative_hour=3,error_type=type(missing.value).__name__,message=str(missing.value),
                pending_attempt_retained=True,extra_normal_job_created=False,extra_selector_calls=0),
            reopen_inspection=dict(completed_hours=inspected.completed_hours,pending_attempt=inspected.pending_attempt,
                continuation_available=inspected.continuation_available,episode_terminal=inspected.episode_terminal),
            lane_status=dict(cfe='actual_unresolved',joint='active',network='active'),
            all_owned_lease_handles_closed=True,saved_file_count=len(before),saved_files_sha256=before,
            reopen_all_saved_bytes_match=True,reopen_scientific_match=True,real_native_calls=0,
            test_only_static_identity_memo=True,production_overhead_measured=False,
            full_192_hour_execution_verified=False,formal_execution_ready=False,resource_admission=False,
            writer_rehydration_implemented=False,persisted_atomic_live_join_authenticated=False,formal_result=False)
        (tmp_path/'outage_chain_result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        trace('reopen_verified')
    finally:
        if owner is not None:owner.close()
        if holder is not None:holder.close()
        if normal._lease is not None:normal.close()
