"""Independent small encodings and event paths for conditional byte envelopes."""
from base64 import b64encode
from itertools import product
from types import SimpleNamespace

import pytest

from experiments import h1_owner_archive_budget_development_v1 as budget
from experiments import h1_phase_owner_development_v1 as owner
from experiments import h1_phase_ticket_holder_development_v1 as holder
from experiments import h1_raw_ingress_development_v1 as source
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver


@pytest.mark.parametrize('length', [0,1,2,3,4,7,8,9,1024])
def test_single_base64_length_agrees_with_actual_encoder(length):
    assert budget.base64_bytes(length)==len(b64encode(b'x'*length))


@pytest.mark.parametrize('caps', [(1,1,1),(3,2,4),(4,5,7),(3,9,20)])
def test_small_group_envelope_contains_every_allowed_length_vector(caps):
    stages,record_cap,total=caps
    bound=budget.packed_group_bound(max_stages=stages,max_record_bytes=record_cap,max_total_bytes=total)
    for n in range(stages+1):
        for lengths in product(range(1,record_cap+1),repeat=n):
            if sum(lengths)>total:continue
            raw=[b'x'*length for length in lengths]
            serialized=owner.encode([b64encode(value).decode('ascii') for value in raw])
            assert len(serialized)-1<=bound['json_list_bytes']


@pytest.mark.parametrize('N,B,A', [(1,3,3),(3,5,11),(4,4,9)])
def test_holder_formula_covers_superset_of_positive_body_length_vectors(N,B,A):
    bound=budget.holder_logical_bound(max_tickets=N,max_ticket_bytes=B,max_total_ticket_bytes=A)
    for n in range(N+1):
        for lengths in product(range(1,B+1),repeat=n):
            if sum(lengths)>A:continue
            for kind in holder.KINDS:
                total=0
                for index,length in enumerate(lengths,1):
                    ticket=holder.old.AppendTicket(budget.PIN,index,(budget.PIN,budget.PIN),kind,b'x'*length)
                    total+=len(holder.encode(dict(sequence=index,previous=budget.PIN,ticket=holder._ticket_payload(ticket))))
                assert total<=bound['ticket_file_bytes_bound']


@pytest.mark.parametrize('value', [{},[1,False,None],{'text':'中文/😀'},1,None])
def test_canonical_representative_tickets_pass_original_ticket_guard(value):
    raw=holder.encode(value)
    for kind in holder.KINDS:
        ticket=holder.old.AppendTicket(budget.PIN,1,(budget.PIN,budget.PIN),kind,raw)
        assert holder._ticket(ticket,len(raw)) is ticket
        wrapper=holder.encode(dict(sequence=1,previous=budget.PIN,ticket=holder._ticket_payload(ticket)))
        assert len(wrapper)==budget.holder_metadata_bytes(1,kind)+budget.base64_bytes(len(raw))


def test_metadata_all_kinds_and_decimal_boundaries_match_actual_wrapper():
    for ordinal in (1,9,10,99,100,575,576,999999):
        for kind in holder.KINDS:
            body=b'{}\n'
            ticket=holder.old.AppendTicket(budget.PIN,ordinal,(budget.PIN,budget.PIN),kind,body)
            actual=holder.encode(dict(sequence=ordinal,previous=budget.PIN,ticket=holder._ticket_payload(ticket)))
            assert len(actual)==budget.holder_metadata_bytes(ordinal,kind)+len(b64encode(body))
    maximum=max(budget.holder_metadata_bytes(576,kind) for kind in holder.KINDS)
    assert maximum==budget.holder_metadata_bytes(576,'episode_terminal')


def test_holder_bounds_are_independent_of_owner_manifest_bounds():
    owner_bounds=dict(max_tickets=32,max_ticket_bytes=1024,max_total_ticket_bytes=32*1024)
    holder_bounds=dict(max_tickets=576,max_ticket_bytes=2048,max_total_ticket_bytes=576*2048)
    assert budget.holder_logical_bound(**holder_bounds)['logical_content_bytes_bound']>budget.holder_logical_bound(**owner_bounds)['logical_content_bytes_bound']


@pytest.mark.parametrize('value', [{}, {'path':'中文/é/😀','values':['\n','"','\\',-0.0,1e308]}, {'nested':[{'a':1,'b':None,'c':False}]}])
def test_source_ascii_cap_covers_owner_json_object_representation(value):
    raw=source.encode(value)
    encoded=owner.encode(value)
    assert len(encoded)-1<=len(raw)


def test_lone_surrogate_is_not_an_owner_encodable_source_object():
    value={'path':'\ud800'}
    assert source.encode(value)
    with pytest.raises(UnicodeEncodeError):owner.encode(value)


def test_intent_envelope_covers_group_count_source_unicode_and_original_pack_boundary():
    ids=('a','中"文')
    limits=SimpleNamespace(max_stages=3,max_record_bytes=15,max_total_bytes=19)
    manifest=SimpleNamespace(lanes=tuple(SimpleNamespace(lane_id=name) for name in ids),replay_limits=limits)
    audit={'text':'é/😀/中文'}
    envelope=budget.intent_logical_bound(lane_ids=ids,source_audit_ascii_cap=len(source.encode(audit)),
        max_stages=3,max_record_bytes=15,max_total_bytes=19)
    reference=(b'x',b'y'*8,b'z'*10)
    actual={ids[0]:(b'k'*15,b'q'*4),ids[1]:(b'r'*9,)}
    packed=owner._pack_records(manifest,reference,actual)
    for hour in (0,9,10,99,100,191):
        raw=owner.encode(dict(hour=hour,terminal=budget.PIN,key=budget.PIN,source_audit=audit,
            records=packed,alternate=False,before_heads=(budget.PIN,budget.PIN)))
        assert len(raw)<=envelope['intent_body_bytes_bound']
    one_group=budget.packed_group_bound(max_stages=3,max_record_bytes=15,max_total_bytes=19)
    assert envelope['selector_groups']==3
    assert envelope['intent_body_bytes_bound']>3*one_group['base64_bytes']


@pytest.mark.parametrize('hours,W', [(1,0),(3,0),(168,0),(192,0),(192,7)])
def test_event_count_by_independent_enumeration(hours,W):
    kinds=['intent','outcome']
    for _ in range(1,hours):kinds.extend(('attempt','intent','outcome'))
    for _ in range(W):kinds.extend(('intent','witness'))
    result=budget.successful_event_counts(hours,alternate_witnesses=W)
    assert len(kinds)==result['events_after_last_paired']
    kinds.append('episode_terminal')
    assert len(kinds)==result['events_after_terminal']


@pytest.mark.parametrize('field,value', [('max_tickets',True),('max_tickets',0),('max_tickets',1000000),('max_ticket_bytes',False),('max_total_ticket_bytes',0)])
def test_rejects_noncanonical_holder_bound_domains(field,value):
    args=dict(max_tickets=3,max_ticket_bytes=9,max_total_ticket_bytes=20);args[field]=value
    with pytest.raises(ValueError):budget.holder_logical_bound(**args)
