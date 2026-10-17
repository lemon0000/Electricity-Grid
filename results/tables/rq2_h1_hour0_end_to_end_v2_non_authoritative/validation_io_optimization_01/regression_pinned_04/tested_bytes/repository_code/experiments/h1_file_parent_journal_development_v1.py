"""Bounded immutable parent event files; external anchor still owns acceptance.

No repair, resume, SQLite, numerical verdict or execution authority.
"""
from dataclasses import asdict
from pathlib import Path

from experiments import h1_attested_source_parent_development_v1 as parent

io, chunks = parent.io, parent.prior.chunks
SCHEMA = 'h1_file_parent_journal_development_v1'
CONTENT_CAP = 256*1024


def implementation_identity():
    return io.digest(io.encode([SCHEMA,parent.implementation_identity(),
        io.digest(Path(__file__).read_bytes())]))


def storage_bound(events):
    if type(events) is not int or not 1 <= events <= 384:
        raise ValueError('exact bounded event count required')
    return dict(logical_bytes=events*(2*CONTENT_CAP+io.META_CAP)+io.META_CAP+1,
        files=3*events+2,directories=events+1,
        filesystem_allocation_bound_proven=False,resource_admission=False)


class Journal:
    def __init__(self,root,budget,*,binding_identity,create=False,expected_head=None):
        if type(budget) is not chunks.ChunkContentBudget:
            raise ValueError('exact content budget required')
        budget.__post_init__()
        storage_bound(budget.max_events)
        if budget.max_event_bytes>2*CONTENT_CAP:
            raise ValueError('bounded parent event size required')
        io.pin(binding_identity)
        if type(create) is not bool or (create and expected_head is not None):
            raise ValueError('separate create/reopen authority required')
        if not create:io.pin(expected_head)
        self._guard=chunks._Exclusive()
        self._closed=self._poisoned=False
        self._writable=create
        self._budget=budget
        self._retained={}
        self._lease=chunks.base.local._Lease(root,create)
        self.root=self._lease.root
        try:
            self._header=dict(schema=SCHEMA,root=str(self.root),budget=asdict(budget),
                binding=binding_identity,implementation=implementation_identity())
            self.identity=io.digest(io.encode(self._header))
            self._head=self.identity if create else expected_head
            if create:io.write_metadata(self.root/'header.json',self._header)
            self._scan()
        except BaseException:
            self.close()
            raise

    def _check(self):
        if self._closed or self._poisoned:
            raise ValueError('closed or poisoned parent file journal')
        self._lease.check()
        if (implementation_identity()!=self._header['implementation']
                or io.read_stable(self.root/'header.json',io.META_CAP)[0]!=io.encode(self._header)):
            raise ValueError('parent file journal binding drift')

    def _scan(self, *, candidate_head=None):
        self._check()
        names=parent.hour_api._names(self.root,self._budget.max_events+2)
        records=names-{'header.json','execution.lock'}
        if records!={f'{i:03d}' for i in range(1,len(records)+1)}:
            raise ValueError('parent event gap or unexpected file')
        if names!=records|{'header.json','execution.lock'} or len(records)>self._budget.max_events:
            raise ValueError('parent journal inventory differs')
        previous=self.identity
        total=payload_total=payload_count=0
        views=[]
        heads=[]
        for seq in range(1,len(records)+1):
            directory=self.root/f'{seq:03d}'
            if parent.hour_api._names(directory,3)!={'metadata.bin','payload.bin','commit.json'}:
                raise ValueError('incomplete parent event')
            values=[]
            for name,cap in (('metadata.bin',CONTENT_CAP),('payload.bin',CONTENT_CAP),('commit.json',io.META_CAP)):
                p=directory/name
                raw,stamp=io.read_stable(p,cap)
                if p in self._retained and self._retained[p]!=stamp:
                    raise ValueError('retained parent event file replaced or changed')
                values.append(raw);views.append((p,cap,stamp,io.digest(raw)))
            raw,payload,commit=values
            decoded=parent.hour_api.json.loads(raw)
            if type(decoded) is not dict or io.encode(decoded)!=raw:
                raise ValueError('canonical parent event metadata required')
            total+=len(raw)+len(payload);payload_total+=len(payload)
            payload_count+=bool(payload)
            if len(raw)+len(payload)>self._budget.max_event_bytes or total>self._budget.max_total_bytes:
                raise ValueError('parent event content budget exceeded')
            descriptor=dict(schema=SCHEMA,sequence=seq,previous=previous,
                metadata_sha256=io.digest(raw),payload_sha256=io.digest(payload),
                metadata_bytes=len(raw),payload_bytes=len(payload))
            if io.encode(descriptor)!=commit:
                raise ValueError('parent event commitment differs')
            previous=io.digest(commit);heads.append(previous)
        if previous!=(self._head if candidate_head is None else candidate_head):
            raise ValueError('independent parent file head differs')
        # Check the complete views again after reading the entire prefix.
        for path,cap,stamp,pin in views:
            raw,fresh=io.read_stable(path,cap)
            if fresh!=stamp or io.digest(raw)!=pin:
                raise ValueError('parent event changed during scan')
        if parent.hour_api._names(self.root,self._budget.max_events+2)!=names:
            raise ValueError('parent journal topology changed')
        for seq in range(1,len(records)+1):
            if parent.hour_api._names(self.root/f'{seq:03d}',3)!={'metadata.bin','payload.bin','commit.json'}:
                raise ValueError('parent event topology changed')
        self._check()
        self._retained={path:stamp for path,cap,stamp,pin in views}
        return chunks.ChunkInspection(self.identity,previous,len(records),total,payload_total,payload_count),heads

    @property
    def head(self):
        with self._guard:
            self._check()
            return self._head

    def inspect(self):
        with self._guard:
            try:return self._scan()[0]
            except BaseException:
                self._poisoned=True
                raise

    def append(self,metadata,payload_chunks,*,expected_head,declared_payload_bytes,expected_payload_sha256):
        with self._guard:
            try:
                self._check()
                if not self._writable or expected_head!=self._head:
                    raise ValueError('writable exact parent predecessor required')
                io.pin(expected_payload_sha256)
                if type(metadata) is not dict or type(declared_payload_bytes) is not int or not 0<=declared_payload_bytes<=CONTENT_CAP:
                    raise ValueError('bounded exact parent event required')
                raw=io.encode(metadata)
                before=self._scan()[0]
                if (before.events>=self._budget.max_events or len(raw)>CONTENT_CAP
                        or len(raw)+declared_payload_bytes>self._budget.max_event_bytes
                        or before.content_bytes+len(raw)+declared_payload_bytes>self._budget.max_total_bytes):
                    raise ValueError('parent content capacity exhausted')
                payload=bytearray()
                for part in payload_chunks:
                    if type(part) is not bytes or not part or len(part)+len(payload)>declared_payload_bytes:
                        raise ValueError('bounded exact parent payload required')
                    payload.extend(part)
                payload=bytes(payload)
                if len(payload)!=declared_payload_bytes or io.digest(payload)!=expected_payload_sha256:
                    raise ValueError('declared parent payload differs')
                seq=before.events+1
                directory=self.root/f'{seq:03d}'
                directory.mkdir(exist_ok=False)
                io.write_new(directory/'metadata.bin',raw)
                io.write_new(directory/'payload.bin',payload)
                descriptor=dict(schema=SCHEMA,sequence=seq,previous=self._head,
                    metadata_sha256=io.digest(raw),payload_sha256=io.digest(payload),
                    metadata_bytes=len(raw),payload_bytes=len(payload))
                head=io.write_metadata(directory/'commit.json',descriptor)
                result=self._scan(candidate_head=head)[0]
                self._head=head
                return result
            except BaseException:
                self._poisoned=True
                raise

    def _event(self,seq,expected_head):
        if type(seq) is not int or seq<1 or expected_head!=self._head:
            raise ValueError('exact event sequence and external head required')
        inspection,heads=self._scan()
        if seq>inspection.events:raise ValueError('absent parent event')
        directory=self.root/f'{seq:03d}'
        raw=io.read_stable(directory/'metadata.bin',CONTENT_CAP)[0]
        payload=io.read_stable(directory/'payload.bin',CONTENT_CAP)[0]
        commit=io.read_stable(directory/'commit.json',io.META_CAP)[0]
        value=parent.hour_api.json.loads(commit)
        if (io.digest(commit)!=heads[seq-1] or value['metadata_sha256']!=io.digest(raw)
                or value['payload_sha256']!=io.digest(payload)):
            raise ValueError('event changed after scan')
        if self._scan()[0]!=inspection:raise ValueError('parent view changed after event read')
        return raw,payload,heads[seq-1]

    def _read(self,seq,expected_head,index):
        with self._guard:
            try:return self._event(seq,expected_head)[index]
            except BaseException:
                self._poisoned=True
                raise

    def event_metadata(self,seq,*,expected_head):return self._read(seq,expected_head,0)
    def event_head(self,seq,*,expected_head):return self._read(seq,expected_head,2)
    def iter_event(self,seq,*,expected_head):
        # One bounded immutable payload; no live file handle escapes the owner.
        payload=self._read(seq,expected_head,1)
        return iter((payload,)) if payload else iter(())

    def close(self):
        with self._guard:
            if not self._closed:
                self._closed=True
                self._lease.close()
