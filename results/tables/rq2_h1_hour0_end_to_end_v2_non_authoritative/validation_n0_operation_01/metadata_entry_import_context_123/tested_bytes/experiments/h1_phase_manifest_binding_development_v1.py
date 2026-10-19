"""Detached training-UB lane declarations; no executable manifest or authority."""
from dataclasses import asdict, dataclass
from fractions import Fraction as Q
from pathlib import Path

from experiments import h1_phase_manifest_group_development_v1 as group
from experiments import h1_selector_configuration_development_v1 as configuration
from experiments import h1_phase_owner_development_v1 as owner

io = group.io
SCHEMA = 'h1_phase_manifest_binding_development_v1'
ARMS = {'network-only': 'network_only_shared', 'CFE-only': 'cfe_only_shared',
        'joint-correct': 'joint_correct_shared',
        'joint-B6': 'joint_b6_separate_planning_shared_execution'}
TERMINAL = frozenset(('conditional_prerequisite_false_not_executed',
    'direct_analytic_witness', 'not_scheduled_due_to_parent_cell_proof'))
ENVELOPE = ('maximum_event_count', 'maximum_event_duration_hours', 'minimum_recovery_hours',
    'normalized_debt_limit', 'normalized_energy_budget', 'recovery_efficiency', 'time_step_hours')


@dataclass(frozen=True)
class ArchiveCapacityDeclaration:
    max_events: int
    max_event_bytes: int
    max_archive_bytes: int
    reserved_alternate_witnesses: int

    def __post_init__(self):
        for key in ('max_events', 'max_event_bytes', 'max_archive_bytes'):
            if type(getattr(self, key)) is not int or getattr(self, key) <= 0:
                raise ValueError('positive exact integer archive declarations required')
        w = self.reserved_alternate_witnesses
        if type(w) is not int or w < 0:
            raise ValueError('nonnegative exact alternate witness reservation required')
        if not 576 + 2*w <= self.max_events <= 999999:
            raise ValueError('192-hour event reservation or ticket holder ceiling differs')
        if self.max_archive_bytes < self.max_events * self.max_event_bytes:
            raise ValueError('full declared event envelope exceeds archive declaration')


@dataclass(frozen=True)
class PreparedManifest:
    # Manually constructible detached data, never an authenticated owner input.
    manifest: owner.Manifest | None
    audit_payload: bytes
    audit_identity: str


def _exact(value):
    if type(value) not in (str, int):
        raise ValueError('exact source rational string or integer required')
    result = Q(value)
    if result < 0:
        raise ValueError('nonnegative source rational required')
    return result


def _scalar(value):
    return owner.business.lossless_builtin(_exact(value))


def _lanes(g):
    """Pure projection helper; caller of public prepare gets fresh pinned input."""
    if (g['family'] != 'training_ub' or g['capacity_is_feasible_certificate'] is not False
            or g['execution_lanes'] is not None or g['audit_labels_are_policy_inputs'] is not False
            or any(g[k] is not False for k in group.FLAGS)
            or g['family_dependency'] != 'complete_training_causal_policy_and_grid_witness'):
        raise ValueError('training UB group semantic boundaries differ')
    siblings = g['siblings']
    if (len(siblings) != 4 or {s['arm_id'] for s in siblings} != set(ARMS)
            or set(g['catalog_arm_order']) != set(ARMS) or len(g['catalog_arm_order']) != 4):
        raise ValueError('all four unique arm obligations required')
    fixed = g['known_scientific_fields']
    inventories = ((fixed, {'mechanism','policy','envelope','enrollment_hours',
        'maximum_followup_hours','due_offset','retain_followup_births_and_debt','workload_decimal_places'}),
        (fixed.get('mechanism'), {'alpha','flexible_fraction','recovery_headroom_coefficient','normalized_unit_mw'}),
        (fixed.get('policy'), {'minimum_event_power','curtailment_up_ramp_per_hour',
            'response_time_hours','maximum_recovery_power','recovery_decimal_places'}),
        (fixed.get('envelope'), set(ENVELOPE)))
    if any(type(value) is not dict or set(value) != expected for value, expected in inventories):
        raise ValueError('exact scientific field inventories required')
    if (fixed['enrollment_hours'], fixed['maximum_followup_hours'], fixed['due_offset'],
            fixed['retain_followup_births_and_debt'], fixed['workload_decimal_places']) != (168,24,24,True,12):
        raise ValueError('fixed 192-hour scientific contract differs')
    capacity = _exact(g['candidate_capacity'])
    if capacity > 1 or capacity != _exact(g['coordinate']['capacity']):
        raise ValueError('capacity coordinate differs or exceeds normalized domain')
    m = fixed['mechanism']; p = fixed['policy']; e = fixed['envelope']
    mechanism = owner.business.Mechanism(_exact(m['alpha']), _exact(m['flexible_fraction']),
        _exact(m['recovery_headroom_coefficient']), _exact(m['normalized_unit_mw']))
    if type(e['maximum_event_count']) is not int or type(p['recovery_decimal_places']) is not int:
        raise ValueError('exact count and recovery precision required')
    envelope = tuple((k, e[k] if k == 'maximum_event_count' else _scalar(e[k])) for k in ENVELOPE)
    lanes, classifications = [], []
    for sibling in siblings:
        arm, disposition = sibling['arm_id'], sibling['disposition']
        if disposition in TERMINAL:
            if sibling['missing_dependency'] is not None:
                raise ValueError('proof-terminal obligation dependency differs')
            category = 'proof_terminal'
        elif disposition == 'unresolved_no_certificate':
            if sibling['missing_dependency'] != 'named_causal_policy_full_training_witness_missing':
                raise ValueError('unresolved training UB obligation dependency differs')
            category = 'pending_separate_B6_planning' if arm == 'joint-B6' else 'direct_shared_lane'
        else:
            raise ValueError('unknown obligation disposition')
        classifications.append(dict(arm_id=arm, classification=category,
            obligation_sha256=sibling['obligation_sha256']))
        if category == 'direct_shared_lane':
            policy = owner.business.business.BidirectionalPolicy(ARMS[arm], _scalar(g['candidate_capacity']),
                g['capacity_declaration_ids'][arm], _scalar(p['minimum_event_power']),
                _scalar(p['curtailment_up_ramp_per_hour']), _scalar(p['response_time_hours']),
                _scalar(p['maximum_recovery_power']), p['recovery_decimal_places'])
            lanes.append(owner.LaneConfig(ARMS[arm], policy, mechanism, envelope))
    return tuple(sorted(lanes, key=lambda lane: lane.lane_id)), classifications


