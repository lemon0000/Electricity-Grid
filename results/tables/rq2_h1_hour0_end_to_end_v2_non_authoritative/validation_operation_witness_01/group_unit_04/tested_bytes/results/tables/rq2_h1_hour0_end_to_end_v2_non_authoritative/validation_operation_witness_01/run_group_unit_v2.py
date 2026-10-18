"""Isolated bounded unit entry; no saved/native/worker integration claim."""
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
PACKAGE=HERE.parent/'validation_path_optimization_01/entry_revision_04'
raw=(PACKAGE/'package_manifest_v1.json').read_bytes()
if sha256(raw).hexdigest()!='d13a08fe6db35e9c5c70b8204e3fb4d0091e43a3ef483e3951a561eac0667e43':
    raise ValueError('configured predecessor package differs')
for name,pin in json.loads(raw)['files_sha256'].items():
    if sha256((PACKAGE/name).read_bytes()).hexdigest()!=pin:
        raise ValueError('configured predecessor member differs: '+name)
sys.path[:]=json.loads((PACKAGE/'interpreter_path_policy_v1.json').read_bytes())['configured_paths']
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
if any(key.startswith('PYTEST') and key!='PYTEST_DISABLE_PLUGIN_AUTOLOAD' for key in os.environ):
    raise ValueError('external pytest options require an explicit unit entry revision')
if len(sys.argv)!=3 or sys.argv[1]!='--basetemp':raise ValueError('explicit unit basetemp required')
import pytest
raise SystemExit(pytest.main(['-q','-p','no:cacheprovider','--import-mode=importlib',
    '--basetemp',sys.argv[2],
    'tests/test_h1_group_operation_witness_development_v2.py']))
