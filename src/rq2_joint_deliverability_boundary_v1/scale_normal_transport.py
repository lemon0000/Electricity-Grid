"""Bounded fixed-class transport of source declarations and the full resource plan."""
from dataclasses import fields
from math import isfinite
from hashlib import sha256
from pathlib import Path
import json

from . import scale_normal_source as source

SCHEMA = 'draft_source_bound_scale_normal_transport_v1'
LIMIT = 16*1024**2
b = source.budgets
CLASSES = (source.ScaleNormalSourceRequest, source.prepare.legacy.NormalTaskSourceRequest,
    source.kernel.Rq2ModelScale, source.kernel.Rq2SolverSpec, b.ScaleNormalBudget, b.NormalResourcePlan, b.SingleNormalResourcePlan,
    b.workload.NormalWork, b.workload.EpisodeWork, b.resources.TaskEnvelope, b.resources.SerialResourceBudget)
TYPES = {c.__name__: c for c in CLASSES}


def implementation_identity(request):
    return source.kernel._digest(SCHEMA, source.request_identity(request), sha256(Path(__file__).read_bytes()).hexdigest())


def _transform(value, decoding=False):
    count = 0
    def visit(x, depth=0):
        nonlocal count
        count += 1
        if depth > 64 or count > 500000:
            raise ValueError('bounded normal request structure exceeded')
        if x is None or type(x) in (str,int,bool):
            return x
        if not decoding:
            if type(x) is float:
                if not isfinite(x): raise ValueError('finite request float required')
                return ['float',x.hex()]
            if type(x) is tuple:
                return ['tuple',[visit(y,depth+1) for y in x]]
            if type(x) not in CLASSES:
                raise ValueError('normal request class outside fixed inventory')
            return [type(x).__name__,[[f.name,visit(getattr(x,f.name),depth+1)] for f in fields(x)]]
        if type(x) is not list or len(x)!=2 or type(x[0]) is not str:
            raise ValueError('canonical normal request wire required')
        tag,body=x
        if tag=='float':
            if type(body) is not str: raise ValueError('canonical float string required')
            result=float.fromhex(body)
            if not isfinite(result) or result.hex()!=body: raise ValueError('canonical finite float required')
            return result
        if tag=='tuple':
            if type(body) is not list: raise ValueError('tuple body array required')
            return tuple(visit(y,depth+1) for y in body)
        if tag not in TYPES or type(body) is not list:
            raise ValueError('normal request class outside fixed inventory')
        cls=TYPES[tag]
        if (any(type(row) is not list or len(row)!=2 for row in body)
                or [row[0] for row in body]!=[f.name for f in fields(cls)]):
            raise ValueError('exact ordered normal request fields required')
        return cls(**{k:visit(v,depth+1) for k,v in body})
    return visit(value)


def export_request(request):
    source.request_identity(request)
    data=source.replay._bytes(dict(schema=SCHEMA,request=_transform(request)))
    if len(data)>LIMIT: raise ValueError('normal request byte limit exceeded')
    return data


def decode_request(data):
    if type(data) is not bytes or len(data)>LIMIT: raise ValueError('bounded request bytes required')
    body=json.loads(data)
    if (type(body) is not dict or set(body)!={'schema','request'} or body['schema']!=SCHEMA
            or source.replay._bytes(body)!=data):
        raise ValueError('canonical exact request packet required')
    request=_transform(body['request'],True)
    if export_request(request)!=data: raise ValueError('normal input roundtrip differs')
    return request


def read_request(path,*,expected_sha256,max_request_bytes):
    if type(max_request_bytes) is not int or not 0<max_request_bytes<=LIMIT:
        raise ValueError('bounded normal request read required')
    source.kernel._pin(expected_sha256)
    return decode_request(source.prepare._read_pinned(path,expected_sha256,max_request_bytes))
