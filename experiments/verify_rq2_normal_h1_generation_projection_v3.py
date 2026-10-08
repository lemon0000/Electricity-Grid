"""Offline 232-stage regression and complete worker benchmark; no native execution.

The capture seam serves independently pinned v2 raw. Gate verification is mocked
only while solver entry points are forbidden, inside this diagnostic process.
Output is never a native calibration root, execution authority or resource proof.
"""
import argparse
from contextlib import ExitStack
from copy import deepcopy
from hashlib import sha256
import json
import os
from math import isfinite
from pathlib import Path
import sqlite3
import sys
from time import perf_counter
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_full_job_v3 as job

OUTER_PIN = '79830ab6c1b31aaef41174544e472ef800674de1f76228793f30f6b87e4f6eba'
INVENTORY_PIN = '281ad90c2da8bdb2ff0a1031d94379f2887dc663f235c52619a1c75e25521fb4'
REVIEW_PIN = '9c034035f67bc8d891d966d19b5fd6e5f90ea8443c58949e19e9c93273c16cf2'


def main(request_path, output):
    base=Path(output).resolve()
    if not base.name.endswith('_non_authoritative'):
        raise ValueError('explicit development diagnostic root required')
    outer,_=job._read(ROOT/'configs/rq2_normal_h1_calibration_v2.OUTER.SHA256SUMS.json',OUTER_PIN)
    old=ROOT/'results/tables/rq2_normal_h1_origin_calibration_v2_non_authoritative'
    inventory,_=job._read(ROOT/'results/tables/rq2_normal_h1_full_job_v2_non_authoritative/calibration_v2.postrun_inventory.json',INVENTORY_PIN)
    review,_=job._read(ROOT/'results/tables/rq2_normal_h1_full_job_v2_non_authoritative/calibration_v2.postrun_review.json',REVIEW_PIN)
    def preserve():
        _exact_inventory(old,inventory['members'])
        for name,pin in outer['members'].items():
            if sha256((ROOT/name).read_bytes()).hexdigest()!=pin:raise ValueError('sealed drift: '+name)
        for name,item in inventory['members'].items():
            raw=(old/name).read_bytes()
            if len(raw)!=item['bytes'] or sha256(raw).hexdigest()!=item['sha256']:
                raise ValueError('retained run drift: '+name)
    preserve()
    request,declared_pin=job._read(request_path)
    job._validate_request(request)
    # This is a separate saved-input worker, never the proposed native root.
    native_root=Path(request['root']).resolve()
    _separate_output(base,native_root,old)
    base.mkdir(parents=True,exist_ok=False)
    root=base/'saved_worker_non_authoritative'
    root.mkdir()
    scratch=root/'scratch_non_authoritative';scratch.mkdir()
    request=deepcopy(request);request['root']=str(root)
    pin=job._write(root/'request.json',request)
    plan=job._configuration(request)[-1]
    job._write(root/'intent.json',dict(schema=job.SCHEMA,request_sha256=pin,
        implementation_identity=request['implementation_identity'],resource_declaration_identity=plan['declaration_identity'],formal_result=False))
    database=old/'collector_non_authoritative/stages_non_authoritative/h1_chunk_journal.sqlite3'
    conn=sqlite3.connect(database.as_uri()+'?mode=ro&immutable=1',uri=True)
    conn.execute('PRAGMA query_only=ON')
    if conn.execute('PRAGMA integrity_check').fetchone()!=('ok',):raise ValueError('source database invalid')
    rows=conn.execute('select seq,metadata,payload_bytes from events order by seq').fetchall()
    metas=[json.loads(row[1]) for row in rows]
    if len(rows)!=232 or [m['index'] for m in metas]!=list(range(232)) or any(m['kind']!='stage_accepted' for m in metas):
        raise ValueError('complete retained accepted stage inventory required')
    served=[];audits=[0]
    audit=job.collector.base.replay._audit_stage
    def checked_audit(packet,spec,limits,index,locks,raw):
        result=audit(packet,spec,limits,index,locks,raw)
        expected=metas[index]
        if (result['native_sha256']!=expected['raw_sha256']
                or result['stage_identity']!=expected['stage_identity']
                or result['numeric_sha256']!=expected['numeric_sha256']
                or result['lock'].hex()!=expected['lock_hex']
                or json.loads(job.source._bytes(result['generation_mapping']))!=expected['generation_mapping']):
            raise ValueError('v3 stage differs from retained v2 oracle: '+str(index))
        audits[0]+=1
        return result
    def saved_capture(*args,**kwargs):
        index=len(served)
        if index>=232:raise ValueError('extra capture requested')
        seq,_,size=rows[index]
        raw=b''.join(v[0] for v in conn.execute('select payload from chunks where event_seq=? order by chunk_index',(seq,)))
        if len(raw)!=size or sha256(raw).hexdigest()!=metas[index]['raw_sha256']:
            raise ValueError('retained raw mismatch')
        served.append(metas[index]['raw_sha256'])
        if len(served)%32==0:print('saved reports served:',len(served),flush=True)
        return raw
    start=perf_counter();cwd=Path.cwd()
    try:
        with ExitStack() as stack:
            stack.enter_context(job.collector.base.replay.guard.solver_calls_forbidden())
            stack.enter_context(patch.object(job.gates,'verify_consumed',lambda gate:deepcopy(request)))
            stack.enter_context(patch.object(job.collector.base.native.capture,'solve_once',saved_capture))
            stack.enter_context(patch.object(job.collector.base.replay,'_audit_stage',checked_audit))
            os.chdir(scratch)
            report=job._execute_development_worker(root/'request.json',pin,_gate={'offline_saved_raw_diagnostic':True})
    finally:
        os.chdir(cwd);conn.close()
    elapsed=perf_counter()-start
    job._validate_report(report,pin,plan)
    if (len(served)!=232 or report['summary']['status']!='accepted' or report['summary']['stored_reports']!=232
            or not report['fresh_reopen_equal'] or report['formal_result'] is not False):
        raise ValueError('complete offline worker chain required')
    preserve()
    terminal=_terminal_gate(root,metas,review['reconstructed_candidate']['payload_sha256'])
    # Preserve the actual timing even when the fixed performance gate rejects.
    job._write(base/'saved_worker_measurement.json',dict(
        schema='h1_v3_saved_worker_timing_measurement',offline_worker_wall_seconds=elapsed,
        declared_overhead_seconds=request['resource']['envelope']['non_solver_seconds'],
        stage_audit_comparisons=audits[0],raw_reports_served=len(served),
        projection_payload_sha256=terminal['projection_sha256'],fresh_reopen_equal=True,
        declared_request_sha256=declared_pin,derived_request_sha256=pin,
        worker_result_sha256=sha256((root/'worker_result.json').read_bytes()).hexdigest(),
        solver_calls=0,formal_result=False,formal_execution_ready=False))
    margin=_timing_gate(elapsed,request['resource']['envelope']['non_solver_seconds'])
    record=dict(schema='h1_v3_saved_worker_performance_diagnostic',status='development_complete',
        source_outer_sha256=OUTER_PIN,source_inventory_sha256=INVENTORY_PIN,
        declared_request_sha256=declared_pin,derived_request_sha256=pin,
        source_raw_sha256=served,raw_reports_served=232,stage_audit_comparisons=audits[0],
        every_stage_numeric_pin_lock_and_mapping_equal=True,fresh_reopen_equal=True,
        source_postrun_review_sha256=REVIEW_PIN,projection_payload_matches_v2=True,
        projection_payload_sha256=terminal['projection_sha256'],overhead_margin_seconds=margin,
        offline_worker_wall_seconds=elapsed,declared_overhead_seconds=request['resource']['envelope']['non_solver_seconds'],
        solver_calls=0,native_calibration_started=False,process_job_supervision_exercised=False,
        native_capture_overhead_measured=False,whole_task_resources_verified=False,
        formal_execution_ready=False,formal_result=False,
        script_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        worker_result_sha256=sha256((root/'worker_result.json').read_bytes()).hexdigest(),
        implementation_identity=job.implementation_identity())
    result_pin=job._write(base/'saved_worker_diagnostic.json',record)
    print(json.dumps(dict(diagnostic_sha256=result_pin,wall_seconds=elapsed,stage_audits=audits[0],solver_calls=0)),flush=True)


