from pathlib import Path
from dataclasses import replace
import pytest
from pyomo.environ import ConcreteModel,Var,Constraint,ConstraintList,Objective,Binary,Integers,Reals,Any,SolverFactory

from src.rq2_joint_deliverability_boundary_v1 import normal_h1_resource_shape as api
from tests.test_rq2_normal_h1_source_v1 import packet
from tests.test_rq2_normal_h1_source_binding_v1 import supplied


def test_algebraic_shape_independent_small_oracle():
    m=ConcreteModel()
    m.b=Var(domain=Binary)
    m.i=Var(domain=Integers)
    m.x=Var(domain=Reals)
    m.row=Constraint(expr=(1,m.x+2*m.i+3*m.b,7))
    m.h1_prior_objective_locks=ConstraintList()
    m.h1_prior_objective_locks.add(m.b==0)
    m.objective=Objective(expr=m.x+m.b)
    shape=api.algebraic_shape(m)
    assert shape['active_var_data']==3
    assert shape['variable_classes']==dict(binary=1,general_integer=1,continuous=1)
    assert shape['active_constraint_data']==2 and shape['ranged_constraint_data']==1
    assert shape['linear_constraint_terms']==4
    assert shape['lock_linear_terms']==1 and shape['objective_linear_terms']==2
    assert not shape['native_matrix_measured'] and not shape['feasibility_checked']
    m.x.fix(2.)
    fixed=api.algebraic_shape(m)
    assert fixed['fixed_var_data']==1 and fixed['linear_constraint_terms']==3


@pytest.mark.parametrize('change',['nonlinear','unknown_domain','second_objective'])
def test_unsupported_shape_rejects(change):
    m=ConcreteModel()
    m.x=Var(domain=Any if change=='unknown_domain' else Reals)
    m.row=Constraint(expr=m.x**2<=2) if change=='nonlinear' else Constraint(expr=m.x<=2)
    m.objective=Objective(expr=m.x)
    if change=='second_objective': m.other=Objective(expr=-m.x)
    with pytest.raises(ValueError): api.algebraic_shape(m)


@pytest.mark.parametrize('entry',['factory','current','chain','capture','adapter'])
def test_zero_solver_guard_fails_even_if_caller_suppresses_error(entry):
    with pytest.raises(RuntimeError,match='attempted'):
        with api.solver_calls_forbidden():
            call={'factory':lambda:SolverFactory('glpk'),'current':api.current.solve_current,
                'chain':api.current.native.run_h1_chain,'capture':api.current.native.capture.solve_once,
                'adapter':api.current.native.capture.provenance.adapter.create_solver}[entry]
            try: call()
            except RuntimeError: pass


def test_h1_endpoint_shapes_do_not_produce_locks_or_certificate():
    report=api.inspect_shapes(packet())
    assert report['stage_count']==3
    first,last=report['measured_stage_shapes']
    assert first['stage_index']==0 and last['stage_index']==2
    assert last['placeholder_lock_count']==2 and last['placeholder_locks']
    assert last['shape']['active_constraint_data']==first['shape']['active_constraint_data']+2
    assert last['lock_provenance_verified'] is False
    assert report['solver_calls']==0 and report['causal_key'] is None and report['accepted_normal_carry'] is None
    assert all(x is None for x in report['unmeasured'].values())
    assert not report['formal_result'] and not report['formal_execution_ready'] and not report['numerical_certificate']


def test_real_network_counterfactual_content_arithmetic():
    result=api.unadmitted_content_envelope(232,192)
    assert result['stage_slots']==44544
    assert result['single_event_bytes']==3892576270
    assert result['journal_content_bytes']==753917760768
    assert not result['within_existing_short_call_domain'] and not result['within_existing_short_hour_domain']
    assert not result['instantiated'] and not result['physical_space_reserved'] and not result['run_authorized']


@pytest.mark.parametrize('stages,hours',[(True,192),(232,True),(0,192),(232,193)])
def test_counterfactual_invalid_dimensions_reject(stages,hours):
    with pytest.raises(ValueError): api.unadmitted_content_envelope(stages,hours)


