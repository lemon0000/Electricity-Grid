"""Reopen frozen ordinary evidence and its explicit non-production boundaries."""
import ast
from hashlib import sha256
import importlib.util
import json
import re
import sys
from capture_checks import ROOT, OUT, PRIOR, entry

MUTABLE = set(entry.NEW_SOURCES[1:3])


def read(name):
    return json.loads((OUT/name).read_bytes())


def definitions(raw):
    return {node.name:ast.dump(node, include_attributes=False) for node in ast.parse(raw).body
        if isinstance(node, (ast.FunctionDef, ast.ClassDef))}


def verify(require_current_navigation=False):
    frozen = read('frozen_epoch.json')
    selected = frozen['source_pins']
    baseline = read('baseline_sources.json')
    assert set(selected) == set(baseline) and len(selected) == 49
    current = True
    for name, expected in selected.items():
        match = entry.pin((ROOT/name).read_bytes()) == expected
        if name not in MUTABLE:
            assert expected == baseline[name] and match, name
        current &= match
    assert len(selected.keys()-MUTABLE) == 47
    assert selected[entry.NEW_SOURCES[0]] == read('admission.json')['frozen_adapter_pin']
    preserved = read('preservation_inventory.json')
    assert len(preserved) == 3176
    for name, expected in preserved.items():
        assert entry.pin((ROOT/name).read_bytes()) == expected, name

    totals = dict(pytest=0., static=0.)
    records = {}
    for path in OUT.glob('*.exit.json'):
        value = json.loads(path.read_bytes())
        records[path.name.removesuffix('.exit.json')] = value
        totals[value['kind']] += value['wall_seconds']
        assert value['exit_code'] == 0 and not value['timed_out']
        assert value['wall_seconds'] <= value['timeout_seconds'] <= 40
        assert value['source_pins_unchanged']
        assert value['actual_saved_F_execution'] is value['F_launch_admitted'] is False
        assert set(value['source_pins']) == set(selected)
        for name, expected in value['source_pins'].items():
            if name not in MUTABLE:
                assert expected == selected[name]
        source_manifest = read(value['snapshot_manifest'])['sources']
        assert set(source_manifest) == set(entry.NEW_SOURCES[:3])
        epoch_input = {n:value['source_pins'][n] for n in entry.NEW_SOURCES[:3]}
        assert sha256(entry.canonical(epoch_input)).hexdigest() == value['source_epoch']
        for name, item in source_manifest.items():
            assert entry.pin((ROOT/item['snapshot']).read_bytes()) == item['pin'] == value['source_pins'][name]
        assert (OUT/path.name.replace('.exit.json', '.stdout.log')).is_file()
        assert (OUT/path.name.replace('.exit.json', '.stderr.log')).read_bytes() == b''
    assert totals['pytest'] <= 160 and totals['static'] <= 40 and sum(totals.values()) <= 200
    assert abs(totals['pytest']-106.875) < .002

    plan = read('group_admission_02.json')
    nodes = []
    current_wall = 0.
    for label, group in plan['groups'].items():
        record = records[label]
        assert record['source_pins'] == selected and record['source_epoch'] == frozen['source_epoch']
        assert record['nodes'] == group == frozen['groups'][label]
        assert record['timeout_seconds'] == plan['caps'][label]
        raw = (OUT/(label+'.stdout.log')).read_text(encoding='utf-8')
        assert re.search(r'\b'+str(len(group))+r' passed\b', raw), label
        nodes.extend(group)
        current_wall += record['wall_seconds']
    assert sorted(nodes) == frozen['nodes'] and len(nodes) == len(set(nodes)) == 53
    assert sum('::test_saved_expectation_' in n for n in nodes) == 35
    assert abs(current_wall-93.828) < .002
    assert records['expectation_smoke_04']['source_epoch'] != frozen['source_epoch']
    assert records['profile_10']['source_pins'] == selected

    old_manifest = read('baseline_01.snapshot.json')['sources']
    new_manifest = read('expectation_smoke_09.snapshot.json')['sources']
    ast_report = read('legacy_ast_check.json')
    for name, item in old_manifest.items():
        old = definitions((ROOT/item['snapshot']).read_bytes())
        new = definitions((ROOT/new_manifest[name]['snapshot']).read_bytes())
        assert all(new.get(key) == value for key, value in old.items()), name
        assert len(old) == ast_report['sources'][name]['legacy_definitions']
        assert ast_report['sources'][name]['unchanged'] is True
    assert ast_report['unchanged_dependency_paths'] == 47

    profile = read('projection_profile.json')
    assert profile['source_pins'] == selected
    assert profile['order'] == ['full_capture', 'expectation_projection']
    full, projection = profile['observations']
    assert (full['content_reads']['P1']['read_calls'], projection['content_reads']['P1']['read_calls']) == (683,53)
    assert (full['content_reads']['P1']['binary_bytes'], projection['content_reads']['P1']['binary_bytes']) == (2950863,94323)
    assert (full['content_reads']['selected_source']['read_calls'], projection['content_reads']['selected_source']['read_calls']) == (174,233)
    assert (full['content_reads']['selected_source']['binary_bytes'], projection['content_reads']['selected_source']['binary_bytes']) == (3546750,4910128)
    assert projection['content_reads']['source_catalog']['read_calls'] == 1
    assert profile['same_caller_image_bytes'] is True
    assert profile['image_sha'] == dict(bytes=437717, sha256='aaffd03d7a9fd4f03afa18d34ab119b10408b82d5e4ab3f8fc83d9a950600031')
    assert profile['forbidden_scientific_effect_calls'] == 0
    for key in ('actual_saved_F_execution','F_launch_admitted','resource_admission','formal_result','full_workflow_cost_measured'):
        assert profile[key] is False
    assert 13419-2*683+2*53 == 12159 < 12500
    assert 12736-2*683+2*53 == 11476

    for name, before in read('navigation_before.json').items():
        raw = (ROOT/name).read_bytes()
        assert raw.partition(b'\n\n')[0].decode() == before['header']
        assert entry.pin(raw[-before['body']['bytes']:]) == before['body']
    after = read('navigation_after.json')
    assert after['future_prepend_only'] is True
    assert set(after['documents']) == set(read('navigation_before.json'))
    navigation_current = True
    for name, expected in after['documents'].items():
        raw = (ROOT/name).read_bytes()
        header, separator, body = raw.partition(b'\n\n')
        assert separator and header.decode() == expected['header']
        assert entry.pin(body[-expected['body']['bytes']:]) == expected['body'], name
        navigation_current &= entry.pin(raw) == expected['full']
    if require_current_navigation:
        assert navigation_current, 'current navigation differs from complete after pins'
    assert read('document_checks.json')['links_resolve'] is True
    for name, expected in read('document_checks.json')['document_pins'].items():
        assert entry.pin((ROOT/name).read_bytes()) == expected, name
    for name, expected in read('support_pins.json').items():
        assert entry.pin((ROOT/name).read_bytes()) == expected, name

    # Predecessor checks import their own sibling helpers. Reuse a dedicated name,
    # put the predecessor directory first, and restore module search state.
    old_path = list(sys.path)
    try:
        sys.path.insert(0, str(PRIOR))
        spec = importlib.util.spec_from_file_location('previous_supervisor_expectation', PRIOR/'saved_checks.py')
        predecessor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(predecessor)
        old = predecessor.verify()
    finally:
        sys.path[:] = old_path
    assert old['P1_unchanged_files'] == 683
    assert old['conditional_P1_with_host_final_reads'] == 13419
    assert old['actual_saved_F_execution'] is old['F_launch_admitted'] is False
    assert not entry.OUTPUT.parent.exists()
    assert frozen['production_input_gateway_open'] is frozen['transitive_global_binding_closed'] is False
    for key in ('actual_saved_F_execution','F_launch_admitted','scientific_evidence_adopted','resource_admission','formal_result'):
        assert frozen[key] is False
    return dict(authority='DRAFT_NONAUTHORITATIVE', frozen_current_epoch_nodes=53,
        current_canonical_matches_frozen_epoch=bool(current), current_epoch_nodes=53 if current else 0,
        navigation_current_whole_pins_match=bool(navigation_current),
        entire_frozen_navigation_body_preserved=True, future_navigation_prepend_only=True,
        new_expectation_nodes=35, binding_regression_nodes=18, prior_161_inherited_as_current=False,
        observed_current_pytest_seconds=current_wall, observed_all_pytest_seconds=totals['pytest'],
        observed_completed_static_seconds=totals['static'], static_cap_seconds=40, total_cap_seconds=200,
        current_process_time_excluded_until_external_exit_record=True, preservation_paths=3176,
        P1_unchanged_files=683, projection_P1_content_reads=53, projection_full_P1_content_verified=False,
        profile_execution_time_helper_pin_bound=False, conditional_success_with_host_final_P1_reads=12159,
        selected_source_observation_before=174, selected_source_observation_after=233,
        transitive_global_binding_closed=False, production_input_gateway_open=False,
        actual_saved_owner_constructed=False, actual_saved_F_execution=False, F_launch_admitted=False,
        scientific_evidence_adopted=False, resource_admission=False, formal_result=False)


if __name__ == '__main__':
    sys.stdout.buffer.write((json.dumps(verify(require_current_navigation=True), sort_keys=True, indent=2)+'\n').encode())
