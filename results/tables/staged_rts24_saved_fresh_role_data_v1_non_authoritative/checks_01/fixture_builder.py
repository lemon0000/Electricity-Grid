"""Independent stdlib declarations; no validator/project implementation import."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
FROZEN=ROOT/'results/tables/staged_rts24_saved_fresh_upstream_contract_v1_non_authoritative/checks_01'
def raw(value):return json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
def sha(data):return sha256(data).hexdigest()
def pin(data):return dict(bytes=len(data),sha256=sha(data))
def image(value):return sha(raw(value))

def build():
    original=ROOT/'results/tables/staged_rts24_saved_fresh_successor_data_v1_non_authoritative/checks_01/fixture_builder.py'
    expected=json.loads((OUT/'baseline.json').read_bytes())['preserved'][original.relative_to(ROOT).as_posix()]
    assert pin(original.read_bytes())==expected
    loader=importlib.util.spec_from_file_location('role_data_independent_context_fixture',original)
    module=importlib.util.module_from_spec(loader);loader.loader.exec_module(module)
    base=module.build();context=json.loads(base['context_raw']);request=json.loads(base['request_raw'])
    registry_raw=(FROZEN/'protocol_domains.json').read_bytes();templates_raw=(FROZEN/'fixed_templates.json').read_bytes()
    assert pin(registry_raw)==dict(bytes=21981,sha256='d5e467a761ea5d50c939f9b76fd702775381341996c3a0aaf5e563025a62520b')
    assert pin(templates_raw)==dict(bytes=2231,sha256='36cff2e3fa3a11da0d6a2de7a088e8be94d528a1f2a2c33e14a88f03d57a0d0a')
    registry=json.loads(registry_raw);templates=json.loads(templates_raw)
    context_sha,request_sha=sha(base['context_raw']),sha(base['request_raw'])
    output=Path(context['output_root']);producer_ids=dict(controller=[1002,2002],parent=[1003,2003],fresh=[1004,2004])
    producers=dict(controller='broker',parent='controller',fresh='parent')
    receipt=dict(**pin(base['context_raw']),identity=[1,700,len(base['context_raw']),123456])
    root_dirs=deepcopy(context['output_parent_directories'])+[[str(output),1,500]]
    def directories(path):
        result=deepcopy(root_dirs);current=output
        for part in path.relative_to(output).parts:
            current=current/part;result.append([str(current),1,int(sha(str(current).encode())[:15],16)+1000])
        return result
    tree=[[n,directories(output/n)] for n in ('','worker','worker/fresh','worker/fresh_parent','parent','diagnostics')]
    tree.append(['context_file_identity',receipt['identity']]);tree_raw=raw(tree)
    broker_stage=image('broker_stage')
    publication=dict(schema='staged_saved_F_successor_publication_declaration_data_v1',data_only=True,
        producer_role='broker',consumer_role='successor_entry_data_validation',context_sha=context_sha,
        request_sha=request_sha,stage_nonce=broker_stage,declared_at=1000.1,tree_declared_at=1000.15,
        producer_identity=producer_ids['controller'],context_path=str(output/'context.json'),context_receipt=receipt,
        root_directories=root_dirs,role_tree_pin=pin(tree_raw))
    def declaration(name,producer,consumer,stamp,*,ctx=context_sha,packet=None,binding=None,stage=broker_stage,**extra):
        return dict(schema='staged_saved_F_successor_'+name+'_declaration_data_v1',data_only=True,
            producer_role=producer,consumer_role=consumer,context_sha=ctx,request_sha=request_sha,
            stage_nonce=stage,packet_sha=packet,permit_binding_sha=binding,declared_at=stamp,**extra)
    header=declaration('mailbox_header','host','broker',1000.0,ctx=None,
        host_identity=[1001,2001],broker_identity=producer_ids['controller'],host_direction_nonce=image('host_nonce'),
        mailbox_name='Local\\electricity_grid_role_data_mailbox',layout_sha=image('unimplemented_wire_layout'))
    offer=declaration('offer','broker','host',1000.2,context_receipt_sha=image(receipt),root_directories_sha=image(root_dirs))
    header_raw,offer_raw=raw(header),raw(offer)
    ack=dict(schema=registry['schemas']['ACK']['schema_literal'],data_only=True,context_sha=context_sha,
        request_sha=request_sha,offer_sha=sha(offer_raw),mailbox_header_sha=sha(header_raw),
        context_receipt_sha=image(receipt),root_directories_sha=image(root_dirs),host_identity=[1001,2001],
        broker_identity=producer_ids['controller'],host_direction_nonce=image('host_nonce'),
        original_invocation_started=1000.0,original_invocation_deadline=1180.0,
        runtime_binding_contract_sha=context['runtime_binding_contract_sha'],deadline_profile_sha=context['deadline_profile_sha'])
    ack_raw=raw(ack)
    built={}
    for role in ('controller','parent','fresh'):
        producer=producers[role]
        source_stage,source_packet,source_binding=broker_stage,None,None
        if role!='controller':
            previous=built['controller' if role=='parent' else 'parent']
            source_stage=previous['packet']['stage_nonce'];source_packet=sha(previous['packet_raw']);source_binding=sha(previous['permit_raw'])
        projection_names=(('broker_ACK_verified',) if role=='controller' else
            ('controller_bootstrap','controller_G0','controller_store','controller_issuer') if role=='parent' else
            ('parent_bootstrap','parent_hold','parent_store','parent_issuer'))
        stamps=(1000.5,) if role=='controller' else (1002.,1005.,1006.,1007.) if role=='parent' else (1011.,1015.,1016.,1017.)
        projections={n:declaration(n,producer,role,stamp,stage=source_stage,packet=source_packet,binding=source_binding,
            **({'ACK_sha':sha(ack_raw)} if role=='controller' else {'image_sha':image('development_'+n)})) for n,stamp in zip(projection_names,stamps)}
        projection_raws={n:raw(v) for n,v in projections.items()}
        transport=dict(schema='staged_saved_F_successor_'+role+'_transport_declaration_data_v1',data_only=True,
            producer_role=producer,consumer_role=role,context_sha=context_sha,request_sha=request_sha,
            entry_transport_name='Local\\electricity_grid_role_data_'+role+'_entry',entry_transport_nonce=image(role+'_entry'),
            stage_name='Local\\electricity_grid_role_data_'+role+'_stage',stage_nonce=image(role+'_stage'))
        total=templates['production_descriptor_values'][role]['total_seconds']
        tail=templates['production_descriptor_values'][role]['quiesce_seconds']+templates['production_descriptor_values'][role]['terminal_seconds']
        started=dict(controller=1001.,parent=1010.,fresh=1020.)[role]
        episode=dict(schema='staged_saved_F_successor_'+role+('_attempt' if role=='controller' else '_reservation')+'_declaration_data_v1',
            data_only=True,producer_role=producer,consumer_role=role,context_sha=context_sha,request_sha=request_sha,
            stage_nonce=source_stage,packet_sha=source_packet,permit_binding_sha=source_binding,
            producer_identity=producer_ids[role],nonce=image(role+'_original_episode'),started=started,deadline=min(1180.,started+total))
        basis=dict(schema='staged_saved_F_successor_'+role+'_basis_declaration_data_v1',data_only=True,
            producer_role=producer,consumer_role=role,context_sha=context_sha,request_sha=request_sha,stage_nonce=source_stage,
            packet_sha=source_packet,permit_binding_sha=source_binding,producer_identity=producer_ids[role],
            permit_nonce=image(role+'_permit'),context_data_identity=None,upstream_data_identity=None,
            local_episode=episode,projection_pins={n:pin(v) for n,v in projection_raws.items()})
        if role=='controller':
            basis.update(ack_pin=pin(ack_raw),mailbox_header_pin=pin(header_raw),offer_pin=pin(offer_raw),
                host_direction_nonce=header['host_direction_nonce'],ACK_declared_at=1000.4)
        common=dict(context_sha=context_sha,request_sha=request_sha,original_invocation_started=1000.,original_invocation_deadline=1180.,
            active_deadline=min(1000.+templates['deadlines'][role][0],1180.,episode['deadline']-tail),
            closed_deadline=min(1000.+templates['deadlines'][role][1],1180.,episode['deadline']),role_tree_sha=sha(tree_raw))
        if role=='controller':
            common.update(controller_attempt_nonce=episode['nonce'],attempt_commit_sha=image(episode),
                attempt_started=started,attempt_deadline=episode['deadline'],ACK_sha=sha(ack_raw),
                mailbox_header_sha=sha(header_raw),broker_ACK_verified_projection_sha=sha(projection_raws['broker_ACK_verified']))
        else:
            common.update(reservation_nonce=episode['nonce'],reservation_commit_sha=image(episode),reservation_started=started,reservation_deadline=episode['deadline'])
            common.update({n+'_projection_sha':sha(v) for n,v in projection_raws.items()})
            common[producer+'_permit_binding_sha']=source_binding
        permit=dict(schema=registry['schemas'][role+'_permit_binding']['schema_literal'],data_only=True,**common,
            producer_identity=producer_ids[role],permit_nonce=basis['permit_nonce'],context_receipt_sha=image(receipt),
            deadline_profile_sha=context['deadline_profile_sha'])
        permit_raw=raw(permit)
        packet=dict(schema=registry['schemas'][role+'_entry_packet']['schema_literal'],data_only=True,**common,
            permit_binding_sha=sha(permit_raw),context_path=publication['context_path'],context_receipt=receipt,
            root_directories_sha=image(root_dirs),source_sha=image(context['source_pins']),environment_sha=image(context['environment']),
            ENTRY_pin=context['source_pins']['experiments/staged_rts24_saved_fresh_adoption_v1.py'],executable_pin=context['executable']['pin'],
            runtime_binding_contract_sha=context['runtime_binding_contract_sha'],deadline_profile_sha=context['deadline_profile_sha'],
            descriptor_template_sha=sha(templates_raw),entry_transport_contract_sha=sha(templates_raw),
            **{n:transport[n] for n in ('entry_transport_name','entry_transport_nonce','stage_name','stage_nonce')})
        packet_raw=raw(packet)
        descriptor={n:deepcopy(rule['literal']) if type(rule) is dict else
            dict(packet_sha=sha(packet_raw),permit_binding_sha=sha(permit_raw),deadline_profile_sha=context['deadline_profile_sha'],data_only=True)[n]
            for n,rule in registry['schemas'][role+'_stage_descriptor']['fields'].items()}
        built[role]=dict(packet=packet,permit=permit,descriptor=descriptor,packet_raw=packet_raw,permit_raw=permit_raw,
            descriptor_raw=raw(descriptor),basis=basis,transport=transport,projections=projections,projection_raws=projection_raws,now=started+.5)
    return dict(base_context_case=base,roles=built,registry_raw=registry_raw,templates_raw=templates_raw,
        publication_raw=raw(publication),tree_raw=tree_raw,ack_raw=ack_raw,mailbox_header_raw=header_raw,offer_raw=offer_raw)
