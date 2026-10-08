from dataclasses import replace
from fractions import Fraction
import pytest
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver,packet,spec
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_full_resource_contract as api


def example(hours=192):
    uids=tuple(f'g{i:03}' for i in range(158))
    order=(('operating_cost',None),*(('commitment',u) for u in uids[:73]),*(('generation',u) for u in uids))
    work=api.H1NormalWork('normal',hours,order,spec())
    content=api.content_inventory(232,hours)
    envelope=api.serial.TaskEnvelope('normal',232*hours+100,100,1000,
        content['total_content_limit_bytes']+100,200,1,1000,2000)
    resource=api.H1TaskResources(envelope,100)
    budget=api.serial.SerialResourceBudget(envelope.max_wall_seconds+10,10,100,100,1200,100,
        envelope.archive_bytes+envelope.scratch_bytes+100,1)
    return (work,),(resource,),budget


def test_full_inventory_and_independent_content_oracle():
    work,resources,budget=example()
    report=api.check_plan(work,resources,budget)
    assert report['declaration_consistent'] and report['solver_calls']==44544
    row=report['tasks'][0]
    assert row['reserved_solver_seconds_ratio']==(44544,1)
    assert row['required_declared_wall_seconds']==44644
    c=row['content']
    assert (c['child_events_per_hour'],c['registry_events_per_hour'],c['anchor_records_per_hour'])==(233,235,236)
    assert (c['parent_events'],c['parent_anchor_records'])==(384,385)
    # Separate arithmetic with literal protocol ceilings, including every header.
    expected=192*(232*16777216+(233+235)*262144+237*65536)+384*524288+386*65536
    assert c['total_content_limit_bytes']==expected
    assert not any(report[k] for k in ('model_shape_verified','whole_task_resources_verified',
        'physical_space_reserved','execution_authorized','formal_ready'))


@pytest.mark.parametrize('field,error',[
    ('max_total_wall_seconds','total_wall_shortfall'),
    ('max_additional_commit_bytes','serial_commit_shortfall'),
    ('max_additional_disk_bytes','retained_disk_shortfall')])
def test_one_unit_serial_shortfalls(field,error):
    work,resources,budget=example()
    report=api.check_plan(work,resources,replace(budget,**{field:getattr(budget,field)-1}))
    assert report['errors']==(('serial_plan',error),) and not report['declaration_consistent']


@pytest.mark.parametrize('field,error',[
    ('max_wall_seconds','task_wall_shortfall'),('archive_bytes','archive_content_and_overhead_shortfall')])
def test_task_shortfall_cannot_borrow_controller_reserve(field,error):
    work,(resource,),budget=example()
    envelope=replace(resource.envelope,**{field:getattr(resource.envelope,field)-1})
    report=api.check_plan(work,(replace(resource,envelope=envelope),),budget)
    assert report['errors']==(('normal',error),)


def test_exact_time_arithmetic_not_rounded_down_at_integer_boundary():
    work,resources,budget=example(hours=1)
    # 0.1 binary64 is above 1/10, so ten such slots require strictly over 1 s.
    order=(('operating_cost',None),*(('generation',str(i)) for i in range(9)))
    work=(replace(work[0],stage_order=order,specification=replace(spec(),time_limit_seconds=0.1)),)
    report=api.check_plan(work,resources,budget)
    assert report['tasks'][0]['required_declared_wall_seconds']==102
    n,d=report['tasks'][0]['reserved_solver_seconds_ratio']
    assert Fraction(n,d)==10*Fraction(0.1)>1


@pytest.mark.parametrize('fault',['hours_bool','hours_zero','hours_193','missing_cost','duplicate_uid',
    'order','unknown_commit','unknown_stage','old_work','duplicate_task','missing_resource','old_resource',
    'zero_overhead','bool_overhead','false_gap'])
