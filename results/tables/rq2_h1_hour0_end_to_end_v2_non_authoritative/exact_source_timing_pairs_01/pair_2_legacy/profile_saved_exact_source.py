"""Saved synthetic exact-source comparison; no producer, Job or native call."""
import cProfile
from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path
import pstats
import sys
import time
import traceback

E = Path(__file__).resolve().parent
ROOT = E.parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2)


def main():
    saved, destination = map(Path, sys.argv[1:3])
    mode = sys.argv[3]
    profiling = '--timing-only' not in sys.argv[4:]
    if mode not in ('legacy', 'successor'):
        raise ValueError('explicit comparison mode required')
    destination.mkdir(exist_ok=False)
    spec = importlib.util.spec_from_file_location('saved_exact_source_fixture', E / 'replay_saved_with_fixture_v1.py')
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    from experiments import h1_phase_exact_source_current_development_v1 as legacy
    from experiments import h1_phase_exact_source_current_development_v2 as successor
    from experiments import h1_historical_n0_verifier_development_v1 as verifier
    implementation = legacy if mode == 'legacy' else successor
    before = {str(p): digest(p) for p in sorted(saved.rglob('*')) if p.is_file()}
    roots = sorted(saved.glob('nt_non_authoritative/episodes/*/controller_non_authoritative'))
    assert len(roots) == 3
    root = roots[0]
    source_base = saved / 'test_complete_independent_N0_r0'
    registry = json.loads((source_base / 'synthetic_registry.json').read_bytes())
    args = dict(expected_binding_sha256=digest(root / 'obligation_non_authoritative/binding.json'),
        expected_terminal_sha256=digest(root / 'obligation_non_authoritative/000.terminal.json'),
        completed_hours=1, expected_registry_identity=registry['expected_registry_identity'])
    paths = [Path(__file__), Path(legacy.__file__), Path(successor.__file__), Path(verifier.__file__),
             Path(verifier.witness.__file__), E / 'replay_saved_with_fixture_v1.py',
             ROOT / 'tests/h1_hour0_saved_replay_v2.py']
    code_before = {str(p): digest(p) for p in paths}
    for path in paths:
        (destination / path.name).write_bytes(path.read_bytes())
    save(destination / 'request.json', dict(root=str(root), arguments=args, mode=mode,
        files_sha256=code_before, saved_files_sha256=before, formal_result=False))
    active = False
    def audit(event, values):
        if active and event == 'open':
            path, mode, flags = values
            if isinstance(path, (str, bytes)) and isinstance(mode, str) and any(c in mode for c in 'wax+'):
                raise RuntimeError('saved replay attempted a write')
    sys.addaudithook(audit)
    patch = None
    profiler = cProfile.Profile()
    start = time.perf_counter()
    error = None
    try:
        patch = fixture.complete_fixture(fixture.saved.synthetic_source)(source_base)
        active = True
        if profiling:
            profiler.enable()
        result = implementation.prepare(root, **args)
        profiler.disable()
        active = False
        audit_payload = json.loads(result.source_projection_audit_payload)
        projection = dict(decision=json.loads(result.prepared_current.decision.decision_bytes),
            frame_sha256=implementation.physical._digest(result.prepared_current.frame),
            action_sha256=implementation.physical._digest(result.prepared_current.source_action),
            origin_sha256=implementation.physical._digest(result.prepared_current.source_origin),
            workload_exact=implementation._ratio(result.workload_exact),
            cfe_exact=implementation._ratio(result.source_cfe_at_alpha_one_exact),
            exogenous_scientific_payload=json.loads(result.exogenous_scientific_payload),
            source_observation_identity=result.source_observation_identity,
            normal_audit_payload=audit_payload['normal_audit_payload'],
            registry_audit_payload=audit_payload['registry_audit_payload'],
            source_observation_audit_payload=audit_payload['source_observation_audit_payload'],
            workload_projection=audit_payload['workload_projection'])
        save(destination / 'scientific_projection.json', projection)
        save(destination / 'audit_payload.json', audit_payload)
    except BaseException:
        profiler.disable()
        active = False
        error = traceback.format_exc()
        (destination / 'error.txt').write_text(error, encoding='utf8')
    finally:
        if patch is not None:
            patch.undo()
    elapsed = time.perf_counter() - start
    full_calls = None
    if profiling:
        profiler.dump_stats(str(destination / 'profile.pstats'))
        stats = pstats.Stats(profiler)
        with (destination / 'profile.txt').open('x') as stream:
            pstats.Stats(profiler, stream=stream).sort_stats('cumulative').print_stats(65)
        hour = str(Path(verifier.witness.hour.__file__).resolve())
        full_calls = sum(row[1] for key, row in stats.stats.items()
                         if Path(key[0]).resolve() == Path(hour) and key[2] == 'inspect')
    after = {str(p): digest(p) for p in sorted(saved.rglob('*')) if p.is_file()}
    code_after = {str(p): digest(p) for p in paths}
    passed = error is None and before == after and code_before == code_after
    terminal = dict(exit_code=0 if passed else 1, elapsed_seconds=elapsed,
        full_hour_inspect_calls=full_calls, error=error, saved_files=len(before),
        saved_files_unchanged=before == after, implementation_before=code_before,
        implementation_after=code_after, mode=mode, Jobs=0, real_native_calls=0,
        formal_result=False, full_chain_passed=False, timing_includes_profiler=profiling)
    save(destination / 'terminal.json', terminal)
    print(json.dumps({k:v for k,v in terminal.items() if not k.startswith('implementation')}), flush=True)
    return terminal['exit_code']


if __name__ == '__main__':
    sys.exit(main())
