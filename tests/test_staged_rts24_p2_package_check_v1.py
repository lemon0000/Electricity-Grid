"""Synthetic saved protocol metadata, never a public P2 or numerical certificate."""
from contextlib import contextmanager
from dataclasses import asdict,replace
from fractions import Fraction as Q
from pathlib import Path
from types import SimpleNamespace
import json
import os
import stat
import sys

import pytest

from src import staged_rts24_p2_package_check_v1 as d
from src import staged_rts24_development_v1 as c
from src.staged_rts24_causal_v1 import ExecutionState,PointEvidence,PreparedHour,Proposal,HourEvidence
from src.staged_rts24_child_optimality_v1 import ChildLpEvidence
from src.staged_rts24_reference_queries_v1 import reference_requests
from src.rq2_joint_deliverability_boundary_v1.debt_cohorts import DebtLedger

ROOT=Path(__file__).resolve().parents[1]
PACKET=ROOT/'results/tables/staged_rts24_p2_packet_v1_non_authoritative/packet_01'


@pytest.fixture(scope='module',autouse=True)
def forbid_scientific_execution():
    import subprocess
    import pyomo.environ as pyo
    from src import staged_rts24_highs_backend_v1 as backend,staged_rts24_numeric_interface_v1 as numeric
    from src import staged_rts24_journal_v2 as journal,staged_rts24_audit_v1 as audit,staged_rts24_child_optimality_v1 as child
    patch=pytest.MonkeyPatch()
    def denied(*a,**kw):pytest.fail('scientific execution or process launch requested by metadata test')
    for module,names in ((subprocess,('Popen',)),(pyo,('SolverFactory','ConcreteModel')),(backend,('call_highs',)),
        (numeric,('compile_problem','import_snapshot')),(journal,('reopen',)),(audit,('audit_point','audit_legal_x','audit_economic_base')),(child,('audit_child_lp',))):
        for name in names:patch.setattr(module,name,denied)
    yield
    patch.undo()


def process(pid,members=None,numeric=False):
    ids=[dict(pid=n,creation_filetime=4560000+n) for n in (members if members is not None else [pid])]
    return dict(exit_code=2 if numeric else 0,stop_reason='child_exit_nonzero' if numeric else None,
        monitor_error=None,cleanup_error=None,job_quiet_confirmed=True,outer_seconds=.1,
        sampled_tree_peak_rss_bytes=1024,rss_observation_available=True,peak_job_commit_bytes=2048,
        samples=1,terminal_bytes=100,terminal_files=1,terminal_reserved_bytes=16384,owner_pid=pid,owner_creation_filetime=4560000+pid,
        quiescence_witness=dict(active_processes=0,final_pids=[],all_handles_signaled=True,complete_inventory=True,
            total_processes=len(ids),observed_unique_member_handles=len(ids),member_identities=ids))


def save(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(d.codec.canonical(value))


def balance(case,raw=None):
    if raw is None:raw={p.relative_to(case.worker).as_posix():p.read_bytes() for p in case.worker.rglob('*') if p.is_file()}
    raw=dict(raw)
    pins={n:d.pin(b) for n,b in raw.items() if n not in d.EXCLUDED}
    raw['completion.json']=d.codec.canonical(dict(files=pins,manifest_files=len(pins),logical_bytes=sum(v['bytes'] for v in pins.values())))
    (case.worker/'completion.json').write_bytes(raw['completion.json'])
    case.process['terminal_files']=len(raw)-int('launcher.json' in raw)
    case.process['terminal_bytes']=sum(len(b) for n,b in raw.items() if n!='launcher.json')
    raw['launcher.json']=d.codec.canonical(case.process);(case.worker/'launcher.json').write_bytes(raw['launcher.json'])
    directories={'.':(0,0)}
    for name in raw:
        for p in d.PurePosixPath(name).parents:
            if p.as_posix()!='.':directories[p.as_posix()]=(0,0)
    # Helper tests use this metadata image; end-to-end inspect always inventories real files.
    return dict(raw=raw,pins={n:d.pin(b) for n,b in raw.items()},files={},directories=directories)


@pytest.fixture(scope='module')
def inputs(tmp_path_factory):
    root=tmp_path_factory.mktemp('package_inputs');repo=root/'repo';repo.mkdir();packet=root/'packet';packet.mkdir()
    context=json.loads((PACKET/'context.json').read_bytes())
    for name in set(context['source_pins'])|set(d.KERNEL_SOURCES)|set(d.OUTER_SOURCES):
        target=repo/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/name).read_bytes())
    for n in d.PACKET_PINS:(packet/n).write_bytes((PACKET/n).read_bytes())
    exe=root/'python.exe';exe.write_bytes(b'ordinary fake executable identity; never launched')
    fixture=c.load_fixture();schedule=json.loads((packet/'packet.json').read_bytes())['schedule'];requests={}
    for h in range(-2,8):
        group=reference_requests(fixture,'on_time','early','full_temporal',h)
        for q in group['requests']:requests[(h,q.role,d.digest(c.plain(q.outages)))]=q
        base=group['requests'][0];q=replace(base,role='actual_P',outages=group['actual_outage'],anchor_id=base.identity)
        requests[(h,q.role,d.digest(c.plain(q.outages)))]=q
    for h in (1,2):
        for q in c.hour_requests(fixture,'on_time','early','full_temporal',h)['requests']:
            requests[(h,q.role,d.digest(c.plain(q.outages)))]=q
    return SimpleNamespace(root=root,repo=repo,packet=packet,exe=exe,fixture=fixture,schedule=schedule,requests=requests)


