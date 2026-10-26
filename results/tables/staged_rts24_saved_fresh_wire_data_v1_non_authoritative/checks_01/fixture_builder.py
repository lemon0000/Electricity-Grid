"""Independent stdlib wire fixture. Never import the validator or its codec."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
WIRE=ROOT/'results/tables/staged_rts24_saved_fresh_wire_contract_v1_non_authoritative/checks_01'
OLD=ROOT/'results/tables/staged_rts24_saved_fresh_upstream_contract_v1_non_authoritative/checks_01'
def raw(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def sha(v):return sha256(v).hexdigest()
def image(v):return sha(raw(v))
def pin(v):return dict(bytes=len(v),sha256=sha(v))
def slot(data,size,header=False):
    assert 0<len(data)<=size-44
    return struct.pack('<I',len(data))+data+b'\0'*(size-44-len(data))+sha256(data).digest()+(b'GRIDHDR1' if header else b'GRIDFRM1')
def build():
    previous=ROOT/'results/tables/staged_rts24_saved_fresh_role_data_v1_non_authoritative/checks_01/fixture_builder.py'
    expected=json.loads((OUT/'baseline.json').read_bytes())['preserved'][previous.relative_to(ROOT).as_posix()]
    assert pin(previous.read_bytes())==expected
    spec=importlib.util.spec_from_file_location('independent_wire_context_fixture',previous);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    old_case=module.build();base=old_case['base_context_case'];ctx=json.loads(base['context_raw']);req=json.loads(base['request_raw'])
    contract_raws=tuple((directory/name).read_bytes() for directory,name in ((WIRE,'wire_domains.json'),(WIRE,'wire_templates.json'),
        (WIRE,'wire_dag_matrix.json'),(OLD,'protocol_domains.json'),(OLD,'fixed_templates.json')))
    registry,template,old=json.loads(contract_raws[0]),json.loads(contract_raws[1]),json.loads(contract_raws[3])
    def value(schema_name,**items):
        result={n:deepcopy(rule['literal']) for n,rule in registry['schemas'][schema_name]['fields'].items() if isinstance(rule,dict) and 'literal' in rule}
        result.update(items);assert set(result)==set(registry['schemas'][schema_name]['fields']),(schema_name,set(registry['schemas'][schema_name]['fields'])-set(result))
        return result
    context_sha,request_sha=sha(base['context_raw']),sha(base['request_raw']);common=dict(context_sha=context_sha,request_sha=request_sha)
    publication=json.loads(old_case['publication_raw']);receipt=publication['context_receipt'];directories=publication['root_directories']
    identities=dict(host=[1001,2001],broker=[1002,2002],controller=[1003,2003],parent=[1004,2004],fresh=[1005,2005])
    directions={n:image('direction_'+n) for n in template['mailbox_directions']};mailbox_name='Local\\electricity_grid_wire_fixture_mailbox'
    header=value('mailbox_header',name=mailbox_name,request_sha=request_sha,host_identity=identities['host'],broker_identity=identities['broker'],direction_nonces=directions)
    header_slot=slot(raw(header),4096);header_sha=sha(header_slot)
    header_basis=dict(schema='staged_saved_F_wire_handshake_basis_declaration_v1',context_ref=None,mailbox_name=mailbox_name,
        direction_nonces=directions,context_receipt=receipt,root_directories=directories,broker_stage_nonce=image('broker_stage'),
        broker_episode_commit_sha=image('broker_episode'))
    ready=value('READY',request_sha=request_sha,mailbox_header_sha=header_sha,broker_identity=identities['broker'],ready_at=1000.1,
        standby_deadline=1010.,original_invocation_started=1000.,original_invocation_deadline=1180.)
    start=value('START',request_sha=request_sha,READY_sha=sha(raw(ready)),mailbox_header_sha=header_sha,host_identity=identities['host'],
        sent_at=1000.2,original_invocation_started=1000.,original_invocation_deadline=1180.)
    offer=value('offer',**common,context=ctx,START_sha=sha(raw(start)),context_receipt=receipt,root_directories=directories,
        broker_identity=identities['broker'],published_at=1000.3)
    ack=deepcopy(json.loads(old_case['ack_raw']));ack.update(offer_sha=sha(raw(offer)),mailbox_header_sha=header_sha,host_direction_nonce=directions['host'])
    envelopes={};mail_slots={};payloads=dict(request=req,ready=ready,start=start,context=offer,ack=ack)
    for kind in ('request','ready','start','context','ack'):
        rule=registry['cross_field_constraints']['mailbox_kinds'][kind]
        producer=identities['host' if rule['direction']=='host' else 'broker']
        previous='0'*64 if rule['previous_kind'] is None else sha(raw(envelopes[rule['previous_kind']]))
        envelopes[kind]=dict(kind=kind,sequence=rule['sequence'],previous_sha=previous,producer_identity=producer,
            direction_nonce=directions[rule['direction']],binding_sha=header_sha,payload=payloads[kind])
        mail_slots[kind]=slot(raw(envelopes[kind]),dict(template['mailbox_slots'])[kind])
    roles={};producers=dict(controller='broker',parent='controller',fresh='parent')
    bootstrap_images={r:image('declared_'+r+'_bootstrap_capability_image') for r in producers}
    for role,producer in producers.items():
        prior=None if role=='controller' else roles['controller' if role=='parent' else 'parent']
        source_packet=None if prior is None else sha(prior['packet_raw']);source_binding=None if prior is None else sha(prior['permit_raw'])
        source_stage=header_basis['broker_stage_nonce'] if prior is None else prior['packet']['stage_nonce']
        start_at=dict(controller=1001.,parent=1010.,fresh=1020.)[role]
        names=registry['cross_field_constraints']['projections']['bundles'][role]
        input_metadata=image(role+'_independent_input_metadata');runtime_binding=image(role+'_independent_runtime_binding');receipt_commit=image(role+'_receipt_commit')
        projections={};image_shas={}
        if prior is None:
            name=names[0];image_shas[name]=image('declared_source_image_'+name)
            projections[name]=value(name,**common,producer_identity=identities[producer],source_packet_sha=None,source_permit_binding_sha=None,
                stage_nonce=source_stage,source_image_sha=image_shas[name],observed_at=1000.5,ACK_sha=sha(raw(ack)),mailbox_header_sha=header_sha,offer_sha=sha(raw(offer)))
        else:
            projections[names[0]]=deepcopy(prior['bootstrap'])
            boot_image=bootstrap_images[producer];hold_name=names[1];store_name=names[2];issuer_name=names[3]
            stamps=[1002.,1003.,1004.] if role=='parent' else [1011.,1012.,1013.]
            for name,stamp in zip(names[1:],stamps):
                image_shas[name]=image('declared_source_image_'+name)
                fields=dict(**common,producer_identity=identities[producer],source_packet_sha=source_packet,source_permit_binding_sha=source_binding,
                    stage_nonce=source_stage,source_image_sha=image_shas[name],observed_at=stamp,bootstrap_image_sha=boot_image)
                if name==hold_name:fields.update(input_files_sha=image(ctx['input_files']),input_metadata_sha=input_metadata,anchor_sha=ctx['anchor_sha'],
                    source_sha=image(ctx['source_pins']),runtime_binding_sha=runtime_binding)
                elif name==store_name:fields.update(**{('G0_image_sha' if role=='parent' else 'hold_image_sha'):image_shas[hold_name]},
                    tree_sha=sha(old_case['tree_raw']),receipt_commit_sha=receipt_commit)
                else:
                    fields.update(**{('G0_image_sha' if role=='parent' else 'hold_image_sha'):image_shas[hold_name]},store_image_sha=image_shas[store_name])
                    if role=='parent':fields['ACK_sha']=sha(raw(ack))
                projections[name]=value(name,**fields)
        basis=dict(schema='staged_saved_F_'+role+'_wire_basis_declaration_v1',context_ref=None,upstream_ref=None,
            producer_identity=identities[producer],entry_name='Local\\electricity_grid_wire_'+role+'_entry',entry_nonce=image(role+'_entry_nonce'),
            stage_name='Local\\electricity_grid_wire_'+role+'_stage',stage_nonce=image(role+'_stage_nonce'),permit_nonce=image(role+'_permit_nonce'),
            episode_nonce=image(role+'_episode_nonce'),episode_commit_sha=image(role+'_independent_episode_commit'),episode_started=start_at,
            episode_deadline=old_case['roles'][role]['basis']['local_episode']['deadline'],upstream_stage_nonce=source_stage,
            role_tree_pin=pin(old_case['tree_raw']),projection_pins={n:pin(raw(v)) for n,v in projections.items()},projection_image_shas=image_shas)
        if prior is not None:basis.update(bootstrap_source_image_sha=bootstrap_images[producer],input_metadata_sha=input_metadata,
            runtime_binding_sha=runtime_binding,receipt_commit_sha=receipt_commit)
        bundle=value(role+'_projection_bundle',**projections);bundle_raw=raw(bundle)
        permit=deepcopy(old_case['roles'][role]['permit']);packet=deepcopy(old_case['roles'][role]['packet']);descriptor=deepcopy(old_case['roles'][role]['descriptor'])
        changes={registry['cross_field_constraints']['projections']['packet_sha_fields'][role][n]:sha(raw(v)) for n,v in projections.items()}
        if role=='controller':changes.update(ACK_sha=sha(raw(ack)),mailbox_header_sha=header_sha,attempt_commit_sha=basis['episode_commit_sha'],controller_attempt_nonce=basis['episode_nonce'])
        else:changes.update(reservation_commit_sha=basis['episode_commit_sha'],reservation_nonce=basis['episode_nonce'],
            **{producer+'_permit_binding_sha':source_binding})
        permit.update(changes,producer_identity=identities[producer],permit_nonce=basis['permit_nonce']);permit_raw=raw(permit)
        packet.update(changes,entry_transport_name=basis['entry_name'],entry_transport_nonce=basis['entry_nonce'],stage_name=basis['stage_name'],
            stage_nonce=basis['stage_nonce'],permit_binding_sha=sha(permit_raw));packet_raw=raw(packet)
        descriptor.update(packet_sha=sha(packet_raw),permit_binding_sha=sha(permit_raw));descriptor_raw=raw(descriptor)
        argv_values=dict(entry_transport_name=basis['entry_name'],entry_transport_nonce=basis['entry_nonce'],stage_name=basis['stage_name'],stage_nonce=basis['stage_nonce'],
            packet_sha=sha(packet_raw),context_sha=context_sha,descriptor_sha=sha(descriptor_raw),mailbox_name=mailbox_name,request_sha=request_sha,ACK_sha=sha(raw(ack)))
        argv=[]
        for token in old['argv_grammars'][role]['tokens']:
            argv.append(str(Path('D:/Miniconda3/envs/compute/python.exe')) if token=='EXE' else str(ROOT/'experiments/staged_rts24_saved_fresh_adoption_v1.py') if token=='ENTRY' else argv_values[token[1:-1]] if token.startswith('{') else token)
        entry_header=value(role+'_entry_header',**common,name=basis['entry_name'],entry_nonce=basis['entry_nonce'],stage_name=basis['stage_name'],stage_nonce=basis['stage_nonce'],
            packet_sha=sha(packet_raw),permit_binding_sha=sha(permit_raw),descriptor_sha=sha(descriptor_raw),argv_sha=image(argv),projection_bundle_sha=sha(bundle_raw),
            producer_identity=identities[producer],original_invocation_started=1000.,original_invocation_deadline=1180.)
        entry_header_slot=slot(raw(entry_header),4096,True)
        binding_frame=dict(kind='binding',sequence=0,previous_sha='0'*64,producer_identity=identities[producer],direction_nonce=basis['entry_nonce'],binding_sha=sha(entry_header_slot),payload=permit)
        packet_frame=dict(kind='packet',sequence=1,previous_sha=sha(raw(binding_frame)),producer_identity=identities[producer],direction_nonce=basis['entry_nonce'],binding_sha=sha(entry_header_slot),payload=packet)
        entry_slots=(entry_header_slot,slot(bundle_raw,18476),slot(raw(binding_frame),4652),slot(raw(packet_frame),36908))
        stage_header=value(role+'_stage_header',context_sha=context_sha,nonce=basis['stage_nonce'],descriptor=descriptor,owner_pid=identities[role][0],
            owner_creation_filetime=identities[role][1],entry_header_sha=sha(entry_header_slot));stage_header_slot=slot(raw(stage_header),4096,True)
        startup_common=dict(**common,entry_header_sha=sha(entry_header_slot),stage_header_sha=sha(stage_header_slot),packet_sha=sha(packet_raw),
            permit_binding_sha=sha(permit_raw),descriptor_sha=sha(descriptor_raw),environment_sha=image(ctx['environment']))
        capture=value(role+'_startup_capture',**startup_common,producer_identity=identities[producer],owner_identity=identities[role],argv=argv,
            command_line=subprocess.list2cmdline(argv),ENTRY_pin=ctx['source_pins']['experiments/staged_rts24_saved_fresh_adoption_v1.py'],
            executable_pin=ctx['executable']['pin'],captured_at=start_at+.1)
        bootstrap=value(role+'_bootstrap_projection',**startup_common,self_identity=identities[role],thread_id=3000+identities[role][0],argv_sha=image(argv),
            source_sha=image(ctx['source_pins']),runtime_binding_contract_sha=ctx['runtime_binding_contract_sha'],observed_at=start_at+.2)
        roles[role]=dict(basis=basis,packet=packet,permit=permit,packet_raw=packet_raw,permit_raw=permit_raw,descriptor_raw=descriptor_raw,entry_header=entry_header,
            bundle=bundle,entry_slots=entry_slots,stage_header_slot=stage_header_slot,capture=capture,capture_raw=raw(capture),bootstrap=bootstrap,bootstrap_slot=slot(raw(bootstrap),4096),
            owner_identity=tuple(identities[role]),thread_id=bootstrap['thread_id'],bootstrap_source_image_sha=bootstrap_images[role],wire_now=start_at+.05,join_now=start_at+.3)
    return dict(base_case=base,contract_raws=contract_raws,header_slot=header_slot,header_basis=header_basis,
        mail_slots=mail_slots,handshake_now=1000.4,roles=roles,tree_raw=old_case['tree_raw'])


def refresh(item,role):
    """Rebuild all public raw hashes after a projection mutation, independently."""
    bundle=item['bundle'];basis=item['basis'];permit=item['permit'];packet=item['packet']
    registry=json.loads((WIRE/'wire_domains.json').read_bytes())
    for name,field in registry['cross_field_constraints']['projections']['packet_sha_fields'][role].items():
        basis['projection_pins'][name]=pin(raw(bundle[name]));permit[field]=packet[field]=sha(raw(bundle[name]))
    permit_raw=raw(permit);packet['permit_binding_sha']=sha(permit_raw);packet_raw=raw(packet)
    descriptor=json.loads(item['descriptor_raw']);descriptor.update(packet_sha=sha(packet_raw),permit_binding_sha=sha(permit_raw))
    descriptor_raw=raw(descriptor);header=item['entry_header']
    argv=item['capture']['argv'];grammar=json.loads((OLD/'protocol_domains.json').read_bytes())['argv_grammars'][role]['tokens']
    for key,val in dict(packet_sha=sha(packet_raw),descriptor_sha=sha(descriptor_raw)).items():argv[grammar.index('{'+key+'}')]=val
    header.update(packet_sha=sha(packet_raw),permit_binding_sha=sha(permit_raw),descriptor_sha=sha(descriptor_raw),argv_sha=image(argv),projection_bundle_sha=sha(raw(bundle)))
    header_slot=slot(raw(header),4096,True)
    producer=permit['producer_identity'];nonce=basis['entry_nonce']
    binding=dict(kind='binding',sequence=0,previous_sha='0'*64,producer_identity=producer,direction_nonce=nonce,binding_sha=sha(header_slot),payload=permit)
    packet_frame=dict(kind='packet',sequence=1,previous_sha=sha(raw(binding)),producer_identity=producer,direction_nonce=nonce,binding_sha=sha(header_slot),payload=packet)
    stage=json.loads(item['stage_header_slot'][4:4+struct.unpack('<I',item['stage_header_slot'][:4])[0]])
    stage.update(descriptor=descriptor,entry_header_sha=sha(header_slot));stage_slot=slot(raw(stage),4096,True)
    for value in (item['capture'],item['bootstrap']):value.update(entry_header_sha=sha(header_slot),stage_header_sha=sha(stage_slot),packet_sha=sha(packet_raw),permit_binding_sha=sha(permit_raw),descriptor_sha=sha(descriptor_raw))
    item['capture']['command_line']=subprocess.list2cmdline(argv);item['bootstrap']['argv_sha']=image(argv)
    item.update(packet_raw=packet_raw,permit_raw=permit_raw,descriptor_raw=descriptor_raw,
        entry_slots=(header_slot,slot(raw(bundle),18476),slot(raw(binding),4652),slot(raw(packet_frame),36908)),
        stage_header_slot=stage_slot,capture_raw=raw(item['capture']),bootstrap_slot=slot(raw(item['bootstrap']),4096))
