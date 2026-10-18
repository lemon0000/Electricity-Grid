"""DRAFT integrated bootstrap storage and execution owner.

This is development code, not a formal runner or run authorization. The owned
producer and paired-owner handoff are added in this same unit before closure.
No detached journal record is a permission to execute a controller.
"""
from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json
import os
import stat
import types
from pathlib import Path
from threading import Lock, get_ident

from experiments import h1_symbolic_normal_manifest_development_v1 as symbolic
from experiments import h1_phase_ticket_holder_development_v1 as storage
from experiments import h1_phase_obligation_controller_development_v1 as phase
from experiments import h1_owned_bootstrap_controller_development_v4 as owned
from experiments import h1_phase_historical_controller_development_v1 as historical
from experiments import h1_historical_n0_verifier_development_v3 as historical_verifier
from experiments import h1_registry_declaration_development_v1 as registry_declaration
from experiments import h1_selector_configuration_development_v1 as selector_config
from experiments import h1_phase_manifest_binding_development_v2 as phase_manifest
from src.solvers.rq2_solver_adapter import Rq2SolverSpec

encode, local = storage.encode, storage.local
SCHEMA = 'h1_bootstrap_integration_development_v4'
FLAGS = dict(formal_result=False,formal_execution_ready=False,resource_admission=False,
    native_execution_authorized=False,full_study_registry_authenticated=False)


def digest(value): return sha256(encode(value)).hexdigest()


N0_PINS=('slot_id','claim_head','claim_proposal_id','global_release_head','bootstrap_release_head',
    'controller_ready_head','controller_binding_sha256','controller_terminal_sha256','audit_payload_sha256',
    'historical_implementation','historical_verifier_identity','decision_identity','parent_head','evidence_identity','normal_request_key',
    'child_head','child_archive_identity','projection_identity','projection_payload_sha256','exact_n0_topology_identity')


def _N0_body(root,pins):
    if type(pins) is not dict or set(pins)!=set(N0_PINS):raise ValueError('exact N0 pin fields required')
    for pin in pins.values():storage._pin(pin)
    return dict(kind='normal_terminal',controller_root=root,completed_hours=1,**pins,
        historical_verifier_schema=historical_verifier.VERIFIER_SCHEMA,
        historical_validation_contract=historical_verifier.VERIFIER_SCHEMA,
        legacy_compatibility_execution_metadata=dict(full_numerical_hour_replays=4,
            fresh_byte_context_revalidations=4,recomputed_on_revalidation=False,
            scope='predecessor_scientific_projection_only'),
        outcome='accepted_N0_numerical_candidate',scratch_contents_audited=False,
        scratch_included_in_scientific_evidence=False,filesystem_allocation_bound_proven=False,
        exact_n0_topology_verified=True,retry_authorized=False,**FLAGS)


def _global_N0_body(local_head,body):
    storage._pin(local_head)
    return dict(kind='normal_terminal',slot_id=body['slot_id'],claim_head=body['claim_head'],
        release_head=body['global_release_head'],bootstrap_terminal_head=local_head,
        bootstrap_terminal_body_sha256=digest(body),evidence_identity=body['evidence_identity'],
        outcome='accepted_N0_numerical_candidate',retry_authorized=False,**FLAGS)


def implementation_identity():
    return digest([SCHEMA,sha256(Path(__file__).read_bytes()).hexdigest(),
        storage.implementation_identity(),phase.implementation_identity(),
        sha256(Path(symbolic.__file__).read_bytes()).hexdigest(),
        sha256(Path(owned.__file__).read_bytes()).hexdigest(),historical.implementation_identity(),
        historical_verifier.verifier_identity(),
        sha256(Path(registry_declaration.__file__).read_bytes()).hexdigest(),
        selector_config.implementation_identity(),sha256(Path(phase_manifest.__file__).read_bytes()).hexdigest(),
        sha256(Path(phase_manifest.verifier.__file__).read_bytes()).hexdigest()])


def _bind_N0_verifier(prepare):
    def verify(root,*,expected_binding_sha256,expected_terminal_sha256,completed_hours,registry_scope=None):
        value=prepare(root,expected_binding_sha256=expected_binding_sha256,
            expected_terminal_sha256=expected_terminal_sha256,completed_hours=completed_hours,registry_scope=registry_scope)
        if (type(value) is not historical_verifier.VerifiedHistoricalEnvelope
                or value.verifier_identity!=historical_verifier.verifier_identity()
                or value.predecessor_schema!=historical.SCHEMA
                or (value.full_numerical_hour_replays,value.fresh_byte_context_revalidations) not in ((4,4),(0,8))
                or type(value.execution_receipt) is not bytes
                or json.loads(value.execution_receipt)['predecessor_audit_sha256']!=sha256(value.audit_payload).hexdigest()):
            raise ValueError('internally prepared N0 verifier envelope required')
        return value
    return verify


_prepare_N0=_bind_N0_verifier(historical_verifier.prepare)


def _snapshot(fn):
    result=types.FunctionType(fn.__code__,fn.__globals__,fn.__name__,fn.__defaults__,fn.__closure__)
    result.__kwdefaults__=dict(fn.__kwdefaults__ or {});return result


def _guard_N0_route(operation):
    route=_prepare_N0;current=_snapshot(historical_verifier.registry_validation_scope)
    poison=_snapshot(historical_verifier._poison_registry_scope)
    def guarded(*args,**kwargs):
        owner=args[0];scope=current(owner)
        try:
            _check_N0_contract(owner)
            if _prepare_N0 is not route or 'registry_scope' in kwargs:raise ValueError('N0 verifier route changed')
            site=kwargs.pop('_n0_site','N0_build')
            if scope is not None:
                claim=args[2];scope.begin_build(owner,claim['proposal']['roots']['controller'],claim['slot_id'],site)
            value=operation(*args,**kwargs,registry_scope=scope)
            _check_N0_contract(owner)
            if scope is not None:scope.confirm_build(value)
            return value
        except BaseException as error:
            if scope is not None:poison(scope,error)
            raise
    return guarded


def _bind_registry_run():
    scope_type=historical_verifier.RegistryValidationScope
    close=_snapshot(historical_verifier._close_registry_scope)
    poison=_snapshot(historical_verifier._poison_registry_scope)
    receipt=_snapshot(historical_verifier._registry_scope_receipt)
    def run(owner,execute):
        scope=scope_type(owner);error=None
        try:
            scope.__enter__();result=execute();_check_N0_contract(owner)
        except BaseException as failure:error=failure;poison(scope,failure);raise
        finally:close(scope,error)
        try:
            proof=receipt(scope)
            if type(result) is not dict or result.get('state')!='pending_post_N' or not proof['complete']:
                raise ValueError('complete bootstrap registry execution receipt required')
            result['N0_validation_execution_receipt']=historical.io.encode(proof)
            _check_N0_contract(owner);return result
        except BaseException as failure:poison(scope,failure);raise
    return run


_run_registry_operation=_bind_registry_run()


def _journal_header(root,declaration,max_events,max_record_bytes,implementation):
    return encode(dict(schema=SCHEMA,root=str(root),declaration=declaration,
        max_events=max_events,max_record_bytes=max_record_bytes,implementation=implementation,**FLAGS))


def _phase_input_fingerprint(configuration):
    """Fresh complete dependencies; ordinal zero is only a fingerprint coordinate.

    Actual candidates still verify their own family and ordinal through prepare.
    No source, historical record or durable owner read is cached here.
    """
    phase_manifest.verifier._scope()
    before=phase_manifest._implementation(configuration)
    verified=phase_manifest.verifier.prepare_group('training_ub',0)
    identity=verified['predecessor_group']['implementation_sha256']
    if phase_manifest._implementation(configuration)!=before:
        raise ValueError('phase implementation changed during fingerprint')
    evidence=phase_manifest._verifier_evidence(verified)
    phase_manifest.verifier._scope()
    return identity,before,evidence['verifier_implementation_sha256'],evidence['dependency_inventory_sha256']


