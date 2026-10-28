"""Creating-bootstrap coordinator. No spawn, disk writes, or permission issuer."""
import builtins
from hashlib import sha256
import json
import os
from pathlib import Path
from threading import get_ident
from types import CodeType,FunctionType

COORDINATOR_FALSE=('parent_independent_P1_verified','external_permission_verified','scientific_evidence_adopted',
    'resource_admission','formal_result','run_authority','actual_F')


def coordinator_require(value,message):
    if not value:raise ValueError(message)


def coordinator_call(spec,*args):
    coordinator_require(type(spec) is tuple and len(spec)==3 and type(spec[0]) is CodeType and type(spec[1]) is dict,
        'creating bootstrap held dispatcher required')
    return FunctionType(spec[0],spec[1])(spec[2],*args)


def coordinator_revoke_packet(packet,state,code):
    coordinator_require(type(packet) is tuple and len(packet)==3 and type(packet[0]) is CodeType and packet[0]==code
        and type(packet[1]) is dict and set(packet[1])=={'__builtins__'} and type(packet[1]['__builtins__']) is dict
        and not packet[1]['__builtins__'] and type(packet[2]) is tuple and len(packet[2])==2
        and packet[2][0] is state and packet[2][1] is object.__setattr__,'original same-state read revoke packet required')


def coordinator_revoke(packet,state,code):
    coordinator_revoke_packet(packet,state,code)
    FunctionType(packet[0],packet[1])(*packet[2])
    coordinator_require(state.guard_phase in ('DENY','CLOSED'),'original read window was not revoked')


def coordinator_terminal(owner):
    resource=owner._resource
    coordinator_require(owner._phase in ('CLOSED','UNRESOLVED') and resource.phase=='CLOSED'
        and resource.owner is owner and not any(resource.pending),'physical producer owner terminal required')
    return dict(runtime_phase=owner._phase,resource_phase=resource.phase,consumer_state=owner._consume_state,
        close_calls=list(resource.close_calls),pending=[bool(value) for value in resource.pending],
        namespace_phase=owner._namespace._phase,cleanup_started=owner._cleanup_started)


def prepare_coordinator_cleanup(owner,permission,permission_raw):
    """Retained by the source-authenticated bootstrap before import/issuance."""
    coordinator_require(owner._phase=='ADOPTED' and owner._creator[:2]==(os.getpid(),get_ident()),
        'creating pre-import cleanup capture required')
    coordinator_require(type(permission) is tuple and len(permission)==3 and type(permission[2]) is tuple
        and len(permission[2])==3,'bootstrap-held permission program required')
    state=permission[2][2]
    coordinator_require(state.owner is owner and type(owner) is state.runtime_type and state.phase=='DISABLED'
        and state.guard_phase=='NEW' and state.admission is None,'same disabled guard owner required')
    coordinator_require(type(permission_raw) is bytes and (len(permission_raw),sha256(permission_raw).hexdigest())
        ==(18952,'0fa4420f1fb3ccfd70f234d7276de79bd780ce796b708ea58c912ebb9a74f9c7'),'fixed permission source required for cleanup capture')
    unit=compile(permission_raw,str(Path(__file__).absolute().with_name('staged_rts24_saved_fresh_p1_permission_v1.py')),
        'exec',dont_inherit=True,optimize=0)
    codes=[code for code in unit.co_consts if type(code) is CodeType and code.co_name==code.co_qualname=='revoke']
    coordinator_require(len(codes)==1,'unique source revoke code required')
    code=codes[0];coordinator_revoke_packet(state.revocation,state,code)
    close=vars(type(owner))['close']
    coordinator_require(type(close) is FunctionType and close.__closure__ is None,'original runtime close required')
    # Isolate the retained revoker's small namespace from the permission state.
    revoke=(code,dict(__builtins__={}),(state,object.__setattr__))
    return ((os.getpid(),get_ident()),owner,permission,state,revoke,
        (close.__code__,close.__globals__,close.__defaults__,close.__kwdefaults__),code)


