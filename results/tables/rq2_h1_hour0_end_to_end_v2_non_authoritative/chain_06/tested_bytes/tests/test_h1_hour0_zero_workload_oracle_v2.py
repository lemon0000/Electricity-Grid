"""Zero-workload selector oracle: real model/replay, fabricated solve results."""
from hashlib import sha256
import json

import pytest
from pyomo.environ import Var, value
from pyomo.opt import SolverResults, SolverStatus, SolutionStatus, TerminationCondition
from pyomo.opt.results.problem import ProblemSense

from experiments import h1_origin_selector_replay_development_v1 as m
from tests import h1_group_selector_integration_helpers_v2 as integration
from tests import test_h1_origin_selector_replay_development_v1 as fixtures
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver


def bundle(monkeypatch,lane):
    _,disclosure,prior,args=fixtures.inputs(lane)
    packet=fixtures.old.packet(raw_workload='0')
    after=m.physical._owned(type(packet.before),network_identity=packet.network.identity,
        completed_hours=1,units=(('G1',True,20.,1),),evidence_role='numerical_lex_candidate')
    frame=m.physical._frame(packet,after)
    before=m.initialize_development_selection(frame,prior.physical_carry.disclosure,lane=lane,
        selector=args['selector'],specification=args['specification'],limits=args['limits'],chronology_origin=True)
    if lane.role!='Rref':
        args['power']=m.physical.RelativeDcPower(0,'0','1','mechanism_assumption')
    calls=[]
    class Fake:
        def solve(self,model,**kwargs):
            calls.append(1)
            clone=model.clone()
            values={v.name:(20. if v.name=='generation[G1]' else 0.)
                    for v in clone.component_data_objects(Var)}
            for name,number in values.items():clone.find_component(name).set_value(number)
            objective=float(value(clone.objective.expr))
            result=SolverResults()
            result.solver.status=SolverStatus.ok
            result.solver.termination_condition=TerminationCondition.optimal
            result.problem.sense=ProblemSense.minimize
            result.problem.number_of_objectives=1
            result.problem.lower_bound=result.problem.upper_bound=objective
            solution=result.solution.add();solution._cuid=False;solution.status=SolutionStatus.optimal
            solution.variable.update({name:{'Value':number} for name,number in values.items()})
            solution.objective['objective']={'Value':objective}
            return result
    monkeypatch.setattr(m.native.capture,'create_solver',lambda spec:(Fake(),m.native.capture.solver_options(spec)))
    key=m.input_identity(frame,disclosure,before,lane=lane,power=args['power'])
    frozen=();records=[]
    for index,label in enumerate(m.stage_labels(frame,lane)):
        def build():
            return m.build_development_stage(frame,disclosure,before,lane=lane,index=index,
                frozen=frozen,expected_identity=key,power=args['power'])
        raw=m.native.capture._solve(build,args['specification'],fixtures.old.BUDGET,
            f'{m.SCHEMA}:{lane.role}:{index}:{label}')
        assert raw.optimal and raw.assignment_valid
        records.append(m.encode_development_record(frame,disclosure,before,raw,
            index=index,frozen=frozen,**args))
        frozen+=(raw.objective,)
    assert len(calls)==(3 if lane.role=='Rref' else 2)
    def denied(*a,**kw):raise AssertionError('replay attempted solver execution')
    monkeypatch.setattr(m.native.capture,'create_solver',denied)
    monkeypatch.setattr(m.native.capture,'_solve',denied)
    def replay(saved):
        return m.replay_development_records(frame,disclosure,before,saved,**args,
            expected_identity=key,expected_policy_identity=before.policy_identity,
            expected_report_sha256=tuple(sha256(raw).hexdigest() for raw in saved))
    return tuple(records),replay


@pytest.mark.parametrize('lane',[fixtures.R,fixtures.A])
def test_zero_workload_real_model_and_replay_match_integration_oracle(monkeypatch,no_solver,lane):
    records,replay=bundle(monkeypatch,lane)
    result=replay(records)
    assert result.status=='replayed_numerical_candidate',result.errors
    expected=integration.ZERO_WORKLOAD_REFERENCE_LOCKS if lane.role=='Rref' else (0.,20.)
    assert result.canonical_lock_hex==tuple(v.hex() for v in expected)
    assert result.next_candidate.physical_carry.generation_mw==( ('G1',20.), )
    assert result.candidate_request_exact==(('0','1') if lane.role=='Rref' else None)
    assert result.solver_calls_by_replay==0


@pytest.mark.parametrize('lane',[fixtures.R,fixtures.A])
def test_zero_sign_replacement_in_saved_objective_is_rejected(monkeypatch,no_solver,lane):
    records,replay=bundle(monkeypatch,lane)
    row=json.loads(records[0])
    original=row['canonical_objective_hex']
    assert float.fromhex(original)==0.
    row['canonical_objective_hex']=(0. if original.startswith('-') else -0.).hex()
    changed=m.native._encoded(row)
    result=replay((changed,))
    assert result.status=='unresolved' and result.next_candidate is None
    assert result.verified_stages==0
    assert any('stored canonical objective hex differs from replay' in error for error in result.errors)
