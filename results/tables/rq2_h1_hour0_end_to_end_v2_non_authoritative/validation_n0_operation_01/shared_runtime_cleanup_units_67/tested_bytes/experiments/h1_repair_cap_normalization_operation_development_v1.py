"""One-shot outer entry adapter for pure repair-cap normalization.

Every call retains the original two registry._pin reads/SHA checks and digest.
Only JSON/Fraction conversion of identical frozen bytes is reused. Consumers
imported inside this scope cannot be reused after restoration: exit the owned
isolated process after saving the closed receipt.
"""
from contextlib import contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from threading import get_ident
from types import FunctionType, ModuleType

SCHEMA='h1_repair_cap_normalization_operation_development_v1'
LABEL='approved_Rref_actual_repair_cap_min_Pmax_60ramp'


def _encode(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')


def _state(value):
    if type(value) is not FunctionType:return None
    return (value.__code__,id(value.__defaults__),repr(value.__defaults__),
        id(value.__kwdefaults__),tuple(sorted((k,id(v),repr(v)) for k,v in (value.__kwdefaults__ or {}).items())))


def implementation_identity():return sha256(Path(__file__).read_bytes()).hexdigest()


def operation(physical):
    """Return a single-use context and a creator-only, closed JSON receipt reader."""
    _RUNTIME()
    if type(physical) is not ModuleType:raise TypeError('explicit physical module required')
    original=physical.repair_mechanism_identity
    if type(original) is not FunctionType or original.__globals__ is not vars(physical):
        raise TypeError('original repair body required; nested adapters are refused')
    # Import-fixed consumers would remain pinned to the original function.
    for module in tuple(sys.modules.values()):
        if not isinstance(module,ModuleType):continue
        for row in vars(module).get('_SOURCE_FIXED',()):
            if type(row) is tuple and len(row)==3 and row[0] is physical and row[1]=='repair_mechanism_identity':
                raise ValueError('repair adapter must precede import-fixed consumers')
    creator=(os.getpid(),get_ident());data={};bindings=[]
    status=dict(phase='new',failure=None,calls=0,reads=0,route=None,route_state=None,receipt=None,
        entry_oracles=0,exit_oracles=0,routed_read_attempts=0,cache_build_reads=0,cache_build_attempts=0)
    own=implementation_identity();original_state=_state(original)

    def check(*,allow_failed=False):
        _RUNTIME()
        if creator!=(os.getpid(),get_ident()):raise ValueError('repair normalization creator required')
        if not allow_failed and status['failure'] is not None:raise ValueError('repair normalization is poisoned')
        expected=original if status['phase']=='new' else status['route']
        if status['phase'] not in ('new','active') or physical.repair_mechanism_identity is not expected:
            raise ValueError('original repair normalization route required')
        if _state(original)!=original_state or any(getattr(obj,key) is not value or _state(value)!=before
                for obj,key,value,before in bindings):raise ValueError('repair normalization dependency changed')
        if status['route'] is not None and _state(status['route'])!=status['route_state']:
            raise ValueError('repair normalization dispatch changed')

    def read(*,routed=False):
        check();registry=data['registry']
        if routed:status['routed_read_attempts']+=1
        raw=registry._pin(data['authority_path'],data['authority_pin']);status['reads']+=1
        if raw!=data['authority_raw']:raise ValueError('fresh repair authority bytes changed')
        if routed:status['routed_read_attempts']+=1
        raw=registry._pin(data['table_path'],data['table_pin']);status['reads']+=1
        if raw!=data['table_raw']:raise ValueError('fresh repair cap bytes changed')
        check()

    @contextmanager
    def scope():
        check()
        if status['phase']!='new':raise ValueError('repair normalization is single-use')
        error=None;cleanup_error=None;installed=False
        report=dict(authority_sha256=None,cap_table_sha256=None,digest=None)
        try:
            registry=physical.registry
            bindings.extend((obj,key,getattr(obj,key),_state(getattr(obj,key))) for obj,keys in (
                (physical,('registry','json','Q','_digest')),(physical.json,('loads',)),
                (physical.Q,('__new__','__init__','numerator','denominator')),
                (registry,('_pin','AUTHORITY','AUTHORITY_SHA','ROOT')),
            ) for key in keys)
            status['cache_build_attempts']+=1
            raw_a=registry._pin(registry.AUTHORITY,registry.AUTHORITY_SHA)
            status['cache_build_reads']+=1
            authority=physical.json.loads(raw_a);table_path=registry.ROOT/authority['cap_table_path']
            table_pin=authority['cap_table_sha256'];status['cache_build_attempts']+=1
            raw_t=registry._pin(table_path,table_pin);status['cache_build_reads']+=1
            table=physical.json.loads(raw_t)
            values=tuple((r['generator_uid'],str(physical.Q(r['proposed_cap_mw_fraction']).numerator),
                str(physical.Q(r['proposed_cap_mw_fraction']).denominator)) for r in table['rows'])
            status['entry_oracles']+=1;expected=original()
            if physical._digest(LABEL,values)!=expected:raise ValueError('original repair normalization differs')
            data.update(registry=registry,authority_path=registry.AUTHORITY,authority_pin=registry.AUTHORITY_SHA,
                authority_raw=raw_a,table_path=table_path,table_pin=table_pin,table_raw=raw_t,
                values=values,expected=expected,digest=physical._digest)
            report.update(authority_sha256=sha256(raw_a).hexdigest(),cap_table_sha256=sha256(raw_t).hexdigest(),
                digest=expected)
            read()
            def route():
                # A foreign thread cannot poison the creating thread's operation.
                if creator!=(os.getpid(),get_ident()):raise ValueError('repair normalization creator required')
                try:
                    read(routed=True);value=data['digest'](LABEL,data['values']);check()
                    if value!=data['expected']:raise ValueError('original repair digest changed')
                    status['calls']+=1
                    return value
                except BaseException as failure:
                    if status['failure'] is None:status['failure']=repr(failure)
                    raise
            status.update(route=route,route_state=_state(route),phase='active')
            physical.repair_mechanism_identity=route;installed=True
            check()
            yield
            check();read()
        except BaseException as failure:
            error=failure
            if status['failure'] is None:status['failure']=repr(failure)
            raise
        finally:
            restored=not installed
            if installed:
                if physical.repair_mechanism_identity is status['route']:
                    physical.repair_mechanism_identity=original;restored=True
                else:cleanup_error=ValueError('foreign repair alias preserved at exit')
            if restored and 'expected' in data:
                try:
                    status['exit_oracles']+=1
                    if original()!=data['expected']:raise ValueError('repair digest differs after restoration')
                except BaseException as failure:cleanup_error=failure
            data.clear();bindings.clear()
            # Generator locals are also released before the closed reader can
            # return. Route closures retained by import-fixed consumers hold an
            # empty data dictionary and fail after this scope.
            raw_a=raw_t=authority=table=values=registry=None
            status.update(phase='closed',route=None,route_state=None)
            status['receipt']=_encode(dict(schema=SCHEMA,implementation=own,**report,
                calls=status['calls'],adapter_pin_reads=status['reads']+status['cache_build_reads'],state='closed',
                cache_build_pin_reads=status['cache_build_reads'],cache_build_pin_read_attempts=status['cache_build_attempts'],
                routed_and_bookend_successful_pin_reads=status['reads'],
                first_failure=status['failure'],cleanup_error=None if cleanup_error is None else repr(cleanup_error),
                all_normalization_cache_entries_cleared=not data and not bindings,
                original_alias_restored=restored,per_routed_call_two_pin_order_preserved=True,
                overall_pin_read_schedule_preserved=False,
                routed_pin_read_attempts=status['routed_read_attempts'],
                original_oracle_invocations=dict(entry=status['entry_oracles'],exit=status['exit_oracles']),
                oracle_pin_reads_per_successful_invocation=2,oracle_reads_in_adapter_pin_counter=False,
                digest_recomputed_per_call=True,json_fraction_failure_timing_preserved=False,
                post_scope_consumer_reuse_allowed=False,process_must_exit_after_receipt=True,
                formal_result=False,resource_admission=False,native_execution_authorized=False))
            if cleanup_error is not None:
                if error is not None:error.add_note('repair normalization cleanup: '+repr(cleanup_error))
                else:raise cleanup_error

    def receipt():
        _RUNTIME()
        if creator!=(os.getpid(),get_ident()) or status['phase']!='closed' or status['receipt'] is None:
            raise ValueError('closed repair normalization creator required for receipt')
        return json.loads(status['receipt'])
    return scope(),receipt


def _install_runtime():
    namespace=vars(sys.modules[__name__])
    bindings=tuple((name,value,_state(value)) for name,value in namespace.items() if not name.startswith('__'))
    def verify():
        if namespace.get('_RUNTIME') is not verify or any(namespace.get(name) is not value or _state(value)!=before
                for name,value,before in bindings):raise ValueError('repair normalization helper scope changed')
    return verify


_RUNTIME=_install_runtime()
