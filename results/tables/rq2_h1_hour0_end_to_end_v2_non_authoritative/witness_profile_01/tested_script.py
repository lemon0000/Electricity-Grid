"""Read-only synthetic N0 replay profile; no cache, Job or native execution."""
import cProfile
import hashlib
import json
from pathlib import Path
import pstats
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(1, str(ROOT / 'tests'))
from experiments import h1_phase_historical_controller_development_v1 as historical
from tests.test_h1_saved_job_development_v1 import install_child_source
from tests.test_h1_hour0_end_to_end_development_v2 import complete_source_rows, no_solver


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    saved, destination = map(Path, sys.argv[1:3])
    mode = sys.argv[3] if len(sys.argv) > 3 else 'full'
    assert mode in ('full', 'witness')
    if mode == 'witness':
        from experiments import h1_historical_n0_verifier_development_v1 as implementation
    else:
        implementation = historical
    destination.mkdir(exist_ok=False)
    script_pin = digest(Path(__file__))
    (destination / 'tested_script.py').write_bytes(Path(__file__).read_bytes())
    before = {str(p): digest(p) for p in saved.rglob('*') if p.is_file()}
    roots = sorted(saved.glob('nt_non_authoritative/episodes/*/controller_non_authoritative'))
    assert len(roots) == 3
    root = roots[0]
    directory = root / 'obligation_non_authoritative'
    args = dict(expected_binding_sha256=digest(directory / 'binding.json'),
                expected_terminal_sha256=digest(directory / '000.terminal.json'), completed_hours=1)
    (destination / 'request.json').write_text(json.dumps(dict(root=str(root), arguments=args,
        mode=mode, script_sha256=script_pin, saved_before=before, real_native_calls=0,
        formal_result=False), indent=2) + '\n', encoding='utf-8')
    patch = None
    profiler = cProfile.Profile()
    paths = set()
    active = False
    def audit(event, values):
        if not active or event != 'open':
            return
        path, mode, flags = values
        if isinstance(path, (str, bytes)):
            if isinstance(mode, str) and any(c in mode for c in 'wax+'):
                raise RuntimeError('replay attempted a write')
            paths.add(str(Path(path).absolute()))
    sys.addaudithook(audit)
    start = time.perf_counter()
    error = None
    try:
        patch = install_child_source(saved / 'test_complete_independent_N0_r0')
        no_solver.__wrapped__(patch)
        complete_source_rows(patch)
        patch.setattr(historical, '_source_paths', lambda d: (
            {Path(d['config_path']), Path(d['upstream_root']) / 'SHA256SUMS'},
            {Path(d['upstream_root'])}))
        proof_raw = (historical.binding.ROOT / historical.binding.MANIFEST).read_bytes()
        assert hashlib.sha256(proof_raw).hexdigest() == historical.binding.MANIFEST_PIN
        resolver = historical.binding.manifest._resolver(proof_raw)
        patch.setattr(historical.binding, 'open_manifest', lambda: resolver)
        # Same explicit synthetic enrollment seam used to produce these Jobs.
        patch.setattr(historical.binding, 'precheck',
                      lambda resolver, declaration, **kw: resolver.resolve(kw['family'], kw['ordinal']))
        patch.setattr(historical.binding, 'prevalidate_enrollment',
                      lambda *a, **kw: dict(test_only_synthetic_source=True))
        active = True
        profiler.enable()
        with historical.history.replay.guard.solver_calls_forbidden():
            envelope = implementation.prepare(root, **args)
        profiler.disable()
        active = False
        (destination / 'audit_payload.json').write_bytes(envelope.audit_payload)
        (destination / 'decision.json').write_bytes(envelope.decision.decision_bytes)
    except BaseException:
        profiler.disable()
        active = False
        error = traceback.format_exc()
        (destination / 'error.txt').write_text(error, encoding='utf-8')
    finally:
        if patch is not None:
            patch.undo()
    elapsed = time.perf_counter() - start
    profiler.dump_stats(str(destination / 'profile.pstats'))
    with (destination / 'profile.txt').open('w', encoding='utf-8') as stream:
        pstats.Stats(profiler, stream=stream).sort_stats('cumulative').print_stats(65)
    after = {str(p): digest(p) for p in saved.rglob('*') if p.is_file()}
    result = dict(exit_code=0 if error is None and before == after else 1,
        elapsed_seconds=elapsed, saved_files=len(before), saved_before_equals_after=before == after,
        script_before_equals_after=digest(Path(__file__)) == script_pin,
        observed_open_paths=sorted(paths), complete_dynamic_input_closure_proved=False,
        mode=mode, optimization_integrated=False, full_chain_passed=False, real_native_calls=0,
        Jobs=0, formal_result=False)
    (destination / 'terminal.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'observed_open_paths'}), flush=True)
    return result['exit_code']


if __name__ == '__main__':
    sys.exit(main())
