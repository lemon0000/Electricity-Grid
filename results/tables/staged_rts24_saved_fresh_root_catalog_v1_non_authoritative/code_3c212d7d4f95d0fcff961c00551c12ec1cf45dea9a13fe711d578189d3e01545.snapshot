"""Bounded static catalog checks; no project imports, solver, Job, or saved role."""
import base64
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).absolute().parents[3]
OUT = Path(__file__).absolute().parent
EXE = 'D:/Miniconda3/envs/compute/python.exe'
TOOL = ROOT/'experiments/staged_rts24_saved_fresh_root_catalog_v1.py'
TEST = ROOT/'tests/test_staged_rts24_saved_fresh_root_catalog_v1.py'
OLD = ROOT/'results/tables/staged_rts24_saved_fresh_machinery_transition_v1_non_authoritative/checks_01'
ARCHIVE = ROOT/'results/tables/staged_rts24_saved_fresh_machinery_transition_archive_v1_non_authoritative'
SCOPE = ROOT/'docs/plan/staged_deliverability_c_saved_fresh_root_catalog_scope_v1.md'


def canonical(value): return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')
def pin(raw): return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
def read(path): return json.loads(path.read_bytes())
def save(path, value):
    with path.open('xb') as stream: stream.write(canonical(value))
def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module
def pins(paths): return {str(p): pin(p.read_bytes()) for p in paths}
def usage():
    files = [p for p in OUT.rglob('*') if p.is_file()]
    return dict(files=len(files), bytes=sum(p.stat().st_size for p in files))
def check_inputs(reg):
    for path, expected in reg['input_pins'].items():
        assert pin(Path(path).read_bytes()) == expected, path


def prerequisites(label, reg):
    expected = dict(unittest=[], catalog=['unittest'], saved=['unittest','catalog'])[label]
    assert sorted(p.name for p in OUT.glob('*.exit.json')) == sorted(n+'.exit.json' for n in expected)
    images = {}
    for name in expected:
        path = OUT/(name+'.exit.json'); record = read(path)
        assert record['accepted'] is True and record['label'] == name
        assert record['kind'] == ('unittest' if name == 'unittest' else 'static')
        assert record['registration_pin'] == pin((OUT/'registration.json').read_bytes())
        assert record['helper_pins'] == reg['helper_pins'] and record['source_epoch'] == reg['source_epoch']
        report_path = OUT/(name+'_report.json')
        assert record['report_pin'] == pin(report_path.read_bytes()) and read(report_path)['accepted'] is True
        images.update(pins([path, report_path]))
    return images


