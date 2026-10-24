"""Bounded AST/byte evidence for explicitly scoped historical check reuse."""
import ast
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
PRIOR = ROOT/'results/tables/staged_rts24_saved_fresh_roles_v1_non_authoritative/checks_01'
ENTRY = 'experiments/staged_rts24_saved_fresh_adoption_v1.py'
TESTS = 'tests/test_staged_rts24_saved_fresh_adoption_v1.py'


def pin(raw): return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())
def tree(raw): return ast.parse(raw)
def dump(node): return ast.dump(node, include_attributes=False)
def definitions(raw): return {n.name: n for n in tree(raw).body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}


def verify():
    old = json.loads((PRIOR/'role_graph_03.snapshot.json').read_bytes())['sources']
    old_entry = (ROOT/old[ENTRY]['snapshot']).read_bytes(); current_entry = (ROOT/ENTRY).read_bytes()
    old_tests = (ROOT/old[TESTS]['snapshot']).read_bytes(); current_tests = (ROOT/TESTS).read_bytes()
    a, b = definitions(old_entry), definitions(current_entry)
    names = ('require canonical digest pin keys parse ordinary directories identity read source_names source_pins environment '
        'output_mode validate_context check_context make_context argv_for validate_actual_entry execution_context '
        'HeldContext hold_context safety_accounting _output_safety').split()
    for name in names: assert dump(a[name]) == dump(b[name]), name
    constants = 'ROOT P1 SCOPE SCHEMA EXE OUTPUT ANCHOR_SHA INHERITED INHERITED_SHA NEW_SOURCES TARGETS RECORDS CAPS STAGE_SECONDS GATES'.split()
    def assignments(raw):
        return {n.targets[0].id: n for n in tree(raw).body if isinstance(n, ast.Assign)
            and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)}
    ca, cb = assignments(old_entry), assignments(current_entry)
    for name in constants: assert dump(ca[name]) == dump(cb[name]), name
    imports = lambda raw: [dump(n) for n in tree(raw).body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert imports(old_entry) == imports(current_entry)
    main = lambda raw: [dump(n) for n in tree(raw).body if isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
        and isinstance(n.test.left, ast.Name) and n.test.left.id == '__name__']
    assert main(old_entry) == main(current_entry)
    historical = json.loads((PRIOR/'adapter_06.exit.json').read_bytes())
    assert historical['exit_code'] == 0 and historical['source_pins_unchanged'] is True and len(historical['nodes']) == 17
    ta, tb = definitions(old_tests), definitions(current_tests)
    for node in historical['nodes']:
        name = node.split('::')[1].split('[')[0]; assert dump(ta[name]) == dump(tb[name]), name
    for name, expected in historical['source_pins'].items():
        if name not in (ENTRY, TESTS): assert pin((ROOT/name).read_bytes()) == expected, name
    # Current-turn role units used the same role/application definitions. The
    # sole _watch_stage delta is a guarded strong reference used only by the
    # external invocation capability; these historical nodes pass no invocation.
    role_run = json.loads((OUT/'role_units_16.exit.json').read_bytes()); assert role_run['exit_code'] == 0 and len(role_run['nodes']) == 26
    snapshot = json.loads((OUT/role_run['snapshot_manifest']).read_bytes())['sources']
    role_entry = (ROOT/snapshot[ENTRY]['snapshot']).read_bytes(); ra = definitions(role_entry)
    role_names = [name for name in ra if name.startswith(('_role_', '_run_', '_publish_role', '_held_role', '_checked_role', '_inner_observation'))]
    role_names += ['RoleStore', 'RoleExecutionUnresolved', 'RolePublicationUnresolved', 'OwnedStage', 'StageChannel']
    for name in role_names: assert dump(ra[name]) == dump(b[name]), name
    before, after = ra['_watch_stage'], ast.fix_missing_locations(tree(current_entry).body[
        next(i for i, n in enumerate(tree(current_entry).body) if isinstance(n, ast.FunctionDef) and n.name == '_watch_stage')])
    removed = []
    class RemoveInvocationFailure(ast.NodeTransformer):
        def visit_If(self, node):
            if (isinstance(node.test, ast.BoolOp) and dump(node.test) == dump(ast.parse(
                    'invocation is not None and invocation.active_error is None', mode='eval').body)):
                assert [dump(n) for n in node.body] == [dump(n) for n in ast.parse(
                    "object.__setattr__(invocation, 'active_error', error); invocation._commit()").body]
                removed.append(True); return None
            return self.generic_visit(node)
    after = RemoveInvocationFailure().visit(after)
    assert len(removed) == 1 and dump(before) == dump(after)
    role_old_tests = definitions((ROOT/snapshot[TESTS]['snapshot']).read_bytes())
    for node in role_run['nodes']:
        name = node.split('::')[1].split('[')[0]; assert dump(role_old_tests[name]) == dump(tb[name])
    return dict(authority='DRAFT_NONAUTHORITATIVE', scope='historical unchanged domains only',
        adapter17_historical_exit_pin=pin((PRIOR/'adapter_06.exit.json').read_bytes()), adapter_functions_unchanged=names,
        bootstrap_constants_unchanged=constants, top_level_imports_and_disabled_main_unchanged=True,
        noncanonical_selected_sources_unchanged=47, scientific_adapter_pin=pin((ROOT/'src/staged_rts24_saved_fresh_adoption_v1.py').read_bytes()),
        role26_snapshot_exit_pin=pin((OUT/'role_units_16.exit.json').read_bytes()), role_definitions_unchanged=role_names,
        watch_delta_is_external_invocation_failure_guard_only=True, historical_adapter_nodes=17, historical_role_unit_nodes=26,
        counted_as_final_source_epoch_nodes=False, fresh_scientific_execution=False)


if __name__ == '__main__': print(json.dumps(verify(), sort_keys=True, indent=2))
