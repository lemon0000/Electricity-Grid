from fractions import Fraction as Q

import pytest

from src.rq2_joint_deliverability_boundary_v1.workload_projection import project_workload_power


@pytest.mark.parametrize('raw,expected',[('0','0'),('1','1'),('0.125','0.12'),('0.135','0.14'),('0.00003733412600572748761922760581','0')])
def test_hand_computed_half_even(raw,expected):
    r=project_workload_power(raw,'250',decimal_places=2)
    assert Q(*map(int,r['projected_fraction_exact']))==Q(expected)
    if Q(raw)>0 and Q(expected)==0:
        assert r['status']=='unresolved' and r['workload_occupancy'] is None
    else:
        assert r['status']=='projected'
        assert Q(str(r['workload_occupancy']))*250==Q(str(r['dc_baseline_mw']))


def test_real_source_decimal_projection_and_signed_error():
    raw='0.00003733412600572748761922760581'
    r=project_workload_power(raw,'250',decimal_places=12)
    assert r['status']=='projected' and r['raw_workload_fraction']==raw
    error=Q(*map(int,r['projection_error_exact']))
    assert error==Q('0.000037334126')-Q(raw)
    assert abs(error)<=Q(1,2*10**12)


def test_above_one_cannot_round_into_allowed_range():
    r=project_workload_power('1.00000000000001','250',decimal_places=12)
    assert r['status']=='unresolved' and r['projected_fraction_exact'] is None
    assert not r['raw_fraction_clipped'] and r['dc_baseline_mw'] is None


@pytest.mark.parametrize('raw,unit,digits',[('-1','250',12),('nan','250',12),('1e-3','250',12),('0.5','0',12),
    (0.5,'250',12),('0.5',250,12),('0.5','250.0',12),('0.5','250',True),('0.5','250',13),('0.5','250',0)])
def test_explicit_valid_parameters_required(raw,unit,digits):
    with pytest.raises(ValueError): project_workload_power(raw,unit,decimal_places=digits)


def test_inexact_or_nonfinite_mw_projection_stays_unresolved():
    r=project_workload_power('0.123456789123','250.123456789',decimal_places=12)
    assert r['reason']=='exact_decimal_interface_identity_not_representable'
    assert r['workload_occupancy'] is None and r['dc_baseline_mw'] is None
    huge=project_workload_power('1','1'+'0'*400,decimal_places=12)
    assert huge['reason']=='nonfinite_float_projection'


def test_real_full_source_against_independent_decimal_oracle():
    from decimal import Decimal, localcontext, ROUND_HALF_EVEN
    from experiments.audit_rq2_workload_projection_v1 import audit
    report=audit('250',12,'0cca33dbfbd934881be3c4e375c76eb668c2ec41ff9bbc7392c2eb3947de18a5')
    assert len(report['rows'])==1632
    assert report['counts']['training']['projected']==816
    assert report['counts']['holdout']['projected']==810
    assert report['counts']['holdout']['unresolved']==6
    assert report['counts']['training']['decimal_product_float_projection_identity_fails']==553
    assert report['counts']['holdout']['decimal_product_float_projection_identity_fails']==543
    assert report['counts']['training']['binary_float_multiplication_identity_fails']==599
    assert report['counts']['holdout']['binary_float_multiplication_identity_fails']==592
    with localcontext() as context:
        context.prec=80
        for item in report['rows']:
            raw=Decimal(item['source_row']['workload_fraction'])
            result=item['projection']
            assert result['raw_workload_fraction']==item['source_row']['workload_fraction']
            if raw>1:
                assert result['workload_occupancy'] is None and result['dc_baseline_mw'] is None
                continue
            oracle=raw.quantize(Decimal('0.000000000001'),rounding=ROUND_HALF_EVEN)
            assert Decimal(str(result['workload_occupancy']))==oracle
            assert Decimal(str(result['dc_baseline_mw']))==oracle*Decimal('250')
            assert abs(raw-oracle)<=Decimal('0.0000000000005')
            assert Q(*map(int,result['projection_error_exact']))==Q(oracle)-Q(raw)
