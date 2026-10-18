"""Canonical native-record persistence and solver-free consistency replay.

This is a diagnostic, not a new solver result or an execution certificate.
Partial execution records are retained but never promoted to complete evidence.
"""
from dataclasses import dataclass, fields, asdict
from hashlib import sha256
from importlib.metadata import version
import json
from math import isfinite
from pathlib import Path

from pyomo.environ import Var, Objective, value
from pyomo.opt import SolverStatus, TerminationCondition, SolutionStatus
from pyomo.opt.results.problem import ProblemSense

from . import continuous_grid_candidate as capture
from .prefix_handoff import IMPLEMENTATION, _encoded, _unique_object, _reject_constant
from .continuous_grid_normal import SOURCE_DEPENDENCIES
from .current_grid_step import _Owned, _owned


SCHEMA = 'rq2_grid_evidence_solver_free_replay_v1'
DEPENDENCIES = tuple(sorted(set(SOURCE_DEPENDENCIES) | set(capture.EXTRA_DEPENDENCIES) | set(IMPLEMENTATION) | {
    'src/rq2_joint_deliverability_boundary_v1/'+name+'.py' for name in (
        'grid_evidence_replay', 'current_grid_step', 'grid_information', 'event_disclosure')}))


def _hash(value):
    if type(value) is not str or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('canonical lowercase SHA256 required')
    return value


def _identity(spec, budget):
    if SCHEMA != 'rq2_grid_evidence_solver_free_replay_v1':
        raise ValueError('grid replay schema drift')
    root = Path(__file__).resolve().parents[2]
    sources = tuple((name, sha256((root/name).read_bytes()).hexdigest()) for name in DEPENDENCIES)
    return capture._digest(SCHEMA, sources,
        capture._execution_identity(spec, budget))


def _admit(spec, budget, purpose, input_identity):
    _hash(input_identity)
    if type(purpose) is not str or not purpose:
        raise ValueError('explicit expected stage purpose required')
    if type(spec) is not capture.Rq2SolverSpec or spec != capture.solver_spec(asdict(spec)):
        raise ValueError('canonical solver specification required')
    if type(budget) is not capture.GridDevelopmentBudget:
        raise ValueError('typed development budget required')
    budget.__post_init__()
    if (spec.time_limit_seconds is None or spec.time_limit_seconds > budget.max_seconds_per_solve
            or spec.time_limit_seconds > budget.max_total_solver_seconds or spec.threads > budget.max_threads):
        raise ValueError('solver specification exceeds development budget')


def export_grid_evidence(raw, *, input_identity, purpose, specification, budget):
    """Preserve owned records, including failures, without assigning trust to JSON."""
    _admit(specification, budget, purpose, input_identity)
    if type(raw) is not capture.GridSolveEvidence or raw.purpose != purpose:
        raise ValueError('owned solve evidence with matching stage purpose required')
    return _encoded(dict(schema=SCHEMA, status='DRAFT_NONAUTHORITATIVE',
        input_identity=input_identity, purpose=purpose, specification=specification, budget=budget,
        implementation_identity=_identity(specification, budget), raw=raw,
        formal_result=False, security_certified=False, native_execution_authenticated=False))


@dataclass(frozen=True, init=False)
class GridEvidenceReplay(_Owned):
    artifact_sha256: str
    input_identity: str
    purpose: str
    implementation_identity: str
    model_structure_identity: str
    model_relative_only: bool
    source_input_binding_verified: bool
    selector_chain_verified: bool
    scope: str
    replay_consistent: bool
    assignment_recomputed: bool
    canonical_assignment_valid: bool | None
    recomputed_objective: float | None
    recomputed_maximum_residual: float | None
    recomputed_maximum_integrality_violation: float | None
    reported_optimal: bool
    reported_native_infeasible: bool
    optimal_flag_reproduced: bool | None
    native_infeasible_flag_reproduced: bool | None
    recorded_execution_errors: tuple
    replay_errors: tuple
    solver_calls_by_replay_module: int
    external_builder_effects_verified: bool
    native_execution_authenticated: bool
    optimality_certificate: None
    infeasibility_certificate: None
    formal_result: bool
    security_certified: bool


def _tuples(item):
    if type(item) is list:
        return tuple(_tuples(x) for x in item)
    if type(item) is dict:
        return {k: _tuples(v) for k, v in item.items()}
    return item


