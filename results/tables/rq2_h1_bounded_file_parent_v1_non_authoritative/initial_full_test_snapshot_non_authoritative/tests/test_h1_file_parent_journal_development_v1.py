from hashlib import sha256

import pytest

from experiments import h1_file_parent_journal_development_v1 as api


def create(root,events=2):
    budget=api.chunks.ChunkContentBudget(events,2*api.CONTENT_CAP,events*2*api.CONTENT_CAP)
    return api.Journal(root,budget,binding_identity='a'*64,create=True)


def reopen(j,head):
    return api.Journal(j.root,j._budget,binding_identity='a'*64,expected_head=head)


def append(j,payload=b'source'):
    return j.append({'kind':'intent'},(payload,) if payload else (),expected_head=j.head,
        declared_payload_bytes=len(payload),expected_payload_sha256=sha256(payload).hexdigest())


def test_roundtrip_and_readonly(tmp_path):
    j=create(tmp_path/'journal_non_authoritative')
    first=append(j)
    final=append(j,b'')
    assert j.event_head(1,expected_head=final.head)==first.head
    assert b''.join(j.iter_event(1,expected_head=final.head))==b'source'
    assert j.event_metadata(2,expected_head=final.head)==b'{"kind":"intent"}'
    with pytest.raises(ValueError,match='held'):reopen(j,final.head)
    j.close()
    q=reopen(j,final.head)
    try:
        assert q.inspect()==final
        with pytest.raises(ValueError,match='writable'):append(q)
    finally:q.close()


@pytest.mark.parametrize('name',['metadata.bin','payload.bin','commit.json'])
@pytest.mark.parametrize('when',['partial','confirmation'])
def test_each_write_failure_retained_and_unanchored(tmp_path,monkeypatch,name,when):
    j=create(tmp_path/'journal_non_authoritative')
    old=j.head
    original=api.io.write_new
    def failed(path,raw):
        if path.name==name:
            if when=='partial':
                with path.open('xb') as f:f.write(raw[:1])
            else:original(path,raw)
            raise OSError('injected write window')
        return original(path,raw)
    monkeypatch.setattr(api.io,'write_new',failed)
    with pytest.raises(OSError):append(j)
    assert (j.root/'001'/name).exists()
    with pytest.raises(ValueError,match='poisoned'):j.inspect()
    j.close()
    with pytest.raises(ValueError):reopen(j,old)


def test_complete_unanchored_tail_rejected(tmp_path):
    j=create(tmp_path/'journal_non_authoritative')
    old=j.head
    append(j);j.close()
    with pytest.raises(ValueError,match='head differs'):reopen(j,old)


@pytest.mark.parametrize('fault',['payload','commit','extra','gap'])
def test_tampered_topology_or_bytes(tmp_path,fault):
    j=create(tmp_path/'journal_non_authoritative');head=append(j).head;j.close()
    if fault=='extra':(j.root/'001/extra').write_bytes(b'x')
    elif fault=='gap':(j.root/'001').rename(j.root/'002')
    else:(j.root/'001'/('payload.bin' if fault=='payload' else 'commit.json')).write_bytes(b'{}')
    with pytest.raises(ValueError):reopen(j,head)


def test_reentrant_payload_fails_without_new_event(tmp_path):
    j=create(tmp_path/'journal_non_authoritative')
    def payload():
        j.inspect()
        yield b'x'
    try:
        with pytest.raises(ValueError,match='already active'):
            j.append({},payload(),expected_head=j.head,declared_payload_bytes=1,
                     expected_payload_sha256=sha256(b'x').hexdigest())
        assert not (j.root/'001').exists()
    finally:j.close()


def test_live_same_bytes_replacement_rejected(tmp_path):
    j=create(tmp_path/'journal_non_authoritative');append(j)
    path=j.root/'001/metadata.bin'
    raw=path.read_bytes()
    path.rename(j.root/'001/saved_original.bin')
    path.write_bytes(raw)
    # Retain the displaced original outside the journal's exact topology.
    (j.root/'001/saved_original.bin').rename(tmp_path/'saved_original.bin')
    try:
        with pytest.raises(ValueError,match='replaced'):j.inspect()
    finally:j.close()


def test_full_384_event_capacity_and_385_rejection(tmp_path):
    j=create(tmp_path/'journal_non_authoritative',384)
    try:
        for _ in range(384):result=append(j,b'')
        assert result.events==384
        head=result.head
        files=[p for p in j.root.rglob('*') if p.is_file()]
        bound=api.storage_bound(384)
        assert len(files)==bound['files']
        assert sum(p.stat().st_size for p in files)<=bound['logical_bytes']
        with pytest.raises(ValueError,match='capacity'):append(j,b'')
        assert not (j.root/'385').exists()
    finally:j.close()
    q=reopen(j,head)
    try:assert q.inspect().events==384
    finally:q.close()
