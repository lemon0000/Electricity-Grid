"""Bounded shared phase-data segment for the new public owner graph.

Only immutable phase science is reused. Dynamic journals, registry rows and N0
records are outside this cache. Instances and returned records grant no authority.
"""
from dataclasses import asdict
import errno
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from threading import Lock, get_ident
from types import FunctionType
from weakref import WeakKeyDictionary

from experiments import h1_phase_manifest_binding_development_v3 as binding
from experiments import h1_phase_dependency_validation_operation_development_v1 as kernel
from experiments import h1_validation_runtime_closure_development_v2 as runtime


SCHEMA='h1_phase_manifest_validation_operation_development_v1'
MAX_PROJECTS=256
MAX_CHECKS=4096
FLAGS=dict(formal_result=False,formal_execution_ready=False,resource_admission=False,
    native_execution_authorized=False,owner_consumption_authorized=False)


def implementation_identity(configuration):
    return binding.io.digest(binding.owner.encode([SCHEMA,
        sha256(Path(__file__).read_bytes()).hexdigest(),binding.implementation_identity(configuration),
        kernel.implementation_identity()]))


def _disjoint(science,roots):
    """Check the complete held inventory against declared dynamic namespaces."""
    base=kernel.predecessor.prior.ROOT
    paths={base/Path(name) for name in science['dependency_sha256']}
    paths.add(Path(kernel.predecessor.__file__))
    for module in (kernel.predecessor.prior,kernel.predecessor.prior.symbolic,
            kernel.predecessor.prior.symbolic.proof,kernel.predecessor.io):
        paths.add(Path(module.__file__))
    parents={parent for path in paths for parent in path.parents}
    ancestor_ids={kernel._plain(parent,directory=True)[:2] for parent in parents}
    for root in roots:
        if not kernel.handles._eligible(root):raise ValueError('canonical absolute dynamic root required')
        if any(path.is_relative_to(root) for path in paths):
            raise ValueError('dynamic root intersects held phase inputs')
        for path in (root,*root.parents):
            try:observed=kernel._plain(path,directory=True)
            except FileNotFoundError as error:
                if error.errno!=errno.ENOENT:raise
            else:
                if path==root and observed[:2] in ancestor_ids:
                    raise ValueError('dynamic root aliases a held phase ancestor')
    return len(paths)


