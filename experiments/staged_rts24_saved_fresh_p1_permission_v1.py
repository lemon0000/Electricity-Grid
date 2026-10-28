"""Held P1 permission machinery. This version has no external authorization root."""
import builtins
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys
from threading import get_ident
import time
from types import CodeType,FunctionType

ROOT=Path(__file__).absolute().parents[1]
P1=ROOT/'results/tables/staged_rts24_native_v1_non_authoritative/p1_01'
ANCHOR=P1.parent/'p1_execution_review_01/postcheck_03.stdout.json'
ANCHOR_SHA='c6a25cd96c8a4a2cf293d41fe51bc7905db63fbc35253076f97e9239a4f22473'
SAVED_OUTPUT=ROOT/'results/tables/staged_rts24_saved_fresh_adoption_v1_non_authoritative'
RUNTIME=Path('D:/Miniconda3/envs/compute')
EXE=RUNTIME/'python.exe'
INHERITED=ROOT/'results/tables/staged_rts24_saved_journal_check_v1_non_authoritative/checks_01/component_source_pins.json'
FIXTURE_INPUTS=tuple(ROOT/name for name in ('configs/staged_deliverability_rts24_v1.DRAFT.yaml',
    'configs/staged_deliverability_small_case_v1.DRAFT.yaml','configs/staged_deliverability_network_v1.DRAFT.yaml'))
SOURCE_EPOCH='acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875'
MAX_EVENTS=16384
OUTER_BINDING=None
FALSE_FIELDS=('external_permission_verified','full_P1_content_verified','independent_root_verified','role_bootstrap',
    'permit_issued','run_authority','F_launch_admitted','actual_F','resource_admission','scientific_evidence_adopted','formal_result')
PROCESS=('subprocess.Popen','os.system','os.posix_spawn','os.fork','os.forkpty','os.startfile','os.startfile/2','_winapi.CreateProcess','pty.spawn')
MUTATIONS=('os.mkdir','os.remove','os.unlink','os.rmdir','os.rename','os.replace','os.link','os.symlink','os.chmod','os.chown','os.utime','os.truncate')


def require(value,message):
    if not value:raise ValueError(message)


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def creator():return os.getpid(),get_ident()


class PermissionUnavailable(PermissionError):pass


class ExternalAuthorization:
    __slots__=('creator','scope','source_epoch','deadline')
    def __new__(cls,*args,**kwargs):raise TypeError('authorization is supplied by an approved outer')
    def __setattr__(self,name,value):raise AttributeError('frozen external authorization')
    def __delattr__(self,name):raise AttributeError('frozen external authorization')
    def __reduce__(self):raise TypeError('external authorization cannot be serialized')


class P1Admission:
    __slots__=('creator','owner','plan','snapshot','guard','deadline','row')
    def __new__(cls,*args,**kwargs):raise TypeError('bootstrap-private admission required')
    def __setattr__(self,name,value):raise AttributeError('frozen admission')
    def __delattr__(self,name):raise AttributeError('frozen admission')
    def __reduce__(self):raise TypeError('admission cannot be serialized')


class PermissionState:
    __slots__=('runtime_type','creator','owner','boundary','plan','snapshot','phase','guard_phase','callback','callback_call',
        'sentinel','token','registry','admission','deadline','allowed','construction','construction_directories','counters','faults',
        'protected_functions','proof','revocation')
    def __new__(cls,*args,**kwargs):raise TypeError('creating permission program required')
    def __setattr__(self,name,value):raise AttributeError('frozen permission state')
    def __delattr__(self,name):raise AttributeError('frozen permission state')


def allocate(runtime_type):
    require(type(runtime_type) is type,'exact bootstrap runtime type required')
    state=object.__new__(PermissionState)
    values=dict(runtime_type=runtime_type,creator=creator(),owner=None,boundary=None,plan=None,snapshot=None,
        phase='DISABLED',guard_phase='NEW',callback=None,callback_call=None,sentinel=0,token=object(),registry={},
        admission=None,deadline=None,allowed=frozenset(),construction=frozenset(),construction_directories=frozenset(),
        counters=dict(selected=0,protected=0,allowed=0,writes=0,processes=0,mutations=0,construction_reads=0,runtime_reads=0,outside_reads=0),
        faults=[],protected_functions=(),proof=None,revocation=None)
    for name,value in values.items():object.__setattr__(state,name,value)
    object.__setattr__(state,'revocation',(revoke.__code__,dict(__builtins__={}),(state,object.__setattr__)))
    return state


def reject(state,kind):
    if len(state.faults)<4:state.faults.append(kind[:96])
    # A swallowed callback rejection cannot reopen a read window.
    object.__setattr__(state,'guard_phase','DENY')
    raise PermissionUnavailable('P1 guard rejected '+kind)


