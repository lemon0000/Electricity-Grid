"""Mechanical diff check of retained positive code and complete v3 routing."""
import ast
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
out = HERE / 'negative_handoff_diff_02_non_authoritative'
out.mkdir(exist_ok=False)
pins = {}


def tree(name):
    path = REPO / name
    raw = path.read_bytes()
    pins[str(path)] = sha256(raw).hexdigest()
    return ast.parse(raw, filename=name)


def remove_doc(module):
    assert isinstance(module.body[0], ast.Expr) and isinstance(module.body[0].value, ast.Constant)
    module.body.pop(0)


old = tree('experiments/h1_selector_phase_handoff_development_v2.py')
new = tree('experiments/h1_selector_phase_handoff_development_v3.py')
remove_doc(old)
remove_doc(new)
added = [node for node in new.body if isinstance(node, ast.FunctionDef) and node.name == '_negative_missing_actual']
assert len(added) == 1
new.body.remove(added[0])
for node in new.body:
    if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'SCHEMA' for target in node.targets):
        assert node.value.value == 'h1_selector_phase_handoff_development_v3'
        node.value.value = 'h1_selector_phase_handoff_development_v2'
    if isinstance(node, ast.ClassDef) and node.name == 'Handoff':
        consume, = [method for method in node.body if isinstance(method, ast.FunctionDef) and method.name == 'consume']
        main_try, = [row for row in consume.body if isinstance(row, ast.Try)]
        insertion = [row for row in main_try.body if isinstance(row, ast.If)
            and isinstance(row.test, ast.Call) and isinstance(row.test.func, ast.Name) and row.test.func.id == 'any']
        assert len(insertion) == 1
        assert ast.unparse(insertion[0].test) == 'any((pair is None for _, pair in bundle.actuals))'
        main_try.body.remove(insertion[0])
assert ast.dump(old) == ast.dump(new)

old_helper = tree('tests/h1_group_selector_integration_helpers_v2.py')
new_helper = tree('tests/h1_group_selector_integration_helpers_v3.py')
remove_doc(old_helper)
remove_doc(new_helper)
for node in ast.walk(new_helper):
    if isinstance(node, ast.alias) and node.name == 'h1_selector_phase_handoff_development_v3':
        node.name = 'h1_selector_phase_handoff_development_v2'
assert ast.dump(old_helper) == ast.dump(new_helper)

old_test = tree('tests/test_h1_hour0_end_to_end_development_v2.py')
new_test = tree('tests/test_h1_hour0_end_to_end_development_v3.py')
remove_doc(old_test)
remove_doc(new_test)
routes = 0
metadata = 0
module_guards = 0
for node in ast.walk(new_test):
    if isinstance(node, ast.Constant) and node.value == 'tests.h1_group_selector_integration_helpers_v3':
        node.value = 'tests.h1_group_selector_integration_helpers_v2'
        module_guards += 1
    if isinstance(node, ast.ImportFrom) and node.module == 'tests.h1_group_selector_integration_helpers_v3':
        node.module = 'tests.h1_group_selector_integration_helpers_v2'
        routes += 1
    if isinstance(node, ast.Call):
        for keyword in tuple(node.keywords):
            if keyword.arg == 'selector_handoff_contract':
                assert keyword.value.value == 'h1_selector_phase_handoff_development_v3'
                node.keywords.remove(keyword)
                metadata += 1
assert routes == 2 and metadata == 1 and module_guards == 1 and ast.dump(old_test) == ast.dump(new_test)
value = dict(status='DRAFT_NONAUTHORITATIVE', exit_code=0,
    script_sha256=sha256(Path(__file__).read_bytes()).hexdigest(), source_sha256=pins,
    handoff_only_schema_and_negative_insertion_changed=True,
    positive_methods_and_consume_body_otherwise_ast_identical=True,
    helper_only_explicit_handoff_import_changed=True,
    full_test_only_two_helper_routes_one_module_guard_and_explicit_report_metadata_changed=True,
    missing_matrix_and_success_and_reopen_retained=True,
    dynamic_test_pass_claimed=False, full_hour0_chain_passed=False, formal_result=False)
with (out / 'terminal.json').open('x', encoding='utf-8') as stream:
    json.dump(value, stream, indent=2)
print(json.dumps({key: value[key] for key in ('exit_code', 'positive_methods_and_consume_body_otherwise_ast_identical',
    'missing_matrix_and_success_and_reopen_retained', 'dynamic_test_pass_claimed')}))