def _validated_group(family, ordinal):
    result = group.prepare(family, ordinal)
    raw = io.read_stable(group.ROOT/group.symbolic.PROOF, group.symbolic.proof.exclusion.INPUT_CAP)[0]
    expected = group._project(raw, family, ordinal, result['implementation_sha256'])
    if owner.encode(result) != owner.encode(expected):
        raise ValueError('fresh group differs from pinned obligation projection')
    return result


def _implementation(c):
    return io.digest(owner.encode([SCHEMA, io.digest(Path(__file__).read_bytes()),
        io.digest(Path(owner.__file__).read_bytes()), io.digest(Path(owner.legacy.__file__).read_bytes()),
        owner.business.implementation_identity(), configuration.implementation_identity(),
        owner.selection.implementation_identity(c.specification, c.limits)]))


def _record_reservation(c, lane_ids):
    # Exact base64/JSON envelope for the declared maximum saved-record lengths.
    # Source audit, intent metadata, outer event framing and storage are additional.
    n = len(c.generation_uids)
    skeleton = dict(reference=['']*(n+2), actual={k: ['']*(n+1) for k in lane_ids})
    return len(owner.encode(skeleton)) + (n+2+len(lane_ids)*(n+1))*4*((c.limits.max_record_bytes+2)//3)


def prepare(family, ordinal, selector_configuration, archive):
    """Fresh-at-return declaration binding. Does not open any owner or run gate."""
    if family != 'training_ub' or type(family) is not str or type(ordinal) is not int or ordinal < 0:
        raise ValueError('training_ub and nonnegative exact ordinal required')
    c = selector_configuration
    if type(c) is not configuration.SelectorRunConfiguration or type(archive) is not ArchiveCapacityDeclaration:
        raise ValueError('exact typed selector and archive declarations required')
    c.__post_init__(); archive.__post_init__()
    request = owner.encode([family, ordinal, c.binding(), asdict(archive)])
    implementation = _implementation(c)
    g = _validated_group(family, ordinal)
    lanes, classifications = _lanes(g)
    reserved_records = _record_reservation(c, [lane.lane_id for lane in lanes]) if lanes else 0
    if archive.max_event_bytes < reserved_records:
        raise ValueError('declared selector record envelope exceeds event declaration')
    manifest = owner.Manifest(lanes, c.reference_selector, c.actual_selector, c.specification,
        c.limits, archive.max_events, archive.max_event_bytes, archive.max_archive_bytes,
        g['accounting_period_id']) if lanes else None
    audit = dict(schema=SCHEMA, implementation_sha256=implementation, family=family, ordinal=ordinal,
        group=g, arm_classifications=classifications, selector_configuration=c.binding(),
        archive_declaration=asdict(archive), manifest=asdict(manifest) if manifest else None,
        archive_derivation=dict(full_192h_primary_event_upper_bound=576,
            origin_events=2, subsequent_hours=191, events_per_subsequent_hour=3, terminal_events=1,
            events_per_alternate_witness=2, conditional_required_events=576+2*archive.reserved_alternate_witnesses,
            reserved_selector_record_bytes=reserved_records,
            conditional_on_witness_count_within_reservation=True, archive_used=bool(lanes),
            alternate_witness_limit_enforced=False, full_event_size_bound_proven=False,
            full_path_archive_sufficiency_proven=False, physical_storage_bound_proven=False),
        detached_declaration=True, group_obligations_complete=False,
        capacity_is_feasible_certificate=False, producer_archive_bound_proven=False,
        paired_owner_authenticated=False, owner_consumption_authorized=False,
        selector_producer_connected=False, normal_source_correspondence_verified=False,
        solver_reuse_verified=False, executable_manifest=False, resource_admission=False,
        formal_execution_ready=False, formal_result=False, native_execution_authorized=False)
    if (owner.encode(_validated_group(family, ordinal)) != owner.encode(g)
            or _implementation(c) != implementation
            or owner.encode([family, ordinal, c.binding(), asdict(archive)]) != request):
        raise ValueError('manifest inputs or implementation changed during preparation')
    payload = owner.encode(audit)
    return PreparedManifest(manifest, payload, io.digest(payload))
