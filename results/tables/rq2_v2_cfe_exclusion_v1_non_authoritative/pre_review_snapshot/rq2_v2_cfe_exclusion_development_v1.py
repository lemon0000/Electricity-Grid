"""Source-bound v2 cell contradiction coverage; zero-solver development only.

Prove emptiness of a deliberately relaxed local service set. No failed policy,
native status, runtime float adapter, individual other pair or holdout outcome
is classified as infeasible. All original obligation identities are retained.
"""
from fractions import Fraction as Q
import json
from pathlib import Path

import yaml

from experiments import audit_rq2_h1_resource_readiness_v1 as inventory
from experiments import h1_raw_ingress_development_v1 as io
from src.rq2_joint_deliverability_boundary_v1 import cfe_preallocation as mapping
from src.rq2_joint_deliverability_boundary_v1 import source_window, workload_projection

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'rq2_v2_cfe_exclusion_development_v1'
CAP = 16 * 1024 * 1024
INPUT_CAP = 32 * 1024 * 1024
PROTOCOL = 'configs/rq2_finite_mechanism_protocol_candidate_v2.DRAFT.yaml'
COVERAGE = 'results/tables/rq2_finite_enrollment_support_v1_non_authoritative/coverage_168_24_verified.json'
CATALOG = 'results/tables/rq2_h1_resource_readiness_v1_non_authoritative/resource_gap_audit_v2_final.json'
OUTER = 'configs/rq2_normal_h1_calibration_v3.OUTER.SHA256SUMS.json'
PINS = {PROTOCOL: inventory.PINS[PROTOCOL], COVERAGE: inventory.PINS[COVERAGE],
    CATALOG: '1a31bdd0d69b717525e1d281f4d53d21bf8f8cca929732b76847cfa332843ad1',
    OUTER: inventory.PINS[OUTER]}
POWER_INDEX, WORKLOAD_INDEX, OFFSET = 8, 17, 162
ARMS = ('CFE-only', 'joint-correct', 'joint-B6')
FLAGS = dict(formal_result=False, capacity_certificate=False, execution_authorized=False,
    resource_admission=False, formal_execution_ready=False, complete_executable_task_inventory=False,
    operational_float_adapter_certified=False, operational_projection_bridge_verified=False,
    runtime_infeasible=False, native_export_coverage=False)


def contradiction(workload, source_cfe, alpha, fraction):
    """Exact relaxed set: 0<=s<=f*w+tau and q_eff-s<=tau.

Every exact f*w-constrained full-service trajectory is in this local superset,
including one permitting tau shortfall. Grid, temporal and causal constraints
are omitted. A nonpositive gap proves nothing about the original object.
"""
    allocation = mapping.allocate(workload, source_cfe, alpha)
    f = mapping._q(fraction)
    if not 0 <= f <= 1: raise ValueError('bounded exact flexibility fraction required')
    tau = mapping.activity_threshold()
    available = f * allocation.workload
    cap = available + tau
    required = allocation.effective_request - tau
    gap = required - cap
    contract_gap = allocation.effective_request - available
    return dict(allocation=allocation.record(), allocation_identity=allocation.identity,
        flexible_fraction=str(f), availability=str(available), activity_threshold=str(tau),
        approved_contract_gap=str(contract_gap),
        approved_contract_contradiction=allocation.effective_request > tau and contract_gap > 0,
        relaxed_service_upper=str(cap), relaxed_service_lower=str(required),
        contradiction_gap=str(gap), local_relaxation_empty=gap > 0,
        absence_of_contradiction_is_feasibility=False)