class _Journal:
    """Private bounded append-only journal with externally retained head.

    A failed append never removes bytes or adopts an unknown suffix. Reopening
    is inspection-only with respect to pending execution, not an automatic retry.
    """
    def __init__(self,root,declaration,*,max_events,max_record_bytes,create,expected_head,retain_head):
        if (type(create) is not bool or type(max_events) is not int or not 1<=max_events<10**20
                or type(max_record_bytes) is not int or not 1024<=max_record_bytes<=1024**2
                or not callable(retain_head)):
            raise ValueError('exact journal configuration and external head retention required')
        if create and expected_head is not None: raise ValueError('create cannot adopt a journal head')
        if not create: storage._pin(expected_head)
        self._pid,self._thread=os.getpid(),get_ident()
        self.closed=self.poisoned=False
        self._lease=local._Lease(root,create);self._original_lease=self._lease
        self.root=self._lease.root;self.max_events=max_events;self.cap=max_record_bytes
        self._configuration=(self.root,self.max_events,self.cap)
        self._retain=self._original_retain=retain_head
        self._implementation=implementation_identity()
        self._declaration=encode(declaration)
        self._header=_journal_header(self.root,declaration,max_events,max_record_bytes,self._implementation)
        try:
            if len(self._header)>self.cap: raise ValueError('journal header exceeds cap')
            if create: storage._new(self.root/'header.json',self._header)
            header,self._header_identity=storage._read(self.root/'header.json',self.cap)
            if header!=self._header:
                raise ValueError('journal declaration changed')
            self.genesis=sha256(self._header).hexdigest()
            self.head=self.genesis if create else expected_head
            self._identities={}
            self.rows()
        except BaseException:
            self.close();raise

    def check(self):
        if (self.closed or self.poisoned or os.getpid()!=self._pid or get_ident()!=self._thread
                or self._lease is not self._original_lease or self._retain is not self._original_retain
                or (self.root,self.max_events,self.cap)!=self._configuration
                or self.genesis!=sha256(self._header).hexdigest()
                or implementation_identity()!=self._implementation):
            raise ValueError('journal live owner/configuration changed')
        self._lease.check()
        if storage._read(self.root/'header.json',self.cap)!=(self._header,self._header_identity):
            raise ValueError('journal header changed')

    def rows(self):
        self.check()
        names={p.name for p in self.root.iterdir()}
        names-={'execution.lock','header.json'}
        if len(names)>self.max_events: raise ValueError('journal event bound exceeded')
        expected={f'{i:020d}.json' for i in range(1,len(names)+1)}
        if names!=expected: raise ValueError('journal namespace discontinuity')
        head=self.genesis;rows=[];identities={}
        for i in range(1,len(names)+1):
            path=self.root/f'{i:020d}.json';raw,identity=storage._read(path,self.cap)
            value=json.loads(raw)
            if (encode(value)!=raw or set(value)!={'sequence','previous','body'}
                    or type(value['sequence']) is not int or value['sequence']!=i or value['previous']!=head
                    or type(value['body']) is not dict): raise ValueError('journal chain differs')
            if path in self._identities and self._identities[path]!=(identity,raw):
                raise ValueError('journal event replaced or changed')
            head=sha256(raw).hexdigest();rows.append((head,value['body']));identities[path]=(identity,raw)
        if head!=self.head: raise ValueError('external retained journal head differs')
        if {p.name for p in self.root.iterdir()}!=names|{'execution.lock','header.json'}:
            raise ValueError('journal changed during replay')
        for path,(identity,raw) in identities.items():
            if storage._read(path,self.cap)!=(raw,identity):
                raise ValueError('journal event changed during replay')
        self._identities=identities;self.check()
        return rows

    def reserve(self,count):
        rows=self.rows()
        if type(count) is not int or count<=0 or len(rows)+count>self.max_events:
            raise ValueError('complete journal branch does not fit')
        return rows

    def append(self,body,*,expected_head):
        if self.head!=expected_head: raise ValueError('stale journal head')
        rows=self.reserve(1)
        raw=encode(dict(sequence=len(rows)+1,previous=self.head,body=body))
        if len(raw)>self.cap: raise ValueError('journal record exceeds cap')
        next_head=sha256(raw).hexdigest();path=self.root/f'{len(rows)+1:020d}.json'
        try:
            storage._new(path,raw)
            if self._retain(self.root,self.head,next_head)!=next_head:
                raise ValueError('external exact head retention failed')
            self.check();self.head=next_head
            if self.rows()!=rows+[(next_head,json.loads(encode(body)))]:
                raise ValueError('journal append readback differs')
            return next_head
        except BaseException:
            self.poisoned=True;raise

    def close(self):
        if os.getpid()!=self._pid or get_ident()!=self._thread: raise ValueError('journal close owner differs')
        if self.closed:return
        self.closed=True;self._original_lease.close()


@dataclass(frozen=True)
class RegistryBinding:
    path: str
    sha256: str
    split: str

    def __post_init__(self):
        if type(self.path) is not str or str(local._path(self.path))!=self.path:
            raise ValueError('canonical absolute registry declaration path required')
        storage._pin(self.sha256)
        if type(self.split) is not str or self.split not in ('training','holdout'):
            raise ValueError('exact registry declaration split required')


@dataclass(frozen=True)
class RunConfiguration:
    """Pure typed declaration; network and source content are not yet verified."""
    upstream_root: str
    config_path: str
    source_config_sha256: str
    network_sha256: str
    dc_bus: int
    specification: Rq2SolverSpec
    limits: phase.base.old.replay.H1HourReplayLimits
    budget: phase.base.old.process.TaskProcessBudget
    stage_order: tuple

    def __post_init__(self):
        for path in (self.upstream_root,self.config_path):
            if type(path) is not str or str(local._path(path))!=path:
                raise ValueError('fixed canonical run configuration paths required')
        for pin in (self.source_config_sha256,self.network_sha256):storage._pin(pin)
        if self.source_config_sha256!=phase.binding.SOURCE_CONFIG_PIN:
            raise ValueError('frozen source configuration required')
        if type(self.dc_bus) is not int:raise ValueError('exact DC bus required')
        phase.base.old.replay.native.capture.provenance.adapter.validate_spec(self.specification)
        if type(self.limits) is not phase.base.old.replay.H1HourReplayLimits:
            raise ValueError('exact replay limits required')
        self.limits.__post_init__()
        if type(self.budget) is not phase.base.old.process.TaskProcessBudget:
            raise ValueError('exact Job budget required')
        self.budget.__post_init__()
        if self.budget.max_elapsed_seconds>300:raise ValueError('short development ceiling is 300 seconds')
        order=self.stage_order
        if (type(order) is not tuple or not order or order[0]!=('operating_cost',None)
                or any(type(v) is not tuple or len(v)!=2 for v in order)
                or any(k not in ('commitment','generation') or type(uid) is not str or not uid for k,uid in order[1:])):
            raise ValueError('exact declared stage order required')
        commitments=tuple(uid for k,uid in order[1:] if k=='commitment')
        generation=tuple(uid for k,uid in order[1:] if k=='generation')
        canonical=(('operating_cost',None),*(('commitment',uid) for uid in sorted(set(commitments))),
            *(('generation',uid) for uid in sorted(set(generation))))
        if (not generation or not set(commitments)<=set(generation) or order!=canonical
                or len(order)>self.limits.max_stages):raise ValueError('complete canonical declared stage order required')

    def declared_profile(self):
        self.__post_init__()
        return asdict(symbolic.StaticProfile(self.network_sha256,digest(self.dc_bus),self.source_config_sha256,
            digest(asdict(self.specification)),digest(asdict(self.limits)),digest(asdict(self.budget)),
            implementation_identity(),digest(self.stage_order),
            sha256(Path(phase.binding.source_binding.h1.model_api.__file__).read_bytes()).hexdigest(),
            phase.binding.followup.implementation_identity()))


@dataclass(frozen=True)
class BootstrapDeclaration:
    study_root: str
    symbolic_path: str
    symbolic_sha256: str
    family: str
    ordinal: int
    max_global_events: int
    max_record_bytes: int
    run_configuration: RunConfiguration | None = None
    registry_binding: RegistryBinding | None = None
    selector_configuration: selector_config.SelectorRunConfiguration | None = None
    phase_archive: phase_manifest.ArchiveCapacityDeclaration | None = None

    def __post_init__(self):
        if self.family!='training_ub' or type(self.family) is not str:
            raise ValueError('only training_ub bootstrap is implemented')
        if type(self.ordinal) is not int or self.ordinal<0:raise ValueError('exact obligation ordinal required')
        storage._pin(self.symbolic_sha256)
        for path in (self.study_root,self.symbolic_path):
            if type(path) is not str or str(local._path(path))!=path:
                raise ValueError('fixed canonical absolute paths required')
        if (type(self.max_global_events) is not int or not 3<=self.max_global_events<10**20
                or type(self.max_record_bytes) is not int or not 1024<=self.max_record_bytes<=1024**2):
            raise ValueError('explicit bounded global journal required')
        if self.run_configuration is not None:
            if type(self.run_configuration) is not RunConfiguration:raise ValueError('exact run configuration required')
            self.run_configuration.__post_init__()
        if self.registry_binding is not None:
            if type(self.registry_binding) is not RegistryBinding:
                raise ValueError('exact registry declaration binding required')
            self.registry_binding.__post_init__()
        if self.selector_configuration is not None:
            if (type(self.selector_configuration) is not selector_config.SelectorRunConfiguration
                    or type(self.run_configuration) is not RunConfiguration):
                raise ValueError('typed selector and N run configurations required')
            self.selector_configuration.validate_normal(
                self.run_configuration.network_sha256, self.run_configuration.stage_order)
        if self.phase_archive is not None:
            if (type(self.phase_archive) is not phase_manifest.ArchiveCapacityDeclaration
                    or type(self.selector_configuration) is not selector_config.SelectorRunConfiguration):
                raise ValueError('phase archive requires exact selector and archive declarations')
            self.phase_archive.__post_init__()


class _BootstrapController(phase.Controller):
    """Constructed inside one bootstrap operation; execution entry still closed."""
    def __init__(self,owner,network):
        if (type(owner) is not BootstrapOwner or not owner._operation.locked()
                or network is not owner._network or owner._controller is not None
                or owner._replay()!='profile_verified'):
            raise ValueError('owned profile-verified controller construction required')
        owner._check();self._bootstrap_owner=owner
        config=owner.declaration.run_configuration
        super().__init__(owner.roots['controller'],network,config.specification,config.limits,
            resolver=phase.binding.open_manifest(),family=owner.declaration.family,ordinal=owner.declaration.ordinal,
            origin=owner._origin(),upstream_root=config.upstream_root,config_path=config.config_path,
            dc_bus=config.dc_bus,hours=192,budget=config.budget)

    def _step_development(self,**kwargs):
        raise ValueError('bootstrap release/capability entry not implemented')

    def _check(self):
        raise ValueError('bootstrap release/capability entry not implemented')


