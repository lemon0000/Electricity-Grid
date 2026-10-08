"""Bounded observations from one unchanged HiGHS legacy-interface call.

No solution is loaded, accepted, reconstructed or certified by this helper.
The caller must durably reserve an invocation and supervise its process.
"""
from copy import deepcopy
from hashlib import sha256
from importlib.metadata import version
from math import isfinite
from pathlib import Path
from time import perf_counter

from pyomo.common import timing
from pyomo.contrib.solver.common import base, results
from pyomo.contrib.solver.solvers import highs
from pyomo.opt import SolverResults, SolverStatus, TerminationCondition

from src.rq2_joint_deliverability_boundary_v1 import normal_execution_stream_numeric as kernel


SCHEMA = 'rq2_single_highs_phase_observation_v1'
LOG_LIMIT = 8192
TIMER_LIMIT = 64
COUNTERS = ('simplex_iteration_count', 'ipm_iteration_count', 'mip_node_count',
            'pdlp_iteration_count', 'qp_iteration_count')


def implementation_identity():
    if version('Pyomo') != '6.10.1' or version('highspy') != '1.15.1':
        raise ValueError('pinned private diagnostic interface versions required')
    return kernel._digest(SCHEMA, kernel.streaming.implementation_identity(),
        tuple((module.__name__, sha256(Path(module.__file__).read_bytes()).hexdigest())
              for module in (base, results, highs, timing, kernel, kernel.native, kernel.legacy)),
        sha256(Path(__file__).read_bytes()).hexdigest())


def _seconds(value):
    if type(value) is not float or not isfinite(value) or value < 0:
        raise ValueError('finite nonnegative observed float seconds required')
    return value


def validate_profile(body):
    expected = {'schema', 'legacy_status', 'legacy_termination', 'solution_count',
        'internal_termination', 'internal_solution_status', 'timers', 'internal_wall_seconds',
        'highs_reported_seconds', 'solve_interface_seconds', 'counters', 'solver_log_bytes',
        'solver_log_sha256', 'solver_calls', 'model_values_loaded', 'normal_accepted',
        'infeasibility_certificate', 'optimality_certificate', 'native_execution_authenticated',
        'formal_result', 'security_certified'}
    if type(body) is not dict or set(body) != expected or body['schema'] != SCHEMA:
        raise ValueError('exact solver profile fields required')
    if (any(body[name] is not False for name in ('model_values_loaded', 'normal_accepted',
            'native_execution_authenticated', 'formal_result', 'security_certified'))
            or any(body[name] is not None for name in ('infeasibility_certificate', 'optimality_certificate'))
            or type(body['solver_calls']) is not int or body['solver_calls'] != 1):
        raise ValueError('diagnostic profile cannot confer authority')
    term = results.TerminationCondition[body['internal_termination']]
    state = results.SolutionStatus[body['internal_solution_status']]
    if (body['legacy_status'] != base.legacy_solver_status_map[term].name
            or body['legacy_termination'] != base.legacy_termination_condition_map[term].name
            or type(body['solution_count']) is not int
            or body['solution_count'] != int(state in (results.SolutionStatus.feasible, results.SolutionStatus.optimal))):
        raise ValueError('profile outcomes do not correspond')
    rows = body['timers']
    if (type(rows) is not list or not 0 < len(rows) <= TIMER_LIMIT
            or any(type(row) is not list or len(row) != 3 or type(row[0]) is not str
                or not 0 < len(row[0]) <= 128 or type(row[1]) is not int or row[1] <= 0 for row in rows)
            or len({row[0] for row in rows}) != len(rows)):
        raise ValueError('bounded unique timer inventory required')
    stages = {row[0]: row for row in rows}
    top = {name: row for name, row in stages.items() if '.' not in name}
    if set(top) != {'set_instance', 'optimize', 'load solution'} or any(row[1] != 1 for row in top.values()):
        raise ValueError('one fresh solver stage required')
    for name, row in stages.items():
        _seconds(row[2])
        if '.' in name and name.rsplit('.', 1)[0] not in stages:
            raise ValueError('timer parent missing')
        children = [child[2] for key, child in stages.items() if '.' in key and key.rsplit('.', 1)[0] == name]
        if sum(children) > row[2] + 1e-6:
            raise ValueError('nested timers exceed parent')
    wall = _seconds(body['internal_wall_seconds'])
    if sum(row[2] for row in top.values()) > wall + 1e-6 or wall > _seconds(body['solve_interface_seconds']) + 1e-6:
        raise ValueError('profile timers exceed wall time')
    if _seconds(body['highs_reported_seconds']) > top['optimize'][2] + 1e-6:
        raise ValueError('native runtime exceeds enclosing optimize timer')
    counters = body['counters']
    if type(counters) is not dict or set(counters) != set(COUNTERS) or any(
            value is not None and (type(value) is not int or value < -1) for value in counters.values()):
        raise ValueError('native counter inventory required')
    size, digest = body['solver_log_bytes'], body['solver_log_sha256']
    if (type(size) is not int or not 0 < size <= LOG_LIMIT
            or type(digest) is not str or len(digest) != 64
            or any(char not in '0123456789abcdef' for char in digest)):
        raise ValueError('bounded log byte count and SHA256 required')