def _coverage(cells, catalog):
    """Factorized proof coverage, not required executions or per-pair failures."""
    excluded = sum(c['status'] == 'cell_local_relaxation_contradiction' for c in cells)
    axes = catalog['axes']
    pairs = len(axes['training_lb']['power']) * len(axes['training_lb']['workload'])
    holdout = len(axes['holdout']['power']) * len(axes['holdout']['workload'])
    affected = dict(training_lb=excluded*pairs*len(ARMS),
        training_ub=excluded*pairs*len(ARMS)*len(axes['training_ub']['capacity']),
        training_b6_actual=excluded*pairs, holdout=excluded*holdout*len(ARMS))
    direct = dict(training_lb=excluded*len(ARMS),
        training_ub=excluded*len(ARMS)*len(axes['training_ub']['capacity']))
    return dict(original_identity_counts=catalog['identity_counts'],
        affected_identity_counts=affected,
        remaining_identity_counts={k:v-affected[k] for k,v in catalog['identity_counts'].items()},
        direct_witness_planning_identity_counts=direct,
        other_pair_planning_identity_counts={k:affected[k]-direct[k] for k in direct},
        other_pair_disposition='not_scheduled_due_to_parent_cell_proof',
        conditional_evaluation_identity_counts={k:affected[k] for k in ('training_b6_actual','holdout')},
        conditional_evaluation_disposition='prerequisite_false_no_training_UB; not_executed',
        family_disposition=dict(
            training_lb='other pair contributions unnecessary for this whole-cell contradiction; not individual pair infeasibility',
            training_ub='no complete full-support UB at any registered D for this cell',
            training_b6_actual='conditional evaluation lacks an eligible training planning UB; not actual execution failure',
            holdout='conditional evaluation lacks an eligible training UB; not holdout infeasibility'),
        power_workload_axes_retained=True, capacity_grid_retained=True, omitted_identities=0,
        source_pair_failure_count=None, native_calls_avoided=None, wall_time_saved=None,
        scheduling_authorized=False, resource_discounts_applied=False)


