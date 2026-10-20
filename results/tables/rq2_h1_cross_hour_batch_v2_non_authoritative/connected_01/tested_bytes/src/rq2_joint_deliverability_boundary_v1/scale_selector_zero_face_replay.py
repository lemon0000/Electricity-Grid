"""Zero-solver replay of a complete mixed native/analytic selector result."""
from hashlib import sha256
import json
from pathlib import Path

from . import scale_selector_zero_face as mixed
from . import scale_selector_replay as old


def encode(result):
    if type(result) is not mixed.MixedSelectionResult:
        raise ValueError('owned mixed selection result required')
    return old.store._bytes(old.codec._encode(result))


def implementation_identity():
    root = Path(__file__).resolve().parents[2]
    return mixed._digest('draft_mixed_zero_face_replay_v1',
        sha256(Path(__file__).read_bytes()).hexdigest(),
        sha256(Path(mixed.__file__).read_bytes()).hexdigest(),
        sha256(Path(old.__file__).read_bytes()).hexdigest(),
        tuple((m.__name__, sha256(Path(m.__file__).read_bytes()).hexdigest()) for m in (old.store, old.codec)),
        tuple((name, sha256((root/name).read_bytes()).hexdigest()) for name in old.native.DEPENDENCIES),
        mixed.analytic.implementation_identity())


def replay(data, info, disclosure, before, *, expected_sha256, expected_implementation,
           expected_identity, selector, solver_specification, budget,
           expected_policy_identity, power=None, max_record_bytes=16*1024**2):
    if (type(data) is not bytes or type(max_record_bytes) is not int
            or not 0 < max_record_bytes <= 16*1024**2 or len(data) > max_record_bytes
            or sha256(data).hexdigest() != expected_sha256):
        raise ValueError('mixed record hash/size mismatch')
    if implementation_identity() != expected_implementation:
        raise ValueError('mixed replay implementation mismatch')
    saved = old.store._fields(json.loads(data), mixed.MixedSelectionResult)
    if saved['status'] != 'selected':
        raise ValueError('only complete selected chains can be reconstructed')
    wire = saved['stages']
    if (type(wire) is not list or len(wire) != 2 or wire[0] != 'tuple'
            or type(wire[1]) is not list or len(wire[1]) != budget.max_solver_calls):
        raise ValueError('complete mixed stage inventory required')
    module = mixed._module(budget)
    cls = module.ReferenceSelectionStage if module is mixed.reference else module.ActualDispatchStage
    count = [0]
    def native_replay(builder, spec, declared_budget, purpose):
        index = count[0]
        stage = old.store._fields(wire[1][index], cls)
        raw_fields = {key: old._value(value) for key, value in
                      old.store._fields(stage['raw_solve'], mixed.native.GridSolveEvidence).items()}
        diagnostic = old.native._replay(raw_fields, builder, spec, declared_budget, purpose)
        if (not diagnostic['replay_consistent'] or raw_fields['calls'] != 1
                or not diagnostic['canonical_assignment_valid'] or not diagnostic['optimal_flag_reproduced']):
            raise ValueError('mixed native prefix replay failed')
        count[0] += 1
        return mixed.native._make(mixed.native.GridSolveEvidence, **raw_fields)
    reproduced = mixed._select_hour(info, disclosure, before, expected_identity=expected_identity,
        selector=selector, solver_specification=solver_specification, budget=budget,
        expected_policy_identity=expected_policy_identity, power=power, _executor=native_replay)
    if encode(reproduced) != data:
        raise ValueError('mixed chain differs from canonical reconstruction')
    if implementation_identity() != expected_implementation:
        raise ValueError('mixed replay implementation drift')
    return dict(schema='draft_mixed_zero_face_replay_v1', archive_reproduced=True,
        reproduced_result_identity=reproduced.identity, native_stages_replayed=count[0],
        analytic_stages_recomputed=len(reproduced.stages)-count[0],
        solver_calls_by_replay=0, formal_result=False, security_certified=False,
        rigorous_exact_physical_feasibility=False, native_execution_authenticated=False), reproduced
