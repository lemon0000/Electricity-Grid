"""Source-bound conditional counts for the original full F; no target execution.

Counts below are a reviewed static path model, not instrumentation or admission.
Only this module's stdlib code executes. Bound project programs are read/parsed.
"""
import ast
from hashlib import sha256
import json
from pathlib import Path


SOURCE_PINS = {
    'experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v40.py': (43645, 'bd049afa324250213d0496a2c4ab0fb4c4c408676507955e6c117a80332f1d2b'),
    'experiments/staged_rts24_saved_fresh_complete_bootstrap_validation_v1.py': (73927, '762224af9656c5dfaa75fa4594bf9d14aea1c1bf37af637aabfb1ad79879f33a'),
    'experiments/staged_rts24_saved_fresh_parent_quiet_actor_v2.py': (22359, 'c6c647b5a9237a63ded591e24674755e3b141343594ae234360d23f22b82fa3b'),
    'experiments/staged_rts24_saved_fresh_retained_producer_v6.py': (65268, '404c9f780d9078d73af5ba35498a0e3d4502c5def367e8682789573666ebb0fd'),
    'experiments/staged_rts24_saved_fresh_producer_bootstrap_v7.py': (29378, '57e9697d5bba7d740a8c845feafc8f3b62aef98bd8c4904459b32e5607435aa4'),
    'experiments/staged_rts24_saved_fresh_bootstrap_actor_v2.py': (15114, '7d8b69f936b3ad71bb01a6c7318571f6bdb5459589f26f782bd2d3f9c586517c'),
    'experiments/staged_rts24_saved_fresh_complete_producer_v2.py': (9264, '0362508e192c116eda5f4428ccbe53969ea23f3e24dc83f132db5e2d53b877f3'),
    'experiments/staged_rts24_saved_fresh_pre_entry_lease_v44.py': (69895, '43f0b2c9add534a4a4fb74413c29fe4649d9a696475a73e80572a7eef15603cc'),
    'experiments/staged_rts24_saved_fresh_entry_namespace_consumer_v4.py': (42798, '2a5963ae94ab86dbeb26d881f70ec688258b319f1696ce52c292c374e5deac66'),
    'experiments/staged_rts24_saved_fresh_producer_project_graph_v3.py': (32664, '4b429203c2b886124d1d6c87a0346d97d4bd081adcab4ed25cc9c5a1fd6ccc4e'),
    'experiments/staged_rts24_saved_fresh_p1_permission_v1.py': (18952, '0fa4420f1fb3ccfd70f234d7276de79bd780ce796b708ea58c912ebb9a74f9c7'),
    'experiments/staged_rts24_saved_fresh_prebound_expectation_code_v3.py': (10526, 'f0fc5fc4c0f45fa6d962593da7b5e752b3568179a4d94213b2db5f02aa1758e6'),
    'experiments/staged_rts24_saved_fresh_producer_packet_v2.py': (15478, 'aa2309c1e6b815c9d6d688bdf8ba3e314bb696ed7cb63b474f96a3bf176d9723'),
    'experiments/staged_rts24_saved_fresh_producer_parent_reopen_v2.py': (6025, '76fd313beb7a4db8ce5f6ada89d6619ccd64c98ae7720c18c894786c261c24ed'),
    'experiments/staged_rts24_saved_fresh_adoption_v1.py': (441013, '3bc91e1b3681c588ba73a44fad73357be60fc4aa2c925a89acdf8bf9d9b53348'),
    'src/staged_rts24_saved_fresh_adoption_v1.py': (17247, '26b919e385f9d7042587db490dab694fc5bf1643665ab4bf94a1c9bac8087396'),
    'docs/plan/staged_deliverability_c_saved_fresh_adoption_scope_budget_v1.md': (23924, 'a1aa2abdcfdbd15958f703088fa94ed79a17cd830b9f6d5a1571a5f75e6a4a98'),
    'docs/plan/staged_deliverability_c_saved_fresh_invocation_development_contract_v1.md': (9214, 'e02bec04f0a84064c9d624f76ecb4663ea7a519172b458523d3068dd0b39b125'),
    'docs/plan/staged_deliverability_c_scientific_adoption_dag_v1.md': (5719, 'a55856ae0ca9b201ca7fe3c6ddafa842dc047a0ce9732495d66eea5b38495d16'),
    'results/tables/staged_rts24_saved_journal_check_v1_non_authoritative/validation_report.md': (3804, '04d320a1670bcf692ad8f3a73cc22e2d0de2e0092a5976fcd327600ed216f184'),
}
ENTRY = 'experiments/staged_rts24_saved_fresh_adoption_v1.py'
VALIDATOR = 'experiments/staged_rts24_saved_fresh_complete_bootstrap_validation_v1.py'
PERMISSION = 'experiments/staged_rts24_saved_fresh_p1_permission_v1.py'
SCOPE = 'saved_P1_actual_21_and_journal_5h'
METRICS = tuple(('state_sha state_cas_sha summary independent_audit scientific_outcome publication_outcome '
                 'terminal_entry_present state_certainty closed_entry_present unaccepted_attempt failure '
                 'pending_terminal_checkpoint pending_cas_objects unreferenced_final_cas_objects genesis_sha '
                 'head_sha final_entries saved_objects resume_permitted').split())
