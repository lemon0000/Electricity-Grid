"""Zero-solver reconstruction of full H1 numerical chains and archive bytes.

Stored native channels are evidence data, not authenticated historical execution.
No executable boundary, published decision or formal certificate is restored.
"""
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

from . import normal_h1_current_solve as current
from . import normal_h1_short_solve as native


SCHEMA = 'h1_current_numerical_archive_v1'
MAX_ARCHIVE_BYTES = 32 * 1024**2


def _decode(raw, maximum):
    if type(raw) is not bytes or not 0 < len(raw) <= maximum:
        raise ValueError('bounded immutable canonical JSON bytes required')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    try:
        value = json.loads(raw, object_pairs_hook=pairs,
            parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite JSON constant')))
        if native.capture.encode(value) != raw:
            raise ValueError('noncanonical JSON bytes')
        return value
    except (TypeError, ValueError, RecursionError) as error:
        raise ValueError('invalid canonical archive JSON: '+str(error)) from error


def implementation_identity():
    return current.source._digest(SCHEMA, MAX_ARCHIVE_BYTES, native.implementation_identity(),
        tuple((m.__name__, sha256(Path(m.__file__).read_bytes()).hexdigest())
              for m in (current, current.source)), sha256(Path(__file__).read_bytes()).hexdigest())


@dataclass(frozen=True, init=False)
class H1ReplayedProjection(current.source._Owned):
    request_key: str
    before_identity: str
    chain_identity: str
    projection_identity: str
    projection_payload: bytes
    report_sha256: tuple[str, ...]
    stage_audits: tuple
    numeric_predicate_payloads: tuple[bytes, ...]
    canonical_locks: tuple[float, ...]
    replay_implementation: str
    solver_calls_by_replay: int
    numerical_chain_recomputed: bool
    native_execution_authenticated: bool
    published: bool
    formal_result: bool


def replay_reports(packet, specification, budget, reports, *, expected_key):
    """Rebuild every stage and derive every RHS; no caller-supplied lock trusted."""
    if (type(reports) is not tuple or not 1 <= len(reports) <= 20
            or any(type(raw) is not bytes or not 0 < len(raw) <= native.MAX_PAYLOAD_BYTES for raw in reports)
            or sum(map(len, reports)) > MAX_ARCHIVE_BYTES):
        raise ValueError('H1 report tuple exceeds aggregate byte/stage budget')
    native._pin(expected_key)
    if current.request_key(packet, specification, budget) != expected_key:
        raise ValueError('H1 replay request key mismatch')
    order = native.model_api.stage_order(packet.inputs)
    if type(reports) is not tuple or len(reports) != len(order):
        raise ValueError('one complete ordered native report tuple required')
    own_pin = implementation_identity()
    chain_pin = native.chain_identity(packet.inputs, specification, budget)
    runner_pin = native.capture.implementation_identity()
    collector_pin = sha256(Path(native.capture.provenance.__file__).read_bytes()).hexdigest()
    adapter_pin = native.capture.provenance.adapter.implementation_identity()
    locks, audits, hashes, numeric_payloads = (), [], [], []
    assignment = None
    for index, (objective, raw) in enumerate(zip(order, reports, strict=True)):
        report = _decode(raw, native.MAX_PAYLOAD_BYTES)
        req = native.model_api.H1StageRequest(packet.inputs, locks)
        stage_pin = native.model_api.h1_stage_identity(req)
        model = native.model_api.build_h1_stage_model(req, expected_identity=stage_pin)
        scale = native.capture.audit.model_scale(model)
        try:
            if (report['schema'] != 'rq2_objective_provenance_owned_solve_v1'
                    or type(report['solver_calls']) is not int or report['solver_calls'] != 1
                    or type(report['variables']) is not int or report['variables'] != scale.variables
                    or type(report['constraints']) is not int or report['constraints'] != scale.constraints
                    or report['implementation_identity'] != runner_pin
                    or report['model_structure_identity'] != native.capture.audit._structure(model)
                    or native.capture.encode(report['solver_options']) != native.capture.encode(
                        native.capture.audit.solver_options(specification))
                    or any(report[k] is not False for k in ('formal_result', 'normal_accepted', 'optimality_certified'))
                    or report['provenance'] is None or report['assignment'] is None):
                raise ValueError('H1 archived report binding mismatch')
            for name in ('native_status', 'native_solution_count', 'pyomo_status', 'pyomo_termination'):
                if (type(report[name]) is not type(report['provenance'][name])
                        or report[name] != report['provenance'][name]):
                    raise ValueError('H1 archived status channel mismatch')
            native.replay.verify_numerical(model, report)
            numeric = native.predicate.evaluate(report, expected_implementation=runner_pin,
                expected_collector=collector_pin, expected_adapter=adapter_pin)
            assignment = {name: float.fromhex(value) for name, value in report['assignment']}
            audit = native.model_api.audit_h1_assignment(req, assignment, expected_identity=stage_pin)
            if (not numeric['candidate_numeric_predicate_passed'] or audit.errors
                    or audit.canonical_objective.hex() != report['provenance']['canonical_objective_hex']):
                raise ValueError('H1 archived numerical/assignment predicate rejected')
            lock = audit.canonical_objective
            if objective[0] == 'commitment':
                lock = float(round(lock))
                if lock not in (0., 1.) or abs(lock-audit.canonical_objective) > 1e-9:
                    raise ValueError('H1 archived commitment is not audited binary')
            locks = (*locks, lock)
            audits.append(audit)
            numeric_payloads.append(native.capture.encode(numeric))
            hashes.append(sha256(raw).hexdigest())
        except (KeyError, TypeError, ValueError, OverflowError) as error:
            raise ValueError(f'H1 archived stage {index} rejected: {error}') from error
    transition = current.source.replay_feasible_boundary(packet, assignment,
        expected_input_identity=packet.input_identity)
    after = transition.candidate_boundary
    projection_pin = current.source._digest('h1_normal_decision_projection_v1', after.network_identity,
                                            after.completed_hours, after.units, locks)
    # This is a diagnostic value projection, not an H1NormalBoundary constructor.
    projection_raw = native.capture.encode(dict(network_identity=after.network_identity,
        completed_hours=after.completed_hours,
        units=[[uid, on, float(power).hex(), age] for uid, on, power, age in after.units],
        canonical_locks=[value.hex() for value in locks]))
    if (current.request_key(packet, specification, budget) != expected_key
            or implementation_identity() != own_pin):
        raise ValueError('H1 replay input or implementation drift')
    return current.source._owned(H1ReplayedProjection, request_key=expected_key,
        before_identity=transition.before_identity, chain_identity=chain_pin,
        projection_identity=projection_pin, projection_payload=projection_raw,
        report_sha256=tuple(hashes), stage_audits=tuple(audits), canonical_locks=locks,
        numeric_predicate_payloads=tuple(numeric_payloads),
        replay_implementation=own_pin, solver_calls_by_replay=0, numerical_chain_recomputed=True,
        native_execution_authenticated=False, published=False, formal_result=False)


def archive_current(packet, specification, budget, result):
    """Preserve raw reports and compare an owned current decision to reconstruction."""
    if (type(result) is not current.H1CurrentSolve or result.current_decision_accepted is not True
            or result.errors or type(result.decision) is not current.H1NormalDecision
            or type(result.evidence) is not native.H1ChainEvidence
            or result.evidence.numerical_chain_accepted is not True or result.evidence.errors
            or any(getattr(result.evidence, name) is not False for name in (
                'exact_mathematical_certificate', 'formal_result', 'hard_process_resources_verified'))
            or type(result.evidence.stages) is not tuple or not 1 <= len(result.evidence.stages) <= 20):
        raise ValueError('complete accepted owned current result required')
    reports = tuple(stage.native_payload for stage in result.evidence.stages)
    replayed = replay_reports(packet, specification, budget, reports, expected_key=result.request_key)
    for index, stage in enumerate(result.evidence.stages):
        if (type(stage) is not native.H1StageEvidence or stage.accepted is not True or stage.errors
                or type(stage.index) is not int or stage.index != index
                or stage.objective != native.model_api.stage_order(packet.inputs)[index]
                or stage.stage_identity != replayed.stage_audits[index].stage_identity
                or stage.assignment_audit != replayed.stage_audits[index]
                or stage.numeric_predicate_payload != replayed.numeric_predicate_payloads[index]
                or stage.prior_locks != replayed.canonical_locks[:index]
                or stage.lock_value != replayed.canonical_locks[index]):
            raise ValueError('owned H1 stage metadata differs from reconstruction')
    decision, boundary = result.decision, result.decision.candidate_boundary
    rebuilt = native.capture.encode(dict(network_identity=boundary.network_identity,
        completed_hours=boundary.completed_hours,
        units=[[uid, on, float(power).hex(), age] for uid, on, power, age in boundary.units],
        canonical_locks=[value.hex() for value in decision.canonical_locks]))
    if (decision.request_key != replayed.request_key or decision.before_identity != replayed.before_identity
            or decision.projection_identity != replayed.projection_identity
            or rebuilt != replayed.projection_payload or decision.published is not False
            or result.evidence.chain_identity != replayed.chain_identity
            or result.evidence.solver_calls != len(reports) or result.evidence.collector_attempts != len(reports)):
        raise ValueError('owned H1 result differs from full numerical reconstruction')
    raw = native.capture.encode(dict(schema=SCHEMA, request_key=replayed.request_key,
        before_identity=replayed.before_identity, chain_identity=replayed.chain_identity,
        projection_identity=replayed.projection_identity,
        projection=json.loads(replayed.projection_payload), report_sha256=replayed.report_sha256,
        reports=[raw.decode('ascii') for raw in reports], replay_implementation=replayed.replay_implementation,
        native_execution_authenticated=False, published=False, formal_result=False))
    if len(raw) > MAX_ARCHIVE_BYTES:
        raise ValueError('H1 archive exceeds development byte budget')
    return raw


def replay_archive(packet, specification, budget, archive, *, expected_key, expected_archive_sha256):
    """Check externally retained bytes pin plus every stage; no archive authority."""
    native._pin(expected_archive_sha256)
    if type(archive) is not bytes or sha256(archive).hexdigest() != expected_archive_sha256:
        raise ValueError('H1 archive SHA256 mismatch')
    item = _decode(archive, MAX_ARCHIVE_BYTES)
    keys = {'schema', 'request_key', 'before_identity', 'chain_identity', 'projection_identity',
            'projection', 'report_sha256', 'reports', 'replay_implementation',
            'native_execution_authenticated', 'published', 'formal_result'}
    if (type(item) is not dict or set(item) != keys or item['schema'] != SCHEMA
            or item['request_key'] != expected_key
            or any(item[k] is not False for k in ('native_execution_authenticated', 'published', 'formal_result'))
            or type(item['reports']) is not list or any(type(raw) is not str for raw in item['reports'])):
        raise ValueError('H1 archive schema or authority mismatch')
    result = replay_reports(packet, specification, budget,
        tuple(raw.encode('ascii') for raw in item['reports']), expected_key=expected_key)
    for name in ('before_identity', 'chain_identity', 'projection_identity', 'replay_implementation'):
        if item[name] != getattr(result, name):
            raise ValueError('H1 archive derived field mismatch: '+name)
    if (native.capture.encode(item['projection']) != result.projection_payload
            or type(item['report_sha256']) is not list or tuple(item['report_sha256']) != result.report_sha256):
        raise ValueError('H1 archive projection/report hash mismatch')
    return result
