from math import nextafter, inf
from fractions import Fraction
from hashlib import sha256
import pytest
from src.solvers import rq2_normal_numerical_candidate_v1 as api


def record(obj=1388837.913859345, lower=None, upper=None):
    lower = obj if lower is None else lower
    upper = obj if upper is None else upper
    terms=[['x',obj.hex(),1.0.hex()]]
    algebra=api.provenance._algebra(0.,terms)
    exact=Fraction.from_float(obj)
    rational=dict(numerator=str(exact.numerator),denominator=str(exact.denominator))
    return dict(implementation_identity='a'*64, variables=1,assignment=[['x',1.0.hex()]],
        assignment_valid=True, maximum_residual=0., maximum_integrality_violation=0.,
        provenance=dict(schema='rq2_objective_provenance_v1',collector_sha256='b'*64,adapter_identity='c'*64,
            is_mip=True, native_model_sense=1, native_status=2,native_solution_count=1,
            pyomo_status='ok', pyomo_termination='optimal', pyomo_solution_status='optimal',
            native={'ObjVal': {'hex':upper.hex(),'available':True}, 'ObjBound': {'hex':lower.hex(),'available':True},
                    'ObjBoundC':{'hex':lower.hex(),'available':True}},
            constant_hex=0.0.hex(),native_constant_hex=0.0.hex(),
            ordered_objective_terms=terms,ordered_native_objective_terms=terms,
            canonical_objective_algebra=algebra,native_objective_algebra=algebra,
            exact_objective=rational,native_exact_objective=rational,
            referenced_assignment=[['x',1.0.hex()]],
            assignment_sha256=sha256(repr((('x',1.0.hex()),)).encode()).hexdigest(),
            pyomo_lower_hex=lower.hex(), pyomo_upper_hex=upper.hex(),
            canonical_objective_hex=obj.hex(), native_algebra_equals_canonical_algebra=True))


def evaluate(n):
    return api.evaluate(n,expected_implementation='a'*64,expected_collector='b'*64,expected_adapter='c'*64)


def test_h25_archived_values_counterfactual_not_direct_provenance():
    # Synthetic report containing the archived values; not reconstructed native evidence.
    report = record(1388837.913859345, 1388837.9138593453, 1388837.9138593455)
    report['maximum_residual']=2.788453912216937e-10
    result=evaluate(report)
    assert result['candidate_numeric_predicate_passed']
    assert not result['strict_legacy_lower_le_canonical']
    assert not result['formal_acceptance_authorized']
    assert not result['rigorous_exact_optimality_certified']


@pytest.mark.parametrize('objective', [-1.,0.,1.])
def test_positive_negative_and_exact_zero(objective):
    assert evaluate(record(objective))['candidate_numeric_predicate_passed']


def test_zero_objective_nonzero_bound_is_unresolved():
    assert not evaluate(record(0., -1e-20, 0.))['candidate_numeric_predicate_passed']


@pytest.mark.parametrize('fault', ['timeout','bound_order','channel','algebra','assignment','residual','integer','objective','gap'])
def test_candidate_rejections_preserve_original_limits(fault):
    n=record(1.)
    p=n['provenance']
    if fault=='timeout': p['native_status']=9; p['pyomo_termination']='maxTimeLimit'
    if fault=='bound_order': p['native']['ObjBound']['hex']=nextafter(1.,inf).hex()
    if fault=='channel': p['pyomo_upper_hex']=nextafter(1.,inf).hex()
    if fault=='algebra':
        p['ordered_native_objective_terms']=[['x',2.0.hex(),1.0.hex()]]
        p['native_objective_algebra']=api.provenance._algebra(0.,p['ordered_native_objective_terms'])
        p['native_exact_objective']={'numerator':'2','denominator':'1'}
        p['native_algebra_equals_canonical_algebra']=False
    if fault=='assignment': n['assignment_valid']=False
    if fault=='residual': n['maximum_residual']=nextafter(1e-9,inf)
    if fault=='integer': n['maximum_integrality_violation']=nextafter(1e-9,inf)
    if fault=='objective': p['canonical_objective_hex']=(1.+2e-9).hex()
    if fault=='gap':
        p['native']['ObjBound']['hex']=(1.-2e-8).hex()
        p['pyomo_lower_hex']=(1.-2e-8).hex()
    assert not evaluate(n)['candidate_numeric_predicate_passed']


def test_missing_provenance_remains_unresolved():
    assert not evaluate({'provenance':None,'implementation_identity':'a'*64})['candidate_numeric_predicate_passed']


@pytest.mark.parametrize('bad',[False,'0',float('nan'),float('inf')])
def test_invalid_residual_types_rejected(bad):
    n=record(1.)
    n['maximum_residual']=bad
    with pytest.raises(ValueError): evaluate(n)


def test_noncanonical_hex_and_boolean_sense_rejected():
    n=record(1.)
    n['provenance']['native_model_sense']=True
    with pytest.raises(ValueError): evaluate(n)
    n=record(1.)
    n['provenance']['native']['ObjVal']['hex']='0x1p+0'
    with pytest.raises(ValueError): evaluate(n)


@pytest.mark.parametrize('fault',['coefficient','constant','assignment','identity','boundc_missing','boundc_nonfinite'])
def test_full_inventory_mutations_rejected(fault):
    n=record(1.)
    p=n['provenance']
    if fault=='coefficient': p['ordered_native_objective_terms']=[['x',2.0.hex(),1.0.hex()]]
    if fault=='constant': p['native_constant_hex']=1.0.hex()
    if fault=='assignment': n['assignment']=[['x',0.0.hex()]]
    if fault=='identity': p['collector_sha256']='0'*64
    if fault=='boundc_missing': p['native']['ObjBoundC']['available']=False
    if fault=='boundc_nonfinite': p['native']['ObjBoundC']['hex']='inf'
    with pytest.raises(ValueError): evaluate(n)


def test_real_tiny_complete_collector_report():
    import json
    from pathlib import Path
    from test_rq2_objective_provenance_run_v1 import builder,spec,arguments
    from src.solvers import rq2_objective_provenance_run_v1 as runner
    n=json.loads(runner.solve_once(builder,spec(),**arguments()))
    result=api.evaluate(n,expected_implementation=runner.implementation_identity(),
        expected_collector=sha256(Path(runner.provenance.__file__).read_bytes()).hexdigest(),
        expected_adapter=runner.provenance.adapter.implementation_identity())
    assert result['candidate_numeric_predicate_passed']


def test_exact_residual_limit_and_negative_nonzero_gap():
    n=record(-1.,-1.-1e-9,-1.)
    n['maximum_residual']=n['maximum_integrality_violation']=1e-9
    assert evaluate(n)['candidate_numeric_predicate_passed']


def test_exact_objective_and_gap_limits():
    # At zero canonical objective, upper=1e-9 gives an exact binary64 difference.
    assert evaluate(record(0.,1e-9,1e-9))['candidate_numeric_predicate_passed']
    # lower=0 makes gap exactly 1, proving the rational comparison path; use a
    # power-of-two upper and boundary-adjacent bounds for the frozen 1e-8 gate.
    limit=Fraction.from_float(1e-8)
    lower=float(Fraction(1)-limit)
    accepted=Fraction(1)-Fraction.from_float(lower)<=limit
    assert evaluate(record(1.,lower,1.))['candidate_numeric_predicate_passed'] is accepted
    below=nextafter(lower,-inf)
    assert not evaluate(record(1.,below,1.))['candidate_numeric_predicate_passed']
    above=nextafter(lower,inf)
    assert evaluate(record(1.,above,1.))['candidate_numeric_predicate_passed']
