"""Reopen draft unit evidence, with explicit frozen/current source separation."""
import ast
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
ENTRY = 'experiments/staged_rts24_saved_fresh_adoption_v1.py'
TESTS = 'tests/test_staged_rts24_saved_fresh_adoption_v1.py'


def pin(raw): return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())
def read(name): return json.loads((OUT/name).read_bytes())


def frozen_binding_recheck():
    folder = ROOT/'results/tables/staged_rts24_saved_fresh_binding_completion_v1_non_authoritative/checks_01'
    prior = ROOT/'results/tables/staged_rts24_saved_fresh_binding_v1_non_authoritative/checks_01'
    admission = json.loads((folder/'admission.json').read_bytes()); selected = admission['source_pins']
    nodes = list(admission['previous_28'])
    groups = [(folder, label, group) for label, group in admission['groups'].items()]
    groups += [(prior, label, json.loads((prior/(label+'.exit.json')).read_bytes())['nodes'])
        for label in ('binding_commit_08', 'binding_reservation_09', 'binding_rest_10')]
    for base, label, expected_nodes in groups:
        value = json.loads((base/(label+'.exit.json')).read_bytes())
        assert value['exit_code'] == 0 and value['source_pins_unchanged'] and value['source_pins'] == selected
        assert value['nodes'] == expected_nodes
        for name, item in json.loads((base/(label+'.snapshot.json')).read_bytes())['sources'].items():
            assert pin((ROOT/item['snapshot']).read_bytes()) == item['pin'] == selected[name]
        if base == folder: nodes += value['nodes']
    assert len(nodes) == len(set(nodes)) == 77
    collected = json.loads((prior/'collected_nodes_04.json').read_bytes())
    assert set(nodes) == {n for n in collected if '::test_saved_binding_' in n}
    navigation = read('navigation_before.json')
    for name, expected in json.loads((folder/'document_checks.json').read_bytes())['document_pins'].items():
        raw = (ROOT/name).read_bytes()
        if name in navigation:
            before = navigation[name]
            # Reconstruct only the frozen document bytes; current navigation is newer.
            raw = before['header'].encode()+b'\n\n'+raw[-before['body']['bytes']:]
        assert pin(raw) == expected, name
    spec = importlib.util.spec_from_file_location('frozen_p1',
        ROOT/'results/tables/staged_rts24_saved_fresh_roles_v1_non_authoritative/checks_01/saved_checks.py')
    p1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(p1)
    assert p1.saved_P1_bytes() == 683
    return 77


def verify():
    summary = read('development_summary.json'); selected = summary['source_pins']
    current = True
    assert len(selected) == 49
    for name, expected in selected.items():
        match = pin((ROOT/name).read_bytes()) == expected
        if name not in (ENTRY, TESTS): assert match, name
        current &= match
    preserved = read('preservation_inventory.json')
    for name, expected in preserved.items(): assert pin((ROOT/name).read_bytes()) == expected, name
    assert len(preserved) == 2848
    pytest_seconds = static_seconds = 0.
    all_nodes = []
    for path in OUT.glob('*.exit.json'):
        value = json.loads(path.read_bytes())
        if value.get('nodes'):
            pytest_seconds += value['wall_seconds']
            assert value['source_pins_unchanged'] is True
            for name, item in read(value['snapshot_manifest'])['sources'].items():
                assert pin((ROOT/item['snapshot']).read_bytes()) == item['pin'] == value['source_pins'][name]
        else: static_seconds += value['wall_seconds']
    assert pytest_seconds <= 240 and static_seconds <= 60
    for label in summary['accepted_groups']:
        value = read(label+'.exit.json'); nodes = summary['accepted_groups'][label]
        assert value['nodes'] == nodes and value['source_pins'] == selected
        assert value['exit_code'] == 0 and value['timed_out'] is False
        assert value['wall_seconds'] <= value['timeout_seconds']
        assert (str(len(nodes))+' passed').encode() in (OUT/(label+'.stdout.log')).read_bytes()
        assert (OUT/(label+'.stderr.log')).read_bytes() == b''
        all_nodes += nodes
    assert len(all_nodes) == len(set(all_nodes))
    owner = [n for n in all_nodes if '::test_saved_owner_' in n]
    assert len(owner) == 56
    final_snapshot = read('owner_bounded_01.snapshot.json')['sources'][TESTS]['snapshot']
    names = {n.name for n in ast.parse((ROOT/final_snapshot).read_bytes()).body
        if isinstance(n, ast.FunctionDef) and n.lineno >= 2190}
    collected = read('collected_nodes_03.json')
    expected_owner = {n for n in collected if n.split('::')[-1].split('[')[0] in names}
    assert set(owner) == expected_owner
    assert read('owner_smoke_01.exit.json')['exit_code'] == 1
    assert read('owner_complete_01.exit.json')['timed_out'] is True
    assert set(read('group_admission_05.json')['groups']) <= set(summary['accepted_groups'])
    for name, before in read('navigation_before.json').items():
        raw = (ROOT/name).read_bytes()
        assert raw.partition(b'\n\n')[0].decode() == before['header']
        assert pin(raw[-before['body']['bytes']:]) == before['body']
    for name, expected in read('document_checks.json')['document_pins'].items():
        assert pin((ROOT/name).read_bytes()) == expected, name
    for name, expected in read('support_pins.json').items(): assert pin((ROOT/name).read_bytes()) == expected, name
    assert frozen_binding_recheck() == 77
    actual_parent = ROOT/'results/tables/staged_rts24_saved_fresh_adoption_v1_non_authoritative'
    assert not actual_parent.exists()
    return dict(authority='DRAFT_NONAUTHORITATIVE', frozen_owner_unit_nodes=56,
        frozen_epoch_terminal_nodes=len(all_nodes), current_canonical_matches_frozen_epoch=bool(current),
        current_canonical_terminal_nodes=len(all_nodes) if current else 0,
        pytest_seconds=pytest_seconds, static_seconds_conservative=static_seconds,
        preserved_old_paths=len(preserved), P1_unchanged_files=683,
        binding_predecessor_nodes_not_inherited=77,
        actual_saved_owner_constructed=False, saved_F_workflow_executed=False, F_launch_admitted=False,
        saved_P1_fresh_process_verified=False, saved_P1_parent_adoption_verified=False,
        scientific_evidence_adopted=False, resource_admission=False, formal_result=False,
        related_regression_complete=summary['related_regression_complete'])


if __name__ == '__main__': sys.stdout.buffer.write((json.dumps(verify(), sort_keys=True, indent=2)+'\n').encode())
