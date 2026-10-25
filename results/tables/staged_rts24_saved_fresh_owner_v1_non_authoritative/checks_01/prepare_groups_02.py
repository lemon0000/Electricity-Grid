"""Collect exact unit/regression nodes; never admit a saved F actor."""
import ast
import json
from capture_checks import capture, save, OUT, ROOT, TARGET, GUARD

result, stdout = capture('collection_02', ['--collect-only', '-q', TARGET, GUARD], 10)
assert result['exit_code'] == 0 and result['source_pins_unchanged']
nodes = [line for line in stdout.decode().splitlines() if line.startswith('tests/') and '::test_' in line]
save('collected_nodes_02.json', nodes)
new_names = {n.name for n in ast.parse((ROOT/TARGET).read_bytes()).body
    if isinstance(n, ast.FunctionDef) and n.lineno >= 2190}
owner = [n for n in nodes if n.split('::')[-1].split('[')[0] in new_names]
stage = [n for n in nodes if '::test_stage_' in n]
guard = [n for n in nodes if n.startswith(GUARD+'::')]
frozen = ROOT/'results/tables/staged_rts24_saved_fresh_binding_completion_v1_non_authoritative/checks_01'
old = json.loads((frozen/'admission.json').read_bytes())
binding = old['previous_28']+[n for group in old['groups'].values() for n in group]
assert len(binding) == 77 and set(binding) <= set(nodes)
groups = {f'owner_complete_{i+1:02d}': owner[i::3] for i in range(3)}
groups.update(stage_regression_01=stage, guard_regression_01=guard,
    binding_regression_01=binding[::2], binding_regression_02=binding[1::2])
caps = {name:25 for name in groups}
caps['stage_regression_01'] = 45
spent = sum(json.loads(p.read_bytes())['wall_seconds'] for p in OUT.glob('*.exit.json')
    if json.loads(p.read_bytes()).get('nodes'))
assert spent+sum(caps.values()) <= 240
save('group_admission_03.json', dict(authority='DRAFT_NONAUTHORITATIVE', groups=groups, caps=caps,
    previous_pytest_seconds=spent, pytest_total_seconds=240, static_total_seconds=60,
    whole_development_seconds=300, automatic_actor_retries=0, actual_saved_F_execution=False, F_launch_admitted=False))
print(json.dumps(dict(counts={k:len(v) for k,v in groups.items()}, previous_pytest_seconds=spent)))
