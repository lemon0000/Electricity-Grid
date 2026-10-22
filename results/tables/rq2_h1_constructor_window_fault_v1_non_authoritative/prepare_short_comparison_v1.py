"""Preserve and adapt only the saved H1 comparison harness's evidence binding."""
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRIOR = HERE.parent / 'rq2_h1_constructor_inspection_v2_non_authoritative'
source = PRIOR / 'compare_short_saved_v1.py'
target = HERE / 'compare_short_saved_v2.py'
oracle = HERE / 'oracle_01/oracle_terminal.json'
raw = oracle.read_bytes()
value = json.loads(raw)
assert value['exit_code'] == 0 and value['saved_identity_bound_science_reconstruction_equal'] is True
assert value['old_raw_science_bytes_directly_read'] is False
assert value['independent_scientific_implementation'] is False
assert len(value['validator_faults']) == 21
assert all(m['normal_model_dependency_bookends_verified'] is True for m in value['observations'])
text = source.read_text(encoding='utf-8')
old = "    assert fixture.pin(HERE / 'oracle_01/oracle_terminal.json') == 'a6850603e74592f486d5e427c9d5ea3f8c204ef91bee37fa5c61b1169376da91'"
new = "    assert fixture.pin(HERE / 'oracle_01/oracle_terminal.json') == '"+sha256(raw).hexdigest()+"'"
assert text.count(old) == 1
text = text.replace(old, new)
old_metric = "            assert batch.observations[0]['observation_token'] != batch.observations[1]['observation_token']"
new_metric = old_metric+"\n            if name == 'new':\n                assert all(m['normal_model_dependency_bookends_verified'] is True for m in batch.observations)"
assert text.count(old_metric) == 1
text = text.replace(old_metric, new_metric)
with target.open('x', encoding='utf-8', newline='\n') as stream:
    stream.write(text)
record = dict(status='DRAFT_NONAUTHORITATIVE', original_harness=str(source),
    original_harness_sha256=sha256(source.read_bytes()).hexdigest(),
    target=str(target), target_sha256=sha256(target.read_bytes()).hexdigest(),
    prior_harness_changes=['bind current H3 reconstruction terminal SHA',
                          'require new normal model bookend metrics'],
    oracle_sha256=sha256(raw).hexdigest(), builder_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
    formal_result=False)
with (HERE / 'short_harness_preparation.json').open('x', encoding='utf-8') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
print(json.dumps(dict(target=str(target), oracle_sha256=record['oracle_sha256'])))
