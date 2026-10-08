"""Local one-shot trust root for registry heads; reopening never grants execution."""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from . import scale_selector_controller as files
from . import normal_h1_chunk_journal as chunks

SCHEMA='h1_local_attempt_anchor_development_v1'


def implementation_identity():
    return sha256(chunks.base._bytes([SCHEMA,
        sha256(Path(__file__).read_bytes()).hexdigest(),
        sha256(Path(files.__file__).read_bytes()).hexdigest()])).hexdigest()


@dataclass(frozen=True)
class AnchorReceipt:
    anchor_identity: str
    sequence: int
    registry_head: str
    record_sha256: str


class DevelopmentH1AttemptAnchor:
    """Explicitly trusted local directory, not a hostile-rollback monotonic service.

    Immutable numbered files are fsynced and fresh-read before returning a receipt.
    Reopens audit only. The caller may additionally pin the final record hash.
    """
    def __init__(self,root,binding,*,max_records,create=False,expected_record_sha256=None):
        chunks._pin(binding)
        if type(create) is not bool or type(max_records) is not int or not 1<=max_records<=24:
            raise ValueError('bounded exact anchor declaration required')
        self._guard=chunks._Exclusive()
        self._closed=self._poisoned=False
        self._writable=create
        self._retained={}
        self._expected_count=None
        self._lease=files.local._Lease(root,create)
        self._header=dict(schema=SCHEMA,root=str(self._lease.root),binding=binding,
            max_records=max_records,implementation=implementation_identity())
        self.identity=sha256(chunks.base._bytes(self._header)).hexdigest()
        self._max_records=max_records
        try:
            if create:self._retained['header.json']=files._write(self._lease.root/'header.json',self._header)
            self._scan()
            for name in ['header.json',*[f'{i:03d}.json' for i in range(0 if self._latest is None else self._latest.sequence+1)]]:
                path=self._lease.root/name
                identity=files.local._file_identity(path)
                self._retained[name]=(identity,sha256(chunks.base._bytes(files._read(path,identity))).hexdigest())
            self._expected_count=0 if self._latest is None else self._latest.sequence+1
            if expected_record_sha256 is not None:
                chunks._pin(expected_record_sha256)
                if self._latest is None or self._latest.record_sha256!=expected_record_sha256:
                    raise ValueError('independent anchor record mismatch')
        except BaseException:
            self.close()
            raise

    def _scan(self):
        if self._closed or self._poisoned:raise ValueError('closed or unresolved anchor')
        self._lease.check()
        if implementation_identity()!=self._header['implementation']:raise ValueError('anchor implementation drift')
        names={p.name for p in self._lease.root.iterdir()}
        records=sorted(names-{'header.json','execution.lock'})
        if self._expected_count is not None and len(records)!=self._expected_count:
            raise ValueError('live anchor record count changed')
        if len(records)>self._max_records or records!=[f'{i:03d}.json' for i in range(len(records))]:
            raise ValueError('anchor record gap or unexpected file')
        for name,(identity,pin) in self._retained.items():
            value=files._read(self._lease.root/name,identity)
            if sha256(chunks.base._bytes(value)).hexdigest()!=pin:raise ValueError('retained anchor changed')
        if files._read(self._lease.root/'header.json')!=self._header:raise ValueError('anchor header mismatch')
        previous=self.identity
        head=None
        latest=None
        for index,name in enumerate(records):
            value=files._read(self._lease.root/name)
            if (set(value)!={'schema','anchor_identity','sequence','previous_record_sha256',
                    'previous_registry_head','registry_head','event_sha256'}
                    or value['schema']!=SCHEMA or value['anchor_identity']!=self.identity
                    or type(value['sequence']) is not int or value['sequence']!=index
                    or value['previous_record_sha256']!=previous or value['previous_registry_head']!=head):
                raise ValueError('anchor record chain mismatch')
            chunks._pin(value['registry_head'])
            chunks._pin(value['event_sha256'])
            previous=sha256(chunks.base._bytes(value)).hexdigest()
            head=value['registry_head']
            latest=AnchorReceipt(self.identity,index,head,previous)
        self._lease.check()
        self._latest=latest
        return latest

    def inspect(self):
        with self._guard:
            try:return self._scan()
            except BaseException:
                self._poisoned=True
                raise

    def advance(self,registry_head,event_sha256,*,expected_previous):
        with self._guard:
            try:
                prior=self._scan()
                if not self._writable:raise ValueError('reopened anchor cannot advance')
                if (None if prior is None else prior.registry_head)!=expected_previous:
                    raise ValueError('anchor predecessor mismatch')
                chunks._pin(registry_head)
                chunks._pin(event_sha256)
                seq=0 if prior is None else prior.sequence+1
                if seq>=self._max_records:raise ValueError('anchor budget exhausted')
                value=dict(schema=SCHEMA,anchor_identity=self.identity,sequence=seq,
                    previous_record_sha256=self.identity if prior is None else prior.record_sha256,
                    previous_registry_head=expected_previous,registry_head=registry_head,event_sha256=event_sha256)
                name=f'{seq:03d}.json'
                self._retained[name]=files._write(self._lease.root/name,value)
                self._expected_count=seq+1
                result=self._scan()
                if result!=AnchorReceipt(self.identity,seq,registry_head,self._retained[name][1]):
                    raise ValueError('fresh anchor receipt mismatch')
                return result
            except BaseException:
                self._poisoned=True
                raise

    def confirm(self,receipt):
        if type(receipt) is not AnchorReceipt or self.inspect()!=receipt:
            raise ValueError('exact fresh anchor receipt required')

    def close(self):
        with self._guard:
            if not self._closed:
                self._lease.close()
                self._closed=True

    __copy__=chunks.DevelopmentH1ChunkJournal.__copy__
    __deepcopy__=chunks.DevelopmentH1ChunkJournal.__deepcopy__
    __reduce_ex__=chunks.DevelopmentH1ChunkJournal.__reduce_ex__
