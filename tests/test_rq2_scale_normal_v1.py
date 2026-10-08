import ast
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path

import pytest

from test_rq2_continuous_grid_normal_v1 import fixture, model_for
from test_rq2_continuous_grid_candidate_v1 import install as old_install, runner as old_native
from src.rq2_joint_deliverability_boundary_v1 import scale_normal as api, scale_normal_budget as budgets
from src.rq2_joint_deliverability_boundary_v1 import scale_normal_replay as replay
from src.rq2_joint_deliverability_boundary_v1 import normal_execution_gurobi_ordered as old
from src.solvers import rq2_gurobi_ordered_development as old_adapter


def arguments(inputs, seconds=600):
    work, res = budgets.workload, budgets.resources
    pin = api.normal_input_identity(inputs)
    uids = tuple(sorted(g.uid for g in inputs.data.generators))
    normal = work.NormalWork('normal', 'training', pin, uids, inputs.source_hours, seconds)
    episode = work.EpisodeWork('episode', 'training', 'normal', pin, uids, inputs.source_hours, 1, (1,)*4)
    env = res.TaskEnvelope('normal', seconds+300, 300, 8*1024**3, 128*1024**2, 16*1024**2, 1, 30000, 100000)
    plan = budgets.NormalResourcePlan((normal,), (episode,), (env, replace(env, task_id='episode', max_wall_seconds=6000)),
        res.SerialResourceBudget(seconds+6400, 100, 1024, 1024, 9*1024**3, 1024, 1024**3, 1))
    budget = budgets.budget_for_task(plan, task_id='normal', max_observed_wall_seconds=seconds+120.,
        max_process_peak_working_set_bytes=8*1024**3, max_core_evidence_payload_bytes=16*1024**2)
    spec = api.Rq2SolverSpec('gurobi', '13.0.2', 1, 1e-8, 1e-9, 1e-9, 1e-9, 0, float(seconds), False)
    scale = api.model_scale(model_for(inputs))
    return dict(expected_input_identity=pin, expected_scale=scale, specification=spec, budget=budget,
        expected_execution_identity=api.normal_execution_identity(pin, scale, spec, budget), resource_plan=plan)


def install(monkeypatch, inputs, **kwargs):
    calls = old_install(monkeypatch, inputs, **kwargs)
    monkeypatch.setattr(api.native, 'create_solver', old_native.create_solver)
    return calls


def audit(result, inputs, args, data=None, **changes):
    data = replay.export_record(result) if data is None else data
    kw = dict(expected_sha256=sha256(data).hexdigest(), expected_result_identity=result.identity,
        expected_replay_identity=replay.replay_identity(args['expected_execution_identity'],
            args['specification'], args['budget']), max_record_bytes=32*1024**2, **args)
    kw.update(changes)
    return replay.replay_record(data, inputs, **kw)


def test_declared_long_budget_reaches_native_unchanged_and_replays_without_solver(monkeypatch):
    inputs = fixture(2)
    args = arguments(inputs)
    calls = install(monkeypatch, inputs)
    solve, received = api.native._solve, []
    def capture(builder, spec, budget, purpose):
        received.append((spec.time_limit_seconds, budget.max_seconds_per_solve, budget.max_observed_wall_seconds))
        return solve(builder, spec, budget, purpose)
    monkeypatch.setattr(api.native, '_solve', capture)
    result = api.run_normal_only(inputs, **args)
    assert result.normal_accepted and calls['solve'] == 1
    assert received == [(600., 600, 720.)]
    def forbidden(*a, **kw):
        raise AssertionError('replay invoked solver')
    monkeypatch.setattr(api.native, '_solve', forbidden)
    monkeypatch.setattr(api.native, 'create_solver', forbidden)
    report = audit(result, inputs, args)
    assert report['record_consistent'] and report['accepted_record_reproduced'], report
    assert report['solver_calls_by_replay'] == 0 and report['witness_reproduced']
    assert not report['formal_result'] and not report['native_execution_authenticated']
    assert not report['resource_measurements_authenticated'] and not report['public_source_binding_verified']


def test_actual_tiny_direct_call_and_independent_replay():
    inputs = fixture(2)
    args = arguments(inputs, seconds=1)
    result = api.run_normal_only(inputs, **args)
    assert result.normal_accepted, result.errors
    assert result.normal.objective == pytest.approx(40.) and result.solver_calls == 1
    report = audit(result, inputs, args)
    assert report['record_consistent'] and report['accepted_record_reproduced'], report


@pytest.mark.parametrize('fault', ['timeout', 'missing', 'unknown', 'objective', 'inverted_bounds',
    'load', 'native_infeasible', 'structure', 'exception'])
