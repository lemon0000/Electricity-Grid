"""Bounded comparison member; original replay plus an optional path lease."""
from contextlib import ExitStack
from hashlib import sha256
from importlib.util import spec_from_file_location, module_from_spec
import json
from pathlib import Path
import sys
from time import perf_counter
import traceback
from types import ModuleType


REPO = Path(__file__).resolve().parents[4]
E = REPO / 'results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative'
PRIOR = E / 'validation_io_optimization_01'
HERE = Path(__file__).resolve().parent
mode, label = sys.argv[1:]
if mode not in ('io', 'io_path') or not label.replace('_', '').isalnum():
    raise ValueError('explicit comparison mode and unique label required')
out = HERE / label
out.mkdir(exist_ok=False)
sys.dont_write_bytecode = True
prefix = out / 'empty_pycache'
prefix.mkdir()
sys.pycache_prefix = str(prefix)
sys.path[:0] = [str(REPO), str(REPO / 'tests')]


def save(name, value):
    with (out / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)


def pin(paths):
    return {str(p): sha256(p.read_bytes()).hexdigest() for p in paths}


def source_module(name, path, expected):
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != expected:
        raise ValueError('module byte pin differs: ' + str(path))
    module = ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = name.rpartition('.')[0]
    sys.modules[name] = module
    exec(compile(raw, str(path), 'exec'), vars(module))
    return module


start = perf_counter()
result = dict(mode=mode, formal_result=False, full_chain_passed=False, real_native_calls=0)
pins = {}
try:
    manifest_bytes = (PRIOR / 'package_manifest_v1.json').read_bytes()
    if sha256(manifest_bytes).hexdigest() != '0cd4511072ee11cc89a942b3eb76a3a91de4390ca1af5febe0981c216976a59a':
        raise ValueError('predecessor package pin differs')
    members = json.loads(manifest_bytes)['files_sha256']
    for name, expected in members.items():
        if Path(name).name != name or sha256((PRIOR / name).read_bytes()).hexdigest() != expected:
            raise ValueError('predecessor member differs')
    expected = {Path(p): h for p, h in json.loads((PRIOR / 'code_allowlist_v3.json').read_bytes())['files_sha256'].items()}
    tests = {REPO / p: h for p, h in json.loads((PRIOR / 'test_closure_v1.json').read_bytes())['files_sha256'].items()}
    metadata = json.loads((PRIOR / 'metadata_allowlist_v1.json').read_bytes())['files_sha256']
    path_source = REPO / 'experiments/h1_canonical_path_lease_development_v1.py'
    fixture_source = E / 'replay_saved_with_fixture_v1.py'
    pins = {str(p): h for p, h in {**expected, **tests}.items()}
    pins.update(pin([Path(__file__), path_source, fixture_source, PRIOR / 'package_manifest_v1.json']))
    pins.update({str(PRIOR / p): h for p, h in members.items()})
    if pin(map(Path, pins)) != pins:
        raise ValueError('current source or fixture closure differs')
    for p in (Path(__file__), path_source):
        (out / p.name).write_bytes(p.read_bytes())
    save('request.json', dict(mode=mode, source_sha256=pins,
        pycache_prefix=str(prefix), pycache_prefix_initially_empty=not any(prefix.iterdir()),
        scope='one saved common arm, original science and validation order',
        baseline='existing code and metadata optimization',
        real_native_calls=0, formal_result=False))
    package = ModuleType('performance')
    package.__path__ = [str(PRIOR)]
    sys.modules['performance'] = package
    code = source_module('performance.code_read_lease', PRIOR / 'code_read_lease.py', members['code_read_lease.py'])
    parsed = source_module('performance.metadata_parse_lease', PRIOR / 'metadata_parse_lease.py', members['metadata_parse_lease.py'])
    paths = source_module('experiments.h1_canonical_path_lease_development_v1', path_source, pins[str(path_source)])
    saved = Path('D:/h1_chain_06_non_authoritative')
    before = pin(p for p in saved.rglob('*') if p.is_file())
    with ExitStack() as outer:
        code_lease = outer.enter_context(code.CodeReadLease(expected, root=REPO))
        from src.rq2_joint_deliverability_boundary_v1 import episode_store
        original_path = episode_store._path
        path_lease = outer.enter_context(paths.CanonicalPathLease(episode_store, [saved, REPO])) if mode == 'io_path' else None
        fixture_spec = spec_from_file_location('path_pair_fixture', fixture_source)
        fixture = module_from_spec(fixture_spec)
        fixture_spec.loader.exec_module(fixture)
        from experiments import h1_selector_input_snapshot_development_v2 as snapshot
        common = snapshot.common.common
        header = json.loads(next(saved.glob('nt_non_authoritative/common_owners_non_authoritative/*/header.json')).read_bytes())['declaration']
        base = saved / 'test_complete_independent_N0_r0'
        packet = json.loads((base / 'parent_non_authoritative/worker_non_authoritative/selector_snapshot.json').read_bytes())
        declaration = packet['declaration']
        manifest, binding, config = snapshot._declarations(declaration['manifest'], declaration['source_binding'], declaration['run_configuration'])
        report = header['initial_report']
        arm = report['canonical_arm']
        patch = fixture.complete_fixture(fixture.saved.synthetic_source)(base)
        try:
            with parsed.MetadataParseLease(metadata) as metadata_lease:
                begin = perf_counter()
                produced = common._arm(report['arm_audits'][arm]['reference'], binding.registry_identity, manifest)
                result['arm_seconds'] = perf_counter() - begin
                if common.encode(produced[1]) != common.encode(report['common_scientific_payload']):
                    raise ValueError('scientific payload differs from saved arm')
                audit = json.loads(common.encode(produced[2]))
                prior = json.loads(common.encode(report['arm_audits'][arm]))
                audit.pop('verification_execution', None)
                audit['exact_current_audit'].pop('implementation_identity')
                prior['exact_current_audit'].pop('implementation_identity')
                if common.encode(audit) != common.encode(prior):
                    raise ValueError('predecessor scientific audit differs')
                save('scientific.json', produced[1])
                save('audit.json', produced[2])
                save('metadata_receipt.json', metadata_lease.receipt())
                if path_lease:
                    save('path_receipt.json', path_lease.receipt())
                save('code_receipt.json', code_lease.receipt())
        finally:
            patch.undo()
    if episode_store._path is not original_path:
        raise ValueError('path dispatch not restored')
    if before != pin(p for p in saved.rglob('*') if p.is_file()):
        raise ValueError('saved artifacts changed')
    result.update(exit_code=0, saved_files_unchanged=True, saved_files=len(before),
        path_hook_restored=True, science_and_projected_audit_equal_saved=True)
except BaseException:
    result.update(exit_code=1, error=traceback.format_exc())
finally:
    if pins and pin(map(Path, pins)) != pins:
        result.update(exit_code=1, source_changed=True)
    result['elapsed_seconds'] = perf_counter() - start
    save('terminal.json', result)
    print(json.dumps(result), flush=True)
sys.exit(result['exit_code'])
