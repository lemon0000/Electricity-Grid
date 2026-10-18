"""Strict bounded export correspondence, development only; never solves.

Call saved_report only AFTER immutable raw ingress. Any exception is unresolved,
not a feasibility verdict. No normalization, retries or projection publication.
"""
from fractions import Fraction
from hashlib import sha256
import json
from math import isfinite

from pyomo.environ import Constraint, Objective, Var, minimize, value
from pyomo.repn import generate_standard_repn

from experiments import h1_report_byte_bound_development_v1 as syntax
from experiments import h1_report_byte_bound_development_v2 as grammar


class ExportUnresolved(ValueError):
    pass


def _finite(number):
    if type(number) not in (int,float) or not isfinite(number):
        raise ExportUnresolved('finite built-in export coefficient required')
    return float(number)


def _canonical(model):
    variables=tuple(model.component_data_objects(Var,descend_into=True))
    names=tuple(v.name for v in variables)
    constraints=sum(1 for _ in model.component_data_objects(Constraint,active=True,descend_into=True))
    if (not variables or len(variables)>891 or len(set(names))!=len(names) or constraints>1272
            or any(len(syntax.encode(name))>38 for name in names)):
        raise ExportUnresolved('model outside pinned-source shape envelope')
    objectives=tuple(model.component_data_objects(Objective,active=True,descend_into=True))
    if len(objectives)!=1 or objectives[0].sense!=minimize:
        raise ExportUnresolved('one active linear minimization objective required')
    repn=generate_standard_repn(objectives[0].expr,compute_values=True)
    if not repn.is_linear() or len(repn.linear_vars)>362:
        raise ExportUnresolved('canonical objective outside term envelope')
    known={id(v):v.name for v in variables}
    coefficients={}
    for v,c in zip(repn.linear_vars,repn.linear_coefs,strict=True):
        if id(v) not in known or v.name in coefficients:
            raise ExportUnresolved('canonical objective variable identity mismatch')
        coefficients[v.name]=Fraction.from_float(_finite(c))
    coefficients={n:c for n,c in coefficients.items() if c}
    return variables,constraints,Fraction.from_float(_finite(value(repn.constant))),coefficients


def live_export(model, *, forward_pairs, reverse_pairs, native_variables, native_expression,
                native_model_sense):
    """Check a live direct-adapter map without optimize/load/capture calls.

    Inputs are bounded tuples of actual variable objects and map.items(). The
    native objects must be the same retained handles, not name-only surrogates.
    This intentionally narrow predicate still requires real adapter validation.
    """
    if type(native_model_sense) is not int or native_model_sense != 1:
        raise ExportUnresolved('exact native minimization sense required')
    variables,_,constant,coefficients=_canonical(model)
    for rows in (forward_pairs,reverse_pairs,native_variables):
        if type(rows) is not tuple or len(rows)!=len(variables):
            raise ExportUnresolved('exact complete bounded native map inventory required')
    if any(type(row) is not tuple or len(row)!=2 for row in forward_pairs+reverse_pairs):
        raise ExportUnresolved('exact map pairs required')
    canonical={id(v):v for v in variables}
    forward={id(v):(v,n) for v,n in forward_pairs}
    reverse={id(n):(n,v) for n,v in reverse_pairs}
    native={id(n):n for n in native_variables}
    if (len(forward)!=len(variables) or set(forward)!=set(canonical)
            or len(reverse)!=len(variables) or len(native)!=len(variables)
            or set(reverse)!=set(native)
            or {id(n) for _,n in forward_pairs}!=set(native)):
        raise ExportUnresolved('native/forward/reverse variable sets differ')
    for v,n in forward_pairs:
        if reverse[id(n)][1] is not v or canonical[id(v)] is not v:
            raise ExportUnresolved('reverse map is not the exact inverse')
    count=native_expression.size()
    if type(count) is not int or not 0<=count<=362:
        raise ExportUnresolved('native objective outside term envelope')
    actual={}
    for index in range(count):
        n=native_expression.getVar(index)
        if id(n) not in reverse:
            raise ExportUnresolved('native term missing reverse map handle')
        name=reverse[id(n)][1].name
        if name in actual:
            raise ExportUnresolved('duplicate native objective term')
        actual[name]=Fraction.from_float(_finite(native_expression.getCoeff(index)))
    actual={n:c for n,c in actual.items() if c}
    if Fraction.from_float(_finite(native_expression.getConstant()))!=constant or actual!=coefficients:
        raise ExportUnresolved('native objective algebra differs from canonical model')
    return dict(live_map_correspondence_checked=True,native_minimization_sense_checked=True,
        variables=len(variables),native_terms=count,
        native_execution_authenticated=False,native_export_coverage=False,formal_result=False)