class BootstrapOwner:
    """Single operation owner; the global journal is private to this unit.

    Current draft binds a retained claim to loaded static content and creates
    its empty controller internally. It stops before release; the live producer
    and paired handoff remain open. No return value authorizes execution.
    """
    def __init__(self,declaration,*,create_study,create,global_head=None,bootstrap_head=None,
                 retain_global_head,retain_bootstrap_head):
        if type(declaration) is not BootstrapDeclaration:raise ValueError('exact bootstrap declaration required')
        declaration.__post_init__()
        if type(create_study) is not bool or type(create) is not bool:raise ValueError('exact create flags required')
        self.declaration=declaration;self._declaration_bytes=encode(asdict(declaration))
        self._pid,self._thread=os.getpid(),get_ident();self._operation=Lock()
        self._original_operation=self._operation;self._operation_nonce=None
        self.closed=self.poisoned=False;self._global=self._bootstrap=None
        self._controller=self._original_controller=None;self._network=None
        self._implementation=implementation_identity()
        self._manifest=symbolic.inspect(declaration.symbolic_path,expected_sha256=declaration.symbolic_sha256)
        self._slot=self._manifest.resolve(declaration.family,declaration.ordinal*192)
        if self._slot['kind']!='potential_N_slot':raise ValueError('proof-discharged obligation cannot bootstrap')
        self._profile=self._manifest.data()['declared_static_profile']
        self._profile_bytes=encode(self._profile)
        self._slot_bytes=encode(self._slot)
        p=self._manifest.obligation(declaration.family,declaration.ordinal)['obligation_node']['record']['payload']
        self._registry_view=self._fresh_registry_declaration()
        self._original_registry_view=self._registry_view
        self._phase_cache=self._original_phase_cache={};self._phase_cache_snapshot=()
        self._phase_inputs=None if declaration.phase_archive is None else _phase_input_fingerprint(declaration.selector_configuration)
        self.study_root=local._path(declaration.study_root)
        self.episode_root=self.study_root/'episodes'/p['obligation_sha256']
        self.roots={name:str(self.episode_root/(name+'_non_authoritative')) for name in ('bootstrap','controller','owner','holder')}
        self._roots_bytes=encode(self.roots)
        self._study_binding=dict(study_root=str(self.study_root),symbolic_path=declaration.symbolic_path,
            symbolic_sha256=declaration.symbolic_sha256,
            run_configuration=None if declaration.run_configuration is None else asdict(declaration.run_configuration),
            selector_configuration=None if declaration.selector_configuration is None else declaration.selector_configuration.binding(),
            phase_archive=None if declaration.phase_archive is None else asdict(declaration.phase_archive),
            registry_binding=None if declaration.registry_binding is None else asdict(declaration.registry_binding),
            registry_declaration=None if self._registry_view is None else {
                k:json.loads(self._registry_view[0])[k] for k in ('split','expected_registry_identity')},
            profile=self._profile,global_root=str(self.study_root/'global_claims_non_authoritative'))
        self._study_binding_bytes=encode(self._study_binding)
        candidate=self._phase_candidate(declaration)
        episode_declaration=self._episode_declaration(declaration,self._slot['slot_id'],self.roots,candidate)
        self._preflight_journal_bytes(episode_declaration,candidate)
        self._check_phase_inputs()
        if encode(episode_declaration)!=encode(self._episode_declaration(
                declaration,self._slot['slot_id'],self.roots,self._phase_candidate(declaration))):
            raise ValueError('phase candidate changed before journal creation')
        try:
            if create_study:self.study_root.mkdir(exist_ok=False)
            self._global=_Journal(self.study_root/'global_claims_non_authoritative',self._study_binding,
                max_events=declaration.max_global_events,max_record_bytes=declaration.max_record_bytes,
                create=create_study,expected_head=global_head,retain_head=retain_global_head)
            self._original_global=self._global
            if create:
                self.episode_root.parent.mkdir(exist_ok=True)
                self.episode_root.mkdir(exist_ok=False)
            self._bootstrap=_Journal(Path(self.roots['bootstrap']),episode_declaration,
                max_events=8,max_record_bytes=declaration.max_record_bytes,create=create,
                expected_head=bootstrap_head,retain_head=retain_bootstrap_head)
            self._original_bootstrap=self._bootstrap
            self._replay()
        except BaseException:
            self.close();raise

    def _check(self):
        _check_N0_contract(self)
        if (self.closed or self.poisoned or (os.getpid(),get_ident())!=(self._pid,self._thread)
                or encode(asdict(self.declaration))!=self._declaration_bytes
                or encode(self.roots)!=self._roots_bytes or encode(self._slot)!=self._slot_bytes
                or encode(self._profile)!=self._profile_bytes or encode(self._study_binding)!=self._study_binding_bytes
                or self._global is not self._original_global or self._bootstrap is not self._original_bootstrap
                or self._controller is not self._original_controller
                or self._operation is not self._original_operation
                or implementation_identity()!=self._implementation):
            raise ValueError('bootstrap owner/configuration changed')
        self.declaration.__post_init__()
        self._check_phase_inputs()
        self._check_phase_header()
        if self._registry_view is not self._original_registry_view:
            raise ValueError('registry declaration observation replaced')
        binding=self.declaration.registry_binding
        if binding is not None and storage._read(Path(binding.path),registry_declaration.DECLARATION_CAP)!=self._registry_view:
            raise ValueError('registry declaration changed during bootstrap')
        self._global.check();self._bootstrap.check()

    def _check_phase_static(self):
        # Finish any implementation reads before comparing mutable in-memory
        # fields. A read callback must not hide a declaration change.
        implementation=implementation_identity()
        self.declaration.__post_init__();self._check_phase_cache()
        if (encode(asdict(self.declaration))!=self._declaration_bytes
                or implementation!=self._implementation
                or encode(self._study_binding)!=self._study_binding_bytes
                or encode(self._profile)!=self._profile_bytes or encode(self._slot)!=self._slot_bytes
                or encode(self.roots)!=self._roots_bytes):
            raise ValueError('phase candidate declaration or implementation changed')

    def _check_phase_inputs(self):
        self._check_phase_static()
        fingerprint=None if self.declaration.phase_archive is None else _phase_input_fingerprint(
            self.declaration.selector_configuration)
        self._check_phase_static()
        if fingerprint!=self._phase_inputs:raise ValueError('phase candidate dependencies changed')
        return fingerprint

    def _phase_key(self,declaration):
        key=(declaration.family,declaration.ordinal,encode(declaration.selector_configuration.binding()),
            encode(asdict(declaration.phase_archive)))
        self._check_phase_static()
        return key

    def _check_phase_header(self):
        # The checked durable header, not a mutable cache snapshot, anchors the
        # current episode's candidate even before the first attempt exists.
        self._bootstrap.check()
        stored=json.loads(self._bootstrap._header)['declaration']['phase_manifest_candidate']
        if self.declaration.phase_archive is None:
            if stored is not None:raise ValueError('phase candidate header differs')
            return
        key=self._phase_key(self.declaration)
        value=self._phase_cache.get(key)
        if (stored is None or value is None
                or value!=(encode(stored['audit']),stored['audit_identity'])):
            raise ValueError('phase candidate cache differs from retained header')

    def _check_phase_cache(self):
        if (self._phase_cache is not self._original_phase_cache
                or type(self._phase_cache) is not dict
                or tuple(sorted(self._phase_cache.items()))!=self._phase_cache_snapshot):
            raise ValueError('phase candidate cache changed')
        for key,value in self._phase_cache.items():
            if (type(key) is not tuple or len(key)!=4
                    or tuple(type(k) for k in key)!=(str,int,bytes,bytes)
                    or key[0]!='training_ub' or key[1]<0
                    or type(value) is not tuple or len(value)!=2 or type(value[0]) is not bytes
                    or type(value[1]) is not str or sha256(value[0]).hexdigest()!=value[1]):
                raise ValueError('phase candidate cache entry differs')

    def _phase_candidate(self,declaration):
        fingerprint=self._check_phase_inputs()
        if encode(asdict(replace(self.declaration,ordinal=declaration.ordinal)))!=encode(asdict(declaration)):
            raise ValueError('foreign phase declaration differs')
        if declaration.phase_archive is None:return None
        c=declaration.selector_configuration
        key=self._phase_key(declaration)
        if key not in self._phase_cache:
            prepared=phase_manifest.prepare(declaration.family,declaration.ordinal,c,declaration.phase_archive)
            raw,pin=prepared.audit_payload,prepared.audit_identity
            audit=json.loads(raw)
            if type(raw) is not bytes or encode(audit)!=raw or sha256(raw).hexdigest()!=pin:
                raise ValueError('phase candidate audit must be canonical and exact')
            siblings=[s for s in audit['group']['siblings'] if type(s['ordinal']) is int and s['ordinal']==declaration.ordinal]
            selected=self._manifest.obligation(declaration.family,declaration.ordinal)['obligation_node']
            if (audit['family']!=declaration.family or type(audit['ordinal']) is not int
                    or audit['ordinal']!=declaration.ordinal or len(siblings)!=1
                    or encode(siblings[0]['obligation_node'])!=encode(selected)
                    or encode(audit['selector_configuration'])!=key[2]
                    or encode(audit['archive_declaration'])!=key[3]
                    or encode(audit['manifest'])!=encode(None if prepared.manifest is None else asdict(prepared.manifest))
                    or (audit['group']['implementation_sha256'],audit['implementation_sha256'],
                        audit['dependency_verifier']['verifier_implementation_sha256'],
                        audit['dependency_verifier']['dependency_inventory_sha256'])!=fingerprint
                    or digest(audit['group'])!=audit['dependency_verifier']['predecessor_group_sha256']):
                raise ValueError('phase candidate request, selected obligation or implementation differs')
            if self._check_phase_inputs()!=fingerprint or self._phase_key(declaration)!=key:
                raise ValueError('phase candidate inputs changed during preparation')
            self._phase_cache[key]=(raw,pin)
            self._phase_cache_snapshot=tuple(sorted(self._phase_cache.items()))
        raw,pin=self._phase_cache[key]
        return dict(audit=json.loads(raw),audit_identity=pin)

    def _episode_declaration(self,declaration,slot,roots,candidate):
        return dict(study=self._study_binding,declaration=asdict(declaration),slot_id=slot,roots=roots,
            phase_manifest_candidate=candidate)

    def _proposal_for(self,declaration,slot,roots,genesis,candidate):
        return dict(study=self._study_binding,family=declaration.family,ordinal=declaration.ordinal,
            slot_id=slot,profile=self._profile,roots=roots,bootstrap_genesis=genesis,
            phase_manifest_audit_identity=None if candidate is None else candidate['audit_identity'])

    def _preflight_journal_bytes(self,episode_declaration,candidate):
        d=self.declaration
        header=_journal_header(self.roots['bootstrap'],episode_declaration,8,d.max_record_bytes,self._implementation)
        genesis=sha256(header).hexdigest()
        proposal=self._proposal_for(d,self._slot['slot_id'],self.roots,genesis,candidate)
        attempt=encode(dict(sequence=1,previous=genesis,
            body=dict(kind='attempt',proposal=proposal,claim_proposal_id=digest(proposal))))
        claim=encode(dict(sequence=d.max_global_events,previous='0'*64,body=dict(kind='claim',
            slot_id=self._slot['slot_id'],proposal=proposal,claim_proposal_id=digest(proposal),
            bootstrap_attempt_head=sha256(attempt).hexdigest())))
        study=_journal_header(self.study_root/'global_claims_non_authoritative',self._study_binding,
            d.max_global_events,d.max_record_bytes,self._implementation)
        if max(map(len,(header,study,attempt,claim)))>d.max_record_bytes:
            raise ValueError('complete bootstrap declarations exceed journal byte cap')

    def _fresh_registry_declaration(self):
        binding=self.declaration.registry_binding
        if binding is None:return None
        payload=self._manifest.obligation(self.declaration.family,self.declaration.ordinal)['obligation_node']['record']['payload']
        if binding.split!=payload['split']:raise ValueError('registry declaration obligation split differs')
        path=Path(binding.path)
        before=storage._read(path,registry_declaration.DECLARATION_CAP)
        registry_declaration.inspect(path,expected_sha256=binding.sha256,split=payload['split'])
        if storage._read(path,registry_declaration.DECLARATION_CAP)!=before:
            raise ValueError('registry declaration changed during validation')
        return before

    def _registry(self):
        states={};views={};genesis_views={};genesis_directories={};journal_directories={};terminal_views={};rows=self._global.rows()
        for head,body in rows:
            kind=body.get('kind');slot=body.get('slot_id')
            storage._pin(slot)
            if kind=='claim':
                if slot in states:raise ValueError('duplicate global slot claim')
                if set(body)!={'kind','slot_id','proposal','claim_proposal_id','bootstrap_attempt_head'}:
                    raise ValueError('global claim schema differs')
                proposal=body['proposal']
                if (type(proposal) is not dict or set(proposal)!={'study','family','ordinal','slot_id',
                        'profile','roots','bootstrap_genesis','phase_manifest_audit_identity'} or proposal['family']!='training_ub'
                        or type(proposal['ordinal']) is not int or proposal['ordinal']<0):
                    raise ValueError('global claim proposal schema differs')
                d=replace(self.declaration,ordinal=proposal['ordinal'])
                resolved=self._manifest.resolve(d.family,d.ordinal*192)
                if resolved['kind']!='potential_N_slot' or resolved['slot_id']!=slot:
                    raise ValueError('global claim slot differs')
                payload=self._manifest.obligation(d.family,d.ordinal)['obligation_node']['record']['payload']
                episode=local._path(d.study_root)/'episodes'/payload['obligation_sha256']
                roots={name:str(episode/(name+'_non_authoritative')) for name in ('bootstrap','controller','owner','holder')}
                candidate=self._phase_candidate(d)
                header=_journal_header(roots['bootstrap'],self._episode_declaration(d,slot,roots,candidate),
                    8,d.max_record_bytes,self._implementation)
                genesis=sha256(header).hexdigest()
                expected=self._proposal_for(d,slot,roots,genesis,candidate)
                attempt=encode(dict(sequence=1,previous=genesis,
                    body=dict(kind='attempt',proposal=expected,claim_proposal_id=digest(expected))))
                expected_claim=dict(kind='claim',slot_id=slot,proposal=expected,
                    claim_proposal_id=digest(expected),bootstrap_attempt_head=sha256(attempt).hexdigest())
                if encode(body)!=encode(expected_claim):raise ValueError('global claim binding differs')
                for name,raw in (('header.json',header),('00000000000000000001.json',attempt)):
                    path=Path(roots['bootstrap'])/name
                    view=storage._read(path,d.max_record_bytes)
                    if view[0]!=raw:raise ValueError('global claim bootstrap cross-reference differs')
                    views[path]=view
                states[slot]=dict(claim=(head,body),release=None,local_terminal=None,terminal=None)
            elif kind=='release_intent':
                if slot not in states or states[slot]['release'] is not None:
                    raise ValueError('global release requires exactly one unreleased claim')
                claim_head,claim=states[slot]['claim']
                release_head,ready_row,release_digest,local_terminal=self._release_cross_reference(
                    claim_head,claim,views,genesis_views,genesis_directories,journal_directories)
                ready_head,ready_body=ready_row
                expected=dict(kind='release_intent',slot_id=slot,claim_head=claim_head,
                    claim_proposal_id=claim['claim_proposal_id'],bootstrap_release_head=release_head,
                    bootstrap_release_body_sha256=release_digest,controller_ready_head=ready_head,**FLAGS)
                if encode(body)!=encode(expected):raise ValueError('global release binding differs')
                states[slot]['release']=(head,body)
                if local_terminal is not None:
                    observed={}
                    expected_terminal=self._build_N0_terminal(claim_head,claim,head,ready_row,release_head,
                        observed,self._check,_n0_site='registry')
                    if encode(local_terminal[1])!=encode(expected_terminal):
                        raise ValueError('local N0 terminal differs from fresh evidence')
                    states[slot]['local_terminal']=local_terminal
                    terminal_views[slot]=(Path(claim['proposal']['roots']['controller']),
                        ready_body['parent_declaration'],observed)
            elif kind=='normal_terminal':
                if (slot not in states or states[slot]['local_terminal'] is None
                        or states[slot]['terminal'] is not None):
                    raise ValueError('global N0 terminal requires exactly one retained local terminal')
                local_head,local_body=states[slot]['local_terminal']
                if encode(body)!=encode(_global_N0_body(local_head,local_body)):
                    raise ValueError('global N0 terminal binding differs')
                states[slot]['terminal']=(head,body)
            else:
                # No future terminal record may be silently accepted
                # before this draft implements its exact transition schema.
                raise ValueError('global execution transition not implemented')
        if self._global.rows()!=rows:raise ValueError('global claims changed during cross-replay')
        for path,view in views.items():
            if storage._read(path,self.declaration.max_record_bytes)!=view:
                raise ValueError('bootstrap cross-reference changed during replay')
        for path,view in genesis_views.items():
            if storage._read(path,phase.CAP)!=view:raise ValueError('release genesis changed during cross-replay')
        for path,view in genesis_directories.items():
            if self._plain_directory(path)!=view:raise ValueError('release genesis directory changed during cross-replay')
        for path,(names,view) in journal_directories.items():
            if phase.bridge.worker.hour._directory(path,names)!=view:
                raise ValueError('release bootstrap namespace changed during cross-replay')
        for root,declaration,observed in terminal_views.values():
            self._observe_N0(root,declaration,observed)
        # Observing numerical/source evidence must not hide a concurrent change
        # to an earlier local journal or genesis cross-reference.
        for path,view in views.items():
            if storage._read(path,self.declaration.max_record_bytes)!=view:
                raise ValueError('bootstrap cross-reference changed after N0 observation')
        for path,view in genesis_views.items():
            if storage._read(path,phase.CAP)!=view:raise ValueError('release genesis changed after N0 observation')
        for path,view in genesis_directories.items():
            if self._plain_directory(path)!=view:raise ValueError('release directory changed after N0 observation')
        for path,(names,view) in journal_directories.items():
            if phase.bridge.worker.hour._directory(path,names)!=view:
                raise ValueError('release namespace changed after N0 observation')
        if self._global.rows()!=rows:raise ValueError('global registry changed during final cross-replay')
        return states

    def _claims(self):
        return {slot:value['claim'] for slot,value in self._registry().items()}

    def _remaining_global_records(self):
        # A claimed slot still owes release+terminal; a released slot owes its
        # terminal even when execution is indeterminate. There is no reuse credit.
        return sum(2 if value['release'] is None else 1 if value['terminal'] is None else 0
            for value in self._registry().values())

    def _release_body(self,claim_head,claim,ready_head,ready_body):
        return dict(kind='release_intent',slot_id=claim['slot_id'],claim_proposal_id=claim['claim_proposal_id'],
            claim_head=claim_head,controller_ready_head=ready_head,
            controller_genesis_sha256=digest(ready_body),retry_authorized=False,**FLAGS)

    def _release_cross_reference(self,claim_head,claim,views,genesis_views,genesis_directories,journal_directories):
        proposal=claim['proposal'];roots=proposal['roots']
        journal=Path(roots['bootstrap'])
        names={'execution.lock','header.json',*(f'{i:020d}.json' for i in range(1,5))}
        actual=historical.history.bounded.prior.hour_api._names(journal,7)
        terminal_name='00000000000000000005.json'
        if actual==names|{terminal_name}:names.add(terminal_name)
        directory=phase.bridge.worker.hour._directory(journal,names)
        journal_directories[journal]=(names,directory)
        declaration=replace(self.declaration,ordinal=proposal['ordinal'])
        previous=claim['bootstrap_attempt_head'];ready_head=None
        for sequence in (2,3,4):
            if sequence==2:body=self._profile_body(claim_head)
            elif sequence==3:
                body=self._controller_body(previous,declaration=declaration,roots=roots,empty_namespace=False,
                    retained_views=genesis_views,retained_directories=genesis_directories)
                ready_body=body
            else:body=self._release_body(claim_head,claim,ready_head,ready_body)
            raw=encode(dict(sequence=sequence,previous=previous,body=body))
            path=Path(roots['bootstrap'])/f'{sequence:020d}.json'
            view=storage._read(path,self.declaration.max_record_bytes)
            if view[0]!=raw:raise ValueError('global release bootstrap prefix differs')
            if path in views and views[path]!=view:raise ValueError('release cross-reference changed')
            views[path]=view;previous=sha256(raw).hexdigest()
            if sequence==3:ready_head=previous
        local_terminal=None
        if terminal_name in names:
            path=journal/terminal_name;view=storage._read(path,self.declaration.max_record_bytes)
            value=json.loads(view[0])
            if (type(value) is not dict or set(value)!={'sequence','previous','body'}
                    or type(value['sequence']) is not int or value['sequence']!=5
                    or value['previous']!=previous or type(value['body']) is not dict
                    or value['body'].get('kind')!='normal_terminal' or encode(value)!=view[0]):
                raise ValueError('global release binding: invalid terminal suffix')
            views[path]=view;local_terminal=(sha256(view[0]).hexdigest(),value['body'])
        if phase.bridge.worker.hour._directory(journal,names)!=directory:
            raise ValueError('release bootstrap namespace changed during replay')
        return previous,(ready_head,ready_body),digest(body),local_terminal

    def _proposal(self):
        candidate=self._phase_candidate(self.declaration)
        self._check_phase_header()
        stored=json.loads(self._bootstrap._header)['declaration']['phase_manifest_candidate']
        if encode(candidate)!=encode(stored):raise ValueError('phase proposal differs from retained header')
        return self._proposal_for(self.declaration,self._slot['slot_id'],self.roots,
            self._bootstrap.genesis,candidate)

    def _origin(self,declaration=None):
        declaration=self.declaration if declaration is None else declaration
        payload=self._manifest.obligation(declaration.family,declaration.ordinal)['obligation_node']['record']['payload']
        point=payload['coordinate']
        return phase.binding.source_binding.H1SourceDeclaration(payload['split'],point['power']['source_start'],
            point['workload']['source_start'],point['power']['outage_seed'],self.declaration.run_configuration.source_config_sha256)

    def _profile_body(self,claim_head):
        config=self.declaration.run_configuration
        if type(config) is not RunConfiguration or encode(config.declared_profile())!=self._profile_bytes:
            raise ValueError('concrete run configuration/profile differs')
        return dict(kind='profile_checked',claim_head=claim_head,profile=self._profile,
            grid_manifest_sha256=phase.binding.source_binding.rts.RTS_GMLC_MANIFEST_SHA256,
            network_identity=config.network_sha256,dc_bus=config.dc_bus,stage_order=config.stage_order,
            observed_stage_count=len(config.stage_order),**FLAGS)

    def _load_network(self):
        """Static extraction only, called after the exact retained attempt/claim."""
        if not self._operation.locked() or self._replay()!='claimed_pre_source':
            raise ValueError('retained bootstrap claim required before network load')
        config=self.declaration.run_configuration;binding=phase.binding.source_binding
        self._check();own=self._implementation;source_implementation=binding.implementation_identity()
        path=Path(config.config_path);view=storage._read(path,1024**2)
        if sha256(view[0]).hexdigest()!=config.source_config_sha256:
            raise ValueError('source configuration content differs')
        manifest=binding.rts._source(config.upstream_root)
        network=binding.h1.static_network(binding.rts.load_rts_gmlc_chronological_data(Path(config.upstream_root)))
        binding.h1._network(network)
        units=network.data.generators
        order=(('operating_cost',None),*(('commitment',g.uid) for g in units if g.dispatch_mode=='committable'),
            *(('generation',g.uid) for g in units))
        if (network.identity!=config.network_sha256 or config.dc_bus not in {b.uid for b in network.data.buses}
                or order!=config.stage_order or len(order)>config.limits.max_stages):
            raise ValueError('loaded network/DC/stage profile differs')
        if self.declaration.selector_configuration is not None:
            self.declaration.selector_configuration.validate_normal(network.identity,order)
        if (binding.rts._source(config.upstream_root)!=manifest
                or manifest!=binding.rts.RTS_GMLC_MANIFEST_SHA256
                or storage._read(path,1024**2)!=view or implementation_identity()!=own
                or binding.implementation_identity()!=source_implementation):
            raise ValueError('static source changed during profile validation')
        self._check()
        return network

    def _parent_declaration(self,declaration=None,roots=None):
        declaration=self.declaration if declaration is None else declaration
        roots=self.roots if roots is None else roots
        config=declaration.run_configuration;parent=phase.base.parent
        return dict(schema=parent.SCHEMA,root=str(Path(roots['controller'])/'source_parent_non_authoritative'),
            network_identity=config.network_sha256,specification=asdict(config.specification),limits=asdict(config.limits),
            origin=asdict(self._origin(declaration)),dc_bus=config.dc_bus,hours=192,declared_stage_slots=192*len(config.stage_order),
            upstream_root=config.upstream_root,config_path=config.config_path,
            implementation_identity=parent.implementation_identity(),child_protocol=parent.CHILD_SCHEMA,
            parent_journal_protocol=parent.bounded.journal.SCHEMA)

    @staticmethod
    def _plain_directory(path):
        info=path.lstat()
        if not stat.S_ISDIR(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:
            raise ValueError('plain controller genesis directory required')
        return info.st_dev,info.st_ino

    def _controller_body(self,profile_head,*,declaration=None,roots=None,empty_namespace=True,
                         retained_views=None,retained_directories=None):
        """Reconstruct a still-empty controller and its five fixed genesis files.

        This is storage correspondence, not a persisted execution capability.
        Before global release the namespace must be empty. Afterwards only the
        fixed genesis is checked here; execution suffixes remain unaudited.
        """
        declaration=self.declaration if declaration is None else declaration
        roots=self.roots if roots is None else roots
        config=declaration.run_configuration;root=Path(roots['controller']);p=root/'source_parent_non_authoritative'
        parent=phase.base.parent;bounded=parent.bounded;decl=self._parent_declaration(declaration,roots)
        # The existing N writer uses canonical JSON WITHOUT our journal's LF.
        # Preserve its exact serialization when reconstructing its identities.
        metadata_digest=lambda value:sha256(phase.io.encode(value)).hexdigest()
        pid=metadata_digest(decl)
        j=p/'parent_events_non_authoritative';a=p/'parent_anchor_non_authoritative'
        journal=dict(schema=bounded.journal.SCHEMA,root=str(j),
            budget=asdict(bounded.chunks.ChunkContentBudget(384,2*bounded.chunks.METADATA_BYTES,384*2*bounded.chunks.METADATA_BYTES)),
            binding=pid,implementation=bounded.journal.implementation_identity())
        anchor=dict(schema=bounded.anchor.SCHEMA,root=str(a),binding=pid,max_records=385,
            implementation=bounded.anchor.implementation_identity())
        genesis=dict(schema=bounded.anchor.SCHEMA,anchor_identity=metadata_digest(anchor),sequence=0,
            previous_record_sha256=metadata_digest(anchor),previous_registry_head=None,registry_head=metadata_digest(journal),
            event_sha256=sha256(b'genesis').hexdigest())
        dirs={root:{'execution.lock','source_parent_non_authoritative','clock_bridge_non_authoritative','obligation_non_authoritative'},
            p:{'execution.lock','parent_events_non_authoritative','parent_anchor_non_authoritative'},
            j:{'execution.lock','header.json'},a:{'execution.lock','header.json','000.json'},
            root/'clock_bridge_non_authoritative':{'execution.lock','binding.json'},
            root/'obligation_non_authoritative':{'execution.lock','binding.json'}}
        def directory(path,names):
            if empty_namespace:return phase.bridge.worker.hour._directory(path,names)
            return self._plain_directory(path)
        directory_views={path:directory(path,names) for path,names in dirs.items()}
        views={}
        def read(path):
            raw,stamp=storage._read(path,phase.CAP);value=json.loads(raw)
            if phase.io.encode(value)!=raw:raise ValueError('canonical controller genesis required')
            views[path]=(raw,stamp);return value
        clock_path=root/'clock_bridge_non_authoritative'/'binding.json';clock=read(clock_path)
        if (set(clock)!={'schema','implementation','parent_identity','pid','creation_filetime','thread_id','clock','hours',*phase.bridge.FLAGS}
                or clock['schema']!=phase.bridge.SCHEMA or clock['implementation']!=phase.bridge.implementation_identity()
                or clock['parent_identity']!=pid or type(clock['hours']) is not int or clock['hours']!=192
                or any(type(clock[k]) is not int or clock[k]<=0 for k in ('pid','creation_filetime','thread_id'))
                or encode(clock['clock'])!=encode(phase.bridge.profile())
                or any(clock[k] is not False for k in phase.bridge.FLAGS)):
            raise ValueError('controller clock genesis differs')
        expected={j/'header.json':journal,a/'header.json':anchor,a/'000.json':genesis,
            root/'obligation_non_authoritative'/'binding.json':dict(schema=phase.SCHEMA,
                implementation=phase.implementation_identity(),parent_declaration=decl,parent_identity=pid,
                manifest_sha256=phase.binding.MANIFEST_PIN,family=declaration.family,ordinal=declaration.ordinal,
                hours=192,budget=asdict(config.budget),clock_binding_sha256=sha256(views[clock_path][0]).hexdigest(),**phase.FLAGS)}
        for path,value in expected.items():
            if encode(read(path))!=encode(value):raise ValueError('controller genesis binding differs')
        for path,view in views.items():
            if storage._read(path,phase.CAP)!=view:raise ValueError('controller genesis changed during replay')
        for path,names in dirs.items():
            if directory(path,names)!=directory_views[path]:
                raise ValueError('controller genesis namespace changed during replay')
        for retained,current in ((retained_views,views),(retained_directories,directory_views)):
            if retained is not None:
                for path,value in current.items():
                    if path in retained and retained[path]!=value:raise ValueError('retained release genesis differs')
                    retained[path]=value
        return dict(kind='controller_ready',profile_head=profile_head,parent_declaration=decl,parent_identity=pid,
            parent_head=metadata_digest(journal),parent_anchor_sha256=metadata_digest(genesis),
            files_sha256={path.relative_to(root).as_posix():sha256(view[0]).hexdigest() for path,view in views.items()},
            producer_implemented=False,live_controller_retained=False,**FLAGS)

    def _controller_artifacts(self):
        """Bounded partial-genesis audit. No partial tree is an execution state."""
        root=Path(self.roots['controller']);parent=root/'source_parent_non_authoritative'
        allowed={root:{'execution.lock','source_parent_non_authoritative','clock_bridge_non_authoritative','obligation_non_authoritative'},
            parent:{'execution.lock','parent_events_non_authoritative','parent_anchor_non_authoritative'},
            parent/'parent_events_non_authoritative':{'execution.lock','header.json'},
            parent/'parent_anchor_non_authoritative':{'execution.lock','header.json','000.json'},
            root/'clock_bridge_non_authoritative':{'execution.lock','binding.json'},
            root/'obligation_non_authoritative':{'execution.lock','binding.json'}}
        def snapshot():
            try:root.lstat()
            except FileNotFoundError:return None
            dirs={};files={};locks={}
            def visit(path):
                info=path.lstat()
                if not stat.S_ISDIR(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:
                    raise ValueError('plain partial controller directory required')
                names=set()
                with os.scandir(path) as entries:
                    for entry in entries:
                        if entry.name not in allowed[path]:raise ValueError('unexpected partial controller suffix')
                        names.add(entry.name)
                        if len(names)>len(allowed[path]):raise ValueError('partial controller namespace cap')
                dirs[path]=(names,phase.bridge.worker.hour._directory(path,names))
                for name in sorted(names):
                    child=path/name
                    if child in allowed:visit(child)
                    elif name=='execution.lock':
                        stamp=child.lstat()
                        if not stat.S_ISREG(stamp.st_mode) or getattr(stamp,'st_file_attributes',0)&0x400:
                            raise ValueError('plain controller lock file required')
                        locks[child]=(stamp.st_dev,stamp.st_ino,stamp.st_size,stamp.st_mtime_ns)
                    else:files[child]=storage._read(child,phase.CAP)
            visit(root)
            return dirs,files,locks
        first=snapshot()
        if snapshot()!=first:raise ValueError('partial controller artifacts changed during replay')
        return first

    def _continue_bootstrap(self):
        # Persistence exceptions are deliberately outside the typed input-stop
        # handlers: an unknown write must remain unknown and poison the owner.
        claim_head=self._claims()[self._slot['slot_id']][0]
        try:network=self._load_network()
        except Exception as error:
            self._record_pre_release_stop('profile',error);raise
        profile_head=self._bootstrap.append(self._profile_body(claim_head),expected_head=self._bootstrap.head)
        self._network=network
        controller=None
        try:
            try:
                controller=_BootstrapController(self,network)
                body=self._controller_body(profile_head)
            finally:
                if controller is not None:controller.close()
        except Exception as error:
            self._record_pre_release_stop('controller',error);raise
        # The live instance never enters owner state or a retain callback. Only
        # closed genesis metadata survives this partial bootstrap implementation.
        controller=None
        self._bootstrap.append(body,expected_head=self._bootstrap.head)
        if self._replay()!='controller_genesis_retained':raise ValueError('controller readback differs')
        raise ValueError('bootstrap release/capability entry not implemented; controller genesis retained')

    def _continue_owned_development(self):
        """Private development entry; default bootstrap remains metadata-only.

        Even a returned N0 numerical outcome remains unregistered globally and
        cannot be consumed as a paired or formal result by this draft.
        """
        claim_head=self._claims()[self._slot['slot_id']][0]
        try:network=self._load_network()
        except Exception as error:
            self._record_pre_release_stop('profile',error);raise
        profile_head=self._bootstrap.append(self._profile_body(claim_head),expected_head=self._bootstrap.head)
        self._network=network
        controller=owned.OwnedController(self,network)
        try:
            with controller._owned_transaction():
                body=self._controller_body(profile_head)
                self._bootstrap.append(body,expected_head=self._bootstrap.head)
                self._record_release()
                result=controller._owned_run()
                return dict(state='pending_N_terminal_registration',parent_head=result.head,
                    clock_terminal_sha256=controller.last_observation.terminal_sha256,
                    obligation_terminal_sha256=controller.last_obligation_observation.terminal_sha256,
                    retry_authorized=False,**FLAGS)
        finally:controller.close()

    def _observe_N0(self,root,declaration,observed):
        """Exact protocol prefix, with the Job scratch directory kept opaque.

        Scratch is not a protocol stream or numerical evidence. Its directory
        identity is retained; its contents grant no result or reuse credit.
        """
        parent=root/'source_parent_non_authoritative'
        clock=root/'clock_bridge_non_authoritative'
        obligation=root/'obligation_non_authoritative'
        events=parent/'parent_events_non_authoritative'
        anchors=parent/'parent_anchor_non_authoritative'
        directories={
            root:{'execution.lock','source_parent_non_authoritative','clock_bridge_non_authoritative',
                'obligation_non_authoritative','job_000_non_authoritative'},
            parent:{'execution.lock','parent_events_non_authoritative','parent_anchor_non_authoritative',
                'hour_000_non_authoritative'},
            clock:{'execution.lock','binding.json','000'},
            obligation:{'execution.lock','binding.json','000.binding.json','000.job.json','000.terminal.json'},
            events:{'execution.lock','header.json','001','002'},
            anchors:{'execution.lock','header.json','000.json','001.json','002.json'}}
        for path,names in directories.items():
            historical._observe(observed,'N0 directory '+str(path),
                phase.bridge.worker.hour._directory(path,names))
            raw,stamp=historical.history._read_single(path/'execution.lock',1)
            if raw!=b'0':raise ValueError('N0 lock bytes differ')
            historical._observe(observed,'N0 lock '+str(path),(raw,stamp))
        job=root/'job_000_non_authoritative'
        for path in (job,job/'worker_non_authoritative'):
            raw,stamp=historical.history._read_single(path/'execution.lock',1)
            if raw!=b'0':raise ValueError('N0 lock bytes differ')
            historical._observe(observed,'N0 lock '+str(path),(raw,stamp))
        for name in ('binding.json','000.binding.json','000.job.json','000.terminal.json'):
            path=obligation/name
            historical._observe(observed,'N0 obligation '+name,historical.history._read_single(path,phase.CAP))
        scratch=root/'job_000_non_authoritative'/'scratch_non_authoritative'
        historical._observe(observed,'N0 scratch directory',self._plain_directory(scratch))
        historical._observe_prefix(observed,root,1,len(self.declaration.run_configuration.stage_order))
        historical._observe_sources(observed,declaration)

    def _prepare_N0_terminal(self):
        """Internally rebuild a candidate body; this does not publish a terminal.

        No caller-supplied envelope, source key, terminal pin or body is accepted.
        The returned private evidence is fresh at return, never an execution
        capability. Registration and its write-window rechecks are separate.
        """
        self._check()
        if not self._operation.locked() or self._operation_nonce is None:
            raise ValueError('active bootstrap operation required for N0 evidence')
        nonce=self._operation_nonce
        local_rows=self._bootstrap.rows();global_rows=self._global.rows()
        if len(local_rows)!=4 or self._replay()!='execution_indeterminate':
            raise ValueError('exact released N0 prefix required')
        claim_head,claim=self._claims()[self._slot['slot_id']]
        release=self._registry()[self._slot['slot_id']]['release']
        ready_head,ready=local_rows[2];local_release_head,_=local_rows[3]
        def check_binding():
            self._check()
            if self._operation_nonce is not nonce or not self._operation.locked():
                raise ValueError('N0 evidence operation changed')
            if self._bootstrap.rows()!=local_rows or self._global.rows()!=global_rows:
                raise ValueError('N0 evidence release heads changed')
        return self._build_N0_terminal(claim_head,claim,release[0],(ready_head,ready),local_release_head,{},check_binding)

    @_guard_N0_route
    def _build_N0_terminal(self,claim_head,claim,release_head,ready_row,local_release_head,observed,check_binding,*,registry_scope=None):
        # Inputs are reconstructed only by this owner's journal replay/writer.
        # They are not public execution or detached-consumption credentials.
        ready_head,ready=ready_row
        root=Path(claim['proposal']['roots']['controller'])
        binding_pin=ready['files_sha256']['obligation_non_authoritative/binding.json']
        terminal_path=root/'obligation_non_authoritative'/'000.terminal.json'
        terminal_view=historical.history._read_single(terminal_path,phase.CAP)
        terminal_pin=sha256(terminal_view[0]).hexdigest()
        declaration=ready['parent_declaration']
        def binding_check():
            check_binding()
            if historical.history._read_single(terminal_path,phase.CAP)!=terminal_view:
                raise ValueError('N0 terminal changed during preparation')
        def check():
            binding_check()
            self._observe_N0(root,declaration,observed)
            binding_check()
        check()
        prepared=_prepare_N0(root,expected_binding_sha256=binding_pin,
            expected_terminal_sha256=terminal_pin,completed_hours=1,registry_scope=registry_scope)
        audit=json.loads(prepared.audit_payload)
        h=audit['historical_controller']
        if (historical.io.encode(audit)!=prepared.audit_payload
                or audit['implementation']!=historical.implementation_identity()
                or audit['parent_declaration']!=declaration
                or audit['controller_header_sha256']!=binding_pin
                or audit['controller_terminal_sha256']!=terminal_pin
                or type(h['completed_hours']) is not int or h['completed_hours']!=1
                or prepared.decision.relative_hour!=0
                or audit['decision_identity']!=prepared.decision.decision_identity
                or any(audit[k] is not False for k in FLAGS if k in audit)):
            raise ValueError('prepared N0 audit binding differs')
        pins=dict(slot_id=claim['slot_id'],claim_head=claim_head,
            claim_proposal_id=claim['claim_proposal_id'],global_release_head=release_head,
            bootstrap_release_head=local_release_head,controller_ready_head=ready_head,
            controller_binding_sha256=binding_pin,controller_terminal_sha256=terminal_pin,
            audit_payload_sha256=sha256(prepared.audit_payload).hexdigest(),
            historical_implementation=audit['implementation'],decision_identity=audit['decision_identity'],
            historical_verifier_identity=prepared.verifier_identity,
            parent_head=h['parent_head'],evidence_identity=h['evidence_identity'],
            normal_request_key=audit['normal_request_key'],child_head=audit['child_head'],
            child_archive_identity=audit['child_archive_identity'],projection_identity=audit['projection_identity'],
            projection_payload_sha256=audit['projection_payload_sha256'])
        check()
        pins['exact_n0_topology_identity']=digest(observed)
        return _N0_body(str(root),pins)

    def _record_release(self):
        """Private persistence seam; never returns an execution capability.

        The default bootstrap still stops at genesis. A later owned producer
        must enter this seam in the same operation before any current N effect.
        """
        self._check()
        if not self._operation.locked() or self._operation_nonce is None:
            raise ValueError('active bootstrap operation required')
        nonce=self._operation_nonce
        def check_operation():
            self._check()
            if self._operation_nonce is not nonce or not self._operation.locked():
                raise ValueError('release operation changed')
        try:
            if self._replay()!='controller_genesis_retained':raise ValueError('fresh unreleased genesis required')
            self._bootstrap.reserve(5);self._global.reserve(self._remaining_global_records())
            claim_head,claim=self._claims()[self._slot['slot_id']]
            ready_head,ready_body=self._bootstrap.rows()[-1]
            profile_head=self._bootstrap.rows()[-2][0]
            check_operation()
            if encode(self._controller_body(profile_head))!=encode(ready_body):raise ValueError('release genesis changed before write')
            body=self._release_body(claim_head,claim,ready_head,ready_body)
            release_head=self._bootstrap.append(body,
                expected_head=self._bootstrap.head)
            check_operation()
            if encode(self._controller_body(profile_head))!=encode(ready_body):raise ValueError('release genesis changed before global write')
            self._global.append(dict(kind='release_intent',slot_id=self._slot['slot_id'],claim_head=claim_head,
                claim_proposal_id=claim['claim_proposal_id'],bootstrap_release_head=release_head,
                bootstrap_release_body_sha256=digest(body),controller_ready_head=ready_head,**FLAGS),expected_head=self._global.head)
            check_operation()
            if encode(self._controller_body(profile_head))!=encode(ready_body):raise ValueError('release genesis changed during registration')
            if self._replay()!='execution_indeterminate':raise ValueError('release readback differs')
            check_operation()
        except BaseException:
            self.poisoned=True;raise

    def _N0_record_sizes(self):
        # All dynamic fields other than the fixed root are validated SHA256s.
        # The global sequence uses the largest representable reserved index.
        body=_N0_body(self.roots['controller'],{key:'0'*64 for key in N0_PINS})
        return (len(encode(dict(sequence=5,previous='0'*64,body=body))),
            len(encode(dict(sequence=self.declaration.max_global_events,previous='0'*64,
                body=_global_N0_body('0'*64,body)))))

    def _reserve_N0_bytes(self):
        local_bytes,global_bytes=self._N0_record_sizes()
        if local_bytes>self._bootstrap.cap or global_bytes>self._global.cap:
            raise ValueError('complete N0 terminal records exceed journal cap')

    def _continue_registered_development(self):
        """Private N0 integration route; paired/hour1+ production remains open."""
        nonce=self._operation_nonce
        self._continue_owned_development()  # Expires scope and closes all leases.
        if nonce is None or self._operation_nonce is not nonce:
            raise ValueError('N0 registration operation changed after controller close')
        return self._finish_N0_terminal(create_local=True)

    def _finish_N0_terminal(self,*,create_local):
        self._check()
        if type(create_local) is not bool or not self._operation.locked() or self._operation_nonce is None:
            raise ValueError('active N0 terminal registration operation required')
        nonce=self._operation_nonce
        expected_state='execution_indeterminate' if create_local else 'local_N_terminal_uncommitted'
        if self._replay()!=expected_state:raise ValueError('N0 registration state differs')
        local_rows=self._bootstrap.rows();global_rows=self._global.rows()
        if len(local_rows)!=(4 if create_local else 5):raise ValueError('N0 registration prefix differs')
        registered=self._registry()[self._slot['slot_id']]
        claim_head,claim=registered['claim'];release_head=registered['release'][0]
        ready_row=local_rows[2];local_release_head=local_rows[3][0]
        observed={}
        root=Path(claim['proposal']['roots']['controller']);declaration=ready_row[1]['parent_declaration']
        def check_binding():
            self._check()
            if self._operation_nonce is not nonce or not self._operation.locked():
                raise ValueError('N0 registration operation changed')
            if self._bootstrap.rows()!=local_rows or self._global.rows()!=global_rows:
                raise ValueError('N0 registration retained heads changed')
        def check():
            check_binding();self._observe_N0(root,declaration,observed);check_binding()
        def prepare():
            return self._build_N0_terminal(claim_head,claim,release_head,ready_row,local_release_head,
                observed,check_binding)
        self._reserve_N0_bytes();self._global.reserve(self._remaining_global_records())
        check_binding()
        body=prepare()
        if create_local:
            self._bootstrap.reserve(4)
            check()
            local_head=self._bootstrap.append(body,expected_head=local_rows[-1][0])
            local_rows=local_rows+[(local_head,body)]
        else:
            local_head,saved=local_rows[4]
            if encode(saved)!=encode(body):raise ValueError('retained local N0 terminal changed')
        check()
        if encode(prepare())!=encode(body):raise ValueError('N0 evidence changed after local retention')
        global_body=_global_N0_body(local_head,body)
        check()
        global_head=self._global.append(global_body,expected_head=global_rows[-1][0])
        global_rows=global_rows+[(global_head,global_body)]
        check()
        if self._replay()!='pending_post_N':raise ValueError('global N0 terminal readback differs')
        check()
        return dict(state='pending_post_N',bootstrap_head=local_head,global_head=global_head,
            parent_head=body['parent_head'],retry_authorized=False,**FLAGS)

    def reconcile_N0_terminal(self):
        """Explicit metadata-only recovery of an externally retained local N0.

        An unknown on-disk suffix is never adopted and N execution is never
        retried. Reopen with both externally retained heads before calling.
        """
        if not self._operation.acquire(False):raise ValueError('bootstrap operation active')
        self._operation_nonce=object()
        try:return self._finish_N0_terminal(create_local=False)
        except BaseException:
            self.poisoned=True;raise
        finally:
            self._operation_nonce=None;self._operation.release()

    def _record_pre_release_stop(self,stage,error):
        name=type(error).__name__
        if not name.isidentifier() or len(name)>100:raise ValueError('unrepresentable failure type; attempt remains unresolved') from error
        self._bootstrap.append(dict(kind='pre_release_stop',stage=stage,error_type=name,
            previous_head=self._bootstrap.head,status='unresolved',retry_authorized=False,**FLAGS),expected_head=self._bootstrap.head)

    def _replay(self):
        self._check();rows=self._bootstrap.rows();registry=self._registry()
        claims={slot:value['claim'] for slot,value in registry.items()}
        def finish(state,artifacts=None,check_artifacts=False):
            if self._registry()!=registry or self._bootstrap.rows()!=rows:
                raise ValueError('bootstrap changed during replay')
            self._check()
            if check_artifacts and self._controller_artifacts()!=artifacts:
                raise ValueError('partial controller artifacts changed during replay')
            return state
        if not rows:
            if self._slot['slot_id'] in claims:raise ValueError('global claim without bootstrap attempt')
            return finish('new')
        head,body=rows[0];proposal=self._proposal()
        if encode(body)!=encode(dict(kind='attempt',proposal=proposal,claim_proposal_id=digest(proposal))):
            raise ValueError('bootstrap attempt differs from fixed declaration')
        claim=claims.get(self._slot['slot_id'])
        if claim is None:
            if len(rows)!=1:raise ValueError('bootstrap suffix without claim')
            return finish('attempt_without_claim')
        if encode(claim[1])!=encode(dict(kind='claim',slot_id=self._slot['slot_id'],proposal=proposal,
                           claim_proposal_id=digest(proposal),bootstrap_attempt_head=head)):
            raise ValueError('global claim/bootstrap correspondence differs')
        index=1;state='claimed_pre_source'
        if len(rows)>index and rows[index][1].get('kind')=='profile_checked':
            if encode(rows[index][1])!=encode(self._profile_body(claim[0])):raise ValueError('loaded profile record differs')
            index+=1;state='profile_verified'
        if len(rows)>index and rows[index][1].get('kind')=='pre_release_stop':
            stop=rows[index][1];error=stop.get('error_type')
            if (type(error) is not str or not error.isidentifier() or len(error)>100
                    or encode(stop)!=encode(dict(kind='pre_release_stop',stage='profile' if index==1 else 'controller',
                        error_type=error,previous_head=rows[index-1][0],status='unresolved',retry_authorized=False,**FLAGS))):
                raise ValueError('pre-release stop differs')
            index+=1;state='pre_release_unresolved'
        elif len(rows)>index and state=='profile_verified':
            released=registry[self._slot['slot_id']]['release'] is not None
            if encode(rows[index][1])!=encode(self._controller_body(rows[index-1][0],empty_namespace=not released)):
                raise ValueError('controller ready record differs')
            index+=1;state='controller_genesis_retained'
        if len(rows)>index and state=='controller_genesis_retained':
            ready_head,ready_body=rows[index-1]
            if encode(rows[index][1])!=encode(self._release_body(claim[0],claim[1],ready_head,ready_body)):
                raise ValueError('bootstrap release record differs')
            index+=1
            state='execution_indeterminate' if registry[self._slot['slot_id']]['release'] else 'release_metadata_uncommitted'
        if len(rows)>index and state=='execution_indeterminate':
            registered=registry[self._slot['slot_id']]
            if registered['local_terminal']!=rows[index]:raise ValueError('local N0 registration differs')
            index+=1
            state='pending_post_N' if registered['terminal'] is not None else 'local_N_terminal_uncommitted'
        if len(rows)!=index:raise ValueError('bootstrap suffix not implemented')
        artifacts=None
        inspect_partial=state not in ('controller_genesis_retained','execution_indeterminate','release_metadata_uncommitted',
            'local_N_terminal_uncommitted','pending_post_N')
        if inspect_partial:
            artifacts=self._controller_artifacts()
            if artifacts is not None:
                if index<2 or rows[1][1].get('kind')!='profile_checked':
                    raise ValueError('controller artifacts without retained profile')
                if state=='profile_verified':state='controller_artifacts_uncommitted'
        return finish(state,artifacts,check_artifacts=inspect_partial)

    def inspect(self):
        if not self._operation.acquire(False):raise ValueError('bootstrap operation active')
        try:
            state=self._replay()
            return dict(state=state,global_head=self._global.head,bootstrap_head=self._bootstrap.head,
                slot_id=self._slot['slot_id'],producer_implemented=False,live_controller_retained=False,
                execution_artifacts_audited=False,
                N0_numerical_evidence_audited=state in ('local_N_terminal_uncommitted','pending_post_N'),
                registry_declaration_bound=self.declaration.registry_binding is not None,
                selector_configuration_bound=self.declaration.selector_configuration is not None,
                phase_manifest_candidate_bound=self.declaration.phase_archive is not None,
                phase_manifest_owner_attached=False,group_execution_roster_authenticated=False,
                all_sibling_execution_verified=False,normal_reuse_verified=False,
                selector_producer_connected=False,
                paired_source_correspondence_verified=False,
                recovery_required=state in ('controller_artifacts_uncommitted','pre_release_unresolved',
                    'release_metadata_uncommitted','execution_indeterminate','local_N_terminal_uncommitted'),
                retry_authorized=False,**FLAGS)
        finally:self._operation.release()

    def bootstrap(self):
        if not self._operation.acquire(False):raise ValueError('bootstrap operation active')
        self._operation_nonce=object()
        try:
            def execute():
                fresh=symbolic.inspect(self.declaration.symbolic_path,expected_sha256=self.declaration.symbolic_sha256)
                if fresh.raw!=self._manifest.raw:raise ValueError('symbolic declaration changed before bootstrap')
                if self._replay()!='new':raise ValueError('existing bootstrap attempt; no automatic retry')
                config=self.declaration.run_configuration
                if type(config) is not RunConfiguration or encode(config.declared_profile())!=self._profile_bytes:
                    raise ValueError('concrete run configuration/profile correspondence required before attempt')
                if self._fresh_registry_declaration()!=self._registry_view:
                    raise ValueError('registry declaration changed before attempt')
                self._check()
                self._reserve_N0_bytes()
                # Each existing claim still owes release and terminal records.
                # Reserving only this attempt would overbook the shared journal.
                self._bootstrap.reserve(8);self._global.reserve(self._remaining_global_records()+3)
                proposal=self._proposal()
                attempt=self._bootstrap.append(dict(kind='attempt',proposal=proposal,claim_proposal_id=digest(proposal)),
                    expected_head=self._bootstrap.head)
                self._check()
                self._global.append(dict(kind='claim',slot_id=self._slot['slot_id'],proposal=proposal,
                    claim_proposal_id=digest(proposal),bootstrap_attempt_head=attempt),expected_head=self._global.head)
                if self._replay()!='claimed_pre_source':raise ValueError('bootstrap claim readback differs')
                if self._fresh_registry_declaration()!=self._registry_view:
                    raise ValueError('registry declaration changed after claim')
                self._check()
                return self._continue_bootstrap()
            return _run_registry_operation(self,execute)
        except BaseException:
            self.poisoned=True;raise
        finally:
            self._operation_nonce=None
            self._operation.release()

    def close(self):
        if (os.getpid(),get_ident())!=(self._pid,self._thread):raise ValueError('bootstrap close owner differs')
        if self.closed:return
        if not self._operation.acquire(False):raise ValueError('bootstrap operation active')
        try:
            self.closed=True
            try:
                if self._original_controller is not None:self._original_controller.close()
            finally:
                for obj in (getattr(self,'_original_bootstrap',self._bootstrap),getattr(self,'_original_global',self._global)):
                    if obj is not None:obj.close()
        finally:self._operation.release()


def _install_N0_contract():
    names=('_check','_finish_N0_terminal','_build_N0_terminal','_registry','_replay',
        '_continue_registered_development','reconcile_N0_terminal')
    def shallow(value):
        if type(value) is types.FunctionType:
            return id(value),id(value.__code__),repr(value.__defaults__),repr(value.__kwdefaults__)
        return id(value),
    def state(value):
        return shallow(value)+(tuple((id(cell),shallow(cell.cell_contents))
            for cell in (value.__closure__ or ())) if type(value) is types.FunctionType else (),)
    bindings=[]
    def check(owner):
        for target,name,value,identity in bindings:
            live=target.get(name) if type(target) is dict else vars(target).get(name)
            if live is not value or state(live)!=identity:
                raise ValueError('definition-time N0 bootstrap route changed: '+name)
        if any(name in vars(owner) for name in names):
            raise ValueError('N0 bootstrap route instance shadow changed')
    def public_check(owner):return check(owner)
    def guard(fn):
        def checked(*args,**kwargs):
            check(args[0]);result=fn(*args,**kwargs);check(args[0]);return result
        return checked
    for name in names:setattr(BootstrapOwner,name,guard(getattr(BootstrapOwner,name)))
    for name in names:
        value=vars(BootstrapOwner)[name];bindings.append((BootstrapOwner,name,value,state(value)))
    for name in ('_prepare_N0','_N0_body','_global_N0_body','_run_registry_operation','_check_N0_contract'):
        value=public_check if name=='_check_N0_contract' else globals()[name]
        bindings.append((globals(),name,value,state(value)))
    for name in ('N0ValidationOperation','VerifiedHistoricalEnvelope','prepare','RegistryValidationScope',
            'registry_validation_scope','_close_registry_scope','_poison_registry_scope','_registry_scope_receipt'):
        value=getattr(historical_verifier,name);bindings.append((historical_verifier,name,value,state(value)))
    return public_check


_check_N0_contract=_install_N0_contract()
