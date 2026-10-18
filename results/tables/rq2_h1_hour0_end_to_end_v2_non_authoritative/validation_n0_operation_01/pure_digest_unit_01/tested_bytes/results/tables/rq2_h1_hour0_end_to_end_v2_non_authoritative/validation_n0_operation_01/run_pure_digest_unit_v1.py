"""Explicit isolated short unit entry; no experiment or solver route."""
import os
from pathlib import Path
import sys

if not sys.flags.isolated or not sys.dont_write_bytecode:
    raise ValueError('fixed isolated no-bytecode unit interpreter required')
repo = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(repo))
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
import pytest
raise SystemExit(pytest.main(['-q', '-p', 'no:cacheprovider', '-p', 'no:faulthandler',
    '--basetemp', 'D:/h1_pure_repair_digest_unit_01_non_authoritative',
    'tests/test_h1_pure_repair_digest_lease_development_v1.py']))
