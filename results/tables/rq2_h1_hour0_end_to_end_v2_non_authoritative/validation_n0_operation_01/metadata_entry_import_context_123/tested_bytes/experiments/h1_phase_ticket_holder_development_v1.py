"""Phase-event prepared-ticket log with explicit full-branch logical capacity.

Development only. No producer, automatic retry, or crash-durability certificate.
The external holder head is a required reopen input, not inferred from disk.
"""
from base64 import b64decode,b64encode
from functools import wraps
from hashlib import sha256
import json
import os
import stat
from pathlib import Path
from threading import Lock,get_ident
from uuid import uuid4

from experiments import h1_persistent_owner_development_v1 as old

SCHEMA='h1_phase_ticket_holder_development_v1'
KINDS=('attempt','intent','outcome','witness','episode_terminal')
local,encode=old.local,old.encode


def implementation_identity():
    return sha256(Path(__file__).read_bytes()).hexdigest()


def _pin(value):
    if type(value) is not str or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('exact SHA256 required')
    return value


def _read(path,cap):
    identity=local._file_identity(path)
    with path.open('rb') as f:
        before=os.fstat(f.fileno())
        raw=f.read(cap+1);after=os.fstat(f.fileno())
    fingerprint=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_mode,s.st_nlink)
    if (len(raw)>cap or fingerprint(before)!=fingerprint(after)
            or not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or (before.st_dev,before.st_ino)!=identity
            or local._file_identity(path)!=identity):raise ValueError('bounded stable holder file required')
    return raw,identity


def _new(path,raw):
    with path.open('xb') as f:
        f.write(raw);f.flush();os.fsync(f.fileno())
    if _read(path,len(raw))[0]!=raw:raise ValueError('holder write readback differs')


def _ticket(value,cap):
    if type(value) is not old.AppendTicket:raise ValueError('exact prepared ticket required')
    if (type(value.sequence) is not int or value.sequence<1 or value.kind not in KINDS
            or type(value.before_heads) is not tuple or len(value.before_heads)!=2
            or type(value.body) is not bytes or len(value.body)>cap
            or encode(json.loads(value.body))!=value.body):raise ValueError('canonical bounded ticket required')
    for pin in (value.store_identity,*value.before_heads):_pin(pin)
    return value


def _ticket_payload(ticket):
    return dict(store_identity=ticket.store_identity,sequence=ticket.sequence,
        before_heads=ticket.before_heads,kind=ticket.kind,body=b64encode(ticket.body).decode('ascii'))


def _holder_serial(method):
    @wraps(method)
    def call(self,*a,**kw):
        if not self._guard.acquire(False):raise ValueError('ticket holder operation active')
        try:return method(self,*a,**kw)
        finally:self._guard.release()
    return call


