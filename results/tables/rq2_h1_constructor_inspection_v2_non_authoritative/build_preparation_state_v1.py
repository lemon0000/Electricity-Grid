"""Read-only evidence/count reconciliation for the full preparation objective."""
from hashlib import sha256
import json
from math import prod
from pathlib import Path
import sys
import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SOURCES = {
    'project_rules': ('agent.md', None),
    'current_plan': ('docs/plan/科研项目执行步骤.md', None),
    'blocker_register': ('docs/model_spec/blocker_register.md', None),
    'finite_v2_specification': ('docs/model_spec/rq2_finite_mechanism_protocol_candidate_v2.md', None),
    'protocol': ('configs/rq2_finite_mechanism_protocol_candidate_v2.DRAFT.yaml',
        '95eb158f0a8e6784d2af401e67164965543c98f42ff02b756c214982601e5430'),
    'obligation_manifest': ('results/tables/rq2_v2_obligation_manifest_v1_non_authoritative/obligation_manifest_v2_final.json',
        'befcfab8180a0124f15ad7652b085514c7aec6278e2b9d967e9885fc5a65fdd7'),
    'exclusion': ('results/tables/rq2_v2_cfe_exclusion_v1_non_authoritative/cell_exclusion_audit_v2_final.json',
        '2e8c9f07db03426c02f3c38f5f938231cb6ca47f30537ad0d740ed9e22341e7c'),
    'coverage': ('results/tables/rq2_finite_enrollment_support_v1_non_authoritative/coverage_168_24_verified.json',
        '29ba7f5662c3dee019f183104479d8fa354f726bea0e055ee456b3dd337042c4'),
    'source_work_units': ('results/tables/rq2_h1_source_replay_cost_v1_non_authoritative/call_dag_and_work_units.json', None),
    'source_previous_final': ('results/tables/rq2_h1_source_replay_cost_v1_non_authoritative/final_verification.json',
        '0f6903580082c705fd7d84a85c2e9102e699ea1a0c0f81f4205230e17e444cf2'),
    'phase_budget': ('results/tables/rq2_h1_phase_boundary_v1_non_authoritative/budget_audit_v1.json', None),
    'saved_3h_postcheck': ('results/tables/rq2_h1_cross_hour_outage_v1_non_authoritative/connected_03_postcheck.json', None),
    'current_3h_oracle': ('results/tables/rq2_h1_constructor_inspection_v2_non_authoritative/oracle_01/oracle_terminal.json', None),
    'current_3h_interpretation': ('results/tables/rq2_h1_constructor_inspection_v2_non_authoritative/oracle_01_interpretation.json', None),
    'current_short_comparison': ('results/tables/rq2_h1_constructor_inspection_v2_non_authoritative/short_comparison_01/comparison_terminal.json', None),
}


