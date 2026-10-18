"""One original saved common arm through the new bounded entry; no producer."""
from contextlib import ExitStack
from hashlib import sha256
import json
from pathlib import Path
import sys
import traceback
from types import ModuleType
from time import perf_counter

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
ENTRY = HERE.parent / 'validation_path_optimization_01/entry_revision_07'
plan_pin, = sys.argv[1:]
raw_plan = (HERE / 'bounded_common_arm_plan_02.json').read_bytes()
if sha256(raw_plan).hexdigest() != plan_pin:
    raise ValueError('fixed hotpath diagnostic plan differs')
plan = json.loads(raw_plan)
OUT = Path(plan['inner_output'])
OUT.mkdir(exist_ok=False)
sys.pycache_prefix = str(OUT / 'empty_pycache')
Path(sys.pycache_prefix).mkdir()
sources = plan['source_sha256']
start = perf_counter()
result = dict(exit_code=1, formal_result=False, resource_admission=False,
    full_hour0_chain_passed=False, native_execution_authorized=False)


def save(name, value):
    with (OUT / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)


def load(name, path):
    value = path.read_bytes()
    if sha256(value).hexdigest() != sources[str(path)]:
        raise ValueError('fixed entry member differs')
    module = ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = name.rpartition('.')[0]
    sys.modules[name] = module
    exec(compile(value, str(path), 'exec'), vars(module))
    return module


try:
    if not sys.flags.isolated or not sys.dont_write_bytecode:
        raise ValueError('fixed -I -B required')
    for path, pin in {**sources, **plan['old_chain_sha256']}.items():
        if sha256(Path(path).read_bytes()).hexdigest() != pin:
            raise ValueError('fixed diagnostic source differs')
    save('request.json', plan)
    package = ModuleType('performance')
    package.__path__ = [str(ENTRY)]
    sys.modules['performance'] = package
    code = load('performance.code_read_lease', ENTRY / 'code_read_lease.py')
    metadata = load('performance.metadata_parse_lease', ENTRY / 'metadata_parse_lease.py')
    policy = load('performance.interpreter_path_policy', ENTRY / 'interpreter_path_policy.py').InterpreterPathPolicy(
        json.loads((ENTRY / 'interpreter_path_policy_v1.json').read_bytes()))
    policy.configure()
    vendor = load('performance.vendor_code_policy', ENTRY / 'vendor_code_policy.py')
    vendor.assert_unloaded(sys.modules)
    bounded = load('performance.bounded_stable_read_entry', HERE / 'bounded_stable_read_entry_v2.py')
    expected = {Path(k): v for k, v in plan['code_lease_sha256'].items()}
    metadata_expected = {Path(k): v for k, v in json.loads(
        (ENTRY / 'metadata_allowlist_v1.json').read_bytes())['files_sha256'].items()}
    saved = Path(plan['saved_root'])
    saved_before = {str(p): sha256(p.read_bytes()).hexdigest() for p in saved.rglob('*') if p.is_file()}
    assert saved_before == plan['saved_sha256']
    with ExitStack() as stack:
        lease = stack.enter_context(bounded.BoundedStableReadLease(expected, root=Path('D:/')))
        fixture = load('bounded_common_arm_fixture', HERE.parent / 'replay_saved_with_fixture_v1.py')
        from experiments import h1_selector_input_snapshot_development_v2 as snapshot
        common = snapshot.common.common
        header = json.loads(next(saved.glob('nt_non_authoritative/common_owners_non_authoritative/*/header.json')).read_bytes())['declaration']
        base = saved / 'test_complete_independent_N0_r0'
        packet = json.loads((base / 'parent_non_authoritative/worker_non_authoritative/selector_snapshot.json').read_bytes())
        d = packet['declaration']
        manifest, binding, configuration = snapshot._declarations(d['manifest'], d['source_binding'], d['run_configuration'])
        report = header['initial_report']
        arm = report['canonical_arm']
        assert arm == 'network-only'
        patch = fixture.complete_fixture(fixture.saved.synthetic_source)(base)
        try:
            policy.admit('saved_fixture_prepared')
            with metadata.MetadataParseLease(metadata_expected) as parsed:
                previous = perf_counter()
                produced = common._arm(report['arm_audits'][arm]['reference'], binding.registry_identity, manifest)
                elapsed = perf_counter() - previous
                assert common.encode(produced[1]) == common.encode(report['common_scientific_payload'])
                audit = json.loads(common.encode(produced[2]))
                prior = json.loads(common.encode(report['arm_audits'][arm]))
                audit.pop('verification_execution', None)
                audit['exact_current_audit'].pop('implementation_identity')
                prior['exact_current_audit'].pop('implementation_identity')
                assert common.encode(audit) == common.encode(prior)
                for name, value in (('scientific.json', produced[1]), ('audit.json', produced[2])):
                    save(name, value)
                    assert (OUT / name).read_bytes() == (ENTRY / 'vendor_saved_arm_01' / name).read_bytes()
                save('bounded_read_receipt.json', lease.receipt())
                metadata_receipt = parsed.receipt()
                assert metadata_receipt['hits'] > 0 and metadata_receipt['misses'] == 0
                save('metadata_receipt.json', metadata_receipt)
        finally:
            patch.undo()
    closed = lease.closed_receipt()
    assert closed['code_owner_closed'] and closed['path_open_restored'] and closed['path_read_bytes_restored']
    assert closed['remaining_code_handles'] == closed['remaining_streams'] == closed['remaining_proxies'] == 0
    assert not closed['cleanup_errors'] and closed['first_failure'] is None
    save('bounded_closed_receipt.json', closed)
    for code_path in expected:
        with code_path.open('r+b'):
            pass
    assert saved_before == {str(p): sha256(p.read_bytes()).hexdigest() for p in saved.rglob('*') if p.is_file()}
    policy.admit('closed')
    save('interpreter_receipt.json', policy.receipt())
    result.update(exit_code=0, arm_seconds=elapsed,
        science_and_full_audit_exact_equal_prior_entry=True, science_and_projected_audit_equal_original_saved=True,
        saved_files_unchanged=len(saved_before), code_paths_reopened_for_write_without_writing=len(expected),
        vendor_module_origins=vendor.origins(sys.modules, required=True), synthetic_jobs=0, real_native_calls=0)
except BaseException:
    result.update(error=traceback.format_exc())
finally:
    for name, pins in (('source', sources), ('old_chain', plan['old_chain_sha256'])):
        drift = [p for p, h in pins.items() if not Path(p).is_file() or sha256(Path(p).read_bytes()).hexdigest() != h]
        result[name + '_unchanged'] = not drift
        result[name + '_drift'] = drift
        if drift:
            result['exit_code'] = 1
    result['elapsed_seconds'] = perf_counter() - start
    save('terminal.json', result)
    print(json.dumps(result), flush=True)
sys.exit(result['exit_code'])
