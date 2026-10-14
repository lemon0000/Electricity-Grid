"""Read-only, externally pinned historical parent prefix; suffix is not evidence."""
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import re
import stat

from experiments import h1_parent_snapshot_development_v1 as prior

io,journal,anchor,chunks=prior.io,prior.journal,prior.anchor,prior.chunks
bounded,source,binding,replay=prior.bounded,prior.source,prior.binding,prior.replay
SCHEMA='h1_historical_parent_prefix_development_v1'


def implementation_identity():
    return io.digest(io.encode([SCHEMA,prior.implementation_identity(),io.digest(Path(__file__).read_bytes())]))


def _inventory(root,base,*,pattern,low,high,directories):
    names=bounded.prior.hour_api._names(root,len(base)+high-low+1)
    if not base<=names:raise ValueError('historical prefix base inventory missing')
    indices=set()
    for name in names-base:
        match=re.fullmatch(pattern,name)
        if match is None or not low<=int(match[1])<=high:
            raise ValueError('unexpected or unbounded historical suffix name')
        path=chunks.base.local._path(root/name)
        info=path.stat(follow_symlinks=False)
        if not (stat.S_ISDIR(info.st_mode) if directories else stat.S_ISREG(info.st_mode)):
            raise ValueError('historical prefix/suffix entry type differs')
        indices.add(int(match[1]))
    return indices


class PrefixJournal(prior.JournalSnapshot):
    def __init__(self,*args,prefix_events,**kwargs):
        if type(prefix_events) is not int or prefix_events<2 or prefix_events%2:
            raise ValueError('complete positive hour prefix required')
        self._prefix_events=prefix_events
        super().__init__(*args,**kwargs)

    def _scan(self,*,candidate_head=None):
        if candidate_head is not None:raise ValueError('historical journal is read only')
        self._check();n=self._prefix_events
        def inventory():
            indices=_inventory(self.root,{'header.json','execution.lock'},pattern=r'(\d{3})',
                low=1,high=self._budget.max_events,directories=True)
            if not set(range(1,n+1))<=indices:raise ValueError('historical event prefix missing')
        inventory();previous=self.identity;total=payload_total=payload_count=0;views=[];heads=[]
        for seq in range(1,n+1):
            directory=self.root/f'{seq:03d}'
            if bounded.prior.hour_api._names(directory,3)!={'metadata.bin','payload.bin','commit.json'}:
                raise ValueError('incomplete historical event')
            values=[]
            for name,cap in (('metadata.bin',journal.CONTENT_CAP),('payload.bin',journal.CONTENT_CAP),('commit.json',io.META_CAP)):
                path=directory/name;raw,stamp=io.read_stable(path,cap)
                if path in self._retained and self._retained[path]!=stamp:
                    raise ValueError('retained historical event changed')
                values.append(raw);views.append((path,cap,stamp,io.digest(raw)))
            raw,payload,commit=values
            decoded=bounded.json.loads(raw)
            if type(decoded) is not dict or io.encode(decoded)!=raw:raise ValueError('canonical event required')
            total+=len(raw)+len(payload);payload_total+=len(payload);payload_count+=bool(payload)
            if len(raw)+len(payload)>self._budget.max_event_bytes or total>self._budget.max_total_bytes:
                raise ValueError('historical content budget exceeded')
            expected=dict(schema=journal.SCHEMA,sequence=seq,previous=previous,
                metadata_sha256=io.digest(raw),payload_sha256=io.digest(payload),metadata_bytes=len(raw),payload_bytes=len(payload))
            if io.encode(expected)!=commit:raise ValueError('historical event hash chain differs')
            previous=io.digest(commit);heads.append(previous)
        if previous!=self._head:raise ValueError('external historical journal head differs')
        for path,cap,stamp,pin in views:
            raw,fresh=io.read_stable(path,cap)
            if fresh!=stamp or io.digest(raw)!=pin:raise ValueError('historical event changed during read')
        inventory()
        for seq in range(1,n+1):
            if bounded.prior.hour_api._names(self.root/f'{seq:03d}',3)!={'metadata.bin','payload.bin','commit.json'}:
                raise ValueError('historical event topology changed')
        self._check();self._retained={p:s for p,c,s,h in views}
        return chunks.ChunkInspection(self.identity,previous,n,total,payload_total,payload_count),heads


