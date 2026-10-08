"""One unchanged direct Gurobi call with bounded read-only MESSAGE capture."""
from copy import deepcopy
from hashlib import sha256
from math import isfinite
from pathlib import Path
import re
from time import perf_counter

import gurobipy as gp
from pyomo.opt import SolverResults, SolverStatus, TerminationCondition
from src.rq2_joint_deliverability_boundary_v1 import normal_execution_gurobi_ordered as kernel

SCHEMA = 'rq2_gurobi_convergence_profile_v1'
LOG_LIMIT = 64*1024
COUNTERS = ('NodeCount', 'IterCount', 'BarIterCount', 'Work', 'SolCount')
NUMBER = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'


def convergence_rows(log):
    """Persist only numeric search observations, never arbitrary message text."""
    rows = {'root_relaxations': [], 'progress': [], 'final_bounds': []}
    for line in log.splitlines():
        match = re.fullmatch(r'Root relaxation: objective ('+NUMBER+r'), (\d+) iterations, ('+
            NUMBER+r') seconds(?: \('+NUMBER+r' work units\))?', line.strip())
        if match:
            rows['root_relaxations'].append([float(match[1]), int(match[2]), float(match[3])])
            continue
        match = re.fullmatch(r'Best objective ('+NUMBER+r'), best bound ('+NUMBER+r'), gap ('+
            NUMBER+r')%', line.strip())
        if match:
            rows['final_bounds'].append([float(match[1]), float(match[2]), float(match[3])])
            continue
        match = re.fullmatch(r'\s*[H*]?\s*(\d+)\s+(\d+)\s+(.+?)\s+('+NUMBER+r')s\s*', line)
        if not match:
            continue
        tokens = match[3].split()
        if len(tokens) not in (4, 7):
            continue
        if not all(t == '-' or re.fullmatch(NUMBER+r'%?', t) for t in tokens):
            continue
        incumbent, bound, gap, iteration = tokens[-4:]
        if gap != '-' and not gap.endswith('%'):
            continue
        number = lambda t: None if t == '-' else float(t.rstrip('%'))
        rows['progress'].append([int(match[1]), int(match[2]), number(incumbent),
            number(bound), number(gap), number(iteration), float(match[4])])
    return rows


def implementation_identity():
    return kernel._digest(SCHEMA, kernel.native.adapter.implementation_identity(),
        kernel.streaming.implementation_identity(), kernel.native.structure.implementation_identity(),
        tuple((m.__name__, sha256(Path(m.__file__).read_bytes()).hexdigest())
              for m in (kernel, kernel.native, kernel.legacy)),
        sha256(Path(__file__).read_bytes()).hexdigest())


class MessageCapture:
    """Only cbGet(MSG_STRING); never inject solutions, cuts, parameters or stops."""
    def __init__(self):
        self.parts, self.size, self.overflow, self.error = [], 0, False, None

    def __call__(self, model, where):
        if where != gp.GRB.Callback.MESSAGE or self.overflow or self.error:
            return
        try:
            line = model.cbGet(gp.GRB.Callback.MSG_STRING)
            if type(line) is not str:
                raise TypeError('native message must be text')
            size = len(line.encode('utf-8'))
            if self.size + size > LOG_LIMIT:
                self.overflow = True
                return
            self.parts.append(line)
            self.size += size
        except Exception as error:
            self.error = type(error).__name__

    def text(self):
        if self.overflow or self.error or not self.size:
            raise ValueError('incomplete bounded native message capture')
        return ''.join(self.parts)


def nonnegative(value):
    if type(value) not in (int, float) or not isfinite(value) or value < 0:
        raise ValueError('finite nonnegative native observation required')
    return value