def state_entry(state):
    require(type(state) is PermissionState and state.creator==creator(),'creating exact permission state required')
    require(state.phase in ('DISABLED','OUTER_BOUND','ISSUED','CLAIMED','RETIRING','RETIRED','UNRESOLVED'),'permission phase differs')
    require(state.guard_phase in ('NEW','INSTALLED_DENY','READ_WINDOW','DENY','CLOSED'),'guard phase differs')
    return state


def bind_owner(state,owner):
    state_entry(state)
    require(state.owner is None and state.phase=='DISABLED' and state.guard_phase=='NEW','single disabled owner binding required')
    require(type(owner) is state.runtime_type and owner._creator[:2]==state.creator and owner._phase=='ADOPTED',
        'creating pre-import runtime required')
    require(owner._resource.owner is owner and owner._resource.phase=='LIVE','same native resource owner required')
    plan=json.loads(owner._raw)
    require(plan['source_epoch']==SOURCE_EPOCH and pin(canonical(plan['source_pins']))['sha256']==SOURCE_EPOCH,'fixed construction source map required')
    paths={os.path.normcase(str(ROOT/name)) for name in plan['source_pins']}
    paths.update(os.path.normcase(ref['path']) for ref in plan['producer_helpers'].values())
    for name in ('namespace_helper','import_helper','import_policy','startup_profile','import_profile'):
        if plan[name] is not None:paths.add(os.path.normcase(plan[name]['path']))
    require(len(paths)<=128 and all(Path(path).is_absolute() and Path(path).is_relative_to(ROOT) for path in paths),
        'fixed bounded construction read set required')
    directories={os.path.normcase(str(parent)) for path in paths for parent in Path(path).parents if parent.is_relative_to(ROOT)}
    object.__setattr__(state,'construction',frozenset(paths));object.__setattr__(state,'construction_directories',frozenset(directories))
    object.__setattr__(state,'owner',owner)
    return owner


def audit_callback(event,args,_state=None,_call=None):return _call(_state,event,args)


def guard_event(state,event,args):
    if state.guard_phase=='CLOSED':return
    if event=='electricity_grid.P1_guard.install':
        if creator()!=state.creator or len(args)!=1 or args[0] is not state.token or state.sentinel:reject(state,'installation_sentinel')
        object.__setattr__(state,'sentinel',1);return
    process=event in PROCESS or event.startswith(('os.spawn','os.exec'))
    mutation=event in MUTATIONS
    metadata=(event in ('object.__setattr__','object.__delattr__') and len(args)>=2
        and args[1] in ('__code__','__defaults__','__kwdefaults__') and any(args[0] is fn for fn in state.protected_functions))
    listing=event in ('os.listdir','os.scandir')
    if event!='open' and not listing and not process and not mutation and not metadata:return
    if creator()!=state.creator:reject(state,'foreign_thread')
    if state.counters['selected']>=MAX_EVENTS:reject(state,'event_cap')
    state.counters['selected']+=1
    if metadata:reject(state,'permission_callable_mutation')
    if process:state.counters['processes']+=1;reject(state,'process')
    if mutation:state.counters['mutations']+=1;reject(state,'mutation')
    if not args or not listing and len(args)<3:reject(state,'open_shape')
    name,mode,flags=(args[0],None,0) if listing else args[:3]
    if mode is not None and type(mode) is not str or type(flags) is not int:reject(state,'open_types')
    if type(mode) is str and any(letter in mode for letter in 'wax+') or type(flags) is int and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_APPEND|os.O_TRUNC):
        state.counters['writes']+=1;reject(state,'write')
    if type(name) not in (str,bytes):reject(state,'file_descriptor_or_opaque_open')
    path=os.path.normcase(os.path.abspath(os.fsdecode(name)))
    protected=any(path==base or path.startswith(base+os.sep) for base in
        (os.path.normcase(str(P1)),os.path.normcase(str(SAVED_OUTPUT)))) or path in tuple(os.path.normcase(str(value)) for value in (ANCHOR,EXE,INHERITED,*FIXTURE_INPUTS))
    if not protected:
        if path in (state.construction_directories if listing else state.construction):state.counters['construction_reads']+=1;return
        base=os.path.normcase(str(RUNTIME))
        if path==base or path.startswith(base+os.sep):state.counters['runtime_reads']+=1;return
        state.counters['outside_reads']+=1;reject(state,'unlisted_read')
    state.counters['protected']+=1
    permitted=path in state.allowed
    if listing:
        permitted=any(Path(path) in Path(file).parents for file in state.allowed if Path(file).is_relative_to(P1))
    if state.guard_phase!='READ_WINDOW' or state.phase not in ('ISSUED','CLAIMED') or not permitted:reject(state,'protected_read')
    owner=state.owner
    if state.faults or state.deadline is None or time.monotonic()>state.deadline:reject(state,'expired_or_faulted_window')
    if (owner._phase!='LIVE' or owner._resource.owner is not owner or owner._resource.phase!='LIVE'
            or owner._consumer_plan is not state.plan or owner._consume_state not in ('PREPARED','RUNNING')):
        reject(state,'owner_window')
    state.counters['allowed']+=1


