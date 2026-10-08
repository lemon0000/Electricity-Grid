"""Pinned-source parent using durable guard/scientific hour evidence.

Reuses the existing bounded source/carry/anchor state machine; replaces only
its child archive protocol under a distinct parent declaration identity.
Saved reports only. No child Job, native route, resume or formal authority.
"""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from experiments import h1_saved_source_parent_development_v1 as prior
from experiments import h1_attested_saved_hour_development_v1 as hour_api

io, replay = hour_api.io, prior.replay
SCHEMA = 'h1_attested_source_parent_development_v1'


def implementation_identity():
    return prior.source._digest(SCHEMA, prior.implementation_identity(),
        hour_api.implementation_pins(), sha256(Path(__file__).read_bytes()).hexdigest())


@dataclass(frozen=True)
class ChildInspection:
    status: str
    head: str
    archive_identity: str
    stored_reports: int
    projection: replay.H1HourReplayedProjection | None = None
    request_key: str = ''
    packet_audit_identity: str = ''
    parent_intent_head: str = ''
    source_lineage_identity: str = ''
    hour_binding_sha256: str = ''
    hour_terminal_sha256: str | None = None
    native_execution_authenticated: bool = False
    independent_hour_jobs_integrated: bool = False
    collector_integrated: bool = False
    producer_coverage_proven: bool = False
    resource_admission: bool = False
    whole_task_resources_verified: bool = False
    formal_execution_ready: bool = False
    formal_result: bool = False

    def __post_init__(self):
        for value in (self.head,self.archive_identity,self.request_key,self.packet_audit_identity,
                      self.parent_intent_head,self.source_lineage_identity,self.hour_binding_sha256):
            io.pin(value)
        if type(self.stored_reports) is not int or not 0 <= self.stored_reports <= 232:
            raise ValueError('bounded exact stored report count required')
        if self.status=='storing':
            if self.projection is not None or self.hour_terminal_sha256 is not None:
                raise ValueError('storing child has no terminal/projection')
        elif self.status=='accepted':
            io.pin(self.hour_terminal_sha256)
            p=self.projection
            if (type(p) is not replay.H1HourReplayedProjection or p.request_key != self.request_key
                    or len(p.canonical_locks) != self.stored_reports
                    or p.numerical_chain_recomputed is not True or p.solver_calls_by_replay != 0
                    or any(getattr(p,key) is not False for key in
                           ('published','formal_result','native_execution_authenticated','exact_mathematical_certificate'))):
                raise ValueError('typed complete saved projection required')
        else:
            raise ValueError('unknown child inspection state')


