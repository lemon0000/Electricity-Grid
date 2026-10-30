"""Bounded outer host preparation and ordinary tests with complete inherited accounting."""
import ast
from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path
import sys
import time
import traceback

assert sys.flags.optimize == 0 and sys.dont_write_bytecode is True
OUT = Path(__file__).absolute().parent
ROOT = OUT.parents[2]
PRIOR = ROOT / 'results/tables/staged_rts24_saved_fresh_host_preentry_v1_non_authoritative'
PROGRAM = ROOT / 'experiments/staged_rts24_saved_fresh_host_windows_preparation_audit_v1.py'
DESIGN = ROOT / 'docs/plan/staged_deliverability_c_saved_fresh_host_windows_design_v1.md'
SCOPE = ROOT / 'docs/plan/staged_deliverability_c_saved_fresh_host_windows_scope_v1.md'
HANDOFF = ROOT / 'docs/plan/continuation_handoff_20261030_saved_fresh_host_preentry_v1.md'
STATE = ROOT / 'docs/plan/continuation_handoff_20261029_saved_fresh_source_cleanup_state_v1.json'
CONTRACT = ROOT / 'experiments/staged_rts24_saved_fresh_contract_snapshot_v1.py'
BEFORE = ROOT / 'results/tables/staged_rts24_saved_fresh_full_context_role_v1_non_authoritative/before_repair.py'
BEFORE_PIN = dict(bytes=48360, sha256='cdfbad787960572c520955bfa8e1187027a2d83d70cf5308050b965ec20ab838')
CHECKPOINT_PIN = dict(bytes=12944, sha256='c2700bd2fa6f9e182753115ad176f64410bcdfc7fd846f5151adfea49df930bf')
INHERITED_COUNT = 1584
OWN_COUNT = 15
OWN_OVERLAP = 6
INPUT_COUNT = 1593
ARCHIVE_COUNT = 348
ARCHIVE_BYTES = 44417283
CAPS = dict(register=5, inspect=6, unit=35, pre_seal=10, saved=8, checkpoint=5)
PHASES = ('register', 'inspect', 'unit', 'pre_seal', 'saved')
TOTAL_CAP = 69
FALSE_FIELDS = ('producer_capability_verified', 'full_runtime_binding_verified', 'full_P1_content_verified',
    'role_bootstrap', 'permit_issued', 'run_authority', 'resource_admission', 'scientific_evidence_adopted',
    'formal_result', 'actual_F', 'production_seal', 'initial_project_state_authenticated',
    'independent_tcb_authenticated', 'whole_workflow_budget_admitted', 'whole_workflow_performance_review_complete',
    'saved_P1_fresh_process_verified', 'saved_P1_parent_adoption_verified', 'full_role_entry_connected',
    'physical_host_provider_implemented','source_authenticated_host_issuer','native_equivalence_verified',
    'native_return_to_publication_window_verified','new_startup_profile_verified','actual_entry_authenticated',
    'real_broker_cancel_ack_verified','real_transport_payload_equivalence_verified','core51_full_manifest_validated',
    'native_authorized','public_P2_execution_enabled')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def read(path):
    return parse_record(path.read_bytes())


def parse_record(raw):
    def unique(items):
        result = {}
        for key, value in items:
            assert key not in result, 'duplicate record key'
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique)


def flags():
    return {key: False for key in FALSE_FIELDS}


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def selected_sources():
    tree = ast.parse(PROGRAM.read_bytes())
    node = next(node for node in tree.body if type(node) is ast.Assign and len(node.targets) == 1
        and type(node.targets[0]) is ast.Name and node.targets[0].id == 'FILES')
    values = ast.literal_eval(node.value)
    assert len(values) == 8 and all(type(value) is str for value in values.values())
    return tuple(ROOT / value for value in values.values())


def own():
    return (PROGRAM, DESIGN, SCOPE, HANDOFF, STATE, CONTRACT, Path(__file__).absolute(), *selected_sources())