def _register():
    started = time.perf_counter()
    assert not (OUT/'registration.json').exists()
    admission = read(OLD/'admission_repair.json')
    profile = read(OLD/'import_policy.json')
    sources = [ROOT/n for n in admission['source_pins']]
    prior = [p for root in (OLD.parent, ARCHIVE) for p in root.rglob('*') if p.is_file()]
    assert len(prior) == 53
    extra = [Path('D:/Miniconda3/envs/compute/Lib/site-packages/distutils-precedence.pth'),
        Path('D:/Miniconda3/envs/compute/Lib/site-packages/_distutils_hack/__init__.py')]
    input_paths = set(sources + prior + extra + [TOOL, TEST, Path(__file__).absolute(), SCOPE, Path(EXE),
        ROOT/'results/tables/staged_rts24_saved_fresh_runtime_binding_v1_non_authoritative/checks_01/root_contracts_v2.json',
        ROOT/'results/tables/staged_rts24_saved_fresh_runtime_binding_v1_non_authoritative/checks_01/capability_edges_v3.json',
        *[Path(n) for n in profile['external_sources']]])
    input_pins = pins(sorted(input_paths))
    # The two-stage bounded drain itself has a pinned, immutable predecessor chain.
    capture = OLD/'capture.py'
    assert input_pins[str(capture)] == dict(bytes=12148, sha256='fe55cb029a7daf842f20673f3dd8a75a38efb906a5e8f0b9e20a3a3971f3858c')
    helper_pins = pins([TOOL, TEST, Path(__file__).absolute()])
    for path in helper_pins:
        raw = Path(path).read_bytes()
        with (OUT/('code_' + pin(raw)['sha256'] + '.snapshot')).open('xb') as stream: stream.write(raw)
    prior_exit = read(ARCHIVE/'terminal_repair.exit.json')
    startup = dict(status='observed_only', expected_truth_external=False, full_startup_inventory_verified=False,
        files=pins(extra), environment_condition='SETUPTOOLS_USE_DISTUTILS defaults to local in the observed .pth route',
        open=['system site/sitecustomize and all pre-main modules not authenticated',
            'observed bytes are not independent external launch expected truth'])
    save(OUT/'startup_observations.json', startup)
    test_class = next(n for n in ast.parse(TEST.read_bytes()).body if isinstance(n, ast.ClassDef) and n.name == 'StaticCatalogTests')
    unit_nodes = sorted('catalog_tests.StaticCatalogTests.'+n.name for n in test_class.body if isinstance(n, ast.FunctionDef) and n.name.startswith('test_'))
    charged = time.perf_counter() - started
    reg = dict(authority='DRAFT_NONAUTHORITATIVE', source_epoch=admission['source_epoch'], unit_nodes=unit_nodes,
        input_pins=input_pins, helper_pins=helper_pins, prior_files=len(prior),
        predecessor_charged_seconds=prior_exit['all_cumulative_charged_seconds'],
        caps=dict(static=30, unittest=20, total=50, files=32, bytes=8*1024**2),
        phase_caps=dict(unittest=8, unittest_repair=12, catalog=12, saved=8),
        registration_charged_seconds=charged, registration_cap_seconds=2,
        actual_F=False, formal_result=False, resource_admission=False, run_authority=False,
        production_seal=False, expected_truth_external=False)
    reg['accepted'] = charged <= 2
    save(OUT/'registration.json', reg)
    print(canonical(dict(registered=True, charged_seconds=charged)).decode())
    if not reg['accepted']: raise SystemExit(1)


def register():
    started = time.perf_counter()
    assert not (OUT/'registration.json').exists() and not (OUT/'registration_failure.json').exists()
    try:
        _register()
    except BaseException as error:
        if not (OUT/'registration.json').exists():
            save(OUT/'registration_failure.json', dict(accepted=False, kind='static', phase='registration',
                charged_seconds=time.perf_counter()-started, cap_seconds=2, error=type(error).__name__,
                driver_pin=pin(Path(__file__).read_bytes()), prior_usage=usage(),
                predecessor_cumulative_verified=False, process_observation=None,
                actual_F=False, formal_result=False, resource_admission=False, run_authority=False, production_seal=False))
        raise