STAGES = dict(prepare=10, parent=45, fresh=40, inner_quiesce=5, inner_terminal=5,
              parent_compare=15, outer_quiesce=5, outer_terminal=10, final_check=15,
              final_publish=15, failure=15)
FULL_DAG = (
    ('F0', (), 'external_context_ack_and_outer_capture_release'),
    ('P', ('F0',), 'independent_parent_B_C_E_21_points_5_hours'),
    ('F1', ('P',), 'reserve_once_capture_inner_owner_before_release'),
    ('Q', ('F1',), 'independent_fresh_B_C_E_21_points_5_hours'),
    ('F2', ('Q',), 'inner_full_job_quiet_before_fresh_content'),
    ('F3', ('F2',), 'full_metrics_compare_F_G1_candidate_parent_exit'),
    ('F4', ('F3',), 'outer_full_job_quiet_before_candidate_content'),
    ('F5', ('F4',), 'supervisor_binds_both_owners_metrics_F_G2'),
    ('F6', ('F5',), 'create_only_readback_F_G3_final_accounting'),
)
FALSE_FIELDS = tuple(('run_authority resource_admission actual_F formal_result scientific_evidence_adopted '
                      'production_seal saved_P1_fresh_process_verified saved_P1_parent_adoption_verified '
                      'whole_workflow_budget_admitted whole_workflow_performance_review_complete').split())


def require(value, message):
    if not value:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')


def pin(raw):
    return len(raw), sha256(raw).hexdigest()


def literal(node):
    """Decode only the small literal grammar needed here; never eval/compile."""
    if type(node) is ast.Constant and type(node.value) in (str, int, bool, type(None)):
        return node.value
    if type(node) in (ast.Tuple, ast.List):
        values = [literal(item) for item in node.elts]
        return tuple(values) if type(node) is ast.Tuple else values
    if type(node) is ast.BinOp and type(node.op) in (ast.Pow, ast.Mult):
        left, right = literal(node.left), literal(node.right)
        require(type(left) is int and type(right) is int and 0 <= left <= 2**31
                and 0 <= right <= (64 if type(node.op) is ast.Pow else 2**31), 'bounded integer expression required')
        return left**right if type(node.op) is ast.Pow else left*right
    if type(node) is ast.Call and type(node.func) is ast.Name and node.func.id == 'dict' and not node.args:
        names = [item.arg for item in node.keywords]
        require(None not in names and len(names) == len(set(names)), 'closed literal dict required')
        return {item.arg: literal(item.value) for item in node.keywords}
    if type(node) is ast.Call and type(node.func) is ast.Name and node.func.id == 'tuple' and len(node.args) == 1 and not node.keywords:
        return tuple(literal(node.args[0]))
    if type(node) is ast.Call and type(node.func) is ast.Attribute and node.func.attr == 'split' and not node.args and not node.keywords:
        value = literal(node.func.value)
        require(type(value) is str, 'literal string required')
        return value.split()
    raise ValueError('expression is outside the static literal grammar')