def output(action):
    return OUT / ('registration.json' if action == 'register' else 'checkpoint.json' if action == 'checkpoint' else action + '.exit.json')


def merge_pins(target, items):
    for path, value in items.items():
        if path in target:
            assert target[path] == value, path
        target[path] = value


def save(path, value):
    raw = canonical(value)
    assert path.parent == OUT and not path.exists() and len(raw) <= 1048576
    files = list(OUT.iterdir())
    reserve = 0 if path.name == 'checkpoint.json' else 1048576
    assert all(path.is_file() for path in files) and len(files) + 1 + bool(reserve) <= 10
    assert sum(path.stat().st_size for path in files) + len(raw) + reserve <= 4194304
    with path.open('xb') as stream:
        stream.write(raw)


def predecessor_accounting():
    raw=(PRIOR/'checkpoint.json').read_bytes();assert pin(raw)==CHECKPOINT_PIN
    cp=parse_record(raw)
    assert canonical(cp)==raw and cp['accepted'] is cp['accounting_complete'] is cp['diagnostic_accepted'] is True
    assert cp['prior_not_accepted_count']==61 and cp['known_scope_not_accepted_records']==[]
    assert cp['all_cumulative_total_seconds']==1553.7301798999972
    assert cp['all_cumulative_charged_seconds']==dict(static=744.9687038000004,pytest=366.48897970000326,unittest=442.27249639999354)
    return cp


def unrelated_snapshot():
    state = read(STATE)
    assert state['unrelated_count'] == len(state['unrelated_worktree']) == 42
    for row in state['unrelated_worktree']:
        path = ROOT / row['path']
        assert path.exists() is row['exists'], row['path']
        if row['exists']:
            assert pin(path.read_bytes()) == {key: row[key] for key in ('bytes', 'sha256')}, row['path']


def previous():
    cp=predecessor_accounting()
    prior_root={path:value for path,value in cp['known_pins'].items() if Path(path).parent==PRIOR}
    prior_root[str(PRIOR/'checkpoint.json')]=CHECKPOINT_PIN
    assert len(prior_root)==7 and sum(row['bytes'] for row in prior_root.values())==915420
    assert set(prior_root)=={str(path) for path in PRIOR.iterdir()}
    raw=(PRIOR/'registration.json').read_bytes();assert pin(raw)==prior_root[str(PRIOR/'registration.json')]
    reg=parse_record(raw)
    assert canonical(reg)==raw and reg['accepted'] is True
    assert reg['effective_input_count']==len(reg['input_pins'])==1578 and len(reg['own_input_pins'])==12
    assert all(cp['known_pins'][path]==value for path,value in reg['own_input_pins'].items())
    inputs=dict(reg['input_pins']);merge_pins(inputs,prior_root)
    assert len(inputs)==INHERITED_COUNT and sum(row['bytes'] for row in inputs.values())==91329946
    archive=dict(reg['archive_pins'])
    assert len(archive)==341 and sum(row['bytes'] for row in archive.values())==43501863
    merge_pins(archive,prior_root)
    assert len(archive)==ARCHIVE_COUNT and sum(row['bytes'] for row in archive.values())==ARCHIVE_BYTES
    verify=dict(inputs);merge_pins(verify,archive)
    for path,value in verify.items():assert pin(Path(path).read_bytes())==value,path
    assert len({str(Path(path).resolve()).casefold() for path in inputs})==INHERITED_COUNT
    assert len({str(Path(path).resolve()).casefold() for path in archive})==ARCHIVE_COUNT
    assert pin(BEFORE.read_bytes())==BEFORE_PIN
    unrelated_snapshot()
    return cp,inputs,archive


def input_maps(inherited):
    own_pins = {str(path): pin(path.read_bytes()) for path in own()}
    assert len(own_pins) == OWN_COUNT and len(set(inherited) & set(own_pins)) == OWN_OVERLAP
    result = dict(inherited)
    merge_pins(result, own_pins)
    assert len(result) == INPUT_COUNT == INHERITED_COUNT + OWN_COUNT - OWN_OVERLAP
    assert len({str(Path(path).resolve()).casefold() for path in result}) == INPUT_COUNT
    return result, own_pins


