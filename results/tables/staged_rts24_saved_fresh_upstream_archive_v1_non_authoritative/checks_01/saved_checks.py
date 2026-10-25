"""Read-only saved design oracle. Current scientific ENTRY is never imported."""
import base64
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import re
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
HERE = ROOT/'results/tables/staged_rts24_saved_fresh_upstream_contract_v1_non_authoritative/final_package_01'
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

def verify_previous_upstream(require_current_sources=False):
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
    migration = read(HERE/'document_migration.json')
    assert pin((HERE/'terminal_checks.py').read_bytes()) == migration['terminal_helper_pin']
    assert set(migration['documents']) == set(baseline['navigation_before']) | {n for n in baseline['new_documents'] if n not in baseline['inputs']}
    current_navigation = True
    for n, expected in docs['document_pins'].items():
        data = (ROOT/n).read_bytes()
        if n not in migration['documents']:
            assert pin(data) == expected
            continue
        item = migration['documents'][n]; prefix = base64.b64decode(item['prefix_base64'])
        assert item['before_pin'] == expected
        current_navigation &= pin(data) == item['after_pin']
        if item['kind'] == 'header_reorder':
            header, separator, body = data.partition(b'\n')
            assert separator and header == base64.b64decode(item['header_base64'])
            suffix = body[-item['body_suffix_pin']['bytes']:]
            assert pin(suffix) == item['body_suffix_pin'] and suffix.startswith(prefix)
            original = header+b'\n'+suffix[len(prefix):]
            assert pin(original) == baseline['navigation_before'][n]
            assert pin(prefix+original) == expected
        else:
            assert item['kind'] == 'prepend'
            suffix = data[-expected['bytes']:]
            assert pin(suffix) == expected
            assert pin(prefix+suffix) == item['after_pin']
            checkpoint = read(HERE.parent/'checkpoint_status.json')
            assert pin(data) == checkpoint['post_terminal_document_pins'][n]
    assert pin((ROOT/migration['supplement_path']).read_bytes()) == migration['supplement_pin']
    for n, expected in migration['original_package_files'].items(): assert pin((ROOT/n).read_bytes()) == expected
    support = read(HERE/'support_pins.json'); support_pin = pin((HERE/'support_pins.json').read_bytes())
    assert set(support) == {(HERE/n).relative_to(ROOT).as_posix() for n in ('execution_freeze.json','saved_checks.py')}
    for n, expected in support.items(): assert pin((ROOT/n).read_bytes()) == expected
    records = {p.relative_to(ROOT).as_posix(): read(p) for directory in (MAIN,HERE) for p in directory.glob('*.exit.json')}
    assert len(records) == 6
    assert {Path(n).name for n in records} == {n+'.exit.json' for n in ('baseline_01','design_02','design_03','finalizer_04','saved_05','terminal_06')}
    main_labels = {Path(n).name for n in records if Path(n).parent == MAIN.relative_to(ROOT)}
    assert main_labels == {n+'.exit.json' for n in ('baseline_01','design_02','design_03','finalizer_04')}
    total = 0.
    for n, value in records.items():
        path = ROOT/n; stem = path.name.removesuffix('.exit.json')
        historical_failure = stem in ('saved_05','terminal_06')
        if historical_failure:
            assert value['returncode'] == 1 and value['accepted'] is False and value['error'] is None
            assert value['stdout_pin'] == pin(b'')
            expected_error = dict(saved_05={'bytes':1200,'sha256':'253ca7d37852b166ecb64e5d2e495a5f5b78b6ccd311ffd50d03b12a0f703037'},
                terminal_06={'bytes':1206,'sha256':'1f8d8e28205adbcebaa4e583ff4587ae18733526151e49e6c2dccb534d7044f7'})[stem]
            assert value['stderr_pin'] == expected_error
            error_raw = (path.parent/(stem+'.stderr.log')).read_bytes()
            assert b'line 178, in verify' in error_raw and error_raw.rstrip().endswith(b'AssertionError')
            if stem == 'terminal_06': assert value['package_postcheck_verified'] is True
        else:
            assert value['returncode'] == 0 and value['accepted'] and value['error'] is None
        old_epoch = stem in ('baseline_01','design_02')
        expected_helpers = baseline['helpers'] if old_epoch else revision['helpers_after']
        expected_inputs = dict(baseline['inputs'])
        expected_fixed = {**baseline['sources'], **baseline['preserved'], **expected_inputs, **expected_helpers}
        if not old_epoch:
            assert value['helper_epoch'] == ('mechanical_successor_02' if stem == 'terminal_06' else 'draft_revision_02')
            assert value['revision_pin'] == pin(revision_path.read_bytes())
            expected_fixed.update(revision['input_overrides'])
            expected_fixed[revision_path.relative_to(ROOT).as_posix()] = pin(revision_path.read_bytes())
            expected_fixed[archive_path.relative_to(ROOT).as_posix()] = revision['archive_pin']
            assert value['design_output_pins'] == { (MAIN/k).relative_to(ROOT).as_posix():pin((MAIN/k).read_bytes())
                for k in ('fixed_templates.json','protocol_domains.json','protocol_dag.json','verification_matrix.json') }
        assert value['fixed_before'] == value['fixed_after'] == pin(raw(expected_fixed))
        assert value['baseline_pin'] == pin((MAIN/'baseline.json').read_bytes())
        assert value['stdout_pin'] == pin((path.parent/(stem+'.stdout.log')).read_bytes())
        assert value['stderr_pin'] == pin((path.parent/(stem+'.stderr.log')).read_bytes())
        if not historical_failure: assert value['stderr_pin'] == pin(b'')
        script_name = Path(value['argv'][2]).relative_to(ROOT).as_posix()
        if stem == 'terminal_06':
            assert script_name == (HERE/'terminal_checks.py').relative_to(ROOT).as_posix()
            assert value['script_pin'] == migration['terminal_helper_pin']
            assert value['migration_pin'] == pin((HERE/'document_migration.json').read_bytes())
            assert value['script_pin'] == pin((HERE/'terminal_checks.snapshot').read_bytes())
        else:
            assert value['script_pin'] == expected_helpers[script_name]
            assert value['script_pin'] == pin((MAIN/('helper_'+value['script_pin']['sha256']+'.snapshot')).read_bytes())
        assert value['tail_reserve_seconds'] == .25
        assert value['charged_seconds'] == value['observed_capture_seconds']+.25 <= 12
        assert value['previous_charged_seconds'] == sum(records[k]['charged_seconds'] for k in value['prior_records'])
        assert all(k in records and pin((ROOT/k).read_bytes()) == p for k,p in value['prior_records'].items())
        if path.parent == HERE: assert value['support_pin'] == support_pin
        total += value['charged_seconds']
    assert total <= 90
    assert {Path(n).name for n,v in records.items() if not v['accepted']} == {'saved_05.exit.json','terminal_06.exit.json'}
    assert pin((HERE/'terminal_checks.snapshot').read_bytes()) == migration['terminal_helper_pin']
    assert pin((HERE/'terminal_capture.snapshot').read_bytes()) == migration['terminal_capture_pin'] == pin((HERE/'terminal_capture.py').read_bytes())
    design = loaded(MAIN/'design_oracle.py', revision['helpers_after'][(MAIN/'design_oracle.py').relative_to(ROOT).as_posix()], 'frozen_upstream_design_oracle').verify()
    assert read(MAIN/'design_03.stdout.log') == design and design['design_mutations_rejected'] == 21
    assert read(MAIN/'design_02.stdout.log')['design_mutations_rejected'] == 15
    previous = loaded(PREVIOUS, baseline['preserved'][PREVIOUS.relative_to(ROOT).as_posix()], 'frozen_direct_entry_archive')
    prior = previous.verify(require_current_sources=require_current_sources)
    assert prior['frozen_epoch_test_nodes'] == 282 and prior['ordinary_cold_process_probes'] == 8
    assert prior['P1_unchanged_files'] == 683 and prior['scientific_ENTRY_imported_by_oracle'] is False
    assert not (ROOT/'results/tables/staged_rts24_saved_fresh_adoption_v1_non_authoritative').exists()
    package = [p for p in HERE.rglob('*') if p.is_file()]
    expected_members = set(migration['expected_package_members'])
    actual_members = {p.name for p in package}
    terminal_members = {'terminal_06.stdout.log','terminal_06.stderr.log','terminal_06.exit.json'}
    assert actual_members == (expected_members if (HERE/'terminal_06.exit.json').exists() else expected_members-terminal_members)
    assert len(package) <= 16 and sum(p.stat().st_size for p in package) <= 1024**2
    return dict(authority='DRAFT_NONAUTHORITATIVE', **{k:v for k,v in design.items() if k != 'authority'},
                preserved_paths=len(baseline['preserved']), P1_unchanged_files=683,
                reused_frozen_epoch_test_nodes=282, current_epoch_test_nodes=282 if current_sources else 0,
                reused_ordinary_cold_process_probes=8, new_pytest_nodes=0, new_cold_process_probes=0, new_simulated_hours=0,
                current_design_epoch='draft_revision_02', historical_design_mutations=15, current_design_mutations=21,
                historical_design_archive_exact_bytes_retained=True, historical_design_archive_execution_binding_proved=False,
                historical_saved_05_exit=1, historical_saved_05_accepted=False, navigation_migration_verified=True,
                historical_terminal_06_exit=1, historical_terminal_06_accepted=False,
                source_epoch=baseline['source_epoch'], current_sources_match=current_sources, current_navigation_match=current_navigation,
                completed_capture_records=len(records), completed_charged_static_seconds=total,
                successful_completed_capture_records=4, failed_historical_capture_records=2,
                current_capture_not_counted_until_external_exit=True, whole_workflow_wall_budget_verified=False,
                execution_files=freeze['count'], execution_bytes=freeze['bytes'], package_files=len(package),
                package_bytes=sum(p.stat().st_size for p in package))