def extract(solver, raw, elapsed):
    """Read already-returned private Results; never call optimize/getSolution/load."""
    if (type(raw) is not SolverResults or len(raw.solver) != 1
            or type(raw.solver[0].status) is not SolverStatus
            or type(raw.solver[0].termination_condition) is not TerminationCondition):
        raise ValueError('one typed legacy solver result required')
    detail = solver._last_results_object
    if type(detail) is not results.Results:
        raise ValueError('pinned internal Results required')
    if (type(detail.termination_condition) is not results.TerminationCondition
            or type(detail.solution_status) is not results.SolutionStatus):
        raise ValueError('typed internal outcome required')
    if (raw.solver[0].status != base.legacy_solver_status_map[detail.termination_condition]
            or raw.solver[0].termination_condition != base.legacy_termination_condition_map[detail.termination_condition]
            or len(raw.solution) != int(detail.incumbent_objective is not None)):
        raise ValueError('legacy/internal outcome correspondence required')
    log = detail.solver_log
    if type(log) is not str or not log or len(log.encode('utf-8')) > LOG_LIMIT:
        raise ValueError('bounded nonempty solver log required')
    timer = detail.timing_info.timer
    if type(timer) is not timing.HierarchicalTimer or timer.stack:
        raise ValueError('complete stopped hierarchical timer required')
    names = timer.get_timers()
    if (type(names) is not list or not 0 < len(names) <= TIMER_LIMIT or len(set(names)) != len(names)
            or any(type(name) is not str or not 0 < len(name) <= 128 for name in names)
            or not {'set_instance', 'optimize', 'load solution'} <= set(names)
            or any(name == 'update' or name.startswith('update.') for name in names)):
        raise ValueError('fresh single-call timer inventory required')
    rows = []
    for name in names:
        count = timer.get_num_calls(name)
        if type(count) is not int or count <= 0:
            raise ValueError('positive timer call count required')
        rows.append([name, count, _seconds(timer.get_total_time(name))])
    top = {row[0]: row for row in rows if '.' not in row[0]}
    if set(top) != {'set_instance', 'optimize', 'load solution'} or any(row[1] != 1 for row in top.values()):
        raise ValueError('one fresh call per top-level solver stage required')
    wall = _seconds(detail.timing_info.wall_time)
    elapsed = _seconds(elapsed)
    if sum(row[2] for row in top.values()) > wall + 1e-6 or wall > elapsed + 1e-6:
        raise ValueError('solver timing intervals exceed containing wall time')
    counters = {}
    for name in COUNTERS:
        value = getattr(detail.extra_info, name, None)
        if value is not None and (type(value) is not int or value < -1):
            raise ValueError('integer native counter or missing value required')
        counters[name] = value
    # Bounds, objectives and assignments deliberately remain in the native record.
    profile = dict(schema=SCHEMA, legacy_status=raw.solver[0].status.name,
        legacy_termination=raw.solver[0].termination_condition.name,
        solution_count=len(raw.solution), internal_termination=detail.termination_condition.name,
        internal_solution_status=detail.solution_status.name, timers=rows,
        internal_wall_seconds=wall, highs_reported_seconds=_seconds(detail.timing_info.highs_time),
        solve_interface_seconds=elapsed, counters=counters, solver_log_bytes=len(log.encode('utf-8')),
        solver_log_sha256=sha256(log.encode('utf-8')).hexdigest(),
        solver_calls=1, model_values_loaded=False, normal_accepted=False,
        infeasibility_certificate=None, optimality_certificate=None,
        native_execution_authenticated=False, formal_result=False, security_certified=False)
    validate_profile(profile)
    return profile


def observe_once(inputs, *, specification, budget, expected_scale, expected_input_identity,
                 expected_implementation_identity, before_solve):
    """One diagnostic call; a failure after the callback leaves invocation unknown."""
    kernel._pin(expected_input_identity)
    kernel._pin(expected_implementation_identity)
    if not callable(before_solve):
        raise TypeError('caller-owned durable invocation reservation required')
    if implementation_identity() != expected_implementation_identity:
        raise ValueError('solver diagnostic implementation drift')
    kernel._validate(specification, budget, expected_scale)
    if specification.name != 'highs' or specification.time_limit_seconds != 1. or specification.threads != 1 or specification.tee:
        raise ValueError('single-thread one-second quiet HiGHS diagnostic required')
    owned = deepcopy(inputs)
    if len(owned.source_hours) > budget.max_horizon or kernel.normal_input_identity(owned) != expected_input_identity:
        raise ValueError('complete bounded normal input identity required')
    model = kernel.streaming.build_continuous_normal_model(owned, expected_identity=expected_input_identity,
        expected_implementation_identity=kernel.streaming.implementation_identity())
    if kernel.model_scale(model) != expected_scale:
        raise ValueError('external model scale mismatch')
    structure, initial = kernel.native._structure(model), kernel.native._snapshot(model)
    solver, options = kernel.native.create_solver(specification)
    if options != kernel.native.solver_options(specification) or solver._last_results_object is not None:
        raise ValueError('fresh solver and exact options required')
    before_solve()
    started = perf_counter()
    raw = solver.solve(model, load_solutions=False, tee=specification.tee, options=options)
    elapsed = perf_counter()-started
    profile = extract(solver, raw, elapsed)
    if kernel.native._structure(model) != structure or kernel.native._snapshot(model) != initial:
        raise ValueError('diagnostic solve changed the unloaded model')
    if (kernel.normal_input_identity(owned) != expected_input_identity
            or implementation_identity() != expected_implementation_identity):
        raise ValueError('post-solve input or implementation drift')
    return dict(profile=profile, model_structure_identity=structure,
        input_identity=expected_input_identity, implementation_identity=expected_implementation_identity)