def main():
    label = sys.argv[1]
    if not label.replace('_', '').isalnum():
        raise ValueError('fresh label required')
    loaded, bindings = {}, {}
    for key, (relative, expected) in SOURCES.items():
        path = REPO / relative
        raw = path.read_bytes()
        pin = sha256(raw).hexdigest()
        if expected is not None and pin != expected:
            raise ValueError('saved top-level evidence differs: '+key)
        loaded[key] = (raw.decode('utf-8') if key in ('project_rules', 'current_plan', 'blocker_register', 'finite_v2_specification')
                       else yaml.safe_load(raw) if key == 'protocol' else json.loads(raw))
        bindings[str(path)] = pin
    protocol, manifest = loaded['protocol'], loaded['obligation_manifest']
    coverage, exclusion = loaded['coverage'], loaded['exclusion']
    axes, counts = manifest['catalog']['axes'], manifest['catalog']['identity_counts']
    assert {family: prod(len(v) for v in mapping.values()) for family, mapping in axes.items()} == counts
    assert len(manifest['nodes']) == 8020 and len(manifest['cells']) == 1900
    assert manifest['contradicted_cell_count'] == exclusion['contradicted_cell_count'] == 1856
    assert all(node['record'][key] is None for node in manifest['nodes']
        for key in ('solver_task_id', 'causal_key', 'runtime_request'))
    assert all(not edge['solver_reuse_edge'] for node in manifest['nodes'] for edge in node['record']['edges'])
    assert protocol['design']['expected_cell_count'] == 1900
    assert protocol['window']['enrollment_hours'] == 168 and protocol['window']['maximum_followup_hours'] == 24
    assert protocol['business_anchor']['episode_event_cap'] == 14
    remaining, affected = manifest['coverage']['remaining_identity_counts'], manifest['coverage']['affected_identity_counts']
    assert {k: remaining[k]+affected[k] for k in counts} == counts
    unknown_arm_cells = 1900+44*3
    assert remaining['training_lb'] == unknown_arm_cells*14644
    assert remaining['training_ub'] == unknown_arm_cells*14644*101
    assert coverage['summary']['training']['all_enrollment_pairs_retained'] == 14644
    assert coverage['summary']['holdout']['all_enrollment_pairs_retained'] == 14336
    assert coverage['summary']['training']['at_least_one_followup_source_missing'] == 604
    assert coverage['summary']['holdout']['at_least_one_followup_source_missing'] == 593
    assert not coverage['missing_tail_is_automatic_unresolved_outcome']
    gates = [
        ('finite_v2_preregistration', [], 'Explicit R4 successor for approved 1900-cell contract, complete inputs/estimands/thresholds/proofs/budgets; synchronize authority entry after evidence and approval.'),
        ('source_semantics', [], 'Retain full marginal support, predecessor identity, mechanism/derived coupling scope, current-only followup need and typed missing source.'),
        ('source_path_performance_and_freshness', ['source_semantics'], 'Complete justified source-path choice: validate/adopt a successor with real file/runtime/determinism/cleanup equivalence, or reject it and budget baseline/another valid path. H3 saved-identity reconstruction and fixed-order H1 timing now exist; original owner still rejects new schema.'),
        ('episode_workflow_budget', ['source_path_performance_and_freshness'], 'Full success/failure/callback/terminal/reopen/report/cleanup DAG; validated work/reuse counts and wall/RSS/storage/stop plan, operational event/holder capacity. No particular optimization is mandatory.'),
        ('phase_terminal_connection', ['episode_workflow_budget'], 'Genuine connected 167-to-168/debt/followup/early completion/due failure/missing-needed-source typed terminal, checkpoint, close and fresh-process replay.'),
        ('writer_and_crash_recovery', ['phase_terminal_connection'], 'Versioned writable rehydration, persistent atomic-live/poison/uncertain/crash windows; preserve all failed roots.'),
        ('native_producer_collector', [], 'Actual 0..191 carry/source and 232-stage producer/adapter/collector coverage under exact evidence grammar; no toy/native equivalence inference.'),
        ('rref_actual_and_invariants', [], 'Causal common N/Rref and per-arm A, shared capacity/availability/recovery/debt/power/service/F-X/nonanticipativity invariants and original numeric gates.'),
        ('operational_mapping_bridge', [], 'Exact preallocation/source conversion and operational adapter under approved roundoff/tolerance semantics; unresolved projection remains unresolved.'),
        ('solver_and_certificate_contract', [], 'Current solver interface/license capacity/actual target model scale; freeze threads/algorithm/formulation through objective-blind repeated pilot; actual primal/dual LB/UB, absolute and incumbent-relative gap, residual/timeout/incumbent/complete certificate contract.'),
        ('executable_task_and_reuse', ['rref_actual_and_invariants'], 'Materialized eligible causal runtime requests and proof-bound reuse edges, separating numeric/source/resource identities; existing 8020-node graph is logical only.'),
        ('capacity_training_holdout_binding', ['executable_task_and_reuse'], 'Same-contract offline LB superset proof and full causal training UB witness; B6 separate tracks/shared actual and frozen named-policy holdout; no D=1 fallback.'),
        ('complete_resource_registration', ['phase_terminal_connection', 'native_producer_collector', 'executable_task_and_reuse', 'capacity_training_holdout_binding', 'solver_and_certificate_contract'], 'Whole-study tasks, legal reductions, bounded serializer success/failure bytes, wall/RSS/archive/scratch/reserve/concurrency and concrete volume admission.'),
        ('formal_runner_result_publication', ['operational_mapping_bridge', 'capacity_training_holdout_binding'], 'Exact runner/config/code/input/env closure and one-shot lease; original raw output/manifest, atomic publication, interrupted/uncertain result handling, audit/report paths and no retry authority inference.'),
        ('seal_and_fresh_official_review', ['finite_v2_preregistration', 'writer_and_crash_recovery', 'complete_resource_registration', 'formal_runner_result_publication'], 'Close pre-seal findings, concrete approval where required, exact atomic production outer; then fresh independent official R3/R4 reviewer.'),
        ('specific_formal_native_authority', ['seal_and_fresh_official_review'], 'Separate explicit authorization for the concrete run package after all required gates; then clean process/root/input/dependency/environment check.'),
    ]
    protocol_gate_mapping = {
        'h1_common_reference_independent_implementation_validation': ['rref_actual_and_invariants', 'phase_terminal_connection'],
        'preallocation_operational_adapter_and_exact_conversion_audit': ['operational_mapping_bridge'],
        'enrollment_followup_and_same_contract_capacity_proofs': ['phase_terminal_connection', 'capacity_training_holdout_binding'],
        'task_inventory_compute_pilot_and_resource_registration': ['executable_task_and_reuse', 'solver_and_certificate_contract', 'complete_resource_registration'],
        'independent_review_of_exact_sealed_execution_candidate': ['seal_and_fresh_official_review'],
        'specific_formal_run_authority': ['specific_formal_native_authority'],
    }
    assert set(protocol_gate_mapping) == set(protocol['remaining_gates'])
    ids = {key for key, _, _ in gates}
    assert all(set(mapped) <= ids for mapped in protocol_gate_mapping.values())
    dependencies = {key: deps for key, deps, _ in gates}
    ancestors = set()
    def visit(key):
        if key in ancestors:
            return
        ancestors.add(key)
        for parent in dependencies[key]:
            visit(parent)
    visit('specific_formal_native_authority')
    assert ancestors == ids
    oracle, timing = loaded['current_3h_oracle'], loaded['current_short_comparison']
    assert oracle['exit_code'] == timing['exit_code'] == 0
    assert loaded['current_3h_interpretation']['direct_predecessor_raw_scientific_payload_read'] is False
    result = dict(status='DRAFT_NONAUTHORITATIVE', objective='complete_all_preparations_before_the_formal_experiment',
        objective_complete=False, scope='read_only_reconciliation_not_execution_admission',
        inventory_completeness='current_reconciled_draft_not_exhaustive_authoritative_acceptance',
        requirements_basis='agent sections 4 7 8 9 10 13 14 plus current plan blocker and approved finite-v2 specification',
        protocol_remaining_gate_mapping=protocol_gate_mapping,
        authority_entry_mismatch='agent section 4 still names older 46-cell preregistration; finite-v2 successor authority synchronization requires exact candidate review/approval',
        top_level_hashes_and_counts_verified=True, full_nested_source_reaudit_performed=False,
        current_development_evidence=dict(saved_3h_identity_bound_scientific_reconstruction=True,
            direct_predecessor_raw_scientific_payload_read=False, independently_implemented_scientific_oracle=False,
            static_identity_memo=False, shared_saved_manifest_resolver_seam_retained=True,
            real_manifest_sources_reaudited=False, source_successor_adopted=False,
            successor_3h_full_batch_seconds=oracle['successor_batch_seconds'],
            short_comparison_H=1, fixed_order=['old', 'new'], repetitions_per_implementation=1,
            short_batch_seconds=[row['elapsed_seconds'] for row in timing['calls']],
            production_speedup_established=False),
        frozen_protocol=dict(cells=1900, theta=19, alpha=100, capacity_grid_points=101,
            training_pairs_per_cell=14644, holdout_pairs_per_cell=14336, training_cell_pairs=27823600,
            E=168, maximum_F=24, scientific_business_episode_event_cap=14,
            complete_preregistration=protocol['complete_preregistration'], solver_budgets=protocol['capacity_evidence']['solver_budgets']),
        proof_reuse=dict(excluded_cfe_related_cells=1856, unknown_cfe_related_cells=44,
            network_only_cells_still_unknown=1900, remaining_planning_arm_cells=unknown_arm_cells,
            original_identity_counts=counts, proof_affected_identity_counts=affected, remaining_identity_counts=remaining,
            node_count=8020, executable_nodes=0, solver_reuse_edges=0, omitted_identities=0,
            native_calls_avoided=None, wall_time_saved=None, resource_discounts_applied=False,
            affected_is_not_individual_pair_dispatch_infeasibility=True,
            conditional_evaluations_are_not_executed_or_scored=True),
        source_support=dict(training_missing_at_least_one_tail=604, holdout_missing_at_least_one_tail=593,
            automatic_unresolved_from_missing_tail=False, registered_joint_coupling=coverage['registered_joint_coupling'],
            coverage_is_service_outcome=coverage['coverage_is_service_outcome']),
        current_episode_scaling=dict(condition='Original owner with extra terminal and reopen constructor/public inspect; no extra independent snapshot probes',
            T=192, reader_observations=1546, reader_prefix_hour_weight=149380,
            parent_traversals=3092, replayed_job_inspections=597520,
            toy_M5_stage_inspections=2987600, conditional_M232_stage_inspections=4*232*149380,
            scientific_native_solves_implied_by_replay_counts=0, normal_192h_stage_slots=192*232,
            min_operational_owner_events=576, old_toy_max_operational_events=32,
            observed_full_192h_execution=False, total_wall_admission_seconds=None, peak_rss_admission_bytes=None,
            total_storage_admission_bytes=None),
        gates=[dict(id=key, requires=deps, remaining_work=work, complete=False) for key, deps, work in gates],
        overall_performance_review_complete=False, long_connected_launch_admitted=False,
        resource_admission=False, formal_execution_ready=False, formal_result=False,
        native_execution_authorized=False, bindings=bindings)
    result['bindings'][str(Path(__file__))] = sha256(Path(__file__).read_bytes()).hexdigest()
    output = HERE / (label+'.json')
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(output=str(output), bindings=len(bindings), open_gates=len(gates),
        remaining_planning_arm_cells=unknown_arm_cells, objective_complete=False)))


if __name__ == '__main__':
    main()
