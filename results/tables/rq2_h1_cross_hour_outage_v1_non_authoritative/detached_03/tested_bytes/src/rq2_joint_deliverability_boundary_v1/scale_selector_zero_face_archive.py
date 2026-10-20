"""Source-bound replay of a mixed selector journal record, with no solver calls.

The caller supplies externally retained record and journal-binding pins. A
reproduced numerical record does not authenticate native execution or resources.
"""
from hashlib import sha256
from pathlib import Path

from . import scale_selector_zero_face_worker as worker
from . import scale_selector_zero_face_replay as replay

SCHEMA = 'draft_mixed_selector_archive_replay_v1'


def implementation_identity():
    return worker.codec._digest(SCHEMA, sha256(Path(__file__).read_bytes()).hexdigest(),
        worker.implementation_identity(), replay.implementation_identity())


def _verify(data, request, *, expected_sha256, expected_binding_identity,
            expected_implementation_identity, max_record_bytes):
    for pin in (expected_sha256, expected_binding_identity, expected_implementation_identity):
        worker.actual._hash(pin)
    if (type(data) is not bytes or type(max_record_bytes) is not int
            or not 0 < max_record_bytes <= 16*1024**2 or len(data) > max_record_bytes
            or sha256(data).hexdigest() != expected_sha256):
        raise ValueError('mixed archive record hash/size mismatch')
    if implementation_identity() != expected_implementation_identity:
        raise ValueError('mixed archive implementation mismatch')
    packet = worker.export_request(request)
    request = worker.decode_request(packet)
    module = worker.scale._admit(request.selection_spec, request.solver_specification,
        request.budget, request.budget.max_solver_calls)
    reference = module is worker.scale.reference
    args = (request.info, request.disclosure, request.before)
    if not reference:
        args += (request.power,)
    identity = module.reference_input_identity if reference else module.dispatch_input_identity
    if (identity(*args) != request.expected_identity
            or worker.scale.policy_identity(request.selection_spec, request.solver_specification,
                                             request.budget) != request.expected_policy_identity
            or tuple(unit.uid for unit in request.info.network.units) != request.budget.generator_uids
            or request.info.current.source_hour != request.budget.source_hour
            or (reference and request.power is not None) or (not reference and request.power is None)
            or (hasattr(request.before, 'selector_policy_identity')
                and request.before.selector_policy_identity != request.expected_policy_identity)):
        raise ValueError('mixed archive input/policy/hour/UID mismatch')
    labels = (('grid_request', 'l1_normal_deviation') if reference
              else ('l1_normal_deviation',))
    labels += tuple('generation:'+uid for uid in request.budget.generator_uids)
    record = worker.store._decoded(data)
    saved = worker.store._validate_record(record,
        dict(request=worker.codec._encode(request), planned_stages=labels), expected_binding_identity)
    result = None
    if saved['status'] == 'unresolved':
        if saved['next_state'] is not None or saved['selected_request_exact'] is not None:
            raise ValueError('unresolved mixed archive cannot publish state')
        report = dict(status='unresolved_archive_not_replayed', archive_reproduced=False,
                      selection_accepted=False)
    elif saved['status'] == 'selected':
        raw = worker.store._bytes(record['encoded_result'])
        report, result = replay.replay(raw, request.info, request.disclosure, request.before,
            expected_sha256=sha256(raw).hexdigest(), expected_implementation=replay.implementation_identity(),
            expected_identity=request.expected_identity, selector=request.selection_spec,
            solver_specification=request.solver_specification, budget=request.budget,
            expected_policy_identity=request.expected_policy_identity, power=request.power,
            max_record_bytes=max_record_bytes)
        if result.identity != record['result_identity']:
            raise ValueError('mixed archive result identity mismatch')
        report.update(status='reproduced_selected_chain', selection_accepted=True)
    else:
        raise ValueError('unknown mixed archive status')
    if (implementation_identity() != expected_implementation_identity
            or worker.export_request(request) != packet):
        raise ValueError('mixed archive source or implementation drift')
    report.update(schema=SCHEMA, record_sha256=expected_sha256,
        binding_identity=expected_binding_identity, solver_calls_by_replay_module=0,
        formal_result=False, security_certified=False, whole_task_resources_verified=False,
        native_execution_authenticated=False, executable_resume_available=False)
    return report, result


def replay_record(data, request, **kwargs):
    return _verify(data, request, **kwargs)[0]
