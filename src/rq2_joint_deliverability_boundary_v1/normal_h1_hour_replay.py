"""Independent full-hour, zero-solver streaming numerical replay candidate."""
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path

from . import normal_h1_replay as old
from . import normal_h1_resource_shape as guard

current,native=old.current,old.native
SCHEMA='h1_full_hour_streaming_replay_development_v1'


@dataclass(frozen=True)
class H1HourReplayLimits:
    max_stages: int
    max_variables: int
    max_constraints: int

    def __post_init__(self):
        for value in asdict(self).values():
            if type(value) is not int or value<1:
                raise ValueError('positive exact replay-only size limits required')
        if self.max_stages>232 or max(self.max_variables,self.max_constraints)>1000000:
            raise ValueError('bounded full-hour replay size limits required')


def implementation_identity():
    return current.source._digest(SCHEMA,old.implementation_identity(),
        sha256(Path(guard.__file__).read_bytes()).hexdigest(),
        sha256(Path(__file__).read_bytes()).hexdigest())


def request_key(packet,specification,limits):
    if type(limits) is not H1HourReplayLimits:
        raise ValueError('exact full-hour replay-only limits required')
    limits.__post_init__()
    current.source.validate_current(packet)
    native.capture.provenance.adapter.validate_spec(specification)
    order=native.model_api.stage_order(packet.inputs)
    if len(order)>limits.max_stages:
        raise ValueError('full-hour stage count exceeds replay limits')
    return current.source._digest(SCHEMA,packet.input_identity,packet.relative_hour,
        asdict(specification),asdict(limits),implementation_identity())


@dataclass(frozen=True,init=False)
class H1HourReplayedProjection(current.source._Owned):
    request_key: str
    before_identity: str
    projection_identity: str
    projection_payload: bytes
    canonical_locks: tuple
    report_sha256: tuple
    stage_identities: tuple
    numeric_sha256: tuple
    replay_implementation: str
    solver_calls_by_replay: int
    numerical_chain_recomputed: bool
    native_execution_authenticated: bool
    exact_mathematical_certificate: bool
    published: bool
    formal_result: bool


class H1ReportAuditRejected(ValueError):
    """Raw report audit failure only; not model/resource/implementation failure."""


def _audit_stage(packet,specification,limits,index,locks,raw):
    """Recompute one stage; callers own ordering and persistence before lock advance."""
    request_key(packet,specification,limits)
    order=native.model_api.stage_order(packet.inputs)
    if type(index) is not int or not 0<=index<len(order) or type(locks) is not tuple or len(locks)!=index:
        raise ValueError('exact stage index and complete prior lock prefix required')
    objective=order[index]
    runner_pin=native.capture.implementation_identity()
    collector_pin=sha256(Path(native.capture.provenance.__file__).read_bytes()).hexdigest()
    adapter_pin=native.capture.provenance.adapter.implementation_identity()
    req = native.model_api.H1StageRequest(packet.inputs, locks)
    stage_pin = native.model_api.h1_stage_identity(req)
    model = native.model_api.build_h1_stage_model(req, expected_identity=stage_pin)
    scale = native.capture.audit.model_scale(model)
    if scale.variables > limits.max_variables or scale.constraints > limits.max_constraints:
        raise ValueError("hour replay model exceeds declared size limits")
    try:
        report = old._decode(raw, native.MAX_PAYLOAD_BYTES)
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
        return dict(lock=lock,assignment=assignment,stage_identity=stage_pin,
            native_sha256=sha256(raw).hexdigest(),numeric_sha256=sha256(native.capture.encode(numeric)).hexdigest())
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        raise H1ReportAuditRejected(f'H1 hour archived stage {index} rejected: {error}') from error


def _projection(packet,locks,assignment,hashes,stage_pins,numeric_pins,*,key,implementation):
    transition=current.source.replay_feasible_boundary(packet,assignment,expected_input_identity=packet.input_identity)
    after=transition.candidate_boundary
    projection_pin=current.source._digest('h1_normal_decision_projection_v1',after.network_identity,
        after.completed_hours,after.units,locks)
    payload=native.capture.encode(dict(network_identity=after.network_identity,completed_hours=after.completed_hours,
        units=[[uid,on,float(power).hex(),age] for uid,on,power,age in after.units],
        canonical_locks=[v.hex() for v in locks]))
    return current.source._owned(H1HourReplayedProjection,request_key=key,before_identity=transition.before_identity,
        projection_identity=projection_pin,projection_payload=payload,canonical_locks=locks,
        report_sha256=tuple(hashes),stage_identities=tuple(stage_pins),numeric_sha256=tuple(numeric_pins),
        replay_implementation=implementation,solver_calls_by_replay=0,numerical_chain_recomputed=True,
        native_execution_authenticated=False,exact_mathematical_certificate=False,published=False,formal_result=False)


def replay_stream(packet,specification,limits,reports,*,expected_key):
    """Forbid known solver entries even inside a caller-provided report iterator."""
    with guard.solver_calls_forbidden():
        return _replay_stream(packet,specification,limits,reports,expected_key=expected_key)


def _replay_stream(packet,specification,limits,reports,*,expected_key):
    """Consume one raw report at a time, retain no tuple of full reports."""
    native._pin(expected_key)
    if request_key(packet,specification,limits)!=expected_key:
        raise ValueError('full-hour replay request mismatch')
    own=implementation_identity()
    order=native.model_api.stage_order(packet.inputs)
    locks=()
    hashes,stage_pins,numeric_pins=[],[],[]
    assignment=None
    for index,raw in enumerate(reports):
        if index>=len(order): raise ValueError('extra full-hour report')
        stage=_audit_stage(packet,specification,limits,index,locks,raw)
        locks=(*locks,stage['lock'])
        assignment=stage['assignment']
        hashes.append(stage['native_sha256'])
        stage_pins.append(stage['stage_identity'])
        numeric_pins.append(stage['numeric_sha256'])
    if len(locks)!=len(order): raise ValueError('incomplete full-hour report prefix')
    result=_projection(packet,locks,assignment,hashes,stage_pins,numeric_pins,key=expected_key,implementation=own)
    if request_key(packet,specification,limits)!=expected_key or implementation_identity()!=own:
        raise ValueError('full-hour replay input or implementation drift')
    return result
