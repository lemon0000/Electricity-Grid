"""One owned development solve with bounded objective provenance output."""
from hashlib import sha256
import json
from pathlib import Path

from pyomo.environ import Var
from . import rq2_objective_provenance_v1 as provenance
from ..rq2_joint_deliverability_boundary_v1 import scale_normal_native as audit


def encode(report):
    return json.dumps(report, sort_keys=True, allow_nan=False, separators=(',', ':')).encode()


def implementation_identity():
    from ..rq2_joint_deliverability_boundary_v1 import normal_task_process, scale_episode_controller
    return sha256(encode({
        'collector': sha256(Path(provenance.__file__).read_bytes()).hexdigest(),
        'runner': sha256(Path(__file__).read_bytes()).hexdigest(),
        'adapter': provenance.adapter.implementation_identity(),
        'audit': sha256(Path(audit.__file__).read_bytes()).hexdigest(),
        'structure': audit.structure.implementation_identity(),
        'supervision': sha256(Path(scale_episode_controller.__file__).read_bytes()).hexdigest(),
        'process': sha256(Path(normal_task_process.__file__).read_bytes()).hexdigest(),
    })).hexdigest()


def solve_once(builder, spec, *, expected_structure, max_variables,
               max_constraints, max_payload_bytes, expected_implementation):
    """Preserve all existing numerical thresholds; report no certification.

    Caller owns source binding, durable intent and hard process supervision.
    This function may call the solver once; exceptions never trigger retries.
    """
    for limit in (max_variables, max_constraints, max_payload_bytes):
        if type(limit) is not int or limit <= 0:
            raise ValueError('positive declared size limit required')
    if implementation_identity() != expected_implementation:
        raise ValueError('provenance implementation mismatch')
    model = builder()
    scale = audit.model_scale(model)
    if scale.variables > max_variables or scale.constraints > max_constraints:
        raise ValueError('declared model scale exceeded')
    if audit._structure(model) != expected_structure:
        raise ValueError('model structure mismatch')
    before = audit._snapshot(model)
    solver, options = provenance.adapter.create_solver(spec)
    try:
        result = solver.solve(model, load_solutions=False, options=options, tee=False)
        if audit._structure(model) != expected_structure or audit._snapshot(model) != before:
            raise ValueError('model mutated before explicit load')
        report = dict(schema='rq2_objective_provenance_owned_solve_v1',
            implementation_identity=expected_implementation,
            model_structure_identity=expected_structure, solver_calls=1,
            variables=scale.variables, constraints=scale.constraints,
            solver_options=options, pyomo_status=str(result.solver.status),
            pyomo_termination=str(result.solver.termination_condition),
            native_status=int(solver._solver_model.Status),
            native_solution_count=int(solver._solver_model.SolCount),
            provenance=None, assignment=None, maximum_residual=None,
            maximum_integrality_violation=None, assignment_valid=False,
            formal_result=False, normal_accepted=False, optimality_certified=False)
        if len(result.solution) == 1:
            values = audit._native_values(model, result, 'variable', Var)
            completed = audit._canonical_completions(model, values)
            model.solutions.load_from(result, select=0, ignore_invalid_labels=False)
            for name, number, _reason in completed:
                model.find_component(name).set_value(number)
            report['provenance'] = provenance.capture_direct(solver, result, model)
            loaded = tuple((name, item[2]) for name, item in audit._snapshot(model))
            if loaded != tuple(sorted((*values, *((n, x) for n, x, _ in completed)))):
                raise ValueError('loaded assignment differs from native and explicit completions')
            canonical = builder()
            if audit._structure(canonical) != expected_structure:
                raise ValueError('fresh canonical model differs')
            assignment = dict(loaded)
            fixed_valid = True
            for variable in canonical.component_data_objects(Var):
                candidate = assignment[variable.name]
                if variable.fixed and abs(candidate - variable.value) > spec.feasibility_tolerance:
                    fixed_valid = False
                variable.set_value(candidate, skip_validation=True)
            residual, integer = audit._constraint_violation(canonical), audit._integrality_violation(canonical)
            report.update(assignment=[(name, number.hex()) for name, number in loaded],
                maximum_residual=residual, maximum_integrality_violation=integer,
                assignment_valid=bool(fixed_valid and residual <= spec.feasibility_tolerance
                    and integer <= spec.integer_feasibility_tolerance))
        if audit._structure(model) != expected_structure or implementation_identity() != expected_implementation:
            raise ValueError('post-solve implementation/model drift')
        raw = encode(report)
        if len(raw) > max_payload_bytes:
            raise ValueError('provenance payload exceeds declared byte limit')
        return raw
    finally:
        solver.close()
