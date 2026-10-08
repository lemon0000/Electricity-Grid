from hashlib import sha256
import sqlite3
import pytest
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_chunk_journal as api


def make(tmp_path,**kwargs):
    return api.DevelopmentH1ChunkJournal(tmp_path/'chunks_non_authoritative',
        kwargs.pop('budget',api.ChunkContentBudget(4,8*1024**2,16*1024**2)),binding_identity='1'*64,create=True,**kwargs)


def test_streaming_roundtrip_reopen_and_independent_head(tmp_path):
    store=make(tmp_path)
    genesis=store.head
    chunks=(b'a'*api.CHUNK_BYTES,b'b'*api.CHUNK_BYTES,b'c')
    result=store.append({'kind':'raw_evidence'},iter(chunks),expected_head=genesis,declared_payload_bytes=sum(map(len,chunks)),expected_payload_sha256=sha256(b''.join(chunks)).hexdigest())
    assert result.payload_bytes==2*api.CHUNK_BYTES+1 and result.chunks==3
    assert result.content_verified and not result.numerical_chain_verified and not result.formal_result
    assert store.event_metadata(1,expected_head=result.head)==b'{"kind":"raw_evidence"}'
    assert tuple(store.iter_event(1,expected_head=result.head))==chunks
    store.close()
    with pytest.raises(ValueError,match='head'):
        api.DevelopmentH1ChunkJournal(tmp_path/'chunks_non_authoritative',api.ChunkContentBudget(4,8*1024**2,16*1024**2),binding_identity='1'*64,expected_head=genesis)
    opened=api.DevelopmentH1ChunkJournal(tmp_path/'chunks_non_authoritative',api.ChunkContentBudget(4,8*1024**2,16*1024**2),binding_identity='1'*64,expected_head=result.head)
    try: assert opened.inspect()==result
    finally: opened.close()


def test_event_exceeds_simulated_single_blob_limit(tmp_path,monkeypatch):
    # Actual SQLite connection limit is lowered, not merely a mocked size check.
    original=api.DevelopmentH1ChunkJournal._connect
    def limited(self):
        connection=original(self)
        connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH,api.CHUNK_BYTES+4096)
        return connection
    monkeypatch.setattr(api.DevelopmentH1ChunkJournal,'_connect',limited)
    store=make(tmp_path)
    try:
        result=store.append({},(b'x'*api.CHUNK_BYTES for _ in range(3)),expected_head=store.head,declared_payload_bytes=3*api.CHUNK_BYTES,expected_payload_sha256=sha256(b'x'*(3*api.CHUNK_BYTES)).hexdigest())
        assert result.payload_bytes>api.CHUNK_BYTES+4096
        assert sum(map(len,store.iter_event(1,expected_head=store.head)))==3*api.CHUNK_BYTES
    finally: store.close()


@pytest.mark.parametrize('fault',['producer','oversize','mutable','budget','commit_before','commit_after'])
def test_atomic_failure_poison_and_retained_database(tmp_path,monkeypatch,fault):
    budget=api.ChunkContentBudget(4,100,400)
    store=make(tmp_path,budget=budget)
    old=store.head
    def chunks():
        yield b'first'
        if fault=='producer':raise RuntimeError('producer failed')
        yield b'x'*(api.CHUNK_BYTES+1) if fault=='oversize' else bytearray(b'x') if fault=='mutable' else b'x'*100 if fault=='budget' else b'last'
    commit=store._commit
    if fault.startswith('commit'):
        def failed(connection):
            if fault=='commit_after':commit(connection)
            raise RuntimeError('commit ambiguity')
        monkeypatch.setattr(store,'_commit',failed)
    with pytest.raises((RuntimeError,ValueError)):store.append({},chunks(),expected_head=old,declared_payload_bytes=9,expected_payload_sha256=sha256(b'firstlast').hexdigest())
    with pytest.raises(ValueError,match='unresolved'):store.inspect()
    with pytest.raises(ValueError,match='unresolved'):_=store.head
    store.close()
    connection=sqlite3.connect(tmp_path/'chunks_non_authoritative/h1_chunk_journal.sqlite3')
    try:
        events=connection.execute('SELECT count(*) FROM events').fetchone()[0]
        count=connection.execute('SELECT count(*) FROM chunks').fetchone()[0]
        assert (events,count)==((1,2) if fault=='commit_after' else (0,0))
    finally:connection.close()


