"""Current-row numerical H1 decisions, without persistence or publication."""
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

from . import normal_h1_source as source
from . import normal_h1_short_solve as native


@dataclass(frozen=True, init=False)
class H1NormalDecision(source._Owned):
    request_key: str
    before_identity: str
    candidate_boundary: source.H1NormalBoundary
    canonical_locks: tuple[float, ...]
    projection_identity: str
    published: bool


@dataclass(frozen=True, init=False)
class H1CurrentSolve(source._Owned):
    request_key: str
    evidence: native.H1ChainEvidence
    decision: H1NormalDecision | None
    current_decision_accepted: bool
    errors: tuple[str, ...]


def request_key(packet, specification, budget):
    return source._digest('h1_current_numerical_decision_v1',
        source.causal_key(packet, specification, budget), sha256(Path(__file__).read_bytes()).hexdigest())


def solve_current(packet, specification, budget, *, expected_key):
    """Own the whole lex execution before deriving a candidate next boundary.

    Only the returned public projection may later enter a common-prefix store.
    The store must separately enforce same-key agreement and atomic publication;
    this development adapter does not authorize any formal state advancement.
    """
    if type(expected_key) is not str or request_key(packet, specification, budget) != expected_key:
        raise ValueError('H1 current request key mismatch')
    result = native.run_h1_chain(packet.inputs, specification, budget,
        expected_identity=native.chain_identity(packet.inputs, specification, budget))
    decision = None
    if result.numerical_chain_accepted:
        try:
            if request_key(packet, specification, budget) != expected_key:
                raise ValueError('H1 current input or implementation changed during solve')
        except Exception as error:
            return source._owned(H1CurrentSolve, request_key=expected_key, evidence=result, decision=None,
                current_decision_accepted=False, errors=('current_input_rejected: '+str(error),))
        assignment = {name: float.fromhex(number)
                      for name, number in json.loads(result.stages[-1].native_payload)['assignment']}
        try:
            transition = source.replay_feasible_boundary(packet, assignment,
                expected_input_identity=packet.input_identity)
        except Exception as error:
            return source._owned(H1CurrentSolve, request_key=expected_key, evidence=result, decision=None,
                current_decision_accepted=False, errors=('current_boundary_rejected: '+str(error),))
        feasible = transition.candidate_boundary
        after = source._owned(source.H1NormalBoundary, network_identity=feasible.network_identity,
            completed_hours=feasible.completed_hours, units=feasible.units,
            evidence_role='numerical_lex_candidate')
        locks = tuple(stage.lock_value for stage in result.stages)
        projection = source._digest('h1_normal_decision_projection_v1', after.network_identity,
                                    after.completed_hours, after.units, locks)
        decision = source._owned(H1NormalDecision, request_key=expected_key,
            before_identity=transition.before_identity, candidate_boundary=after,
            canonical_locks=locks, projection_identity=projection, published=False)
    return source._owned(H1CurrentSolve, request_key=expected_key, evidence=result, decision=decision,
        current_decision_accepted=decision is not None, errors=result.errors)