def _capsule(plan,c,archive,roots,max_projects,max_checks,check_runtime):
    creator=(os.getpid(),get_ident());guard=Lock();state='new';window=None
    binding_check=binding._RUNTIME;encode=binding.owner.encode;decode=json.loads
    error_type=BaseException;describe=BaseException.__repr__;annotate=BaseException.add_note
    identity=implementation_identity(c);binding_id=binding.implementation_identity(c)
    request=encode([c.binding(),asdict(archive)]);first_failure=None
    science={};ordinals={};cache={};fingerprint=None;checks=projects=cache_hits=0
    kernel_receipt=None;disjoint_checks=0;seed_attempts=seed_returns=0
    kernel_type=kernel.PhaseDependencyValidationOperation
    kernel_enter=kernel_type.__enter__;kernel_exit=kernel_type.__exit__
    kernel_prepare=kernel_type.prepare_group;kernel_observe=kernel_type.receipt

    def poison(error):
        nonlocal first_failure
        if first_failure is None:
            try:first_failure=describe(error)
            except error_type:first_failure='<exception description unavailable>'

    def thread():
        if creator!=(os.getpid(),get_ident()):raise ValueError('phase segment requires creating thread')

    def config():
        check_runtime();binding_check()
        if encode([c.binding(),asdict(archive)])!=request:
            raise ValueError('phase segment configuration changed')

    def disjoint():
        nonlocal disjoint_checks
        for raw in science.values():
            if _disjoint(decode(raw),roots)!=kernel_observe(window)['inventory_paths']:
                raise ValueError('complete held phase inventory required for write separation')
        disjoint_checks+=1

    def check():
        nonlocal checks
        thread()
        try:
            config()
            if state!='active' or first_failure is not None or not guard.locked():
                raise ValueError('active unpoisoned phase segment required')
            checks+=1
            if checks>max_checks:raise ValueError('phase segment check bound exceeded')
            observed=kernel_observe(window)
            if (observed['state']!='active' or observed['first_failure'] is not None
                    or not observed['entry_physical_validation_completed'] or not observed['pending_handles']):
                raise ValueError('original active held phase window required')
        except error_type as error:poison(error);raise

    def enter():
        nonlocal state,window,fingerprint,seed_attempts,seed_returns
        thread()
        if state!='new' or not guard.acquire(False):
            error=ValueError('single-use nonreentrant phase segment required');poison(error);raise error
        try:
            config();state='acquiring'
            window=kernel_type(plan=plan,diagnostic_only=True)
            kernel_enter(window)
            for family,ordinal in plan:
                seed_attempts+=1;payload=kernel_prepare(window,family,ordinal);seed_returns+=1
                data=decode(payload)['scientific_projection']
                evidence=binding._evidence(data);g=data['predecessor_group'];group=g['group_identity']
                raw=encode(data)
                if group in science and science[group]!=raw:
                    raise ValueError('same phase group produced different science')
                science[group]=raw
                observed=(g['implementation_sha256'],binding_id,
                    evidence['verifier_implementation_sha256'],evidence['dependency_inventory_sha256'])
                if fingerprint is not None and fingerprint!=observed:
                    raise ValueError('phase seed inventories differ')
                fingerprint=observed
                for row in g['siblings']:
                    key=(family,row['ordinal'])
                    if key in ordinals and ordinals[key]!=group:raise ValueError('phase sibling groups overlap')
                    ordinals[key]=group
            disjoint();config()
            if implementation_identity(c)!=identity:raise ValueError('phase segment implementation changed')
            state='active'
        except error_type as error:
            poison(error);close(error);raise

    def prepare(family,ordinal):
        nonlocal projects,cache_hits
        check()
        try:
            projects+=1
            if (projects>max_projects or type(family) is not str or type(ordinal) is not int
                    or (family,ordinal) not in ordinals):
                raise ValueError('declared phase group and bounded exact request required')
            key=(family,ordinal)
            if key not in cache:
                cache[key]=binding._project(family,ordinal,c,archive,decode(science[ordinals[key]]),binding_id)
            else:cache_hits+=1
            check()
            record=cache[key]
            execution=encode(dict(schema=SCHEMA,active_implementation=identity,stable_audit_sha256=record[2],
                state=state,project=projects,kernel_payloads_returned=seed_returns,consumer_bound=False,
                detached_data=True,closed=False,**FLAGS))
            return binding.PreparedManifest(*record,execution)
        except error_type as error:poison(error);raise

    def get_fingerprint():
        check();return fingerprint

    def close(body_error=None):
        nonlocal state,kernel_receipt
        thread()
        if state=='closed':return
        primary=body_error
        if primary is not None:poison(primary)
        try:
            if state=='active':
                check();disjoint()
                if implementation_identity(c)!=identity:raise ValueError('phase segment implementation changed')
            elif state not in ('acquiring','cleanup_pending'):
                raise ValueError('entered phase segment required')
        except error_type as error:
            poison(error)
            if primary is None:primary=error
        try:
            if window is not None:
                kernel_exit(window,type(primary) if primary is not None else None,primary,None)
        except error_type as error:
            poison(error)
            if primary is None:primary=error
            elif primary is not error:
                try:annotate(primary,'phase kernel cleanup: '+describe(error))
                except error_type:pass
        finally:
            science.clear();ordinals.clear();cache.clear()
            try:kernel_receipt=None if window is None else kernel_observe(window)
            except error_type:kernel_receipt=None
            complete=window is None or kernel_receipt is not None and kernel_receipt['all_handles_closed']
            state='closed' if complete else 'cleanup_pending'
            if complete and guard.locked():guard.release()
        if body_error is None and primary is not None:raise primary

    def receipt():
        thread();check_runtime()
        return dict(schema=SCHEMA,active_implementation=identity,diagnostic_only=True,consumer_bound=False,
            declared_kernel_plan=decode(encode(plan)),maximum_projects=max_projects,maximum_checks=max_checks,
            declared_kernel_requests=len(plan),kernel_request_attempts=seed_attempts,
            kernel_payloads_returned=seed_returns,project_calls=projects,project_cache_hits=cache_hits,
            active_check_attempts=checks,
            dynamic_roots=[str(p) for p in roots],disjoint_checks=disjoint_checks,
            cached_science_cleared=not science and not ordinals and not cache,
            state=state,closed=state=='closed',first_failure=first_failure,
            original_guard_released=not guard.locked(),phase_kernel_receipt=kernel_receipt,
            lifecycle_complete=state=='closed' and first_failure is None and kernel_receipt is not None
                and kernel_receipt['lifecycle_complete'],per_call_physical_freshness=False,
            between_bookend_ABA_covered=False,detached_data=True,**FLAGS)

    return enter,prepare,get_fingerprint,check,close,receipt


