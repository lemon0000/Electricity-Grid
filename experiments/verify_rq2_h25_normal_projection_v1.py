"""Zero-solver source/plan projection of the separately pinned H25 archive."""
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments import verify_rq2_h25_normal_acceptance_v1 as retained
from src.rq2_joint_deliverability_boundary_v1 import normal_numerical_source as api


def verify():
    verifier_sha256 = sha256(Path(__file__).read_bytes()).hexdigest()
    implementation = api.implementation_identity()
    before = retained.snapshot()
    request, identity = retained.entry.check(retained.SCRIPT, retained.RUNNER)
    record = json.loads(before['native_record.json'][2])
    retained.entry.validate_record(record, request, identity, retained.SCRIPT, retained.RUNNER)
    raw = api.capture.encode(record['numerical'])
    declaration = api.information.PlanInformationDeclaration(0,
        'supplied_normal_profiles_declared_as_pre_episode_forecast',
        'fixed_normal_schedule_issued_before_first_action', 'mechanism_assumption')
    args = dict(expected_record_sha256=sha256(raw).hexdigest(), max_record_bytes=api.LIMIT)
    args['expected_binding_identity'] = api.binding_identity(request, declaration, **args)
    targets = ((api.capture, 'solve_once'), (api.capture.provenance.adapter, 'create_solver'),
        (api.source, 'run_source'), (api.source.kernel, 'run_normal_only'),
        (api.source.kernel.native, '_solve'))
    originals = [(module, name, getattr(module, name)) for module, name in targets]
    def forbidden(*args, **kwargs):
        raise RuntimeError('solver forbidden during H25 projection')
    try:
        for module, name, _ in originals: setattr(module, name, forbidden)
        report, prepared = api.prepare_information(raw, request, declaration, **args)
        if retained.snapshot() != before or retained.entry.check(retained.SCRIPT, retained.RUNNER)[1] != identity:
            raise ValueError('retained H25 source drift')
        if prepared is None or len(prepared.hours) != 25 or len(prepared.network.units) != 158:
            raise ValueError('complete H25 plan projection required')
        if (sha256(Path(__file__).read_bytes()).hexdigest() != verifier_sha256
                or api.implementation_identity() != implementation):
            raise ValueError('H25 projection verifier implementation drift')
        return dict(schema='rq2_h25_normal_source_projection_verification_v1',
            scope='retained_h25_archive_source_and_plan_correspondence',
            verifier_sha256=verifier_sha256, projection_implementation_identity=implementation,
            evidence_sha256=dict(retained.PINS), source_binding=args,
            report=report, prepared_information=api.source.kernel._encode(prepared),
            hours=len(prepared.hours), units=len(prepared.network.units),
            solver_calls_by_verifier=0, formal_result=False,
            original_result_status_changed=False, native_execution_authenticated=False)
    finally:
        for module, name, original in originals: setattr(module, name, original)


if __name__ == '__main__':
    print(json.dumps(verify(), sort_keys=True, allow_nan=False))
