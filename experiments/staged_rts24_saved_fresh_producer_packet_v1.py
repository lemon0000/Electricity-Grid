"""Lossless expectation/context data. No raw 683-file payload or P1 I/O."""
import base64
from hashlib import sha256
import json
import math
from pathlib import PurePosixPath
import zlib

PACKET_RAW_CAP=1048576
PACKET_INPUT_CAP=2097152
PACKET_WIRE_CAP=131072
PACKET_SOURCE_EPOCH='acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875'
PACKET_GATES=('native_authorized','resource_admission','formal_result','scientific_evidence_adopted','public_P2_execution_enabled')
PACKET_CORE_KEYS=frozenset(('files fixture_sha outer trusted expectations bindings source anchor_path anchor_pin anchor_identity '
    'anchor_directories root_directories historical_metrics expected_evidence_refs inventory').split())
PACKET_EXPECTATION_KEYS=frozenset(('schema authority scope caller_expectation_core caller_expectation_sha source_sha input_pins_sha '
    'content_read_files metadata_passes full_P1_content_verified F_launch_admitted').split())|frozenset(PACKET_GATES)
PACKET_CONTEXT_KEYS=frozenset(('schema authority scope repo_root input_root output_root output_mode output_parent_directories source_pins '
    'executable environment anchor_sha input_files invocation_started deadline stage_seconds limits inherited_sources_pin '
    'caller_expectation_core caller_expectation_sha expectation_sha full_P1_content_verified').split())|frozenset(PACKET_GATES)
PACKET_CONTENT_FILES=tuple(sorted(('launcher.json','trusted_binding.json','start.json','request_schedule.json','fresh.json',
    *(f'trusted_prefixes/prefix_{index:06d}.json' for index in range(6)),
    *(f'points/point_{index:04d}/{name}.json' for index in range(1,22) for name in ('request','result')))))
PACKET_FALSE=('full_P1_content_verified','external_permission_verified','parent_python_graph_attested',
    'scientific_evidence_adopted','resource_admission','formal_result','run_authority','actual_F')
PACKET_KEYS=frozenset(('schema','authority','sources','files','core_tail','expectation_tail','context_tail','raw_pins','stages','clocks'))|frozenset(PACKET_FALSE)


def packet_require(value,message):
    if not value:raise ValueError(message)


def packet_canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def packet_pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def packet_decode(raw,cap):
    packet_require(type(raw) is bytes and len(raw)<=cap,'bounded producer data required')
    def pairs(items):
        result={}
        for key,value in items:
            packet_require(key not in result,'duplicate producer JSON key');result[key]=value
        return result
    def invalid(value):raise ValueError('nonfinite producer data')
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid)
    packet_require(packet_canonical(value)==raw and type(value) is dict,'canonical producer object required')
    return value


def packet_checked_pin(value,cap):
    packet_require(type(value) is dict and set(value)=={'bytes','sha256'} and type(value['bytes']) is int
        and 0<=value['bytes']<=cap and type(value['sha256']) is str and len(value['sha256'])==64
        and all(letter in '0123456789abcdef' for letter in value['sha256']),'bounded exact producer pin required')
    return value


def packet_files(value,count,total=None):
    packet_require(type(value) is dict and len(value)==count,'complete producer file map required')
    folded=set()
    for name,row in value.items():
        packet_require(type(name) is str and 0<len(name)<=4096 and '\\' not in name and ':' not in name and '\x00' not in name
            and not PurePosixPath(name).is_absolute() and all(part not in ('','.','..') for part in name.split('/'))
            and name.casefold() not in folded,'unique relative producer path required')
        folded.add(name.casefold());packet_checked_pin(row,8388608)
    if total is not None:packet_require(sum(row['bytes'] for row in value.values())==total,'producer full input bytes differ')
    return value


def packet_inventory(inventory,files):
    packet_require(type(inventory) is dict and set(inventory)=={'pins','files','directories'} and inventory['pins']==files,
        'complete metadata inventory required; raw content is not exported')
    rows=inventory['files'];folders=inventory['directories']
    packet_require(type(rows) is dict and set(rows)==set(files) and type(folders) is dict and 1<=len(folders)<=16384 and '.' in folders,
        'complete producer metadata identities required')
    identities=set()
    for name,row in rows.items():
        packet_require(type(row) is list and len(row)==4 and all(type(number) is int and 0<=number<2**128 for number in row)
            and row[1]>0 and row[2]==files[name]['bytes'] and tuple(row[:2]) not in identities,'unique producer file identity required')
        identities.add(tuple(row[:2]))
    aliases={name.casefold() for name in files}
    for name,row in folders.items():
        packet_require(type(name) is str and 0<len(name)<=4096 and '\\' not in name and ':' not in name and '\x00' not in name
            and (name=='.' or all(part not in ('','.','..') for part in name.split('/')))
            and not PurePosixPath(name).is_absolute() and name.casefold() not in aliases,'unique producer directory path required')
        aliases.add(name.casefold())
        packet_require(type(row) is list and len(row)==2 and type(row[0]) is int and 0<=row[0]<2**64
            and type(row[1]) is int and 0<row[1]<2**128,'bounded producer directory identity required')
    packet_require(all(all(parent.as_posix() in folders for parent in PurePosixPath(name).parents) for name in files),
        'producer metadata parent missing')