def saved_report(raw, model):
    """Validate immutable saved bytes against the actual current stage model.

    The original report does not contain reverse-map handles. This checks only
    report/model correspondence and cannot infer the live-map check occurred.
    """
    try:
        if type(raw) is not bytes or not 0<len(raw)<=16*1024*1024:
            raise ExportUnresolved('bounded original raw bytes required')
        report=json.loads(raw)
        syntax.validate(report,grammar.grammar())
        if syntax.encode(report)!=raw:
            raise ExportUnresolved('exact canonical original serializer bytes required')
        variables,constraints,constant,coefficients=_canonical(model)
        if report['variables']!=len(variables) or report['constraints']!=constraints:
            raise ExportUnresolved('report/model size mismatch')
        if report['assignment'] is None or report['provenance'] is None:
            raise ExportUnresolved('complete assignment/provenance unavailable')
        rows=report['assignment']
        assigned=dict(rows)
        if len(assigned)!=len(rows) or set(assigned)!={v.name for v in variables}:
            raise ExportUnresolved('exact complete unique assignment required')
        for v in variables:
            if v.fixed and _finite(value(v)).hex()!=assigned[v.name]:
                raise ExportUnresolved('canonical fixed assignment differs')
        p=report['provenance']
        referenced=p['referenced_assignment']
        refs=dict(referenced)
        if (len(refs)!=len(referenced) or referenced!=sorted(referenced)
                or any(assigned.get(n)!=x for n,x in referenced)
                or sha256(repr(tuple(tuple(row) for row in referenced)).encode()).hexdigest()!=p['assignment_sha256']):
            raise ExportUnresolved('referenced assignment differs')
        def channel(prefix):
            c=Fraction.from_float(float.fromhex(p[prefix+'constant_hex']))
            terms=p['ordered_'+prefix+'objective_terms']
            terms_by_name={}
            total=c
            for name,coefficient,x in terms:
                if name in terms_by_name or name not in refs or assigned.get(name)!=x:
                    raise ExportUnresolved('duplicate/foreign term or assignment mismatch')
                f=Fraction.from_float(float.fromhex(coefficient))
                terms_by_name[name]=f
                total+=f*Fraction.from_float(float.fromhex(x))
            nonzero={n:v for n,v in terms_by_name.items() if v}
            algebra=[str(c),[[n,str(f)] for n,f in sorted(nonzero.items())]]
            exact=dict(numerator=str(total.numerator),denominator=str(total.denominator))
            label='native_' if prefix else 'canonical_'
            if (p[label+'objective_algebra']!=algebra or p[prefix+'exact_objective']!=exact
                    or c!=constant or nonzero!=coefficients):
                raise ExportUnresolved('objective algebra/exact value differs from canonical model')
            return total
        canonical_total,native_total=channel(''),channel('native_')
        if (p['native_algebra_equals_canonical_algebra'] is not True
                or p['native_exact_value_equals_canonical_exact_value'] is not (native_total==canonical_total)):
            raise ExportUnresolved('algebra/value equality flag mismatch')
        limit=syntax.bound(grammar.grammar())
        if len(raw)>limit:
            raise ExportUnresolved('conditional report byte bound exceeded')
        return dict(schema='h1_native_export_guard_development_v1',raw_sha256=sha256(raw).hexdigest(),
            raw_bytes=len(raw),conditional_bound_bytes=limit,report_shape_and_objective_correspondence_checked=True,
            full_scientific_replay_required=True,
            live_reverse_map_checked=False,native_export_coverage=False,resource_admission=False,
            scientific_acceptance=False,formal_result=False)
    except (KeyError,TypeError,ValueError,OverflowError) as error:
        if isinstance(error,ExportUnresolved):raise
        raise ExportUnresolved('report export unresolved: '+str(error)) from error
