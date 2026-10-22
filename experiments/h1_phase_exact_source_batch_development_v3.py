"""Two independent single-traversal Readers for accepted N prefixes.

No internal cache survives a call. The owner keeps
the returned currents private to one complete scientific replay. Not authority.
"""
from pathlib import Path
from dataclasses import dataclass
import json
import sys
from types import FunctionType

from experiments import h1_phase_exact_source_current_development_v1 as prior
from experiments import h1_phase_historical_batch_development_v3 as historical

SCHEMA = 'h1_phase_exact_source_batch_development_v3'
MAX_CURRENT_BYTES = 64*1024**2
io, source, registry, physical = prior.io, prior.source, prior.registry, prior.physical
_REPLAY_PREFIXES = historical.replay_prefixes


@dataclass(frozen=True)
class CurrentBatch:
    """Call-local replay data and cost observations; never a capability."""
    currents: dict
    observations: tuple


def _check_reader_entry():
    if any(_LOCAL_NAMESPACE.get(name) is not value for name, value in _LOCAL_BINDINGS):
        raise ValueError('single-traversal batch local dependency alias changed')
    for obj, name, function, before in _ENTRY_FUNCTIONS:
        if getattr(obj, name) is not function:
            raise ValueError('single-traversal batch historical entry changed')
        after = (function.__code__, function.__globals__, function.__defaults__, repr(function.__defaults__),
            function.__kwdefaults__, repr(function.__kwdefaults__), function.__closure__,
            tuple(cell.cell_contents for cell in function.__closure__ or ()))
        if (any(after[i] is not before[i] for i in (0, 1, 2, 4, 6))
                or any(after[i] != before[i] for i in (3, 5))
                or any(a is not b for a, b in zip(after[7], before[7]))):
            raise ValueError('single-traversal batch historical callable changed')
    historical._CHECK_DEPENDENCIES()


def implementation_identity():
    return io.digest(io.encode([SCHEMA, prior.implementation_identity(), historical.implementation_identity(),
                                io.digest(Path(__file__).read_bytes())]))


def _validate_reader_metric(metric, completed_hours):
    inventory=dict(historical._RUNTIME_SEAL[5])
    if (type(metric) is not dict or type(metric.get('parent_inspect_traversals')) is not int
                or metric['parent_inspect_traversals'] != 1
                or metric.get('constructor_inspection_reused') is not True
                or metric.get('normal_model_dependency_bookends_verified') is not True
                or type(metric.get('completed_hours')) is not int or metric['completed_hours'] != completed_hours
                or type(metric.get('all_hour_packet_count')) is not int or metric['all_hour_packet_count'] != completed_hours
                or any(metric.get(name) is not True for name in (
                    'all_hour_packet_revalidation_verified','parent_namespace_bookends_verified',
                    'final_post_revalidation_bookends_verified','named_runtime_bookends_verified'))
                or metric.get('complete_dynamic_input_closure_proved') is not False
                or metric.get('unobserved_between_bookends_ABA_covered') is not False
                or type(metric.get('parent_namespace_observations')) is not int
                or metric['parent_namespace_observations'] != 3
                or type(metric.get('retained_cap_bytes')) is not int
                or metric['retained_cap_bytes'] != historical.MAX_RETAINED_BYTES
                or any(type(metric.get(name)) is not int or metric[name] < 0 for name in (
                    'selected_frame_bytes','all_hour_packet_bytes','combined_retained_bytes'))
                or metric['selected_frame_bytes'] + metric['all_hour_packet_bytes'] != metric['combined_retained_bytes']
                or metric['combined_retained_bytes'] > metric['retained_cap_bytes']
                or type(metric.get('named_runtime_inventory')) is not dict
                or metric['named_runtime_inventory'] != inventory
                or any(type(metric['named_runtime_inventory'][name]) is not type(value)
                       for name,value in inventory.items())):
        raise ValueError('single constructor traversal, all-hour revalidation and final bookends required')


def _validate_reader_metrics(first, second, completed_hours):
    for metric in (first, second):
        _validate_reader_metric(metric, completed_hours)
    tokens = tuple(metric.get('observation_token') for metric in (first, second))
    if (any(type(token) is not str or len(token) != 32 for token in tokens) or tokens[0] == tokens[1]):
        raise ValueError('distinct independent Reader observations required')


