"""Independent stdlib carriers and expected declarations; no validator import."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import struct
ROOT=Path(__file__).resolve().parents[4]
CONTRACT=ROOT/'results/tables/staged_rts24_saved_fresh_wire_contract_v1_non_authoritative/checks_01'
def raw(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def sha(v):return sha256(v).hexdigest()
def image(v):return sha(raw(v))
def pin(v):return dict(bytes=len(v),sha256=sha(v))
def slot(v,size=4096,header=False):
    assert 0<len(v)<=size-44
    return struct.pack('<I',len(v))+v+b'\0'*(size-44-len(v))+sha256(v).digest()+(b'GRIDHDR1' if header else b'GRIDFRM1')
def decode(v):return v[4:4+struct.unpack('<I',v[:4])[0]]
def registry():return json.loads((CONTRACT/'wire_domains.json').read_bytes())
def value(name,**fields):
    spec=registry()['schemas'][name]['fields'];result={n:r['literal'] for n,r in spec.items() if isinstance(r,dict) and 'literal' in r}
    result.update(fields);assert set(result)==set(spec),(name,set(spec)-set(result));return result
def stage(case,role,*,error_at=None,early=False,prefix_count=None):
    item=case['roles'][role];rules=registry()['cross_field_constraints']['stage_frames']['per_role'][role]
    slots=[] if early else [item['bootstrap_slot']];previous='0'*64 if early else sha(raw(item['bootstrap']))
    phases=['error'] if early else [r['phase'] for r in rules['phase_frames']]+['terminal']
    for i,phase in enumerate(phases,0 if early else 1):
        if error_at==i:phase='error'
        frame=value(role+'_stage_frame',sequence=i,phase=phase,binding_sha=sha(item['stage_header_slot']),previous_sha=previous,
            producer_pid=item['owner_identity'][0],producer_creation_filetime=item['owner_identity'][1],
            stamp=item['join_now']+.1+i*.01,error_code='bootstrap' if phase=='error' else None)
        encoded=raw(frame);slots.append(slot(encoded));previous=sha(encoded)
        if phase=='error':break
    if prefix_count is not None:slots=slots[:prefix_count]
    return tuple(slots+[b'\0'*4096]*(16-len(slots)))
def mailbox(case,kind,payload):
    rules=registry()['cross_field_constraints']['mailbox_kinds'][kind];header=json.loads(decode(case['header_slot']))
    producer=case['roles']['controller']['owner_identity'] if kind=='controller_return' else header['broker_identity']
    previous='0'*64 if rules['previous_kind'] is None else sha(decode(case['mail_slots'][rules['previous_kind']]))
    envelope=dict(kind=kind,sequence=rules['sequence'],previous_sha=previous,producer_identity=list(producer),
        direction_nonce=header['direction_nonces'][rules['direction']],binding_sha=sha(case['header_slot']),payload=payload)
    sizes=dict(json.loads((CONTRACT/'wire_templates.json').read_bytes())['mailbox_slots'])
    return slot(raw(envelope),sizes[kind])
def failure(case,role):
    owner={'host':(1001,2001),'broker':(1002,2002),**{r:v['owner_identity'] for r,v in case['roles'].items()}}[role]
    return value(role+'_failure',context_sha=sha(case['base_case']['context_raw']),request_sha=sha(case['base_case']['request_raw']),
        owner_identity=list(owner),phase='return',primary_index=0,
        exceptions=[dict(index=i,code='unknown',exception_type='ValueError',message='declared error '+str(i),truncated=False) for i in range(3)],
        cleanup_indices=[2,1],omitted_count=0,incomplete=False,may_have_published=False,expected_publication_pin=None,
        observed_at=1030.,quiet_known=False)
def build(case):
    controller=case['roles']['controller'];ctx=sha(case['base_case']['context_raw']);req=sha(case['base_case']['request_raw'])
    binding=value('controller_binding',context_sha=ctx,request_sha=req,ACK_sha=sha(raw(json.loads(decode(case['mail_slots']['ack']))['payload'])),
        entry_header_sha=sha(controller['entry_slots'][0]),stage_header_sha=sha(controller['stage_header_slot']),startup_capture=deepcopy(controller['capture']))
    diagnostic=value('constructor_diagnostic',context_sha=ctx,request_sha=req,ACK_sha=binding['ACK_sha'],
        original_attempt_started=controller['basis']['episode_started'],observed_at=controller['wire_now']+.01)
    references={}
    for name in ('final_observation_reference','controller_process_reference','parent_metrics_reference','fresh_metrics_reference','candidate_reference','failure_reference'):
        fields=registry()['types'][name]['fields'];reference={n:r['literal'] for n,r in fields.items() if isinstance(r,dict) and 'literal' in r}
        item=case['roles'][reference['writer_role']]
        reference.update(context_sha=ctx,request_sha=req,stage_nonce=item['basis']['stage_nonce'],episode_commit_sha=item['basis']['episode_commit_sha'],pin=pin(raw(name)))
        references[name]=reference
    returns={}
    for status in ('returned_candidate','failed','unknown'):
        refs={n:(v if (status=='returned_candidate' and n!='failure_reference') or (status=='failed' and n=='failure_reference') else None) for n,v in references.items()}
        returns[status]=value('controller_return',context_sha=ctx,request_sha=req,status=status,stage_nonce=controller['basis']['stage_nonce'],
            episode_commit_sha=controller['basis']['episode_commit_sha'],**refs,G2_image_sha=image('declared_G2') if status=='returned_candidate' else None)
    brokers={}
    for status in ('returned_candidate','failed','unknown'):
        brokers[status]=value('broker_return',context_sha=ctx,request_sha=req,status=status,controller_return_sha=sha(raw(returns['returned_candidate'])),
            controller_binding_sha=sha(raw(binding)),stage_nonce=case['header_basis']['broker_stage_nonce'],episode_commit_sha=case['header_basis']['broker_episode_commit_sha'],
            broker_process_image_sha=image('declared_broker_process'),failure_record=None if status=='returned_candidate' else failure(case,'broker'))
    return dict(binding=binding,diagnostic=diagnostic,references=references,returns=returns,brokers=brokers)
