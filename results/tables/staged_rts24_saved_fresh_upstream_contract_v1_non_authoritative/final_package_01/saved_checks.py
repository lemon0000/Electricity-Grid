"""Read-only saved design oracle. Current scientific ENTRY is never imported."""
import base64
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
MAIN = HERE.parent/'checks_01'
PREVIOUS = ROOT/'results/tables/staged_rts24_saved_fresh_successor_direct_entry_v1_non_authoritative/final_package_01/saved_checks.py'

def raw(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('ascii')

def pin(data):
    return dict(bytes=len(data), sha256=sha256(data).hexdigest())

def read(path):
    return json.loads(path.read_bytes())

def loaded(path, expected, label):
    data = path.read_bytes(); assert pin(data) == expected
    loader = importlib.util.spec_from_file_location(label, path)
    module = importlib.util.module_from_spec(loader); loader.loader.exec_module(module)
    assert pin(path.read_bytes()) == expected
    return module

def verify(require_current_sources=False, require_current_navigation=False):
    freeze = read(HERE/'execution_freeze.json')
    actual = {p.relative_to(ROOT).as_posix(): pin(p.read_bytes()) for p in MAIN.rglob('*') if p.is_file()}
    assert actual == freeze['files'] and len(actual) == freeze['count'] <= 32
    assert sum(p['bytes'] for p in actual.values()) == freeze['bytes'] <= 2*1024**2
    assert pin(raw(actual)) == freeze['root']
    baseline = read(MAIN/'baseline.json')
    revision_path = MAIN/'draft_revision_02.json'; revision = read(revision_path)
    assert revision['baseline_pin'] == pin((MAIN/'baseline.json').read_bytes())
    assert set(revision['helpers_after']) == set(baseline['helpers'])
    assert set(revision['input_overrides']) == {'docs/plan/staged_deliverability_c_saved_fresh_upstream_contract_scope_budget_v1.md'}
    archive_path = MAIN/'design_attempt_01.snapshot.json'
    assert pin(archive_path.read_bytes()) == revision['archive_pin']
    archive = read(archive_path)['files']
    assert set(archive) == {'fixed_templates.json','protocol_domains.json','protocol_dag.json','verification_matrix.json',*revision['input_overrides']}
    for n, item in archive.items():
        data = base64.b64decode(item['raw_base64'])
        assert pin(data) == {k:item[k] for k in ('bytes','sha256')}
        if n in revision['input_overrides']: assert pin(data) == baseline['inputs'][n]
    for helper_epoch in (baseline['helpers'], revision['helpers_after']):
        for n, expected in helper_epoch.items():
            assert pin((MAIN/('helper_'+expected['sha256']+'.snapshot')).read_bytes()) == expected, n
    for n, expected in {**baseline['preserved'], **baseline['inputs'], **baseline['helpers'], **revision['helpers_after'], **revision['input_overrides']}.items():
        assert pin((ROOT/n).read_bytes()) == expected, n
    current_sources = all(pin((ROOT/n).read_bytes()) == p for n, p in baseline['sources'].items())
    if require_current_sources: assert current_sources
    docs = read(MAIN/'document_checks.json')
    current_navigation = all(pin((ROOT/n).read_bytes()) == p for n, p in docs['document_pins'].items())
    if require_current_navigation: assert current_navigation
    else:
        for n, expected in docs['document_pins'].items():
            data = (ROOT/n).read_bytes()
            assert pin(data[-expected['bytes']:] if n in baseline['navigation_before'] else data) == expected, n
    support = read(HERE/'support_pins.json'); support_pin = pin((HERE/'support_pins.json').read_bytes())
    assert set(support) == {(HERE/n).relative_to(ROOT).as_posix() for n in ('execution_freeze.json','saved_checks.py')}
    for n, expected in support.items(): assert pin((ROOT/n).read_bytes()) == expected
    records = {p.relative_to(ROOT).as_posix(): read(p) for directory in (MAIN,HERE) for p in directory.glob('*.exit.json')}
    assert 4 <= len(records) <= 6
    main_labels = {Path(n).name for n in records if Path(n).parent == MAIN.relative_to(ROOT)}
    assert main_labels == {n+'.exit.json' for n in ('baseline_01','design_02','design_03','finalizer_04')}
    total = 0.
    for n, value in records.items():
        path = ROOT/n; stem = path.name.removesuffix('.exit.json')
        assert value['returncode'] == 0 and value['accepted'] and value['error'] is None
        old_epoch = stem in ('baseline_01','design_02')
        expected_helpers = baseline['helpers'] if old_epoch else revision['helpers_after']
        expected_inputs = dict(baseline['inputs'])
        expected_fixed = {**baseline['sources'], **baseline['preserved'], **expected_inputs, **expected_helpers}
        if not old_epoch:
            assert value['helper_epoch'] == 'draft_revision_02' and value['revision_pin'] == pin(revision_path.read_bytes())
            expected_fixed.update(revision['input_overrides'])
            expected_fixed[revision_path.relative_to(ROOT).as_posix()] = pin(revision_path.read_bytes())
            expected_fixed[archive_path.relative_to(ROOT).as_posix()] = revision['archive_pin']
            assert value['design_output_pins'] == { (MAIN/k).relative_to(ROOT).as_posix():pin((MAIN/k).read_bytes())
                for k in ('fixed_templates.json','protocol_domains.json','protocol_dag.json','verification_matrix.json') }
        assert value['fixed_before'] == value['fixed_after'] == pin(raw(expected_fixed))
        assert value['baseline_pin'] == pin((MAIN/'baseline.json').read_bytes())
        assert value['stdout_pin'] == pin((path.parent/(stem+'.stdout.log')).read_bytes())
        assert value['stderr_pin'] == pin(b'') == pin((path.parent/(stem+'.stderr.log')).read_bytes())
        script_name = Path(value['argv'][2]).relative_to(ROOT).as_posix()
        assert value['script_pin'] == expected_helpers[script_name]
        assert value['script_pin'] == pin((MAIN/('helper_'+value['script_pin']['sha256']+'.snapshot')).read_bytes())
        assert value['tail_reserve_seconds'] == .25
        assert value['charged_seconds'] == value['observed_capture_seconds']+.25 <= 12
        assert value['previous_charged_seconds'] == sum(records[k]['charged_seconds'] for k in value['prior_records'])
        assert all(k in records and pin((ROOT/k).read_bytes()) == p for k,p in value['prior_records'].items())
        if path.parent == HERE: assert value['support_pin'] == support_pin
        total += value['charged_seconds']
    assert total <= 90
    design = loaded(MAIN/'design_oracle.py', revision['helpers_after'][(MAIN/'design_oracle.py').relative_to(ROOT).as_posix()], 'frozen_upstream_design_oracle').verify()
    assert read(MAIN/'design_03.stdout.log') == design and design['design_mutations_rejected'] == 21
    assert read(MAIN/'design_02.stdout.log')['design_mutations_rejected'] == 15
    previous = loaded(PREVIOUS, baseline['preserved'][PREVIOUS.relative_to(ROOT).as_posix()], 'frozen_direct_entry_archive')
    prior = previous.verify(require_current_sources=require_current_sources)
    assert prior['frozen_epoch_test_nodes'] == 282 and prior['ordinary_cold_process_probes'] == 8
    assert prior['P1_unchanged_files'] == 683 and prior['scientific_ENTRY_imported_by_oracle'] is False
    assert not (ROOT/'results/tables/staged_rts24_saved_fresh_adoption_v1_non_authoritative').exists()
    package = [p for p in HERE.rglob('*') if p.is_file()]
    assert len(package) <= 16 and sum(p.stat().st_size for p in package) <= 1024**2
    return dict(authority='DRAFT_NONAUTHORITATIVE', **{k:v for k,v in design.items() if k != 'authority'},
                preserved_paths=len(baseline['preserved']), P1_unchanged_files=683,
                reused_frozen_epoch_test_nodes=282, current_epoch_test_nodes=282 if current_sources else 0,
                reused_ordinary_cold_process_probes=8, new_pytest_nodes=0, new_cold_process_probes=0, new_simulated_hours=0,
                current_design_epoch='draft_revision_02', historical_design_mutations=15, current_design_mutations=21,
                historical_design_archive_exact_bytes_retained=True, historical_design_archive_execution_binding_proved=False,
                source_epoch=baseline['source_epoch'], current_sources_match=current_sources, current_navigation_match=current_navigation,
                completed_capture_records=len(records), completed_charged_static_seconds=total,
                current_capture_not_counted_until_external_exit=True, whole_workflow_wall_budget_verified=False,
                execution_files=freeze['count'], execution_bytes=freeze['bytes'], package_files=len(package),
                package_bytes=sum(p.stat().st_size for p in package))

def guard(event, args):
    if event in ('subprocess.Popen','os.system','os.posix_spawn','os.spawn'):
        raise AssertionError('saved oracle cannot launch a subprocess')
    if event == 'import' and args and str(args[0]).split('.')[0] in ('src','experiments','numpy','scipy','pyomo','highspy'):
        raise AssertionError('saved oracle cannot import scientific/project implementation')

if __name__ == '__main__':
    assert not sys.argv[1:]
    sys.addaudithook(guard)
    print(json.dumps(verify(require_current_sources=True, require_current_navigation=True), sort_keys=True))