def audit():
    views = {}
    def read(name, pin=None):
        path = Path(name)
        if not path.is_absolute(): path = ROOT/path
        raw, stamp = io.read_stable(path, INPUT_CAP)
        if pin is not None and io.digest(raw) != io.pin(pin): raise ValueError('pinned proof input differs: '+str(name))
        views[path] = (raw, stamp)
        return raw
    for name, pin in PINS.items(): read(name, pin)
    # The pinned existing outer closes all src dependencies used by the source
    # loader and exact mapping; no member is altered or newly sealed here.
    outer = json.loads(views[ROOT/OUTER][0])
    for name, pin in outer['members'].items(): read(name, pin)
    read(__file__); read(inventory.__file__); read(io.__file__)
    protocol = yaml.safe_load(views[ROOT/PROTOCOL][0])
    coverage = json.loads(views[ROOT/COVERAGE][0])
    existing = json.loads(views[ROOT/CATALOG][0])['obligation_catalog']
    counts = inventory.protocol_counts(protocol, coverage)
    catalog = inventory.obligation_catalog(protocol, coverage, counts)
    if not io.same(catalog, existing): raise ValueError('complete v2 obligation catalog differs')
    if (protocol['clean_allocation'] != 'action_independent_current_baseline_R_times_w'
            or protocol['joint_service'] != 'additive_disjoint_service_commitment_benchmark'
            or protocol['b6_planning']['availability_per_track'] != 'f_times_w'
            or Q(protocol['business_anchor']['service_tolerance']) != mapping.activity_threshold()):
        raise ValueError('same approved allocation/service contract required')
    axes = catalog['axes']['training_lb']
    windows = {'power': axes['power'][POWER_INDEX], 'workload': axes['workload'][WORKLOAD_INDEX]}
    if (POWER_INDEX,WORKLOAD_INDEX,OFFSET,windows['power']['source_start'],
            windows['workload']['source_start'],windows['power']['outage_seed']) != (8,17,162,192,408,20260822):
        raise ValueError('named v2 training witness identity differs')
    config = source_window.audit.DEFAULT_CONFIG
    read(config, coverage['source_config_sha256'])
    sources = {}
    for kind, window in windows.items():
        if window['split'] != 'training' or window['enrollment_end_inclusive'] != window['source_start']+167:
            raise ValueError('complete training enrollment witness required')
        source = source_window.load_source_window(kind, 'training', window['source_start'],168,
            outage_seed=window['outage_seed'],config_path=config,expected_config_sha256=coverage['source_config_sha256'])
        if source['chain']['chain_id'] != window['chain_id'] or len(source['rows']) != 168:
            raise ValueError('witness source chain/clock differs')
        binding = coverage['input_packages'][kind]
        for name, pin in binding['members'].items(): read(Path(binding['package'])/name,pin)
        if not io.same(source['members'],binding['members']): raise ValueError('window package differs from coverage')
        sources[kind] = source
    projections = [workload_projection.project_workload_power(row['workload_fraction'],
        protocol['source_mapping']['normalized_power_unit_mw'],
        decimal_places=protocol['source_mapping']['workload_projection_decimal_places']) for row in sources['workload']['rows']]
    if any(p['status'] != 'projected' or p['exact_interface_identity_verified'] is not True for p in projections):
        raise ValueError('whole enrollment workload projection must be valid')
    if any(not 0 <= Q(row['cfe_call_fraction']) <= 1 for row in sources['power']['rows']):
        raise ValueError('complete source CFE domain required')
    source_cfe = sources['power']['rows'][OFFSET]['cfe_call_fraction']
    workload = str(projections[OFFSET]['workload_occupancy'])
    witness = dict(power_index=POWER_INDEX,workload_index=WORKLOAD_INDEX,relative_offset=OFFSET,
        power_window=windows['power'],workload_window=windows['workload'],
        whole_enrollment_source_windows=sources,whole_enrollment_workload_projection=projections,
        raw_source_hours={kind:window['source_start']+OFFSET for kind,window in windows.items()},
        selected_source_rows={kind:source['rows'][OFFSET] for kind,source in sources.items()},
        selected_workload_projection=projections[OFFSET],
        source_cfe=source_cfe,projected_workload=workload,
        joint_observation_claim=False,normal_reference_reachability_proven=False,
        role='necessary condition on any hypothetical complete service trajectory, not an observed dispatch')
    witness_pin = io.digest(io.encode(witness))
    proofs, groups, cells = {}, {}, []
    for ti, theta in enumerate(axes['theta']):
        for ai, alpha in enumerate(axes['alpha']):
            arithmetic = contradiction(workload,source_cfe,alpha,theta['flexible_fraction'])
            group_pin = io.digest(io.encode(arithmetic))
            groups.setdefault(group_pin,arithmetic)
            proof = dict(schema=SCHEMA,lemma='local_service_relaxation_contradiction_v1',
                protocol_sha256=PINS[PROTOCOL],catalog_sha256=PINS[CATALOG],witness_sha256=witness_pin,
                arithmetic=arithmetic,registered_capacity_domain=protocol['capacity_domain'],
                affected_arms=list(ARMS),policy_quantifier='every complete causal policy in the named v2 contract',
                normal_reference_feasibility_not_assumed=True,formal_result=False)
            pin = io.digest(io.encode(proof)) if arithmetic['local_relaxation_empty'] else None
            if pin is not None: proofs.setdefault(pin,proof)
            cells.append(dict(theta_index=ti,alpha_index=ai,theta=theta,alpha=alpha,
                cell_sha256=io.digest(io.encode(dict(protocol_sha256=PINS[PROTOCOL],theta=theta,alpha=alpha))),
                status='cell_local_relaxation_contradiction' if pin else 'no_contradiction_from_selected_witness',
                arithmetic_group_sha256=group_pin,proof_sha256=pin,network_only_conclusion=None,
                planning_arm_disposition={arm:'no_training_UB' if pin else 'unknown' for arm in ARMS},
                conditional_evaluation_disposition='prerequisite_false_no_training_UB' if pin else 'unknown'))
    source_pins = {p.relative_to(ROOT).as_posix():io.digest(raw) for p,(raw,stamp) in views.items()}
    for path, view in views.items():
        if io.read_stable(path,INPUT_CAP) != view: raise ValueError('proof evidence changed during audit')
    result = dict(schema=SCHEMA,status='DRAFT_NONAUTHORITATIVE',protocol_sha256=PINS[PROTOCOL],
        catalog_sha256=PINS[CATALOG],source_sha256=source_pins,witness=witness,witness_sha256=witness_pin,
        theta_count=len(axes['theta']),alpha_count=len(axes['alpha']),cells=cells,proofs=proofs,
        arithmetic_groups=groups,
        contradicted_cell_count=sum(c['proof_sha256'] is not None for c in cells),
        coverage=_coverage(cells,catalog),solver_calls=0,holdout_sources_evaluated=False,
        per_pair_offline_lb_computed=False,complete_policy_ub_computed=False,**FLAGS)
    if len(io.encode(result)) > CAP: raise ValueError('exclusion report cap')
    return result


def inspect(path, *, expected_sha256):
    raw, stamp = io.read_stable(Path(path),CAP)
    if io.digest(raw) != io.pin(expected_sha256): raise ValueError('external exclusion pin differs')
    result = audit()
    if io.encode(result) != raw: raise ValueError('fresh source-bound exclusion reconstruction differs')
    if io.read_stable(Path(path),CAP) != (raw,stamp): raise ValueError('exclusion report changed during inspection')
    return result