def test_native_failure_retains_unresolved_status(monkeypatch, fault):
    inputs = fixture(2)
    args = arguments(inputs)
    calls = install(monkeypatch, inputs, fault=fault)
    result = api.run_normal_only(inputs, **args)
    assert not result.normal_accepted and result.solver_calls == calls['solve'] == 1
    report = audit(result, inputs, args)
    assert not report['accepted_record_reproduced'] and report['solver_calls_by_replay'] == 0
    if fault == 'timeout':
        assert result.normal.assignment_valid and report['record_consistent'], report


@pytest.mark.parametrize('fault', ['plan', 'pin', 'hours', 'uids', 'split', 'budget_type'])
def test_original_plan_and_actual_inputs_bound_before_solver(monkeypatch, fault):
    inputs = fixture(2)
    args = arguments(inputs)
    calls = install(monkeypatch, inputs)
    plan = args['resource_plan']
    if fault == 'plan': args['resource_plan'] = replace(plan, serial_budget=replace(plan.serial_budget, controller_seconds=101))
    elif fault == 'pin': args['budget'] = replace(args['budget'], resource_contract_identity='0'*64)
    elif fault == 'budget_type': args['budget'] = old.NormalExecutionBudget(15., 1, 25, 30000, 100000, 60., 8*1024**3, 16*1024**2)
    else:
        kw = {'hours':dict(source_hours=(2,3)), 'uids':dict(generator_uids=('G2',)), 'split':dict(split='holdout')}[fault]
        norm = replace(plan.normals[0], **kw)
        ep = replace(plan.episodes[0], **kw)
        args['resource_plan'] = replace(plan, normals=(norm,), episodes=(ep,))
        args['budget'] = budgets.budget_for_task(args['resource_plan'], task_id='normal', max_observed_wall_seconds=720.,
            max_process_peak_working_set_bytes=8*1024**3, max_core_evidence_payload_bytes=16*1024**2)
    with pytest.raises(ValueError): api.run_normal_only(inputs, **args)
    assert calls == {'create':0, 'solve':0}


@pytest.mark.parametrize('changes', [dict(time_limit_seconds=599.), dict(threads=2), dict(random_seed=1),
    dict(mip_relative_gap=1e-7), dict(feasibility_tolerance=1e-8), dict(tee=True)])
def test_specification_exact_budget_and_unchanged_numerics(changes):
    inputs = fixture(2)
    args = arguments(inputs)
    with pytest.raises(ValueError):
        api.normal_execution_identity(args['expected_input_identity'], args['expected_scale'],
            replace(args['specification'], **changes), args['budget'])


@pytest.mark.parametrize('field,value', [('max_observed_wall_seconds',901.), ('max_observed_wall_seconds',599.),
    ('max_observed_wall_seconds',float('nan')), ('max_seconds_per_solve',True), ('max_horizon',3),
    ('max_core_evidence_payload_bytes',129*1024**2), ('max_process_peak_working_set_bytes',0)])
def test_allocation_rejects_unbound_or_invalid_values(field,value):
    with pytest.raises(ValueError): replace(arguments(fixture(2))['budget'], **{field:value})


def test_pre_and_post_memory_wall_checks_preserved(monkeypatch):
    inputs = fixture(2)
    args = arguments(inputs)
    calls = install(monkeypatch, inputs)
    monkeypatch.setattr(api, '_peak_working_set_bytes', lambda: 9*1024**3)
    with pytest.raises(ValueError, match='peak working set'): api.run_normal_only(inputs, **args)
    assert calls['create'] == 0
    monkeypatch.setattr(api, '_peak_working_set_bytes', lambda: 1)
    clock, solve, elapsed = api.perf_counter, api.native._solve, [0.]
    def after(builder, spec, budget, purpose):
        raw = solve(builder, spec, budget, purpose)
        elapsed[0] = 721.
        return raw
    monkeypatch.setattr(api.native, '_solve', after)
    monkeypatch.setattr(api, 'perf_counter', lambda: clock()+elapsed[0])
    result = api.run_normal_only(inputs, **args)
    assert not result.normal_accepted and 'observed_wall_time_exceeds_budget' in result.errors
    assert result.normal.assignment_valid and result.solver_calls == 1
    report = audit(result, inputs, args)
    assert report['record_consistent'] and not report['accepted_record_reproduced'], report


@pytest.mark.parametrize('field,value', [('formal_result',True), ('normal_accepted',False),
    ('solver_calls',0), ('core_evidence_payload_bytes',0), ('contract','old')])
def test_rehash_does_not_hide_record_tampering(monkeypatch,field,value):
    inputs=fixture(2)
    args=arguments(inputs)
    install(monkeypatch,inputs)
    result=api.run_normal_only(inputs,**args)
    record=json.loads(replay.export_record(result))
    for row in record['result'][1]:
        if row[0]==field: row[1]=api._encode(value)
    record['result_identity']=sha256(replay._bytes(['tuple',[record['result']]])).hexdigest()
    data=replay._bytes(record)
    try:
        report=audit(result,inputs,args,data,expected_result_identity=record['result_identity'])
    except ValueError:
        return
    assert not report['record_consistent'] and not report['accepted_record_reproduced']


