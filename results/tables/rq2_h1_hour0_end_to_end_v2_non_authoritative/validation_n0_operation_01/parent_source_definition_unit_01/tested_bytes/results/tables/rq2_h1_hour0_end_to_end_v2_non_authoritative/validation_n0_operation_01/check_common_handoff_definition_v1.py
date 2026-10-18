"""Cold real definitions only: no owner, validation lease, producer or native call."""
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]

from experiments import h1_selector_phase_handoff_development_v4 as h
from experiments import h1_common_validation_operation_development_v2 as bridge
from experiments import h1_operation_historical_witness_development_v3 as witness
from experiments import h1_phase_exact_source_current_development_v4 as source
from experiments import h1_group_n0_common_input_binding_development_v4 as common

h._CHECK()
bridge._RUNTIME()
witness._runtime_check(full=True)
source._FIXED(full=True)
common._FIXED(full=True)
assert witness.operation_bridge is bridge and source.witness is witness
assert common.source is source and common.witness is witness and h.validation is bridge
for name, filename, pin in bridge._PINNED_ROUTES:
    assert sys.modules[name].__file__ == str(ROOT / 'experiments' / filename)
    assert sha256((ROOT / 'experiments' / filename).read_bytes()).hexdigest() == pin
assert not h._OWNERS
print(json.dumps(dict(cold_real_definition_checks=True, Handoff_owners_created=0,
    validation_leases_issued=0, common_calls=0, real_native_calls=0,
    full_hour0_chain_passed=False, formal_result=False, resource_admission=False,
    source_sha256={m.__name__: sha256(Path(m.__file__).read_bytes()).hexdigest()
        for m in (h, bridge, witness, source, common)})), flush=True)