def packet_envelopes(expectation,context,core,sources,files):
    # This is the pure data subset. Live clock, filesystem identities, original
    # Source49 execution and parent content checks remain separate authorities.
    packet_require(set(expectation)==PACKET_EXPECTATION_KEYS and set(context)==PACKET_CONTEXT_KEYS and set(core)==PACKET_CORE_KEYS,
        'closed original producer envelopes required')
    packet_require(expectation['schema']=='staged_saved_P1_caller_expectation_development_v1'
        and context['schema']=='staged_saved_P1_expectation_context_development_v1','producer original schemas differ')
    for value in (expectation,context):
        packet_require(value['authority']=='DRAFT_NONAUTHORITATIVE' and value['scope']=='saved_P1_actual_21_and_journal_5h'
            and value['full_P1_content_verified'] is False and all(value[name] is False for name in PACKET_GATES),
            'producer original authority fields differ')
    packet_require(expectation['F_launch_admitted'] is False and type(expectation['metadata_passes']) is int
        and expectation['metadata_passes']==2 and expectation['content_read_files']==list(PACKET_CONTENT_FILES),
        'producer expectation read domain differs')
    digest=packet_pin(packet_canonical(core))['sha256']
    packet_require(expectation['caller_expectation_sha']==context['caller_expectation_sha']==digest
        and expectation['source_sha']==packet_pin(packet_canonical(sources))['sha256']
        and expectation['input_pins_sha']==packet_pin(packet_canonical(files))['sha256'],'producer envelope digest relationships differ')
    packet_require(all(type(core[key]) is dict for key in ('outer','trusted','expectations','historical_metrics'))
        and type(core['bindings']) is list and len(core['bindings'])==6
        and type(core['expected_evidence_refs']) is list and len(core['expected_evidence_refs'])==21,'producer original core shapes differ')
    packet_inventory(core['inventory'],files)


def packet_stages(stages,clocks):
    packet_require(type(stages) is list and len(stages)==3 and all(type(row) is dict for row in stages)
        and [row.get('stage') for row in stages]==['G0','G2','G3'],
        'exact G0 G2 G3 producer evidence required')
    packet_require(type(clocks) is list and len(clocks)==3 and all(type(value) is float and math.isfinite(value) and value>0 for value in clocks)
        and clocks==sorted(clocks),'monotonic producer stage clocks required')
    first=stages[0]
    packet_require(set(first)=={'stage','expectation_raw_pin','caller_image_pin','context_pin','held_image_pin','local_full_input_verified'}
        and first['local_full_input_verified'] is True,'closed G0 evidence required')
    for name in ('expectation_raw_pin','caller_image_pin','context_pin','held_image_pin'):packet_checked_pin(first[name],PACKET_INPUT_CAP)
    for row in stages[1:]:
        packet_require(set(row)=={'stage','context_pin','held_image_pin','local_full_input_bookend'}
            and row['local_full_input_bookend'] is True,'closed G2 G3 evidence required')
        packet_checked_pin(row['context_pin'],PACKET_INPUT_CAP);packet_checked_pin(row['held_image_pin'],PACKET_INPUT_CAP)


def packet_capture(expectation_raw,context_raw,caller_image,sources,files,stages,clocks):
    """Detach exact canonical bytes by factoring shared maps, with an inverse."""
    expectation=packet_decode(expectation_raw,PACKET_INPUT_CAP);context=packet_decode(context_raw,PACKET_INPUT_CAP)
    core=packet_decode(caller_image,PACKET_INPUT_CAP)
    packet_files(sources,49);packet_files(files,683,2950863)
    packet_require(packet_pin(packet_canonical(sources))['sha256']==PACKET_SOURCE_EPOCH,'fixed Source49 epoch required')
    packet_require(expectation.get('caller_expectation_core')==context.get('caller_expectation_core')==core
        and context.get('source_pins')==core.get('source')==sources
        and context.get('input_files')==core.get('files')==files
        and context.get('expectation_sha')==sha256(expectation_raw).hexdigest(),'producer raw/core/map join differs')
    inventory=core.get('inventory')
    packet_inventory(inventory,files)
    packet_envelopes(expectation,context,core,sources,files)
    packet_stages(stages,clocks)
    core_tail={key:value for key,value in core.items() if key not in ('source','files','inventory')}
    core_tail['inventory']={key:value for key,value in inventory.items() if key!='pins'}
    result=dict(schema='staged_saved_F_detached_producer_packet_v1',authority='DRAFT_NONAUTHORITATIVE',
        sources=sources,files=files,core_tail=core_tail,
        expectation_tail={key:value for key,value in expectation.items() if key!='caller_expectation_core'},
        context_tail={key:value for key,value in context.items() if key not in ('caller_expectation_core','source_pins','input_files')},
        raw_pins=dict(expectation=packet_pin(expectation_raw),context=packet_pin(context_raw),caller_image=packet_pin(caller_image)),
        stages=stages,clocks=clocks,**{key:False for key in PACKET_FALSE})
    raw=packet_canonical(result);packet_require(len(raw)<=PACKET_RAW_CAP,'detached producer packet cap')
    restored=packet_restore(raw)
    packet_require(restored['expectation_raw']==expectation_raw and restored['context_raw']==context_raw
        and restored['caller_image']==caller_image,'producer factoring inverse differs')
    return raw