def child(action):
    reg = read(OUT/'registration.json'); check_inputs(reg)
    predecessor_pins = prerequisites(action, reg)
    if action in ('unittest', 'unittest_repair'):
        import unittest
        module = load(TEST, 'catalog_tests')
        suite = unittest.defaultTestLoader.loadTestsFromModule(module)
        def names(item):
            if isinstance(item, unittest.TestSuite): return [n for sub in item for n in names(sub)]
            return [item.id()]
        nodes = sorted(names(suite)); assert len(nodes) == len(set(nodes)) and nodes == reg['unit_nodes']
        admission = dict(nodes=nodes, helper_pins=reg['helper_pins'], source_epoch=reg['source_epoch'], before_test_calls=True)
        save(OUT/(action+'_admission.json'), admission)
        before = pin((OUT/(action+'_admission.json')).read_bytes())
        result = unittest.TextTestRunner(verbosity=1).run(suite)
        check_inputs(reg); assert pin((OUT/(action+'_admission.json')).read_bytes()) == before
        report = dict(accepted=result.wasSuccessful() and result.testsRun == len(nodes) and not result.skipped,
            nodes=nodes, tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
            skipped=len(result.skipped), admission_pin=before, helper_pins=reg['helper_pins'])
        save(OUT/(action+'_report.json'), report)
        if not report['accepted']: raise AssertionError('unit failure preserved')
    else:
        tool = load(TOOL, 'catalog_tool')
        result = tool.build_catalog(ROOT); raw = canonical(result)
        assert all(result[k] is False for k in tool.FALSE_GATES)
        if action == 'catalog':
            with (OUT/'catalog.json').open('xb') as stream: stream.write(raw)
            graph = result['reference_graph']
            report = dict(accepted=True, catalog_pin=pin(raw), current_roots=len(result['current_roots']),
                legacy_roots=len(result['legacy33_disposition']), symbols=len(graph['nodes']), edges=len(graph['edges']),
                recursive_components=len(graph['recursive_components']), evidence_templates=len(result['required_evidence_dag']['nodes']))
        else:
            assert action == 'saved'
            assert raw == (OUT/'catalog.json').read_bytes()
            report = dict(accepted=True, canonical_reopen_equal=True, catalog_pin=pin(raw),
                catalog_exit_pin=pin((OUT/'catalog.exit.json').read_bytes()),
                unit_exit_pin=pin((OUT/'unittest.exit.json').read_bytes()), all_capabilities_verified=False)
        check_inputs(reg); save(OUT/(action+'_report.json'), report)
    assert prerequisites(action, reg) == predecessor_pins
    print(canonical(dict(accepted=True, action=action)).decode())


def _action(label):
    started = time.perf_counter(); reg = read(OUT/'registration.json')
    target = OUT/(label+'.exit.json'); assert not target.exists() and reg['accepted'] is True
    cap = reg['phase_caps'][label]; kind = 'unittest' if label.startswith('unittest') else 'static'
    prior = [read(p) for p in OUT.glob('*.exit.json')]
    spent = {k: sum(r['charged_seconds'] for r in prior if r['kind'] == k) for k in ('static', 'unittest')}
    spent['static'] += reg['registration_charged_seconds']
    assert spent[kind]+cap <= reg['caps'][kind] and sum(spent.values())+cap <= 50
    if label == 'unittest_repair': raise ValueError('repair requires explicit pinned revision; no automatic retry')
    check_inputs(reg)
    predecessor_pins = prerequisites(label, reg)
    reserve_bytes = 4*1024**2+131072 if label == 'catalog' else 131072
    assert usage()['files']+4 <= 32 and usage()['bytes']+reserve_bytes <= 8*1024**2
    before_reg = pin((OUT/'registration.json').read_bytes())
    capture = load(OLD/'capture.py', 'fixed_catalog_capture')
    timeout = cap - (time.perf_counter()-started) - 0.7
    code, stdout, stderr, error, observation = capture.bounded([EXE, '-B', '-s', str(Path(__file__).absolute()), 'child', label], timeout)
    accepted = False
    try:
        check_inputs(reg); assert pin((OUT/'registration.json').read_bytes()) == before_reg
        assert prerequisites(label, reg) == predecessor_pins
        drain = observation['bounded_drain']
        assert code == 0 and error is None and not observation['cleanup'] and observation['handle_closed']
        assert drain['reader_threads_terminal'] and drain['pipes_closed'] and not drain['reader_errors'] and not drain['cleanup']
        assert not drain['stdout_truncated'] and not drain['stderr_truncated'] and not drain['killed']
        assert json.loads(stdout) == dict(accepted=True, action=label)
        report = read(OUT/(label+'_report.json')); assert report['accepted'] is True
        if kind == 'unittest': assert report['tests_run'] == len(reg['unit_nodes']) and report['failures'] == report['errors'] == report['skipped'] == 0
        if label == 'saved': assert report['canonical_reopen_equal'] is True
        accepted = True
    except BaseException as caught:
        error = type(caught).__name__ + (':' + str(error) if error else '')
    charged = time.perf_counter() - started
    spent[kind] += charged
    accepted = accepted and charged <= cap and spent[kind] <= reg['caps'][kind] and sum(spent.values()) <= 50
    record = dict(accepted=accepted, kind=kind, label=label, charged_seconds=charged, cap_seconds=cap,
        source_epoch=reg['source_epoch'], predecessor_pins=predecessor_pins,
        charged_seconds_by_kind=spent, all_cumulative_charged_seconds=dict(
            static=reg['predecessor_charged_seconds']['static']+spent['static'],
            pytest=reg['predecessor_charged_seconds']['pytest'], unittest=spent['unittest']),
        returncode=code, error=error, process_observation=observation,
        registration_pin=before_reg, helper_pins=reg['helper_pins'],
        stdout_pin=pin(stdout), stderr_pin=pin(stderr),
        stdout_raw_base64=base64.b64encode(stdout).decode(), stderr_raw_base64=base64.b64encode(stderr).decode(),
        report_pin=pin((OUT/(label+'_report.json')).read_bytes()) if (OUT/(label+'_report.json')).exists() else None,
        charge_scope='parent preparation through postchecks; final exit serialization and editor/review/Git excluded; 0.7s target tail reserved',
        actual_F=False, run_authority=False, formal_result=False, resource_admission=False, production_seal=False)
    record['storage_before_exit'] = usage()
    record['storage_cap_satisfied'] = True
    candidate_bytes = len(canonical(record))+2  # both acceptance booleans can grow by one byte
    storage_ok = record['storage_before_exit']['files']+1 <= 32 and record['storage_before_exit']['bytes']+candidate_bytes <= 8*1024**2
    record['storage_cap_satisfied'] = storage_ok
    record['accepted'] = accepted = accepted and storage_ok
    save(target, record)
    assert usage()['files'] <= 32 and usage()['bytes'] <= 8*1024**2
    print(canonical(dict(accepted=accepted, charged_seconds=charged, kind=kind)).decode())
    if not accepted: raise SystemExit(1)


