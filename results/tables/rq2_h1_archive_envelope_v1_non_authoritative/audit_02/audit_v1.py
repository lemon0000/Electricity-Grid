"""Read accepted old bytes and declarations; never open an owner or source Reader."""
from base64 import b64decode
from hashlib import sha256
import inspect
import json
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
sys.path.insert(0,str(REPO))
from experiments import h1_owner_archive_budget_development_v1 as budget
from experiments import h1_cross_hour_owner_development_v2 as cross
from experiments import h1_phase_owner_development_v1 as owner
from experiments import h1_phase_ticket_holder_development_v1 as holder
from experiments import h1_raw_ingress_development_v1 as ingress
from src.rq2_joint_deliverability_boundary_v1 import prefix_handoff

CASE=Path('D:/h1_outage_connected_03_non_authoritative/test_three_hour_connected_outa0')
PRIOR={
    'rq2_h1_target_business_cost_v1_non_authoritative':
        ('bd17b1ce1594b08dc0c4046240e1ed4d31dfdee83235190a5b351caf18463af8',69),
    'rq2_h1_constructor_window_fault_v1_non_authoritative':
        ('925f9370ad00f72d8cb0a3af7abdca26dcb8eb168f346ba9ac24b763232fcb20',208),
}


def pin(path):return sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def write_checked(path,value):
    raw=(json.dumps(value,indent=2,ensure_ascii=True,allow_nan=False)+'\n').encode('utf-8')
    if path.exists():assert path.read_bytes()==raw,('retain old result; use a successor',str(path))
    else:
        with path.open('xb') as stream:stream.write(raw)