def test_pinned_source_shape_and_independent_pin(supplied,monkeypatch):
    root,config,d,_=supplied
    receipt=api.binding.load_pinned_current(d,root,config_path=config)
    report=api.pinned_shape_probe(d,root,config_path=config,expected_source_identity=receipt.identity,dc_bus=1)
    assert report['source_binding_identity']==receipt.identity and report['solver_calls']==0
    monkeypatch.setattr(api,'inspect_shapes',lambda *a:pytest.fail('wrong pin reached model shape'))
    with pytest.raises(ValueError,match='source pin'):
        api.pinned_shape_probe(d,root,config_path=config,expected_source_identity='0'*64,dc_bus=1)


def test_probe_rechecks_source_after_model_builds(supplied,monkeypatch):
    root,config,d,state=supplied
    receipt=api.binding.load_pinned_current(d,root,config_path=config)
    original=api.inspect_shapes
    def drift(*a):
        result=original(*a)
        state['workload']='0.3'
        return result
    monkeypatch.setattr(api,'inspect_shapes',drift)
    with pytest.raises(ValueError,match='current sources'):
        api.pinned_shape_probe(d,root,config_path=config,expected_source_identity=receipt.identity,dc_bus=1)


from copy import deepcopy
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_shape_process as controller


def complete_receipt():
    report=api.inspect_shapes(packet())
    report.update(source_binding_identity='1'*64,source_binding_audit_sha256='2'*64,
        source_declaration={'test':'synthetic'},dc_bus=1,source_load_and_assembly_seconds=0.1,
        source_revalidation_seconds=0.1,source_authenticated=False,selection_registered=False,
        request_sha256='3'*64,worker_sha256='4'*64,process_peak_working_set_bytes=1024,
        worker_elapsed_seconds=1.,peak_working_set_scope='process_lifetime_not_single_model',hard_rss_limit_enforced=False)
    request=dict(expected_source_identity=report['source_binding_identity'],
        shape_implementation_identity=report['implementation_identity'],worker_sha256=report['worker_sha256'],
        declaration=report['source_declaration'],dc_bus=1,expected_stage_count=report['stage_count'],
        expected_network_identity=report['network_identity'])
    return report,request


def test_complete_receipt_validation():
    report,request=complete_receipt()
    controller.validate_result(report,request)


@pytest.mark.parametrize('mutation',[
    lambda r:r.update(extra=None),lambda r:r.update(solver_calls=False),
    lambda r:r.update(worker_elapsed_seconds=float('nan')),
    lambda r:r.update(source_revalidation_seconds=-1),lambda r:r.update(unmeasured={}),
    lambda r:r['formal_resource_contract'].update(threads=1),
    lambda r:r['sharing'].update(observed_hit_count=1),
    lambda r:r['runtime_versions'].update(pyomo_version='forged'),
    lambda r:r['measured_stage_shapes'][-1]['shape'].update(lock_constraint_data=0),
    lambda r:r['measured_stage_shapes'][0]['shape'].update(native_matrix_measured=True),
    lambda r:r['measured_stage_shapes'][0].update(model_construction_seconds=True),
    lambda r:r['measured_stage_shapes'][0]['shape']['variable_classes'].update(binary=999),
    lambda r:r['counterfactual_unadmitted_content_envelope'].update(single_event_bytes=1),
    lambda r:r.update(counterfactual_single_event_fits_observed_sqlite_length_limit=0),
])
def test_parent_rejects_self_consistent_bad_receipts(mutation):
    report,request=complete_receipt()
    mutation(report)
    with pytest.raises(ValueError):controller.validate_result(report,request)


from experiments import probe_rq2_normal_h1_shape_v1 as worker
from hashlib import sha256
import json


