"""Reuse the saved H3 reconstruction harness with accurate evidence labels."""
from hashlib import sha256
import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PRIOR = HERE.parent / 'rq2_h1_constructor_inspection_v2_non_authoritative'
sys.path.insert(0, str(PRIOR))
spec = importlib.util.spec_from_file_location('saved_identity_bound_oracle_harness',
    PRIOR / 'oracle_saved_v1.py')
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)
harness.HERE = HERE
original_save = harness.core.save


def save(root, name, value):
    value = dict(value)
    if name == 'oracle_request.json':
        value['oracle_scope'] = 'saved_identity_bound_reconstruction_using_original_join_projection'
        value['old_raw_science_bytes_directly_read'] = False
        value['independent_scientific_implementation'] = False
        value['shared_saved_manifest_pin_resolver'] = True
        value['original_harness_sha256'] = sha256((PRIOR / 'oracle_saved_v1.py').read_bytes()).hexdigest()
    elif name == 'oracle_terminal.json':
        value['saved_identity_bound_science_reconstruction_equal'] = value.pop('old_saved_science_bytes_equal', False)
        value['old_raw_science_bytes_directly_read'] = False
        value['independent_scientific_implementation'] = False
        value['shared_saved_manifest_pin_resolver'] = True
        value['one_field_packet_projection_standin'] = True
    original_save(root, name, value)


harness.core.save = save
if __name__ == '__main__':
    raise SystemExit(harness.main())