def _enum(record, enum):
    matches = [x for x in enum if capture._enum(x) == record]
    if len(matches) != 1:
        raise ValueError('unrecognized typed native enumeration')
    return matches[0]


def _number_record(record):
    if type(record) is not tuple or len(record) != 3 or any(type(x) is not str for x in record[:2]):
        raise ValueError('invalid native number descriptor')
    kind, representation, number = record
    if number is None:
        # Unknown/nonfinite native values stay unknown. Do not eval repr text.
        if kind in ('builtins.int', 'builtins.float'):
            try:
                parsed = float(representation)
            except ValueError as exc:
                raise ValueError('invalid numeric repr') from exc
            if isfinite(parsed):
                raise ValueError('finite native repr cannot have null numeric value')
        return None
    if type(number) is not float or not isfinite(number) or kind not in ('builtins.int', 'builtins.float'):
        raise ValueError('unsupported finite native number descriptor')
    parsed = int(representation) if kind == 'builtins.int' else float(representation)
    if not isfinite(parsed) or float(parsed) != number or repr(parsed) != representation:
        raise ValueError('native number descriptor differs from value')
    return number


def _values(rows, allowed):
    if type(rows) is not tuple or any(type(r) is not tuple or len(r) != 2 for r in rows):
        raise ValueError('invalid immutable native assignment inventory')
    names = tuple(r[0] for r in rows)
    if any(type(n) is not str for n in names) or names != tuple(sorted(set(names))) or not set(names) <= allowed:
        raise ValueError('foreign, duplicate or unsorted native assignment')
    if any(type(x) is not float or not isfinite(x) for _, x in rows):
        raise ValueError('finite native float assignment required')
    return dict(rows)


