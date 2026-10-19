"""Fabricated direct-adapter outputs exercise ordering, never native optimality."""
from dataclasses import replace
from importlib.metadata import version
from types import MappingProxyType
import json

import pytest
from pyomo.environ import Var, Constraint, Integers, value
from pyomo.repn import generate_standard_repn
from pyomo.opt import SolverResults, SolverStatus, SolutionStatus, TerminationCondition
from pyomo.opt.results.problem import ProblemSense

from experiments import h1_selector_raw_science_development_v1 as m
from tests import test_h1_origin_selector_replay_development_v1 as fixtures
from tests.test_h1_linear_export_guard_development_v1 import Native, Handle, Expression
from tests.test_h1_native_raw_capture_development_v1 import FakeDirect
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver


def inputs(lane):
    f,d,b,args=fixtures.inputs(lane)
    args['specification']=replace(args['specification'],name='gurobi',expected_package_version=version('gurobipy'))
    b=m.selector.initialize_development_selection(f,b.physical_carry.disclosure,lane=lane,
        selector=args['selector'],specification=args['specification'],limits=args['limits'],chronology_origin=True)
    return f,d,b,args


def install(monkeypatch,path,lane,fault=None):
    instances=[]
    class Direct(FakeDirect):
        def __init__(self):
            super().__init__(None,None,None,path/'capture',fault)
            instances.append(self)

        def _presolve(self,model,**kwargs):
            self.model=model
            vals={v.name:0. for v in model.component_data_objects(Var)}
            vals.update({'generation[G1]':30. if lane.role=='Rref' else 25.,
                         'selector_deviation[G1]':15. if lane.role=='Rref' else 20.})
            if lane.role=='Rref':vals['reference_power']=10.
            if fault=='negative':vals['generation[G1]']=-1e-12
            if fault=='signed_zero':vals['generation[G1]']=-0.
            n=Native();self.native=n;owner=object();rowowner=object()
            variables=list(model.component_data_objects(Var));rows=list(model.component_data_objects(Constraint,active=True))
            n.NumVars=len(variables);n.NumConstrs=len(rows)
            n.variables=[Handle(owner,i,VarName=v.name,VType='C',
                LB=float(value(v.value if v.fixed else v.lb)) if v.fixed or v.lb is not None else -1e100,
                UB=float(value(v.value if v.fixed else v.ub)) if v.fixed or v.ub is not None else 1e100,
                X=vals[v.name]) for i,v in enumerate(variables)]
            byname={v.name:nv for v,nv in zip(variables,n.variables)}
            def expression(expr):
                rep=generate_standard_repn(expr,compute_values=True)
                return Expression([(byname[v.name],float(c)) for v,c in zip(rep.linear_vars,rep.linear_coefs)],float(rep.constant))
            n.objective=expression(model.objective.expr);n.rows=[];n.constraints=[]
            for i,c in enumerate(rows):
                e=expression(c.body);bound=c.lower if c.has_lb() else c.upper
                n.constraints.append(Handle(rowowner,i,Sense='=' if c.equality else '>' if c.has_lb() else '<',
                    RHS=float(value(bound))-e.constant,Lazy=0))
                e.constant=0.;n.rows.append(e)
            objective=n.objective.constant+sum(c*v.X for v,c in n.objective.terms)
            n.Status=2;n.SolCount=1;n.ObjVal=n.ObjBound=n.ObjBoundC=objective;n.Runtime=.01;n.MIPGap=0.
            n.update=lambda:None
            if fault=='native_bound':n.ObjBound-=1.
            if fault=='uncorrected_bound':n.ObjBoundC-=1.
            if fault=='status':n.Status=9
            vf=tuple(zip(variables,n.variables));cf=tuple(zip(rows,n.constraints))
            self.args=dict(variable_forward=vf,variable_reverse=tuple((n,v) for v,n in vf),
                constraint_forward=cf,constraint_reverse=tuple((n,c) for c,n in cf))
            self.result=SolverResults();self.result.solver.status=SolverStatus.ok
            self.result.solver.termination_condition=TerminationCondition.optimal
            self.result.problem.sense=ProblemSense.minimize
            self.result.problem.lower_bound=self.result.problem.upper_bound=objective
            self.result.problem.number_of_objectives=1
            s=self.result.solution.add();s._cuid=False;s.status=SolutionStatus.optimal
            s.variable.update({k:{'Value':v} for k,v in vals.items()})
            if fault=='post_value':s.variable['generation[G1]']['Value']+=1.
            if fault=='count':n.SolCount=2
            if fault=='native_value':n.ObjVal+=1.
            if fault=='pyomo_status':self.result.solver.status=SolverStatus.warning
            if fault=='pyomo_termination':self.result.solver.termination_condition=TerminationCondition.maxTimeLimit
            if fault=='solution_status':s.status=SolutionStatus.feasible
            if fault=='inverted':
                self.result.problem.lower_bound=objective+1.;n.ObjBound=n.ObjBoundC=objective+1.
            if fault=='canonical_mismatch':
                self.result.problem.upper_bound=objective+1.;n.ObjVal=objective+1.
            if fault=='small_gap':
                self.result.problem.lower_bound=n.ObjBound=n.ObjBoundC=objective-1e-10
                self.result.problem.upper_bound=n.ObjVal=objective+1e-10
            super()._presolve(model,**kwargs)

        def _apply_solver(self):
            # Negative fault above targets generation, not the first angle column.
            saved=self.fault
            if saved=='negative':self.fault=None
            try:
                out=super()._apply_solver()
                if saved=='model_sense':self.native.ModelSense=-1
                return out
            finally:self.fault=saved

        def _postsolve(self):
            super()._postsolve()
            assert not (path/'postsolve.json').exists()
            assert not (path/'selector_record.json').exists()
            return self.result

        def close(self):
            assert not (path/'selector_record.json').exists()
            if fault in (None,'close','small_gap'):
                assert (path/'postsolve.json').exists()
            super().close()
    monkeypatch.setattr(m.capture,'GurobiDirect',Direct)
    monkeypatch.setattr(m.capture.old.provenance.adapter,'create_solver',
        lambda spec:(Direct(),m.selector.native.capture.solver_options(spec)))
    return instances


