"""Two-observation current reconstruction for selected accepted N prefixes.

No internal cache survives a call. The owner keeps
the returned currents private to one complete scientific replay. Not authority.
"""
from pathlib import Path
from dataclasses import dataclass
import json

from experiments import h1_phase_exact_source_current_development_v1 as prior
from experiments import h1_phase_historical_batch_development_v1 as historical

SCHEMA = 'h1_phase_exact_source_batch_development_v1'
MAX_CURRENT_BYTES = 64*1024**2
io, source, registry, physical = prior.io, prior.source, prior.registry, prior.physical
_REPLAY_PREFIXES = historical.replay_prefixes


@dataclass(frozen=True)
class CurrentBatch:
    """Call-local replay data and cost observations; never a capability."""
    currents: dict
    observations: tuple


def _check_reader_entry():
    if historical.replay_prefixes is not _REPLAY_PREFIXES:
        raise ValueError('original batch historical entry required')


def implementation_identity():
    return io.digest(io.encode([SCHEMA, prior.implementation_identity(), historical.implementation_identity(),
                                io.digest(Path(__file__).read_bytes())]))


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
    _check_reader_entry()
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
        _check_reader_entry()
        values = {}
        retained = 0
        for hour in selected:
            row = _materialize(header, captured[hour], first[hour], hour=hour, terminal=terminals[hour],
                               binding=expected_binding_sha256, registry_pin=expected_registry_identity, own=own)
            retained += historical.retained_size(row)
            if retained > MAX_CURRENT_BYTES:
                raise ValueError('batch current retained data byte cap exceeded')
            values[hour] = row
        _check_reader_entry()
        second, fresh, fresh_header, second_metrics = _REPLAY_PREFIXES(root, **args, _observed=observed)
        _check_reader_entry()
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
        _check_reader_entry()
        if implementation_identity() != own:
            raise ValueError('implementation changed after final batch source observation')
        return CurrentBatch({h:row[0] for h,row in values.items()}, (first_metrics,second_metrics))
    finally:
        captured.clear()
        fresh.clear()
        values.clear()
        observed.clear()