@pytest.mark.parametrize('mutation',[
    "UPDATE chunks SET payload=x'00' WHERE chunk_index=0",
    "DELETE FROM chunks WHERE chunk_index=0",
    "UPDATE chunks SET chunk_index=8 WHERE chunk_index=0",
    "INSERT INTO chunks VALUES (9,0,x'01','bad','bad')",
    "UPDATE events SET payload_bytes=0",
    "UPDATE events SET predecessor='bad'",
    "UPDATE metadata SET header=x'00'",
])
def test_corruption_rejected_and_owner_poisoned(tmp_path,mutation):
    store=make(tmp_path)
    try:
        store.append({},iter([b'abc',b'def']),expected_head=store.head,declared_payload_bytes=6,expected_payload_sha256=sha256(b'abcdef').hexdigest())
        connection=sqlite3.connect(store._database)
        try:connection.execute(mutation);connection.commit()
        finally:connection.close()
        with pytest.raises(ValueError):store.inspect()
        with pytest.raises(ValueError,match='unresolved'):store.inspect()
    finally:store.close()


@pytest.mark.parametrize('budget',[(True,1,1),(1,True,1),(1,1,True),(385,1,1),(1,2,1),(1,1,2**63)])
def test_budget_exact_types_and_limits(budget):
    with pytest.raises(ValueError):api.ChunkContentBudget(*budget)


def test_metadata_only_and_total_budget(tmp_path):
    store=make(tmp_path,budget=api.ChunkContentBudget(4,3,3))
    try:
        first=store.append({},iter(()),expected_head=store.head,declared_payload_bytes=0,expected_payload_sha256=sha256(b'').hexdigest())
        assert first.content_bytes==2 and first.payload_bytes==0 and first.chunks==0
        with pytest.raises(ValueError,match='total budget'):store.append({},iter(()),expected_head=store.head,declared_payload_bytes=0,expected_payload_sha256=sha256(b'').hexdigest())
    finally:store.close()


import json
from dataclasses import asdict


def append_small(store,payload=b'abc',metadata=None,**kw):
    return store.append({} if metadata is None else metadata,iter([payload]) if payload else iter(()),
        expected_head=store.head,declared_payload_bytes=len(payload),expected_payload_sha256=sha256(payload).hexdigest(),**kw)


def test_independent_chunk_and_event_hash_oracle(tmp_path):
    store=make(tmp_path)
    try:
        before=store.head
        result=append_small(store)
        def digest(obj):return sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')).hexdigest()
        genesis=digest([api.SCHEMA,1,before,'chunks'])
        chunk=digest([api.SCHEMA,1,0,genesis,3,sha256(b'abc').hexdigest()])
        expected=digest([api.SCHEMA,1,before,sha256(b'{}').hexdigest(),3,1,sha256(b'abc').hexdigest(),chunk])
        assert result.head==expected
    finally:store.close()


@pytest.mark.parametrize('fault',['noop','fresh_readback'])
def test_successful_commit_must_have_fresh_verified_readback(tmp_path,monkeypatch,fault):
    store=make(tmp_path)
    if fault=='noop':monkeypatch.setattr(store,'_commit',lambda c:None)
    else:
        original=store._scan
        calls=[]
        def scan(c):
            calls.append(1)
            if len(calls)==2:raise ValueError('injected fresh readback failure')
            return original(c)
        monkeypatch.setattr(store,'_scan',scan)
    try:
        with pytest.raises(ValueError):append_small(store)
        assert store._poisoned
    finally:store.close()


@pytest.mark.parametrize('fault',['wrong_head','wrong_hash','short_stream','long_stream','bool_size','nonfinite_metadata'])
def test_independent_payload_declaration_and_head(tmp_path,fault):
    store=make(tmp_path)
    try:
        metadata={'x':float('nan')} if fault=='nonfinite_metadata' else {}
        with pytest.raises(ValueError):store.append(metadata,iter([b'abc']),
            expected_head='0'*64 if fault=='wrong_head' else store.head,
            declared_payload_bytes=True if fault=='bool_size' else 4 if fault=='short_stream' else 2 if fault=='long_stream' else 3,
            expected_payload_sha256='0'*64 if fault=='wrong_hash' else sha256(b'abc').hexdigest())
        connection=sqlite3.connect(store._database)
        try:assert connection.execute('SELECT count(*) FROM events').fetchone()==(0,)
        finally:connection.close()
    finally:store.close()


@pytest.mark.parametrize('mutation',[
    "UPDATE chunks SET chunk_chain='bad'",
    "UPDATE chunks SET payload_sha='bad'",
    "UPDATE events SET chunk_root='bad'",
    "UPDATE events SET head='bad'",
    "UPDATE events SET seq=4",
    "UPDATE events SET chunk_count=0",
])
def test_descriptor_chain_corruption(tmp_path,mutation):
    store=make(tmp_path)
    try:
        append_small(store)
        connection=sqlite3.connect(store._database)
        try:connection.execute(mutation);connection.commit()
        finally:connection.close()
        with pytest.raises(ValueError):store.inspect()
    finally:store.close()