def install_guard(state,boundary):
    state_entry(state);owner=state.owner
    require(state.guard_phase=='NEW' and owner is not None and owner._phase=='IMPORTING'
        and owner._boundary is boundary and boundary._creator==state.creator and boundary._state[:2]==('ACTIVE_B3',True),
        'install after B_S hook and before audit handoff')
    require(owner._audit_handed_off is False and owner._resource.guard['active'] is True,'predecessor guard must still be active')
    call=FunctionType(guard_event.__code__,globals(),'held_P1_guard_event',guard_event.__defaults__)
    callback=FunctionType(audit_callback.__code__,globals(),'held_P1_guard_callback',(state,call))
    object.__setattr__(state,'callback',callback);object.__setattr__(state,'callback_call',call)
    object.__setattr__(state,'protected_functions',tuple(fn for fn in globals().values() if type(fn) is FunctionType)+(callback,call))
    object.__setattr__(state,'boundary',boundary);object.__setattr__(state,'guard_phase','INSTALLED_DENY')
    sys.addaudithook(callback);sys.audit('electricity_grid.P1_guard.install',state.token)
    require(state.sentinel==1,'P1 guard installation absent')
    return state


def mechanical_issue(state,owner,plan,snapshot,deadline,allowed,outer_row):
    """State kernel for a future approved outer; not exported by this program."""
    state_entry(state)
    require(state.phase=='OUTER_BOUND' and state.guard_phase=='INSTALLED_DENY' and not state.faults
        and outer_row is state.registry.get('external') and outer_row is not None,'held outer registry row required')
    require(type(outer_row) is ExternalAuthorization and outer_row.creator==state.creator
        and outer_row.scope=='saved_P1_readonly_diagnostic' and outer_row.source_epoch==SOURCE_EPOCH
        and type(outer_row.deadline) is float and math.isfinite(outer_row.deadline) and deadline<=outer_row.deadline,
        'exact scoped outer authorization row required')
    require(owner is state.owner and owner._phase=='LIVE' and owner._import_profile_matched is True
        and owner._consume_state=='PREPARED' and owner._consumer_plan is plan and type(plan) is tuple and len(plan)==13
        and plan[0] is owner and owner._namespace is plan[2] and owner._adapter is plan[4],'original LIVE consumer binding required')
    require(type(deadline) is float and math.isfinite(deadline) and time.monotonic()<deadline,'current finite deadline required')
    require(type(allowed) is frozenset and 1<=len(allowed)<=689 and all(type(value) is str for value in allowed),'bounded exact read set required')
    fixed={os.path.normcase(str(path)) for path in (ANCHOR,EXE,INHERITED,*FIXTURE_INPUTS)};base=os.path.normcase(str(P1))+os.sep
    require(all(path==os.path.normcase(os.path.abspath(path)) and (path in fixed or path.startswith(base)) for path in allowed),
        'read set escaped saved P1/context scope')
    require(state.boundary is owner._boundary and state.boundary._state[:2]==('CLOSED',False),'closed original B_S boundary required')
    admission=object.__new__(P1Admission)
    row=(admission,owner,plan,snapshot,state,deadline,outer_row)
    for name,value in dict(creator=state.creator,owner=owner,plan=plan,snapshot=snapshot,guard=state,deadline=deadline,row=row).items():object.__setattr__(admission,name,value)
    state.registry['admission']=row
    for name,value in dict(plan=plan,snapshot=snapshot,deadline=deadline,allowed=allowed,admission=admission,
            phase='ISSUED',guard_phase='READ_WINDOW').items():object.__setattr__(state,name,value)
    return admission