def original_contract():
    return load(CONTRACT, '_held_original_F_contract').snapshot()


def check(reg):
    assert reg['accepted'] is True and reg['python_optimized'] is False
    _, inherited, archive = previous()
    inputs, own_pins = input_maps(inherited)
    assert reg['input_pins'] == inputs and reg['effective_input_count'] == INPUT_COUNT
    assert reg['archive_pins'] == archive and reg['prior_archive_files'] == ARCHIVE_COUNT
    assert reg['prior_archive_bytes'] == ARCHIVE_BYTES and reg['own_input_pins'] == own_pins
    assert reg['previous_checkpoint_pin'] == CHECKPOINT_PIN
    assert canonical(reg['original_F_contract']) == canonical(original_contract())
    assert all(reg[key] is False for key in FALSE_FIELDS)
    return reg


def saved(reg):
    row = read(OUT / 'inspect.exit.json')
    assert row['accepted'] is True
    review = read(OUT / 'pre_seal.exit.json')
    assert review['accepted'] is True
    finding = review['payload']['findings']
    assert finding['registration_pin'] == pin((OUT / 'registration.json').read_bytes())
    assert finding['inspect_exit_pin'] == pin((OUT / 'inspect.exit.json').read_bytes())
    assert finding['own_input_pins'] == reg['own_input_pins'] and finding['must_fix_open'] == []
    unit_row = read(OUT / 'unit.exit.json')
    assert unit_row['accepted'] is True and finding['unit_exit_pin'] == pin((OUT / 'unit.exit.json').read_bytes())
    unit_report = unit_row['payload']['report']
    assert pin(canonical(unit_report)) == unit_row['payload']['report_pin']
    assert unit_report['success'] is True and unit_report['methods'] == 42 and unit_report['errors'] == unit_report['failures'] == unit_report['skipped'] == []
    assert pin(unit_report['raw_log'].encode('utf8')) == unit_report['raw_log_pin']
    assert finding['official_review'] is False and finding['verified_input_count'] == INPUT_COUNT
    report = row['payload']['report']
    assert pin(canonical(report)) == row['payload']['report_pin']
    audit = load(PROGRAM, '_saved_static_route')
    audit.verify_unit(unit_report)
    replay = audit.replay_saved(report)
    return dict(accepted=True, inspect_exit_pin=pin((OUT / 'inspect.exit.json').read_bytes()),
        report_pin=pin(canonical(report)), replay=replay, unit_exit_pin=pin((OUT / 'unit.exit.json').read_bytes()),
        unit_raw_log_pin=unit_report['raw_log_pin'], unit_methods=42, validation_child_processes=0,
        project_target_child_processes=0, P1_reads=0, source49_modules_executed=0, **flags())


def charge_fields(row, action):
    assert row['action'] == action and row['authority'] == 'DRAFT_NONAUTHORITATIVE'
    assert row['kind'] == ('unittest' if action == 'unit' else 'static') and row['cap_seconds'] == CAPS[action]
    charge = row['charged_seconds']
    assert type(charge) in (float, int) and math.isfinite(charge) and charge >= 0
    return row


def record_fields(row, action):
    charge_fields(row, action)
    assert type(row['accepted']) is bool and all(row[key] is False for key in FALSE_FIELDS)
    if row['accepted']:
        assert row['error'] is None and row['charged_seconds'] <= CAPS[action]
    return row


def phase_records(action):
    paths = {output(name).name: name for name in PHASES}
    present = {path.name for path in OUT.iterdir()}
    assert present <= set(paths) | {'driver.py'} and 'driver.py' in present
    records = {}
    for name, phase in paths.items():
        if name in present:
            raw = (OUT / name).read_bytes()
            row = record_fields(parse_record(raw), phase)
            assert canonical(row) == raw
            records[name] = row
    names = [name for name in PHASES if output(name).name in records]
    assert names == list(PHASES[:len(names)])
    if action == 'checkpoint':
        assert names and (len(names) == len(PHASES) or records[output(names[-1]).name]['accepted'] is False)
        assert all(records[output(name).name]['accepted'] is True for name in names[:-1])
    else:
        assert names == list(PHASES[:PHASES.index(action)]) and all(row['accepted'] is True for row in records.values())
    assert sum(row['charged_seconds'] for row in records.values()) + CAPS[action] <= TOTAL_CAP
    return records


