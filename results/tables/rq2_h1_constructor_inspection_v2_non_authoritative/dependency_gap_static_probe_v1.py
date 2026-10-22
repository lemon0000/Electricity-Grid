"""Observe one unlisted model dependency alias. Does not execute a Reader."""
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))

from experiments import h1_phase_historical_batch_development_v2 as historical
from src.rq2_joint_deliverability_boundary_v1 import continuous_grid_normal as model

paths = (Path(__file__), Path(historical.__file__), Path(model.__file__))
before_files = {str(p): sha256(p.read_bytes()).hexdigest() for p in paths}
original = model._dependencies
before = historical.implementation_identity()
def changed_dependencies():
    sources, runtime = original()
    return sources, runtime+(('development_probe', 'changed'),)
try:
    model._dependencies = changed_dependencies
    historical._check_dependencies()
    after = historical.implementation_identity()
    guard_accepted = True
finally:
    model._dependencies = original
assert all(sha256(Path(p).read_bytes()).hexdigest() == expected for p, expected in before_files.items())
result = dict(status='DRAFT_NONAUTHORITATIVE', scope='static_dependency_surface_observation_only',
    historical_guard_accepts_unlisted_model_dependency_alias=guard_accepted,
    implementation_identity_unchanged=before == after, before_identity=before, after_identity=after,
    dependency_alias_restored=model._dependencies is original, source_files_unchanged=True,
    actual_reader_executed=False, normal_input_identity_executed=False,
    old_reject_new_accept_counterexample_proved=False,
    conclusion='A concrete unlisted model dependency requires constructor-window investigation before adoption.',
    new_normal_jobs=0, real_native_calls=0, formal_result=False, bindings=before_files)
with (HERE/'dependency_gap_static_probe_v1.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps(result))