def build(inputs,root,count=319,numeric=False,terminal_rejection=False):
    worker=root/'worker';par=root/'parent';worker.mkdir(parents=True);par.mkdir()
    pins=dict(preparation_sources=json.loads((inputs.packet/'context.json').read_bytes())['source_pins'],
        P2_sources={n:d.pin((inputs.repo/n).read_bytes()) for n in d.KERNEL_SOURCES},preparation_files=d.PACKET_PINS,
        legacy_scientific_and_P1_runtime=dict(executable=str(inputs.exe),runtime=dict(executable_sha256=d.pin(inputs.exe.read_bytes())['sha256'])))
    reg=dict(schema='staged_rts24_P2_execution_registration_v1',authority='DRAFT_NONAUTHORITATIVE',native_authorized=False,
        output=str(worker),limits=d.CAPS,point_limits=d.POINT_LIMITS,fresh_limits=d.FRESH_LIMITS,max_point_attempts=319,
        packet_pin=d.PACKET_PINS['packet.json'],authorization='separate_explicit_user_instruction_required_not_granted_by_this_file',
        schedule_sha=d.digest(inputs.schedule),pins=pins,preserved=dict(ordinary_metadata_fixture=True))
    registration=root/'registration.json';save(registration,reg);registration_sha=d.pin(registration.read_bytes())['sha256']
    raw={};points={};states=[];state_map={};events=[];rows=[];query_ids={};memo={}
    def cached_digest(value):
        key=id(value);prior=memo.get(key)
        if prior is None:
            prior=(value,c.digest(value));memo[key]=prior
        assert prior[0] is value
        return prior[1]
    def write(name,value):raw[name]=d.codec.canonical(value)
    def put(prefix,value):
        identity,blobs=d.codec.pack(value)
        for k,b in blobs.items():raw[prefix+k+'.json']=b
        return identity
    def event(stage,**kw):events.append(dict(stage=stage,sequence=len(events)+1,elapsed=len(events)*.001,**kw))
    state=ExecutionState(inputs.fixture.source_identity,'on_time','early','full_temporal',inputs.fixture.parameters,
        -2,4,8,'ordinary metadata only',DebtLedger('ordinary','metadata',0));states.append(state)
    def prepared_for(hour):
        slots=[s for s in inputs.schedule if s['section']=='actual' and s['hour']==hour];by_role={s['role']:points[s['ordinal']] for s in slots[:-1]}
        evidence=HourEvidence(by_role['reference_base_P0'],by_role.get('reference_raw_need'),by_role['recovery_min_meter'],by_role['recovery_max_meter'])
        prepared=PreparedHour(cached_digest(state),c.observe(inputs.fixture,'on_time','early',hour),evidence,Q(0),Q(0),Q(0),Q(0),Q(0),Q(0),Q(0),
            by_role['recovery_min_meter'].query.request.outages,'{}')
        kwargs={f.name:(cached_digest(state) if f.name=='state_sha' else cached_digest(prepared) if f.name=='prepared_sha' else () if f.name in ('allocations','violations') else Q(0)) for f in d.fields(Proposal)}
        return prepared,Proposal(**kwargs)
    event('start')
    for slot in inputs.schedule[:count]:
        i=slot['ordinal'];q=inputs.requests[(slot['hour'],slot['role'],d.digest(slot['outage']))];parent=points.get(slot['parent_slot'])
        query=c.BoundQuery(q,None if parent is None else parent.query,None if parent is None else parent.point,None if parent is None else parent.economic)
        qid=query.identity;query_ids[i]=qid
        witness=c.PointWitness(qid,0.,0.,(),(),());economic=child=None
        if slot['evidence_kind']=='economic_kkt':economic=c.EconomicEvidence(qid,cached_digest(witness),(),(),(),(),(),())
        elif slot['evidence_kind']=='child_lp_kkt':child=ChildLpEvidence(qid,cached_digest(witness),'a'*64,(),(),(),(),(),())
        evidence=PointEvidence(query,witness,economic,child);prefix=f'points/point_{i:04d}/';objects=prefix+'cas/objects/'
        query_ref=put(objects,query);gate=slot['state_after_actual_slot']
        binding=dict(ordinal=i,slot_sha=d.digest(slot),request_sha=q.identity,bound_query_sha=qid,parent_slot=slot['parent_slot'],
            parent_point_sha=None if parent is None else cached_digest(parent.point),parent_economic_sha=None if parent is None else cached_digest(parent.economic),
            state_after_actual_slot=gate,accepted_state_sha=None if gate is None else state_map[gate])
        request=dict(ordinal=i,query_ref=query_ref,query_sha=qid,problem_sha=d.digest(dict(ordinary_problem=i)),pins_sha=d.digest(pins),
            role=q.role,hour=q.hour,registration_sha=registration_sha,execution_binding=binding)
        write(prefix+'request.json',request);raw[prefix+'native.log']=b'ordinary metadata log; no native execution\n'
        write(prefix+'native.json',dict(problem_sha=request['problem_sha'],log_pin=d.pin(raw[prefix+'native.log']),run_invoked=True,run_returned=True))
        failed=numeric and i==count;ref=None if failed else put(objects,evidence)
        write(prefix+'result.json',dict(status='numeric_unresolved' if failed else 'imported',error=dict(type='UnresolvedNumeric',message='ordinary') if failed else None,
            evidence_ref=ref,raw_pin=d.pin(raw[prefix+'native.json']),request_sha=d.pin(raw[prefix+'request.json'])['sha256'],query_sha=qid,
            problem_sha=request['problem_sha'],infeasibility_inferred=False))
        write(prefix+'process.json',process(1000+i,numeric=failed));write(prefix+'point_observations.json',dict(allow_native=True))
        raw[prefix+'point.stdout.log']=raw[prefix+'point.stderr.log']=b'';event('point_reserved',ordinal=i,role=q.role,hour=q.hour)
        if failed:break
        points[i]=evidence;event('point_imported',ordinal=i)
        if q.role=='actual_P':
            prepared,proposal=prepared_for(q.hour)
            row=dict(prepared=prepared,proposal=proposal,actual=evidence,actual_audit=dict(point_constraints_satisfied=True),
                actual_accepted=not terminal_rejection,proposal_ledger_applied=not terminal_rejection,violations=('actual_network_point',) if terminal_rejection else (),
                full_replay_conditions_satisfied=not terminal_rejection,ledger_scope='accepted_static_dc_policy_execution',fx_contract_status='not_evaluated_by_actual_path_step')
            state=replace(state,records=state.records+(row,),ledger=state.ledger if terminal_rejection else DebtLedger('ordinary','metadata',len(states)),stopped=terminal_rejection)
            states.append(state)
            if not terminal_rejection:state_map[i]=cached_digest(state)
            event('hour_adopted',next_hour=state.next_hour,stopped=terminal_rejection)
        if slot['section']=='contract' and q.role=='fault_raw_need':
            normal,firm=points[slot['parent_slot']],points[i-1]
            rows.append(dict(hour=q.hour,outage=asdict(q.outages),normal_query=query_ids[slot['parent_slot']],firm_query=query_ids[i-1],raw_query=qid,
                raw_curtailment_mw=0.,normal_point_sha=cached_digest(normal.point),normal_economic_sha=cached_digest(normal.economic),
                firm_point_sha=cached_digest(firm.point),raw_point_sha=cached_digest(witness),raw_optimality_sha=cached_digest(child),
                firm_audit=dict(point_constraints_satisfied=True),raw_optimality_audit=dict(lp_optimality_conditions_satisfied=True),
                legal_X=dict(point_legal_under_X=False,temporal_backing='not_established')))
            event('contract_row',hour=q.hour,rows=len(rows))
    if terminal_rejection and inputs.schedule[count-1]['role']!='actual_P':
        hour=inputs.schedule[count-1]['hour'];prepared,proposal=prepared_for(hour)
        row=dict(prepared=prepared,proposal=proposal,actual=None,actual_audit=None,actual_accepted=False,proposal_ledger_applied=False,
            violations=('connection_capacity',),full_replay_conditions_satisfied=False,ledger_scope='accepted_static_dc_policy_execution',fx_contract_status='not_evaluated_by_actual_path_step')
        state=replace(state,records=state.records+(row,),stopped=True);states.append(state);event('hour_adopted',next_hour=state.next_hour,stopped=True)
    journal='journal/objects/';fixture_ref=put(journal,inputs.fixture);initial=put(journal,states[0])
    def object_keys():return sorted(n[len(journal):] for n in raw if n.startswith(journal))
    genesis=dict(schema='staged_rts24_development_journal_v2',kind='genesis',codec=d.codec.SCHEMA,fixture_ref=fixture_ref,
        fixture_sha=cached_digest(inputs.fixture),state_ref=initial,after_state_sha=cached_digest(states[0]),plan='on_time',clean='early',method='full_temporal',
        runtime_identity=pins['legacy_scientific_and_P1_runtime']['runtime'],authority='DRAFT_NONAUTHORITATIVE',resume_permitted=False,after_cas_keys=object_keys())
    write('journal/genesis.json',genesis);genesis_sha=d.pin(raw['journal/genesis.json'])['sha256'];head=genesis_sha
    actual_numeric=numeric and inputs.schedule[count-1]['role']=='actual_P'
    outcome='known_rejection' if terminal_rejection else 'actual_unresolved' if actual_numeric else 'missing_input'
    def trusted(i,closed,current):return dict(genesis_sha=genesis_sha,known_head_sha=head,known_entries=i,known_state_sha=cached_digest(current),
        closed=closed,scientific_outcome=outcome if closed else None,publication_outcome='committed',failure_sha=None,known_cas_keys=object_keys())
    write('trusted_prefixes/prefix_000000.json',trusted(0,False,states[0]));prior_state=states[0]
    for i,current in enumerate(states[1:],1):
        payload=put(journal,dict(row=current.records[-1],independent_audit=dict(test_scope='unverified metadata')));state_ref=put(journal,current)
        entry=dict(schema=genesis['schema'],kind='hour',ordinal=i,previous_sha=head,before_state_sha=cached_digest(prior_state),
            after_state_sha=cached_digest(current),payload_ref=payload,state_ref=state_ref,after_cas_keys=object_keys())
        write(f'journal/entry_{i:06d}.json',entry);head=d.pin(raw[f'journal/entry_{i:06d}.json'])['sha256'];write(f'trusted_prefixes/prefix_{i:06d}.json',trusted(i,False,current));prior_state=current
    summary=dict(coverage_complete=False,method_conditions_satisfied=None,full_replay_conditions_satisfied=None,test_scope='metadata fixture')
    audit=dict(test_scope='unverified worker audit placeholder')
    attempt=None
    if actual_numeric:
        slot=inputs.schedule[count-1];prepared,proposal=prepared_for(slot['hour'])
        attempt=dict(stage='actual',observation=prepared.observation,evidence=prepared.evidence,prepared=prepared,proposal=proposal,actual=None,
            error_type='ValueError',error='ordinary unresolved actual',reference_request_ids=tuple(inputs.schedule[n-1]['request_sha'] for n in slot['reference_slots']),
            adopted=False,mathematical_infeasibility_inferred=False,after_state_sha=None)
    payload=put(journal,attempt if actual_numeric else dict(checkpoint_state=state,summary=summary,independent_audit=audit,scientific_outcome=outcome,resume_permitted=False,next_input='not_observed'))
    state_ref=put(journal,state);i=len(states)
    entry=dict(schema=genesis['schema'],kind='attempt' if actual_numeric else 'terminal',ordinal=i,previous_sha=head,before_state_sha=cached_digest(state),after_state_sha=None if actual_numeric else cached_digest(state),payload_ref=payload,state_ref=None if actual_numeric else state_ref,after_cas_keys=object_keys())
    write(f'journal/entry_{i:06d}.json',entry);head=d.pin(raw[f'journal/entry_{i:06d}.json'])['sha256'];write('trusted_binding.json',trusted(i,True,state))
    metrics=dict(state_sha=cached_digest(state),state_cas_sha=state_ref,summary=summary,independent_audit=audit,scientific_outcome=outcome,publication_outcome='committed',
        terminal_entry_present=not actual_numeric,state_certainty='known',closed_entry_present=True,unaccepted_attempt=c.plain(attempt),failure=None,pending_terminal_checkpoint=None,pending_cas_objects=[],
        unreferenced_final_cas_objects=[],genesis_sha=genesis_sha,head_sha=head,final_entries=i,saved_objects=len(object_keys()),resume_permitted=False)
    stage='contract_numeric' if count>41 else 'actual_numeric' if actual_numeric else 'reference_numeric';failure=dict(stage=stage,type='UnresolvedNumeric',message='ordinary') if numeric else None
    if numeric:write('numeric_failure.json',dict(**failure,infeasibility_inferred=False))
    complete=not (numeric or terminal_rejection)
    write('report.json',dict(authority='DRAFT_NONAUTHORITATIVE',package_complete=complete,failure=failure,point_attempts_reserved=count,points_imported=count-int(numeric),
        native_run_invoked_observed=count,native_run_returned_observed=count,fresh_launches=1,metrics=metrics,contracts=rows,full_139_executed=complete,
        actual_accepted_slots=list(state_map),resource_admission=False,overall_performance_review_complete=False,fx_temporal_backing=False,formal_result=False))
    write('contract_rows.json',rows);write('fresh.json',dict(metrics=metrics,solver_calls=0));write('fresh_process.json',process(2000))
    write('fresh_observations.json',dict(allow_native=False));write('worker_observations.json',dict(allow_native=False))
    write('launcher_start.json',dict(limits=d.CAPS,package='staged_rts24_P2_v1',registration_sha=registration_sha))
    write('start.json',dict(authority='DRAFT_NONAUTHORITATIVE',pins=pins,preserved=reg['preserved'],packet_pin=d.PACKET_PINS['packet.json'],max_point_attempts=319,
        registration_sha=registration_sha,native_user_authority='external_explicit_user_instruction_not_inferred_from_files'))
    for n in d.EXCLUDED|{'fresh.stdout.log','fresh.stderr.log'}:raw.setdefault(n,b'')
    event('fresh_reserved');event('fresh_returned');event('report',package_complete=complete)
    raw['events.jsonl']=b'\n'.join(d.codec.canonical(e) for e in events)+b'\n'
    for name,b in raw.items():p=worker/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
    record=process(1000,[1000,*range(1001,1001+count),2000,2500],numeric=numeric or terminal_rejection)
    case=SimpleNamespace(worker=worker,parent=par,process=record,registration=registration,reg=reg,inputs=inputs,points=points,state_map=state_map,rows=rows)
    case.snapshot=balance(case,raw);case.context=d.context_bytes(inputs.repo,worker,par,registration,inputs.packet,inputs.exe);case.sha=d.pin(case.context)['sha256'];case.startup=json.loads(case.context)['startup']
    return case