def mechanical_verify(state,admission,owner,plan,snapshot,stage):
    state_entry(state)
    row=state.registry.get('admission')
    require(type(admission) is P1Admission and row is admission.row and row is not None
        and row[0] is admission and row[1] is owner is state.owner and row[2] is plan is state.plan
        and row[3] is snapshot is state.snapshot and row[4] is state and row[5]==state.deadline
        and row[6] is state.registry.get('external') and row[6] is not None,'exact retained permission registry row required')
    require(stage in ('prepare','entry','claim') and state.phase in ('ISSUED','CLAIMED')
        and state.guard_phase=='READ_WINDOW' and not state.faults and time.monotonic()<=state.deadline,
        'active unexpired read permission required')
    require(owner._phase=='LIVE' and owner._resource.owner is owner and owner._resource.phase=='LIVE'
        and owner._consumer_plan is plan and owner._consume_state in ('PREPARED','RUNNING'),'same live permission owner required')
    if stage in ('prepare','claim'):require(state.phase=='ISSUED' and owner._consume_state=='PREPARED','fresh permission reservation required')
    else:require(state.phase=='CLAIMED' and owner._consume_state=='RUNNING','claimed running permission required')
    if stage=='claim':
        require(state.phase=='ISSUED' and owner._consume_state=='PREPARED','single permission claim required')
        object.__setattr__(state,'phase','CLAIMED')
    return row


def revoke(state,put):
    if state.guard_phase!='CLOSED':put(state,'guard_phase','DENY')


def retire(state,admission):
    revoke(state,object.__setattr__)
    state_entry(state)
    if state.phase=='RETIRED':
        require(admission is state.admission,'same retired admission required');return
    if state.admission is not None:require(admission is state.admission,'foreign retirement admission')
    else:require(admission is None,'disabled issuer has no admission')
    object.__setattr__(state,'phase','RETIRED')


def close_guard(state):
    revoke(state,object.__setattr__)
    state_entry(state)
    if state.guard_phase=='CLOSED':return
    owner=state.owner
    require(owner is not None and owner._resource.phase=='CLOSED' and not any(owner._resource.pending)
        and owner._phase in ('CLOSED','UNRESOLVED'),'native owner must be terminal before guard close')
    if state.phase not in ('DISABLED','RETIRED'):object.__setattr__(state,'phase','UNRESOLVED')
    object.__setattr__(state,'guard_phase','CLOSED')
    state.registry.clear()
    for name in ('owner','boundary','plan','snapshot','admission','callback','callback_call','revocation'):
        object.__setattr__(state,name,None)
    for name in ('allowed','construction','construction_directories'):object.__setattr__(state,name,frozenset())
    object.__setattr__(state,'protected_functions',())


def observation(state):
    state_entry(state)
    value=dict(schema='staged_saved_F_P1_permission_observation_v1',authority='DRAFT_NONAUTHORITATIVE',
        issuer_phase=state.phase,guard_phase=state.guard_phase,installed=state.sentinel==1,
        counters=dict(state.counters),faults=list(state.faults),admission_present=state.admission is not None,
        **{name:False for name in FALSE_FIELDS})
    require(len(canonical(value))<=32768,'permission report cap');return value


def program_dispatch(held,operation,args):
    context,proof,state=held
    FunctionType(proof[0],proof[1])(*proof[2])
    # No globals, caller callback, bool, token or reconstructed state can make
    # this source version grant permission. A real outer requires a successor.
    if operation in ('issue','verify','claim'):raise PermissionError('no approved external P1 authorization root')
    functions={'bind_owner':'bind_owner','install_guard':'install_guard','retire':'retire','close_guard':'close_guard','report':'observation'}
    if operation not in functions or type(args) is not tuple:raise ValueError('closed permission operation required')
    return context[functions[operation]](state,*args)


def source_program(raw,runtime_type,utilities_raw):
    """Only loader-owned runtime identity is accepted; no external-cut parameter."""
    require(type(raw) is bytes and type(utilities_raw) is bytes and type(runtime_type) is type,'held source/runtime required')
    require(raw==Path(__file__).read_bytes(),'exact loader-held permission source required')
    require(pin(utilities_raw)==dict(bytes=40820,sha256='51682c35d4432633f143c7c53b78106e157eb17ef184adff6ebb30b73236b6a1'),
        'fixed source witness utilities required')
    utility=dict(__file__=str(ROOT/'experiments/staged_rts24_saved_fresh_retained_producer_v1.py'),__name__='_permission_source_utilities')
    exec(compile(utilities_raw,utility['__file__'],'exec',dont_inherit=True,optimize=0),utility,utility)
    namespace=dict(__file__=__file__,__name__='_P1_permission_private')
    exec(compile(raw,__file__,'exec',dont_inherit=True,optimize=0),namespace,namespace)
    require(namespace['OUTER_BINDING'] is None,'this source has no external root')
    witness=utility['_program_witness'](namespace,raw)
    isolated=dict(__builtins__=dict(vars(builtins)),FunctionType=FunctionType)
    proof=utility['_verify_programs'].__code__,isolated,((witness,),utility['_metadata'].__code__)
    context=utility['_private_functions'](namespace);state=context['allocate'](runtime_type)
    object.__setattr__(state,'proof',proof)
    return context['program_dispatch'].__code__,isolated,(context,proof,state)
