"""Read-only check of retained-CAS/root successor evidence and the old saved core."""
import json
from pathlib import Path
import sys
ROOT = Path(__file__).absolute().parents[4]
sys.path.insert(0, str(ROOT))
from experiments import staged_rts24_journal_closure_diagnostic_v2 as d


def main():
    output = Path(__file__).absolute().parent
    report = d.codec.parse(d.codec.read_bytes(output/'report.json'))
    completion = d.codec.parse(d.codec.read_bytes(output/'completion.json'))
    launch = json.loads((output/'launcher.json').read_text(encoding='utf-8'))
    assert report['bindings'] == d.bindings() and report['preserved'] == d.verify_prior()
    assert all(d.old.stamp(output/name) == pin for name,pin in completion['files'].items())
    assert launch['exit_code'] == 0 and launch['stop_reason'] is None and not launch['child_running_after_cleanup']
    assert launch['terminal_bytes_excluding_launcher']+launch['launcher_reserved_bytes'] <= launch['limits']['output_bytes']
    assert launch['terminal_files_excluding_launcher']+1 <= launch['limits']['files']
    parent, child = report['parent_counts'], report['fresh']['counts']
    assert (parent['selective_compiler_calls']+child['selective_compiler_calls'],parent['selective_descriptions']+child['selective_descriptions']) == (37,121)
    for key in ('summary','independent_audit','scientific_outcome','publication_outcome','terminal_entry_present'):
        assert report['fresh']['result'][key] == report['expected_old_prefix'][key]
    for case in ('deleted_before_begin','deleted_after_entry'):
        result = report['failure_cases'][case]
        assert result['writer_adopted'] is False and result['reader_state'] == 'unresolved_missing_retained_CAS'
        removed = output/case/'removed_object.json'
        root = output/case/'journal'
        genesis = d.codec.parse(d.codec.read_bytes(root/'genesis.json'))
        assert d.codec.sha(d.codec.read_bytes(removed)) == genesis['fixture_ref']
        assert not (root/'objects'/(genesis['fixture_ref']+'.json')).exists()
    success = output/'success'
    expected = d.codec.parse(d.codec.read_bytes(success/'trusted_binding.json'))
    store = d.codec.EvidenceStore(success/'journal')
    assert sorted(store.inventory()) == expected['known_cas_keys']
    print(json.dumps(dict(core_files=completion['manifest_files'], core_bytes=completion['logical_bytes'],
        reference_calls=37, reference_descriptions=121, old_core_and_sources_preserved=True,
        success_retained_CAS_keys=len(expected['known_cas_keys']), scope='read_only_saved_successor_postcheck'),sort_keys=True))


if __name__ == '__main__': main()