@pytest.fixture(scope='module')
def full(inputs,tmp_path_factory):return build(inputs,tmp_path_factory.mktemp('full_protocol'))


def inspect(case,**kw):return d.inspect_package(case.context,case.sha,case.process,case.startup,**kw)


@contextmanager
def changed(path,value):
    raw=path.read_bytes()
    try:path.write_bytes(value);yield
    finally:path.write_bytes(raw)


def test_full_saved_protocol_closes_with_negative_X_and_scientific_flags_false(full):
    result=inspect(full)
    assert result['inspection_status']=='success_protocol_closed',result['protocol_error']
    assert (result['point_reference_count'],result['contract_row_reference_count'],result['actual_state_reference_count'])==(319,138,10)
    assert result['mechanical_package_integrity'] and result['inner_process_records_verified'] and result['journal_reference_chain_verified']
    assert all(result[n] is False for n in ('scientific_evidence_adopted','scientific_audit_replayed','full_139_independently_verified','formal_result','resource_admission','actual_spawn_argv_verified','typed_values_validated'))
    assert all(r['legal_X']['point_legal_under_X'] is False for r in full.rows)
    assert result['unverified_worker_claims']==dict(full_139_executed=True,package_complete=True)
    assert result['outer_residual_member_count']==2 and result['outer_member_count']==result['known_inner_member_count']+2
    assert result['outer_residual_member_identities']==[dict(pid=p,creation_filetime=4560000+p) for p in (1000,2500)]
    assert result['process_tree_attribution_independently_verified'] is False


