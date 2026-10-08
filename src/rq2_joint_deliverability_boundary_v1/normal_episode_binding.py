"""Bind independently declared episode inputs to an accepted numerical normal.

This audit-side bridge performs no execution and grants no run authority.
Current conditions and reference/actual origins remain mechanism declarations.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from fractions import Fraction as Q
from contextlib import contextmanager

from . import normal_numerical_execution_v2 as normal
from . import scale_episode_zero_face_transport as transport
from . import event_disclosure as disclosure
from . import reference_grid, source_pair

episode = transport.episode
mapping = episode.tx.mapping_api
information = normal.projection.information
SCHEMA = 'draft_normal_bound_mixed_episode_inputs_v1'


def implementation_identity():
    return normal.kernel._digest(SCHEMA, normal.implementation_identity(),
        transport.implementation_identity(),
        tuple((m.__name__, sha256(Path(m.__file__).read_bytes()).hexdigest())
            for m in (mapping, information, disclosure, reference_grid, source_pair)),
        sha256(Path(__file__).read_bytes()).hexdigest())


def binding_identity(request, *, normal_sha256, episode_sha256, max_normal_bytes, max_episode_bytes):
    request_pin = normal.request_identity(request)
    if type(request.resource_plan) is not normal.budgets.NormalResourcePlan:
        raise ValueError('single-normal diagnostic cannot authorize an episode dependency')
    for pin in (normal_sha256, episode_sha256): normal.kernel._pin(pin)
    if (type(max_normal_bytes) is not int or not 0 < max_normal_bytes <= 64*1024**2
            or type(max_episode_bytes) is not int or not 0 < max_episode_bytes <= transport.LIMIT):
        raise ValueError('explicit bounded normal and episode archives required')
    return normal.kernel._digest(SCHEMA, request_pin, normal_sha256,
        episode_sha256, max_normal_bytes, max_episode_bytes, implementation_identity())


def _same(actual, expected, message):
    if normal.replay._bytes(normal.kernel._encode(actual)) != normal.replay._bytes(normal.kernel._encode(expected)):
        raise ValueError(message)


def _origins(packet):
    first, reference = packet.hours[0], packet.reference_request.before
    ref = reference_grid
    physical = ref._physical(reference)
    state = physical.disclosure
    active = None if state.active is None else state.active.component
    initial = disclosure.initialize_disclosure(state.protocol, source_hour=state.source_hour,
        active_component=active)
    _same(state, initial, 'reference origin disclosure is not an initial declaration')
    expected = ref.initialize_reference_origin(first.info, initial,
        reference_protocol=reference.protocol, grid_protocol=physical.protocol,
        generation_mw=physical.generation_mw, base_availability=physical.base_availability)
    _same(reference, expected, 'reference origin differs from rebuilt normal-plan binding')
    request = packet.reference_request
    if episode.tx.scale._admit(request.selection_spec, request.solver_specification, request.budget,
            len(first.info.network.units)+2) is not episode.tx.scale.reference:
        raise ValueError('reference selector role required')
    if (request.expected_identity != ref.reference_input_identity(first.info, first.disclosure, reference)
            or request.expected_policy_identity != episode.tx.scale.policy_identity(
                request.selection_spec, request.solver_specification, request.budget)):
        raise ValueError('reference request input or policy identity mismatch')
    for arm in packet.arms:
        actual = episode.tx.scale.actual._physical(arm.grid)
        _same(actual.disclosure, initial, 'actual/reference origin disclosure mismatch')
        expected = episode.tx.scale.initialize_actual_origin(first.info, initial,
            grid_protocol=actual.protocol, generation_mw=actual.generation_mw,
            base_availability=actual.base_availability, selector=arm.selector,
            solver_specification=arm.specification, budget=arm.budget,
            expected_policy_identity=episode.tx.scale.policy_identity(arm.selector, arm.specification, arm.budget))
        _same(arm.grid, expected, 'actual origin differs from rebuilt normal-plan binding')
        anchor = arm.business.execution.tracks[0][1].physical.anchor
        episode.tx._validate_next_identity(anchor, first.source_hour)
        if actual.source_hour != anchor.power_source_hour:
            raise ValueError('business and physical origin clock mismatch')
    return initial


@contextmanager
def solver_free():
    targets = ((episode.controller, 'supervise_selector'),
        (episode.controller.process, 'normal_task_child'),
        (episode.DevelopmentMixedSelectorEpisode, 'advance'))
    originals = [(obj, name, getattr(obj, name)) for obj, name in targets]
    def forbidden(*a, **k): raise RuntimeError('normal episode binding execution forbidden')
    with normal.solver_free():
        try:
            for obj, name in targets: setattr(obj, name, forbidden)
            yield
        finally:
            for obj, name, original in originals: setattr(obj, name, original)


def bind_episode(normal_data, request, episode_data, *, normal_sha256, episode_sha256,
                 max_normal_bytes, max_episode_bytes, expected_request_identity, expected_binding_identity):
    """Return (source-binding report, validated complete EpisodeInputs).

    The caller must persist and recheck this binding at its execution boundary;
    a bare episode transport packet still carries no normal-source authority.
    """
    request = deepcopy(request)
    normal.kernel._pin(expected_request_identity)
    normal.kernel._pin(expected_binding_identity)
    args = dict(normal_sha256=normal_sha256, episode_sha256=episode_sha256,
        max_normal_bytes=max_normal_bytes, max_episode_bytes=max_episode_bytes)
    def check():
        if (normal.request_identity(request) != expected_request_identity
                or binding_identity(request, **args) != expected_binding_identity):
            raise ValueError('normal/episode external binding drift')
    check()
    if (type(episode_data) is not bytes or len(episode_data) > max_episode_bytes
            or sha256(episode_data).hexdigest() != episode_sha256):
        raise ValueError('bounded externally pinned episode bytes required')
    declarations = normal.legacy._declarations(request.normal)
    with solver_free():
        audit, prepared = normal.replay_information(normal_data, request,
            expected_sha256=normal_sha256, expected_request_identity=expected_request_identity,
            max_record_bytes=max_normal_bytes)
        if not audit['accepted_record_reproduced'] or prepared is None:
            raise ValueError('accepted complete numerical normal plan required')
        inputs, before = normal._snapshot(request, expected_request_identity)
        packet = transport.decode_inputs(episode_data)
        if type(request.resource_plan) is not normal.budgets.NormalResourcePlan:
            raise ValueError('single-normal diagnostic cannot authorize an episode dependency')
        for name in ('normals', 'episodes', 'envelopes', 'serial_budget'):
            _same(getattr(packet.resource_plan, name), getattr(request.resource_plan, name),
                'normal and episode complete resource plans differ: '+name)
        task = next(t for t in packet.resource_plan.episodes if t.task_id == packet.reference_request.budget.task_id)
        if task.normal_task_id != request.budget.normal.task_id:
            raise ValueError('episode references a different normal task')
        hours = tuple(h.info.current.source_hour for h in packet.hours)
        if (any(b != a+1 for a,b in zip(hours, hours[1:]))
                or not set(hours).issubset(inputs.source_hours)):
            raise ValueError('episode requires contiguous normal-covered hours')
        declaration = source_pair.PairDeclaration(**before['declaration'])
        pair = source_pair.prepare_source_pair(declaration, config_path=request.source.config_path)
        if (pair['pair_identity'] != request.source.expected_pair_identity
                or pair['status'] != 'staged' or type(pair['hours']) is not list
                or tuple(h['power_source_hour'] for h in pair['hours']) != inputs.source_hours):
            raise ValueError('complete independently rebuilt source pair required')
        paired_mapping = mapping.CommonRequestMapping(**pair['mapping'])
        paired_hours = {row['power_source_hour']: transport.boundary.ContinuationHour(**row)
            for row in pair['hours']}
        for hour in packet.hours:
            _same(hour.source_hour, paired_hours[hour.info.current.source_hour],
                'business hour differs from independently rebuilt source pair')
            _same(hour.mapping, paired_mapping, 'business mapping differs from source pair')
            _same(hour.mapping, packet.hours[0].mapping, 'common request mapping changed within episode')
            current = information.current_grid_information(prepared, hour.info.current,
                expected_audit_identity=prepared.audit_identity)
            _same(hour.info, current, 'hour information differs from accepted normal plan')
            source_audit = mapping.bind_request_source(inputs, prepared, current,
                expected_normal_identity=request.source.expected_input_identity,
                expected_prepared_identity=prepared.audit_identity)
            _same(hour.source_audit, source_audit, 'episode source audit differs from rebuilt source')
            hour.mapping.__post_init__()
            hour.source_hour.__post_init__()
            source = hour.source_hour
            if (type(hour.mapping) is not mapping.CommonRequestMapping
                    or (source.split, source.power_outage_seed, source.power_source_hour)
                       != (source_audit.split, source_audit.outage_seed, current.current.source_hour)
                    or (source.arm_id, source.track_id) != (episode.tx.JOINT, 'shared')
                    or source.grid_request != 0
                    or source.workload_normalization_sha256 != hour.mapping.workload_normalization_sha256
                    or Q(str(source.workload_occupancy))*Q(hour.mapping.normalized_unit_mw)
                       != Q(str(current.current.dc_baseline_mw))):
                raise ValueError('common business/current source mapping mismatch')
        previous = _origins(packet)
        previous_source = None
        for hour in packet.hours:
            expected = disclosure.disclose_current(previous, hour.disclosure.report)
            _same(hour.disclosure, expected, 'episode disclosure chain mismatch')
            if expected.after.source_hour != hour.info.current.source_hour:
                raise ValueError('disclosure and current information clock mismatch')
            if previous_source is not None:
                episode.tx._validate_next_identity(episode.tx.legacy._anchor(previous_source), hour.source_hour)
            previous, previous_source = expected.after, hour.source_hour
        _, after = normal._snapshot(request, expected_request_identity)
        _same(before, after, 'normal source changed during episode binding')
        if declarations != normal.legacy._declarations(request.normal):
            raise ValueError('normal declarations changed during episode binding')
        check()
    report = dict(schema=SCHEMA, binding_identity=expected_binding_identity,
        normal_sha256=normal_sha256, episode_sha256=episode_sha256,
        normal_request_identity=expected_request_identity, normal_input_identity=request.source.expected_input_identity,
        prepared_information_identity=prepared.audit_identity, allowed_plan_identity=prepared.allowed_plan_identity,
        source_hours=list(hours), complete_resource_plan_equal=True, solver_calls_by_binding=0,
        business_pair_correspondence_verified=True, pair_identity=pair['pair_identity'],
        origins_role='independently_declared_mechanism_assumptions', current_conditions_role='mechanism_assumption',
        observed_power_mapping=False, registered_coupling=False, causal_certificate=None,
        capacity_certificate=None, native_execution_authenticated=False, whole_task_resources_verified=False,
        security_certified=False, rigorous_exact_optimality_certified=False, formal_result=False,
        executable_resume_available=False)
    return report, packet