@pytest.mark.parametrize('lane',[fixtures.R,fixtures.A])
def test_complete_owned_stage_chain_after_close(tmp_path,monkeypatch,no_solver,lane):
    f,d,b,args=inputs(lane);records=();locks=[]
    original=m._audit_stage
    for i in range(len(m.selector.stage_labels(f,lane))):
        path=tmp_path/str(i);instances=install(monkeypatch,path,lane)
        def audit(*a,**kw):
            assert instances[0].close_calls==1
            assert (path/'capture/complete.json').exists()
            return original(*a,**kw)
        monkeypatch.setattr(m,'_audit_stage',audit)
        out=m._run_stage(path,f,d,b,records,expected_key=m.request_key(f,d,b,records,**args),**args)
        records+=(out['selector_record'],);locks.append(float.fromhex(out['lock_hex']))
        assert out['selector_chain_complete']==(i==len(m.selector.stage_labels(f,lane))-1)
        assert out['completion_scope']=='selector_replay_chain_only'
        assert not any(out[k] for k in m.FLAGS)
        assert instances[0].apply_calls==instances[0].post_calls==instances[0].close_calls==1
        terminal=json.loads((path/'terminal.json').read_bytes())
        assert terminal['selector_record_sha256']==m.io.digest(records[-1])
        assert terminal['capture_complete_sha256']==m.io.digest((path/'capture/complete.json').read_bytes())
        assert terminal['evidence_role']=='reconstructed_selector_view'
        if i==0:
            changed=json.loads(records[0]);changed['raw']['native_objectives']=[['objective',locks[0]]]
            altered=(m.selector.native._encoded(changed),)
            assert m.request_key(f,d,b,altered,**args)!=m.request_key(f,d,b,records,**args)
        with pytest.raises(FileExistsError):
            m._run_stage(path,f,d,b,records[:-1],expected_key=m.request_key(f,d,b,records[:-1],**args),**args)
        assert len(instances)==1
    assert locks==([15.,15.,30.] if lane.role=='Rref' else [20.,25.])


@pytest.mark.parametrize('fault',['close','postsolve','negative','native_bound','uncorrected_bound','status','post_value',
    'count','no_incumbent','model_sense','native_value','pyomo_status','pyomo_termination','solution_status','inverted','canonical_mismatch'])
