"""Isolated short checks for the diagnostic sampler, without scientific imports."""
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PACKAGE = HERE.parent/'validation_path_optimization_01/entry_revision_04'
assert sha256((PACKAGE/'package_manifest_v1.json').read_bytes()).hexdigest() == \
    'd13a08fe6db35e9c5c70b8204e3fb4d0091e43a3ef483e3951a561eac0667e43'
sys.path[:] = json.loads((PACKAGE/'interpreter_path_policy_v1.json').read_bytes())['configured_paths']
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
assert len(sys.argv) == 3 and sys.argv[1] == '--basetemp'
base = Path(sys.argv[2])
assert base.is_absolute() and base.name.endswith('_non_authoritative') and not base.exists()
base.mkdir()
paths = [REPO/'tests'/name for name in ('h1_gil_stack_observer_development_v1.py',
    'test_h1_gil_stack_observer_development_v1.py')]
pins = {str(path):sha256(path.read_bytes()).hexdigest() for path in paths}
tested = base/'sampler_tested_bytes'
tested.mkdir()
for path in paths:
    (tested/path.name).write_bytes(path.read_bytes())
import pytest
status = int(pytest.main(['-q', '-p', 'no:cacheprovider', '-p', 'no:faulthandler',
    '--import-mode=importlib', '--basetemp', str(base/'pytest_non_authoritative'),
    'tests/test_h1_gil_stack_observer_development_v1.py']))
assert all(sha256(Path(name).read_bytes()).hexdigest() == pin for name,pin in pins.items())
with (base/'source_postcheck.json').open('x', encoding='utf-8') as stream:
    json.dump(dict(exit_code=status, source_sha256=pins, source_unchanged=True,
        formal_result=False), stream, indent=2)
raise SystemExit(status)
