"""One conditional saved Rref inspection and read-footprint discovery; no lease authority."""
from contextlib import ExitStack
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from time import perf_counter
import traceback
from types import ModuleType

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
ENTRY = HERE.parent / 'validation_path_optimization_01/entry_revision_07'
pin, = sys.argv[1:]
raw_plan = (HERE / 'parent_inspection_footprint_plan_03.json').read_bytes()
if sha256(raw_plan).hexdigest() != pin:
    raise ValueError('fixed Parent read-footprint plan differs')
plan = json.loads(raw_plan)
OUT = Path(plan['inner_output'])
OUT.mkdir(exist_ok=False)
sys.pycache_prefix = str(OUT / 'empty_pycache')
Path(sys.pycache_prefix).mkdir()
sources = plan['source_sha256']
result = dict(exit_code=1, formal_result=False, resource_admission=False,
    full_hour0_chain_passed=False, native_execution_authorized=False,
    live_Parent_credential_issued=False, numerical_proof_reuse_admitted=False)
start = perf_counter()


def save(name, value):
    with (OUT / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)


def load(name, path):
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != sources[str(path)]:
        raise ValueError('declared diagnostic source differs')
    module = ModuleType(name)
    module.__file__, module.__package__ = str(path), name.rpartition('.')[0]
    sys.modules[name] = module
    exec(compile(raw, str(path), 'exec'), vars(module))
    return module