def complete_producer(owner,bridge,permission,cleanup,output_root,started):
    """Called only with private specs retained by the creating bootstrap.

    The coordinator does not authenticate an arbitrary caller-provided program.
    Its source and all specs must be bound by that bootstrap's source witness.
    Current exported permission programs refuse issuance/claim; this function
    cannot turn their None root into authority.
    """
    # Only the bootstrap-held cleanup packet is read outside the protected
    # operation. Foreign callers cannot initiate cleanup of another actor.
    coordinator_require(type(cleanup) is tuple and len(cleanup)==7 and cleanup[0]==(os.getpid(),get_ident())
        and cleanup[1] is owner and cleanup[2] is permission,'creating original cleanup packet required')
    _,_,_,state,revoke,held_close,revoke_code=cleanup
    producer=None;bundle=None;primary=None;carrier=None;secondary=[];result=None
    try:
        coordinator_require(owner._creator[:2]==(os.getpid(),get_ident()) and owner._phase=='LIVE'
            and owner._import_profile_matched is True and owner._consume_state=='PREPARED','same prepared LIVE owner required')
        coordinator_require(state.owner is owner,'original outer guard owner required')
        bundle=coordinator_call(bridge,'bundle',owner,())
        inner=bundle[2][3][2][0]
        coordinator_require(inner['_ADMITTED_OWNER'] is owner and inner['_P1_PERMISSION_PROGRAM'] is permission,
            'same bundle permission/owner required')
        authority=inner['_P1_AUTHORITY']
        producer=coordinator_call(bundle,None,'prepare',(owner,authority),{})
        coordinator_require(producer._owner is owner and producer._creator==(os.getpid(),get_ident()),'exact creating producer required')
        coordinator_require(coordinator_call(bundle,producer,'run',(output_root,),dict(started=started)) is producer,'same G0 producer required')
        for stage in ('G2','G3'):
            coordinator_require(coordinator_call(bundle,producer,stage,(),{}) is producer,'same bookend producer required')
        report=coordinator_call(bundle,producer,'close',(),{})
        terminal=coordinator_terminal(owner)
        coordinator_require(producer._phase=='CLOSED' and producer._failure is None and terminal['runtime_phase']=='CLOSED'
            and terminal['consumer_state']=='CONSUMED' and terminal['close_calls']==[1,1],'successful producer close required')
        coordinator_call(permission,'close_guard',())
        permission_report=coordinator_call(permission,'report',())
        coordinator_require(permission_report['issuer_phase']=='RETIRED' and permission_report['guard_phase']=='CLOSED'
            and permission_report['faults']==[],'retired permission and closed guard required')
        result=dict(schema='staged_saved_F_complete_producer_data_v2',authority='DRAFT_NONAUTHORITATIVE',
            producer=report,permission=permission_report,terminal=terminal,
            **{key:False for key in COORDINATOR_FALSE})
        coordinator_require(len(json.dumps(result,sort_keys=True,separators=(',',':'),ensure_ascii=True,
            allow_nan=False).encode('ascii'))<=262144,'complete producer data cap; transport needs one extra newline byte')
        coordinator_call(bridge,'release',owner,())
    except BaseException as error:primary=error
    if primary is not None:
        # This packet was retained before prepare; verifier/raw drift cannot
        # prevent denial. Native close remains independent of permission proof.
        try:coordinator_revoke(revoke,state,revoke_code)
        except BaseException as error:secondary.append(error)
        if producer is not None and producer._phase not in ('CLOSED','FAILED','UNRESOLVED'):
            try:coordinator_call(bundle,producer,'bootstrap_abort',(primary,),{})
            except BaseException as error:
                if error is producer._failure and error is not primary:carrier=error
                elif error is not primary:secondary.append(error)
        if producer is None:
            try:coordinator_call(permission,'retire',(state.admission,))
            except BaseException as error:secondary.append(error)
        if not owner._cleanup_started:
            try:
                close=FunctionType(held_close[0],held_close[1],'held_coordinator_runtime_close',held_close[2])
                close.__kwdefaults__=held_close[3];close(owner,primary)
            except BaseException as error:
                expected=held_close[1].get('LocalRuntimeUnresolved')
                if not (expected is not None and type(error) is expected and error.owner is owner
                        and error.primary is primary and not error.secondary):secondary.append(error)
        try:coordinator_terminal(owner)
        except BaseException as error:secondary.append(error)
        try:coordinator_call(permission,'close_guard',())
        except BaseException as error:secondary.append(error)
        if carrier is not None:
            if secondary:raise carrier from BaseExceptionGroup('complete producer cleanup errors',tuple(secondary))
            raise carrier
        if secondary:raise primary from BaseExceptionGroup('complete producer cleanup errors',tuple(secondary))
        raise primary
    return result