def guard(event, args):
    if event in ('subprocess.Popen','os.system','os.posix_spawn','os.spawn'):
        raise AssertionError('saved oracle cannot launch a subprocess')
    if event == 'import' and args and str(args[0]).split('.')[0] in ('src','experiments','numpy','scipy','pyomo','highspy'):
        raise AssertionError('saved oracle cannot import scientific/project implementation')

def verify(require_current_sources=False, require_current_navigation=False, require_support=True):
    baseline = read(OUT/'baseline.json')
    for n, expected in {**baseline['preserved'], **baseline['helpers'], **baseline['fixed_documents']}.items():
        assert pin((ROOT/n).read_bytes()) == expected, n
    for n, expected in baseline['helpers'].items():
        assert pin((OUT/(Path(n).stem+'.snapshot')).read_bytes()) == expected
    current_sources = all(pin((ROOT/n).read_bytes()) == expected for n,expected in baseline['sources'].items())
    if require_current_sources: assert current_sources
    nav = read(OUT/'navigation_migration.json')
    assert set(nav) == {'docs/plan/科研项目执行步骤.md','docs/plan/staged_deliverability_c_scope_and_budget_plan_v1.md',
                        'docs/model_spec/blocker_register.md','paper/drafts/README.md'}
    current_navigation = True
    for n, item in nav.items():
        assert set(item) == {'header_base64','prefix_base64','before_full_pin','before_body_pin','after_body_pin','after_full_pin'}
        data = (ROOT/n).read_bytes(); header, separator, body = data.partition(b'\n\n')
        assert separator and header == base64.b64decode(item['header_base64'])
        suffix = body[-item['after_body_pin']['bytes']:]
        assert pin(suffix) == item['after_body_pin']
        prefix = base64.b64decode(item['prefix_base64'])
        assert suffix.startswith(prefix)
        previous_body = suffix[len(prefix):]
        assert pin(previous_body) == item['before_body_pin']
        assert pin(header+b'\n'+previous_body) == item['before_full_pin']
        assert pin(header+b'\n\n'+suffix) == item['after_full_pin']
        current_navigation &= pin(data) == item['after_full_pin']
    if require_current_navigation: assert current_navigation
    support_path = OUT/'support_pins.json'
    if require_support:
        support = read(support_path)
        assert set(support) == set(baseline['support_member_names'])
        for n,expected in support.items(): assert pin((ROOT/n).read_bytes()) == expected, n
    else:
        assert not support_path.exists()
    records = {p.name.removesuffix('.exit.json'):read(p) for p in OUT.glob('*.exit.json')}
    order = ('check_01','saved_02','terminal_03','reserve_04')
    assert len(records) <= 4 and set(records) == set(order[:len(records)])
    expected_fixed = pin(raw({**baseline['sources'],**baseline['preserved'],**baseline['helpers'],**baseline['fixed_documents']}))
    total = 0.
    for label, record in records.items():
        assert record['label'] == label and record['returncode'] == 0 and record['accepted'] and record['error'] is None
        assert record['fixed_before'] == record['fixed_after'] == expected_fixed
        assert record['baseline_pin'] == pin((OUT/'baseline.json').read_bytes())
        assert record['navigation_pin'] == pin((OUT/'navigation_migration.json').read_bytes())
        assert record['script_pin'] == baseline['helpers'][(OUT/'saved_checks.py').relative_to(ROOT).as_posix()]
        assert record['capture_pin'] == baseline['helpers'][(OUT/'capture.py').relative_to(ROOT).as_posix()]
        assert record['package_postcheck_verified'] is True
        assert record['stdout_pin'] == pin((OUT/(label+'.stdout.log')).read_bytes())
        assert record['stderr_pin'] == pin(b'') == pin((OUT/(label+'.stderr.log')).read_bytes())
        assert record['tail_reserve_seconds'] == .5
        assert record['charged_seconds'] == record['observed_capture_seconds']+.5 <= 30
        assert record['target_timeout_seconds'] <= 25 and record['target_seconds'] <= record['target_timeout_seconds']
        assert set(record['prior_records']) == set(order[:order.index(label)])
        assert record['previous_charged_seconds'] == sum(records[k]['charged_seconds'] for k in record['prior_records'])
        for k, expected in record['prior_records'].items(): assert pin((OUT/(k+'.exit.json')).read_bytes()) == expected
        if label != 'check_01': assert record['support_pin'] == pin(support_path.read_bytes())
        total += record['charged_seconds']
    assert total <= 120
    prior = verify_previous_upstream(require_current_sources=require_current_sources)
    assert prior['successful_completed_capture_records'] == 4 and prior['failed_historical_capture_records'] == 2
    # Check local references in this round's own documents and inserted navigation prefixes.
    link_count = 0
    link_documents = [(ROOT/n,(ROOT/n).read_text(encoding='utf-8')) for n in baseline['current_documents']]
    link_documents += [(ROOT/n,base64.b64decode(item['prefix_base64']).decode('utf-8')) for n,item in nav.items()]
    for path,text in link_documents:
        for target in re.findall(r'\]\(([^)]+)\)', text):
            if '://' in target or target.startswith('#'): continue
            assert (path.parent/target.split('#')[0]).resolve().exists(), (path,target)
            link_count += 1
    files = [p for p in OUT.rglob('*') if p.is_file()]
    assert len(files) <= 24 and sum(p.stat().st_size for p in files) <= 4*1024**2
    return dict(authority='DRAFT_NONAUTHORITATIVE',scope='independent_static_archive_successor',
        successor_archive_oracle_body_verified=bool(require_support),support_pins_verified=bool(require_support),
        full_ancestor_archive_verified=True,historical_failure_records=2,
        historical_success_records=4, historical_charged_seconds=prior['completed_charged_static_seconds'],
        historical_failures_relabelled=False, source_epoch=prior['source_epoch'],
        frozen_epoch_test_nodes=282,current_epoch_test_nodes=282 if current_sources else 0,
        reused_ordinary_cold_process_probes=8,P1_unchanged_files=683,preserved_paths=len(baseline['preserved']),
        current_design_negative_cases=21,exact_data_schemas=10,expanded_nodes=59,runtime_faults_unrun=26,
        current_sources_match=current_sources,current_navigation_match=bool(current_navigation),
        completed_capture_records=len(records),completed_charged_static_seconds=total,
        current_capture_excluded_until_external_exit=True,checked_links=link_count,
        new_pytest_nodes=0,new_cold_probes=0,new_simulated_hours=0,scientific_ENTRY_imported=False,
        whole_workflow_wall_budget_verified=False,actual_F=False,scientific_evidence_adopted=False,resource_admission=False,formal_result=False)

if __name__ == '__main__':
    assert sys.argv[1:] in ([],['--draft'])
    sys.addaudithook(guard)
    print(json.dumps(verify(require_current_sources=True,require_current_navigation=True,require_support=not sys.argv[1:]),sort_keys=True))