try:
    if not sys.flags.isolated or not sys.dont_write_bytecode:
        raise ValueError('isolated -I -B entry required')
    for path, expected_pin in {**sources, **plan['old_chain_sha256']}.items():
        if sha256(Path(path).read_bytes()).hexdigest() != expected_pin:
            raise ValueError('fixed source/old-chain bytes differ')
    save('request.json', plan)
    package = ModuleType('performance')
    package.__path__ = [str(ENTRY)]
    sys.modules['performance'] = package
    load('performance.code_read_lease', ENTRY / 'code_read_lease.py')
    metadata = load('performance.metadata_parse_lease', ENTRY / 'metadata_parse_lease.py')
    policy = load('performance.interpreter_path_policy', ENTRY / 'interpreter_path_policy.py').InterpreterPathPolicy(
        json.loads((ENTRY / 'interpreter_path_policy_v1.json').read_bytes()))
    policy.configure()
    vendor = load('performance.vendor_code_policy', ENTRY / 'vendor_code_policy.py')
    vendor.assert_unloaded(sys.modules)
    bounded = load('performance.bounded_stable_read_entry', HERE / 'bounded_stable_read_entry_v2.py')
    expected = {Path(path): value for path, value in plan['code_lease_sha256'].items()}
    metadata_expected = {Path(path): value for path, value in json.loads(
        (ENTRY / 'metadata_allowlist_v1.json').read_bytes())['files_sha256'].items()}
    saved = Path(plan['saved_root'])
    def saved_inventory():
        result = {}
        for name in plan['saved_inventory_roots']:
            root = Path(name)
            for path in (root.rglob('*') if root.is_dir() else (root,)):
                if path.is_file() and path.suffix != '.lock':result[str(path)] = sha256(path.read_bytes()).hexdigest()
        return result
    saved_before = saved_inventory()
    assert saved_before == plan['saved_sha256']
    with ExitStack() as stack:
        lease = stack.enter_context(bounded.BoundedStableReadLease(expected, root=Path('D:/')))
        paths = load('experiments.h1_canonical_path_lease_development_v1', ENTRY / 'canonical_path_lease.py')
        from src.rq2_joint_deliverability_boundary_v1 import episode_store
        original_path = episode_store._path
        path_lease = stack.enter_context(paths.CanonicalPathLease(episode_store, [Path(name) for name in plan['path_roots']]))
        fixture = load('parent_footprint_saved_fixture', HERE.parent / 'replay_saved_with_fixture_v1.py')
        from experiments import h1_selector_worker_output_inspection_development_v2 as inspection
        base = Path(plan['fixture_base'])
        parent_root = base / 'parent_non_authoritative'
        worker_root = parent_root / 'worker_non_authoritative'
        binding = json.loads((parent_root / 'binding.json').read_bytes())
        launch = json.loads((worker_root / 'launch.json').read_bytes())
        terminal = json.loads((parent_root / 'terminal.json').read_bytes())
        observation = terminal['lifecycle']['observation']
        assert observation['exit_code'] == 0 and observation['whole_job_quiescent'] is True
        def saved_pin(name):
            cap = inspection.snapshot.CAP if name == 'selector_snapshot.json' else inspection.worker.CAP
            raw, _ = inspection.worker._read(worker_root / name, cap)
            return inspection.io.digest(raw)
        retained_data = terminal['lifecycle']['inspection']['data']
        snapshot_raw = inspection.worker._read(worker_root / 'selector_snapshot.json', inspection.snapshot.CAP)[0]
        assert json.loads(snapshot_raw)['implementation'] == inspection.snapshot.implementation_identity()
        pins = {name: saved_pin(name) for name in inspection.INPUT_FILES}
        assert all(pins[name] == retained_data['pins'][name] for name in pins)
        outputs = {name: retained_data['pins'][name] for name in inspection.OUTPUT_FILES}
        assert all(saved_pin(name) == outputs[name] for name in outputs)
        assert launch['process_identity'] == terminal['lifecycle']['process_identity'] == retained_data['process_identity']
        assert (terminal['lifecycle']['pid'], terminal['lifecycle']['creation_filetime']) == (
            retained_data['pid'], retained_data['creation_filetime'])
        prior = deepcopy(terminal['lifecycle']['inspection'])
        prior['data']['output_pins_externally_supplied'] = True
        audit_state = dict(active=False, opened={}, ignored_file_descriptors=0)
        def audit(event, arguments):
            if event != 'open' or not audit_state['active']:
                return
            path, mode, flags = arguments
            if isinstance(path, int):
                audit_state['ignored_file_descriptors'] += 1
                return
            name = os.fsdecode(os.fspath(path))
            if len(audit_state['opened']) > 8192:
                raise ValueError('bounded read-footprint path limit exceeded')
            row = audit_state['opened'].setdefault(name, dict(calls=0, modes=set(), flags=set()))
            row['calls'] += 1
            row['modes'].add(mode)
            row['flags'].add(flags)
        # Fresh isolated process only. This discovery hook is never installed in
        # a production entry; it supplies no caching, proof or mutable callback.
        sys.addaudithook(audit)
        patch = fixture.complete_fixture(fixture.saved.synthetic_source)(base)
        try:
            policy.admit('saved_fixture_prepared')
            with metadata.MetadataParseLease(metadata_expected) as parsed:
                begin = perf_counter()
                audit_state['active'] = True
                try:
                    diagnostic = inspection.inspect(worker_root, pins=pins,
                        environment=binding['declaration']['environment'],
                        expected_process_identity=launch['process_identity'],
                        expected_pid=terminal['lifecycle']['pid'],
                        expected_creation_filetime=terminal['lifecycle']['creation_filetime'],
                        expected_output_pins=outputs)
                finally:
                    audit_state['active'] = False
                elapsed = perf_counter() - begin
                assert inspection.io.encode(diagnostic) == inspection.io.encode(prior)
                (OUT / 'conditional_inspection.json').write_bytes(inspection.io.encode(diagnostic))
                code_keys = {os.path.normcase(str(path)) for path in expected}
                metadata_keys = {os.path.normcase(str(path)) for path in metadata_expected}
                rows = []
                for name, row in sorted(audit_state['opened'].items()):
                    path = Path(name).resolve()
                    key = os.path.normcase(str(path))
                    category = ('code_lease' if key in code_keys else 'metadata_lease' if key in metadata_keys
                        else 'saved_inventory' if str(path) in saved_before else 'outside_previous_closures')
                    rows.append(dict(path=str(path), calls=row['calls'], modes=sorted(row['modes'], key=repr),
                        flags=sorted(row['flags']), category=category, exists=path.is_file(),
                        sha256=sha256(path.read_bytes()).hexdigest() if path.is_file() else None))
                save('observed_open_footprint.json', dict(rows=rows,
                    ignored_file_descriptor_events=audit_state['ignored_file_descriptors'],
                    missing_open_events_do_not_prove_no_reads=True,
                    scope='observed Python audit open events; code/metadata leases observed separately',
                    complete_dependency_closure_proven=False))
                save('metadata_receipt.json', parsed.receipt())
                save('bounded_read_receipt.json', lease.receipt())
                save('path_receipt.json', path_lease.receipt())
        finally:
            patch.undo()
    closed = lease.closed_receipt()
    assert closed['code_owner_closed'] and closed['path_open_restored'] and closed['path_read_bytes_restored']
    assert closed['remaining_code_handles'] == closed['remaining_streams'] == closed['remaining_proxies'] == 0
    assert not closed['cleanup_errors'] and closed['first_failure'] is None
    assert episode_store._path is original_path and path_lease._state == 'closed'
    assert len(path_lease._directories) == len(path_lease._paths) == 0
    save('bounded_closed_receipt.json', closed)
    for path in expected:
        with path.open('r+b'):
            pass
    assert saved_before == saved_inventory()
    policy.admit('closed')
    save('interpreter_receipt.json', policy.receipt())
    result.update(exit_code=0, conditional_inspection_seconds=elapsed,
        conditional_inspection_bytes_equal_saved=True,
        observed_open_calls=sum(row['calls'] for row in rows), observed_open_paths=len(rows),
        outside_previous_closures=[row['path'] for row in rows if row['category'] == 'outside_previous_closures'],
        complete_dependency_closure_proven=False, saved_files_unchanged=len(saved_before),
        code_paths_reopened_for_write_without_writing=len(expected),
        vendor_module_origins=vendor.origins(sys.modules, required=True), synthetic_jobs=0, real_native_calls=0)
except BaseException:
    result.update(error=traceback.format_exc())
finally:
    for label, declared in (('source', sources), ('old_chain', plan['old_chain_sha256'])):
        drift = [path for path, expected_pin in declared.items()
            if not Path(path).is_file() or sha256(Path(path).read_bytes()).hexdigest() != expected_pin]
        result[label + '_unchanged'] = not drift
        result[label + '_drift'] = drift
        if drift:
            result['exit_code'] = 1
    result['elapsed_seconds'] = perf_counter() - start
    save('terminal.json', result)
    print(json.dumps(result), flush=True)
sys.exit(result['exit_code'])