@pytest.mark.parametrize('count,rows',[(1,0),(4,0),(5,0),(319,137)])
def test_numeric_diagnostic_uses_observed_prefix_and_never_upgrades_success(inputs,tmp_path,full,count,rows):
    if count!=319:case=build(inputs,tmp_path,count,numeric=True)
    else:
        # Reuse saved synthetic bytes; avoid rebuilding 319 placeholder dataclass graphs.
        worker=tmp_path/'worker';par=tmp_path/'parent';worker.mkdir();par.mkdir()
        for name,b in full.snapshot['raw'].items():
            p=worker/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
        reg=json.loads(d.codec.canonical(full.reg));reg['output']=str(worker);registration=tmp_path/'registration.json';save(registration,reg)
        reg_sha=d.pin(registration.read_bytes())['sha256']
        for i in range(1,320):
            p=worker/f'points/point_{i:04d}/request.json';request=json.loads(p.read_bytes());request['registration_sha']=reg_sha;save(p,request)
            p=worker/f'points/point_{i:04d}/result.json';result=json.loads(p.read_bytes());result['request_sha']=d.pin((p.parent/'request.json').read_bytes())['sha256'];save(p,result)
        last=worker/'points/point_0319';result=json.loads((last/'result.json').read_bytes());result.update(status='numeric_unresolved',error=dict(type='UnresolvedNumeric',message='ordinary'),evidence_ref=None);save(last/'result.json',result)
        keep=set(d.codec.pack(full.points[319].query)[1])
        for p in (last/'cas/objects').iterdir():
            if p.stem not in keep:p.unlink()
        save(last/'process.json',process(1319,numeric=True))
        failure=dict(stage='contract_numeric',type='UnresolvedNumeric',message='ordinary');report=json.loads((worker/'report.json').read_bytes())
        report.update(package_complete=False,full_139_executed=False,failure=failure,points_imported=318,contracts=report['contracts'][:-1]);save(worker/'report.json',report)
        save(worker/'contract_rows.json',report['contracts']);save(worker/'numeric_failure.json',dict(**failure,infeasibility_inferred=False))
        save(worker/'launcher_start.json',dict(limits=d.CAPS,package='staged_rts24_P2_v1',registration_sha=reg_sha))
        start=json.loads((worker/'start.json').read_bytes());start['registration_sha']=reg_sha;save(worker/'start.json',start)
        events=[json.loads(b) for b in full.snapshot['raw']['events.jsonl'].splitlines()]
        events=[e for e in events if not (e['stage']=='point_imported' and e['ordinal']==319 or e['stage']=='contract_row' and e['rows']==138)]
        for i,e in enumerate(events,1):e['sequence']=i
        events[-1]['package_complete']=False;(worker/'events.jsonl').write_bytes(b'\n'.join(d.codec.canonical(e) for e in events)+b'\n')
        case=SimpleNamespace(worker=worker,parent=par,process=process(1000,[1000,*range(1001,1320),2000,2500],numeric=True))
        balance(case);case.context=d.context_bytes(inputs.repo,worker,par,registration,inputs.packet,inputs.exe);case.sha=d.pin(case.context)['sha256'];case.startup=json.loads(case.context)['startup']
    result=inspect(case)
    assert result['inspection_status']=='numeric_diagnostic_closed',result['protocol_error']
    assert (result['point_reference_count'],result['points_imported'],result['contract_row_reference_count'])==(count,count-1,rows)
    assert result['unverified_worker_claims']==dict(package_complete=False,full_139_executed=False)
    assert result['scientific_evidence_adopted'] is False


