"""One owned synthetic N0, close its owner, then measure the original source.

This is a bounded cost diagnostic for the hour0 path. No roster, common owner,
selector Parent, native call or complete-chain credential is produced.
"""
from dataclasses import fields,is_dataclass
from fractions import Fraction
import json
from pathlib import Path
from time import perf_counter

import pytest

from tests import test_h1_hour0_end_to_end_development_v4 as fixture
from tests.test_h1_hour0_end_to_end_development_v4 import (
    example,setup,numerical,environment,synthetic_reports,supplied,no_solver,saved,retained)


@pytest.fixture
def prepared(numerical,environment,synthetic_reports,tmp_path,monkeypatch):
    yield from fixture.complete_group.__wrapped__(numerical,environment,synthetic_reports,tmp_path,monkeypatch)


def _literal(value):
    if type(value) in (str,int,bool,type(None)):return [type(value).__name__,value]
    if type(value) is float:return ['float',value.hex()]
    if type(value) is bytes:return ['bytes',value.hex()]
    if isinstance(value,Fraction):return ['fraction',value.numerator,value.denominator]
    if is_dataclass(value):return ['dataclass',type(value).__module__,type(value).__qualname__,
        [[field.name,_literal(getattr(value,field.name))] for field in fields(value)]]
    if type(value) in (tuple,list):return [type(value).__name__,[_literal(item) for item in value]]
    if type(value) is dict:return ['dict',sorted([[_literal(k),_literal(v)] for k,v in value.items()],key=repr)]
    if type(value) in (set,frozenset):return [type(value).__name__,sorted([_literal(item) for item in value],key=repr)]
    raise TypeError('unsupported complete source field '+str(type(value)))


def test_closed_owned_n0_original_source_cost(prepared,tmp_path):
    s,declaration,captured,final=prepared
    assert not final and fixture.m.SCHEMA=='h1_bootstrap_integration_development_v2'
    start=perf_counter();times={}
    owner=s.open(declaration=declaration)
    times['owner_open']=perf_counter()-start;fixture.trace('cost_owner_open')
    try:
        begin=perf_counter();result=owner.bootstrap();times['N0_registration']=perf_counter()-begin
        assert result['state']=='pending_post_N'
        body=owner._bootstrap.rows()[-1][1]
        root=Path(body['controller_root'])
        args=dict(expected_binding_sha256=body['controller_binding_sha256'],
            expected_terminal_sha256=body['controller_terminal_sha256'],completed_hours=1,
            expected_registry_identity=json.loads(Path(declaration.registry_binding.path).read_bytes())['expected_registry_identity'])
        fixture.trace('cost_N0_registered')
        job=json.loads((root/'job_000_non_authoritative/observation.json').read_bytes())
        assert job['exit_code']==0 and job['whole_job_quiescent'] is True
    finally:
        begin=perf_counter();owner.close();times['owner_close']=perf_counter()-begin
        fixture.trace('cost_owner_closed')
    assert len(captured)==1 and all(lease.stream is None for lease in captured[0]._owned_original_cleanup)
    source=fixture.common.phase.source
    begin=perf_counter();current=source.prepare(root,**args);times['original_source_prepare']=perf_counter()-begin
    assert type(current) is source.ExactSourceCurrent
    audit=json.loads(current.source_projection_audit_payload)
    assert audit['controller_binding_sha256']==args['expected_binding_sha256']
    assert audit['controller_terminal_sha256']==args['expected_terminal_sha256']
    assert audit['registry_identity']==args['expected_registry_identity'] and audit['completed_hours']==1
    assert (audit['full_numerical_hour_replays'],audit['fresh_byte_context_revalidations'],
        audit['recomputed_on_revalidation'])==(4,4,False)
    assert current.prepared_current.audit_payload==current.source_projection_audit_payload
    assert current.prepared_current.decision.normal.decision_identity==body['decision_identity']
    (tmp_path/'source_audit.json').write_bytes(current.source_projection_audit_payload)
    projection=source.io.encode(_literal(current))
    (tmp_path/'source_complete_fields.json').write_bytes(projection)
    times['body_total']=perf_counter()-start
    report=dict(scope='one fresh owned Bootstrap2 N0 then original source after owner close',
        source_arguments=dict(root=str(root),**args),times=times,N0_terminal=body,
        source_audit_sha256=source.io.digest(current.source_projection_audit_payload),
        source_complete_fields_sha256=source.io.digest(projection),synthetic_jobs=1,real_native_calls=0,
        original_source_prepares=1,owner_closed_before_source=True,full_hour0_chain_passed=False,
        formal_result=False,resource_admission=False,native_execution_authorized=False)
    (tmp_path/'n0_source_cost_report.json').write_bytes(fixture.m.encode(report))
    fixture.trace('cost_original_source_complete')