def assignment(tree, name):
    matches = [node.value for node in tree.body if type(node) is ast.Assign
               and any(type(target) is ast.Name and target.id == name for target in node.targets)]
    require(len(matches) == 1, 'one top-level assignment required: ' + name)
    return literal(matches[0])


def node_at(tree, name):
    node = tree
    for part in name.split('.'):
        matches = [child for child in node.body if type(child) in (ast.ClassDef, ast.FunctionDef) and child.name == part]
        require(len(matches) == 1, 'one source definition required: ' + name)
        node = matches[0]
    return node


def verify_sources(root, raw_sources=None):
    root = Path(root)
    if raw_sources is None:
        raw_sources = {name: (root/name).read_bytes() for name in SOURCE_PINS}
    require(type(raw_sources) is dict and set(raw_sources) == set(SOURCE_PINS), 'exact source set required')
    trees = {}
    for name, expected in SOURCE_PINS.items():
        raw = raw_sources[name]
        require(type(raw) is bytes and pin(raw) == expected, 'bound source bytes differ: ' + name)
        if name.endswith('.py'):
            trees[name] = ast.parse(raw, filename=name)
    return trees


def checked_dag(rows):
    require(type(rows) is tuple and len(rows) == len(FULL_DAG), 'complete original F DAG required')
    seen = set()
    for row in rows:
        require(type(row) is tuple and len(row) == 3, 'closed stage row required')
        name, dependencies, purpose = row
        require(type(name) is str and name not in seen and type(dependencies) is tuple
                and len(dependencies) == len(set(dependencies)) and set(dependencies) <= seen
                and type(purpose) is str and purpose, 'ordered unique DAG required')
        seen.add(name)
    require(rows == FULL_DAG, 'scope/stage dependencies differ from original F')
    return [dict(stage=name, after=list(deps), purpose=purpose) for name, deps, purpose in rows]


def integer(value, cap, name):
    require(type(value) is int and 0 <= value <= cap, name + ' must be a bounded integer')
    return value


def parent_projection(disk_files=0, disk_bytes=0):
    """One hypothetical accepted producer with all historical files available.

    Defaults are currently unreachable. D is the startup profile disk set, not
    683 P1 files. Raw IO here means logical read invocations, not OS operations.
    """
    d = integer(disk_files, 128, 'startup disk files')
    b = integer(disk_bytes, 32*1024**2, 'startup disk bytes')
    require(d > 0 or b == 0, 'nonzero bytes require an observed disk file')
    require(b <= d*8*1024**2, 'startup per-file byte cap differs')
    rows = (
        ('discovery', 7, 24, 87), ('import_discovery', 4, 31, 98),
        ('producer_capture', 1, 38, 109), ('producer_pre_release_post_quiet', 2, 33, 99),
    )
    calls = sum(n*c for _, n, c, _ in rows)
    reads = sum(n*r for _, n, _, r in rows)
    return dict(
        scope='one_Parent40_leaf_conditional_success_not_full_F', currently_reachable=False,
        context_rows=[dict(case=k, multiplicity=n, calls=c, content_reads=r) for k, n, c, r in rows],
        input_contexts=sum(row[1] for row in rows), context_calls=calls, context_content_reads=reads,
        generic_calls_internal=calls+22+1+1+15, generic_calls_via_source_dispatch=calls+22+1+1+15+2,
        content_reads_internal=reads+10+5+1+1+7+7*d, content_reads_with_outer_parent_source=reads+25+7*d,
        startup_disk_reads=7*d, startup_disk_read_bytes=7*b,
        source49_reads=14*49, source_control_reads=14, exe_runtime_reads=14*7,
        audit_saved=11, open_saved_receipt_calls=22, saved_receipt_json_decodes=44,
        replay=12, child_decode_calls=23,
        memory_guard_checks=23, source_module=26, transport=14,
        program_internal=6, program_including_source_dispatch=7,
        parent_packet_callbacks=dict(packet_decode=1, packet_unwire=1, packet_restore_explicit=1),
        parent_packet_restore_physical=2, parent_packet_decode_physical=3,
        parent_packet_zlib_decompress=1, physical_parent_P1_reads=0,
        model_method='source_bound_manual_recursion_count_not_runtime_instrumentation')