class AttestedChild:
    """Parent-bound create-once child; reopen is complete-hour inspection only."""
    def __init__(self, root, packet, specification, limits, *, parent_intent_head,
                 source_lineage_identity, create=False, expected_head=None):
        if type(create) is not bool or (create and expected_head is not None):
            raise ValueError('separate create/reopen authority required')
        io.pin(parent_intent_head)
        io.pin(source_lineage_identity)
        if not create: io.pin(expected_head)
        self.root = Path(root).resolve()
        self.packet, self.specification, self.limits = packet, specification, limits
        self.parent_intent_head, self.source_lineage_identity = parent_intent_head, source_lineage_identity
        self.key = replay.request_key(packet,specification,limits)
        self.owner = None
        self.closed = self.poisoned = False
        self.writable = create
        try:
            if create:
                self.root.mkdir(exist_ok=False)
                self.owner = hour_api.SavedHour(self.root/'attested_hour_non_authoritative',
                                               packet,specification,limits)
                self.core_binding_sha256 = self.owner.binding_sha256
            else:
                raw = io.read_stable(self.root/'binding.json',io.META_CAP)[0]
                self.core_binding_sha256 = hour_api.json.loads(raw)['hour_binding_sha256']
                io.pin(self.core_binding_sha256)
            self.binding = self._binding()
            self.identity = io.digest(io.encode(self.binding))
            self.head = self.identity if create else expected_head
            if create:
                io.write_metadata(self.root/'binding.json',self.binding)
            else:
                self.inspect()
        except BaseException:
            self.poisoned = True
            raise

    def _binding(self):
        return dict(schema=SCHEMA, root=str(self.root), request_key=self.key,
            hour_binding_sha256=self.core_binding_sha256,
            stages=len(replay.native.model_api.stage_order(self.packet.inputs)),
            packet_audit_identity=self.packet.audit_identity,
            parent_intent_head=self.parent_intent_head, source_lineage_identity=self.source_lineage_identity,
            implementation_identity=implementation_identity())

    def _check(self):
        if self.closed or self.poisoned:
            raise ValueError('closed or poisoned attested child')
        if (replay.request_key(self.packet,self.specification,self.limits) != self.key
                or self._binding() != self.binding
                or io.read_stable(self.root/'binding.json',io.META_CAP)[0] != io.encode(self.binding)):
            raise ValueError('attested child binding drift')

    def _read_terminal(self):
        raw, stamp = io.read_stable(self.root/'terminal.json',io.META_CAP)
        if io.digest(raw) != self.head:
            raise ValueError('external child terminal pin mismatch')
        doc = hour_api.json.loads(raw)
        if io.encode(doc) != raw:
            raise ValueError('canonical child terminal required')
        return doc, raw, stamp

    def _inspection(self, status, count, projection=None, terminal=None):
        return ChildInspection(status,self.head,self.identity,count,projection,
            self.key,self.packet.audit_identity,self.parent_intent_head,self.source_lineage_identity,
            self.core_binding_sha256,terminal)

    def inspect(self):
        try:
            self._check()
            if self.writable:
                # This live count is not a scientific result or a resume token.
                return self._inspection('storing',len(self.owner.locks))
            if hour_api._names(self.root,3) != {'binding.json','terminal.json','attested_hour_non_authoritative'}:
                raise ValueError('unexpected child files')
            terminal, raw, stamp = self._read_terminal()
            core = self.root/'attested_hour_non_authoritative'
            view = core_view(core,len(replay.native.model_api.stage_order(self.packet.inputs)))
            if terminal['hour_binding_sha256'] != self.core_binding_sha256:
                raise ValueError('core binding differs from wrapper')
            result = hour_api.inspect(core,self.packet,self.specification,self.limits,
                expected_binding_sha256=terminal['hour_binding_sha256'],
                expected_terminal_sha256=terminal['hour_terminal_sha256'])
            if not result['saved_hour_evidence_complete']:
                raise ValueError('child hour evidence unresolved')
            # Obtain the typed carry projection through the unchanged public
            # zero-solver replay interface, never by deserializing an owned type.
            projection = replay.replay_stream(self.packet,self.specification,self.limits,
                (io.read_stable(core/'raw'/f'{i:03d}'/'raw.bin',io.RAW_CAP)[0]
                 for i in range(len(replay.native.model_api.stage_order(self.packet.inputs)))),
                expected_key=self.key)
            expected = dict(schema=SCHEMA,binding_sha256=self.identity,request_key=self.key,
                hour_binding_sha256=result['binding_sha256'],hour_terminal_sha256=result['terminal_sha256'],
                stored_reports=result['stages_recomputed'],projection_identity=projection.projection_identity,
                projection_sha256=io.digest(projection.projection_payload),
                replay_vector_sha256=hour_api.vector_pin(projection))
            if not io.same(terminal,expected):
                raise ValueError('parent child terminal differs from fresh replay')
            # Full bounded file views bracket both independent scientific reads.
            if core_view(core,len(replay.native.model_api.stage_order(self.packet.inputs))) != view:
                raise ValueError('child evidence changed during typed replay')
            fresh, fresh_stamp = io.read_stable(self.root/'terminal.json',io.META_CAP)
            if fresh != raw or fresh_stamp != stamp:
                raise ValueError('child terminal view changed')
            self._check()
            if hour_api._names(self.root,3) != {'binding.json','terminal.json','attested_hour_non_authoritative'}:
                raise ValueError('child directory changed')
            return self._inspection('accepted',result['stages_recomputed'],projection,
                                    result['terminal_sha256'])
        except BaseException:
            self.poisoned = True
            raise

    def record_report(self, raw, *, expected_head):
        try:
            self._check()
            if not self.writable or expected_head != self.head:
                raise ValueError('writable exact child predecessor required')
            self.owner.deliver(raw)
            self._check()
            self.head = self.owner.head
            return self.inspect()
        except BaseException:
            self.poisoned = True
            raise

    def finish(self, *, expected_head):
        try:
            self._check()
            if not self.writable or expected_head != self.head:
                raise ValueError('writable exact child predecessor required')
            projection, evidence = self.owner.finish()
            terminal = dict(schema=SCHEMA,binding_sha256=self.identity,request_key=self.key,
                hour_binding_sha256=evidence['binding_sha256'],hour_terminal_sha256=evidence['terminal_sha256'],
                stored_reports=evidence['stages_recomputed'],projection_identity=projection.projection_identity,
                projection_sha256=io.digest(projection.projection_payload),
                replay_vector_sha256=hour_api.vector_pin(projection))
            head = io.write_metadata(self.root/'terminal.json',terminal)
            self._check()
            self.head, self.writable = head, False
            return self.inspect()
        except BaseException:
            self.poisoned = True
            raise

    def close(self):
        self.closed = True