def _replay(raw, builder, spec, budget, purpose):
    errors = []
    def require(condition, message):
        if not condition:
            errors.append(message)
    if set(raw) != {f.name for f in fields(capture.GridSolveEvidence)}:
        raise ValueError('raw evidence field inventory mismatch')
    for key in ('optimal', 'assignment_valid', 'native_infeasible'):
        if type(raw[key]) is not bool:
            raise ValueError('typed evidence boolean required')
    for key in ('variables', 'constraints'):
        if type(raw[key]) is not int or raw[key] < 0:
            raise ValueError('nonnegative integer model scale required')
    for key in ('objective', 'lower', 'upper', 'maximum_residual', 'maximum_integrality_violation'):
        if raw[key] is not None and (type(raw[key]) is not float or not isfinite(raw[key])):
            raise ValueError('finite float metric or explicit unknown required')
    if (type(raw['calls']) is not int or raw['calls'] not in (0, 1)
            or (raw['solution_count'] is not None and (type(raw['solution_count']) is not int or raw['solution_count'] < 0))
            or type(raw['errors']) is not tuple or any(type(e) is not str for e in raw['errors'])):
        raise ValueError('invalid raw call/count/error evidence')
    model = builder()
    scale = capture.model_scale(model)
    if scale.variables > budget.max_variables or scale.constraints > budget.max_constraints:
        raise ValueError('replay model exceeds declared development scale')
    structure = capture._structure(model)
    initial = capture._snapshot(model)
    versions = (version('Pyomo'), version('highspy' if spec.name == 'highs' else 'gurobipy'))
    options = tuple(sorted(capture.solver_options(spec).items()))
    require(raw['purpose'] == purpose, 'purpose_mismatch')
    require((raw['variables'], raw['constraints']) == (scale.variables, scale.constraints), 'model_scale_mismatch')
    require(_encoded(raw['initial_values']) == _encoded(initial), 'initial_assignment_mismatch')
    require(type(raw['structures']) is tuple and len(raw['structures']) == 3, 'structure_inventory_mismatch')
    partial = bool(raw['errors'] and raw['errors'] != ('canonical_assignment_invalid',))
    complete_metadata = (_encoded((raw['structures'], raw['preload_values'], raw['versions'], raw['options']))
        == _encoded(((structure,)*3, initial, (versions,)*2, (options,)*2))
        and versions[1] == spec.expected_package_version)
    if not partial:
        require(complete_metadata, 'structure_preload_runtime_or_options_mismatch')
    else:
        require(raw['structures'] and raw['structures'][0] == structure, 'initial_structure_mismatch')
    count = raw['solution_count']
    objective = residual = integer = assignment = None
    recomputed = False
    status = termination = solution_status = lower = upper = None
    native_metadata = False
    try:
        if len(raw['solver_records']) != 1 or len(raw['problem_records']) != 1:
            raise ValueError('one returned solver/problem record required')
        if type(raw['solver_records'][0]) is not tuple or len(raw['solver_records'][0]) != 2:
            raise ValueError('native solver record must be an exact status/termination pair')
        status, termination = (_enum(raw['solver_records'][0][0], SolverStatus),
                               _enum(raw['solver_records'][0][1], TerminationCondition))
        problem = raw['problem_records'][0]
        if len(problem) != 6 or _enum(problem[0], ProblemSense) is not ProblemSense.minimize:
            raise ValueError('one minimization problem required')
        lower, upper, _, _, objectives = map(_number_record, problem[1:])
        if objectives != 1 or count is None or len(raw['solution_statuses']) != count:
            raise ValueError('native objective or solution count mismatch')
        statuses = tuple(_enum(x, SolutionStatus) for x in raw['solution_statuses'])
        solution_status = statuses[0] if count == 1 else None
        native_metadata = True
        require(raw['calls'] == 1, 'native_return_without_one_recorded_call')
        require((raw['lower'], raw['upper']) == (lower, upper), 'native_bound_projection_mismatch')
    except (ValueError, TypeError, IndexError) as exc:
        if not partial:
            errors.append('native_metadata:'+str(exc))
    if count == 1 and raw['loaded_values']:
        try:
            fresh = builder()
            if capture._structure(fresh) != structure or capture._snapshot(fresh) != initial:
                raise ValueError('fresh canonical model changed during replay')
            model = fresh
            variables = {v.name: v for v in model.component_data_objects(Var)}
            objectives = {o.name: o for o in model.component_data_objects(Objective)}
            native = _values(raw['native_values'], set(variables))
            loaded = _values(raw['loaded_values'], set(variables))
            reported_objectives = _values(raw['native_objectives'], set(objectives))
            completions = capture._canonical_completions(model, tuple(native.items()))
            require(_encoded(raw['canonical_completed_values']) == _encoded(completions), 'canonical_completion_mismatch')
            completed = tuple(sorted((*native.items(), *((n, x) for n, x, _ in completions))))
            if raw['loaded_values'] != completed or set(loaded) != set(variables):
                raise ValueError('native_completed_loaded_assignment_mismatch')
            fixed_failed = False
            for name, variable in variables.items():
                if variable.fixed and abs(loaded[name]-variable.value) > spec.feasibility_tolerance:
                    fixed_failed = True
                variable.set_value(loaded[name], skip_validation=True)
            r, i = capture._constraint_violation(model), capture._integrality_violation(model)
            residual, integer = (r if isfinite(r) else None), (i if isfinite(i) else None)
            assignment = (not fixed_failed and residual is not None and integer is not None
                and residual <= spec.feasibility_tolerance and integer <= spec.integer_feasibility_tolerance)
            if len(objectives) != 1:
                raise ValueError('one canonical objective required')
            objective = capture._number(value(next(iter(objectives.values())).expr))
            recomputed = True
            require(not reported_objectives or (len(reported_objectives) == 1
                and abs(next(iter(reported_objectives.values()))-objective) <= min(spec.feasibility_tolerance, 1e-9)),
                'native_objective_mismatch')
            require((raw['objective'], raw['maximum_residual'], raw['maximum_integrality_violation'])
                == (objective, residual, integer), 'canonical_objective_or_residual_mismatch')
        except (ValueError, TypeError, KeyError, OverflowError) as exc:
            errors.append('assignment_replay:'+str(exc))
    elif not partial:
        require(count != 1, 'single_solution_missing_loaded_assignment')
        require(not any(raw[k] for k in ('loaded_values', 'native_values', 'native_objectives', 'canonical_completed_values')),
            'assignment_without_single_solution')
        require(all(raw[k] is None for k in ('objective', 'maximum_residual', 'maximum_integrality_violation')),
            'assignment_metric_without_single_solution')
    complete = complete_metadata and native_metadata and count in (0, 1) and not partial
    optimal = infeasible = None
    if complete:
        require(raw['assignment_valid'] == (bool(assignment) and not raw['errors']), 'assignment_flag_mismatch')
        expected_errors = ('canonical_assignment_invalid',) if assignment is False else ()
        require(raw['errors'] == expected_errors, 'execution_error_projection_mismatch')
        domain = (not hasattr(model, 'curtailment') or
            (upper is not None and 0 <= upper <= capture._number(value(model.curtailment.ub))))
        optimal = bool(not raw['errors'] and status is SolverStatus.ok
            and termination in (TerminationCondition.optimal, TerminationCondition.globallyOptimal)
            and solution_status is SolutionStatus.optimal and assignment and objective is not None
            and lower is not None and upper is not None and lower <= upper and lower <= objective and domain
            and abs(upper-objective) <= min(spec.feasibility_tolerance, 1e-9)
            and (upper-lower)/max(abs(objective), 1e-12) <= spec.mip_relative_gap)
        known_highs = (spec.name == 'highs' and versions == ('6.10.1', '1.15.1')
            and status is SolverStatus.error and purpose.startswith(('corrective_source_', 'zero_dc_source_'))
            and all(v.is_continuous() for v in model.component_data_objects(Var)))
        infeasible = bool(not raw['errors'] and (status in (SolverStatus.ok, SolverStatus.warning) or known_highs)
            and termination is TerminationCondition.infeasible and count == 0)
        require(raw['optimal'] == optimal, 'optimal_flag_mismatch')
        require(raw['native_infeasible'] == infeasible, 'native_infeasible_flag_mismatch')
    elif raw['optimal'] or raw['assignment_valid'] or raw['native_infeasible']:
        errors.append('partial_evidence_claims_complete_execution_flag')
    return dict(model_structure_identity=structure,
        scope='complete_native_record' if complete else 'partial_execution_evidence',
        replay_consistent=complete and not errors, assignment_recomputed=recomputed,
        canonical_assignment_valid=assignment, recomputed_objective=objective,
        recomputed_maximum_residual=residual, recomputed_maximum_integrality_violation=integer,
        reported_optimal=raw['optimal'], reported_native_infeasible=raw['native_infeasible'],
        optimal_flag_reproduced=optimal, native_infeasible_flag_reproduced=infeasible,
        recorded_execution_errors=raw['errors'], replay_errors=tuple(errors))