class TicketHolder:
    """One owner's external append-only log, pinned across process restarts.

    A failed/unknown write poisons this handle. Reopen requires an independently
    retained exact head; an unknown suffix is never automatically adopted.
    """
    def __init__(self,root,*,owner_root,max_tickets,max_ticket_bytes,max_total_ticket_bytes,create=False,expected_head=None,retain_head=None):
        if type(create) is not bool or any(type(x) is not int or x<=0 for x in (max_tickets,max_ticket_bytes,max_total_ticket_bytes)):
            raise ValueError('explicit positive holder bounds required')
        if create and expected_head is not None:raise ValueError('create cannot adopt holder head')
        if max_tickets>999999:raise ValueError('six-digit bounded holder ordinal required')
        if retain_head is not None and not callable(retain_head):raise ValueError('external head retention callback required')
        if not create:_pin(expected_head)
        self._guard=Lock();self._pid=os.getpid();self._thread=get_ident();self.closed=self.poisoned=False
        self.lease=local._Lease(root,create);self._lease_object=self.lease;self.root=self.lease.root
        self.owner_root=local._path(owner_root)
        self.max_tickets,self.max_ticket_bytes=max_tickets,max_ticket_bytes
        self.max_total_ticket_bytes=max_total_ticket_bytes
        self.retain_head=retain_head
        self.cap=2*max_ticket_bytes+4096
        self._implementation=implementation_identity()
        self._seen={}
        try:
            if self.root==self.owner_root or self.root in self.owner_root.parents or self.owner_root in self.root.parents:
                raise ValueError('separate non-nested owner and ticket holder roots required')
            path=self.root/'header.json'
            if create:
                _new(path,encode(dict(schema=SCHEMA,role='prepared_ticket_holder',root=str(self.root),
                    owner_root=str(self.owner_root),max_tickets=max_tickets,max_ticket_bytes=max_ticket_bytes,max_total_ticket_bytes=max_total_ticket_bytes,
                    nonce=uuid4().hex,implementation=self._implementation,formal_result=False)))
            self.header,self.header_identity=_read(path,4096)
            value=json.loads(self.header)
            if (encode(value)!=self.header or type(value.get('nonce')) is not str or len(value['nonce'])!=32
                    or value!=dict(schema=SCHEMA,role='prepared_ticket_holder',root=str(self.root),
                        owner_root=str(self.owner_root),max_tickets=max_tickets,max_ticket_bytes=max_ticket_bytes,max_total_ticket_bytes=max_total_ticket_bytes,
                        nonce=value['nonce'],implementation=self._implementation,formal_result=False)):
                raise ValueError('ticket holder header differs')
            self.genesis=sha256(self.header).hexdigest()
            self.head=self.genesis if create else expected_head
            self.binding=self._live_binding()
            self._binding_bytes=encode(self.binding)
            self._snapshot()
        except BaseException:
            self.close();raise

    def _live_binding(self):
        return dict(root=str(self.root),owner_root=str(self.owner_root),genesis=self.genesis,
            directory_identity=self.lease.root_identity,header_identity=self.header_identity,
            lock_identity=self.lease.file_identity,max_tickets=self.max_tickets,
            max_ticket_bytes=self.max_ticket_bytes,max_total_ticket_bytes=self.max_total_ticket_bytes,implementation=self._implementation)

    def _check(self):
        if self.closed or self.poisoned or os.getpid()!=self._pid or get_ident()!=self._thread:
            raise ValueError('live same-process/thread ticket holder required')
        if self.lease is not self._lease_object:raise ValueError('ticket holder lease instance changed')
        self.lease.check()
        if (implementation_identity()!=self._implementation or encode(self.binding)!=self._binding_bytes
                or encode(self._live_binding())!=self._binding_bytes
                or self.cap!=2*self.max_ticket_bytes+4096
                or _read(self.root/'header.json',4096)!=(self.header,self.header_identity)
                or sha256(self.header).hexdigest()!=self.genesis):raise ValueError('ticket holder identity changed')

    def _snapshot(self,*,expected_head=None):
        self._check();names=set()
        for path in self.root.iterdir():
            names.add(path.name)
            if len(names)>self.max_tickets+2:raise ValueError('ticket holder namespace bound')
        if not {'header.json','execution.lock'}<=names:raise ValueError('ticket holder base namespace missing')
        count=len(names)-2
        if names!={'header.json','execution.lock'}|{f'{i:06d}.json' for i in range(1,count+1)}:
            raise ValueError('ticket holder namespace gap or unexpected entry')
        previous=self.genesis;tickets=[];views={};contents={};store=None;total_body_bytes=0
        for i in range(1,count+1):
            path=self.root/f'{i:06d}.json';raw,identity=_read(path,self.cap)
            if identity in views.values():raise ValueError('ticket holder inode alias')
            views[path.name]=identity
            contents[path.name]=(raw,identity)
            value=json.loads(raw)
            if set(value)!={'sequence','previous','ticket'} or value['sequence']!=i or value['previous']!=previous:
                raise ValueError('ticket holder chain differs')
            t=value['ticket']
            if set(t)!={'store_identity','sequence','before_heads','kind','body'}:raise ValueError('ticket schema differs')
            ticket=_ticket(old.AppendTicket(t['store_identity'],t['sequence'],tuple(t['before_heads']),t['kind'],
                b64decode(t['body'],validate=True)),self.max_ticket_bytes)
            if (encode(dict(sequence=i,previous=previous,ticket=_ticket_payload(ticket)))!=raw or ticket.sequence!=i
                    or i>1 and (ticket.store_identity!=store or ticket.before_heads!=tickets[-1].after_heads)):
                raise ValueError('ticket owner chain differs')
            if i==1 and ticket.before_heads!=(ticket.store_identity,ticket.store_identity):raise ValueError('ticket genesis differs')
            store=ticket.store_identity;tickets.append(ticket);previous=sha256(raw).hexdigest()
            total_body_bytes+=len(ticket.body)
            if total_body_bytes>self.max_total_ticket_bytes:
                raise ValueError('ticket holder total body bound')
        if any(views.get(k)!=v for k,v in self._seen.items()):raise ValueError('retained holder file removed or replaced')
        if previous!=(self.head if expected_head is None else expected_head):raise ValueError('external holder head differs; recovery required')
        final_names=set()
        for path in self.root.iterdir():
            final_names.add(path.name)
            if len(final_names)>self.max_tickets+2:raise ValueError('ticket holder namespace bound')
        if final_names!=names:raise ValueError('ticket holder namespace changed')
        if any(_read(self.root/name,self.cap)!=view for name,view in contents.items()):
            raise ValueError('ticket holder changed during snapshot')
        self._seen.update(views);self._check()
        return tuple(tickets)

    @_holder_serial
    def inspect(self):return self._snapshot()

    @_holder_serial
    def retain(self,ticket):
        _ticket(ticket,self.max_ticket_bytes);tickets=self._snapshot()
        if (ticket.sequence!=len(tickets)+1 or len(tickets)>=self.max_tickets
                or tickets and (ticket.store_identity!=tickets[0].store_identity or ticket.before_heads!=tickets[-1].after_heads)
                or not tickets and ticket.before_heads!=(ticket.store_identity,ticket.store_identity)
                or sum(len(t.body) for t in tickets)+len(ticket.body)>self.max_total_ticket_bytes):
            raise ValueError('ticket already prepared or outside holder chain/bounds')
        raw=encode(dict(sequence=len(tickets)+1,previous=self.head,ticket=_ticket_payload(ticket)))
        if len(raw)>self.cap:raise ValueError('ticket holder record bound')
        after=sha256(raw).hexdigest()
        try:
            if self.retain_head is None or self.retain_head(self.genesis,self.head,after,len(tickets)+1)!=after:
                raise ValueError('independent prospective holder head retention required')
            if self._snapshot()!=tickets:raise ValueError('holder changed during prospective head handoff')
            _new(self.root/f'{len(tickets)+1:06d}.json',raw)
            if self._snapshot(expected_head=after)!=tickets+(ticket,):raise ValueError('ticket holder append differs')
            self.head=after
            return ticket.identity
        except BaseException:
            self.poisoned=True;raise

    @_holder_serial
    def check_branches(self,*,expected_head,branches):
        """Fresh logical fit for every alternative; not a held reservation.

        The caller must supply conservative whole-branch canonical body caps.
        A live owner must retain its own guard through check, attempt and use,
        verify its independent DB capacity, and reject underestimated bodies.
        This detached return grants no producer or resource authority.
        """
        _pin(expected_head)
        tickets=self._snapshot()
        if self.head!=expected_head:raise ValueError('stale holder head for branch capacity')
        if type(branches) is not tuple or not branches:
            raise ValueError('explicit nonempty alternative branches required')
        used=sum(len(t.body) for t in tickets)
        for branch in branches:
            if (type(branch) is not tuple or not branch
                    or any(type(n) is not int or not 1<=n<=self.max_ticket_bytes for n in branch)):
                raise ValueError('positive bounded body caps required for every branch')
            if len(tickets)+len(branch)>self.max_tickets or used+sum(branch)>self.max_total_ticket_bytes:
                raise ValueError('complete branch does not fit holder capacity')
        if self._snapshot()!=tickets or self.head!=expected_head:
            raise ValueError('holder changed during branch capacity check')
        return dict(holder_head=expected_head,used_events=len(tickets),used_body_bytes=used,
            branch_caps=branches,logical_fit=True,reservation_held=False,
            owner_database_capacity_verified=False,producer_admitted=False,resource_admission=False)

    @_holder_serial
    def close(self):
        if os.getpid()!=self._pid or get_ident()!=self._thread:raise ValueError('ticket holder close owner differs')
        if not self.closed:self.closed=True;self._lease_object.close()

    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    __copy__=old.DevelopmentOwner.__copy__
    __deepcopy__=old.DevelopmentOwner.__deepcopy__
    __reduce_ex__=old.DevelopmentOwner.__reduce_ex__