def core_view(root, count):
    """Bounded exact file/identity view; no scientific or execution authority."""
    if type(count) is not int or not 1 <= count <= 232:
        raise ValueError('bounded stage count required')
    specs = {name:io.META_CAP for name in ('adapter_binding.json','attestation_binding.json',
        'attestation_terminal.json','raw/binding.json','raw/terminal.json','timing/binding.json')}
    specs['projection.bin'] = hour_api.PROJECTION_CAP
    specs.update({f'timing/{i:05d}.json':io.META_CAP for i in range(6*count+5)})
    for i in range(count):
        specs.update({f'raw/{i:03d}/{name}':io.META_CAP for name in ('intent.json','raw_receipt.json','outcome.json')})
        specs[f'raw/{i:03d}/raw.bin'] = io.RAW_CAP
        specs.update({f'attestation/{i:03d}.{name}.json':io.META_CAP for name in ('guard','science','commit')})
        specs[f'attestation/{i:03d}.mapping.json'] = hour_api.MAPPING_CAP
    directories = {}
    for name in specs:
        parts = Path(name).parts
        for depth in range(len(parts)):
            directory = Path(*parts[:depth])
            directories.setdefault(directory,set()).add(parts[depth])
    for directory, names in directories.items():
        if hour_api._names(root/directory,len(names)) != names:
            raise ValueError('core file topology differs')
    result = []
    for name,cap in sorted(specs.items()):
        raw,stamp = io.read_stable(root/name,cap)
        result.append((name,stamp,io.digest(raw)))
    return tuple(result)


class SavedSourceParent(prior.SavedSourceParent):
    def _declare(self):
        result = super()._declare()
        result.update(schema=SCHEMA,implementation_identity=implementation_identity(),
                      child_protocol=hour_api.SCHEMA)
        return result

    def _intent(self, *args):
        result = super()._intent(*args)
        result['child_protocol'] = hour_api.SCHEMA
        return result

    def _child(self, hour, packet, intent_head, lineage, **kwargs):
        return AttestedChild(self._root/f'hour_{hour:03d}_non_authoritative',packet,
            self._spec,self._limits,parent_intent_head=intent_head,
            source_lineage_identity=lineage,**kwargs)

    def _outcome(self, hour, intent_head, result):
        if (type(result) is not ChildInspection or result.status != 'accepted'
                or result.stored_reports != self._stages
                or type(result.projection) is not replay.H1HourReplayedProjection
                or result.parent_intent_head != intent_head
                or any(getattr(result,name) is not False for name in (
                    'native_execution_authenticated','independent_hour_jobs_integrated','collector_integrated',
                    'producer_coverage_proven','resource_admission','whole_task_resources_verified',
                    'formal_execution_ready','formal_result'))):
            raise ValueError('complete independently replayed attested child required')
        raw=io.read_stable(self._root/f'hour_{hour:03d}_non_authoritative'/'binding.json',io.META_CAP)[0]
        bound=hour_api.json.loads(raw)
        if (io.encode(bound)!=raw or io.digest(raw)!=result.archive_identity
                or any(bound[field]!=getattr(result,attribute) for field,attribute in (
                    ('request_key','request_key'),('packet_audit_identity','packet_audit_identity'),
                    ('source_lineage_identity','source_lineage_identity'),('parent_intent_head','parent_intent_head'),
                    ('hour_binding_sha256','hour_binding_sha256')))):
            raise ValueError('typed child context differs from bound parent child')
        return dict(schema=prior.SCHEMA,kind='accepted',hour=hour,intent_head=intent_head,
            child_protocol=hour_api.SCHEMA,child_head=result.head,child_identity=result.archive_identity,
            hour_binding_sha256=result.hour_binding_sha256,hour_terminal_sha256=result.hour_terminal_sha256,
            stored_reports=result.stored_reports,projection_identity=result.projection.projection_identity)


def child_storage_bound(stages):
    result = hour_api.storage_bound(stages)
    result['logical_bytes'] += 2*io.META_CAP
    result['files'] += 2
    result['directories'] += 1
    return result