def known_pins():
    result, errors = {}, []
    for path in (*own(), PRIOR / 'checkpoint.json', *OUT.iterdir()):
        if str(path) in result:
            continue
        try:
            result[str(path)] = pin(path.read_bytes())
        except BaseException as caught:
            errors.append(str(path) + ':' + type(caught).__name__ + ':' + str(caught))
    return result, errors


def checkpoint_accounting():
    usage, errors, pins, failed = dict(static=0., unittest=0.), [], {}, []
    expected = {output(name).name: name for name in PHASES}
    for path in OUT.iterdir():
        if path.name == 'driver.py':
            continue
        try:
            raw = path.read_bytes()
            pins[str(path)] = pin(raw)
            assert path.name in expected
            row = charge_fields(parse_record(raw), expected[path.name])
            usage[row['kind']] += row['charged_seconds']
            if row.get('accepted') is False:
                failed.append(path.name)
            record_fields(row, expected[path.name])
            assert canonical(row) == raw
        except BaseException as caught:
            errors.append(path.name + ':' + type(caught).__name__ + ':' + str(caught))
    prior = None
    try:
        prior = predecessor_accounting()
    except BaseException as caught:
        errors.append('predecessor:' + type(caught).__name__ + ':' + str(caught))
    return dict(scope_charged_seconds=usage, scope_accounting_complete=not any(not item.startswith('predecessor:') for item in errors),
        prior_accounting_complete=prior is not None, accounting_errors=errors, charged_record_pins=pins,
        known_scope_not_accepted_records=failed, previous_cumulative=None if prior is None else prior['all_cumulative_charged_seconds'],
        previous_not_accepted_count=None if prior is None else prior['prior_not_accepted_count'])


