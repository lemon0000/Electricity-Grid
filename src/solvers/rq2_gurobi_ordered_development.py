"""Version-pinned direct Gurobi interface for bounded development checks.

Callers must bind its implementation identity and own execution provenance.
"""
from hashlib import sha256
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path

from pyomo.environ import SolverFactory
from pyomo.opt.results import results_, solution, solver as solver_results
from pyomo.solvers.plugins.solvers import GUROBI, gurobi_direct, direct_solver, direct_or_persistent_solver

from . import rq2_solver_adapter as legacy


def implementation_identity():
    if version('Pyomo') != '6.10.1' or version('gurobipy') != '13.0.2':
        raise ValueError('pinned direct interface versions required')
    files = (legacy, GUROBI, gurobi_direct, direct_solver, direct_or_persistent_solver,
        results_, solution, solver_results)
    values = tuple((m.__name__, sha256(Path(m.__file__).read_bytes()).hexdigest()) for m in files)
    return sha256(repr(('rq2_gurobi_ordered_development_v1', values,
        sha256(Path(__file__).read_bytes()).hexdigest())).encode()).hexdigest()


def validate_spec(spec):
    if (type(spec) is not legacy.Rq2SolverSpec or spec.name != 'gurobi'
            or spec.expected_package_version != '13.0.2' or spec.threads != 1
            or spec.time_limit_seconds != 15. or spec.tee is not False):
        raise ValueError('fifteen-second single-thread direct Gurobi development scope required')
    if (legacy.solver_spec(asdict(spec)) != spec or spec.random_seed != 0
            or spec.mip_relative_gap != 1e-8 or any(getattr(spec, name) != 1e-9 for name in (
                'feasibility_tolerance', 'optimality_tolerance', 'integer_feasibility_tolerance'))):
        raise ValueError('unchanged numeric tolerances and seed required')


def create_solver(spec):
    validate_spec(spec)
    implementation_identity()
    solver = SolverFactory('gurobi', solver_io='direct')
    if type(solver) is not gurobi_direct.GurobiDirect or not solver.available(exception_flag=False):
        raise ValueError('exact available direct Gurobi interface required')
    return solver, legacy.solver_options(spec)