def packet_restore(raw):
    packet=packet_decode(raw,PACKET_RAW_CAP)
    packet_require(set(packet)==PACKET_KEYS and packet['schema']=='staged_saved_F_detached_producer_packet_v1'
        and packet['authority']=='DRAFT_NONAUTHORITATIVE' and all(packet[key] is False for key in PACKET_FALSE),
        'closed detached producer packet required')
    sources=packet_files(packet['sources'],49);files=packet_files(packet['files'],683,2950863)
    packet_require(packet_pin(packet_canonical(sources))['sha256']==PACKET_SOURCE_EPOCH,'producer Source49 differs')
    packet_stages(packet['stages'],packet['clocks'])
    core_tail=packet['core_tail'];et=packet['expectation_tail'];ct=packet['context_tail']
    packet_require(type(core_tail) is dict and not {'source','files'}&set(core_tail)
        and type(core_tail.get('inventory')) is dict and set(core_tail['inventory'])=={'files','directories'}
        and type(et) is dict and 'caller_expectation_core' not in et
        and type(ct) is dict and not {'caller_expectation_core','source_pins','input_files'}&set(ct),'closed producer factoring fields required')
    core=dict(core_tail,files=files,source=sources);core['inventory']=dict(core_tail['inventory'],pins=files)
    expectation=dict(et,caller_expectation_core=core)
    context=dict(ct,caller_expectation_core=core,source_pins=sources,input_files=files)
    packet_envelopes(expectation,context,core,sources,files)
    e=packet_canonical(expectation);c=packet_canonical(context);i=packet_canonical(core)
    for value in (e,c,i):packet_require(len(value)<=PACKET_INPUT_CAP,'restored producer input cap')
    pins=packet['raw_pins'];packet_require(type(pins) is dict and set(pins)=={'expectation','context','caller_image'},'closed producer raw pins required')
    for key,value in (('expectation',e),('context',c),('caller_image',i)):
        packet_checked_pin(pins[key],PACKET_INPUT_CAP);packet_require(pins[key]==packet_pin(value),'restored producer raw pin differs: '+key)
    packet_require(context.get('expectation_sha')==pins['expectation']['sha256'],'producer context expectation pin differs')
    first=packet['stages'][0];context_pin=pins['context'];image_pin=pins['caller_image']
    packet_require(first['expectation_raw_pin']==pins['expectation'] and first['caller_image_pin']==image_pin
        and first['context_pin']==context_pin and first['held_image_pin']==image_pin,
        'G0 producer pin chain differs')
    packet_require(all(row['context_pin']==context_pin and row['held_image_pin']==image_pin for row in packet['stages'][1:]),
        'G2 G3 producer pin chain differs')
    start=context.get('invocation_started');deadline=context.get('deadline')
    packet_require(type(start) is float and math.isfinite(start) and start>0 and type(deadline) is float
        and math.isfinite(deadline) and deadline==start+180.0 and start<=packet['clocks'][0]<=packet['clocks'][-1]<=deadline,
        'producer invocation clock interval differs')
    return dict(packet=packet,expectation_raw=e,context_raw=c,caller_image=i)


def packet_wire(raw):
    packet_restore(raw)
    value=dict(encoding='zlib_base64',raw_pin=packet_pin(raw),data=base64.b64encode(zlib.compress(raw,9)).decode('ascii'))
    packet_require(len(packet_canonical(value))<=PACKET_WIRE_CAP,'producer wire cap; native admission still required')
    return value


def packet_unwire(value):
    packet_require(type(value) is dict and set(value)=={'encoding','raw_pin','data'} and value['encoding']=='zlib_base64'
        and type(value['data']) is str and len(packet_canonical(value))<=PACKET_WIRE_CAP,'closed bounded producer wire required')
    packet_checked_pin(value['raw_pin'],PACKET_RAW_CAP);compressed=base64.b64decode(value['data'],validate=True)
    decoder=zlib.decompressobj();raw=decoder.decompress(compressed,PACKET_RAW_CAP+1)
    packet_require(len(raw)<=PACKET_RAW_CAP and decoder.eof and not decoder.unconsumed_tail and not decoder.unused_data
        and packet_pin(raw)==value['raw_pin'],'complete producer compressed stream required')
    packet_restore(raw);return raw
