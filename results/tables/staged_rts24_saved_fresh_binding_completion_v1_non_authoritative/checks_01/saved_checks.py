"""Frozen binding unit evidence only; no owner or scientific execution."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
PRIOR = ROOT/'results/tables/staged_rts24_saved_fresh_binding_v1_non_authoritative/checks_01'
MUTABLE = {'experiments/staged_rts24_saved_fresh_adoption_v1.py', 'tests/test_staged_rts24_saved_fresh_adoption_v1.py'}


def pin(raw): return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())
def read(name): return json.loads((OUT/name).read_bytes())


def verify():
    admission = read('admission.json'); nodes = []; seconds = 0.
    preserved = read('preservation_inventory.json')
    for name, expected in preserved.items(): assert pin((ROOT/name).read_bytes()) == expected, name
    selected = admission['source_pins']; current = True
    for name, expected in selected.items():
        match = pin((ROOT/name).read_bytes()) == expected
        if name not in MUTABLE: assert match, name
        current &= match
    for label in admission['groups']:
        value = read(label+'.exit.json'); seconds += value['wall_seconds']
        assert value['source_pins'] == selected and value['source_pins_unchanged'] is True
        assert value['exit_code'] == 0 and value['timed_out'] is False
        assert value['nodes'] == admission['groups'][label] and value['wall_seconds'] <= admission['caps'][label]
        assert (OUT/(label+'.stderr.log')).read_bytes() == b''
        assert (str(len(value['nodes']))+' passed').encode() in (OUT/(label+'.stdout.log')).read_bytes()
        for name, item in read(label+'.snapshot.json')['sources'].items():
            assert pin((ROOT/item['snapshot']).read_bytes()) == item['pin'] == selected[name]
        nodes += value['nodes']
    assert len(nodes) == len(set(nodes)) == 49 and seconds <= 80
    summary = json.loads((PRIOR/'ordinary_check_summary.json').read_bytes())
    prior = [n for n in summary['final_nodeids'] if '::test_saved_binding_' in n]
    assert prior == admission['previous_28'] and len(prior) == 28 and not set(prior)&set(nodes)
    for label in ('binding_commit_08', 'binding_reservation_09', 'binding_rest_10'):
        value = json.loads((PRIOR/(label+'.exit.json')).read_bytes())
        assert value['exit_code'] == 0 and value['source_pins'] == selected and value['source_pins_unchanged'] is True
        for name, item in json.loads((PRIOR/(label+'.snapshot.json')).read_bytes())['sources'].items():
            assert pin((ROOT/item['snapshot']).read_bytes()) == item['pin'] == selected[name]
    all_nodes = json.loads((PRIOR/'collected_nodes_04.json').read_bytes())
    assert set(prior+nodes) == {n for n in all_nodes if '::test_saved_binding_' in n} and len(prior+nodes) == 77
    assert read('baseline_saved_01.exit.json')['exit_code'] == 0
    spec = importlib.util.spec_from_file_location('frozen_p1', ROOT/'results/tables/staged_rts24_saved_fresh_roles_v1_non_authoritative/checks_01/saved_checks.py')
    p1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(p1); assert p1.saved_P1_bytes() == 683
    for name, expected in read('navigation_before.json').items():
        raw = (ROOT/name).read_bytes(); assert raw.partition(b'\n\n')[0].decode() == expected['header']
        assert pin(raw[-expected['body']['bytes']:]) == expected['body']
    for name, expected in read('document_checks.json')['document_pins'].items(): assert pin((ROOT/name).read_bytes()) == expected
    for name, expected in read('support_pins.json').items(): assert pin((ROOT/name).read_bytes()) == expected
    assert not (ROOT/'results/tables/staged_rts24_saved_fresh_adoption_v1_non_authoritative').exists()
    return dict(authority='DRAFT_NONAUTHORITATIVE', frozen_binding_unit_nodes=77, new_nodes=49,
        pytest_seconds=seconds, current_canonical_matches_frozen_epoch=bool(current),
        current_canonical_verified_binding_nodes=77 if current else 0,
        preserved_old_paths=len(preserved), P1_unchanged_files=683,
        actual_saved_file_process_verified=False, actual_saved_owner_constructed=False,
        saved_F_workflow_executed=False, F_launch_admitted=False,
        scientific_evidence_adopted=False, resource_admission=False, formal_result=False)


if __name__ == '__main__': sys.stdout.buffer.write((json.dumps(verify(), sort_keys=True, indent=2)+'\n').encode())