def _separate_output(base,native_root,old):
    for protected in (native_root,old):
        if base==protected or base.is_relative_to(protected) or protected.is_relative_to(base):
            raise ValueError('diagnostic must be separate from native and retained roots')


def _exact_inventory(root,members):
    current={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if current!=set(members):raise ValueError('retained run file inventory changed')


def _timing_gate(elapsed,limit):
    if type(elapsed) not in (int,float) or not isfinite(elapsed) or not 0<elapsed<limit:
        raise ValueError('offline worker exceeds declared non-solver budget')
    return limit-elapsed


def _terminal_gate(root,metas,expected_payload):
    database=root/'collector_non_authoritative/stages_non_authoritative/h1_chunk_journal.sqlite3'
    with sqlite3.connect(database.as_uri()+'?mode=ro&immutable=1',uri=True) as conn:
        rows=conn.execute('select metadata from events order by seq').fetchall()
    if len(rows)!=233:raise ValueError('complete stage and terminal inventory required')
    terminal=json.loads(rows[-1][0])
    if (terminal.get('kind')!='accepted_terminal' or terminal.get('stored_reports')!=232
            or terminal.get('canonical_locks')!=[m['lock_hex'] for m in metas]
            or terminal.get('projection_sha256')!=expected_payload):
        raise ValueError('complete physical projection differs from v2')
    return terminal


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();main(args.request,args.output)
