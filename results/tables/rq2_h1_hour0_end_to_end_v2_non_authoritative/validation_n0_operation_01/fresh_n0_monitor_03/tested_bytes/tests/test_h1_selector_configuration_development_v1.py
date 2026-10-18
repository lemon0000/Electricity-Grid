"""Pure declaration checks; no source load, Job or native solver."""
from dataclasses import replace

import pytest

from experiments import h1_selector_configuration_development_v1 as m
from tests.test_h1_selector_replay_development_v1 import REF, ACT


@pytest.fixture(autouse=True)
def no_execution(monkeypatch):
    def denied(*a, **k):
        raise AssertionError('configuration validation reached execution')
    monkeypatch.setattr(m.inspector.bridge.capture.old.provenance.adapter, 'create_solver', denied)
    monkeypatch.setattr(m.inspector.bridge, '_run_stage', denied)
    monkeypatch.setattr(m.inspector.bridge.capture, 'StageCapture', denied)
    monkeypatch.setattr(m.process, 'normal_task_child', denied)


def configuration(uids=('G1',), network='a'*64):
    count = len(uids) + 2
    return m.SelectorRunConfiguration(network, uids, REF, ACT,
        m.selection.native.capture.Rq2SolverSpec('gurobi', '13.0.2', 1, 1e-8, 1e-9, 1e-9, 1e-9, 0, 1., False),
        m.selection.ReplayLimits(count, 1000, 2000, 65536, count*65536, 1, 1, count, count),
        m.process.TaskProcessBudget(count+2, .05, 512*1024**2, 768*1024**2, 2),
        m.process.TaskProcessBudget(count+1, .05, 512*1024**2, 768*1024**2, 2), 2, 2)


@pytest.mark.parametrize('uids', [('G1',), ('G1','G2','G3')])
def test_full_stage_inventory_and_n_correspondence(uids):
    c = configuration(uids)
    assert c.stage_orders == dict(reference=('grid_request','l1_normal_deviation',
        *('generation:'+u for u in uids)), actual=('l1_normal_deviation',*('generation:'+u for u in uids)))
    c.validate_normal(c.network_sha256, (('operating_cost',None),('commitment',uids[0]),
        *(('generation',u) for u in uids)))
    b = c.binding()
    assert b['configuration_declared'] is True
    assert all(v is False for k,v in b.items() if k not in (
        'schema','configuration','stage_orders','implementation','configuration_declared'))


@pytest.mark.parametrize('uids', [(), ['G1'], ('G2','G1'), ('G1','G1'), ('',), (True,), ('G1',None)])
def test_invalid_uid_inventory(uids):
    with pytest.raises(ValueError,match='UID'): configuration(uids)


@pytest.mark.parametrize('change', ['network','missing','extra','order'])
def test_normal_inventory_requires_exact_sequence(change):
    c=configuration(('G1','G2'))
    network=c.network_sha256;uids=c.generation_uids
    if change=='network':network='b'*64
    elif change=='missing':uids=uids[:1]
    elif change=='extra':uids=(*uids,'G3')
    else:uids=tuple(reversed(uids))
    with pytest.raises(ValueError,match='declarations differ'):
        c.validate_normal(network,tuple(('generation',u) for u in uids))


@pytest.mark.parametrize('field,value', [('max_stages',2),('max_solver_calls',2),
    ('max_total_solver_seconds',2),('max_total_bytes',3*65536-1)])
def test_complete_reference_chain_must_fit(field,value):
    c=configuration()
    with pytest.raises(ValueError):replace(c,limits=replace(c.limits,**{field:value}))


@pytest.mark.parametrize('role', ['reference','actual'])
def test_independent_job_budget_exact_boundary(role):
    c=configuration();field=role+'_job_budget';budget=getattr(c,field)
    replace(c,**{field:replace(budget,max_elapsed_seconds=budget.max_elapsed_seconds)})
    with pytest.raises(ValueError,match='time declaration'):
        replace(c,**{field:replace(budget,max_elapsed_seconds=budget.max_elapsed_seconds-.0001)})
    with pytest.raises(ValueError,match='exact selector Job'):
        replace(c,**{field:vars(budget)})


@pytest.mark.parametrize('role', ['reference','actual'])
@pytest.mark.parametrize('value', [0, -1, True, '2', float('nan'), float('inf')])
def test_invalid_non_solver_allowance(role,value):
    with pytest.raises(ValueError,match='non-solver'):replace(configuration(),**{role+'_non_solver_seconds':value})


@pytest.mark.parametrize('field,value', [('name','highs'),('threads',2),
    ('feasibility_tolerance',1e-5),('optimality_tolerance',1e-5),
    ('time_limit_seconds',None),('time_limit_seconds',2.),('time_limit_seconds',True),
    ('expected_package_version','13.0.1'),('random_seed',1),('mip_relative_gap',1e-7),('tee',True)])
def test_solver_contract_remains_strict(field,value):
    c=configuration()
    with pytest.raises((ValueError,TypeError)):
        replace(c,specification=replace(c.specification,**{field:value}))


@pytest.mark.parametrize('role', ['reference','actual'])
def test_chain_job_declaration_uses_process_ceiling(role):
    c=configuration();name=role+'_job_budget';budget=getattr(c,name)
    replace(c,**{name:replace(budget,max_elapsed_seconds=3600.)})
    with pytest.raises(ValueError,match='development ceiling'):
        replace(c,**{name:replace(budget,max_elapsed_seconds=3600.0001)})


@pytest.mark.parametrize('role', ['reference','actual'])
def test_selector_gap_lock_contract_preserved(role):
    c=configuration();name=role+'_selector'
    with pytest.raises(ValueError):replace(c,**{name:replace(getattr(c,name),absolute_gap_mw=1e-4)})
    with pytest.raises(ValueError):replace(c,**{name:replace(getattr(c,name),lock_tolerance_mw=1e-4)})


def test_revalidation_detects_mutated_nested_dataclass():
    c=configuration();object.__setattr__(c.limits,'max_solver_calls',1)
    with pytest.raises(ValueError):c.binding()


def test_fractional_declared_time_comparison():
    c=configuration()
    c=replace(c,specification=replace(c.specification,time_limit_seconds=.1),
        reference_non_solver_seconds=.1,actual_non_solver_seconds=.1,
        reference_job_budget=replace(c.reference_job_budget,max_elapsed_seconds=.4),
        actual_job_budget=replace(c.actual_job_budget,max_elapsed_seconds=.3))
    c.__post_init__()
    with pytest.raises(ValueError,match='time declaration'):
        replace(c,actual_job_budget=replace(c.actual_job_budget,max_elapsed_seconds=.29999999999999993))
