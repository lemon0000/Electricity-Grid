"""Cold definitions for both bridges; no owner, source prepare, lease or Job."""
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from experiments import h1_selector_phase_handoff_development_v4 as host
from experiments import h1_selector_parent_validation_operation_development_v1 as parent_bridge
from experiments import h1_common_validation_operation_development_v2 as common_bridge
from experiments import h1_operation_historical_witness_development_v3 as common_witness
from experiments import h1_phase_exact_source_current_development_v4 as source
from experiments import h1_group_n0_common_input_binding_development_v4 as common

host._CHECK();parent_bridge._RUNTIME();common_bridge._RUNTIME()
common_witness._runtime_check(full=True);source._FIXED(full=True);common._FIXED(full=True)
assert host.parent_validation is parent_bridge
assert host._PARENT_VALIDATE_PAIR is parent_bridge._validate_pair
assert host._PARENT_DECLARATION is parent_bridge._declaration
assert parent_bridge._WITNESS_NAME not in sys.modules
assert not host._OWNERS
assert all(value is False for value in host.FLAGS.values())
for name,filename,pin in common_bridge._PINNED_ROUTES:
    assert sys.modules[name].__file__==str(ROOT/'experiments'/filename)
    assert sha256((ROOT/'experiments'/filename).read_bytes()).hexdigest()==pin
print(json.dumps(dict(cold_real_definition_checks=True,owners=0,leases=0,source_prepares=0,
    numerical_replays=0,Jobs=0,real_native_calls=0,full_hour0_chain_passed=False,formal_result=False,
    source_sha256={module.__name__:sha256(Path(module.__file__).read_bytes()).hexdigest()
        for module in (host,parent_bridge,common_bridge,common_witness,source,common)})),flush=True)