def test_metadata_boundary_and_event_count(tmp_path):
    store=make(tmp_path,budget=api.ChunkContentBudget(1,api.METADATA_BYTES,api.METADATA_BYTES))
    try:
        # Canonical {"x":"..."} contributes exactly eight framing bytes.
        first=append_small(store,b'',{'x':'a'*(api.METADATA_BYTES-8)})
        assert first.content_bytes==api.METADATA_BYTES
        with pytest.raises(ValueError,match='count'):append_small(store,b'')
    finally:store.close()


def test_metadata_one_byte_over_boundary(tmp_path):
    store=make(tmp_path)
    try:
        with pytest.raises(ValueError,match='metadata'):append_small(store,b'',{'x':'a'*(api.METADATA_BYTES-7)})
    finally:store.close()


def test_changed_binding_or_budget_cannot_reopen(tmp_path):
    store=make(tmp_path)
    head=store.head
    store.close()
    for binding,budget in [('2'*64,api.ChunkContentBudget(4,8*1024**2,16*1024**2)),('1'*64,api.ChunkContentBudget(3,8*1024**2,16*1024**2))]:
        with pytest.raises(ValueError,match='header'):
            api.DevelopmentH1ChunkJournal(tmp_path/'chunks_non_authoritative',budget,binding_identity=binding,expected_head=head)


def test_stream_consumed_once_and_abandoned_reader_poisoned(tmp_path):
    store=make(tmp_path)
    class Once:
        def __init__(self):self.calls=0
        def __iter__(self):
            self.calls+=1
            assert self.calls==1
            yield b'ab'
            yield b'c'
    stream=Once()
    try:
        store.append({},stream,expected_head=store.head,declared_payload_bytes=3,expected_payload_sha256=sha256(b'abc').hexdigest())
        reader=store.iter_event(1,expected_head=store.head)
        assert next(reader)==b'ab'
        reader.close()
        assert store._poisoned
    finally:store.close()



def test_old_store_type_isolation(tmp_path):
    store=make(tmp_path)
    head=store.head
    store.close()
    with pytest.raises((ValueError,FileNotFoundError)):
        api.base.DevelopmentH1ProjectionStore(tmp_path/'chunks_non_authoritative',expected_head=head)
    old=api.base.DevelopmentH1ProjectionStore(tmp_path/'old_non_authoritative',create=True)
    old_head=old.head
    old.close()
    with pytest.raises((ValueError,FileNotFoundError)):
        api.DevelopmentH1ChunkJournal(tmp_path/'old_non_authoritative',api.ChunkContentBudget(1,100,100),binding_identity='1'*64,expected_head=old_head)


@pytest.mark.parametrize('mutation',[
    'PRAGMA application_id=1',
    'CREATE INDEX unexpected_idx ON events (head)',
    'CREATE TRIGGER unexpected_trigger AFTER INSERT ON events BEGIN SELECT 1; END',
])
def test_unexpected_database_schema_rejects(tmp_path,mutation):
    store=make(tmp_path)
    try:
        connection=sqlite3.connect(store._database)
        try:connection.execute(mutation);connection.commit()
        finally:connection.close()
        with pytest.raises(ValueError,match='schema'):store.inspect()
    finally:store.close()


def test_stream_underreported_size_stops_before_next_item(tmp_path):
    store=make(tmp_path)
    def chunks():
        yield b'abcd'
        pytest.fail('stream was consumed after declared length exhausted')
    try:
        with pytest.raises(ValueError,match='budget'):
            store.append({},chunks(),expected_head=store.head,declared_payload_bytes=3,expected_payload_sha256=sha256(b'abc').hexdigest())
    finally:store.close()



def test_reentrant_stream_and_live_reader_reject_without_deadlock(tmp_path):
    store=make(tmp_path)
    def chunks():
        with pytest.raises(ValueError,match='already active'):store.inspect()
        with pytest.raises(ValueError,match='already active'):_=store.head
        yield b'ab'
        yield b'c'
    try:
        store.append({},chunks(),expected_head=store.head,declared_payload_bytes=3,expected_payload_sha256=sha256(b'abc').hexdigest())
        stream=store.iter_event(1,expected_head=store.head)
        assert next(stream)==b'ab'
        with pytest.raises(ValueError,match='already active'):store.close()
        assert list(stream)==[b'c']
        assert store.inspect().events==1
    finally:store.close()
