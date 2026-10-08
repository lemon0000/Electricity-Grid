"""Job-child entry for a bounded zero-solver H1 algebraic shape probe."""
import json
import os
from pathlib import Path
import sys
from hashlib import sha256
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from src.rq2_joint_deliverability_boundary_v1 import normal_h1_resource_shape as shape
from src.rq2_joint_deliverability_boundary_v1.normal_execution import _peak_working_set_bytes

MAX_RESULT_BYTES=1024*1024
REQUEST_FIELDS={'schema','declaration','upstream_root','config_path','expected_source_identity','dc_bus',
                'expected_network_identity','expected_stage_count','output_file','shape_implementation_identity','worker_sha256'}


def execute(request_path, expected_request_sha256):
    started=perf_counter()
    shape.binding.windows._sha(expected_request_sha256)
    path=Path(request_path)
    if path.stat().st_size > 64*1024:
        raise ValueError('bounded shape request required')
    raw=path.read_bytes()
    if sha256(raw).hexdigest()!=expected_request_sha256:
        raise ValueError('shape request hash mismatch')
    request=shape.episode.replay._decode(raw,64*1024)
    if (type(request) is not dict or set(request)!=REQUEST_FIELDS
            or request['schema']!='h1_zero_solver_shape_probe_request_v1'
            or request['shape_implementation_identity']!=shape.implementation_identity()
            or request['worker_sha256']!=sha256(Path(__file__).read_bytes()).hexdigest()):
        raise ValueError('shape worker request schema/implementation mismatch')
    output=Path(request['output_file'])
    if (not output.is_absolute() or output.parent.resolve()!=Path.cwd().resolve()
            or not output.parent.name.endswith('_non_authoritative') or output.exists()):
        raise ValueError('exclusive non-authoritative scratch output required')
    declaration=shape.binding.H1SourceDeclaration(**request['declaration'])
    report=shape.pinned_shape_probe(declaration,request['upstream_root'],config_path=request['config_path'],
        expected_source_identity=request['expected_source_identity'],dc_bus=request['dc_bus'])
    report.update(request_sha256=expected_request_sha256,worker_sha256=request['worker_sha256'],
        process_peak_working_set_bytes=_peak_working_set_bytes(),worker_elapsed_seconds=perf_counter()-started,
        peak_working_set_scope='process_lifetime_not_single_model',hard_rss_limit_enforced=False)
    if shape.implementation_identity()!=request['shape_implementation_identity']:
        raise ValueError('shape worker implementation drift')
    payload=json.dumps(report,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
    if len(payload)>MAX_RESULT_BYTES:
        raise ValueError('shape result byte limit exceeded')
    temporary=output.with_name(output.name+'.pending')
    with temporary.open('xb') as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    # Windows rename refuses an existing destination. This worker is launched
    # only by the Windows Job owner; no replace/overwrite path is used.
    if os.name!='nt':
        raise OSError('Windows shape worker required')
    os.rename(temporary,output)
    if output.read_bytes()!=payload:
        raise ValueError('shape worker result readback mismatch')
    return sha256(payload).hexdigest()


if __name__=='__main__':
    try:
        if len(sys.argv)!=3:
            raise ValueError('request path and independently retained request SHA256 required')
        execute(sys.argv[1],sys.argv[2])
    except BaseException as error:
        message=(type(error).__name__+': '+str(error)).encode('utf-8','backslashreplace')
        with (Path.cwd()/'shape_worker_error.txt').open('xb') as stream:
            stream.write(message[:4096])
        raise SystemExit(2)
