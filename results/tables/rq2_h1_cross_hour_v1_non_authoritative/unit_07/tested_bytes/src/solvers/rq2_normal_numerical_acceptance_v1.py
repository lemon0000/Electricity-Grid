"""Authorized numerical normal criterion, including a fresh chronology witness.

This successor preserves original evidence and never issues an exact, security,
or formal-experiment certificate. Frozen-package review is an external gate.
"""
from hashlib import sha256
from pathlib import Path

from . import rq2_normal_numerical_candidate_v1 as predicate
from ..rq2_joint_deliverability_boundary_v1 import continuous_grid_normal_stream_ordered as stream
from ..rq2_joint_deliverability_boundary_v1 import scale_normal_native as native
from experiments.replay_rq2_h25_native_provenance_v1 import verify_numerical
from experiments import replay_rq2_h25_native_provenance_v1 as replay_helper


def assess_assignment(inputs, numerical, *, expected_input_identity,
                      expected_runner_identity, expected_collector_sha256,
                      expected_adapter_identity):
    """Pure audit after owned source/process/schema validation by the caller.

    The supplied model is reconstructed from inputs; no solver is invoked.
    An externally frozen verifier must bind the source and execution archive.
    """
    implementation = stream.implementation_identity()
    model=stream.build_continuous_normal_model(inputs,expected_identity=expected_input_identity,
        expected_implementation_identity=implementation)
    scale=native.model_scale(model)
    if (scale.variables!=numerical['variables'] or scale.constraints!=numerical['constraints']
            or native._structure(model)!=numerical['model_structure_identity']):
        raise ValueError('normal scale/structure mismatch')
    recomputed=verify_numerical(model,numerical)
    numeric=predicate.evaluate(numerical,expected_implementation=expected_runner_identity,
        expected_collector=expected_collector_sha256,expected_adapter=expected_adapter_identity)
    assignment={name:float.fromhex(number) for name,number in numerical['assignment']}
    witness=stream.audit_normal_assignment(inputs,assignment,expected_identity=expected_input_identity,
        expected_implementation_identity=implementation)
    accepted=bool(numeric['candidate_numeric_predicate_passed'] and not witness.errors
        and witness.terminal_carry is not None)
    if stream.implementation_identity()!=implementation:
        raise ValueError('normal model implementation drift')
    return dict(schema='rq2_normal_numerical_acceptance_successor_v1',
        scope='numerical_normal_assignment_and_chronology_only',
        initial_history_role=inputs.carry.initial_history_role,
        input_identity=expected_input_identity,normal_model_implementation=implementation,
        verifier_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        predicate_sha256=sha256(Path(predicate.__file__).read_bytes()).hexdigest(),
        replay_helper_sha256=sha256(Path(replay_helper.__file__).read_bytes()).hexdigest(),
        numerical_solver_optimality_accepted=accepted,
        checks=numeric['checks'],raw_relative_gap_exact=numeric['raw_relative_gap_exact'],
        canonical_assignment_recomputed=recomputed['canonical_assignment_recomputed'],
        archived_objective_channel_relations_recomputed=recomputed['objective_channels_recomputed'],
        normal_witness=stream.legacy._encode(witness),normal_witness_identity=stream._digest(witness),
        normal_witness_errors=list(witness.errors),solver_calls_by_verifier=0,
        rigorous_exact_optimality_certified=False,security_certified=False,
        native_execution_authenticated=False,formal_result=False,
        whole_task_resources_verified=False)