def test_failed_stage_keeps_raw_without_record(tmp_path,monkeypatch,no_solver,fault):
    f,d,b,args=inputs(fixtures.R);path=tmp_path/'stage';instances=install(monkeypatch,path,fixtures.R,fault)
    with pytest.raises((ValueError,RuntimeError)):
        m._run_stage(path,f,d,b,(),expected_key=m.request_key(f,d,b,(),**args),**args)
    assert (path/'capture/native_raw/000/raw.bin').exists()
    assert not (path/'selector_record.json').exists() and not (path/'terminal.json').exists()
    assert instances[0].apply_calls==instances[0].close_calls==1
    if fault not in ('postsolve','no_incumbent','model_sense'):assert (path/'postsolve.json').exists()
    if fault=='negative':
        raw=json.loads((path/'capture/native_raw/000/raw.bin').read_bytes())
        row=next(r for r in raw['variables'] if r['canonical_name']=='generation[G1]')
        assert row['attributes']['X']['atom']['value']==(-1e-12).hex()


def test_wrong_request_and_highs_stop_before_allocation(tmp_path,monkeypatch,no_solver):
    f,d,b,args=inputs(fixtures.R)
    with pytest.raises(ValueError,match='request'):
        m._run_stage(tmp_path/'wrong',f,d,b,(),expected_key='0'*64,**args)
    f,d,b,args=fixtures.inputs()
    with pytest.raises(ValueError,match='Gurobi'):
        m._run_stage(tmp_path/'highs',f,d,b,(),expected_key=m.request_key(f,d,b,(),**args),**args)
    assert not list(tmp_path.iterdir())


def test_actual_negative_and_canonical_lock_not_native_value(tmp_path,monkeypatch,no_solver):
    for fault in ('negative','small_gap'):
        f,d,b,args=inputs(fixtures.A);path=tmp_path/fault;install(monkeypatch,path,fixtures.A,fault)
        key=m.request_key(f,d,b,(),**args)
        if fault=='negative':
            with pytest.raises(ValueError,match='negative selector generation'):
                m._run_stage(path,f,d,b,(),expected_key=key,**args)
        else:
            out=m._run_stage(path,f,d,b,(),expected_key=key,**args)
            assert float.fromhex(out['lock_hex'])==20.
            raw=json.loads((path/'capture/native_raw/000/raw.bin').read_bytes())
            assert raw['attributes']['ObjVal']['atom']['value']!=out['lock_hex']


def test_signed_zero_reaches_physical_audit_without_negative_rejection(tmp_path,monkeypatch,no_solver):
    f,d,b,args=inputs(fixtures.R);path=tmp_path/'stage';install(monkeypatch,path,fixtures.R,'signed_zero')
    with pytest.raises(ValueError,match='physical/gap/lock replay rejected'):
        m._run_stage(path,f,d,b,(),expected_key=m.request_key(f,d,b,(),**args),**args)
    raw=json.loads((path/'capture/native_raw/000/raw.bin').read_bytes())
    row=next(r for r in raw['variables'] if r['canonical_name']=='generation[G1]')
    assert row['attributes']['X']['atom']['value']==(-0.).hex()


@pytest.mark.parametrize('fault',['integer','scale'])
def test_model_admission_before_capture(tmp_path,monkeypatch,no_solver,fault):
    f,d,b,args=inputs(fixtures.R)
    if fault=='integer':
        original=m.selector.build_development_stage
        def build(*a,**kw):
            model=original(*a,**kw);model.generation['G1'].domain=Integers;return model
        monkeypatch.setattr(m.selector,'build_development_stage',build)
    else:
        args['limits']=replace(args['limits'],max_variables=1)
        b=m.selector.initialize_development_selection(f,b.physical_carry.disclosure,lane=fixtures.R,
            selector=args['selector'],specification=args['specification'],limits=args['limits'],chronology_origin=True)
    with pytest.raises(ValueError,match='continuous|replay limits'):
        m._run_stage(tmp_path/'stage',f,d,b,(),expected_key=m.request_key(f,d,b,(),**args),**args)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('target',['capture','capture/native_raw','capture/native_raw/000',
    'postsolve.json','observations.json','selector_record.json','terminal.json'])
