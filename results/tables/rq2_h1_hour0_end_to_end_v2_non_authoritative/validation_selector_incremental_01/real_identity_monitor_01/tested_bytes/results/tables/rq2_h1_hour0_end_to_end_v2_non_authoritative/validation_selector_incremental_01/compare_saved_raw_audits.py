"""One bounded saved-capture comparison; real identity discovery, zero solvers."""
from contextlib import ExitStack
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import perf_counter
import traceback
from types import ModuleType

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PRIOR = HERE.parent / 'validation_io_optimization_01'
label, supplied = sys.argv[1:]
if not label.replace('_', '').isalnum():
    raise ValueError('explicit unique label required')
out = HERE / label
out.mkdir(exist_ok=False)
base = Path(supplied)
if not base.is_absolute() or base != base.resolve(strict=True):
    raise ValueError('canonical saved-capture root required')
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


def load(name, path, expected):
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != expected:
        raise ValueError('fixed package member changed')
    module = ModuleType(name)
    module.__file__, module.__package__ = str(path), name.rpartition('.')[0]
    sys.modules[name] = module
    exec(compile(raw, str(path), 'exec'), vars(module))
    return module


start = perf_counter()
source_pins = saved_pins = {}
measurements = []
result = dict(formal_result=False, full_chain_passed=False, resource_admission=False,
    formal_execution_ready=False, native_execution_authorized=False, real_native_calls=0)
try:
    manifest = (PRIOR / 'package_manifest_v1.json').read_bytes()
    if sha256(manifest).hexdigest() != '0cd4511072ee11cc89a942b3eb76a3a91de4390ca1af5febe0981c216976a59a':
        raise ValueError('fixed predecessor package differs')
    members = json.loads(manifest)['files_sha256']
    if pin(PRIOR / p for p in members) != {str(PRIOR / p): h for p, h in members.items()}:
        raise ValueError('fixed predecessor members differ')
    expected = {Path(p): h for p, h in json.loads((PRIOR / 'code_allowlist_v3.json').read_bytes())['files_sha256'].items()}
    tests = {REPO / p: h for p, h in json.loads((PRIOR / 'test_closure_v1.json').read_bytes())['files_sha256'].items()}
    additions = [REPO / 'experiments/h1_origin_selector_incremental_replay_development_v1.py',
        REPO / 'experiments/h1_selector_raw_science_development_v2.py', Path(__file__).resolve()]
    expected.update({p: sha256(p.read_bytes()).hexdigest() for p in additions})
    source_pins = {str(p): h for p, h in {**expected, **tests}.items()}
    source_pins.update({str(PRIOR / p): h for p, h in members.items()})
    source_pins[str(PRIOR / 'package_manifest_v1.json')] = sha256(manifest).hexdigest()
    if pin(map(Path, source_pins)) != source_pins:
        raise ValueError('source/test closure differs before import')
    saved_pins = pin(p for p in base.rglob('*') if p.is_file())
    save('request.json', dict(scope='Rref and Actual final saved raw capsule audits only',
        source_sha256=source_pins, saved_sha256=saved_pins,
        static_identity_shortcut=False, metadata_discovery_fresh=True,
        fixed_byte_and_metadata_parse_package_sha256=sha256(manifest).hexdigest(),
        route_identity=sha256(Path(__file__).read_bytes()).hexdigest(),
        formal_result=False, resource_admission=False, real_native_calls=0))
    package = ModuleType('performance')
    package.__path__ = [str(PRIOR)]
    sys.modules['performance'] = package
    code = load('performance.code_read_lease', PRIOR / 'code_read_lease.py', members['code_read_lease.py'])
    parsed = load('performance.metadata_parse_lease', PRIOR / 'metadata_parse_lease.py', members['metadata_parse_lease.py'])
    metadata = json.loads((PRIOR / 'metadata_allowlist_v1.json').read_bytes())['files_sha256']
    with ExitStack() as stack:
        code_lease = stack.enter_context(code.CodeReadLease(expected, root=REPO))
        from experiments import h1_selector_raw_science_development_v1 as old
        from experiments import h1_selector_raw_science_development_v2 as new
        from tests import test_h1_selector_raw_science_development_v1 as producer
        for module, name in ((old.selector.physical, 'implementation_identity'),
                (old.selector, 'implementation_identity'), (old.selector.native, '_identity')):
            if Path(getattr(module, name).__code__.co_filename).resolve() != Path(module.__file__).resolve():
                raise ValueError('test identity shortcut leaked into real comparison')
        parse_lease = stack.enter_context(parsed.MetadataParseLease(metadata))
        for lane, final in ((producer.fixtures.R, 2), (producer.fixtures.A, 1)):
            f, d, b, args = producer.inputs(lane)
            records = tuple((base / (lane.role + str(i) + '_incremental') / 'selector_record.json').read_bytes()
                for i in range(final))
            for mode, bridge in (('legacy', old), ('incremental', new)):
                path = base / (lane.role + str(final) + '_' + mode)
                terminal = json.loads((path / 'terminal.json').read_bytes())
                observations = json.loads((path / 'observations.json').read_bytes())['observations']
                raw = (path / 'capture/native_raw/000/raw.bin').read_bytes()
                post = (path / 'postsolve.json').read_bytes()
                begin = perf_counter()
                with bridge.science.prior.guard.solver_calls_forbidden():
                    produced = bridge._audit_stage(raw, post, f, d, b, records, **args,
                        expected_key=terminal['request_key'], expected_binding=terminal['binding_sha256'],
                        expected_export=terminal['export_sha256'], observations=observations)
                elapsed = perf_counter() - begin
                if produced['selector_record'] != (path / 'selector_record.json').read_bytes():
                    raise ValueError('saved selector record differs')
                projection = {k: v for k, v in produced.items() if k not in (
                    'selector_record', 'native_sha256', 'postsolve_sha256')}
                projection['selector_record_sha256'] = sha256(produced['selector_record']).hexdigest()
                measured = dict(lane=lane.role, mode=mode, audit_seconds=elapsed,
                    projection=projection, bridge_implementation_identity=bridge.implementation_identity())
                save(lane.role + '_' + mode + '.json', measured)
                measurements.append(measured)
                print(json.dumps(dict(lane=lane.role, mode=mode, audit_seconds=elapsed)), flush=True)
            if measurements[-2]['projection'] != measurements[-1]['projection']:
                raise ValueError('legacy/incremental scientific projection differs')
        result.update(measurements=measurements, code_read_hits=code_lease.hits,
            metadata_parse_hits=parse_lease.hits, static_identity_shortcut=False,
            metadata_discovery_fresh=True, both_lane_projections_equal=True)
    if pin(p for p in base.rglob('*') if p.is_file()) != saved_pins:
        raise ValueError('saved capture files changed')
    result.update(exit_code=0, saved_unchanged=True, saved_files=len(saved_pins))
except BaseException:
    result.update(exit_code=1, error=traceback.format_exc(), measurements=measurements)
finally:
    drift = [p for p, h in source_pins.items() if not Path(p).is_file() or sha256(Path(p).read_bytes()).hexdigest() != h]
    if drift:
        result.update(exit_code=1, source_drift=drift)
    result.update(elapsed_seconds=perf_counter() - start, source_unchanged=not drift)
    save('terminal.json', result)
    print(json.dumps({k: v for k, v in result.items() if k not in ('measurements',)}), flush=True)
sys.exit(result['exit_code'])
