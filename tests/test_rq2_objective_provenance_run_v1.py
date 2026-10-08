import json
import os
import sys
import inspect
from pathlib import Path
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import pytest
from pyomo.environ import ConcreteModel, Var, Objective, Constraint, Binary

from src.solvers import rq2_objective_provenance_run_v1 as api
from src.solvers.rq2_solver_adapter import Rq2SolverSpec
from experiments import audit_rq2_h25_native_provenance_v1 as entry


def builder():
    model = ConcreteModel()
    model.x = Var(domain=Binary)
    model.minimum = Constraint(expr=model.x >= 1)
    model.cost = Objective(expr=2 * model.x)
    return model


def arguments():
    return dict(expected_structure=api.audit._structure(builder()), max_variables=1,
        max_constraints=1, max_payload_bytes=100000,
        expected_implementation=api.implementation_identity())


def spec():
    return Rq2SolverSpec('gurobi', '13.0.2', 1, 1e-8, 1e-9, 1e-9, 1e-9, 0, 1., False)


def test_owned_single_solve_records_canonical_and_direct_channels():
    report = json.loads(api.solve_once(builder, spec(), **arguments()))
    assert report['solver_calls'] == 1 and report['assignment_valid']
    assert report['maximum_residual'] == report['maximum_integrality_violation'] == 0
    assert report['assignment'] == [['x', 1.0.hex()]]
    assert report['provenance']['native_algebra_equals_canonical_algebra']
    assert report['provenance']['optimal_status_channels_consistent']
    assert not report['normal_accepted'] and not report['optimality_certified']


@pytest.mark.parametrize('field,bad', [('expected_structure', '0'*64), ('max_variables', 0),
    ('max_constraints', 0), ('max_payload_bytes', 0), ('expected_implementation', '0'*64)])
def test_bad_declaration_rejected_before_native(monkeypatch, field, bad):
    kw = arguments()
    kw[field] = bad
    def forbidden(*args):
        raise AssertionError('pre-admission must not call native')
    monkeypatch.setattr(api.provenance.adapter, 'create_solver', forbidden)
    with pytest.raises(ValueError):
        api.solve_once(builder, spec(), **kw)


def test_payload_limit_is_enforced_after_one_call(monkeypatch):
    kw = dict(arguments(), max_payload_bytes=1)
    factory = api.provenance.adapter.create_solver
    calls = []
    def capture(*args):
        calls.append(1)
        return factory(*args)
    monkeypatch.setattr(api.provenance.adapter, 'create_solver', capture)
    with pytest.raises(ValueError, match='payload'):
        api.solve_once(builder, spec(), **kw)
    assert len(calls) == 1


def test_model_drift_in_fresh_rebuild_rejected():
    calls = []
    def drifting():
        model = builder()
        calls.append(1)
        if len(calls) == 2:
            model.cost.set_value(3 * model.x)
        return model
    with pytest.raises(ValueError, match='fresh canonical'):
        api.solve_once(drifting, spec(), **arguments())


def test_exclusive_publication_preserves_existing_bytes(tmp_path):
    target = tmp_path/'report.json'
    entry.write_new(target, {'first': True})
    before = target.read_bytes()
    with pytest.raises(FileExistsError):
        entry.write_new(target, {'first': False})
    assert target.read_bytes() == before


def test_existing_attempt_rejected_before_process(monkeypatch, tmp_path):
    monkeypatch.setattr(entry, 'OUTPUT', tmp_path)
    monkeypatch.setattr(entry, 'check', lambda *args: (None, '1'*64))
    def forbidden(*args, **kwargs):
        raise AssertionError('no spawn for existing attempt')
    monkeypatch.setattr(entry.process, 'normal_task_child', forbidden)
    with pytest.raises(FileExistsError):
        entry.execute('2'*64, '3'*64)


def test_worker_binds_source_and_writes_owned_numeric_report(monkeypatch, tmp_path):
    request = SimpleNamespace(specification=spec(), source=SimpleNamespace(expected_input_identity='4'*64))
    monkeypatch.setattr(entry, 'OUTPUT', tmp_path)
    monkeypatch.setattr(entry, 'STRUCTURE', api.audit._structure(builder()))
    monkeypatch.setattr(entry, 'check', lambda *args: (request, '1'*64))
    monkeypatch.setattr(entry.transport.source, '_prepare', lambda *args: (None, None))
    monkeypatch.setattr(entry.transport.source.kernel.streaming, 'build_continuous_normal_model', lambda *args, **kw: builder())
    (tmp_path/'scratch').mkdir()
    entry.write_new(tmp_path/'intent.json', dict(script_sha256='2'*64,
        runner_identity=api.implementation_identity(), request_identity='1'*64))
    entry.write_new(tmp_path/'launch.json', dict(pid=os.getpid()))
    entry.worker('2'*64, api.implementation_identity(), '1'*64)
    report = json.loads((tmp_path/'native_record.json').read_bytes())
    assert report['source_request_identity'] == '1'*64
    assert report['numerical']['assignment_valid']
    assert report['numerical']['provenance']['native_algebra_equals_canonical_algebra']
    assert not report['normal_accepted']


def wrap(numerical):
    return dict(schema='rq2_h25_native_provenance_diagnostic_v1', source_request_sha256=entry.PACKET_PIN,
        source_request_identity='1'*64, source_input_identity='4'*64, script_sha256='2'*64,
        runner_identity=api.implementation_identity(), numerical=numerical,
        formal_result=False, normal_accepted=False)


