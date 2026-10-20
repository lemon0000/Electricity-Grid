"""Post-stop saved-prefix replay; never an owner/holder reopen or adoption."""
from base64 import b64decode
from contextlib import closing
from dataclasses import replace
from fractions import Fraction as Q
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import stat
import time

import pytest

from tests import h1_cross_hour_outage_fixture_v1 as case
from tests.test_h1_cross_hour_owner_development_v1 import static_code_identities, real

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
m,prior=case.m,case.prior


def load(path):return json.loads(path.read_bytes())
def pin(path):return sha256(path.read_bytes()).hexdigest()
def files(root):return {str(p):pin(p) for p in root.rglob('*') if p.is_file()}


def test_frozen_three_hour_prefix_detached_replay(tmp_path,monkeypatch,real,static_code_identities):
    started=time.perf_counter()
    snapshot=load(HERE/'connected_02_closed_snapshot.json');root=Path(snapshot['case'])
    assert snapshot['captured_after_monitor_stop'] is True and snapshot['before_original_reopen_not_available'] is True
    assert snapshot['formal_result'] is False and len(snapshot['files_sha256'])==462
    assert root==Path('D:/h1_outage_connected_02_non_authoritative/test_three_hour_connected_outa0')
    assert files(root)==snapshot['files_sha256']
    terminal=load(HERE/'connected_02/terminal.json')
    assert terminal['exit_code']==15 and terminal['reason']=='no_progress'
    assert terminal['source_unchanged'] and terminal['observed_processes_absent']
    assert terminal['monitor_errors']==[] and terminal['cleanup_events']
    assert all(v['action']=='kill_owned' and v['reason']=='no_progress' for v in terminal['cleanup_events'])
    assert not (root/'outage_chain_result.json').exists()
    assert not (root/'static_identity_bookends.json').exists() and not (HERE/'connected_02/junit.xml').exists()
    for filename,expected in load(HERE/'connected_02/request.json')['sources_sha256'].items():
        assert pin(Path(filename))==expected
    # Reinstall the exact synthetic source recipe while forbidding any rewrite
    # of the already frozen source files. No controller or worker is created.
    mkdir,write=Path.mkdir,Path.write_bytes
    expected={root/'upstream/SHA256SUMS':b'synthetic-current-source\n',root/'source.yaml':b'{}'}
    with pytest.MonkeyPatch.context() as temporary:
        def same_mkdir(path,*args,**kwargs):
            if path==root/'upstream':assert path.is_dir();return None
            if path==root or root in path.parents:raise AssertionError('frozen root mkdir forbidden')
            return mkdir(path,*args,**kwargs)
        def same_write(path,data):
            if path in expected:assert path.read_bytes()==data==expected[path];return len(data)
            if path==root or root in path.parents:raise AssertionError('frozen root write forbidden')
            return write(path,data)
        temporary.setattr(Path,'mkdir',same_mkdir);temporary.setattr(Path,'write_bytes',same_write)
        env=prior.supplied.__wrapped__(root,monkeypatch)
    prior.environment.__wrapped__(env,monkeypatch)
    case.install_case(env,monkeypatch);prior.no_solver.__wrapped__(monkeypatch)
    # Reuse the same explicit synthetic binding seams as the original case;
    # resolve the real symbolic inventory before installing the toy source.
    resolver,ordinal=real;binding_module=m.normal.binding
    node=resolver.resolve('training_ub',ordinal)
    monkeypatch.setattr(binding_module,'open_manifest',lambda:resolver)
    monkeypatch.setattr(binding_module,'precheck',lambda *args,**kwargs:node)
    monkeypatch.setattr(binding_module,'prevalidate_enrollment',lambda *args,**kwargs:dict(test_only_synthetic_source=True))
    database=root/'owner_non_authoritative/owner.sqlite'
    with closing(sqlite3.connect(database.as_uri()+'?mode=ro&immutable=1',uri=True)) as db:
        assert db.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
        raw_header=db.execute('SELECT body FROM header WHERE id=1').fetchone()[0]
        rows=db.execute('SELECT seq,predecessor,kind,body,head FROM events ORDER BY seq').fetchall()
    header=json.loads(raw_header);genesis=m.digest(['owner_genesis',sha256(raw_header).hexdigest()])
    previous=genesis
    for i,(seq,pred,kind,raw,head) in enumerate(rows,1):
        assert seq==i and pred==previous and m.encode(json.loads(raw))==raw
        assert head==m.digest([seq,pred,kind,sha256(raw).hexdigest()]);previous=head
    assert [r[2] for r in rows]==['intent','outcome','attempt','intent','outcome','attempt','intent','outcome','attempt']
    holder=root/'holder_non_authoritative';holder_header=(holder/'header.json').read_bytes()
    holder_meta=json.loads(holder_header);previous=sha256(holder_header).hexdigest()
    assert m.encode(holder_meta)==holder_header
    assert holder_meta==dict(schema=m.saved.tickets.SCHEMA,role='prepared_ticket_holder',root=str(holder),
        owner_root=str(root/'owner_non_authoritative'),max_tickets=32,max_ticket_bytes=1048576,
        max_total_ticket_bytes=33554432,nonce=holder_meta['nonce'],
        implementation=m.saved.tickets.implementation_identity(),formal_result=False)
    assert len(holder_meta['nonce'])==32 and int(holder_meta['nonce'],16)>=0
    assert holder_meta['max_tickets']>=len(rows)==9
    before=(genesis,genesis);total=0
    for row in rows:
        seq,pred,kind,raw,head=row;path=holder/f'{seq:06d}.json'
        info=path.lstat();assert stat.S_ISREG(info.st_mode) and info.st_nlink==1
        assert path.stat().st_size<=2*holder_meta['max_ticket_bytes']+4096
        payload=path.read_bytes();value=json.loads(payload);ticket=value['ticket']
        assert set(value)=={'sequence','previous','ticket'}
        assert type(value['sequence']) is int and type(ticket['sequence']) is int
        assert m.encode(value)==payload and value['sequence']==seq and value['previous']==previous
        assert ticket==dict(store_identity=genesis,sequence=seq,before_heads=list(before),kind=kind,body=ticket['body'])
        assert b64decode(ticket['body'],validate=True)==raw and pred==before[1]
        assert len(raw)<=holder_meta['max_ticket_bytes'];total+=len(raw)
        before=(head if kind=='outcome' else before[0],head);previous=sha256(payload).hexdigest()
    assert {p.name for p in holder.iterdir()}=={'header.json','execution.lock'}|{f'{i:06d}.json' for i in range(1,10)}
    assert total<=holder_meta['max_total_ticket_bytes']
    cfg=replace(prior.manifest(),accounting_period_id='synthetic-three-hour-outage-single-episode')
    storage=header['storage']['storage'];assert json.loads(m.encode(cfg))==storage['manifest']
    binding=m.saved.SourceBinding(**storage['binding'])
    intents=[json.loads(r[3]) for r in rows if r[2]=='intent']
    outcomes=[json.loads(r[3]) for r in rows if r[2]=='outcome']
    terminals={body['hour']:body['terminal'] for body in intents}
    batch=m.batch_source.prepare_many(binding.root,expected_binding_sha256=binding.binding_sha256,
        expected_terminals=terminals,expected_registry_identity=binding.registry_identity,selected_hours=(0,1,2))
    m._validate_batch(batch,binding,terminals,(0,1,2),m.batch_source.implementation_identity())
    state=m.saved._initial(cfg,batch.currents[0]);states=[];stages=0
    for hour,(intent,outcome) in enumerate(zip(intents,outcomes,strict=True)):
        current=batch.currents[hour]
        assert json.loads(current.source_projection_audit_payload)==intent['source_audit']
        assert m._request(cfg,state,current)==intent['key']==outcome['key']
        records=m.saved._unpack_records(cfg,intent['records'])
        stages+=len(records['reference'])+sum(map(len,records['actual'].values()))
        after,projection=m._transition(cfg,state,current,records)
        assert json.loads(projection)==outcome['projection'] and sha256(projection).hexdigest()==outcome['projection_sha256']
        states.append(after);state=after
    assert state.hour==3 and stages==34
    assert sum(d['paired_committed'] for o in outcomes for d in o['projection']['lanes'])==7
    lanes=dict(state.lanes)
    assert lanes['cfe'].halted and lanes['cfe'].reason=='actual_unresolved'
    assert lanes['cfe'].business==dict(states[0].lanes)['cfe'].business
    assert lanes['cfe'].actual==dict(states[0].lanes)['cfe'].actual
    debts={k:lane.business.cursor.execution.tracks[0][1].ledger.debt for k,lane in lanes.items()}
    assert debts==dict(cfe=Q(1,50),joint=Q(29,1000),network=Q(7,20_000_000_000_000))
    assert json.loads(rows[-1][3])['hour']==3 and m.saved._assessment(state).needs_next_hour
    assert len(batch.observations)==2 and sum(v['completed_hours'] for v in batch.observations)==6
    for h in range(3):
        job=load(root/f'normal_non_authoritative/job_{h:03d}_non_authoritative/observation.json')
        assert job['exit_code']==0 and job['whole_job_quiescent']
    assert files(root)==snapshot['files_sha256']
    result=dict(status='DRAFT_NONAUTHORITATIVE',seconds=time.perf_counter()-started,
        source_snapshot_sha256=pin(HERE/'connected_02_closed_snapshot.json'),all_462_saved_bytes_unchanged=True,
        original_attempt_exit_code=15,original_attempt_reason='no_progress',original_authenticated_reopen=False,
        independent_retained_heads=False,original_reopen_before_after_equality_verified=False,
        original_static_bookend_verified=False,original_RAM_scientific_equality_verified=False,
        owner_or_holder_constructor_called=False,live_continuation_or_adoption_authorized=False,
        detached_three_hour_projection_bytes_equal=True,paired_lane_hours=7,saved_selector_records=34,
        final_scientific=state.scientific,debts={k:str(v) for k,v in debts.items()},batch_observations=batch.observations,
        new_normal_jobs=0,new_selector_calls=0,real_native_calls=0,formal_result=False)
    (tmp_path/'detached_saved_replay.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