def test_unknown_suffix_rejected_at_persistence_boundaries(tmp_path,monkeypatch,no_solver,target):
    f,d,b,args=inputs(fixtures.R);path=tmp_path/'stage';install(monkeypatch,path,fixtures.R)
    original=m.io.write_new
    def write(p,data):
        result=original(p,data)
        trigger='observations.json' if target.startswith('capture') else target
        if p==path/trigger:
            directory=path/target if target.startswith('capture') else path
            (directory/'unknown_suffix').write_bytes(b'preserve failure')
        return result
    monkeypatch.setattr(m.io,'write_new',write)
    with pytest.raises(ValueError,match='namespace'):
        m._run_stage(path,f,d,b,(),expected_key=m.request_key(f,d,b,(),**args),**args)
    assert (path/'capture/native_raw/000/raw.bin').exists()
    assert not (path/'terminal.json').exists() or target=='terminal.json'


@pytest.mark.parametrize('output,after',[('observations.json',False),('observations.json',True),
    ('selector_record.json',False),('selector_record.json',True),('terminal.json',False),('terminal.json',True)])
def test_write_failure_is_retained_and_never_retried(tmp_path,monkeypatch,no_solver,output,after):
    f,d,b,args=inputs(fixtures.R);path=tmp_path/'stage';instances=install(monkeypatch,path,fixtures.R)
    original=m.io.write_new
    def write(p,data):
        if p==path/output and not after:raise OSError('injected write before')
        result=original(p,data)
        if p==path/output and after:raise OSError('injected write after')
        return result
    monkeypatch.setattr(m.io,'write_new',write)
    key=m.request_key(f,d,b,(),**args)
    with pytest.raises(OSError,match='injected'):
        m._run_stage(path,f,d,b,(),expected_key=key,**args)
    assert (path/'capture/complete.json').exists()
    assert (path/'postsolve.json').exists()
    assert (path/output).exists()==after
    with pytest.raises(FileExistsError):m._run_stage(path,f,d,b,(),expected_key=key,**args)
    assert instances[0].apply_calls==1 and len(instances)==1


@pytest.mark.parametrize('output',['observations.json','selector_record.json','terminal.json'])
def test_retained_postsolve_mutation_fails_fresh_return(tmp_path,monkeypatch,no_solver,output):
    f,d,b,args=inputs(fixtures.R);path=tmp_path/'stage';install(monkeypatch,path,fixtures.R)
    original=m.io.write_new
    def write(p,data):
        result=original(p,data)
        if p==path/output:(path/'postsolve.json').write_bytes(b'changed')
        return result
    monkeypatch.setattr(m.io,'write_new',write)
    with pytest.raises(ValueError,match='retained view'):
        m._run_stage(path,f,d,b,(),expected_key=m.request_key(f,d,b,(),**args),**args)
    assert (path/'capture/native_raw/000/raw.bin').exists()


@pytest.mark.parametrize('fault',['mutation','rebind','schema'])
def test_callback_cannot_promote_scope(tmp_path,monkeypatch,no_solver,fault):
    f,d,b,args=inputs(fixtures.R);path=tmp_path/'stage';install(monkeypatch,path,fixtures.R)
    original=m.io.write_new
    def write(p,data):
        result=original(p,data)
        if p==path/'postsolve.json':
            if fault=='mutation':m.FLAGS['formal_result']=True
            elif fault=='rebind':monkeypatch.setattr(m,'FLAGS',MappingProxyType(dict(m.FLAGS,native_execution_authorized=True)))
            else:monkeypatch.setattr(m,'SCHEMA','changed')
        return result
    monkeypatch.setattr(m.io,'write_new',write)
    key=m.request_key(f,d,b,(),**args)
    with pytest.raises((ValueError,TypeError),match='scope|item assignment'):
        m._run_stage(path,f,d,b,(),expected_key=key,**args)
    assert (path/'capture/native_raw/000/raw.bin').exists()
    assert (path/'postsolve.json').exists()
    assert not (path/'selector_record.json').exists() and not (path/'terminal.json').exists()


@pytest.mark.parametrize('fault',['mutable','missing','extra','true'])
def test_scope_rebinding_rejected_before_allocation(tmp_path,monkeypatch,no_solver,fault):
    f,d,b,args=inputs(fixtures.R);key=m.request_key(f,d,b,(),**args);flags=dict(m.FLAGS)
    if fault=='missing':flags.pop('formal_result')
    if fault=='extra':flags['foreign']=False
    if fault=='true':flags['formal_execution_ready']=True
    monkeypatch.setattr(m,'FLAGS',flags if fault=='mutable' else MappingProxyType(flags))
    with pytest.raises(ValueError,match='scope'):
        m._run_stage(tmp_path/'stage',f,d,b,(),expected_key=key,**args)
    assert not list(tmp_path.iterdir())