def test_legacy_api_and_native_algorithm_preserved():
    args=arguments(fixture(2))
    with pytest.raises(ValueError): old_adapter.validate_spec(args['specification'])
    with pytest.raises(ValueError): old.normal_execution_identity(args['expected_input_identity'],
        args['expected_scale'],args['specification'],args['budget'])
    with pytest.raises(ValueError): old.NormalExecutionBudget(600.,1,25,30000,100000,720.,8*1024**3,16*1024**2)
    def solve_ast(module):
        tree=ast.parse(Path(module.__file__).read_text(encoding='utf-8'))
        return ast.dump(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_solve'))
    assert solve_ast(api.native)==solve_ast(old.native)


@pytest.mark.parametrize('module', [api.native.adapter, api.native, budgets, replay])
def test_transitive_source_drift_rejected_by_replay(monkeypatch,module):
    inputs=fixture(2)
    args=arguments(inputs)
    install(monkeypatch,inputs)
    result=api.run_normal_only(inputs,**args)
    pin=replay.replay_identity(args['expected_execution_identity'],args['specification'],args['budget'])
    original=Path.read_bytes
    target=Path(module.__file__).resolve()
    def changed(path):
        data=original(path)
        return data+b'\n# injected source change\n' if path.resolve()==target else data
    monkeypatch.setattr(Path,'read_bytes',changed)
    with pytest.raises(ValueError): audit(result,inputs,args,expected_replay_identity=pin)


def test_old_result_tag_rejected_even_after_rehash(monkeypatch):
    inputs=fixture(2)
    args=arguments(inputs)
    install(monkeypatch,inputs)
    result=api.run_normal_only(inputs,**args)
    record=json.loads(replay.export_record(result))
    record['result'][0]=old.GurobiOrderedNormalExecutionResult.__name__
    record['result_identity']=sha256(replay._bytes(['tuple',[record['result']]])).hexdigest()
    with pytest.raises(ValueError,match='field inventory'):
        audit(result,inputs,args,replay._bytes(record),expected_result_identity=record['result_identity'])


def test_unknown_native_call_retained_after_pipeline_interruption(monkeypatch):
    inputs=fixture(2)
    args=arguments(inputs)
    def interrupted(*a,**kw):
        raise KeyboardInterrupt('injected pipeline interruption')
    monkeypatch.setattr(api.native,'_solve',interrupted)
    result=api.run_normal_only(inputs,**args)
    assert result.status=='interrupted_normal' and result.solver_calls is None and not result.call_count_complete
    report=audit(result,inputs,args)
    assert report['record_consistent'] and not report['accepted_record_reproduced'],report


@pytest.mark.parametrize('origin', ['raw','witness'])
def test_duplicate_inherited_error_cannot_survive_rehash(monkeypatch,origin):
    inputs=fixture(2)
    args=arguments(inputs)
    if origin=='raw':
        original_assignment=old_install.__globals__['assignment_for']
        model=model_for(inputs)
        from pyomo.environ import Var
        angle=next(v.name for v in model.component_data_objects(Var) if 'angle' in v.name and not v.fixed)
        def invalid_assignment(*a,**kw):
            values=original_assignment(*a,**kw)
            values[angle]+=1.
            return values
        monkeypatch.setitem(old_install.__globals__,'assignment_for',invalid_assignment)
    install(monkeypatch,inputs)
    if origin=='witness':
        original=api.streaming.audit_normal_assignment
        def with_error(*a,**kw):
            witness=original(*a,**kw)
            from dataclasses import fields
            values={f.name:getattr(witness,f.name) for f in fields(witness)}
            values['errors']=('injected_witness_error',)
            return api.native._make(api.NormalAssignmentWitness,**values)
        monkeypatch.setattr(api.streaming,'audit_normal_assignment',with_error)
    result=api.run_normal_only(inputs,**args)
    inherited=result.normal.errors if origin=='raw' else result.witness.errors
    assert inherited and not result.normal_accepted
    baseline=audit(result,inputs,args)
    assert baseline['record_consistent'],baseline
    record=json.loads(replay.export_record(result))
    for row in record['result'][1]:
        if row[0]=='errors': row[1]=api._encode(result.errors+(inherited[0],))
    record['result_identity']=sha256(replay._bytes(['tuple',[record['result']]])).hexdigest()
    with pytest.raises(ValueError,match='error vocabulary'):
        audit(result,inputs,args,replay._bytes(record),expected_result_identity=record['result_identity'])