def replay_grid_evidence(data, *, expected_sha256, expected_input_identity, expected_purpose,
                         specification, budget, builder):
    """Check consistency relative to a caller's model, without a native solve.

    input_identity is an external metadata pin, not a proof that builder is
    derived from those inputs. Selector-specific source/chain auditing remains
    required before using this diagnostic in a complete episode verifier.
    """
    _admit(specification, budget, expected_purpose, expected_input_identity)
    if type(data) is not bytes or sha256(data).hexdigest() != _hash(expected_sha256):
        raise ValueError('grid evidence digest mismatch')
    implementation = _identity(specification, budget)
    try:
        payload = json.loads(data, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
        expected = dict(schema=SCHEMA, status='DRAFT_NONAUTHORITATIVE', input_identity=expected_input_identity,
            purpose=expected_purpose, specification=specification, budget=budget,
            implementation_identity=implementation, raw=payload['raw'],
            formal_result=False, security_certified=False, native_execution_authenticated=False)
        if _encoded(expected) != data:
            raise ValueError('canonical evidence or independently expected metadata mismatch')
        result = _replay(_tuples(payload['raw']), builder, specification, budget, expected_purpose)
    except (TypeError, KeyError, AttributeError, IndexError, OverflowError) as exc:
        raise ValueError('invalid grid evidence structure') from exc
    if implementation != _identity(specification, budget):
        raise ValueError('grid replay implementation changed during audit')
    return _owned(GridEvidenceReplay, artifact_sha256=expected_sha256, input_identity=expected_input_identity,
        purpose=expected_purpose, implementation_identity=implementation, **result,
        model_relative_only=True, source_input_binding_verified=False, selector_chain_verified=False,
        solver_calls_by_replay_module=0, external_builder_effects_verified=False,
        native_execution_authenticated=False, optimality_certificate=None,
        infeasibility_certificate=None, formal_result=False, security_certified=False)


def write_grid_evidence(raw, path, **metadata):
    path = Path(path)
    if not path.name.endswith('_non_authoritative.json'):
        raise ValueError('explicit non_authoritative filename required')
    data = export_grid_evidence(raw, **metadata)
    with path.open('xb') as stream:
        stream.write(data)
    return sha256(data).hexdigest()


def read_grid_evidence(path, **expectations):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('regular grid evidence file required')
    return replay_grid_evidence(path.read_bytes(), **expectations)