def p1_scenarios():
    """Conditional integration subtotals. Reuse rows are unimplemented proofs."""
    files = 683
    replay_side = files + 2152 + 801 + files
    full_base = 2*replay_side + 4*files
    lc = 53 + 3*files
    cases = (
        ('original_two_replays_four_F_inventories', full_base, False),
        ('one_uncomposed_LC_and_independent_Parent_inventory', full_base+lc+files, False),
        ('two_uncomposed_LC_and_independent_Parent_inventory', full_base+2*lc+files, False),
        ('conditional_same_owner_held_input_reuse', full_base+lc+files-files, True),
        ('conditional_held_input_and_E_final_to_LC_G2_reuse', full_base+lc+files-2*files, True),
        ('conditional_one_LC_three_proven_inventory_reuses', full_base+lc+files-3*files, True),
        ('conditional_two_LC_five_proven_inventory_reuses', full_base+2*lc+files-5*files, True),
    )
    return dict(
        unit='logical_P1_content_read_calls', original_cap=12500, E_success_per_side=replay_side,
        E_components=dict(capture_inventory=files, B_points=2152, E_journal=801, final_inventory=files),
        LC6_success=lc, LC6_components=dict(expectation=53, hold_inventory=files, LC_G2=files, LC_G3=files),
        whole_workflow_upper_bound=None, failure_read_upper_bound=None,
        failure_extra_full_inventory_per_adapter_replay_catch=files,
        scenarios=[dict(name=name, conditional_subtotal=value, exceeds_cap_by=max(value-12500, 0),
                        arithmetic_room=12500-value, requires_unimplemented_reuse=reuse,
                        unknown_additional_cost=True, budget_admitted=False) for name, value, reuse in cases],
        reuse_conditions=['same_exact_live_HeldInput_owner_thread_source_root_anchor_and_raw_map',
                          'same_physical_E_final_inventory_commits_LC_G2_at_same_window',
                          'same_authority_and_window_for_any_Parent_to_F_inventory_replacement',
                          'fresh_root_ancestor_identity_bookends_and_complete_failure_evidence'],
        inventory_domains_distinct=['LC.G0', 'LC.G2', 'LC.G3', 'F.G0', 'F.G1', 'F.G2', 'F.G3'],
        inventory_domain_list_scope='LC_and_F_only_E_and_Parent_windows_separately_not_exhaustive')


def lifecycle_projection():
    entries = 1+7+6+6+3
    return dict(scope='one_LC6_Helper7_success_leaf_not_full_runtime_or_F',
                operation_entries=dict(claim=1, run=7, LC_G2=6, LC_G3=6, close=3),
                LC_entry=entries, runtime_entry_from_LC=entries+1+2+2+1,
                runtime_source_bookend_from_LC=entries+1,
                graph_capture=1, graph_check=entries+1+1+5, graph_physical_builds=1+entries+1+1+5,
                Helper_runtime_entry_before_operations=8, Helper_runtime_entry_in_operations=5,
                Helper_runtime_entry=13, runtime_entry_from_LC_and_Helper=entries+6+8+5,
                excludes=['Loader5_two_runtime_entries_and_source_bookends', 'Core_import_handoff_and_namespace_internal_calls',
                          'scientific_B_C_E_runtime_callbacks', 'other_full_F_processes', 'failure_paths'],
                whole_runtime_entry_upper_bound=None, graph_nodes_and_build_seconds=None)


