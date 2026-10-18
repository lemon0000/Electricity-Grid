"""Cheap saved input identity selection before any numerical replay."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
ENTRY = HERE.parent / 'validation_path_optimization_01/entry_revision_07'
sys.path[:0] = [str(REPO), str(REPO / 'tests')]
spec = importlib.util.spec_from_file_location('parent_preflight_interpreter_policy', ENTRY / 'interpreter_path_policy.py')
policy_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = policy_module
spec.loader.exec_module(policy_module)
policy = policy_module.InterpreterPathPolicy(json.loads((ENTRY / 'interpreter_path_policy_v1.json').read_bytes()))
policy.configure()
from experiments import h1_selector_input_snapshot_development_v2 as snapshot

current = snapshot.implementation_identity()
rows = []
for chain in ('06', '07'):
    path = Path('D:/h1_chain_' + chain + '_non_authoritative/test_complete_independent_N0_r0/'
        'parent_non_authoritative/worker_non_authoritative/selector_snapshot.json')
    raw = path.read_bytes()
    doc = json.loads(raw)
    rows.append(dict(path=str(path), raw_sha256=sha256(raw).hexdigest(),
        current_implementation_identity=current, saved_implementation_identity=doc['implementation'],
        identity_matches=doc['implementation'] == current,
        canonical_bytes_match=snapshot.encode(doc) == raw))
    assert path.read_bytes() == raw
assert not snapshot.io.digest(b'') == current
print(json.dumps(dict(rows=rows, numerical_inspections=0, Parent_credentials_issued=0,
    real_native_calls=0, formal_result=False, resource_admission=False)), flush=True)
