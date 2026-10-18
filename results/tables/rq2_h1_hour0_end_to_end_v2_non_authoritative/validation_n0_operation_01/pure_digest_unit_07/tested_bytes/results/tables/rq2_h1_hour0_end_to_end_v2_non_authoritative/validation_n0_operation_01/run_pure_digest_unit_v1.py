"""Explicit isolated short unit entry; no experiment or solver route."""
import os
import json
from pathlib import Path
import sys

if not sys.flags.isolated or not sys.dont_write_bytecode:
    raise ValueError('fixed isolated no-bytecode unit interpreter required')
repo = Path(__file__).resolve().parents[4]
test, helper, option, basetemp = sys.argv[1:]
if (test != 'tests/test_h1_pure_repair_digest_lease_development_v1.py'
        or helper != 'experiments/h1_pure_repair_digest_lease_development_v1.py'
        or option != '--basetemp' or Path(basetemp).exists()):
    raise ValueError('fixed test/helper and unused basetemp required')
policy = repo / 'results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/validation_path_optimization_01/entry_revision_07/interpreter_path_policy_v1.json'
sys.path[:] = json.loads(policy.read_bytes())['configured_paths']
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
import pytest
raise SystemExit(pytest.main(['-q', '-p', 'no:cacheprovider', '-p', 'no:faulthandler',
    '--basetemp', basetemp, test]))
