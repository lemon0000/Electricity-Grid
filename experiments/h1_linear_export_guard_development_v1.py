"""Development-only exact linear export check; no solver creation or execution.

The caller must update the native model before checking and must prevent mutation
through optimize. This predicate does not authenticate a caller or authorize it.
"""
from fractions import Fraction

from pyomo.environ import Constraint, value
from pyomo.repn import generate_standard_repn

from experiments.h1_native_export_guard_development_v1 import (
    ExportUnresolved, _canonical, _finite,
)


def _number(x):
    return Fraction.from_float(_finite(x))


def _index(handle, size):
    index = handle.index
    if type(index) is not int or not 0 <= index < size:
        raise ExportUnresolved('native index outside exact inventory')
    return index


def _same(a, b):
    # Gurobi wrapper identity is a native-object property, not Python id().
    if a.sameAs(b) is not True or b.sameAs(a) is not True:
        raise ExportUnresolved('native handle identity differs')


def _inventory(handles, expected):
    if len(handles) != expected:
        raise ExportUnresolved('native inventory size differs')
    result = {}
    for handle in handles:
        index = _index(handle, expected)
        if index in result:
            raise ExportUnresolved('duplicate native index')
        result[index] = handle
    return result


def _maps(canonical, native, forward, reverse):
    if (type(forward) is not tuple or type(reverse) is not tuple
            or len(forward) != len(canonical) or len(reverse) != len(canonical)
            or any(type(row) is not tuple or len(row) != 2 for row in forward + reverse)):
        raise ExportUnresolved('complete exact map tuples required')
    by_id = {id(item): item for item in canonical}
    mapping = {}
    seen = set()
    for item, handle in forward:
        if id(item) not in by_id or id(item) in seen:
            raise ExportUnresolved('canonical map inventory differs')
        seen.add(id(item))
        index = _index(handle, len(native))
        _same(handle, native[index])
        if index in mapping:
            raise ExportUnresolved('forward map not bijective')
        mapping[index] = item
    seen = set()
    for handle, item in reverse:
        index = _index(handle, len(native))
        _same(handle, native[index])
        if index in seen or mapping[index] is not item:
            raise ExportUnresolved('reverse map is not exact inverse')
        seen.add(index)
    return mapping


def _terms(expression, native, mapping, cap):
    count = expression.size()
    if type(count) is not int or not 0 <= count <= cap:
        raise ExportUnresolved('native term count outside envelope')
    terms = {}
    for i in range(count):
        handle = expression.getVar(i)
        index = _index(handle, len(native))
        _same(handle, native[index])
        name = mapping[index].name
        if name in terms:
            raise ExportUnresolved('duplicate native expression term')
        terms[name] = _number(expression.getCoeff(i))
    return {name: coefficient for name, coefficient in terms.items() if coefficient}


def _repn(expression, variables):
    repn = generate_standard_repn(expression, compute_values=True)
    if not repn.is_linear():
        raise ExportUnresolved('only linear constraint bodies supported')
    known = {id(v): v for v in variables}
    terms = {}
    for variable, coefficient in zip(repn.linear_vars, repn.linear_coefs, strict=True):
        if id(variable) not in known or variable.name in terms:
            raise ExportUnresolved('foreign or duplicate canonical term')
        terms[variable.name] = _number(coefficient)
    return _number(value(repn.constant)), {n: c for n, c in terms.items() if c}


def check(model, *, native_model, variable_forward, variable_reverse,
          constraint_forward, constraint_reverse):
    """Check complete variables, domains, bounds, objective and linear rows.

    Native methods follow the pinned Gurobi direct interface. Tests use synthetic
    handles only. Ranges, hidden auxiliaries and rounded algebra discrepancies
    fail closed. Success is neither actual-adapter coverage nor feasibility.
    """
    variables, count, constant, objective = _canonical(model)
    constraints = tuple(model.component_data_objects(Constraint, active=True, descend_into=True))
    for name, expected in (('NumVars', len(variables)), ('NumConstrs', count),
                           ('NumQConstrs', 0), ('NumSOS', 0), ('NumGenConstrs', 0),
                           ('NumQNZs', 0), ('NumScenarios', 0), ('NumPWLObjVars', 0),
                           ('NumObj', 1), ('ModelSense', 1)):
        actual = getattr(native_model, name)
        if type(actual) is not int or actual != expected:
            raise ExportUnresolved('native model attribute differs: ' + name)
    native_vars = _inventory(native_model.getVars(), len(variables))
    native_cons = _inventory(native_model.getConstrs(), count)
    vmap = _maps(variables, native_vars, variable_forward, variable_reverse)
    cmap = _maps(constraints, native_cons, constraint_forward, constraint_reverse)
    for index, variable in vmap.items():
        handle = native_vars[index]
        kind = 'B' if variable.is_binary() else 'I' if variable.is_integer() else 'C' if variable.is_continuous() else None
        if kind is None or handle.VType != kind:
            raise ExportUnresolved('native variable domain differs')
        lower = variable.value if variable.fixed else variable.lb
        upper = variable.value if variable.fixed else variable.ub
        for side, bound, infinity in (('LB', lower, -1e100), ('UB', upper, 1e100)):
            actual = _number(getattr(handle, side))
            if bound is None:
                expected = _number(infinity)
            else:
                number = _finite(value(bound))
                if abs(number) >= 1e20:
                    raise ExportUnresolved('finite canonical bound reaches native infinity')
                expected = _number(number)
            if actual != expected:
                raise ExportUnresolved('native variable bound differs')
    expression = native_model.getObjective()
    if (_terms(expression, native_vars, vmap, 362) != objective
            or _number(expression.getConstant()) != constant):
        raise ExportUnresolved('native objective algebra differs')
    for index, constraint in cmap.items():
        if constraint.equality:
            sense, bound = '=', constraint.lower
        elif constraint.has_lb() and constraint.has_ub():
            raise ExportUnresolved('ranged constraint requires a separately proved auxiliary protocol')
        elif constraint.has_lb():
            sense, bound = '>', constraint.lower
        elif constraint.has_ub():
            sense, bound = '<', constraint.upper
        else:
            raise ExportUnresolved('unbounded constraint row')
        offset, expected = _repn(constraint.body, variables)
        rhs = _number(value(bound)) - offset
        if abs(rhs) >= _number(1e20):
            raise ExportUnresolved('finite row RHS reaches native infinity envelope')
        handle = native_cons[index]
        row = native_model.getRow(handle)
        if (type(handle.Lazy) is not int or handle.Lazy != 0
                or _number(row.getConstant()) != 0 or handle.Sense != sense
                or _terms(row, native_vars, vmap, len(variables)) != expected
                or _number(handle.RHS) != rhs):
            raise ExportUnresolved('native constraint algebra differs')
    return dict(schema='h1_linear_export_guard_development_v1', variables=len(variables),
                constraints=count, exact_linear_correspondence_checked=True,
                native_export_coverage=False, native_execution_authenticated=False,
                resource_admission=False, formal_execution_ready=False, formal_result=False)
