"""Closed, bounded initial-input transport; reconstructed inputs confer no authority."""
from dataclasses import dataclass, fields
from fractions import Fraction
from hashlib import sha256
from math import isfinite
from pathlib import Path

from . import scale_episode_zero_face as episode, scale_selector_zero_face_worker as selector
from . import boundary, capacity_policy, causal_policy, debt_cohorts, four_arm_replay, multiday

SCHEMA = 'draft_initial_mixed_selector_episode_transport_v1'
LIMIT = 16*1024**2


@dataclass(frozen=True)
class EpisodeInputs:
    reference_request: object
    arms: tuple
    hours: tuple
    budget: episode.EpisodeBudget
    resource_plan: episode.resources.EpisodeResourcePlan


CLASSES = tuple(cls for cls in selector.CLASSES if cls not in (
    selector.reference.ReferenceGridState, selector.actual.ActualDispatchState)) + (
    EpisodeInputs, episode.ArmSetup, episode.HourInput, episode.EpisodeBudget,
    episode.resources.EpisodeResourcePlan, episode.controller.process.TaskProcessBudget,
    episode.resources.contract.TaskEnvelope, episode.resources.contract.SerialResourceBudget,
    selector.scale.legacy.execution_workload.NormalWork, selector.scale.legacy.execution_workload.EpisodeWork,
    boundary.BoundaryAnchor, boundary.ContinuationHour, boundary.TemporalCarryState,
    capacity_policy.CapacityPolicy, capacity_policy.CapacityPolicyCursor,
    causal_policy.HourlyLimits, debt_cohorts.DebtLedger,
    four_arm_replay.ArmCursor, four_arm_replay.BoundTrack, multiday.JointReplayCursor,
    episode.tx.mapping_api.CommonRequestMapping, episode.tx.mapping_api.RequestSourceAudit,
)
TYPES = {cls.__name__: cls for cls in CLASSES}
if len(TYPES) != len(CLASSES):
    raise ValueError('ambiguous episode transport class names')


def implementation_identity():
    return episode.tx.legacy._identity(SCHEMA, episode._implementation(), selector.implementation_identity(),
        sha256(Path(__file__).read_bytes()).hexdigest())


def validate(inputs):
    if type(inputs) is not EpisodeInputs or type(inputs.reference_request) is not selector.store.MixedSelectorRequest:
        raise ValueError('typed initial episode inputs required')
    request = inputs.reference_request
    if type(request.before) is not selector.reference.ReferenceGridOrigin or request.power is not None:
        raise ValueError('initial reference origin required')
    selector.reference._physical(request.before)
    if type(inputs.budget) is not episode.EpisodeBudget:
        raise ValueError('typed episode budget required')
    inputs.budget.__post_init__()
    episode._fairness(inputs.arms)
    if (type(inputs.hours) is not tuple or not inputs.hours
            or any(type(h) is not episode.HourInput for h in inputs.hours)
            or request.info != inputs.hours[0].info or request.disclosure != inputs.hours[0].disclosure):
        raise ValueError('complete initial episode window required')
    episode.resources.bind_plan(inputs.resource_plan, inputs.budget, request, inputs.arms, inputs.hours)


def _transform(value, *, decoding):
    count = 0
    def visit(item, depth=0):
        nonlocal count
        count += 1
        if depth > 64 or count > 500000:
            raise ValueError('bounded episode input structure exceeded')
        if item is None or type(item) in (str, int, bool):
            return item
        if not decoding:
            if type(item) is float:
                if not isfinite(item): raise ValueError('finite episode float required')
                return ['float', item.hex()]
            if type(item) is Fraction:
                return ['fraction', [item.numerator, item.denominator]]
            if type(item) is tuple:
                return ['tuple', [visit(x, depth+1) for x in item]]
            if type(item) not in CLASSES:
                raise ValueError('episode input class not in fixed inventory')
            return [type(item).__name__, [[f.name, visit(getattr(item, f.name), depth+1)] for f in fields(item)]]
        if type(item) is not list or len(item) != 2 or type(item[0]) is not str:
            raise ValueError('canonical episode wire required')
        name, body = item
        if name == 'float':
            if type(body) is not str: raise ValueError('canonical float string required')
            result = float.fromhex(body)
            if not isfinite(result) or result.hex() != body: raise ValueError('canonical finite float required')
            return result
        if name == 'fraction':
            if (type(body) is not list or len(body) != 2
                    or any(type(x) is not int for x in body) or body[1] <= 0):
                raise ValueError('canonical rational pair required')
            result = Fraction(*body)
            if [result.numerator, result.denominator] != body: raise ValueError('reduced rational pair required')
            return result
        if name == 'tuple':
            if type(body) is not list: raise ValueError('tuple array required')
            return tuple(visit(x, depth+1) for x in body)
        if name not in TYPES or type(body) is not list:
            raise ValueError('episode input class not in fixed inventory')
        cls = TYPES[name]
        if (any(type(pair) is not list or len(pair) != 2 for pair in body)
                or [pair[0] for pair in body] != [f.name for f in fields(cls)]):
            raise ValueError('exact ordered episode input fields required')
        values = {key: visit(v, depth+1) for key, v in body}
        return cls(**values) if cls.__dataclass_params__.init else selector.step._owned(cls, **values)
    return visit(value)


def export_inputs(inputs):
    wire = _transform(inputs, decoding=False)
    validate(inputs)
    raw = selector.store._bytes(dict(schema=SCHEMA, inputs=wire))
    if len(raw) > LIMIT: raise ValueError('episode input byte limit exceeded')
    return raw


def decode_inputs(raw):
    if type(raw) is not bytes or len(raw) > LIMIT:
        raise ValueError('bounded episode input bytes required')
    packet = selector.store._decoded(raw)
    if type(packet) is not dict or set(packet) != {'schema', 'inputs'} or packet['schema'] != SCHEMA:
        raise ValueError('exact episode input packet required')
    result = _transform(packet['inputs'], decoding=True)
    if export_inputs(result) != raw: raise ValueError('episode input roundtrip mismatch')
    return result


def read_inputs(path, *, expected_sha256, max_request_bytes):
    selector.scale.actual._hash(expected_sha256)
    if type(max_request_bytes) is not int or not 0 < max_request_bytes <= LIMIT:
        raise ValueError('explicit bounded episode input size required')
    path = selector.store.local._path(path)
    identity = selector.store.local._file_identity(path)
    with path.open('rb') as stream: raw = stream.read(max_request_bytes+1)
    if len(raw) > max_request_bytes or sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('episode input size/hash mismatch')
    if selector.store.local._file_identity(path) != identity:
        raise ValueError('episode input changed during read')
    return decode_inputs(raw)
