"""Finite N planning slots, not runtime requests or an execution inventory.

The caller's static profile is a declaration, not verified run authority. Each
unresolved obligation owns its own potential episode; candidate sharing earns
no resource credit. No scientific source loader or solver is called.
"""
from dataclasses import asdict, dataclass, field
import json
from math import prod
from pathlib import Path

from experiments import rq2_v2_obligation_manifest_development_v1 as proof

io = proof.io
ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'h1_symbolic_normal_manifest_development_v1'
PROOF = 'results/tables/rq2_v2_obligation_manifest_v1_non_authoritative/obligation_manifest_v2_final.json'
PROOF_PIN = 'befcfab8180a0124f15ad7652b085514c7aec6278e2b9d967e9885fc5a65fdd7'
BASELINE = 'results/tables/rq2_h1_phase_ticket_holder_v1_non_authoritative/development_checks.json'
BASELINE_PIN = 'dcc66a0f0bd8fb229b3516b75a359a5b484e463e6a1dace938320f3962c06dd1'
HOURS, STAGES = 192, 232
FLAGS = dict(complete_executable_task_inventory=False, causal_request_keys_materialized=False,
    solver_reuse_verified=False, resource_discounts_applied=False, resource_admission=False,
    formal_execution_ready=False, formal_result=False, native_execution_authorized=False,
    static_profile_execution_validated=False, global_one_attempt_registry_implemented=False)


@dataclass(frozen=True)
class StaticProfile:
    network_sha256: str
    dc_bus_sha256: str
    source_config_sha256: str
    specification_sha256: str
    limits_sha256: str
    hour_budget_sha256: str
    implementation_sha256: str
    stage_order_sha256: str
    origin_rule_sha256: str
    need_rule_sha256: str

    def __post_init__(self):
        for value in asdict(self).values(): io.pin(value)


def _counts(value):
    """Independent factorized partition; never enumerate the full product."""
    catalog, cells = value['catalog'], value['cells']
    result = {}
    for family, order in catalog['axis_order'].items():
        axes = catalog['axes'][family]
        original = prod(len(axes[k]) for k in order)
        multiplicity = prod(len(axes[k]) for k in order if k not in ('theta','alpha','arm'))
        affected = sum(arm in c['arm_implication_nodes'] for c in cells for arm in axes['arm'])*multiplicity
        remaining = original-affected
        for key, count in [('original_identity_counts',original),('affected_identity_counts',affected),
                           ('remaining_identity_counts',remaining)]:
            if value['coverage'][key][family] != count: raise ValueError('proof partition count differs')
        result[family] = dict(original_identities=original, proof_discharged=affected,
            unresolved_identities=remaining, potential_hour_slots=remaining*HOURS,
            conditional_stage_slots=remaining*HOURS*STAGES, ordinal_span=original*HOURS)
    if value['coverage']['omitted_identities'] != 0: raise ValueError('omitted obligation identities')
    return result


def _compile(raw, profile, implementation):
    if type(profile) is not StaticProfile: raise ValueError('exact declared StaticProfile required')
    profile.__post_init__()
    value = json.loads(raw)
    counts = _counts(value)
    totals = {k:sum(c[k] for c in counts.values()) for k in
        ('original_identities','proof_discharged','unresolved_identities','potential_hour_slots','conditional_stage_slots')}
    pairs = {}
    for split,family in [('training','training_ub'),('holdout','holdout')]:
        axes = value['catalog']['axes'][family]
        pairs[split] = len(axes['power'])*len(axes['workload'])*HOURS
    summary = dict(schema=SCHEMA,status='DRAFT_NONAUTHORITATIVE',scope='N_layer_symbolic_only',
        proof_manifest_sha256=io.digest(raw),protocol_sha256=value['protocol_sha256'],
        catalog_sha256=value['catalog_sha256'],implementation_sha256=implementation,
        declared_static_profile=asdict(profile),hours=HOURS,conditional_stages_per_hour=STAGES,
        stage_count_condition='232 only after exact fixed RTS N stage-order/profile validation; not validated here',
        max_attempts_per_slot=1,retry_policy='none',
        ceiling_condition='one globally registered episode per unresolved obligation; at most one attempt per slot',
        ceiling_is_enforced=False,eligible_execution_count=None,complete_study_task_bound=None,
        other_role_multiplicities={k:None for k in ('Rref','business','A','LB','UB_policy_search')},
        slot_domain='family, original obligation ordinal, hour; proof-discharged ordinals have no slots',
        slot_ordinal_formula='original_obligation_ordinal * 192 + relative_hour',
        families=counts,totals=totals,omitted_identities=0,
        candidate_pair_hour_counts=pairs,conditional_candidate_pair_stage_count=sum(pairs.values())*STAGES,
        candidate_quotient_condition='unique canonical N producer per source pair or verified global reuse registry',
        verified_reuse_edges=[],source_loader_calls=0,solver_calls=0,**FLAGS)
    result = object.__new__(SymbolicManifest)
    object.__setattr__(result,'_raw',io.encode(summary))
    object.__setattr__(result,'_proof_raw',bytes(raw))
    return result