@pytest.mark.parametrize('fault',['quiet','owner','handles','cleanup','incomplete'])
def test_unknown_ownership_never_reads_inputs_or_worker(full,monkeypatch,fault):
    record=json.loads(d.codec.canonical(full.process));w=record['quiescence_witness']
    if fault=='quiet':record['job_quiet_confirmed']=False
    elif fault=='owner':record['owner_creation_filetime']+=1
    elif fault=='handles':w['all_handles_signaled']=False
    elif fault=='cleanup':record['cleanup_error']='close failed'
    else:w['complete_inventory']=False
    monkeypatch.setattr(d,'read_inputs',lambda *a:pytest.fail('input read before ownership quiet'))
    monkeypatch.setattr(d,'inventory',lambda *a:pytest.fail('worker read before ownership quiet'))
    result=d.inspect_package(full.context,full.sha,record,full.startup)
    assert result['inspection_status']=='inspection_prohibited' and result['inventory'] is None


@pytest.mark.parametrize('fault',['exit3','monitor','wall'])
def test_failed_exit_with_success_appearance_captures_inventory_only(full,monkeypatch,fault):
    record=json.loads(d.codec.canonical(full.process))
    if fault=='exit3':record['exit_code']=3
    elif fault=='monitor':record['monitor_error']='sample failed'
    else:record['stop_reason']='wall_limit'
    monkeypatch.setattr(d,'protocol',lambda *a:pytest.fail('success protocol inspected after failed execution'))
    monkeypatch.setattr(d,'inventory',lambda *a:full.snapshot)
    result=d.inspect_package(full.context,full.sha,record,full.startup)
    assert result['inspection_status']=='failure_inventory_captured' and result['full_inventory_verified']
    assert result['mechanical_package_integrity'] is False


def test_partial_failed_inventory_needs_no_completion_report_or_failure_file(inputs,tmp_path,monkeypatch):
    case=build(inputs,tmp_path,1,numeric=True)
    for p in case.worker.rglob('*'):
        if p.is_file():p.unlink()
    save(case.worker/'points/point_0001/request.json.pending',dict(ordinary_partial=True));case.process['exit_code']=3
    monkeypatch.setattr(d,'protocol',lambda *a:pytest.fail('partial package subjected to success schema'))
    result=inspect(case)
    assert result['inspection_status']=='failure_inventory_captured' and result['inventory_files']==1
    assert result['completion_core_verified'] is False


@pytest.mark.parametrize('count',[3,4])
def test_known_rejection_keeps_committed_hour_separate_from_accepted_actual(inputs,tmp_path,count):
    case=build(inputs,tmp_path,count,terminal_rejection=True);result=inspect(case)
    assert result['inspection_status']=='terminal_diagnostic_closed',result['protocol_error']
    assert result['committed_hour_entries']==1 and result['actual_state_reference_count']==0
    assert result['points_imported']==count and result['contract_row_reference_count']==0
    assert result['unverified_worker_claims']==dict(package_complete=False,full_139_executed=False)


@pytest.fixture(scope='module')
def actual_numeric(inputs,tmp_path_factory):return build(inputs,tmp_path_factory.mktemp('actual_numeric'),4,numeric=True)


@pytest.mark.parametrize('fault',['accepted_missing','closed','unaccepted','orphans','active_outcome'])
def test_actual_attempt_metrics_and_imported_slot_edges_are_required(actual_numeric,fault):
    case=actual_numeric;raw=dict(case.snapshot['raw']);report=json.loads(raw['report.json'])
    if fault=='accepted_missing':report['points_imported']=4
    elif fault=='closed':report['metrics']['closed_entry_present']=False
    elif fault=='unaccepted':report['metrics']['unaccepted_attempt']=None
    elif fault=='orphans':report['metrics']['unreferenced_final_cas_objects']=['a'*64+'.json']
    else:
        name='trusted_prefixes/prefix_000000.json';v=json.loads(raw[name]);v['scientific_outcome']='complete';raw[name]=d.codec.canonical(v)
    with pytest.raises(ValueError):d.journal_references(raw,case.inputs.schedule,report,case.reg,json.loads((case.inputs.packet/'packet.json').read_bytes()))


@pytest.mark.parametrize('fault',['owner','helper'])
def test_internal_jobs_cannot_share_identities(full,fault):
    raw=dict(full.snapshot['raw']);record=json.loads(raw['points/point_0002/process.json'])
    if fault=='owner':record=json.loads(raw['points/point_0001/process.json'])
    else:
        member=dict(pid=1001,creation_filetime=4561001);record['quiescence_witness']['member_identities'].append(member)
        record['quiescence_witness']['total_processes']=record['quiescence_witness']['observed_unique_member_handles']=2
    raw['points/point_0002/process.json']=d.codec.canonical(record)
    members={(m['pid'],m['creation_filetime']) for m in full.process['quiescence_witness']['member_identities']}
    with pytest.raises(ValueError,match='overlap'):d.point_references(raw,full.snapshot['pins'],full.inputs.schedule,319,319,full.reg,
        json.loads(full.context)['registration']['pin']['sha256'],full.state_map,members)


def test_numeric_exit_requires_fixed_guard_stop_reason():
    r=process(1001,numeric=True);r['stop_reason']=None
    with pytest.raises(ValueError,match='process protocol'):d.process_ok(r,d.POINT_LIMITS,{(1001,4561001)},numeric=True)


def payload_variant(case,change):
    """Rehash a synthetic closing payload and all metadata edges to isolate its schema."""
    raw=dict(case.snapshot['raw']);report=json.loads(raw['report.json']);i=report['metrics']['final_entries'];path=f'journal/entry_{i:06d}.json';entry=json.loads(raw[path])
    view=d.WireView(raw,'journal/objects/');payload=json.loads(d.codec.canonical(view.get(entry['payload_ref'],'dict')));change(payload)
    prefix=json.loads(raw[f'trusted_prefixes/prefix_{i-1:06d}.json']);keep=set(prefix['known_cas_keys']);ref,blobs=d.codec.pack(payload)
    for n in list(raw):
        if n.startswith('journal/objects/') and n.rsplit('/',1)[-1] not in keep:del raw[n]
    for key,b in blobs.items():raw['journal/objects/'+key+'.json']=b;keep.add(key+'.json')
    entry['payload_ref']=ref;entry['after_cas_keys']=sorted(keep);raw[path]=d.codec.canonical(entry);head=d.pin(raw[path])['sha256']
    trusted=json.loads(raw['trusted_binding.json']);trusted.update(known_head_sha=head,known_cas_keys=sorted(keep));raw['trusted_binding.json']=d.codec.canonical(trusted)
    report['metrics'].update(head_sha=head,saved_objects=len(keep))
    if entry['kind']=='attempt':report['metrics']['unaccepted_attempt']=payload
    return raw,report