def source_projection(disk_files=0):
    """Uncomposed conditional additions, not a future implementation lower bound.

    4176 is valid only while the old two-sided source/runtime path is retained.
    Source-control reads are shown both outside and inside the 6500 category;
    no category decision, integration reuse or new cap is authorized here.
    """
    d = integer(disk_files, 128, 'startup disk files')
    strict_per_context = 3+49+7+3+22
    parent = 14*strict_per_context+5+1+1+7+1+7*d
    lc = 24*49
    cases = (('old_two_sided_source_runtime_base', 4176),
             ('one_uncomposed_LC_and_Parent', 4176+parent+lc),
             ('two_uncomposed_LC_and_Parent', 4176+parent+2*lc))
    return dict(unit='logical_source_exe_anchor_content_read_calls', original_cap=6500,
                original_two_sided_conditional_base=4176, startup_disk_files=d,
                original_two_sided_anchor_tail_reads_separate=2,
                Parent_strict_per_context=strict_per_context, Parent_strict=parent,
                Parent_source_control_separate=14, LC_source_bookend_calls=24,
                LC_source_files_per_bookend=49, LC_source_bookend_reads=lc,
                category_of_source_control_resolved=False, whole_workflow_upper_bound=None,
                scenarios=[dict(name=name, strict_conditional_subtotal=value,
                                exceeds_cap_by=max(value-6500, 0),
                                with_Parent_source_control=value+(0 if name == cases[0][0] else 14),
                                with_old_anchor_tail=value+2,
                                unknown_additional_cost=True, budget_admitted=False) for name, value in cases],
                requires=['unchanged_old_two_sided_path_for_4176', 'independent_additions_without_proven_reuse'],
                excluded_unknowns=['adapter_sources_loaded_module_rereads', 'other_Loader_Core_Helper_callbacks',
                                   'genuine_authorization_profile_and_outer_costs', 'failure_and_publication_tail'])


def stage_projection(stages):
    require(type(stages) is dict and stages == STAGES and all(type(value) is int for value in stages.values()), 'frozen stage allocation required')
    return dict(allocations=dict(stages), global_seconds=sum(stages.values()),
                success_allocation_seconds=sum(value for key, value in stages.items() if key != 'failure'),
                failure_reserve_seconds=stages['failure'], fresh_envelope_seconds=sum(stages[key] for key in ('fresh', 'inner_quiesce', 'inner_terminal')),
                parent_envelope_seconds=sum(stages[key] for key in ('parent', 'fresh', 'inner_quiesce', 'inner_terminal', 'parent_compare', 'outer_quiesce', 'outer_terminal')),
                single_absolute_clock=True, phase_reset_allowed=False, timeout_is_ETA=False,
                arming_wall_seconds=None, measured_whole_workflow_wall_seconds=None, hard_stop_verified=False)


def source_witnesses(trees):
    selected = {
        'runtime_handoff_parent_v40': ('program', 'dependencies', 'call', 'input_context', 'capture', 'run_owned', 'source_dispatch'),
        'complete_bootstrap_validation_v1': ('startup_relation', 'profile_relation', 'audit_saved', 'open_saved_receipt', 'replay', 'replay_retained'),
        'retained_producer_v6': ('entry', 'prepare', 'invoke', '_bookend', '_produce', '_close'),
        'producer_bootstrap_v7': ('new_import_bridge', '_begin', 'check', 'finalize_project_construction', '_make_bundle', 'verify_bundle', 'bundle_dispatch'),
        'pre_entry_lease_v44': ('LocalRuntimeInputs.entry', 'LocalRuntimeInputs.source_bookend', 'LocalRuntimeInputs.close'),
        'producer_project_graph_v3': ('capture', 'check', '_build'),
        'bootstrap_actor_v2': ('dispatch',),
        'producer_packet_v2': ('packet_restore', 'packet_unwire'),
        'producer_parent_reopen_v2': ('audit_producer_data',),
    }
    result = {}
    for suffix, names in selected.items():
        path = 'experiments/staged_rts24_saved_fresh_' + suffix + '.py'
        for name in names:
            node = node_at(trees[path], name)
            result[path + ':' + name] = dict(line=node.lineno, end_line=node.end_lineno,
                                             ast_sha256=sha256(ast.dump(node, include_attributes=False).encode()).hexdigest())
    for name in ('capture', 'hold', 'bookend', 'replay', '_replay', 'compare_payloads'):
        path = 'src/staged_rts24_saved_fresh_adoption_v1.py'
        node = node_at(trees[path], name)
        result[path + ':' + name] = dict(line=node.lineno, end_line=node.end_lineno,
                                         ast_sha256=sha256(ast.dump(node, include_attributes=False).encode()).hexdigest())
    return result


