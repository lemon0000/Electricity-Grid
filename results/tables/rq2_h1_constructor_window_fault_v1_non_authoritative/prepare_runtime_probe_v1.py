"""Create one external metadata fault harness without changing prior attempts."""
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
source = HERE / 'probe_saved_v1.py'
raw = source.read_bytes()
text = raw.decode('utf-8')
newline = '\r\n' if b'\r\n' in raw else '\n'
text = text.replace('\r\n', '\n')
changes = []


def replace(old, new, expected=1):
    global text
    assert text.count(old) == expected, old
    text = text.replace(old, new)
    changes.append(dict(before=old, after=new, count=expected))


replace('import importlib.util', 'import importlib.util\nimport importlib.metadata as metadata\nfrom types import SimpleNamespace')
replace('        original=model._dependencies',
        '        original=metadata.distribution\n        original_model_dependencies=model._dependencies')
replace("            def changed_dependencies():\n                state['dependency_calls_after_injection']+=1\n                sources,runtime=original()\n                return sources,runtime+(('development_constructor_window_probe','changed'),)",
        "            def changed_distribution(distribution_name):\n                state['dependency_calls_after_injection']+=1\n                item=original(distribution_name)\n                if distribution_name=='numpy':\n                    state['changed_numpy_version_observations']=state.get('changed_numpy_version_observations',0)+1\n                    return SimpleNamespace(version=item.version+'.development_constructor_window_probe')\n                return item")
replace('                    model._dependencies=changed_dependencies',
        "                    state['normal_model_dependency_alias_unchanged_at_injection']=model._dependencies is original_model_dependencies\n                    metadata.distribution=changed_distribution")
replace('                model._dependencies=original', '                metadata.distribution=original')
replace('                model_dependency_alias_restored=model._dependencies is original,',
        '                runtime_distribution_function_restored=metadata.distribution is original,\n                normal_model_dependency_alias_unchanged=model._dependencies is original_model_dependencies,')
replace("            assert row['model_dependency_alias_restored'] and sys.getprofile() is None",
        "            assert row['runtime_distribution_function_restored'] and row['normal_model_dependency_alias_unchanged'] and sys.getprofile() is None\n            assert state['normal_model_dependency_alias_unchanged_at_injection']\n            assert state.get('changed_numpy_version_observations',0)>0")
replace('        real_manifest_sources_reaudited=False,Jobs=0,native=0,formal_result=False))',
        "        real_manifest_sources_reaudited=False,\n        fault='external_importlib_metadata_distribution_numpy_version',\n        normal_model_dependency_alias_changed=False,physical_files_changed=False,\n        Jobs=0,native=0,formal_result=False))")
replace('        named_dependency_fault_rejected_by_both=', '        named_runtime_distribution_fault_rejected_by_both=')
target = HERE / 'probe_runtime_saved_v1.py'
with target.open('xb') as stream:
    stream.write(text.replace('\n', newline).encode('utf-8'))

runner_source = HERE / 'run_probe_v1.py'
runner_raw = runner_source.read_bytes()
runner = runner_raw.decode('utf-8')
assert runner.count('probe_saved_v1.py') == 2
runner = runner.replace('probe_saved_v1.py', 'probe_runtime_saved_v1.py')
old_scope = 'two_saved_one_hour_historical_readers_constructor_window_dependency_alias_fault'
assert runner.count(old_scope) == 1
runner = runner.replace(old_scope, 'two_saved_H1_historical_readers_constructor_return_external_metadata_version_fault')
runner_target = HERE / 'run_runtime_probe_v1.py'
with runner_target.open('xb') as stream:
    stream.write(runner.encode('utf-8'))
record = dict(status='DRAFT_NONAUTHORITATIVE',
    harness_source=str(source), harness_source_sha256=sha256(raw).hexdigest(),
    harness_target=str(target), harness_target_sha256=sha256(target.read_bytes()).hexdigest(),
    runner_source=str(runner_source), runner_source_sha256=sha256(runner_raw).hexdigest(),
    runner_target=str(runner_target), runner_target_sha256=sha256(runner_target.read_bytes()).hexdigest(),
    newline_policy='preserve original CRLF or LF bytes outside declared replacements',
    harness_substitutions=changes, runner_substitutions=['worker path twice', 'scope label once'],
    actual_implementation_changes=False, formal_result=False)
with (HERE / 'runtime_harness_preparation.json').open('x', encoding='utf-8') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
print(json.dumps(dict(harness=str(target), runner=str(runner_target), substitutions=len(changes))))