class PrefixAnchor:
    def __init__(self,root,binding_identity,*,max_records,prefix_events,expected_record_sha256):
        io.pin(binding_identity);io.pin(expected_record_sha256)
        if (type(max_records) is not int or not 3<=max_records<=anchor.MAX_RECORDS
                or type(prefix_events) is not int or not 2<=prefix_events<max_records or prefix_events%2):
            raise ValueError('bounded complete anchor prefix required')
        self._lease=prior.ReadView(root);self._retained={};self._max_records=max_records
        self._n=prefix_events;self._pin=expected_record_sha256;self._closed=False
        self._header=dict(schema=anchor.SCHEMA,root=str(self._lease.root),binding=binding_identity,
            max_records=max_records,implementation=anchor.implementation_identity())
        self.identity=io.digest(chunks.base._bytes(self._header))
        try:self.inspect()
        except BaseException:self.close();raise

    def inspect(self):
        if self._closed:raise ValueError('closed historical anchor')
        self._lease.check();root=self._lease.root;views=[];records=[]
        def inventory():
            indices=_inventory(root,{'header.json','execution.lock'},pattern=r'(\d{3})\.json',
                low=0,high=self._max_records-1,directories=False)
            if not set(range(self._n+1))<=indices:raise ValueError('historical anchor prefix missing')
        def read(name):
            p=root/name;raw,stamp=io.read_stable(p,anchor.MAX_RECORD_BYTES)
            if p in self._retained and self._retained[p]!=stamp:raise ValueError('historical anchor replaced or changed')
            value=bounded.json.loads(raw)
            if io.encode(value)!=raw:raise ValueError('canonical anchor record required')
            views.append((p,stamp,io.digest(raw)));return value,io.digest(raw)
        inventory();header,_=read('header.json')
        if header!=self._header or anchor.implementation_identity()!=self._header['implementation']:
            raise ValueError('historical anchor header/implementation differs')
        previous=self.identity;head=None;latest=None
        for i in range(self._n+1):
            value,pin=read(f'{i:03d}.json')
            if (set(value)!={'schema','anchor_identity','sequence','previous_record_sha256',
                            'previous_registry_head','registry_head','event_sha256'}
                    or value['schema']!=anchor.SCHEMA or value['anchor_identity']!=self.identity
                    or type(value['sequence']) is not int or value['sequence']!=i
                    or value['previous_record_sha256']!=previous or value['previous_registry_head']!=head):
                raise ValueError('historical anchor chain differs')
            io.pin(value['registry_head']);io.pin(value['event_sha256'])
            previous=pin;head=value['registry_head'];records.append(value)
            latest=anchor.FullAnchorReceipt(self.identity,i,head,pin)
        if latest.record_sha256!=self._pin:raise ValueError('external historical anchor pin differs')
        for p,stamp,pin in views:
            raw,fresh=io.read_stable(p,anchor.MAX_RECORD_BYTES)
            if fresh!=stamp or io.digest(raw)!=pin:raise ValueError('historical anchor changed during read')
        inventory();self._lease.check();self._retained={p:s for p,s,h in views};self.records=tuple(records)
        return latest

    def confirm(self,receipt):
        if type(receipt) is not anchor.FullAnchorReceipt or self.inspect()!=receipt:
            raise ValueError('historical anchor receipt differs')

    def advance(self,*args,**kwargs):raise ValueError('historical anchor is read only')
    def close(self):self._closed=True;self._lease.close()


