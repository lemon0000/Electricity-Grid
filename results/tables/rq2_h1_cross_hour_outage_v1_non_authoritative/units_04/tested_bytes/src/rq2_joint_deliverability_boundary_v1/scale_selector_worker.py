"""Pinned selector worker and bounded input transport; not a task controller.

Transport reconstructs only externally pinned input declarations. It grants no
normal-plan, predecessor, source, numerical or execution authority.
"""
import argparse
from dataclasses import fields
from hashlib import sha256
from math import isfinite
import os
from pathlib import Path
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = 'src.rq2_joint_deliverability_boundary_v1'

from . import scale_selector as scale, scale_selector_store as store
from . import grid_information as grid, event_disclosure as event, current_grid_step as step
from . import reference_grid as reference, actual_dispatch_selector as actual
from . import continuous_grid_normal as codec
from ..solvers import rq2_solver_adapter as solver

SCHEMA = 'draft_pinned_scale_selector_worker_v1'
CLASSES = (
    store.SelectorRequest, scale.ScaleSelectorBudget, solver.Rq2SolverSpec,
    scale.reference.ReferenceSelectorSpec, actual.ActualDispatchSpec,
    grid.CurrentGridInformation, grid.StaticNetwork, grid.StaticUnit, grid.StaticAcBranch,
    grid.StaticDcBranch, grid.NormalHourView, grid.PlanInformationDeclaration, grid.CurrentGridConditions,
    event.OutageComponent, event.DisclosureProtocol, event.RevealedOutage,
    event.DisclosureState, event.CurrentOutageReport, event.DisclosureStep,
    step.CurrentGridProtocol, step.PrescribedDcPower, step.ActualStepCarry,
    reference.ReferenceProtocol, reference.ReferenceGridOrigin, reference.ReferenceGridState,
    actual.ActualDispatchOrigin, actual.ActualDispatchState,
)
TYPES = {cls.__name__: cls for cls in CLASSES}


def implementation_identity():
    modules = (scale, store, grid, event, step, reference, scale.reference, actual, codec, solver, store.local,
               scale.execution_resource_contract, scale.execution_workload)
    return codec._digest(SCHEMA, sha256(Path(__file__).read_bytes()).hexdigest(),
        tuple((m.__name__, sha256(Path(m.__file__).read_bytes()).hexdigest()) for m in modules),
        codec._dependencies())


def export_request(request):
    if type(request) is not store.SelectorRequest:
        raise ValueError('typed selector request required')
    return store._bytes(dict(schema=SCHEMA, request=codec._encode(request)))


def decode_request(raw):
    packet = store._decoded(raw)
    if type(packet) is not dict or set(packet) != {'schema', 'request'} or packet['schema'] != SCHEMA:
        raise ValueError('exact worker packet required')
    count = 0
    def decode(wire, depth=0):
        nonlocal count
        count += 1
        if depth > 32 or count > 100000:
            raise ValueError('bounded worker input structure exceeded')
        if wire is None or type(wire) in (str, int, bool):
            return wire
        if type(wire) is not list or len(wire) != 2 or type(wire[0]) is not str:
            raise ValueError('canonical input wire required')
        name, body = wire
        if name == 'float':
            if type(body) is not str:
                raise ValueError('canonical hex float required')
            value = float.fromhex(body)
            if not isfinite(value) or value.hex() != body:
                raise ValueError('finite canonical hex float required')
            return value
        if name == 'tuple':
            if type(body) is not list:
                raise ValueError('tuple wire requires array')
            return tuple(decode(x, depth+1) for x in body)
        if name not in TYPES or type(body) is not list:
            raise ValueError('input class is not in fixed worker inventory')
        cls = TYPES[name]
        if (any(type(pair) is not list or len(pair) != 2 for pair in body)
                or [pair[0] for pair in body] != [field.name for field in fields(cls)]):
            raise ValueError('exact ordered class fields required')
        values = {key: decode(value, depth+1) for key, value in body}
        return cls(**values) if cls.__dataclass_params__.init else step._owned(cls, **values)
    result = decode(packet['request'])
    if type(result) is not store.SelectorRequest or export_request(result) != raw:
        raise ValueError('canonical request roundtrip mismatch')
    return result


def read_request(path, *, expected_sha256, max_request_bytes):
    scale.actual._hash(expected_sha256)
    if type(max_request_bytes) is not int or not 0 < max_request_bytes <= 16*1024**2:
        raise ValueError('explicit request byte limit in (0,16MiB] required')
    path = store.local._path(path)
    before = store.local._file_identity(path)
    with path.open('rb') as stream:
        raw = stream.read(max_request_bytes+1)
    if len(raw) > max_request_bytes or sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('worker request size/hash mismatch')
    if store.local._file_identity(path) != before:
        raise ValueError('worker request file replaced during read')
    return decode_request(raw)


def run_worker(*, request_path, expected_request_sha256, max_request_bytes,
               store_root, receipt_path, max_record_bytes, expected_implementation_identity):
    scale.actual._hash(expected_implementation_identity)
    if implementation_identity() != expected_implementation_identity:
        raise ValueError('worker implementation drift')
    receipt_path = store.local._path(receipt_path)
    if not receipt_path.name.endswith('_non_authoritative.json') or receipt_path.exists():
        raise ValueError('new non_authoritative receipt required')
    request = read_request(request_path, expected_sha256=expected_request_sha256, max_request_bytes=max_request_bytes)
    with store.DevelopmentScaleSelectorStore(store_root, request, max_record_bytes=max_record_bytes) as owned:
        result = owned.execute()
        inspection = owned.inspection()
    if (implementation_identity() != expected_implementation_identity
            or export_request(read_request(request_path, expected_sha256=expected_request_sha256,
                                           max_request_bytes=max_request_bytes)) != export_request(request)):
        raise ValueError('worker source or request changed during invocation')
    receipt = dict(schema=SCHEMA, request_sha256=expected_request_sha256,
        implementation_identity=expected_implementation_identity,
        store_binding_identity=inspection['binding_identity'], result_identity=result.identity,
        reported_status=result.status, inspection=inspection,
        formal_result=False, whole_task_resources_verified=False)
    raw = store._bytes(receipt)
    with receipt_path.open('xb') as stream:
        if stream.write(raw) != len(raw):
            raise OSError('worker receipt short write')
        stream.flush()
        os.fsync(stream.fileno())
        written = os.fstat(stream.fileno())
    identity = store.local._file_identity(receipt_path)
    if identity != (written.st_dev, written.st_ino):
        raise ValueError('worker receipt file replaced after write')
    with receipt_path.open('rb') as stream:
        if stream.read(len(raw)+1) != raw:
            raise ValueError('worker receipt exact readback mismatch')
    if store.local._file_identity(receipt_path) != identity:
        raise ValueError('worker receipt file replaced during readback')
    if (implementation_identity() != expected_implementation_identity
            or export_request(read_request(request_path, expected_sha256=expected_request_sha256,
                                           max_request_bytes=max_request_bytes)) != export_request(request)):
        raise ValueError('worker source or request changed during receipt publication')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('request-path', 'expected-request-sha256', 'store-root', 'receipt-path', 'expected-implementation-identity'):
        parser.add_argument('--'+name, required=True)
    for name in ('max-request-bytes', 'max-record-bytes'):
        parser.add_argument('--'+name, required=True, type=int)
    run_worker(**vars(parser.parse_args()))


if __name__ == '__main__':
    main()
