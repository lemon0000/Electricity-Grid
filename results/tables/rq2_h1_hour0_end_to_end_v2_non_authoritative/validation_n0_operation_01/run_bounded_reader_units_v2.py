"""Successor entry units with explicit pins for imported predecessor test cases."""
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
source, support, *targets = sys.argv[1:]
if ((REPO / source).resolve() != (HERE / 'bounded_stable_read_entry_v2.py').resolve()
        or (REPO / support).resolve() != (REPO / 'tests/test_h1_bounded_stable_read_entry_development_v1.py').resolve()
        or not targets):
    raise ValueError('explicit successor entry, predecessor test support and unit targets required')
sys.path.insert(0, str(REPO))
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
import pytest
sys.exit(pytest.main(['-q', '--disable-warnings', '--maxfail=1', '-p', 'no:cacheprovider', *targets]))
