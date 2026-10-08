"""Full-inventory H1 collector core; public execution awaits Job integration."""
from copy import deepcopy
from dataclasses import asdict,dataclass
from hashlib import sha256
from pathlib import Path

from . import normal_h1_stage_collector_v2 as base
from . import normal_h1_full_resource_contract_v2 as resources
from . import normal_h1_full_attempt_anchor as anchor

SCHEMA='h1_full_inventory_collector_development_v2'


def implementation_identity():
    return base.replay.current.source._digest(SCHEMA,base.implementation_identity(),
        resources.implementation_identity(),anchor.implementation_identity(),
        sha256(Path(__file__).read_bytes()).hexdigest())


@dataclass(frozen=True)
class _StageLimits:
    max_variables: int
    max_constraints: int


@dataclass(frozen=True,init=False)
class H1FullCollectorInspection(base.replay.current.source._Owned):
    full_collector_identity: str
    resource_declaration_identity: str
    inspection: base.H1CollectorInspection
    whole_task_resources_verified: bool
    formal_execution_ready: bool


class DevelopmentH1FullCollector(base.DevelopmentH1StageCollector):
    """Keep the old ordered commit/replay algorithm under an independent binding.

    A single hour consumes one slot of the declared task; this core does not
    enforce cross-root uniqueness or supervise the whole task. Public execution
    stays closed until the versioned Job controller owns that responsibility.
    """
    def __init__(self,root,packet,work,resource,serial_budget,limits,*,anchor_root,
                 parent_intent_head,source_lineage_identity,create=False,expected_anchor_record=None):
        resources.validate_work(work)
        resources._validate_resource(resource)
        self._work,self._resource,self._serial=deepcopy((work,resource,serial_budget))
        self._packet,self._spec,self._limits=deepcopy((packet,work.specification,limits))
        self._parent,self._source=parent_intent_head,source_lineage_identity
        self._anchor_root=str(Path(anchor_root).resolve())
        self._anchor=None
        # Complete arithmetic and actual endpoint shape gates precede all files.
        self._shape=resources.bind_current_hour(self._work,self._resource,self._packet,self._limits)
        value=self._declare()
        binding=sha256(base.chunks.base._bytes(value)).hexdigest()
        holder=anchor.DevelopmentH1FullAttemptAnchor(anchor_root,binding,
            max_records=len(value['stage_order'])+4,create=create,expected_record_sha256=expected_anchor_record)
        try:
            receipt=holder.inspect()
            if not create and receipt is None:raise ValueError('anchor lacks registry genesis; unresolved attempt')
            cap=_StageLimits(min(resource.envelope.max_variables,limits.max_variables),
                min(resource.envelope.max_constraints,limits.max_constraints))
            super().__init__(root,self._packet,self._spec,cap,self._limits,
                parent_intent_head=self._parent,source_lineage_identity=self._source,
                create=create,expected_head=None if create else receipt.registry_head)
            self._anchor=holder
            if create:receipt=holder.advance(self._registry.head,sha256(b'genesis').hexdigest(),expected_previous=None)
            holder.confirm(receipt)
        except BaseException:
            holder.close()
            if hasattr(self,'_guard'):self.close()
            raise

    def _declare(self):
        base.native._pin(self._parent)
        base.native._pin(self._source)
        plan=resources.check_plan((self._work,),(self._resource,),self._serial)
        if not plan['declaration_consistent']:
            raise ValueError('complete H1 resource declaration inconsistent: '+repr(plan['errors']))
        if self._spec!=self._work.specification:raise ValueError('full collector specification drift')
        key=base.replay.request_key(self._packet,self._spec,self._limits)
        if (base.native.model_api.stage_order(self._packet.inputs)!=self._work.stage_order
                or self._packet.relative_hour>=self._work.hours or self._shape['request_key']!=key):
            raise ValueError('full collector actual request/inventory drift')
        cap=_StageLimits(min(self._resource.envelope.max_variables,self._limits.max_variables),
            min(self._resource.envelope.max_constraints,self._limits.max_constraints))
        if hasattr(self,'_budget') and (type(self._budget) is not _StageLimits or self._budget!=cap):
            raise ValueError('full collector runtime shape cap drift')
        return dict(schema=SCHEMA,request_key=key,resource_declaration=plan,
            chain_identity=base.replay.current.source._digest(SCHEMA,key,plan['declaration_identity']),
            packet_audit_identity=self._packet.audit_identity,parent_intent_head=self._parent,
            source_lineage_identity=self._source,relative_hour=self._packet.relative_hour,
            stage_order=[list(v) for v in self._work.stage_order],limits=asdict(self._limits),
            runtime_shape_limits=asdict(cap),endpoint_shape=deepcopy(self._shape),
            anchor_root=self._anchor_root,implementation_identity=implementation_identity())

    def _check(self):
        super()._check()
        if self._anchor is not None:
            receipt=self._anchor.inspect()
            if receipt is None or receipt.registry_head!=self._registry.head:
                raise ValueError('full collector registry lacks fresh durable anchor')
            self._anchor.confirm(receipt)

    def _append(self,metadata):
        if type(self._anchor) is not anchor.DevelopmentH1FullAttemptAnchor:
            raise ValueError('exact full durable anchor required')
        previous=self._registry.head
        prior=self._anchor.inspect()
        if prior is None or prior.registry_head!=previous:raise ValueError('full registry not anchored')
        result=super()._append(metadata)
        receipt=self._anchor.advance(self._registry.head,
            sha256(base.chunks.base._bytes(metadata)).hexdigest(),expected_previous=previous)
        self._anchor.confirm(receipt)
        return result

    def _receipt(self,value):
        if type(value) is not base.H1CollectorInspection:raise ValueError('exact collector inspection required')
        return base.replay.current.source._owned(H1FullCollectorInspection,
            full_collector_identity=self._binding,
            resource_declaration_identity=self._declaration['resource_declaration']['declaration_identity'],
            inspection=value,whole_task_resources_verified=False,formal_execution_ready=False)

    def inspect(self):return self._receipt(super().inspect())

    def run(self,**kwargs):
        raise ValueError('full inventory Job controller integration required before execution')

    def _require_execution_gate(self, gate):
        from . import normal_h1_full_job_v2 as job
        request = job.gates.verify_consumed(gate)
        work, resource, serial, limits, _, _ = job._configuration(request)
        if ((self._work, self._resource, self._serial, self._limits) != (work, resource, serial, limits)
                or self._packet != job._packet(request)
                or self._parent != sha256(job.source._bytes(request)).hexdigest()
                or self._source != request['source_identity']
                or self._registry._lease.root != Path(request['root'])/'collector_non_authoritative'
                or self._anchor_root != str(Path(request['root'])/'anchor_non_authoritative')):
            raise ValueError('full collector differs from consumed calibration request')

    def _run_development(self,*,expected_head,_gate=None):
        """Native execution always requires the consumed exact calibration gate."""
        if type(self._anchor) is not anchor.DevelopmentH1FullAttemptAnchor:
            raise ValueError('exact full durable anchor required')
        receipt=self._anchor.inspect()
        if receipt is None or receipt.registry_head!=expected_head:raise ValueError('independent anchored head required')
        self._anchor.confirm(receipt)
        return self._receipt(self._run_checkpoint_development(expected_head=expected_head, _gate=_gate))

    def _run_checkpoint_development(self, *, expected_head, _gate=None):
        self._require_execution_gate(_gate)
        result = super()._run_checkpoint_development(expected_head=expected_head)
        self._require_execution_gate(_gate)
        return result

    def close(self):
        try:super().close()
        finally:
            if self._anchor is not None:self._anchor.close()