def main():
    bindings={}
    prior=[]
    for name,(expected,count) in PRIOR.items():
        path=HERE.parent/name/'final_verification.json'
        assert pin(path)==expected
        value=load(path)
        assert len(value['bindings'])==count
        assert all(pin(p)==v for p,v in value['bindings'].items())
        bindings.update(value['bindings']);bindings[str(path)]=expected
        prior.append(dict(path=str(path),sha256=expected,bindings_verified=count))
    post_path=HERE.parent/'rq2_h1_cross_hour_outage_v1_non_authoritative/connected_03_postcheck.json'
    expected=load(post_path)['diagnostic_case_files_sha256']
    actual={str(p):pin(p) for p in CASE.rglob('*') if p.is_file()}
    assert actual==expected and len(actual)==465
    owned=load(CASE/'external_preclose_checkpoint.json')['saved_files_sha256']
    assert len(owned)==444 and all(actual[name]==value for name,value in owned.items())
    bindings.update(actual);bindings[str(post_path)]=pin(post_path)
    source=cross.batch_source
    assert source is __import__('experiments.h1_phase_exact_source_batch_development_v1',fromlist=['x'])
    assert source.io.encode is ingress.encode and owner.encode is prefix_handoff._encoded
    source_cap=source.prior.historical.binding.CAP
    assert source_cap==131072
    # Bind both the producer cap and the consuming owner's independent cap/canonical check.
    assert 'len(audit) > prior.historical.binding.CAP' in inspect.getsource(source._materialize)
    validation=inspect.getsource(cross._validate_batch)
    assert 'len(current.source_projection_audit_payload)>prior.historical.binding.CAP' in validation
    assert 'encoded(audit)!=current.source_projection_audit_payload' in validation
    files=[Path(__file__),Path(budget.__file__),Path(owner.__file__),Path(holder.__file__),
        Path(cross.__file__),Path(source.__file__),Path(source.prior.__file__),
        Path(source.prior.historical.__file__),Path(source.prior.historical.binding.__file__),
        Path(ingress.__file__),Path(prefix_handoff.__file__),Path(holder.old.__file__),
        REPO/'tests/test_h1_owner_archive_budget_development_v1.py',HERE/'design_and_budget.md']
    files+=list((HERE/'unit_01').iterdir())
    bindings.update({str(path):pin(path) for path in files})
    db_path=CASE/'owner_non_authoritative/owner.sqlite'
    # No owner constructor, mutating PRAGMA, producer, historical replay or solver.
    db=sqlite3.connect(db_path.resolve().as_uri()+'?mode=ro',uri=True,timeout=0)
    try:
        assert db.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
        header_raw=db.execute('SELECT body FROM header WHERE id=1').fetchone()[0]
        header=json.loads(header_raw);assert owner.encode(header)==header_raw
        schema=db.execute("SELECT sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall()
        assert sorted(sql for (sql,) in schema)==sorted(owner.TABLES)
        rows=db.execute('SELECT seq,predecessor,kind,body,head FROM events ORDER BY seq').fetchall()
        pages={name:db.execute('PRAGMA '+name).fetchone()[0]
            for name in ('page_size','page_count','freelist_count')}
        journal_mode=db.execute('PRAGMA journal_mode').fetchone()[0]
    finally:db.close()
    assert len(rows)==9
    manifest=header['storage']['storage']['manifest']
    holder_binding=header['storage']['holder'];root=Path(holder_binding['root'])
    holder_header_raw=(root/'header.json').read_bytes();hh=json.loads(holder_header_raw)
    assert holder.encode(hh)==holder_header_raw and len(holder_header_raw)<=4096
    assert pin(root/'header.json')==holder_binding['genesis']
    assert (root/'execution.lock').read_bytes()==b'0'
    assert set(p.name for p in root.iterdir())=={'header.json','execution.lock'}|{f'{i:06d}.json' for i in range(1,10)}
    assert all(hh[k]==holder_binding[k] for k in ('max_tickets','max_ticket_bytes','max_total_ticket_bytes'))
    genesis=owner.digest(['owner_genesis',sha256(header_raw).hexdigest()])
    heads=(genesis,genesis);previous=sha256(holder_header_raw).hexdigest()
    row_facts=[];intent_facts=[];ticket_bytes=0;encoded_bodies=0
    limits=manifest['replay_limits']
    lane_ids=tuple(c['lane_id'] for c in manifest['lanes'])
    mock=SimpleNamespace(lanes=tuple(SimpleNamespace(lane_id=k) for k in lane_ids),
        replay_limits=SimpleNamespace(**limits))
    for sequence,pred,kind,raw,head in rows:
        value=json.loads(raw);assert owner.encode(value)==raw
        ticket=holder.old.AppendTicket(genesis,sequence,heads,kind,raw)
        assert ticket.event==(sequence,pred,kind,raw,head)
        wrapper=(root/f'{sequence:06d}.json').read_bytes()
        assert wrapper==holder.encode(dict(sequence=sequence,previous=previous,ticket=holder._ticket_payload(ticket)))
        b64=budget.base64_bytes(len(raw))
        assert len(wrapper)==budget.holder_metadata_bytes(sequence,kind)+b64
        ticket_bytes+=len(wrapper);encoded_bodies+=b64
        previous=sha256(wrapper).hexdigest();heads=ticket.after_heads
        row_facts.append(dict(sequence=sequence,kind=kind,body_bytes=len(raw),holder_file_bytes=len(wrapper)))
        if kind=='intent':
            audit=value['source_audit'];source_raw=ingress.encode(audit)
            assert type(audit) is dict and len(owner.encode(audit))-1<=len(source_raw)<=source_cap
            packed=value['records']
            reference=tuple(b64decode(x,validate=True) for x in packed['reference'])
            actual_records={k:tuple(b64decode(x,validate=True) for x in values)
                for k,values in packed['actual'].items()}
            assert owner._pack_records(mock,reference,actual_records)==packed
            groups={'reference':reference,**actual_records}
            intent_facts.append(dict(hour=value['hour'],body_bytes=len(raw),
                source_ascii_bytes=len(source_raw),source_owner_object_bytes=len(owner.encode(audit))-1,
                group_record_counts={k:len(v) for k,v in groups.items()},
                group_raw_bytes={k:sum(map(len,v)) for k,v in groups.items()}))
    raw_total=sum(len(r[3]) for r in rows)
    logical=budget.holder_logical_bound(**{k:hh[k] for k in
        ('max_tickets','max_ticket_bytes','max_total_ticket_bytes')})
    holder_total=ticket_bytes+len(holder_header_raw)+1
    assert holder_total<=logical['logical_content_bytes_bound']
    assert raw_total<=manifest['max_archive_bytes'] and max(len(r[3]) for r in rows)<=manifest['max_event_bytes']
    envelope=budget.intent_logical_bound(lane_ids=lane_ids,source_audit_ascii_cap=source_cap,
        **{k:limits[k] for k in ('max_stages','max_record_bytes','max_total_bytes')})
    # Pack-only adversarial bytes illustrate where capacity is checked. They are
    # deliberately NOT a valid numerical report or an attainable H1 transition.
    packed=owner._pack_records(mock,(b'x'*limits['max_record_bytes'],),{k:() for k in lane_ids})
    padded=owner.encode(dict(hour=191,terminal=budget.PIN,key=budget.PIN,source_audit={},
        records=packed,alternate=False,before_heads=(budget.PIN,budget.PIN)))
    assert len(padded)>manifest['max_event_bytes']
    scenarios={}
    for hours in (168,192):
        events=budget.successful_event_counts(hours)
        n=events['events_after_terminal'];b=manifest['max_event_bytes']
        conditional_holder=budget.holder_logical_bound(max_tickets=n,max_ticket_bytes=b,max_total_ticket_bytes=n*b)
        scenarios[str(hours)]=dict(success_W0_counts=events,current_toy_event_cap=manifest['max_events'],
            current_toy_event_cap_sufficient=False,
            illustrative_parameters_only=dict(max_tickets=n,max_ticket_bytes=b,max_total_ticket_bytes=n*b),
            hypothetical_raw_body_content_cap=n*b,hypothetical_holder=conditional_holder,
            hypothetical_raw_plus_holder_content_bytes=n*b+conditional_holder['logical_content_bytes_bound'],
            actual_configuration_changed=False,admission=False)
    assert sqlite3.sqlite_version==header['storage']['storage']['sqlite_version']
    # A final full-name/hash check proves this read-only audit left old bytes intact.
    assert {str(p):pin(p) for p in CASE.rglob('*') if p.is_file()}==expected
    assert all(pin(p)==value for p,value in bindings.items())
    result=dict(status='DRAFT_NONAUTHORITATIVE',scope='logical_archive_envelopes_and_readonly_old_case',
        prior_evidence_verified=prior,saved_case_files=465,saved_owned_files=444,
        old_case_names_and_sha256_unchanged=True,sqlite_open_mode='ro',
        sqlite=dict(runtime_version=sqlite3.sqlite_version,header_recorded_version=header['storage']['storage']['sqlite_version'],
            file_bytes=db_path.stat().st_size,raw_body_bytes=raw_total,header_bytes=len(header_raw),
            pages=pages,journal_mode=journal_mode,physical_upper_bound_bytes=None,
            page_difference_is_not_scaling_formula=True,body_cap_is_not_disk_quota=True),
        old_manifest=manifest,old_rows=row_facts,old_intents=intent_facts,
        old_holder=dict(header_limits={k:hh[k] for k in ('max_tickets','max_ticket_bytes','max_total_ticket_bytes')},
            ticket_files=len(rows),ticket_file_bytes=ticket_bytes,base64_body_bytes=encoded_bodies,
            header_bytes=len(holder_header_raw),lock_bytes=1,all_file_content_bytes=holder_total,
            all_file_content_excluding_lock=ticket_bytes+len(holder_header_raw),declared_logical_bound=logical,
            exact_wrapper_and_database_prefix_correspondence=True),
        intent_declared_envelope=envelope,
        accepted_intent_body_bytes_bound=min(manifest['max_event_bytes'],envelope['intent_body_bytes_bound']),
        declared_envelope_is_pre_owner_not_accepted_body_bound=True,
        source_cap=dict(bytes=source_cap,producer_and_consumer_cap_checks_bound=True,
            source_encoder='raw_ingress.encode: ensure_ascii=True, compact, no newline',
            owner_encoder='prefix_handoff._encoded: ensure_ascii=False, compact, one outer newline',
            relation='For accepted canonical JSON objects encodable by owner, owner object bytes <= source ASCII bytes',
            source_encoders_are_identical=False,owner_utf8_encoding_success_required=True),
        pack_only_example=dict(raw_bytes=limits['max_record_bytes'],packed_by_original=True,
            intent_bytes=len(padded),event_cap_bytes=manifest['max_event_bytes'],
            exceeds_event_cap=True,numerical_report_validated=False,scientific_counterexample=False,
            establishes_only='packer limits alone do not guarantee later event-cap acceptance'),
        scenarios=scenarios,alternate_witness_limit_enforced=False,
        failure_states=dict(missing_or_failed_next_after_H_successful_hours='For 1<=H<192: 3H+2W DB rows, pending attempt, no terminal',
            after_next_intent_before_outcome='For 1<=H<192: 3H+1+2W DB rows, pending intent, no terminal',
            bootstrap_failure='Before first outcome: 0 or 1 DB row, no later-hour attempt; holder may lead by one',
            prepared_holder_tail='DB prefix <= holder prefix <= DB prefix+1, both independently capped',
            add_extra_ticket_above_both_declared_caps=False,crash_recovery_or_writer_rehydration_proved=False),
        exclusions=['SQLite pages/header/record/index/freelist/journal physical upper bound',
            'filesystem allocation/directory metadata', 'normal and selector external archives',
            'external holder-head retention/checkpoint/report/scratch/reserve/concurrency',
            'unbounded alternate attempts beyond existing archive exhaustion',
            'wall/RSS and terminal/reopen/failure-tail resource evidence'],
        total_wall_admission_seconds=None,peak_rss_admission_bytes=None,total_storage_admission_bytes=None,
        bindings=bindings,overall_performance_review_complete=False,resource_admission=False,
        formal_execution_ready=False,full_192_hour_execution_verified=False,
        source_successor_adopted=False,new_normal_jobs=0,real_native_calls=0,formal_result=False)
    write_checked(HERE/'archive_audit_v1.json',result)
    print(json.dumps(dict(case_files=465,owned_files=444,raw_bytes=raw_total,holder_bytes=holder_total,
        intent_envelope=envelope['intent_body_bytes_bound'],bindings=len(bindings),
        audit_sha256=pin(HERE/'archive_audit_v1.json'))))


if __name__=='__main__':main()
