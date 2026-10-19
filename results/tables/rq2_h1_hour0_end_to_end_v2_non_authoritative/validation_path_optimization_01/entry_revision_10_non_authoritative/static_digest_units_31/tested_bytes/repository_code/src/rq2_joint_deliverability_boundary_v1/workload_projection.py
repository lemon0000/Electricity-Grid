"""Explicit numerical workload projection for a declared linear power mechanism.

No overload policy, pairing, CFE transformation or empirical calibration.
"""
from fractions import Fraction as Q
from math import isfinite
from re import fullmatch


def _ratio(x):
    return [str(x.numerator), str(x.denominator)]


def project_workload_power(raw_fraction, normalized_unit_mw, *, decimal_places):
    """Round exact source decimals half-even, then verify the existing MW identity.

    decimal_places and MW scale are caller-declared development parameters.
    This function does not register them for formal experiments.
    """
    for name, number in (('raw fraction',raw_fraction),('MW unit',normalized_unit_mw)):
        if type(number) is not str or fullmatch(r'(?:0|[1-9][0-9]*)(?:\.[0-9]+)?',number) is None:
            raise ValueError('nonnegative plain decimal string required: '+name)
    if type(decimal_places) is not int or not 1 <= decimal_places <= 12:
        raise ValueError('explicit decimal places from 1 through 12 required')
    raw,unit=Q(raw_fraction),Q(normalized_unit_mw)
    if unit<=0:
        raise ValueError('positive MW unit required')
    if fullmatch(r'(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?',normalized_unit_mw) is None:
        raise ValueError('canonical decimal MW unit required by CommonRequestMapping')
    result={'raw_workload_fraction':raw_fraction,'normalized_unit_mw':normalized_unit_mw,
        'decimal_places':decimal_places,'projection_rule':'exact_decimal_half_even_then_str_float_identity_v1',
        'power_rule':'linear_workload_power_no_idle_offset_v1', 'parameter_role':'mechanism_assumption',
        'status':'unresolved','reason':None,'workload_occupancy':None,'dc_baseline_mw':None,
        'projected_fraction_exact':None,'projection_error_exact':None,
        'maximum_rounding_error_exact':_ratio(Q(1,2*10**decimal_places)),
        'exact_interface_identity_verified':False,'raw_fraction_clipped':False,
        'observed_power_mapping':False,'formal_result':False}
    if raw>1:
        result['reason']='raw_fraction_above_one_requires_separate_contract'
        return result
    projected=Q(round(raw*10**decimal_places),10**decimal_places)
    result['projected_fraction_exact']=_ratio(projected)
    result['projection_error_exact']=_ratio(projected-raw)
    if raw>0 and projected==0:
        result['reason']='positive_source_would_project_to_zero'
        return result
    try:
        occupancy,power=float(projected),float(projected*unit)
    except OverflowError:
        result['reason']='nonfinite_float_projection'
        return result
    if not isfinite(occupancy) or not isfinite(power):
        result['reason']='nonfinite_float_projection'
        return result
    if Q(str(occupancy))!=projected or Q(str(power))!=projected*unit:
        result['reason']='exact_decimal_interface_identity_not_representable'
        return result
    result.update(status='projected',workload_occupancy=occupancy,dc_baseline_mw=power,
        exact_interface_identity_verified=True)
    return result