@dataclass(frozen=True,init=False)
class SymbolicManifest:
    _raw: bytes = field(repr=False)
    _proof_raw: bytes = field(repr=False)

    def __init__(self,*a,**kw): raise ValueError('build or fresh inspect required')
    def __copy__(self): raise ValueError('fresh inspect required')
    def __deepcopy__(self,memo): raise ValueError('fresh inspect required')
    def __reduce_ex__(self,protocol): raise ValueError('fresh inspect required')
    @property
    def raw(self): return self._raw
    @property
    def identity(self): return io.digest(self._raw)
    def data(self): return json.loads(self._raw)

    def obligation(self,family,ordinal):
        # The source is exact pinned immutable proof bytes; this creates no
        # runtime credential and does not rebuild or load scientific sources.
        node = proof._resolver(self._proof_raw).resolve(family,ordinal)
        p = node['record']['payload']
        discharged = p['disposition'] != 'unresolved_no_certificate'
        return dict(obligation_node=node,kind='proof_terminal_ref' if discharged else 'potential_N_episode',
            slot_range=None if discharged else [ordinal*HOURS,(ordinal+1)*HOURS],
            solver_reuse_edge=False)

    def resolve(self,family,slot_ordinal):
        if type(slot_ordinal) is not int or slot_ordinal<0: raise ValueError('exact nonnegative slot ordinal required')
        ordinal,hour = divmod(slot_ordinal,HOURS)
        mapping = self.obligation(family,ordinal)
        if mapping['kind']=='proof_terminal_ref': return mapping
        node = mapping['obligation_node'];p = node['record']['payload'];summary = self.data()
        profile = summary['declared_static_profile']
        pair = {k:p['coordinate'][k] for k in ('power','workload')}
        context = dict(schema=SCHEMA,role='N_unshared',proof_manifest_sha256=summary['proof_manifest_sha256'],
            obligation_sha256=p['obligation_sha256'],family=family,ordinal=ordinal,
            split=p['split'],source_pair=pair,static_profile=profile,
            implementation_sha256=summary['implementation_sha256'])
        genesis = io.digest(io.encode(dict(context,kind='declared_genesis_slot')))
        previous = genesis
        # At most192 symbolic hashes; never enumerate another obligation.
        for h in range(hour+1):
            body = dict(context,relative_hour=h,phase='enrollment' if h<168 else 'followup',
                predecessor_slot_id=previous,max_attempts=1)
            identity = io.digest(io.encode(body))
            if h==hour: break
            previous = identity
        candidate_context = dict(schema=SCHEMA,role='N_candidate_class',split=p['split'],
            source_pair=pair,static_profile=profile,implementation_sha256=summary['implementation_sha256'])
        candidate_previous = io.digest(io.encode(dict(candidate_context,kind='candidate_genesis')))
        for h in range(hour+1):
            candidate = io.digest(io.encode(dict(candidate_context,relative_hour=h,predecessor_class=candidate_previous)))
            if h==hour: break
            candidate_previous = candidate
        edge = dict(kind='declared_genesis' if hour==0 else 'causal_predecessor',
            parent=previous,solver_reuse_edge=False)
        return dict(kind='potential_N_slot',slot_id=identity,slot_ordinal=slot_ordinal,record=body,
            edges=[edge],activation='bootstrap_attempt_before_source' if hour==0 else 'runtime_owner_need_after_predecessor',
            training_frozen_barrier_required=p['split']=='holdout',
            candidate_class_id=candidate,candidate_predecessor_class=candidate_previous,
            candidate_class_is_reuse_proof=False,resource_credit_applied=False,
            source_identity=None,before_identity=None,normal_input_identity=None,causal_key=None,
            runtime_task_id=None,process_identity=None,outcome=None,resource_profile_id=None,
            eligible_for_execution=False)


def _views():
    baseline = io.read_stable(ROOT/BASELINE,proof.CAP)
    if io.digest(baseline[0])!=BASELINE_PIN: raise ValueError('baseline pin differs')
    names = [(ROOT/PROOF,PROOF_PIN),(Path(__file__),None),(Path(proof.__file__),None),
             (ROOT/BASELINE,BASELINE_PIN)]
    names += [(ROOT/name,pin) for name,pin in json.loads(baseline[0])['files_sha256'].items()]
    views = {}
    for path,pin in names:
        view = io.read_stable(path,proof.exclusion.INPUT_CAP)
        if pin is not None and io.digest(view[0])!=pin: raise ValueError('pinned proof manifest differs')
        views[path] = view
    return views


def build(profile):
    views = _views()
    implementation = io.digest(io.encode({(p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else p.as_posix()):io.digest(v[0])
        for p,v in views.items() if p!=ROOT/PROOF}))
    result = _compile(views[ROOT/PROOF][0],profile,implementation)
    for path,view in views.items():
        if io.read_stable(path,proof.exclusion.INPUT_CAP)!=view: raise ValueError('symbolic manifest input changed')
    return result


def inspect(path,*,expected_sha256):
    path = Path(path)
    raw,stamp = io.read_stable(path,proof.CAP)
    if io.digest(raw)!=io.pin(expected_sha256): raise ValueError('symbolic manifest external pin differs')
    value = json.loads(raw)
    rebuilt = build(StaticProfile(**value['declared_static_profile']))
    if raw!=rebuilt.raw: raise ValueError('symbolic manifest reconstruction differs')
    if io.read_stable(path,proof.CAP)!=(raw,stamp): raise ValueError('symbolic manifest changed during inspect')
    return rebuilt
