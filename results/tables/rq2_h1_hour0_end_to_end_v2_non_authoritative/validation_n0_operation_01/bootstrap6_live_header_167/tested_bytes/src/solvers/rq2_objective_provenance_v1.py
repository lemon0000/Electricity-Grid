"""Read-only objective provenance for development; never issues a certificate.

Call after explicit solution loading, before closing the direct solver. This
collector does not solve, load, normalize bounds, or change acceptance rules.
"""
from fractions import Fraction
from hashlib import sha256
from math import isfinite
from pathlib import Path

from pyomo.environ import Objective, value, minimize
from pyomo.opt import ProblemSense
from pyomo.repn import generate_standard_repn
from pyomo.solvers.plugins.solvers.gurobi_direct import GurobiDirect
from gurobipy import GurobiError, GRB

from . import rq2_gurobi_declared_normal as adapter


def _number(number):
    number = float(number)
    if not isfinite(number):
        raise ValueError('finite numeric channel required')
    return number


def _hex(number):
    return _number(number).hex()


def _attribute(native, name):
    try:
        return {'hex': _hex(getattr(native, name)), 'available': True, 'error': None}
    except AttributeError:
        return {'hex': None, 'available': False, 'error': 'AttributeError'}
    except GurobiError as error:
        if error.errno != GRB.Error.DATA_NOT_AVAILABLE:
            raise
        return {'hex': None, 'available': False, 'error': 'GurobiError:DATA_NOT_AVAILABLE'}


def _algebra(constant, terms):
    coefficients = {}
    for name, coefficient, _assigned in terms:
        coefficients[name] = coefficients.get(name, Fraction(0)) + Fraction.from_float(float.fromhex(coefficient))
    return (str(Fraction.from_float(constant)),
            tuple((name, str(c)) for name, c in sorted(coefficients.items()) if c))


def compare_channels(*, native_objective, native_bound, pyomo_lower,
                     pyomo_upper, canonical_objective, exact_objective):
    """Exact binary64 comparisons; no tolerance or status-based acceptance."""
    values = tuple(map(_number, (native_objective, native_bound, pyomo_lower,
                                pyomo_upper, canonical_objective)))
    obj, bound, lower, upper, canonical = values
    if type(exact_objective) is not Fraction:
        raise TypeError('exact Fraction objective required')
    return {
        'native_to_pyomo_lower_hex_equal': bound.hex() == lower.hex(),
        'native_to_pyomo_upper_hex_equal': obj.hex() == upper.hex(),
        'lower_le_upper': lower <= upper,
        'lower_le_canonical': lower <= canonical,
        'lower_le_exact': Fraction.from_float(lower) <= exact_objective,
        'exact_minus_lower': str(exact_objective - Fraction.from_float(lower)),
        'canonical_minus_native_objective': str(
            Fraction.from_float(canonical) - Fraction.from_float(obj)),
    }