def tiny_request():
    return SimpleNamespace(specification=spec(), source=SimpleNamespace(
        expected_input_identity='4'*64, expected_scale=api.audit.model_scale(builder())))


@pytest.fixture
def tiny_report(monkeypatch):
    monkeypatch.setattr(entry, 'STRUCTURE', arguments()['expected_structure'])
    return wrap(json.loads(api.solve_once(builder, spec(), **arguments())))


@pytest.mark.parametrize('path,bad', [
    (('source_request_sha256',), '0'*64), (('source_input_identity',), '0'*64),
    (('numerical','solver_calls'), 2), (('numerical','variables'), 2),
    (('numerical','model_structure_identity'), '0'*64),
    (('numerical','normal_accepted'), True),
    (('numerical','provenance','native_execution_authenticated'), True),
    (('numerical','provenance','solver_calls_by_collector'), 1),
    (('numerical','provenance','collector_sha256'), '0'*64),
    (('numerical','provenance','native','ObjVal','available'), False),
])
def test_parent_rejects_self_consistent_nested_tamper(tiny_report, path, bad):
    report = deepcopy(tiny_report)
    target = report
    for name in path[:-1]:
        target = target[name]
    target[path[-1]] = bad
    report = json.loads(api.encode(report))  # New bytes/hash cannot repair the semantic conflict.
    with pytest.raises(ValueError):
        entry.validate_record(report, tiny_request(), '1'*64, '2'*64, api.implementation_identity())


@pytest.mark.parametrize('fault', [None, 'record_replace', 'intent_tamper'])
def test_real_tiny_subprocess_and_retained_crosslinks(tmp_path, monkeypatch, fault):
    monkeypatch.setattr(entry, 'STRUCTURE', arguments()['expected_structure'])
    scratch = tmp_path/'scratch'
    scratch.mkdir()
    root = Path(__file__).resolve().parents[1]
    code = f'''import sys,json,os
from pathlib import Path
sys.stderr=open({str(tmp_path/'child_error.txt')!r},'w')
sys.path.insert(0,{str(root)!r})
from pyomo.environ import ConcreteModel, Var, Objective, Constraint, Binary
from src.solvers.rq2_solver_adapter import Rq2SolverSpec
from src.solvers import rq2_objective_provenance_run_v1 as api
from experiments import audit_rq2_h25_native_provenance_v1 as entry
{inspect.getsource(builder)}
{inspect.getsource(spec)}
{inspect.getsource(arguments)}
{inspect.getsource(wrap)}
root=Path({str(tmp_path)!r})
assert json.loads((root/'launch.json').read_bytes())['pid']==os.getpid()
report=wrap(json.loads(api.solve_once(builder,spec(),**arguments())))
entry.write_new(root/'native_record.json',report)
'''
    budget = entry.process.TaskProcessBudget(30., .1, 512*1024**2, 512*1024**2, 3.)
    host = entry.process.resources.HostResourceBudget(640*1024**2, 16*1024**2,
        (entry.process.resources.DirectoryDemand('scratch',str(scratch), 16*1024**2, 16*1024**2),))
    environment = dict(os.environ, TEMP=str(scratch), TMP=str(scratch), OMP_NUM_THREADS='1',
                       OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    args = dict(cwd=scratch, environment=environment,budget=budget,host_budget=host,
        expected_host_identity=entry.process.resources.resource_identity(host))
    intent = dict(request_identity='1'*64,script_sha256='2'*64,runner_identity=api.implementation_identity())
    def validate(report):
        entry.validate_record(report,tiny_request(),'1'*64,'2'*64,api.implementation_identity())
    def after():
        if fault == 'record_replace':
            path=tmp_path/'native_record.json'
            raw=path.read_bytes()
            path.rename(tmp_path/'retained_original.json')
            path.write_bytes(raw)
        elif fault == 'intent_tamper':
            (tmp_path/'intent.json').write_text('{}')
    argv=[sys.executable,'-I','-B','-c',code]
    if fault:
        with pytest.raises(ValueError, match='retained evidence'):
            entry.supervise(tmp_path,argv,args,intent,validate,after)
        assert not (tmp_path/'result.json').exists()
    else:
        result=entry.supervise(tmp_path,argv,args,intent,validate,after)
        assert result['solver_calls']==1 and result['assignment_valid']
        assert result['observation']['whole_job_quiescent']
        assert set(result['file_sha256'])=={'intent.json','launch.json','observation.json','native_record.json'}
        for name,pin in result['file_sha256'].items():
            assert entry.retained(tmp_path/name)[1]==pin
        assert not result['independent_numerical_replay_completed']
        observed = entry.process.TaskProcessObservation(**result['observation'])
        launch = json.loads((tmp_path/'launch.json').read_bytes())
        for changes in [dict(last_resource_errors=('error',)), dict(stop_markers=()),
                dict(pid=observed.pid+1), dict(creation_filetime=observed.creation_filetime+1),
                dict(job_peak_total_commit_bytes=budget.max_job_commit_bytes+1),
                dict(formal_result=True), dict(observation_error_type='error')]:
            with pytest.raises(ValueError):
                entry.validate_observation(replace(observed, **changes), args, launch, result['process_identity'])
