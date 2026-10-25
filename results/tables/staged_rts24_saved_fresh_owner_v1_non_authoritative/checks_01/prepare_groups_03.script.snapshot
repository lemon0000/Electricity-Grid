"""Add the final kernel identity negative to the still-unrun regression plan."""
import json
from capture_checks import capture, save, OUT, TARGET, GUARD

result, stdout = capture('collection_03', ['--collect-only', '-q', TARGET, GUARD], 10)
assert result['exit_code'] == 0 and result['source_pins_unchanged']
nodes = [line for line in stdout.decode().splitlines() if line.startswith('tests/') and '::test_' in line]
save('collected_nodes_03.json', nodes)
plan = json.loads((OUT/'group_admission_03.json').read_bytes())
node = TARGET+'::test_saved_owner_fixed_unit_post_bind_method_drift_retains_without_calling_foreign[kernel_job_none]'
assert node in nodes and not any(node in group for group in plan['groups'].values())
plan['groups']['owner_complete_03'].append(node)
assert all(n in nodes for group in plan['groups'].values() for n in group)
save('group_admission_04.json', plan)
print(json.dumps({k:len(v) for k,v in plan['groups'].items()}))