def test_invalid_declarations_rejected(fault):
    work,resources,budget=example()
    w=work[0]
    if fault.startswith('hours_'):w=replace(w,hours={'hours_bool':True,'hours_zero':0,'hours_193':193}[fault])
    elif fault=='missing_cost':w=replace(w,stage_order=w.stage_order[1:])
    elif fault=='duplicate_uid':w=replace(w,stage_order=w.stage_order+(w.stage_order[-1],))
    elif fault=='order':w=replace(w,stage_order=(w.stage_order[0],)+tuple(reversed(w.stage_order[1:])))
    elif fault=='unknown_commit':w=replace(w,stage_order=(('operating_cost',None),('commitment','z'),('generation','g')))
    elif fault=='unknown_stage':w=replace(w,stage_order=(('operating_cost',None),('x','g')))
    elif fault=='old_work':w=object()
    elif fault=='missing_resource':resources=()
    elif fault=='old_resource':resources=(resources[0].envelope,)
    elif fault in ('zero_overhead','bool_overhead'):resources=(replace(resources[0],archive_overhead_bytes=0 if fault=='zero_overhead' else True),)
    elif fault=='false_gap':w=replace(w,specification=replace(spec(),mip_relative_gap=1e-4))
    work=(w,w) if fault=='duplicate_task' else (w,)
    with pytest.raises(ValueError):api.check_plan(work,resources,budget)


def test_current_hour_binding_matches_real_model_and_rejects_missing_stages():
    p=packet()
    order=api.replay.native.model_api.stage_order(p.inputs)
    work=api.H1NormalWork('n',1,order,spec())
    resource=api.H1TaskResources(api.serial.TaskEnvelope('n',100,50,1000,10**9,100,1,100,500),100)
    limits=api.replay.H1HourReplayLimits(3,100,500)
    result=api.bind_current_hour(work,resource,p,limits)
    assert result['model_shape_verified'] and result['solver_calls']==3 and not result['execution_authorized']
    with pytest.raises(ValueError,match='inventory'):
        api.bind_current_hour(replace(work,stage_order=(order[0],order[-1])),resource,p,limits)
    with pytest.raises(ValueError,match='shape'):
        api.bind_current_hour(work,replace(resource,envelope=replace(resource.envelope,max_variables=1)),p,limits)


def test_serial_memory_max_but_all_archives_and_scratch_retained():
    work,resources,budget=example(hours=1)
    other=replace(work[0],task_id='second')
    r=replace(resources[0],envelope=replace(resources[0].envelope,task_id='second',max_job_commit_bytes=900))
    report=api.check_plan(work+(other,),resources+(r,),replace(budget,
        max_total_wall_seconds=2*resources[0].envelope.max_wall_seconds+10,
        max_additional_disk_bytes=2*(resources[0].envelope.archive_bytes+200)+100))
    assert report['declaration_consistent']
    assert report['solver_calls']==464 and report['required_additional_commit_bytes']==1200


def test_current_hour_scope_overhead_and_endpoint_drift(tmp_path,monkeypatch):
    from pyomo.environ import Constraint,Var
    p=packet()
    source=api.replay.current.source
    work=api.H1NormalWork('n',1,api.replay.native.model_api.stage_order(p.inputs),spec())
    resource=api.H1TaskResources(api.serial.TaskEnvelope('n',100,50,1000,10**9,100,1,100,500),100)
    limits=api.replay.H1HourReplayLimits(3,100,500)
    for bad in (0,True):
        with pytest.raises(ValueError,match='overhead'):
            api.bind_current_hour(work,replace(resource,archive_overhead_bytes=bad),p,limits)
    # Synthetic legal boundary is only a shape-test input, not native evidence.
    before=source._owned(source.H1NormalBoundary,network_identity=p.network.identity,completed_hours=1,
        units=tuple((uid,on,power,age+1) for uid,on,power,age in p.before.units),
        evidence_role='numerical_lex_candidate')
    later=packet(relative_hour=1,before=before)
    with pytest.raises(ValueError,match='outside declared task'):
        api.bind_current_hour(work,resource,later,limits)
    build=api.replay.native.model_api.build_h1_stage_model
    calls=[]
    def drift(*a,**k):
        model=build(*a,**k)
        calls.append(True)
        if len(calls)==2:model.extra_shape_row=Constraint(expr=next(model.component_data_objects(Var))<=999.)
        return model
    monkeypatch.setattr(api.replay.native.model_api,'build_h1_stage_model',drift)
    with pytest.raises(ValueError,match='endpoint shape'):
        api.bind_current_hour(work,resource,p,limits)