@pytest.mark.parametrize('fault',['evidence','adopted','infeasibility','extra'])
def test_actual_attempt_payload_cannot_drift_independently(actual_numeric,fault):
    def change(p):
        if fault=='evidence':p['evidence']=None
        elif fault=='adopted':p['adopted']=True
        elif fault=='infeasibility':p['mathematical_infeasibility_inferred']=True
        else:p['scientific_evidence_adopted']=True
    case=actual_numeric;raw,report=payload_variant(case,change)
    with pytest.raises(ValueError):d.journal_references(raw,case.inputs.schedule,report,case.reg,json.loads((case.inputs.packet/'packet.json').read_bytes()))


@pytest.mark.parametrize('fault',['extra','next_input'])
def test_terminal_payload_has_closed_fields_and_original_next_input(reference_numeric,fault):
    case=reference_numeric
    def change(p):p['scientific_evidence_adopted' if fault=='extra' else 'next_input']=True
    raw,report=payload_variant(case,change)
    with pytest.raises(ValueError):d.journal_references(raw,case.inputs.schedule,report,case.reg,json.loads((case.inputs.packet/'packet.json').read_bytes()))


@pytest.mark.parametrize('fault',['extra','type_scalar','message_scalar'])
def test_numeric_error_record_has_closed_string_fields(actual_numeric,fault):
    case=actual_numeric;raw=dict(case.snapshot['raw']);p='points/point_0004/result.json';value=json.loads(raw[p])
    if fault=='extra':value['error']['infeasibility_inferred']=True
    elif fault=='type_scalar':value['error']['type']=1
    else:value['error']['message']=False
    raw[p]=d.codec.canonical(value);members={(m['pid'],m['creation_filetime']) for m in case.process['quiescence_witness']['member_identities']}
    with pytest.raises(ValueError):d.point_references(raw,case.snapshot['pins'],case.inputs.schedule,4,3,case.reg,json.loads(case.context)['registration']['pin']['sha256'],case.state_map,members)


@pytest.mark.parametrize('which',['registration','packet','prepared_source','kernel_source','outer_source','exe'])
def test_input_byte_drift_prevents_worker_read(full,monkeypatch,which):
    context=json.loads(full.context)
    paths=dict(registration=full.registration,packet=full.inputs.packet/'packet.json',prepared_source=full.inputs.repo/next(iter(full.reg['pins']['preparation_sources'])),
        kernel_source=full.inputs.repo/d.KERNEL_SOURCES[0],outer_source=full.inputs.repo/d.OUTER_SOURCES[0],exe=full.inputs.exe)
    monkeypatch.setattr(d,'inventory',lambda *a:pytest.fail('worker read after input identity drift'))
    with changed(paths[which],b'drift'):
        with pytest.raises((ValueError,KeyError)):inspect(full)


@pytest.mark.parametrize('fault',['argv','cwd','root','limits','authority','context_sha'])
def test_context_and_parent_startup_are_closed_and_held(full,fault):
    startup=json.loads(d.codec.canonical(full.startup));raw=full.context;sha=full.sha
    if fault=='context_sha':sha='0'*64
    elif fault=='authority':v=json.loads(raw);v['native_authorized']=True;raw=d.codec.canonical(v);sha=d.pin(raw)['sha256']
    elif fault=='argv':startup['argv'].append('--fresh')
    elif fault=='cwd':startup['cwd']=str(full.parent)
    elif fault=='root':startup['worker_root']=str(full.parent)
    else:startup['limits']['wall_seconds']=3601
    with pytest.raises(ValueError):d.inspect_package(raw,sha,full.process,startup)


@pytest.mark.parametrize('fault',['extra','missing','nested_exclusion','pin','count','bool_count','bytes'])
def test_completion_recomputes_exact_root_exclusions(full,fault):
    raw=dict(full.snapshot['raw']);pins=dict(full.snapshot['pins']);value=json.loads(raw['completion.json'])
    if fault=='extra':raw['extra.json']=b'{}';pins['extra.json']=d.pin(b'{}')
    elif fault=='missing':raw.pop('worker.stdout.log');pins.pop('worker.stdout.log')
    elif fault=='nested_exclusion':raw['points/completion.json']=b'{}';pins['points/completion.json']=d.pin(b'{}')
    elif fault=='pin':value['files']['report.json']['sha256']='0'*64
    elif fault=='count':value['manifest_files']+=1
    elif fault=='bool_count':value['manifest_files']=True
    else:value['logical_bytes']+=1
    raw['completion.json']=d.codec.canonical(value)
    with pytest.raises(ValueError):d.completion(raw,pins)


@pytest.mark.parametrize('fault',['ordinal','binding','parent','state','raw','log','cas','witness'])
def test_point_reference_and_internal_job_corruption_rejected(full,fault):
    raw=dict(full.snapshot['raw']);pins=dict(full.snapshot['pins']);i=2 if fault in ('parent','state') else 1
    path=f'points/point_{i:04d}/request.json';v=json.loads(raw[path])
    if fault=='ordinal':v['ordinal']=2
    elif fault=='binding':v['execution_binding']['bound_query_sha']='0'*64
    elif fault=='parent':v['execution_binding']['parent_point_sha']='0'*64
    elif fault=='state':v['execution_binding']['accepted_state_sha']='0'*64
    elif fault in ('raw','log'):raw[f'points/point_0001/native.{"json" if fault=="raw" else "log"}']=b'changed'
    elif fault=='cas':raw.pop(next(n for n in raw if n.startswith('points/point_0001/cas/objects/')))
    else:
        p='points/point_0001/process.json';record=json.loads(raw[p]);record['quiescence_witness']['all_handles_signaled']=False;raw[p]=d.codec.canonical(record)
    raw[path]=d.codec.canonical(v);pins={n:d.pin(b) for n,b in raw.items()}
    members={(m['pid'],m['creation_filetime']) for m in full.process['quiescence_witness']['member_identities']}
    with pytest.raises((ValueError,KeyError,TypeError)):
        d.point_references(raw,pins,full.inputs.schedule,319,319,full.reg,json.loads(full.context)['registration']['pin']['sha256'],full.state_map,members)