def validate_profile(body):
    fields = {'schema', 'native_status', 'legacy_status', 'legacy_termination',
        'native_runtime_seconds', 'solve_interface_seconds', 'counters', 'convergence',
        'solver_log_bytes', 'solver_log_sha256', 'solver_calls', 'model_values_loaded',
        'normal_accepted', 'formal_result', 'security_certified'}
    if type(body) is not dict or set(body) != fields or body['schema'] != SCHEMA:
        raise ValueError('exact convergence profile required')
    if (any(body[k] is not False for k in ('model_values_loaded', 'normal_accepted',
            'formal_result', 'security_certified'))
            or type(body['solver_calls']) is not int or body['solver_calls'] != 1):
        raise ValueError('diagnostic call cannot confer acceptance')
    correspondence = {
        gp.GRB.OPTIMAL: ('ok', 'optimal'), gp.GRB.TIME_LIMIT: ('aborted', 'maxTimeLimit'),
        gp.GRB.INFEASIBLE: ('warning', 'infeasible'),
        gp.GRB.INF_OR_UNBD: ('warning', 'infeasibleOrUnbounded'),
        gp.GRB.UNBOUNDED: ('warning', 'unbounded')}
    if (type(body['native_status']) is not int
            or correspondence.get(body['native_status']) != (body['legacy_status'], body['legacy_termination'])):
        raise ValueError('native and interface status mismatch or unsupported outcome')
    native = nonnegative(body['native_runtime_seconds'])
    elapsed = nonnegative(body['solve_interface_seconds'])
    if native > elapsed + 1e-6:
        raise ValueError('native time exceeds enclosing call')
    counters = body['counters']
    if type(counters) is not dict or set(counters) != set(COUNTERS):
        raise ValueError('exact native counter inventory required')
    for name, value in counters.items():
        nonnegative(value)
        if name != 'Work' and int(value) != value:
            raise ValueError('integral native counter required')
    if type(body['solver_log_bytes']) is not int or not 0 < body['solver_log_bytes'] <= LOG_LIMIT:
        raise ValueError('bounded native log byte count required')
    kernel._pin(body['solver_log_sha256'])
    rows = body['convergence']
    if type(rows) is not dict or set(rows) != {'root_relaxations', 'progress', 'final_bounds'}:
        raise ValueError('exact numeric convergence inventory required')
    for name, items in rows.items():
        if type(items) is not list or len(items) > LOG_LIMIT:
            raise ValueError('bounded numeric convergence rows required')
        for row in items:
            if type(row) is not list or len(row) != (7 if name == 'progress' else 3):
                raise ValueError('numeric convergence row shape mismatch')
            for i, value in enumerate(row):
                if name == 'progress' and i in (2, 3, 4, 5) and value is None:
                    continue
                if type(value) not in (int, float) or not isfinite(value):
                    raise ValueError('finite numeric convergence value required')
                if not ((name == 'root_relaxations' and i == 0) or
                        (name == 'progress' and i in (2, 3)) or
                        (name == 'final_bounds' and i in (0, 1))):
                    nonnegative(value)


def extract(solver, raw, elapsed, capture):
    if (type(raw) is not SolverResults or len(raw.solver) != 1
            or type(raw.solver[0].status) is not SolverStatus
            or type(raw.solver[0].termination_condition) is not TerminationCondition
            or type(solver._solver_model) is not gp.Model):
        raise ValueError('typed direct native/interface result required')
    model = solver._solver_model
    log = capture.text()
    body = dict(schema=SCHEMA, native_status=model.Status,
        legacy_status=raw.solver[0].status.name,
        legacy_termination=raw.solver[0].termination_condition.name,
        native_runtime_seconds=model.Runtime, solve_interface_seconds=elapsed,
        counters={name:model.getAttr(name) for name in COUNTERS}, convergence=convergence_rows(log),
        solver_log_bytes=len(log.encode('utf-8')), solver_log_sha256=sha256(log.encode('utf-8')).hexdigest(),
        solver_calls=1, model_values_loaded=False, normal_accepted=False,
        formal_result=False, security_certified=False)
    validate_profile(body)
    return body


def observe_once(inputs, *, specification, budget, expected_scale, expected_input_identity,
                 expected_implementation_identity, before_solve):
    kernel._pin(expected_input_identity)
    kernel._pin(expected_implementation_identity)
    if not callable(before_solve):
        raise TypeError('durable invocation reservation required')
    if implementation_identity() != expected_implementation_identity:
        raise ValueError('convergence profile implementation drift')
    kernel._validate(specification, budget, expected_scale)
    kernel.native.adapter.validate_spec(specification)
    owned = deepcopy(inputs)
    if len(owned.source_hours) > budget.max_horizon or kernel.normal_input_identity(owned) != expected_input_identity:
        raise ValueError('complete bounded input identity required')
    model = kernel.streaming.build_continuous_normal_model(owned,
        expected_identity=expected_input_identity,
        expected_implementation_identity=kernel.streaming.implementation_identity())
    if kernel.model_scale(model) != expected_scale:
        raise ValueError('external model scale mismatch')
    structure, initial = kernel.native._structure(model), kernel.native._snapshot(model)
    solver, options = kernel.native.create_solver(specification)
    if options != kernel.native.solver_options(specification) or solver._callback is not None:
        raise ValueError('fresh solver with exact options required')
    capture = MessageCapture()
    solver._callback = capture
    before_solve()
    started = perf_counter()
    raw = solver.solve(model, load_solutions=False, tee=False, options=options)
    elapsed = perf_counter()-started
    body = extract(solver, raw, elapsed, capture)
    if kernel.native._structure(model) != structure or kernel.native._snapshot(model) != initial:
        raise ValueError('diagnostic solve changed unloaded model')
    if (kernel.normal_input_identity(owned) != expected_input_identity
            or implementation_identity() != expected_implementation_identity):
        raise ValueError('post-solve input or implementation drift')
    return dict(profile=body, model_structure_identity=structure,
        input_identity=expected_input_identity, implementation_identity=expected_implementation_identity)
