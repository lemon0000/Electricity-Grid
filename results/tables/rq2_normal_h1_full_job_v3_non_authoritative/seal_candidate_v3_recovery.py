"""Mechanical seal completion after pinned pre-commit size failure; no retries."""
from hashlib import sha256
import argparse
import json
from math import isfinite
import os
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_calibration_gate_v3 as gate
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_full_job_v3 as job


def main(evidence_sha256):
    base=Path(__file__).resolve().parent
    rel=lambda p:p.relative_to(ROOT).as_posix()
    pin=lambda p:sha256(p.read_bytes()).hexdigest()
    prior=ROOT/'configs/rq2_normal_h1_calibration_v2.OUTER.SHA256SUMS.json'
    if pin(prior)!='79830ab6c1b31aaef41174544e472ef800674de1f76228793f30f6b87e4f6eba':
        raise ValueError('prior outer pin drift')
    old=json.loads(prior.read_bytes())
    for name,expected in old['members'].items():
        if pin(ROOT/name)!=expected:raise ValueError('old sealed drift: '+name)
    inventory=ROOT/'results/tables/rq2_normal_h1_full_job_v2_non_authoritative/calibration_v2.postrun_inventory.json'
    if pin(inventory)!='281ad90c2da8bdb2ff0a1031d94379f2887dc663f235c52619a1c75e25521fb4':
        raise ValueError('old run inventory drift')
    old_root=ROOT/'results/tables/rq2_normal_h1_origin_calibration_v2_non_authoritative'
    retained=json.loads(inventory.read_bytes())['members']
    if {p.relative_to(old_root).as_posix() for p in old_root.rglob('*') if p.is_file()}!=set(retained):
        raise ValueError('old run file-set drift')
    for name,item in retained.items():
        p=old_root/name
        if p.stat().st_size!=item['bytes'] or pin(p)!=item['sha256']:
            raise ValueError('old run byte drift')
    request_path=base/'review_candidate_anchor_non_authoritative/calibration_request.DRAFT.json'
    if pin(request_path)!='c31c3638695009c65c3e01e2990cbda9a71e5ff66f57c7f636ec88a7fb99fd6f':
        raise ValueError('final tested request drift')
    request=json.loads(request_path.read_bytes())
    job._validate_request(request)
    evidence_path=base/'development_checks_recovery.json'
    gate._pin(evidence_sha256)
    if pin(evidence_path)!=evidence_sha256:raise ValueError('independently pinned preseal evidence required')
    evidence=json.loads(evidence_path.read_bytes())
    if (evidence.get('schema')!='h1_replay_performance_v3_development_checks'
            or evidence.get('status')!='PRE_SEAL_AUDIT' or evidence.get('findings_closed') is not True
            or evidence.get('official_verdict') is not None
            or evidence.get('formal_result') is not False or evidence.get('formal_execution_ready') is not False
            or evidence.get('native_run_authorized') is not False or evidence.get('native_solver_calls')!=0
            or evidence.get('request_sha256')!=pin(request_path)):
        raise ValueError('independent preseal closure required')
    tests=base/'anchor_development_test_results.json'
    if pin(tests)!='dae424c4ee2325036cea3836000bf8aa240c1884dfb7677d8364c29c72153d7b':
        raise ValueError('independently retained test evidence pin drift')
    if evidence.get('test_results_sha256')!=pin(tests):raise ValueError('preseal test evidence binding drift')
    tested=json.loads(tests.read_bytes())
    for name,expected in tested['source_sha256'].items():
        if pin(ROOT/name)!=expected:raise ValueError('tested source drift: '+name)
    diagnostic_root=base/'anchor_saved_worker_non_authoritative'
    diagnostic=diagnostic_root/'saved_worker_diagnostic.json'
    measured=json.loads(diagnostic.read_bytes())
    old_db=old_root/'collector_non_authoritative/stages_non_authoritative/h1_chunk_journal.sqlite3'
    with sqlite3.connect(old_db.as_uri()+'?mode=ro&immutable=1',uri=True) as connection:
        raw_pins=[json.loads(row[0])['raw_sha256'] for row in
            connection.execute('SELECT metadata FROM events ORDER BY seq')]
    if (pin(diagnostic)!=evidence['diagnostic_sha256']
            or measured.get('schema')!='h1_v3_saved_worker_performance_diagnostic'
            or measured.get('status')!='development_complete'
            or measured.get('raw_reports_served')!=232 or measured.get('solver_calls')!=0
            or type(measured.get('stage_audit_comparisons')) is not int
            or measured['stage_audit_comparisons']!=6*232
            or measured.get('every_stage_numeric_pin_lock_and_mapping_equal') is not True
            or measured.get('projection_payload_matches_v2') is not True
            or measured.get('declared_request_sha256')!=pin(request_path)
            or measured.get('derived_request_sha256')!=pin(diagnostic_root/'saved_worker_non_authoritative/request.json')
            or measured.get('implementation_identity')!=job.implementation_identity()
            or measured.get('script_sha256')!=pin(ROOT/'experiments/verify_rq2_normal_h1_generation_projection_v3.py')
            or measured.get('worker_result_sha256')!=pin(diagnostic_root/'saved_worker_non_authoritative/worker_result.json')
            or measured.get('source_outer_sha256')!=pin(prior)
            or measured.get('source_inventory_sha256')!=pin(inventory)
            or measured.get('source_postrun_review_sha256')!='9c034035f67bc8d891d966d19b5fd6e5f90ea8443c58949e19e9c93273c16cf2'
            or measured.get('fresh_reopen_equal') is not True
            or measured.get('projection_payload_sha256')!='034d14eb5728732790177a2f76af7fa552d9a7dad56ecfbfaf43d217eb7b2cc9'
            or type(measured.get('offline_worker_wall_seconds')) not in (int,float)
            or not isfinite(measured['offline_worker_wall_seconds'])
            or not 0<measured['offline_worker_wall_seconds']<2440
            or measured.get('declared_overhead_seconds')!=2440
            or measured.get('overhead_margin_seconds')!=2440-measured['offline_worker_wall_seconds']
            or len(raw_pins)!=232 or measured.get('source_raw_sha256')!=raw_pins
            or any(measured.get(k) is not False for k in ('native_calibration_started',
                'process_job_supervision_exercised','native_capture_overhead_measured',
                'whole_task_resources_verified','formal_execution_ready','formal_result'))):
        raise ValueError('complete saved-worker performance evidence required')
    for digest in measured['source_raw_sha256']:gate._pin(digest)
    review=inventory.parent/'calibration_v2.postrun_review.json'
    if pin(review)!=measured['source_postrun_review_sha256']:raise ValueError('old review pin drift')
    stem=ROOT/'configs/rq2_normal_h1_calibration_v3'
    config=Path(str(stem)+'.json');lease=Path(str(stem)+'.LEASE.json')
    inner=Path(str(stem)+'.SHA256SUMS.json');outer=Path(str(stem)+'.OUTER.SHA256SUMS.json')
    pending=Path(str(outer)+'.pending')
    claim=base/'calibration_v3.consume.json'
    for p in (inner,outer,pending,claim,Path(request['root'])):
        if p.exists():raise ValueError('exclusive new publication/root required: '+str(p))
    retained_leaves={config:'c31c3638695009c65c3e01e2990cbda9a71e5ff66f57c7f636ec88a7fb99fd6f',
        lease:'cd5fcf4c10b07ec04c2052bbda54157f6cccd454175e846c01c95eba6faab8e2'}
    for p,digest in retained_leaves.items():
        if pin(p)!=digest:raise ValueError('retained production leaf drift')
    expected_lease=dict(schema=gate.SCHEMA,request_sha256=pin(request_path),
        root=request['root'],claim_path=rel(claim),one_shot=True)
    if config.read_bytes()!=gate._bytes(request) or lease.read_bytes()!=gate._bytes(expected_lease):
        raise ValueError('retained production leaf content drift')
    paths={ROOT/name for name in old['members']}
    paths.update(ROOT/name for name in gate.required_code_members())
    paths.update(old_root/name for name in retained)
    paths.update(p for p in diagnostic_root.rglob('*') if p.is_file())
    # Retain the completed over-budget development attempt and its exact source
    # snapshot as history, distinct from the successful admission evidence.
    rejection_path=base/'saved_worker_budget_rejection.json'
    if pin(rejection_path)!='3f6c2a92ba30a04c13233c29b3ba2f992ac4e6738d9b9dc64125876288a69acd':
        raise ValueError('historical budget rejection pin drift')
    rejection=json.loads(rejection_path.read_bytes())
    rejected_root=base/'verified_saved_worker_non_authoritative'
    if {p.relative_to(rejected_root).as_posix() for p in rejected_root.rglob('*') if p.is_file()}!=set(rejection['inventory']):
        raise ValueError('historical diagnostic file-set drift')
    for name,item in rejection['inventory'].items():
        p=rejected_root/name
        if p.stat().st_size!=item['bytes'] or pin(p)!=item['sha256']:
            raise ValueError('historical diagnostic byte drift')
        paths.add(p)
    snapshot=base/'pre_anchor_source_snapshot_non_authoritative'
    historical_pins={
        base/'mechanical_seal_failure.json':'dcc0481264895ac1e630d9af42a3085fd35d92743ebfdcc9e9dfa378cf38660f',
        base/'seal_candidate_v3.py':'83d1153c6e230a89d16ca8cc4549daf406de5820e8f3d81cc079b16cde9c1e63',
        base/'development_checks.json':'0e7790d8e37976008488ff638761b3bce0ba7800d420128d8dfded05778d1eda',

        base/'preseal_root_verification.json':'a15944347811028f8698dc3e0b7bf704363c1b300a5a05c7b5952ea7d1ece739',
        base/'source_diff_from_prior.txt':'035e53e95435f54515af20c8af152a14156c5d22ef05457f1b10904c8a0ec62c',
        base/'development_test_results.json':'564a2ec1590783eab236cb3f935bdfbebd23e8ef8e64cf2a11aa520eba8864cf',
        base/'final_development_test_results.json':'c826426bcf5e883b7d9fc7e4adb4551f9a8a2786d717c9256f2018fe13b098b6',
        snapshot/'source_pins.json':'299c7709835898eaf63b5c26977d5b2db979076525b1e6da0947d6b86ea1b13d',
        base/'budget_rejection_payload_check.json':'836680e9547268a368365127eea84596e8880c829839326362b0d96e5ab1af5d',
        base/'retained_anchor_scan_profile.json':'7791cf241ec8a87142e9a9523590ed6aa78980055718cd655ba329e8424387f7',
        base/'collector_declaration_profile.json':'9171666b0b7635e8c59d66a09a5d7bd75b62c9604e922121e486b7f328b9ec4e'}
    for p,digest in historical_pins.items():
        if pin(p)!=digest:raise ValueError('independently retained history pin drift')
    snapshot_members=json.loads((snapshot/'source_pins.json').read_bytes())
    if {p.relative_to(snapshot).as_posix() for p in snapshot.rglob('*') if p.is_file()}!=set(snapshot_members)|{'source_pins.json'}:
        raise ValueError('historical source snapshot file-set drift')
    for name,digest in snapshot_members.items():
        p=snapshot/name
        if (type(name) is not str or Path(name).is_absolute() or '..' in Path(name).parts
                or not p.resolve().is_relative_to(snapshot.resolve())
                or p.relative_to(snapshot).as_posix()!=name):
            raise ValueError('canonical relative snapshot member required')
        if pin(p)!=digest:raise ValueError('historical source snapshot drift')
        paths.add(p)
    paths.update([rejection_path,snapshot/'source_pins.json',base/'budget_rejection_payload_check.json',
        base/'retained_anchor_scan_profile.json',base/'collector_declaration_profile.json'])
    paths.update([prior,inventory,request_path,tests,evidence_path,Path(__file__).resolve(),
        ROOT/'docs/model_spec/rq2_normal_h1_replay_performance_v3.md',
        base/'development_test_results.json',base/'final_development_test_results.json',
        base/'source_diff_from_prior.txt',
        base/'preseal_root_verification.json',
        inventory.parent/'calibration_v2.postrun_review.json'])
    paths.update(historical_pins)
    # All checks above precede any new production write. Exclusive write + fsync/readback.
    # A pre-rename mechanical failure retains every leaf and requires manual
    # examination; this helper never overwrites leaves or retries publication.
    request_pin=pin(config)
    lease_pin=pin(lease)
    paths.update((config,lease))
    members={rel(p):pin(p) for p in sorted(paths)}
    inner_value=dict(schema=gate.SCHEMA,files=dict(members),
        source_closure=list(gate.required_code_members()))
    inner_raw=gate._bytes(inner_value)
    inner_pin=sha256(inner_raw).hexdigest()
    members[rel(inner)]=inner_pin
    value=dict(schema=gate.SCHEMA,state='SEALED_READY_FOR_INDEPENDENT_REVIEW',
        request_path=rel(config),request_sha256=request_pin,lease_path=rel(lease),lease_sha256=lease_pin,
        claim_path=rel(claim),members=members,preseal_evidence_path=rel(evidence_path),
        preseal_evidence_sha256=pin(evidence_path),inner_path=rel(inner),inner_sha256=inner_pin)
    # Size both manifests against the existing manifest reader BEFORE any write.
    outer_raw=gate._bytes(value)
    if len(inner_raw)>gate.LIMIT or len(outer_raw)>gate.LIMIT:
        raise ValueError('bounded sealed manifest required')
    if any(pin(p)!=digest for p,digest in retained_leaves.items()):
        raise ValueError('retained production leaf drift before completion')
    if job.files._write(inner,inner_value)!=inner_pin:
        raise ValueError('inner manifest readback pin drift')
    outer_pin=job.files._write(pending,value)
    gate.verify_package(pending,outer_pin)
    # Windows rename refuses an existing destination. This is the commitment point.
    os.rename(pending,outer)
    gate.verify_package(outer,outer_pin)
    print(json.dumps(dict(outer=rel(outer),sha256=outer_pin,members=len(members),
        state='SEALED_READY_FOR_INDEPENDENT_REVIEW',native_run_authorized=False)),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-sha256',required=True)
    main(parser.parse_args().evidence_sha256)
