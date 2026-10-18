"""Scoped normalization of the two freshly pinned, frozen repair-cap inputs.

The original authority/table reads and SHA checks still run on every request.
Only JSON/Fraction conversion of identical bytes is reused. The digest itself
is evaluated on every request. This is a declared development entry adapter.
"""
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
import json
import os
from pathlib import Path
from threading import get_ident
from types import FunctionType, ModuleType

SCHEMA='h1_repair_cap_normalization_operation_development_v1'
LABEL='approved_Rref_actual_repair_cap_min_Pmax_60ramp'


def _state(value):
    return (value.__code__,value.__defaults__,value.__kwdefaults__) if type(value) is FunctionType else None


def implementation_identity():
    return sha256(Path(__file__).read_bytes()).hexdigest()


class RepairCapNormalization:
    """One creator, one enter/exit; install before import-fixed consumers load."""
    def __init__(self,physical):
        if type(physical) is not ModuleType:raise TypeError('explicit physical module required')
        self.physical=physical
        self.registry=physical.registry
        self.original=physical.repair_mechanism_identity
        self.creator=(os.getpid(),get_ident())
        self.phase='new';self.failure=None;self.calls=0;self.reads=0
        self.authority_raw=self.table_raw=None;self.values=None;self.table=None
        self.authority=None;self.expected=None;self.route=None
        self.bindings=tuple((obj,key,getattr(obj,key),_state(getattr(obj,key))) for obj,keys in (
            (physical,('registry','json','Q','_digest')),
            (physical.json,('loads',)),
            (physical.Q,('__new__','__init__','numerator','denominator')),
            (self.registry,('_pin','AUTHORITY','AUTHORITY_SHA','ROOT')),
        ) for key in keys)
        self.original_state=_state(self.original)
        self.own=implementation_identity()

    def _check(self):
        if self.creator!=(os.getpid(),get_ident()) or self.failure is not None:
            raise ValueError('original repair normalization creator and clean lifetime required')
        if self.phase not in ('new','active') or self.physical.repair_mechanism_identity is not (
                self.original if self.phase=='new' else self.route):
            raise ValueError('original repair normalization route required')
        if _state(self.original)!=self.original_state or any(
                getattr(obj,key) is not value or _state(value)!=before
                for obj,key,value,before in self.bindings):
            raise ValueError('repair normalization dependency changed')

    def _read(self):
        self._check()
        authority=self.registry._pin(self.registry.AUTHORITY,self.registry.AUTHORITY_SHA)
        self.reads+=1
        table=self.registry._pin(self.table,self.authority['cap_table_sha256'])
        self.reads+=1
        if authority!=self.authority_raw or table!=self.table_raw:
            raise ValueError('fresh repair authority or cap bytes changed')
        self._check()

    def __enter__(self):
        self._check()
        if self.phase!='new':raise ValueError('repair normalization is single-use')
        # The baseline function remains installed throughout initial equality.
        self.authority_raw=self.registry._pin(self.registry.AUTHORITY,self.registry.AUTHORITY_SHA)
        self.authority=self.physical.json.loads(self.authority_raw)
        self.table=self.registry.ROOT/self.authority['cap_table_path']
        self.table_raw=self.registry._pin(self.table,self.authority['cap_table_sha256'])
        rows=self.physical.json.loads(self.table_raw)['rows']
        self.values=tuple((row['generator_uid'],str(self.physical.Q(row['proposed_cap_mw_fraction']).numerator),
            str(self.physical.Q(row['proposed_cap_mw_fraction']).denominator)) for row in rows)
        self.expected=self.original()
        if self.physical._digest(LABEL,self.values)!=self.expected:
            raise ValueError('complete original repair normalization differs')
        self._read()
        def route():
            try:
                self._read()
                value=self.physical._digest(LABEL,self.values)
                self._check()
                if value!=self.expected:raise ValueError('original repair digest changed')
                self.calls+=1
                return value
            except BaseException as error:
                if self.failure is None:self.failure=repr(error)
                raise
        self.route=route;self.phase='active'
        self.physical.repair_mechanism_identity=route
        self._check()
        return self

    def __exit__(self,kind,error,traceback):
        if self.creator!=(os.getpid(),get_ident()):
            raise ValueError('repair normalization exit requires original creator')
        cleanup_error=None
        try:
            self._read()
        except BaseException as failure:cleanup_error=failure
        finally:
            # Always restore the captured callable, even after replacement.
            self.physical.repair_mechanism_identity=self.original
            self.phase='closed'
        try:
            if self.original()!=self.expected:
                raise ValueError('repair digest differs after restoration')
        except BaseException as failure:
            if cleanup_error is None:cleanup_error=failure
        self.values=None
        if error is not None:
            if cleanup_error is not None:error.add_note('repair normalization cleanup: '+repr(cleanup_error))
            return False
        if cleanup_error is not None:raise cleanup_error
        return False

    def receipt(self):
        return dict(schema=SCHEMA,implementation=self.own,state=self.phase,calls=self.calls,
            original_pin_reads=self.reads,authority_sha256=sha256(self.authority_raw).hexdigest(),
            cap_table_sha256=sha256(self.table_raw).hexdigest(),digest=self.expected,
            normalization_cache_cleared=self.values is None,first_failure=self.failure,
            original_pin_read_schedule_preserved=True,digest_recomputed_per_call=True,
            pure_normalization_reused=True,formal_result=False,resource_admission=False,
            native_execution_authorized=False)
