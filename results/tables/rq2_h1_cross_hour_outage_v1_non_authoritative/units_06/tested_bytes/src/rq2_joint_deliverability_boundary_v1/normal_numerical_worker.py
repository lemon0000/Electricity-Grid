"""Fixed source-normal execute/audit worker; requires caller-owned supervision."""
import argparse
from hashlib import sha256
import os
from pathlib import Path
import sys

if __package__ in (None, ''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
    __package__='src.rq2_joint_deliverability_boundary_v1'

from . import normal_numerical_transport as transport, scale_selector_controller as files

source=transport.source
SCHEMA='draft_source_bound_numerical_normal_worker_v1'


def implementation_identity(request):
    return source.kernel._digest(SCHEMA,transport.implementation_identity(request),
        tuple((m.__name__,sha256(Path(m.__file__).read_bytes()).hexdigest())
              for m in (files,files.local,files.worker.store)),sha256(Path(__file__).read_bytes()).hexdigest())


def environment_identity():
    return sha256(files.worker.store._bytes(dict(os.environ))).hexdigest()


def _write_record(path,raw,maximum):
    if len(raw)>maximum: raise ValueError('source record exceeds declared byte limit')
    with path.open('xb') as stream:
        if stream.write(raw)!=len(raw): raise OSError('short source record write')
        stream.flush()
        os.fsync(stream.fileno())
        stat=os.fstat(stream.fileno())
    identity=(stat.st_dev,stat.st_ino)
    pin=sha256(raw).hexdigest()
    if (source.prepare._read_pinned(path,pin,maximum)!=raw or files.local._file_identity(path)!=identity):
        raise ValueError('source record publication readback differs')
    return identity,pin


def run_worker(*,mode,request_path,expected_request_sha256,expected_request_identity,
               max_request_bytes,root,receipt_path,expected_environment_identity,
               expected_implementation_identity,max_record_bytes,expected_intent_sha256=None,
               expected_record_sha256=None,expected_execution_environment_identity=None):
    if mode not in ('execute','audit'): raise ValueError('fixed source normal worker mode required')
    if type(max_record_bytes) is not int or not 0<max_record_bytes<=64*1024**2:
        raise ValueError('explicit bounded source record required')
    for pin in (expected_request_sha256,expected_request_identity,expected_environment_identity,expected_implementation_identity):
        source.kernel._pin(pin)
    if mode=='execute':
        if (expected_intent_sha256 is not None or expected_record_sha256 is not None
                or expected_execution_environment_identity is not None):
            raise ValueError('new execution cannot accept audit/resume pins')
    else:
        source.kernel._pin(expected_intent_sha256)
        source.kernel._pin(expected_record_sha256)
        source.kernel._pin(expected_execution_environment_identity)
    root,receipt,request_path=map(files.local._path,(root,receipt_path,request_path))
    if (receipt.is_relative_to(root) or request_path.is_relative_to(root)
            or not receipt.name.endswith('_non_authoritative.json') or receipt.exists()):
        raise ValueError('new separate receipt and external request required')
    def check():
        request=transport.read_request(request_path,expected_sha256=expected_request_sha256,max_request_bytes=max_request_bytes)
        if (source.request_identity(request)!=expected_request_identity
                or implementation_identity(request)!=expected_implementation_identity
                or environment_identity()!=expected_environment_identity):
            raise ValueError('source worker input/environment/implementation drift')
        return request
    request=check()
    if max_record_bytes>request.budget.envelope.archive_bytes:
        raise ValueError('source record allocation exceeds declared task archive')
    upstream=files.local._path(request.source.upstream_root)
    source_files={files.local._path(getattr(request.source,k)) for k in
                  ('normal_record_path','pair_declaration_path','config_path')}
    if root.is_relative_to(upstream) or receipt.is_relative_to(upstream) or receipt in source_files:
        raise ValueError('worker output must not modify source paths')
    if any(p.is_relative_to(root) for p in source_files):
        raise ValueError('source declarations must be outside worker evidence root')
    intent=dict(schema=SCHEMA,request_sha256=expected_request_sha256,request_identity=expected_request_identity,
        implementation_identity=expected_implementation_identity,environment_identity=(expected_environment_identity
            if mode=='execute' else expected_execution_environment_identity),
        max_record_bytes=max_record_bytes,planned_solver_calls=1,reserved_solver_seconds=request.budget.max_seconds_per_solve,
        formal_result=False,executable_resume_available=False)
    lease=files.local._Lease(root,mode=='execute')
    try:
        def inventory(expected):
            lease.check()
            if {p.name for p in root.iterdir()}!=set(expected): raise ValueError('exact source evidence inventory required')
        if mode=='execute':
            inventory(('execution.lock',))
            intent_file,intent_pin=files._write(root/'intent.json',intent)
        else:
            inventory(('execution.lock','intent.json','normal_record.json'))
            intent_pin=expected_intent_sha256
            source.prepare._read_pinned(root/'intent.json',intent_pin,files.LIMIT)
            intent_file=files.local._file_identity(root/'intent.json')
            if files.worker.store._bytes(files._read(root/'intent.json',intent_file))!=files.worker.store._bytes(intent):
                raise ValueError('source intent differs from independent request')
        def runtime_check():
            lease.check()
            check()
            if files.local._file_identity(root/'intent.json')!=intent_file:
                raise ValueError('source intent identity changed')
            source.prepare._read_pinned(root/'intent.json',intent_pin,files.LIMIT)
        runtime_check()
        if mode=='execute':
            outcome=source.run_source(request,expected_request_identity=expected_request_identity,before_kernel=runtime_check)
            runtime_check()
            record_file,record_pin=_write_record(root/'normal_record.json',source.replay._bytes(outcome),max_record_bytes)
            summary=dict(accepted=outcome['accepted'],status=outcome['status'],solver_calls=outcome['solver_calls'],
                call_count_complete=outcome['call_count_complete'],source_correspondence_verified=outcome['source_correspondence_verified'])
        else:
            record_file=files.local._file_identity(root/'normal_record.json')
            record_pin=expected_record_sha256
            raw=source.prepare._read_pinned(root/'normal_record.json',record_pin,max_record_bytes)
            with source.solver_free():
                summary=source.audit_source(raw,request,expected_sha256=record_pin,
                    expected_request_identity=expected_request_identity,max_record_bytes=max_record_bytes)

        def retained():
            runtime_check()
            inventory(('execution.lock','intent.json','normal_record.json'))
            if files.local._file_identity(root/'normal_record.json')!=record_file:
                raise ValueError('source record replaced')
            source.prepare._read_pinned(root/'normal_record.json',record_pin,max_record_bytes)
        retained()
        result=dict(schema=SCHEMA,mode=mode,request_identity=expected_request_identity,
            request_sha256=expected_request_sha256,environment_identity=expected_environment_identity,
            implementation_identity=expected_implementation_identity,root=str(root),intent_sha256=intent_pin,
            record_sha256=record_pin,outcome=summary,formal_result=False,whole_task_resources_verified=False,
            executable_resume_available=False)
        files._write(receipt,result)
        retained()
        return result
    finally:
        lease.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('execute','audit'),required=True)
    for name in ('request-path','expected-request-sha256','expected-request-identity','root','receipt-path',
                 'expected-environment-identity','expected-implementation-identity'):
        parser.add_argument('--'+name,required=True)
    for name in ('max-request-bytes','max-record-bytes'):
        parser.add_argument('--'+name,required=True,type=int)
    for name in ('expected-intent-sha256','expected-record-sha256','expected-execution-environment-identity'):
        parser.add_argument('--'+name)
    run_worker(**vars(parser.parse_args()))


if __name__=='__main__': main()