def _define_api(check_runtime):
    records=WeakKeyDictionary()
    class PhaseManifestValidationOperation:
        __slots__=('__weakref__',)
        def __init__(self,*,plan,configuration,archive,dynamic_roots,maximum_projects,maximum_checks,diagnostic_only):
            check_runtime();binding._RUNTIME()
            if (self in records or diagnostic_only is not True or type(plan) is not tuple
                    or not 1<=len(plan)<=kernel.MAX_PREPARES
                    or any(type(row) is not tuple or len(row)!=2 or row[0]!='training_ub'
                        or type(row[0]) is not str or type(row[1]) is not int or row[1]<0 for row in plan)
                    or len(set(plan))!=len(plan)
                    or type(dynamic_roots) is not tuple or not dynamic_roots
                    or any(type(p) is not type(Path()) for p in dynamic_roots)
                    or type(maximum_projects) is not int or not 1<=maximum_projects<=MAX_PROJECTS
                    or type(maximum_checks) is not int or not 1<=maximum_checks<=MAX_CHECKS):
                raise ValueError('bounded exact immutable phase segment declarations required')
            binding._validate(plan[0][0],plan[0][1],configuration,archive)
            records[self]=_capsule(plan,configuration,archive,dynamic_roots,maximum_projects,maximum_checks,check_runtime)
        def __enter__(self):records[self][0]();return self
        def prepare(self,family,ordinal):return records[self][1](family,ordinal)
        def fingerprint(self):return records[self][2]()
        def check(self):return records[self][3]()
        def close(self):return records[self][4]()
        def retry_cleanup(self):return records[self][4]()
        def __exit__(self,kind,value,traceback):records[self][4](value)
        def receipt(self):return records[self][5]()
        def __copy__(self):raise TypeError('phase segment cannot be copied')
        def __deepcopy__(self,memo):raise TypeError('phase segment cannot be copied')
        def __reduce_ex__(self,protocol):raise TypeError('phase segment cannot be serialized')
    return PhaseManifestValidationOperation


_RUNTIME,_ARM=runtime.make_runtime(globals(),'shared phase data segment',alias='_RUNTIME')
PhaseManifestValidationOperation=_define_api(_RUNTIME)
_MODULES=tuple((module.__name__,module) for module in
    (sys.modules[__name__],binding,kernel,kernel.handles,runtime))


def _routes():
    if any(sys.modules.get(name) is not module for name,module in _MODULES):
        raise ValueError('canonical shared phase module registry changed')


def _attributes():
    rows=[]
    for module,names in ((binding,('_RUNTIME','_validate','_project','_evidence','implementation_identity','PreparedManifest')),
            (kernel,('PhaseDependencyValidationOperation','implementation_identity','_plain','predecessor')),
            (kernel.handles,('_eligible',)),(Path,('read_bytes','stat','exists','is_relative_to')),
            (os,('getpid',)),(json,('loads',)),(binding.owner,('encode',))):
        rows.extend((module,name,getattr(module,name)) for name in names)
    for cls in (PhaseManifestValidationOperation,kernel.PhaseDependencyValidationOperation):
        rows.extend((cls,name,value) for name,value in vars(cls).items()
            if isinstance(value,(FunctionType,property,staticmethod,classmethod)))
    for name in ('__truediv__','parents','is_absolute','anchor','parts','is_relative_to','__eq__','__hash__'):
        owner=next(cls for cls in Path.__mro__ if name in vars(cls))
        rows.append((owner,name,vars(owner)[name]))
    for _,module in _MODULES:
        rows.extend((module,name,getattr(module,name)) for name in
            ('__name__','__file__','__spec__','__loader__','__package__'))
        if module.__spec__ is not None:
            rows.extend((module.__spec__,name,getattr(module.__spec__,name))
                for name in ('name','origin','loader'))
        if module.__loader__ is not None:
            rows.extend((module.__loader__,name,getattr(module.__loader__,name))
                for name in ('name','path') if hasattr(module.__loader__,name))
    return tuple(rows)


_ARM(attributes=_attributes(),checks=(_routes,),ignored=('_ARM',))
del _ARM