@pytest.mark.parametrize('fault',['missing','order','duplicate','point_sha'])
def test_contract_reference_failures_do_not_change_negative_X(full,fault):
    rows=json.loads(d.codec.canonical(full.rows));points={i:dict(query_sha=e.query.identity,point_sha=c.digest(e.point),economic_sha=None if e.economic is None else c.digest(e.economic),
        child_sha=None if e.child_lp is None else c.digest(e.child_lp),point=c.plain(e.point)) for i,e in full.points.items()}
    if fault=='missing':rows.pop()
    elif fault=='order':rows[0],rows[1]=rows[1],rows[0]
    elif fault=='duplicate':rows[1]=rows[0]
    else:rows[0]['raw_point_sha']='0'*64
    with pytest.raises(ValueError):d.contract_references(rows,full.inputs.schedule,points,319)


@pytest.mark.parametrize('fault',['sequence','nonfinite','order'])
def test_events_require_serial_protocol(full,fault):
    events=[json.loads(v) for v in full.snapshot['raw']['events.jsonl'].splitlines()]
    if fault=='sequence':events[1]['sequence']=True
    elif fault=='nonfinite':events[1]['elapsed']=-1
    else:events[1]['stage']='point_imported'
    raw=b'\n'.join(d.codec.canonical(v) for v in events)+b'\n'
    with pytest.raises(ValueError):d.events_check(raw,full.inputs.schedule,319,319,10,138,True)


def test_inventory_bookend_drift_never_returns_a_verified_package(reference_numeric):
    case=reference_numeric;target=case.worker/'worker.stdout.log'
    with changed(target,target.read_bytes()):
        def hook(stage,root):target.write_bytes(b'late changed')
        record=json.loads(d.codec.canonical(case.process));record['exit_code']=3
        with pytest.raises(ValueError,match='bookend'):d.inspect_package(case.context,case.sha,record,case.startup,hook=hook)


def test_inventory_bounds_metadata_before_content_and_rejects_hardlinks(tmp_path,monkeypatch):
    large=tmp_path/'large'
    with large.open('wb') as f:f.truncate(d.CAPS['output_bytes']+1)
    monkeypatch.setattr(d,'bounded_file_bytes',lambda *a:pytest.fail('content read before tree bound'))
    with pytest.raises(d.InventoryLimit):d.inventory(tmp_path)
    large.unlink();a=tmp_path/'a';a.write_bytes(b'x');os.link(a,tmp_path/'b')
    with pytest.raises(ValueError,match='nonordinary'):d.inventory(tmp_path)


@pytest.mark.parametrize('name',['../outside','a/../outside','a//b','/absolute','C:/absolute','a\\b','a.','a '])
def test_noncanonical_relative_paths_rejected(name):
    with pytest.raises(ValueError):d.relative(name)


def test_wire_reference_cycle_and_duplicate_fields_are_rejected():
    one='a'*64
    view=object.__new__(d.WireView);view.objects={one:dict(kind='dict',payload=['dict',[['a',['ref',one]]]])};view.cache={};view.active=set();view.nodes=0
    with pytest.raises(ValueError,match='cyclic'):view.get(one)
    view.active=set();view.cache={};view.objects[one]['payload']=['dict',[['a',1],['a',2]]]
    with pytest.raises(ValueError,match='uniqueness'):view.get(one)


def test_import_does_not_import_runner_or_start_process():
    # The module uses frozen codec class definitions; it never imports an experiment runner.
    assert 'subprocess' not in d.__dict__ and 'experiments.staged_rts24_p2_native_probe_v1' not in d.__dict__


@pytest.mark.parametrize('size',[0,17,8*1024**2])
def test_bounded_reader_retains_bytes_and_requests_observed_size_plus_one(tmp_path,monkeypatch,size):
    path=tmp_path/'object';data=b'x'*size;path.write_bytes(data);real_open=Path.open;requests=[]
    class Reader:
        def __enter__(self):self.stream=real_open(path,'rb');return self
        def __exit__(self,*args):self.stream.close()
        def fileno(self):return self.stream.fileno()
        def read(self,n):requests.append(n);return self.stream.read(n)
    monkeypatch.setattr(Path,'open',lambda p,*a,**kw:Reader() if p==path else real_open(p,*a,**kw))
    assert d.bounded_file_bytes(path)==data and requests==[size+1]


@pytest.mark.parametrize('fault',['over_limit','metadata','first_fstat','second_fstat','short','grow','truncate','path_replace','directory'])
def test_bounded_reader_identity_and_length_failure_windows(tmp_path,monkeypatch,fault):
    path=tmp_path/'object';path.write_bytes(b'abc');real_open=Path.open;real_fstat=os.fstat;real_dirs=d.codec.directory_identity
    calls=dict(fstat=0,directory=0,read=0)
    if fault=='over_limit':
        with real_open(path,'wb') as stream:stream.truncate(8*1024**2+1)
    def fake_fstat(fd):
        info=real_fstat(fd);calls['fstat']+=1
        if calls['fstat']==({'first_fstat':1,'second_fstat':2}.get(fault,0)):
            return SimpleNamespace(st_dev=info.st_dev,st_ino=info.st_ino+1,st_size=info.st_size,st_mtime_ns=info.st_mtime_ns)
        return info
    def dirs(p):
        value=real_dirs(p);calls['directory']+=1
        return value+(('changed_ancestor',0,0),) if fault=='directory' and calls['directory']==2 else value
    class Reader:
        def __enter__(self):self.stream=real_open(path,'rb');return self
        def __exit__(self,*args):
            self.stream.close()
            if fault=='path_replace':
                other=tmp_path/'replacement';other.write_bytes(b'abc');os.replace(other,path)
        def fileno(self):return self.stream.fileno()
        def read(self,n):
            calls['read']+=1;raw=self.stream.read(n)
            if fault in ('grow','truncate'):
                with real_open(path,'wb') as out:out.write(b'abcdef' if fault=='grow' else b'a')
            return raw[:-1] if fault=='short' else raw
    monkeypatch.setattr(os,'fstat',fake_fstat);monkeypatch.setattr(d.codec,'directory_identity',dirs)
    monkeypatch.setattr(Path,'open',lambda p,*a,**kw:Reader() if p==path else real_open(p,*a,**kw))
    with pytest.raises(ValueError):d.bounded_file_bytes(path,(0,0,3,0) if fault=='metadata' else None)
    if fault in ('over_limit','metadata','first_fstat'):assert calls['read']==0


@pytest.mark.parametrize('fault',['hardlink','reparse','symlink'])
def test_bounded_reader_rejects_link_forms(tmp_path,monkeypatch,fault):
    path=tmp_path/'object';path.write_bytes(b'abc')
    if fault=='hardlink':os.link(path,tmp_path/'link')
    else:
        real_lstat=os.lstat
        def lstat(p,*a,**kw):
            info=real_lstat(p,*a,**kw)
            if Path(p)==path:return SimpleNamespace(st_mode=stat.S_IFLNK if fault=='symlink' else info.st_mode,st_file_attributes=0 if fault=='symlink' else 0x400)
            return info
        monkeypatch.setattr(os,'lstat',lstat)
    with pytest.raises(ValueError):d.bounded_file_bytes(path)