def run(action):
    assert action in CAPS
    path = output(action)
    assert not path.exists() and not (OUT / 'checkpoint.json').exists(), 'create-only terminal scope'
    started = time.perf_counter()
    payload, error, accepted, records = {}, None, False, {}
    try:
        records = phase_records(action)
        if action == 'register':
            _, inherited, archive = previous()
            for item in own():
                if item.suffix == '.py':
                    compile(item.read_bytes(), str(item), 'exec', dont_inherit=True, optimize=0)
            inputs, own_pins = input_maps(inherited)
            payload = dict(input_pins=inputs, effective_input_count=INPUT_COUNT, archive_pins=archive,
                own_input_pins=own_pins, prior_archive_files=ARCHIVE_COUNT, prior_archive_bytes=ARCHIVE_BYTES,
                original_F_contract=original_contract(), python_optimized=False, previous_checkpoint_pin=CHECKPOINT_PIN)
        elif action == 'checkpoint':
            failed = [name for name, value in records.items() if value['accepted'] is False]
            if not failed:
                assert set(records) == {output(name).name for name in PHASES}
                reg = check(records['registration.json'])
                assert canonical(saved(reg)) == canonical(records['saved.exit.json']['payload'])
            else:
                previous()
            payload = dict(diagnostic_accepted=not failed)
        else:
            reg = check(read(OUT / 'registration.json'))
            if action == 'inspect':
                audit = load(PROGRAM, '_endpoint_preparation_static')
                report = audit.snapshot()
                assert report['acceptance_scope'] == 'host_win32_resource_source_and_private_protocol_synthetic_only'
                assert report['test_methods'] == 42
                assert all(report[key] is False for key in ('full_role_entry_connected','native_equivalence_verified',
                    'native_return_to_publication_window_verified','new_startup_profile_verified','run_authority','actual_F','formal_result'))
                payload = dict(report=report, report_pin=pin(canonical(report)))
            elif action == 'unit':
                report = load(PROGRAM, '_endpoint_preparation_unit').unit()
                payload = dict(report=report, report_pin=pin(canonical(report)))
                assert report['success'] is True and report['methods'] == 42 and report['skipped'] == []
                assert len(report['ids']) == len(set(report['ids'])) == 42
            elif action == 'pre_seal':
                raw = sys.stdin.buffer.read(32769)
                assert len(raw) <= 32768
                finding = parse_record(raw)
                assert canonical(finding) == raw and finding['must_fix_open'] == [] and finding['official_review'] is False
                assert finding['registration_pin'] == pin((OUT / 'registration.json').read_bytes())
                assert finding['inspect_exit_pin'] == pin((OUT / 'inspect.exit.json').read_bytes())
                assert finding['own_input_pins'] == reg['own_input_pins'] and finding['verified_input_count'] == INPUT_COUNT
                assert read(OUT / 'inspect.exit.json')['accepted'] is True
                assert read(OUT / 'unit.exit.json')['accepted'] is True
                assert finding['unit_exit_pin'] == pin((OUT / 'unit.exit.json').read_bytes())
                payload = dict(findings=finding)
            else:
                assert read(OUT / 'pre_seal.exit.json')['accepted'] is True
                payload = saved(reg)
            check(reg)
        accepted = True
    except BaseException as caught:
        error = type(caught).__name__ + ':' + str(caught)
        payload['failure_trace'] = [dict(file=row.filename, line=row.lineno, function=row.name, source=row.line)
            for row in traceback.extract_tb(caught.__traceback__, limit=20)]
    if action == 'checkpoint':
        payload.update(checkpoint_accounting())
    if not accepted or action == 'checkpoint':
        known, pin_errors = known_pins()
        payload.update(known_pins=known, pin_errors=pin_errors)
    charge = time.perf_counter() - started
    accepted = accepted and charge <= CAPS[action]
    if charge > CAPS[action] and error is None:
        error = 'phase_cap_exceeded'
    record = dict(accepted=accepted, authority='DRAFT_NONAUTHORITATIVE', action=action, kind='unittest' if action == 'unit' else 'static',
        charged_seconds=charge, cap_seconds=CAPS[action], error=error, payload=payload, **flags())
    if action == 'register' and accepted:
        record.update(payload)
    if action == 'checkpoint':
        usage = payload['scope_charged_seconds']
        usage['static'] += charge
        complete = payload['scope_accounting_complete'] and payload['prior_accounting_complete']
        accepted = accepted and complete and not payload['pin_errors'] and sum(usage.values()) <= TOTAL_CAP and usage['static'] <= 34 and usage['unittest'] <= 35
        cumulative = dict(payload['previous_cumulative']) if complete else None
        if complete:
            cumulative['static'] += usage['static']
            cumulative['unittest'] += usage['unittest']
        diagnostic = accepted and payload.get('diagnostic_accepted') is True
        record.update(payload, accepted=accepted, diagnostic_accepted=diagnostic, error=error,
            acceptance_scope='host_win32_resource_source_and_private_protocol_synthetic_only' if diagnostic else 'rejection_metadata_only',
            accounting_complete=complete, all_cumulative_charged_seconds=cumulative,
            all_cumulative_total_seconds=None if cumulative is None else sum(cumulative.values()),
            package_charged_seconds=sum(usage.values()), prior_not_accepted_count=None if not complete else
                payload['previous_not_accepted_count'] + len(payload['known_scope_not_accepted_records']) + (not accepted),
            validation_child_processes=0, project_target_child_processes=0, fixture_child_processes=0,
            P1_reads=0, cold_calls=0, source49_modules_executed=0)
    save(path, record)
    print(canonical(dict(action=action, accepted=accepted, charge=charge, error=error)).decode())
    if not accepted:
        raise SystemExit(1)


if __name__ == '__main__':
    run(sys.argv[1])