def _materialize(header, captured, proof, *, hour, terminal, binding, registry_pin, own):
    count = hour+1
    envelope = prior._envelope(header, captured, proof)
    _, declaration, origin, current = prior.origin_join.predecessor._coordinates(envelope, count)
    registry_args = dict(split=origin.split, raw_start=origin.power_raw_hour, hours=count,
                         outage_seed=origin.outage_seed, expected_registry_identity=registry_pin)
    prefix = registry.prepare(**registry_args)
    if prefix.audit['registry_identity'] != registry_pin:
        raise ValueError('registry identity differs')
    observation = source.load_pinned_current(current, declaration['upstream_root'], config_path=declaration['config_path'])
    decision, frame, action = prior.origin_join._join(envelope, prefix, observation, completed_hours=count)
    w, cfe, projection = prior._project(observation, frame, captured['packet'])
    # This is the unchanged scientific quantity schema. Validation provenance
    # below is explicitly the batch successor's schema and implementation.
    scientific = io.encode(dict(schema=prior.SCHEMA, relative_hour=hour,
        current_decision_identity=decision.decision_identity, workload_exact=prior._ratio(w),
        source_cfe_at_alpha_one_exact=prior._ratio(cfe), projection_rule=projection['projection_rule'],
        power_rule=projection['power_rule'], decimal_places=12, normalized_unit_mw='250',
        cfe_source_mapping_rule=prior.CFE_RULE))
    audit = io.encode(dict(schema=SCHEMA, implementation_identity=own, completed_hours=count,
        controller_binding_sha256=binding, controller_terminal_sha256=terminal,
        historical_controller=proof, normal_audit_identity=envelope.audit_identity,
        normal_audit_payload=json.loads(envelope.audit_payload),
        source_observation_identity=observation.identity, registry_identity=registry_pin,
        source_observation_audit_payload=json.loads(observation.audit_payload), registry_audit_payload=prefix.audit,
        registry_audit_identity=io.digest(io.encode(prefix.audit)), registry_prefix_decision_identity=prefix.decision_identity,
        decision_identity=decision.decision_identity, exogenous_scientific_identity=io.digest(scientific),
        source_action_audit_identity=physical._digest(action), origin_kind=prefix.audit['origin_kind'],
        source_cap_table_sha256=prefix.audit['cap_table_sha256'], workload_projection=projection,
        source_cfe_at_alpha_one_exact=prior._ratio(cfe), current_source_correspondence_checked=True,
        registry_action_and_cap_lookup_checked=True, exact_source_projection_checked=True, policy_visible=False,
        shared_observed_clock=False, accepted_real_RTS_root_integration_verified=False,
        detached_consumer_authenticated=False, persistent_lane_owner_implemented=False, common_publication_verified=False,
        full_192_hour_execution_verified=False, resource_admission=False, formal_execution_ready=False,
        formal_result=False, native_execution_authorized=False, replay_contract=SCHEMA))
    if len(audit) > prior.historical.binding.CAP:
        raise ValueError('exact source audit exceeds bounded record cap')
    prepared = prior.normal._owned(prior.origin_join.PreparedCurrent, decision=decision, frame=frame,
        source_origin=prefix.origin, source_action=action, audit_payload=audit)
    value = prior.normal._owned(prior.ExactSourceCurrent, prepared_current=prepared, workload_exact=w,
        source_cfe_at_alpha_one_exact=cfe, exogenous_scientific_payload=scientific,
        source_observation_identity=observation.identity, source_projection_audit_payload=audit)
    return value, envelope, prefix, observation, declaration, registry_args


