"""Read-only application of the authorized numerical rule to retained H25 evidence.

This is a numerical-normal successor assessment, not a formal experiment runner.
The caller publishes its report separately; all original evidence stays immutable.
"""
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments import audit_rq2_h25_native_provenance_v1 as entry
from experiments import replay_rq2_h25_native_provenance_v1 as replay
from src.solvers import rq2_normal_numerical_acceptance_v1 as acceptance

PINS = {
    'result.json': 'a3832900d078a569cb0f9862cf0dbfafac17f0cc2c4ca9aa80aa6edccf8608f0',
    'native_record.json': '87cefb0f180f49d0315de24b761e85f4fa8dd27c85310ca944652e184f49979d',
    'intent.json': '0cd52e2d3d6da10c6f053cd4492a4e6678a4a0a5d8e7214caa225121e66e9720',
    'launch.json': '03ce0d0898c74871392760c89b24de1c3cab7be9b9556f7241752f2335a41536',
    'observation.json': '038cec4c4dbeceda0b883086f1a03189390ecfe6ed24a8ca5fa4facd1708a578',
}
SCRIPT = 'd1125fe93deaf741db319602306aa5119fdc3bb3b014e79d704c1d6960873b97'
RUNNER = '6befe7cc582bd33d35f2af8e56a3cf89966cfcd25d3a6551233632dffbdc8bbd'


def snapshot():
    records = {name: entry.retained(entry.OUTPUT / name) for name in PINS}
    if any(records[name][1] != pin for name, pin in PINS.items()):
        raise ValueError('retained H25 evidence pin mismatch')
    manifest = json.loads(records['result.json'][2])
    if manifest['file_sha256'] != {k: v for k, v in PINS.items() if k != 'result.json'}:
        raise ValueError('retained H25 manifest inventory mismatch')
    return records


def verify():
    retained = snapshot()
    report = json.loads(retained['native_record.json'][2])
    request, identity = entry.check(SCRIPT, RUNNER)
    entry.validate_record(report, request, identity, SCRIPT, RUNNER)
    source = entry.transport.source
    modules = (Path(__file__), Path(acceptance.__file__), Path(acceptance.predicate.__file__),
               Path(replay.__file__))
    code_pins = {str(p.relative_to(ROOT)).replace('\\', '/'): sha256(p.read_bytes()).hexdigest()
                 for p in modules}
    targets = ((entry.run, 'solve_once'), (entry.run.provenance.adapter, 'create_solver'),
               (source, 'run_source'), (source.kernel, 'run_normal_only'),
               (source.kernel.native, '_solve'))
    originals = [(module, name, getattr(module, name)) for module, name in targets]
    def forbidden(*args, **kwargs):
        raise RuntimeError('solver forbidden during successor verification')
    try:
        for module, name in targets:
            setattr(module, name, forbidden)
        inputs, _ = source._prepare(request, identity)
        assessed = acceptance.assess_assignment(inputs, report['numerical'],
            expected_input_identity=request.source.expected_input_identity,
            expected_runner_identity=RUNNER,
            expected_collector_sha256=sha256(Path(entry.run.provenance.__file__).read_bytes()).hexdigest(),
            expected_adapter_identity=entry.run.provenance.adapter.implementation_identity())
        if entry.check(SCRIPT, RUNNER)[1] != identity or snapshot() != retained:
            raise ValueError('source or retained evidence drift during verification')
        if any(sha256((ROOT / name).read_bytes()).hexdigest() != pin for name, pin in code_pins.items()):
            raise ValueError('successor implementation drift')
        return dict(schema='rq2_h25_normal_acceptance_assessment_v1',
            scope='retained_h25_numerical_normal_archive_only',
            mechanism_initial_state=True, observed_power_mapping=False,
            registered_coupling=False, source_correspondence_rechecked=True,
            source_request_identity=identity, evidence_sha256=dict(PINS),
            implementation_sha256=code_pins, assessment=assessed,
            solver_calls_by_verifier=0, formal_result=False,
            original_result_status_changed=False, independent_review_gate_closed=False)
    finally:
        for module, name, original in originals:
            setattr(module, name, original)


if __name__ == '__main__':
    print(json.dumps(verify(), sort_keys=True, allow_nan=False))