class HistoricalSnapshot(bounded.SavedSourceParent):
    def __init__(self,declaration,*,completed_hours,expected_parent_identity,expected_anchor_record):
        io.pin(expected_parent_identity);io.pin(expected_anchor_record)
        if type(declaration) is not dict or io.digest(io.encode(declaration))!=expected_parent_identity:
            raise ValueError('external parent declaration pin differs')
        d=deepcopy(declaration)
        if (type(completed_hours) is not int or type(d['hours']) is not int
                or not 1<=completed_hours<=d['hours']<=192):raise ValueError('bounded historical progress required')
        self._prefix_hours=completed_hours;self.prefix_implementation=implementation_identity()
        self._origin=binding.H1SourceDeclaration(**d['origin']);self._origin.__post_init__()
        self._upstream_root=Path(d['upstream_root']).resolve(strict=True)
        self._config_path=Path(d['config_path']).resolve(strict=True);self._root=Path(d['root']).resolve(strict=True)
        self._network=binding.load_pinned_current(self._origin,self._upstream_root,config_path=self._config_path).network
        source._network(self._network)
        self._spec=prior.Rq2SolverSpec(**d['specification']);replay.native.capture.provenance.adapter.validate_spec(self._spec)
        self._limits=replay.H1HourReplayLimits(**d['limits']);self._limits.__post_init__()
        self._hours,self._dc_bus=d['hours'],d['dc_bus']
        if type(self._dc_bus) is not int or self._dc_bus not in {b.uid for b in self._network.data.buses}:
            raise ValueError('static DC bus differs')
        self._stages=1+len(self._network.data.generators)+sum(g.dispatch_mode=='committable' for g in self._network.data.generators)
        if self._stages>self._limits.max_stages:raise ValueError('complete stage inventory exceeds limits')
        self._guard=chunks._Exclusive();self._closed=self._poisoned=self._writable=False
        self._journal=self._anchor=self._root_lease=None
        self._declaration=self._declare();self.identity=io.digest(io.encode(self._declaration))
        if self._declaration!=d or self.identity!=expected_parent_identity:raise ValueError('rebuilt parent declaration differs')
        n=2*completed_hours
        try:
            self._root_lease=prior.ReadView(self._root)
            self._anchor=PrefixAnchor(self._root/'parent_anchor_non_authoritative',self.identity,
                max_records=2*self._hours+1,prefix_events=n,expected_record_sha256=expected_anchor_record)
            receipt=self._anchor.inspect()
            budget=chunks.ChunkContentBudget(2*self._hours,2*chunks.METADATA_BYTES,4*self._hours*chunks.METADATA_BYTES)
            self._journal=PrefixJournal(self._root/'parent_events_non_authoritative',budget,
                binding_identity=self.identity,expected_head=receipt.registry_head,prefix_events=n)
            state=self.inspect()
            if state.completed_hours!=completed_hours or state.attempted_hours!=completed_hours or state.status not in ('ready','complete'):
                raise ValueError('historical prefix must contain only complete accepted hours')
        except BaseException:self.close();raise

    def _check(self):
        if implementation_identity()!=self.prefix_implementation:raise ValueError('historical reader implementation drift')
        super()._check()
        indices=_inventory(self._root,{'execution.lock','parent_events_non_authoritative','parent_anchor_non_authoritative'},
            pattern=r'hour_(\d{3})_non_authoritative',low=0,high=self._hours-1,directories=True)
        if not set(range(self._prefix_hours))<=indices:raise ValueError('historical child prefix missing')
        records=self._anchor.records
        if (records[0]['registry_head']!=self._journal.identity or records[0]['event_sha256']!=io.digest(b'genesis')):
            raise ValueError('historical anchor genesis differs')
        for seq in range(1,2*self._prefix_hours+1):
            if (records[seq]['registry_head']!=self._journal.event_head(seq,expected_head=self._journal.head)
                    or records[seq]['event_sha256']!=io.digest(self._journal.event_metadata(seq,expected_head=self._journal.head))):
                raise ValueError('historical anchor and event linkage differs')

    def _append(self,*args,**kwargs):raise ValueError('historical parent is read only')