def prepare_many(root, *, expected_binding_sha256, expected_terminals, expected_registry_identity, selected_hours=None):
    """Read externally pinned history twice, returning current-only projections."""
    check_entry=_CHECK_READER_ENTRY
    check_entry()
    if (type(expected_terminals) is not dict or not expected_terminals
            or any(type(h) is not int or not 0 <= h < 192 for h in expected_terminals)):
        raise ValueError('bounded exact selected terminal map required')
    terminals = {h:io.pin(pin) for h,pin in expected_terminals.items()}
    if set(terminals) != set(range(max(terminals)+1)):
        raise ValueError('every pinned N predecessor terminal is required')
    selected = tuple(sorted(terminals)) if selected_hours is None else selected_hours
    if (type(selected) is not tuple or not selected or any(type(h) is not int for h in selected)
            or selected != tuple(sorted(set(selected))) or not set(selected) <= set(terminals)):
        raise ValueError('bounded sorted selected current hours required')
    io.pin(expected_binding_sha256); io.pin(expected_registry_identity)
    own = implementation_identity()
    observed = {}
    latest = max(terminals)
    args = dict(expected_binding_sha256=expected_binding_sha256, expected_terminal_sha256=terminals[latest],
                completed_hours=latest+1, expected_terminals=terminals, selected_hours=selected)
    captured, fresh, values = {}, {}, {}
    try:
        first, captured, header, first_metrics = _REPLAY_PREFIXES(root, **args, _observed=observed)
        check_entry()
        _validate_reader_metric(first_metrics, latest+1)
        values = {}
        retained = 0
        for hour in selected:
            row = _materialize(header, captured[hour], first[hour], hour=hour, terminal=terminals[hour],
                               binding=expected_binding_sha256, registry_pin=expected_registry_identity, own=own)
            retained += historical.retained_size(row)
            if retained > MAX_CURRENT_BYTES:
                raise ValueError('batch current retained data byte cap exceeded')
            values[hour] = row
        check_entry()
        second, fresh, fresh_header, second_metrics = _REPLAY_PREFIXES(root, **args, _observed=observed)
        check_entry()
        _validate_reader_metrics(first_metrics, second_metrics, latest+1)
        if first != second or header != fresh_header:
            raise ValueError('N batch prefix changed during preparation')
        for hour, (value, envelope, prefix, observation, declaration, registry_args) in values.items():
            repeated = prior._envelope(fresh_header, fresh[hour], second[hour])
            source.validate_pinned_current(observation, declaration['upstream_root'], expected_identity=observation.identity,
                                           config_path=declaration['config_path'])
            if (envelope.audit_payload != repeated.audit_payload
                    or envelope.decision.decision_bytes != repeated.decision.decision_bytes
                    or registry.prepare(**registry_args) != prefix or implementation_identity() != own):
                raise ValueError('historical N, source, registry or implementation changed during exact batch join')
        historical._observe_sources(observed['identities'], header['parent_declaration'])
        check_entry()
        if implementation_identity() != own:
            raise ValueError('implementation changed after final batch source observation')
        _validate_reader_metrics(first_metrics, second_metrics, latest+1)
        return CurrentBatch({h:row[0] for h,row in values.items()}, (first_metrics,second_metrics))
    finally:
        captured.clear()
        fresh.clear()
        values.clear()
        observed.clear()


_CHECK_READER_ENTRY=FunctionType(_check_reader_entry.__code__,globals(),'frozen_source_reader_entry_check')
_LOCAL_NAMESPACE = globals()
_LOCAL_BINDINGS = tuple((name, _LOCAL_NAMESPACE[name]) for name in (
    'prior', 'historical', 'io', 'source', 'registry', 'physical', '_REPLAY_PREFIXES', '_materialize',
    'MAX_CURRENT_BYTES', 'implementation_identity', '_check_reader_entry', 'SCHEMA', '_validate_reader_metrics',
    '_validate_reader_metric', '_CHECK_READER_ENTRY', 'FunctionType'))
_ENTRY_FUNCTIONS = tuple((historical, name, getattr(historical, name), historical._function_state(getattr(historical, name)))
    for name in ('replay_prefixes', '_check_dependencies', '_CHECK_DEPENDENCIES', '_function_state'))
_ENTRY_FUNCTIONS += tuple((sys.modules[__name__], name, globals()[name], historical._function_state(globals()[name]))
    for name in ('_materialize', 'implementation_identity', '_validate_reader_metrics', '_validate_reader_metric',
                 '_check_reader_entry', '_CHECK_READER_ENTRY'))
