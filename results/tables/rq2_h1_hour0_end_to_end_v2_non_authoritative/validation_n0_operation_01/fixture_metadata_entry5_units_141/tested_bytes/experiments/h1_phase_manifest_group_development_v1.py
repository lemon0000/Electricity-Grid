"""Pinned family/arm obligation projection; no executable Phase Manifest.

This detached planning projection grants neither reuse nor producer authority.
Numeric selector/solver/resource configuration must be registered separately.
"""
import json
from pathlib import Path

from experiments import h1_symbolic_normal_manifest_development_v1 as symbolic

io = symbolic.io
ROOT = symbolic.ROOT
SCHEMA = 'h1_phase_manifest_group_development_v1'
PROTOCOL = 'configs/rq2_finite_mechanism_protocol_candidate_v2.DRAFT.yaml'
# Full byte pin, rather than a YAML reinterpretation of the scientific contract.
PROTOCOL_PIN = '95eb158f0a8e6784d2af401e67164965543c98f42ff02b756c214982601e5430'
FLAGS = dict(executable_manifest=False, paired_owner_authenticated=False,
    solver_reuse_verified=False, resource_admission=False,
    formal_execution_ready=False, formal_result=False, native_execution_authorized=False)


def _project(raw, family, ordinal, implementation):
    if io.digest(raw) != symbolic.PROOF_PIN:
        raise ValueError('exact pinned obligation manifest required')
    value = json.loads(raw)
    if value['protocol_sha256'] != PROTOCOL_PIN:
        raise ValueError('protocol correspondence differs')
    resolver = symbolic.proof._resolver(raw)
    selected = resolver.resolve(family, ordinal)['record']['payload']
    coordinate = selected['coordinate']
    group_coordinate = {k:v for k,v in coordinate.items() if k != 'arm'}
    group = dict(schema=SCHEMA, proof_manifest_sha256=symbolic.PROOF_PIN,
        protocol_sha256=PROTOCOL_PIN, family=family, coordinate=group_coordinate)
    group_id = io.digest(io.encode(group))
    siblings = []
    for arm in sorted(value['catalog']['axes'][family]['arm']):
        point = dict(group_coordinate, arm=arm)
        index = resolver.encode_coordinate(family, point)
        node = resolver.resolve(family, index)
        p = node['record']['payload']
        siblings.append(dict(arm_id=arm, ordinal=index,
            obligation_sha256=p['obligation_sha256'], disposition=p['disposition'],
            missing_dependency=p['missing_dependency'], obligation_node=node))
    theta = coordinate['theta']
    fixed = dict(mechanism=dict(alpha=coordinate['alpha'],
        flexible_fraction=theta['flexible_fraction'],
        recovery_headroom_coefficient=theta['recovery_headroom_coefficient'], normalized_unit_mw='250'),
        policy={k:theta[k] for k in ('minimum_event_power','curtailment_up_ramp_per_hour',
            'response_time_hours','maximum_recovery_power','recovery_decimal_places')},
        envelope=dict(maximum_event_count=theta['episode_event_cap'],
            maximum_event_duration_hours=theta['maximum_event_duration_hours'],
            minimum_recovery_hours=theta['minimum_rest_hours'],
            normalized_debt_limit=theta['normalized_debt_cap'],
            normalized_energy_budget=theta['episode_call_energy_cap'],
            recovery_efficiency=theta['recovery_efficiency'],time_step_hours=theta['time_step_hours']),
        enrollment_hours=168,maximum_followup_hours=24,due_offset=24,
        retain_followup_births_and_debt=True,workload_decimal_places=12)
    unresolved = [s['arm_id'] for s in siblings if s['disposition']=='unresolved_no_certificate']
    # UB B6 means separate causal planning tracks, not an actual shared lane.
    needs = {
        'training_lb':'same_contract_lower_bound_feasible_set_superset',
        'training_ub':'complete_training_causal_policy_and_grid_witness',
        'training_b6_actual':'frozen_B6_training_capacity_and_policy_certificate',
        'holdout':'frozen_training_capacity_and_named_policy_certificate',
    }
    return dict(**group,group_identity=group_id,implementation_sha256=implementation,
        split=selected['split'],catalog_arm_order=value['catalog']['axes'][family]['arm'],
        siblings=siblings,unresolved_arms=unresolved,
        known_scientific_fields=fixed,candidate_capacity=coordinate.get('capacity'),
        capacity_is_feasible_certificate=False,execution_lanes=None,
        family_dependency=needs[family],
        configuration_dependencies=['pinned_complete_Rref_A_selector_specs',
            'pinned_finite_Rref_A_solver_and_replay_limits',
            'justified_event_and_archive_capacity_bounds'],
        accounting_period_id=io.digest(io.encode([SCHEMA,'accounting',group_id])),
        capacity_declaration_ids={s['arm_id']:io.digest(io.encode([SCHEMA,'capacity',
            group_id,s['obligation_sha256'],coordinate.get('capacity')])) for s in siblings},
        audit_labels_are_policy_inputs=False,**FLAGS)


def prepare(family, ordinal):
    """Fresh-at-return detached projection, never an execution credential."""
    views = symbolic._views()
    for path, expected in ((ROOT/PROTOCOL, PROTOCOL_PIN),(Path(__file__),None)):
        view = io.read_stable(path,symbolic.proof.exclusion.INPUT_CAP)
        if expected is not None and io.digest(view[0]) != expected:
            raise ValueError('pinned phase input differs')
        views[path] = view
    implementation = io.digest(io.encode({(p.relative_to(ROOT).as_posix()
        if p.is_relative_to(ROOT) else p.as_posix()):io.digest(v[0])
        for p,v in views.items()}))
    result = _project(views[ROOT/symbolic.PROOF][0],family,ordinal,implementation)
    for path,view in views.items():
        if io.read_stable(path,symbolic.proof.exclusion.INPUT_CAP) != view:
            raise ValueError('phase group source changed during preparation')
    return result
