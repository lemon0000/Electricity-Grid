"""Zero-solver successor replay of the retained v1 calibration prefix."""
from dataclasses import asdict
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_full_job_v2 as job
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_incremental_archive_v2 as archive


def main(request_path, output):
    base = Path(output).resolve()
    if not base.name.endswith('_non_authoritative'):
        raise ValueError('explicit non-authoritative output directory required')
    base.mkdir(parents=True, exist_ok=False)
    old = ROOT/'results/tables/rq2_normal_h1_origin_calibration_v1_non_authoritative'
    manifest, _ = job._read(ROOT/'configs/rq2_normal_h1_calibration_v1.OUTER.SHA256SUMS.json',
        '289f9b147afa7a00b1abc4ff5dc10da09b57e0920d57be0215c352ff4648438d')
    inventory, _ = job._read(ROOT/'results/tables/rq2_normal_h1_full_job_v1_non_authoritative/calibration_v1.postrun_inventory.json',
        '37d55a780e7d92936a9e6d80082428293f703ed96714ba16a0b4809a5ff375ef')
    def preservation():
        for name, pin in manifest['members'].items():
            if sha256((ROOT/name).read_bytes()).hexdigest() != pin:
                raise ValueError('legacy sealed member drift: '+name)
        for name, item in inventory['files'].items():
            raw=(old/name).read_bytes()
            if len(raw)!=item['bytes'] or sha256(raw).hexdigest()!=item['sha256']:
                raise ValueError('legacy run member drift: '+name)
    preservation()
    old_result, old_result_pin = job._read(old/'worker_result.json',inventory['files']['worker_result.json']['sha256'])
    if old_result['summary']['status']!='rejected' or old_result['summary']['stored_reports']!=26:
        raise ValueError('expected retained rejected prefix required')
    request, request_pin = job._read(request_path)
    work, _, _, limits, _, _ = job._validate_request(request)
    database = old/'collector_non_authoritative/stages_non_authoritative/h1_chunk_journal.sqlite3'
    database_pin = sha256(database.read_bytes()).hexdigest()
    output = base/'prefix_archive_non_authoritative'
    with archive.replay.guard.solver_calls_forbidden():
        packet = job._packet(request)
        connection = sqlite3.connect(database.as_uri()+'?mode=ro&immutable=1',uri=True)
        owner = None
        try:
            connection.execute('PRAGMA query_only=ON')
            owner = archive.DevelopmentH1IncrementalArchive(output,packet,work.specification,limits,
                parent_intent_head=sha256((old/'request.json').read_bytes()).hexdigest(),
                source_lineage_identity=request['source_identity'],create=True)
            pins=[]
            for seq, metadata, size in connection.execute('SELECT seq,metadata,payload_bytes FROM events ORDER BY seq'):
                metadata=json.loads(metadata)
                raw=b''.join(row[0] for row in connection.execute(
                    'SELECT payload FROM chunks WHERE event_seq=? ORDER BY chunk_index',(seq,)))
                pin=sha256(raw).hexdigest()
                if len(raw)!=size or pin!=metadata['raw_sha256']:
                    raise ValueError('retained raw drift')
                state=owner.record_report(raw,expected_head=owner.head)
                pins.append(pin)
            final=owner.inspect()
            if final.stored_reports!=26 or final.status!='collecting' or final.projection is not None:
                raise ValueError('exact incomplete 26-candidate successor prefix required')
            head=owner.head
            last=json.loads(owner._journal.event_metadata(26,expected_head=head))
            mapping=last['generation_mapping']
            if (last['kind']!='stage_accepted' or last['raw_sha256']!=pins[-1]
                    or mapping['candidate_accepted'] is not True or not mapping['changes']
                    or mapping['rule_identity']!=archive.replay.generation_projection.implementation_identity()):
                raise ValueError('last successor stage lacks reconstructed authorized mapping')
        finally:
            if owner is not None:owner.close()
            connection.close()
        reopened=archive.DevelopmentH1IncrementalArchive(output,packet,work.specification,limits,
            parent_intent_head=sha256((old/'request.json').read_bytes()).hexdigest(),
            source_lineage_identity=request['source_identity'],expected_head=head)
        try:
            if reopened.inspect()!=final:
                raise ValueError('fresh successor archive differs from retained result')
        finally:reopened.close()
    if sha256(database.read_bytes()).hexdigest()!=database_pin:
        raise ValueError('legacy source database changed during diagnostic')
    preservation()
    record=dict(schema='h1_generation_projection_v2_retained_prefix_diagnostic',
        source_database_sha256=database_pin,source_raw_sha256=pins,stored_reports=26,
        candidate_stage_count=26,complete_projection=False,solver_calls=0,fresh_reopen_equal=True,
        old_run_status=old_result['summary']['status'],old_worker_result_sha256=old_result_pin,
        request_sha256=request_pin,legacy_members_preserved=len(manifest['members']),
        legacy_run_members_preserved=len(inventory['files']),last_stage_mapping=mapping,
        implementation_identity=archive.base.implementation_identity(),inspection=asdict(final),
        script_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),formal_execution_ready=False,formal_result=False)
    pin=job._write(base/'prefix_diagnostic.json',record)
    print(json.dumps(dict(sha256=pin,candidate_stage_count=26,complete_projection=False,solver_calls=0)))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    main(args.request,args.output)