def report(root, raw_sources=None):
    trees = verify_sources(root, raw_sources)
    entry, validator, permission = trees[ENTRY], trees[VALIDATOR], trees[PERMISSION]
    caps = assignment(entry, 'CAPS')
    require(assignment(validator, '_EXACT_CONTRACTS') == (('discovery', ()), ('import_discovery', None), ('producer', None)), 'default exact graphs differ')
    require(assignment(validator, '_PROFILE_ACCEPTED_ANCHOR') is None
            and assignment(permission, 'OUTER_BINDING') is None
            and assignment(entry, '_SAVED_LAUNCH_ISSUER') is None, 'closed authorization roots differ')
    issuer = node_at(entry, '_SavedLaunchIssuer')
    require(all(type(node_at(issuer, name).body[0]) is ast.Raise for name in ('__new__', 'check')), 'legacy issuer must stay closed')
    targets = assignment(entry, 'TARGETS')
    require(len(targets) == len(set(targets)) == 17, 'full F output target set differs')
    require(caps['wall_seconds'] == 180 and caps['output_bytes'] == 8*1024**2
            and caps['files'] == 64 and caps['record_bytes'] == 131072, 'frozen full F design caps differ')
    unknowns = tuple(('genuine_external_grant_and_parent_read_grant_cost actual_profile_graph_size_and_stop_cost '
                      'startup_import_discovery_admission_multiplicity full_B_C_E_in_new_coordinator '
                      'source_runtime_anchor_full_chain_reads LC_and_F_inventory_window_integration '
                      'failure_partial_reads_cleanup_retirement_cost input_directory_identity_and_metadata_cost '
                      'packet_raw_wire_report_peak_and_canonical_encoding outer_inner_launch_and_mailbox_cost '
                      'publication_readback_final_G3_and_host_tail arming_and_sync_kernel_hard_stop '
                      'whole_tree_plus_host_continuous_memory_and_storage_peak').split())
    return dict(
        schema='staged_saved_F_whole_workflow_static_cost_v1', authority='DRAFT_NONAUTHORITATIVE',
        acceptance_scope='static_source_bound_DAG_and_conditional_arithmetic_only', scope=SCOPE,
        source49_epoch=assignment(permission, 'SOURCE_EPOCH'),
        source_pins={name: dict(bytes=n, sha256=s) for name, (n, s) in SOURCE_PINS.items()}, source_witnesses=source_witnesses(trees),
        dag=checked_dag(FULL_DAG), scientific_scope=dict(independent_replays=2, points_each=21, accepted_hours_each=5, CAS_each=130,
            P1_files=683, P1_bytes=2950863, journal_files=137, journal_bytes=427629,
            newly_executed_simulated_hours=0, metric_fields=list(METRICS)),
        original_conditional_base=dict(compile=84, snapshot=42, imports=42, prepare=40, propose=40,
            execution_audit=66, historical_row_audit=170, typed_pack=310, source_runtime_reads=4176),
        original_logical_caps=dict(compile=84, snapshot=42, imports=42, typed_pack=320,
            P1_content_reads=12500, source_exe_anchor_content_reads=6500),
        parent_projection_range=[parent_projection(), parent_projection(128, 32*1024**2)],
        P1_projection=p1_scenarios(), lifecycle_projection=lifecycle_projection(),
        source_exe_anchor_projection_range=[source_projection(0), source_projection(128)],
        stage_projection=stage_projection(assignment(entry, 'STAGE_SECONDS')),
        resource_design_caps=caps, output_targets=list(targets), terminal_record_reserve=dict(records=4, bytes=4*caps['record_bytes'], included_in_output_cap=True),
        memory_policy='deduplicate_nested_Job_members_by_pid_creation_and_include_host', measured_whole_workflow_peak_bytes=None,
        unknown_costs={key: None for key in unknowns},
        default_blockers=['no_external_profile_anchor', 'no_import_exact_graph', 'no_producer_exact_graph',
                          'Permission1_public_issue_verify_claim_closed', 'Source49_legacy_issuer_closed',
                          'Parent40_has_no_launcher_or_P1_reader', 'whole_workflow_costs_and_failure_bounds_open'],
        **{key: False for key in FALSE_FIELDS})


if __name__ == '__main__':
    print(canonical(report(Path(__file__).absolute().parents[1])).decode())
