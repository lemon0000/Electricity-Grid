"""Ordinary static cost checks: no project program or child is executed."""
import ast
from collections import Counter
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).absolute().parents[1]
SPEC = importlib.util.spec_from_file_location('_static_F_cost', ROOT/'experiments/staged_rts24_saved_fresh_workflow_cost_model_v1.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class WorkflowCostTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = {name: (ROOT/name).read_bytes() for name in M.SOURCE_PINS}
        cls.trees = M.verify_sources(ROOT, cls.raw)
        cls.full = M.report(ROOT, cls.raw)

    def test_01_literal_grammar_cannot_call_a_program(self):
        self.assertEqual(M.literal(ast.parse('dict(a=2*1024**3,b=tuple("a b".split()))', mode='eval').body),
                         {'a': 2147483648, 'b': ('a', 'b')})
        for text in ('__import__("os").system("never")', 'dict(**x)', 'tuple(x)', '1 << 20', '2**999999', 'dict(a=1,a=2)'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                M.literal(ast.parse(text, mode='eval').body)

    def test_02_source_mutation_missing_extra_and_nonbytes_rejected(self):
        name = M.ENTRY
        for mode in ('mutate', 'missing', 'extra', 'nonbytes'):
            altered = dict(self.raw)
            if mode == 'mutate':
                altered[name] += b'\nraise RuntimeError("must not execute")\n'
            elif mode == 'missing':
                del altered[name]
            elif mode == 'extra':
                altered['extra.py'] = b'pass'
            else:
                altered[name] = bytearray(altered[name])
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                M.verify_sources(ROOT, altered)

    def test_03_full_DAG_rejects_dropped_reordered_or_self_dependent_stage(self):
        self.assertEqual([row['stage'] for row in M.checked_dag(M.FULL_DAG)], ['F0', 'P', 'F1', 'Q', 'F2', 'F3', 'F4', 'F5', 'F6'])
        bad_order = list(M.FULL_DAG)
        bad_order[4], bad_order[5] = bad_order[5], bad_order[4]
        self_dep = list(M.FULL_DAG)
        self_dep[4] = ('F2', ('F2',), self_dep[4][2])
        for rows in (M.FULL_DAG[:-1], tuple(bad_order), tuple(self_dep)):
            with self.assertRaises(ValueError):
                M.checked_dag(rows)

    def test_04_independent_expansion_of_historical_contexts(self):
        # Each I audit visits its own context and one earlier D audit.
        # Each of three P windows visits D and I; live P replay visits I again.
        def historical(kind):
            visits = Counter({kind: 1})
            if kind == 'I':
                visits.update(historical('D'))
            return visits
        visits = Counter()
        for _ in range(3):
            visits.update({'P': 1})
            visits.update(historical('D'))
            visits.update(historical('I'))
        visits.update(historical('I'))
        result = M.parent_projection()
        by_kind = Counter()
        for row in result['context_rows']:
            kind = {'discovery': 'D', 'import_discovery': 'I'}.get(row['case'], 'P')
            by_kind[kind] += row['multiplicity']
        self.assertEqual(by_kind, visits)
        self.assertEqual((result['input_contexts'], result['audit_saved'], result['replay']), (14, 11, 12))
        self.assertEqual((result['context_calls'], result['context_content_reads']), (396, 1308))
        self.assertEqual((result['generic_calls_internal'], result['generic_calls_via_source_dispatch']), (435, 437))

    def test_05_disk_cost_is_monotone_and_limits_are_not_authority(self):
        previous = None
        for count in (0, 1, 4, 64, 128):
            row = M.parent_projection(count, min(count*8*1024**2, 32*1024**2))
            self.assertEqual(row['content_reads_with_outer_parent_source']-row['content_reads_internal'], 1)
            if previous:
                self.assertEqual(row['content_reads_internal']-previous[1], 7*(count-previous[0]))
            previous = count, row['content_reads_internal']
            self.assertFalse(row['currently_reachable'])
        self.assertEqual(previous[1], 2228)
        self.assertEqual(row['startup_disk_read_bytes'], 234881024)

    def test_06_disk_validation_preserves_per_file_and_aggregate_caps(self):
        for count, size in ((True, 0), (1.0, 0), (-1, 0), (129, 0), (0, 1), (1, 9*1024**2), (4, 32*1024**2+1)):
            with self.subTest(count=count, size=size), self.assertRaises(ValueError):
                M.parent_projection(count, size)
        self.assertEqual(M.parent_projection(1, 0)['startup_disk_reads'], 7)

    def test_07_packet_physical_recursion_is_counted(self):
        codec = self.trees['experiments/staged_rts24_saved_fresh_producer_packet_v2.py']
        reopen = self.trees['experiments/staged_rts24_saved_fresh_producer_parent_reopen_v2.py']
        def calls(node, name):
            return sum(type(item) is ast.Call and
                       ((type(item.func) is ast.Name and item.func.id == name) or
                        (type(item.func) is ast.Attribute and item.func.attr == name)) for item in ast.walk(node))
        top = M.node_at(reopen, 'audit_producer_data')
        restores = calls(top, 'packet_restore') + calls(top, 'packet_unwire')*calls(M.node_at(codec, 'packet_unwire'), 'packet_restore')
        decodes = calls(top, 'packet_decode') + restores*calls(M.node_at(codec, 'packet_restore'), 'packet_decode')
        row = M.parent_projection()
        self.assertEqual((restores, decodes), (row['parent_packet_restore_physical'], row['parent_packet_decode_physical']))
        self.assertEqual((row['program_internal'], row['program_including_source_dispatch']), (6, 7))
        opened = M.node_at(self.trees[M.VALIDATOR], 'open_saved_receipt')
        self.assertEqual(row['saved_receipt_json_decodes'], row['open_saved_receipt_calls']*calls(opened, 'unique_json'))
        self.assertEqual(row['saved_receipt_json_decodes'], 44)

    def test_08_event_oracle_finds_uncomposed_P1_overrun(self):
        # A virtual read event for each logical read, no P1 paths or disk IO.
        E = ['capture']*683 + ['B']*2152 + ['journal']*801 + ['final']*683
        events = E*2 + ['F.G']*(4*683)
        self.assertEqual(len(events), 11370)
        LC = ['expectation']*53 + ['LC.inventory']*(3*683)
        events += LC + ['Parent.inventory']*683
        cases = self.full['P1_projection']['scenarios']
        self.assertEqual(len(events), cases[1]['conditional_subtotal'])
        self.assertEqual(len(events)-12500, 1655)
        self.assertEqual(cases[2]['conditional_subtotal'], len(events)+len(LC))
        # Strict source calls exclude manifest/profile/control data; no OS IO claim.
        source = ['old_B_C_E']*4176
        for _ in range(14):
            source += ['transport']*3 + ['selected_source']*49 + ['exe_runtime']*7 + ['attachments']*3 + ['helpers']*22
        source += ['dependency']*5 + ['drain', 'codec'] + ['startup_Core']*7 + ['outer_Parent']
        source += ['LC_source']*(24*49)
        source_row = self.full['source_exe_anchor_projection_range'][0]
        self.assertEqual(len(source), source_row['scenarios'][1]['strict_conditional_subtotal'])
        self.assertEqual(len(source)-6500, 43)

    def test_09_two_proposed_reuses_still_exceed_cap(self):
        rows = self.full['P1_projection']['scenarios']
        self.assertEqual([row['conditional_subtotal'] for row in rows[3:]], [13472, 12789, 12106, 12842])
        self.assertEqual(rows[4]['exceeds_cap_by'], 289)
        self.assertEqual(rows[-1]['exceeds_cap_by'], 342)
        self.assertEqual(rows[5]['arithmetic_room'], 394)
        for row in rows:
            self.assertFalse(row['budget_admitted'])
            self.assertTrue(row['unknown_additional_cost'])
        minimum, maximum = self.full['source_exe_anchor_projection_range']
        self.assertEqual([row['strict_conditional_subtotal'] for row in minimum['scenarios']], [4176, 6543, 7719])
        self.assertEqual(maximum['scenarios'][1]['strict_conditional_subtotal']-minimum['scenarios'][1]['strict_conditional_subtotal'], 7*128)
        self.assertEqual(minimum['scenarios'][1]['with_Parent_source_control'], 6557)
        self.assertFalse(minimum['category_of_source_control_resolved'])
        for row in minimum['scenarios']+maximum['scenarios']:
            self.assertFalse(row['budget_admitted'])
        for bad in (True, -1, 129, 1.0):
            with self.assertRaises(ValueError):
                M.source_projection(bad)

    def test_10_failure_inventory_and_owner_windows_remain_distinct(self):
        row = self.full['P1_projection']
        self.assertIsNone(row['failure_read_upper_bound'])
        self.assertIsNone(row['whole_workflow_upper_bound'])
        self.assertEqual(row['failure_extra_full_inventory_per_adapter_replay_catch'], 683)
        self.assertEqual(len(set(row['inventory_domains_distinct'])), 7)
        self.assertIn('LC.G2', row['inventory_domains_distinct'])
        self.assertIn('F.G2', row['inventory_domains_distinct'])

    def test_11_all_five_bundle_operations_charge_runtime_entries(self):
        result = M.lifecycle_projection()
        operations = ('prepare', 'run', 'G2', 'G3', 'close')
        helper = ['entry']*8 + ['entry' for _ in operations]
        lc = [event for count in (1, 7, 6, 6, 3) for event in ['entry']*count]
        self.assertEqual(result['Helper_runtime_entry'], len(helper))
        self.assertEqual(result['runtime_entry_from_LC_and_Helper'], len(lc)+6+len(helper))
        self.assertEqual((result['LC_entry'], result['graph_check'], result['graph_physical_builds']), (23, 30, 31))
        self.assertIsNone(result['whole_runtime_entry_upper_bound'])

    def test_12_phase_allocation_cannot_renew_the_global_clock(self):
        row = self.full['stage_projection']
        self.assertEqual((row['global_seconds'], row['success_allocation_seconds'], row['failure_reserve_seconds']), (180, 165, 15))
        self.assertEqual((row['fresh_envelope_seconds'], row['parent_envelope_seconds']), (50, 125))
        for replacement in (41, 40.0, True):
            altered = dict(M.STAGES, fresh=replacement)
            with self.assertRaises(ValueError):
                M.stage_projection(altered)
        self.assertFalse(row['phase_reset_allowed'])
        self.assertFalse(row['hard_stop_verified'])

    def test_13_full_scope_metrics_targets_and_reserve_are_kept(self):
        scope = self.full['scientific_scope']
        self.assertEqual((scope['independent_replays'], scope['points_each'], scope['accepted_hours_each'], scope['CAS_each']), (2, 21, 5, 130))
        self.assertEqual(len(set(scope['metric_fields'])), 19)
        self.assertEqual(len(set(self.full['output_targets'])), 17)
        self.assertEqual(self.full['terminal_record_reserve']['bytes'], 524288)
        self.assertEqual(scope['newly_executed_simulated_hours'], 0)

    def test_14_real_gates_stay_closed_despite_arithmetic_room(self):
        self.assertGreater(self.full['P1_projection']['scenarios'][0]['arithmetic_room'], 0)
        for key in M.FALSE_FIELDS:
            self.assertIs(self.full[key], False)
        self.assertIsNone(M.assignment(self.trees[M.PERMISSION], 'OUTER_BINDING'))
        self.assertIsNone(M.assignment(self.trees[M.VALIDATOR], '_PROFILE_ACCEPTED_ANCHOR'))
        self.assertGreater(len(self.full['default_blockers']), 5)
        for value in self.full['unknown_costs'].values():
            self.assertIsNone(value)

    def test_15_report_parses_target_without_exec_import_or_P1_access(self):
        before = set(sys.modules)
        with patch('builtins.exec', side_effect=AssertionError('target execution forbidden')):
            value = M.report(ROOT/'absent_root_must_not_be_read', dict(self.raw))
        self.assertEqual(M.canonical(value), M.canonical(self.full))
        self.assertEqual(set(sys.modules), before)

    def test_16_witnesses_bind_actual_function_definitions(self):
        for key, row in self.full['source_witnesses'].items():
            path, name = key.split(':')
            node = M.node_at(self.trees[path], name)
            self.assertEqual((row['line'], row['end_line']), (node.lineno, node.end_lineno))
            self.assertEqual(len(row['ast_sha256']), 64)
        def direct_named_calls(node, name):
            return sum(type(item) is ast.Call and type(item.func) is ast.Name and item.func.id == name for item in ast.walk(node))
        graph = self.trees['experiments/staged_rts24_saved_fresh_producer_project_graph_v3.py']
        lc = self.full['lifecycle_projection']
        builds = lc['graph_capture']*direct_named_calls(M.node_at(graph, 'capture'), '_build')
        builds += lc['graph_check']*direct_named_calls(M.node_at(graph, 'check'), '_build')
        self.assertEqual(builds, lc['graph_physical_builds'])
        runtime = self.trees['experiments/staged_rts24_saved_fresh_pre_entry_lease_v44.py']
        one_bookend = direct_named_calls(M.node_at(runtime, 'LocalRuntimeInputs.source_bookend'), 'read_file')
        self.assertEqual(one_bookend*49*lc['runtime_source_bookend_from_LC'], self.full['source_exe_anchor_projection_range'][0]['LC_source_bookend_reads'])
        with self.assertRaises(ValueError):
            M.assignment(ast.parse('x=1\nx=2'), 'x')


if __name__ == '__main__':
    unittest.main()