@pytest.mark.parametrize('fault',['good','request_pin','producer_pin','extra','existing_output','oversize'])
def test_worker_exclusive_bounded_receipt(tmp_path,monkeypatch,fault):
    scratch=tmp_path/'worker_non_authoritative'
    scratch.mkdir()
    monkeypatch.chdir(scratch)
    output=scratch/'result.json'
    request=dict(schema='h1_zero_solver_shape_probe_request_v1',
        declaration=dict(split='training',power_raw_hour=0,workload_raw_hour=0,outage_seed=1,config_sha256='1'*64),
        upstream_root=str(tmp_path),config_path=str(tmp_path/'config'),expected_source_identity='2'*64,
        expected_network_identity='3'*64,expected_stage_count=3,dc_bus=1,output_file=str(output),
        shape_implementation_identity=api.implementation_identity(),worker_sha256=sha256(Path(worker.__file__).read_bytes()).hexdigest())
    if fault=='producer_pin':request['worker_sha256']='0'*64
    if fault=='extra':request['extra']=None
    if fault=='existing_output':output.write_bytes(b'preserve')
    payload=api.binding._bytes(request)
    path=scratch/'request.json'
    path.write_bytes(payload)
    monkeypatch.setattr(api,'pinned_shape_probe',lambda *a,**k:{'test_payload':'x'*(worker.MAX_RESULT_BYTES if fault=='oversize' else 1)})
    pin='0'*64 if fault=='request_pin' else sha256(payload).hexdigest()
    if fault=='good':
        assert worker.execute(path,pin)==sha256(output.read_bytes()).hexdigest()
    else:
        with pytest.raises(ValueError):worker.execute(path,pin)
        assert output.read_bytes()==b'preserve' if fault=='existing_output' else not output.exists()


def test_controller_refuses_budget_before_directory_creation(tmp_path):
    budget=controller.process.TaskProcessBudget(61.,0.1,1024**3,1024**3,2.)
    root=tmp_path/'refused_non_authoritative'
    with pytest.raises(ValueError,match='short process ceiling'):
        controller.run_shape_job(root,None,tmp_path,config_path=tmp_path,expected_source_identity='0'*64,
            dc_bus=1,expected_network_identity='0'*64,expected_stage_count=232,task_budget=budget,
            commit_reserve_bytes=1,disk_demand_bytes=1,disk_reserve_bytes=1)
    assert not root.exists()


from contextlib import contextmanager
from types import SimpleNamespace


@pytest.mark.parametrize('fault',['timeout','not_quiet','no_output','bad_output','oversize'])
def test_controller_failure_never_publishes_checks(tmp_path,monkeypatch,fault):
    root=tmp_path/'job_non_authoritative'
    config=tmp_path/'config.json'
    config.write_text('{}')
    d=api.binding.H1SourceDeclaration('training',0,0,1,'1'*64)
    obs=controller.process.TaskProcessObservation('2'*64,1,1,0,
        'wall_timeout' if fault=='timeout' else 'child_exited',1.,1,1024,(),(),None,(),1024,1024,fault!='not_quiet')
    @contextmanager
    def child(*a,**k):
        def release():
            output=root/'scratch_non_authoritative/shape_result.json'
            if fault=='bad_output':output.write_bytes(b'{}')
            if fault=='oversize':output.write_bytes(b'x'*(controller.MAX_RESULT_BYTES+1))
        yield SimpleNamespace(pid=1,creation_filetime=1,initial_observation=d,release=release,wait=lambda:obs)
    monkeypatch.setattr(controller.process,'normal_task_child',child)
    monkeypatch.setattr(controller.process,'task_process_identity',lambda *a,**k:'2'*64)
    monkeypatch.setattr(controller.process.resources,'resource_identity',lambda *a,**k:'3'*64)
    with pytest.raises((ValueError,FileNotFoundError)):
        controller.run_shape_job(root,d,tmp_path,config_path=config,expected_source_identity='0'*64,
            dc_bus=1,expected_network_identity='0'*64,expected_stage_count=232,
            task_budget=controller.process.TaskProcessBudget(60.,.1,1024**3,1024**3,2.),
            commit_reserve_bytes=1,disk_demand_bytes=1,disk_reserve_bytes=1)
    assert (root/'intent.json').exists() and (root/'process_observation.json').exists()
    assert not (root/'shape_job_checks.json').exists()