def capture_direct(solver, results, model):
    """Capture a loaded linear minimization result from the pinned direct API.

    A caller must archive and bind this report to its owned solve/assignment.
    Matching channels alone are neither execution authentication nor a proof
    of exact primal feasibility or optimality.
    """
    implementation = adapter.implementation_identity()
    if type(solver) is not GurobiDirect or solver._pyomo_model is not model:
        raise ValueError('exact direct solver and its loaded model required')
    native = solver._solver_model
    if native.ModelSense != 1 or len(results.problem) != 1:
        raise ValueError('one minimization problem required')
    if native.SolCount < 1 or len(results.solution) != 1:
        raise ValueError('one returned incumbent required')
    objectives = tuple(model.component_data_objects(Objective, active=True))
    if len(objectives) != 1 or objectives[0].sense != minimize:
        raise ValueError('one active minimization objective required')
    repn = generate_standard_repn(objectives[0].expr, compute_values=True)
    if not repn.is_linear():
        raise ValueError('linear objective required')
    # Compare all referenced assignments, including variables absent from the
    # objective. Unreferenced Pyomo variables are explicitly outside this map.
    assignment = []
    for variable, native_variable in solver._pyomo_var_to_solver_var_map.items():
        if solver._referenced_variables[variable] > 0:
            loaded, direct = _number(value(variable)), _number(native_variable.X)
            if loaded.hex() != direct.hex():
                raise ValueError('loaded/native assignment differs: ' + variable.name)
            assignment.append((variable.name, loaded.hex()))
    constant = _number(value(repn.constant))
    exact = Fraction.from_float(constant)
    terms = []
    for coefficient, variable in zip(repn.linear_coefs, repn.linear_vars):
        coefficient, assigned = _number(coefficient), _number(value(variable))
        terms.append((variable.name, coefficient.hex(), assigned.hex()))
        exact += Fraction.from_float(coefficient) * Fraction.from_float(assigned)
    canonical = _number(value(objectives[0].expr))
    native_objective = _number(native.ObjVal)
    native_expr = native.getObjective()
    native_terms = []
    native_exact = Fraction.from_float(_number(native_expr.getConstant()))
    reverse = solver._solver_var_to_pyomo_var_map
    for index in range(native_expr.size()):
        variable = native_expr.getVar(index)
        coefficient, assigned = _number(native_expr.getCoeff(index)), _number(variable.X)
        native_terms.append((reverse[variable].name, coefficient.hex(), assigned.hex()))
        native_exact += Fraction.from_float(coefficient) * Fraction.from_float(assigned)
    # Pyomo 6.10.1 maps continuous bounds from ObjVal, not ObjBound.
    is_mip = native.NumBinVars + native.NumIntVars > 0
    mapped_bound = _number(native.ObjBound) if is_mip else native_objective
    problem = results.problem[0]
    if problem.sense is not ProblemSense.minimize:
        raise ValueError('Pyomo minimization sense required')
    comparisons = compare_channels(native_objective=native_objective,
        native_bound=mapped_bound, pyomo_lower=problem.lower_bound,
        pyomo_upper=problem.upper_bound, canonical_objective=canonical,
        exact_objective=exact)
    attributes = {name: _attribute(native, name) for name in ('ObjVal', 'ObjBound', 'ObjBoundC', 'Runtime')}
    canonical_algebra = _algebra(constant, terms)
    native_algebra = _algebra(_number(native_expr.getConstant()), native_terms)
    termination_optimal = str(results.solver.termination_condition) in ('optimal', 'globallyOptimal')
    solution_optimal = str(results.solution[0].status) == 'optimal'
    return {
        'schema': 'rq2_objective_provenance_v1',
        'adapter_identity': implementation,
        'collector_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
        'native': attributes,
        'native_status': int(native.Status), 'native_solution_count': int(native.SolCount),
        'native_model_sense': int(native.ModelSense), 'is_mip': is_mip,
        'pyomo_status': str(results.solver.status),
        'pyomo_termination': str(results.solver.termination_condition),
        'pyomo_solution_status': str(results.solution[0].status),
        'optimal_status_channels_consistent': (
            (native.Status == GRB.OPTIMAL) == termination_optimal == solution_optimal
            and (native.Status != GRB.OPTIMAL or str(results.solver.status) == 'ok')),
        'pyomo_lower_hex': _hex(problem.lower_bound),
        'pyomo_upper_hex': _hex(problem.upper_bound),
        'pyomo_lower_source': 'ObjBound' if is_mip else 'ObjVal',
        'canonical_objective_hex': canonical.hex(),
        'exact_objective': {'numerator': str(exact.numerator), 'denominator': str(exact.denominator)},
        'constant_hex': constant.hex(), 'ordered_objective_terms': terms,
        'native_constant_hex': _hex(native_expr.getConstant()),
        'ordered_native_objective_terms': native_terms,
        'native_exact_objective': {'numerator': str(native_exact.numerator),
                                   'denominator': str(native_exact.denominator)},
        'native_exact_value_equals_canonical_exact_value': native_exact == exact,
        'canonical_objective_algebra': canonical_algebra,
        'native_objective_algebra': native_algebra,
        'native_algebra_equals_canonical_algebra': native_algebra == canonical_algebra,
        'referenced_assignment': sorted(assignment),
        'assignment_sha256': sha256(repr(tuple(sorted(assignment))).encode()).hexdigest(),
        'comparisons': comparisons,
        'formal_result': False, 'optimality_certified': False,
        'native_execution_authenticated': False,
        'solver_calls_by_collector': 0,
    }
