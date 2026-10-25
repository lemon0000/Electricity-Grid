"""Exact-source 143+18 frozen unit closure; no scientific or process authority."""
import importlib.util
import json
from hashlib import sha256
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
OWNER = ROOT/'results/tables/staged_rts24_saved_fresh_owner_v1_non_authoritative/checks_01'
MUTABLE = {'experiments/staged_rts24_saved_fresh_adoption_v1.py', 'tests/test_staged_rts24_saved_fresh_adoption_v1.py'}


def pin(raw): return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())
def read(name): return json.loads((OUT/name).read_bytes())


def verify():
    admission = read('admission.json'); current = True
    assert len(admission['source_pins']) == 49
    for name, expected in admission['source_pins'].items():
        match = pin((ROOT/name).read_bytes()) == expected
        if name not in MUTABLE: assert match, name
        current &= match
    preserved = read('preservation_inventory.json')
    for name, expected in preserved.items(): assert pin((ROOT/name).read_bytes()) == expected, name
    value = read('binding_completion_01.exit.json')
    assert value['exit_code'] == 0 and value['timed_out'] is False and value['source_pins_unchanged'] is True
    assert value['nodes'] == admission['nodes'] and value['source_pins'] == admission['source_pins']
    assert value['wall_seconds'] <= admission['pytest_cap_seconds'] == 45
    assert b'18 passed' in (OUT/'binding_completion_01.stdout.log').read_bytes()
    assert (OUT/'binding_completion_01.stderr.log').read_bytes() == b''
    assert read('baseline_owner_01.exit.json')['exit_code'] == 0
    for label in ('baseline_owner_01', 'binding_completion_01'):
        for name, item in read(label+'.snapshot.json')['sources'].items():
            assert pin((ROOT/item['snapshot']).read_bytes()) == item['pin'] == admission['source_pins'][name]
    prior = json.loads((OWNER/'development_summary.json').read_bytes())
    assert prior['source_pins'] == admission['source_pins'] and len(prior['final_nodeids']) == 143
    assert len(admission['nodes']) == len(set(admission['nodes'])) == 18
    assert not set(prior['final_nodeids'])&set(admission['nodes'])
    assert set(admission['nodes']) == set(prior['pending_affected_binding_nodes'])
    spec = importlib.util.spec_from_file_location('frozen_owner', OWNER/'saved_checks.py')
    owner = importlib.util.module_from_spec(spec); spec.loader.exec_module(owner); old = owner.verify()
    assert old['frozen_epoch_terminal_nodes'] == 143 and old['P1_unchanged_files'] == 683
    static_seconds = read('preparation_timing.json')['external_tool_wall_seconds']
    static_seconds += sum(read(p.name)['wall_seconds'] for p in OUT.glob('*.exit.json') if not read(p.name).get('nodes'))
    assert static_seconds <= 15
    for name, before in read('navigation_before.json').items():
        raw = (ROOT/name).read_bytes()
        assert raw.partition(b'\n\n')[0].decode() == before['header']
        assert pin(raw[-before['body']['bytes']:]) == before['body']
    for name, expected in read('document_checks.json')['document_pins'].items(): assert pin((ROOT/name).read_bytes()) == expected, name
    for name, expected in read('support_pins.json').items(): assert pin((ROOT/name).read_bytes()) == expected, name
    assert not (ROOT/'results/tables/staged_rts24_saved_fresh_adoption_v1_non_authoritative').exists()
    return dict(authority='DRAFT_NONAUTHORITATIVE', frozen_owner_related_unit_nodes=161, new_binding_nodes=18,
        current_canonical_matches_frozen_epoch=bool(current), current_canonical_terminal_nodes=161 if current else 0,
        pytest_seconds=value['wall_seconds'], static_seconds_conservative=static_seconds,
        predecessor_pytest_seconds=prior['pytest_seconds'], predecessor_pytest_cap_seconds=240,
        preserved_old_paths=len(preserved), P1_unchanged_files=683, packet_scope_regression_complete=True,
        full_binding_77_rerun=False, actual_saved_owner_constructed=False, saved_F_workflow_executed=False,
        F_launch_admitted=False, saved_P1_fresh_process_verified=False, saved_P1_parent_adoption_verified=False,
        scientific_evidence_adopted=False, resource_admission=False, formal_result=False)


if __name__ == '__main__': sys.stdout.buffer.write((json.dumps(verify(), sort_keys=True, indent=2)+'\n').encode())