def action(label):
    started = time.perf_counter(); target = OUT/(label+'.exit.json')
    assert not target.exists(), 'create-only action, no retry'
    try:
        _action(label)
    except BaseException as error:
        if not target.exists():
            reg = read(OUT/'registration.json'); kind = 'unittest' if label.startswith('unittest') else 'static'
            charged = time.perf_counter()-started
            prior = [read(p) for p in OUT.glob('*.exit.json')]
            spent = {k: sum(r['charged_seconds'] for r in prior if r['kind'] == k) for k in ('static','unittest')}
            spent['static'] += reg['registration_charged_seconds']; spent[kind] += charged
            try: held_predecessors = prerequisites(label, reg)
            except BaseException: held_predecessors = None
            save(target, dict(accepted=False, label=label, kind=kind, charged_seconds=charged,
                cap_seconds=reg['phase_caps'][label], charged_seconds_by_kind=spent,
                all_cumulative_charged_seconds=dict(static=reg['predecessor_charged_seconds']['static']+spent['static'],
                    pytest=reg['predecessor_charged_seconds']['pytest'], unittest=spent['unittest']),
                source_epoch=reg['source_epoch'], registration_pin=pin((OUT/'registration.json').read_bytes()),
                helper_pins=reg['helper_pins'], report_pin=None, returncode=None,
                predecessor_pins=held_predecessors, predecessor_pins_verified=held_predecessors is not None,
                stdout_pin=pin(b''), stderr_pin=pin(b''), stdout_raw_base64='', stderr_raw_base64='',
                raw_streams_observed=False, process_terminal_verified=False,
                prelaunch_or_parent_failure=True, error=type(error).__name__, process_observation=None,
                actual_F=False, formal_result=False, resource_admission=False, run_authority=False, production_seal=False))
        raise


if __name__ == '__main__':
    if sys.argv[1:] == ['register']: register()
    elif len(sys.argv) == 3 and sys.argv[1] == 'child': child(sys.argv[2])
    elif len(sys.argv) == 2 and sys.argv[1] in ('unittest', 'catalog', 'saved'): action(sys.argv[1])
    else: raise SystemExit('fixed static checks only')
