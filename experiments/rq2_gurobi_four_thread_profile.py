"""Declared four-thread diagnostic successor; unchanged model and tolerances."""
from copy import deepcopy
from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from experiments import rq2_gurobi_convergence_profile as baseline

kernel, gp = baseline.kernel, baseline.gp
MessageCapture, extract = baseline.MessageCapture, baseline.extract
validate_profile, convergence_rows = baseline.validate_profile, baseline.convergence_rows
LOG_LIMIT, COUNTERS, SCHEMA = baseline.LOG_LIMIT, baseline.COUNTERS, baseline.SCHEMA


def implementation_identity():
    return kernel._digest('rq2_four_thread_convergence_diagnostic_v1',
        baseline.implementation_identity(), sha256(Path(__file__).read_bytes()).hexdigest())


def validate_spec(spec):
    if type(spec) is not kernel.Rq2SolverSpec or type(spec.threads) is not int or spec.threads != 4:
        raise ValueError('exact four-thread diagnostic specification required')
    kernel.native.adapter.validate_spec(replace(spec, threads=1))


def create_solver(spec):
    validate_spec(spec)
    adapter = kernel.native.adapter
    adapter.implementation_identity()
    solver = adapter.SolverFactory('gurobi', solver_io='direct')
    if type(solver) is not adapter.gurobi_direct.GurobiDirect or not solver.available(exception_flag=False):
        raise ValueError('exact available direct interface required')
    return solver, kernel.native.solver_options(spec)


def observe_once(inputs, *, specification, budget, expected_scale, expected_input_identity,
                 expected_implementation_identity, before_solve):
    kernel._pin(expected_input_identity)
    kernel._pin(expected_implementation_identity)
    if not callable(before_solve):
        raise TypeError('durable invocation reservation required')
    if implementation_identity() != expected_implementation_identity:
        raise ValueError('convergence profile implementation drift')
    kernel._validate(specification, budget, expected_scale)
    validate_spec(specification)
    owned = deepcopy(inputs)
    if len(owned.source_hours) > budget.max_horizon or kernel.normal_input_identity(owned) != expected_input_identity:
        raise ValueError('complete bounded input identity required')
    model = kernel.streaming.build_continuous_normal_model(owned,
        expected_identity=expected_input_identity,
        expected_implementation_identity=kernel.streaming.implementation_identity())
    if kernel.model_scale(model) != expected_scale:
        raise ValueError('external model scale mismatch')
    structure, initial = kernel.native._structure(model), kernel.native._snapshot(model)
    solver, options = create_solver(specification)
    if options != kernel.native.solver_options(specification) or solver._callback is not None:
        raise ValueError('fresh solver with exact options required')
    capture = MessageCapture()
    solver._callback = capture
    before_solve()
    started = perf_counter()
    raw = solver.solve(model, load_solutions=False, tee=False, options=options)
    elapsed = perf_counter()-started
    if solver._solver_model.Params.Threads != 4:
        raise ValueError('native thread parameter differs from diagnostic declaration')
    body = extract(solver, raw, elapsed, capture)
    if kernel.native._structure(model) != structure or kernel.native._snapshot(model) != initial:
        raise ValueError('diagnostic solve changed unloaded model')
    if (kernel.normal_input_identity(owned) != expected_input_identity
            or implementation_identity() != expected_implementation_identity):
        raise ValueError('post-solve input or implementation drift')
    return dict(profile=body, model_structure_identity=structure,
        input_identity=expected_input_identity, implementation_identity=expected_implementation_identity, diagnostic_specification=asdict(specification))