@pytest.fixture(scope='module')
def reference_numeric(inputs,tmp_path_factory):return build(inputs,tmp_path_factory.mktemp('reference_numeric'),1,numeric=True)


def test_saved_P1_wire_projection_matches_original_state_and_bound_query_digests():
    # Read the frozen five-hour pack without imposing P2 acceptance conditions.
    root=ROOT/'results/tables/staged_rts24_native_v1_non_authoritative/p1_01'
    raw={'journal/objects/'+p.name:p.read_bytes() for p in (root/'journal/objects').iterdir()}
    view=d.WireView(raw,'journal/objects/');metrics=json.loads((root/'fresh.json').read_bytes())['metrics']
    assert d.digest(view.get(metrics['state_cas_sha'],'ExecutionState'))==metrics['state_sha']
    point=root/'points/point_0001';raw={'cas/objects/'+p.name:p.read_bytes() for p in (point/'cas/objects').iterdir()}
    view=d.WireView(raw,'cas/objects/');request=json.loads((point/'request.json').read_bytes());result=json.loads((point/'result.json').read_bytes())
    query=view.get(request['query_ref'],'BoundQuery');evidence=view.get(result['evidence_ref'],'PointEvidence')
    assert d.query_identity(query)==request['query_sha'] and d.same(evidence['query'],query)


def old_image(value):
    return ''.join(json.JSONEncoder(ensure_ascii=True,sort_keys=True,separators=(',',':'),allow_nan=False).iterencode(value)).encode('ascii')


@pytest.mark.parametrize('value',[None,True,1,-1,10**100,0.0,-0.0,5e-324,1e100,[],{},(),
    {'\u4e2d\U0001f600\ud800':['\x00\n\t"\\',False,{'v':1.25}]},[{'same':[1,2]}]*3])
def test_canonical_image_matches_old_streaming_bytes_and_hash(value):
    expected=old_image(value);assert d.canonical_image(value)==expected and d.digest(value)==d.pin(expected)['sha256']


@pytest.mark.parametrize('fault',['nan','infinity','integer_key','bool_key','float_key','none_key','string_subclass','int_subclass','float_subclass','tuple_subclass','list_subclass','dict_subclass','cycle','alias_bomb','depth'])
def test_canonical_image_rejects_unsupported_or_unbounded_inputs_before_final_encoding(monkeypatch,fault):
    value={'nan':float('nan'),'infinity':float('inf'),'integer_key':{1:'a'},'bool_key':{True:'a'},'float_key':{1.5:'a'},'none_key':{None:'a'}}.get(fault)
    if fault.endswith('_subclass'):
        kind={'string_subclass':str,'int_subclass':int,'float_subclass':float,'tuple_subclass':tuple,'list_subclass':list,'dict_subclass':dict}[fault];value=type('Subclass',(kind,),{})()
    elif fault=='cycle':value=[];value.append(value)
    elif fault in ('alias_bomb','depth'):
        value=[]
        for _ in range(23 if fault=='alias_bomb' else 514):value=[value,value] if fault=='alias_bomb' else [value]
    monkeypatch.setattr(d.json,'dumps',lambda *a,**kw:pytest.fail('final encoding requested before admission'))
    with pytest.raises(ValueError):d.canonical_image(value)


def test_canonical_image_exact_limit_and_local_cache_invalidation(monkeypatch):
    limit=8*1024**2;value=['x'*(limit-4)];assert len(d.canonical_image(value))==limit
    value[0]+='x';monkeypatch.setattr(d.json,'dumps',lambda *a,**kw:pytest.fail('oversize final encoding'))
    with pytest.raises(ValueError,match='byte limit'):d.canonical_image(value)
    monkeypatch.undo();shared={'v':1};root=[shared,shared];assert d.canonical_image(root)==old_image(root)
    shared['v']=2;assert d.canonical_image(root)==old_image(root) and b'2' in d.canonical_image(root)


def test_full_319_protocol_digest_entrances_match_old_streaming_oracle(full,monkeypatch):
    calls=[]
    def oracle(value):
        raw=d.canonical_image(value);expected=old_image(value);assert raw==expected
        calls.append((type(value).__name__,len(raw)));return d.pin(raw)['sha256']
    monkeypatch.setattr(d,'digest',oracle)
    result=d.protocol(full.snapshot,json.loads(full.context),full.reg,json.loads((full.inputs.packet/'packet.json').read_bytes()),full.process,False)
    assert result['point_reference_count']==319 and result['contract_row_reference_count']==138 and len(calls)>1000
    print(json.dumps(dict(oracle='full_319_all_protocol_digest_entrances',calls=len(calls),bytes=sum(n for _,n in calls),root_types=sorted({t for t,_ in calls}))))


def test_saved_P1_all_wire_roots_match_old_streaming_canonical_image():
    root=ROOT/'results/tables/staged_rts24_native_v1_non_authoritative/p1_01';calls=0;size=0
    groups=[(root/'journal/objects','journal/objects/')]+[(root/f'points/point_{i:04d}/cas/objects','cas/objects/') for i in range(1,32)]
    for folder,prefix in groups:
        view=d.WireView({prefix+p.name:p.read_bytes() for p in folder.iterdir()},prefix)
        for identity in view.objects:
            value=view.get(identity);raw=d.canonical_image(value);assert raw==old_image(value)
            calls+=1;size+=len(raw)
    assert calls>=403
    print(json.dumps(dict(oracle='all_saved_P1_wire_roots',roots=calls,bytes=size)))


@pytest.mark.parametrize('mode',['success_root','numeric_nested'])
def test_failure_marker_exemption_is_root_numeric_only(full,reference_numeric,mode):
    case=full if mode=='success_root' else reference_numeric;snapshot=dict(case.snapshot);raw=dict(snapshot['raw'])
    raw['numeric_failure.json' if mode=='success_root' else 'points/numeric_failure.json']=b'{}';snapshot['raw']=raw
    with pytest.raises(ValueError,match='failure|pending'):
        d.protocol(snapshot,json.loads(case.context),case.reg,json.loads((case.inputs.packet/'packet.json').read_bytes()),case.process,mode!='success_root')
