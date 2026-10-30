"""Full-context host protocol draft. Public issuer and Native provider are closed.

The orchestration body is exercised only in a private ordinary-test copy. It is
not an executable broker, source-authenticated lease, or full-role entry point.
"""
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
from threading import get_ident

ROOT = Path(__file__).absolute().parents[1]
P1 = ROOT / 'results/tables/staged_rts24_native_v1_non_authoritative/p1_01'
ENTRY_ROOT = ROOT / 'results/tables/staged_rts24_saved_fresh_full_role_entry_native_v1_non_authoritative'
SOURCE_EPOCH = 'acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875'
SCOPE = 'saved_P1_actual_21_and_journal_5h'
AUTHORITY = 'DRAFT_NONAUTHORITATIVE'
GATES = ('native_authorized', 'resource_admission', 'formal_result',
         'scientific_evidence_adopted', 'public_P2_execution_enabled')
CAPS = dict(wall_seconds=180, no_progress_seconds=65, rss_bytes=1024**3,
    process_commit_bytes=1024**3, job_commit_bytes=2*1024**3, output_bytes=8*1024**2,
    files=64, member_handles=1024, record_bytes=131072)
STAGES = dict(prepare=10, parent=45, fresh=40, inner_quiesce=5, inner_terminal=5,
    parent_compare=15, outer_quiesce=5, outer_terminal=10, final_check=15, final_publish=15, failure=15)
RESOURCES = ('mapping', 'mutex', 'view', 'job', 'thread', 'process')
EFFECTS = ('resource_snapshot', 'clock', 'check_context', 'check_manifest', 'check_transport', 'publish', 'published_read', 'endpoint_create', 'create_suspended',
    'child_identity', 'endpoint_commit', 'endpoint_read', 'accept_binding', 'resume',
    'terminate', 'quiet', 'close', 'closed_witness')


class FullHostUnavailable(RuntimeError): pass


class HostUnresolved(RuntimeError):
    def __init__(self, host, primary, secondary):
        self.host, self.primary, self.secondary = host, primary, tuple(secondary)
        super().__init__('full-role host lifetime unresolved')
    def __reduce__(self): raise TypeError('live host failure cannot be serialized')


def require(value, message):
    if not value: raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')


def pin(raw): return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())
def digest(value): return pin(canonical(value))['sha256']
def creator(): return os.getpid(), get_ident()


def decode(raw, cap=2*1024**2):
    require(type(raw) is bytes and 0 < len(raw) <= cap, 'bounded immutable bytes required')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key'); result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs)
    require(canonical(value) == raw, 'canonical closed record required')
    return value


def keys(value, names):
    require(type(value) is dict and set(value) == set(names.split()), 'closed fields differ')


def hex64(value):
    require(type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value), 'SHA/nonce domain')


def checked_pin(value, cap=8*1024**2):
    keys(value, 'bytes sha256'); hex64(value['sha256'])
    require(type(value['bytes']) is int and 0 <= value['bytes'] <= cap, 'pin byte cap')


def identity(value):
    keys(value, 'pid creation_filetime')
    require(all(type(v) is int and v > 0 for v in value.values()), 'physical process identity required')
    require(value['pid'] < 2**32 and value['creation_filetime'] < 2**64, 'Win32 identity widths')


def context_data(raw):
    """RAM relation only. Held source checker must still authenticate real input."""
    value = decode(raw)
    keys(value, 'schema authority scope repo_root input_root output_root source_pins executable environment '
        'anchor_sha input_files invocation_started deadline stage_seconds limits inherited_sources_pin '
        'caller_core caller_sha output_mode output_parent_directories ' + ' '.join(GATES))
    require(value['schema'] == 'staged_rts24_saved_P1_fresh_context_development_v1'
        and value['authority'] == AUTHORITY and value['scope'] == SCOPE
        and all(value[k] is False for k in GATES), 'full context scope/authority required')
    require(value['repo_root'] == str(ROOT) and value['input_root'] == str(P1)
        and value['output_mode'] == 'saved_P1_F_validation', 'full context roots/mode required')
    output = Path(value['output_root'])
    require(output.is_absolute() and '..' not in output.parts and output != P1
        and not output.is_relative_to(P1) and not P1.is_relative_to(output), 'disjoint absolute output required')
    require(value['limits'] == CAPS and value['stage_seconds'] == STAGES, 'original complete F budget required')
    started, deadline = value['invocation_started'], value['deadline']
    require(type(started) is type(deadline) is float and math.isfinite(started) and math.isfinite(deadline)
        and 0 < started < deadline and deadline == started + 180.0, 'one original 180 second clock required')
    require(type(value['source_pins']) is dict and len(value['source_pins']) == 49
        and digest(value['source_pins']) == SOURCE_EPOCH, 'complete frozen Source49 map required')
    require(type(value['input_files']) is dict and len(value['input_files']) == 683
        and value['anchor_sha'] == 'c6a25cd96c8a4a2cf293d41fe51bc7905db63fbc35253076f97e9239a4f22473', 'complete saved input map required')
    for item in (*value['source_pins'].values(), *value['input_files'].values(), value['inherited_sources_pin']): checked_pin(item)
    require(type(value['caller_core']) is dict and value['caller_sha'] == digest(value['caller_core'])
        and value['caller_core']['files'] == value['input_files']
        and value['caller_core']['source'] == value['source_pins'], 'full independent caller core relation')
    keys(value['executable'], 'path pin identity python'); checked_pin(value['executable']['pin'])
    require(value['executable']['path'] == str(Path('D:/Miniconda3/envs/compute/python.exe')), 'fixed executable path')
    require(type(value['environment']) is dict and value['environment']
        and all(type(k) is type(v) is str and k and '=' not in k and '\0' not in k+v for k,v in value['environment'].items())
        and len({k.upper() for k in value['environment']}) == len(value['environment']), 'closed Windows environment')
    require(type(value['output_parent_directories']) is list and value['output_parent_directories'], 'held parent directories required')
    return value


def request_data(raw, context_raw):
    value = decode(raw, 32768); context = context_data(context_raw)
    keys(value, 'schema authority scope role context_pin source_epoch invocation_started deadline nonce host_identity broker_identity')
    require(value['schema'] == 'staged_saved_F_full_host_request_v1' and value['authority'] == AUTHORITY
        and value['scope'] == SCOPE and value['role'] in ('controller','parent','fresh'), 'full host request required')
    require(value['context_pin'] == pin(context_raw) and value['source_epoch'] == SOURCE_EPOCH
        and value['invocation_started'] == context['invocation_started'] and value['deadline'] == context['deadline'], 'request/context clock and pin')
    hex64(value['nonce']); identity(value['host_identity']); identity(value['broker_identity'])
    require(value['host_identity'] != value['broker_identity'], 'independent host and broker required')
    return value, context


def offer_bytes(request_raw, context_raw):
    request, context = request_data(request_raw, context_raw)
    return canonical(dict(schema='staged_saved_F_full_host_offer_v1', authority=AUTHORITY, scope=SCOPE,
        request_sha=pin(request_raw)['sha256'], context=context, context_pin=pin(context_raw),
        host_identity=request['host_identity'], broker_identity=request['broker_identity'],
        invocation_started=request['invocation_started'], deadline=request['deadline']))


def ack_bytes(request_raw, context_raw, offer_raw):
    request, _ = request_data(request_raw, context_raw)
    require(offer_raw == offer_bytes(request_raw, context_raw), 'complete held OFFER differs')
    return canonical(dict(schema='staged_saved_F_full_host_ack_v1', authority=AUTHORITY, scope=SCOPE,
        request_sha=pin(request_raw)['sha256'], offer_sha=pin(offer_raw)['sha256'], context_sha=pin(context_raw)['sha256'],
        host_identity=request['host_identity'], broker_identity=request['broker_identity'], nonce=request['nonce'],
        invocation_started=request['invocation_started'], deadline=request['deadline']))


def artifacts(request_raw, context_raw, offer_raw, ack_raw, template_raw, transport_raw, payload_raw):
    """Forward-only hash DAG. Output remains data, with no launch authority."""
    request, context = request_data(request_raw, context_raw)
    require(ack_raw == ack_bytes(request_raw, context_raw, offer_raw), 'host ACK differs')
    template = decode(template_raw, 131072)
    keys(template, 'schema authority nonce source_pins source_epoch bootstrap_pin executable_pin python environment cwd '
        'initial_paths selected_runtime_file_observations startup_absent startup_profile namespace_helper import_helper '
        'import_policy import_profile producer_helpers graph_contract case')
    require(type(template) is dict and template.get('schema') == 'staged_saved_F_complete_bootstrap_manifest_v2'
        and template.get('authority') == AUTHORITY and template.get('source_epoch') == SOURCE_EPOCH
        and template.get('source_pins') == context['source_pins']
        and template.get('environment') == context['environment'] and template.get('cwd') == str(ROOT)
        and template.get('executable_pin') == context['executable']['pin']
        and template.get('nonce') == request['nonce'][:32]
        and 'pre_manifest_binding' not in template, 'unbound Core51 manifest template required')
    require(type(transport_raw) is bytes and 0 < len(transport_raw) <= 131072
        and type(payload_raw) is bytes and 0 < len(payload_raw) <= 131072
        and template.get('bootstrap_pin') == pin(transport_raw), 'held transport/payload bounds')
    nonce = request['nonce']; role = request['role']
    path = str(ENTRY_ROOT / 'transport' / nonce / (role+'.plan.json'))
    descriptor = dict(schema='staged_saved_F_pre_manifest_descriptor_v1', authority=AUTHORITY, scope=SCOPE,
        role=role, manifest_path=path, channel_name='Local\\saved_F_pre_entry_v1_'+nonce, channel_nonce=nonce,
        request_sha=pin(request_raw)['sha256'], offer_sha=pin(offer_raw)['sha256'], context_sha=pin(context_raw)['sha256'],
        ack_sha=pin(ack_raw)['sha256'], source_epoch=SOURCE_EPOCH, transport_pin=pin(transport_raw), payload_pin=pin(payload_raw),
        invocation_started=request['invocation_started'], deadline=request['deadline'])
    template['pre_manifest_binding'] = dict(descriptor)
    manifest = canonical(template); require(len(manifest) <= 131072, 'manifest byte cap')
    descriptor['manifest_sha'] = pin(manifest)['sha256']
    argv = [context['executable']['path'], '-P','-B','-s','-S','-c',transport_raw.decode('utf8'),
        '--full-role-pre-entry', path, descriptor['manifest_sha'], descriptor['channel_name'], nonce, role,
        descriptor['request_sha'], descriptor['offer_sha'], descriptor['context_sha'], descriptor['ack_sha'],
        request['invocation_started'].hex(), request['deadline'].hex()]
    require(len(argv) == 19 and all('\0' not in item for item in argv), 'closed actual argv')
    command = subprocess.list2cmdline(argv)
    units = len(command.encode('utf-16-le'))//2+1
    require(units <= 30000, 'complete quoted command line including NUL exceeds original cap')
    return dict(descriptor=descriptor, manifest=manifest, argv=argv, command=command, utf16_units=units)


def header_bytes(descriptor, child):
    identity(child)
    raw = canonical(dict(schema='staged_saved_F_pre_manifest_header_v1', nonce=descriptor['channel_nonce'],
        descriptor=descriptor, owner_pid=child['pid'], owner_creation_filetime=child['creation_filetime'], slots=16, slot_bytes=4096))
    require(0 < len(raw) <= 4096-44, 'endpoint header cap')
    return len(raw).to_bytes(4,'little')+raw+b'\0'*(4096-44-len(raw))+sha256(raw).digest()+b'FEPv1OK!'


class Host:
    __slots__ = ('_anchor',)
    def __new__(cls, *args, **kwargs): raise FullHostUnavailable('source-authenticated host issuer is closed')
    def __setattr__(self, name, value): raise TypeError('held host cannot be rebound')
    def __delattr__(self, name): raise TypeError('held host cannot be deleted')
    def __reduce__(self): raise TypeError('live host cannot be serialized')
    def __copy__(self): raise TypeError('live host cannot be copied')
    def __deepcopy__(self, memo): raise TypeError('live host cannot be copied')


def open_full_role_host(*args, **kwargs):
    raise FullHostUnavailable('external root, host Native provider and full-role entry remain unbound')


def _mechanical_host(request_raw, context_raw, template_raw, transport_raw, payload_raw, effects):
    raise FullHostUnavailable('no source-authenticated host effect issuer')
    require(type(effects) is tuple and len(effects) == len(EFFECTS) and all(callable(f) for f in effects), 'held effect table')
    request, context = request_data(request_raw, context_raw)
    require(request['role'] == 'controller', 'this host owns the outer prepare reservation; nested roles need their own source launcher')
    host = object.__new__(Host)
    immutable = (request_raw, context_raw, template_raw, transport_raw, payload_raw)
    # Native provider must publish acquisitions into this preallocated escrow.
    # Native-return-to-publication and coordinated root mutation remain OPEN.
    escrow = {name: None for name in RESOURCES}
    anchor = dict(host=host, creator=creator(), effects=effects, immutable=immutable,
        immutable_pins=tuple(pin(raw) for raw in immutable), escrow=escrow,
        acquisitions={}, close_states={name:['IDLE',0] for name in RESOURCES},
        state=['NEW'], release=['IDLE',0], termination=['IDLE',0], cleanup=['IDLE',None],
        primary=[None], errors=[], offer=[None], ack=[None], built=[None], binding=[None], child=[None],
        publication=[None], artifact_seal=[None], acceptance=['IDLE',0], publication_state=['IDLE',None],
        operation=['IDLE'], reentry=[0], last_clock=[context['invocation_started']],
        prepare_deadline=context['invocation_started']+10.0, cleanup_deadline=[None],
        deadline=context['deadline'], started=context['invocation_started'])
    object.__setattr__(host, '_anchor', tuple(anchor.items()))
    _seal_artifacts(anchor)
    _entry(host, ('NEW',)); return host


def _held(host, states):
    require(type(host) is Host, 'exact held host required')
    root = dict(object.__getattribute__(host, '_anchor'))
    require(root['host'] is host and root['creator'] == creator(), 'creating host required')
    if root['cleanup'][1] is not None: raise root['cleanup'][1]
    require(root['host'] is host and root['creator'] == creator() and root['state'][0] in states,
        'creating host and lifecycle state required')
    require(tuple(pin(raw) for raw in root['immutable']) == root['immutable_pins'], 'held host inputs changed')
    require(_artifact_image(root)==root['artifact_seal'][0] and root['reentry'][0]==0, 'committed host artifacts drifted or operation reentered')
    return root


def _entry(host, states):
    root = _held(host, states)
    now = _clock(root)
    require(now < min(root['prepare_deadline'],root['deadline']-15.0), 'original outer preparation/failure reservation expired')
    return root


def _clock(root):
    now = _effect(root, 'clock')
    require(type(now) is float and math.isfinite(now) and root['last_clock'][0] <= now, 'monotonic held clock required')
    root['last_clock'][0] = now
    return now


def _artifact_image(root):
    built=root['built'][0]
    return (root['offer'][0], root['ack'][0], root['binding'][0], root['child'][0], root['publication'][0],
        None if built is None else (canonical(built['descriptor']),built['manifest'],tuple(built['argv']),built['command'],built['utf16_units']))


def _seal_artifacts(root):root['artifact_seal'][0]=_artifact_image(root)


def _image(root):
    return (root['state'][0],root['operation'][0],root['reentry'][0],tuple(root['release']),tuple(root['termination']),
        tuple(root['acceptance']),tuple(root['publication_state']),tuple(root['acquisitions'].items()),
        tuple((name,tuple(state)) for name,state in root['close_states'].items()),_artifact_image(root))


def _effect(root, name, *args):
    if root['state'][0]!='CLOSING':require(_artifact_image(root)==root['artifact_seal'][0], 'held artifacts changed before effect')
    anchor=object.__getattribute__(root['host'],'_anchor'); before=_image(root); primary=None
    allowed={'endpoint_create':('mapping','mutex','view'),'create_suspended':('job','thread','process')}.get(name,())
    escrow={key:value for key,value in root['escrow'].items() if key not in allowed}
    try: return root['effects'][EFFECTS.index(name)](*args)
    except BaseException as error: primary=error; raise
    finally:
        try:
            require(object.__getattribute__(root['host'],'_anchor') is anchor and _image(root)==before,
                'effect changed committed host state or reentered')
            require(set(root['escrow'])==set(RESOURCES)
                and escrow=={key:value for key,value in root['escrow'].items() if key not in allowed},'effect changed another resource domain')
        except BaseException as error:
            root['errors'].append(('effect_bookend',error))
            if primary is None: raise


def _begin(host, name, states):
    require(type(host) is Host,'exact held host required')
    root=dict(object.__getattribute__(host,'_anchor'))
    require(root['host'] is host and root['creator']==creator(),'creating operation owner required')
    if root['operation'][0]!='IDLE':
        error=ValueError('reentrant host operation');root['reentry'][0]+=1;root['errors'].append(('reentry',error));raise error
    if root['cleanup'][1] is not None:raise root['cleanup'][1]
    require(root['state'][0] in states,'host lifecycle state required')
    root['operation'][0]=name;return root


def _finish(root): root['operation'][0]='IDLE'


def offer(host):
    root = _begin(host, 'offer', ('NEW',)); root['state'][0] = 'OFFER_ISSUED'
    try:
        _entry(host, ('OFFER_ISSUED',))
        request, context, *_ = root['immutable']
        require(_effect(root, 'check_context', context) is True, 'held full context source check rejected')
        raw = offer_bytes(request, context); root['offer'][0] = raw; _seal_artifacts(root)
        root['state'][0] = 'OFFERED'; _entry(host, ('OFFERED',)); return raw
    except BaseException as primary: return _abort(host, primary)
    finally: _finish(root)


def acknowledge(host, ack_raw):
    root = _begin(host, 'ack', ('OFFERED',))
    try:
        _entry(host, ('OFFERED',))
        request, context, *_ = root['immutable']
        require(ack_raw == ack_bytes(request, context, root['offer'][0]), 'full original ACK required')
        root['ack'][0] = ack_raw; _seal_artifacts(root); root['state'][0] = 'ACKED'
    except BaseException as primary: return _abort(host, primary)
    finally: _finish(root)


def _capture(root):
    require(type(root['escrow']) is dict and set(root['escrow']) == set(RESOURCES), 'fixed Native resource escrow')
    errors=[]
    try:
        observed=_effect(root,'resource_snapshot')
        require(type(observed) is tuple and len(observed)==2,'Native snapshot plus unresolved responsibility')
        snapshot,pending=observed
        require(type(pending) is tuple and len(set(pending))==len(pending) and all(type(name) is str and name in
            ('process_info_recovery','endpoint','creation','header_state','resume','termination','mutex','attributes','pending_member','provider_reentry','census_failure') for name in pending),
            'closed Native pending responsibility')
        require(type(snapshot) is tuple and len(snapshot)==len(RESOURCES)
            and tuple(row[0] for row in snapshot)==RESOURCES,'complete original Native resource snapshot')
        for name,value in snapshot:
            if value is None:continue
            require(type(value) is int and value>0,'Native snapshot resource domain')
            if root['escrow'][name] is None:root['escrow'][name]=value
            elif root['escrow'][name]!=value:errors.append(ValueError('host mirror changed from Native resource root'))
            if name in root['acquisitions']:
                require(root['acquisitions'][name]==value,'original Native acquisition identity changed')
            else:
                require(name=='view' or value not in (h for n,h in root['acquisitions'].items() if n!='view'),'duplicate recovered kernel HANDLE')
                root['acquisitions'][name]=value
        if pending:errors.append(ValueError('unresolved Native responsibility: '+','.join(pending)))
    except BaseException as error:errors.append(error)
    for name, handle in root['escrow'].items():
        try:
            if handle is not None:
                require(type(handle) is int and handle > 0, 'positive owned Native handle')
                if name in root['acquisitions']:
                    require(root['acquisitions'][name] == handle, 'retained resource replaced')
                else:
                    require(name=='view' or handle not in (h for n,h in root['acquisitions'].items() if n!='view'), 'duplicate kernel handle')
                    root['acquisitions'][name] = handle
        except BaseException as error:errors.append(error)
    if errors:raise errors[0]


def _acquire(root,name,*args):
    try:_effect(root,name,*args)
    except BaseException:
        try:_capture(root)
        except BaseException as secondary:root['errors'].append(('acquisition_capture',secondary))
        raise
    _capture(root)


def _publish_manifest(root, built):
    root['publication_state'][:]=['ISSUED',built['descriptor']['manifest_path']]
    try:
        receipt=_effect(root,'publish',built['descriptor']['manifest_path'],built['manifest'])
        keys(receipt,'path pin identity create_only')
        require(receipt['path']==built['descriptor']['manifest_path'] and receipt['pin']==pin(built['manifest'])
            and type(receipt['identity']) is list and len(receipt['identity'])==4
            and all(type(n) is int and n>=0 for n in receipt['identity']) and receipt['create_only'] is True,'create-only manifest receipt')
        root['publication'][0]=canonical(receipt);_seal_artifacts(root)
        _publication_bookend(root)
        root['publication_state'][0]='RETAINED'
    except BaseException:
        root['publication_state'][0]='UNCERTAIN';raise


def prepare(host):
    root = _begin(host, 'prepare', ('ACKED',)); root['state'][0] = 'PREPARE_ISSUED'
    try:
        _entry(host, ('PREPARE_ISSUED',))
        request_raw, context_raw, template, transport, payload = root['immutable']
        request, context = request_data(request_raw, context_raw)
        built = artifacts(request_raw, context_raw, root['offer'][0], root['ack'][0], template, transport, payload)
        root['built'][0] = built
        _seal_artifacts(root)
        require(_effect(root, 'check_context', context_raw) is True, 'full source bookend before publication')
        require(_effect(root, 'check_transport', transport, payload) is True, 'held transport/payload equivalence rejected')
        require(_effect(root, 'check_manifest', built['manifest']) is True, 'held Core manifest check rejected')
        # Published manifests are retained immutable forensic artifacts. Even an
        # uncertain publication permanently consumes this nonce/path reservation.
        _publish_manifest(root,built)
        _entry(host, ('PREPARE_ISSUED',))
        _acquire(root,'endpoint_create',root['escrow'],canonical(built['descriptor']))
        require(all(root['escrow'][name] is not None for name in ('mapping','mutex','view')), 'all endpoint resources required')
        _entry(host, ('PREPARE_ISSUED',))
        _acquire(root,'create_suspended',root['escrow'],tuple(built['argv']),context['repo_root'],canonical(context['environment']),canonical(context['limits']))
        require(all(root['escrow'][name] is not None for name in ('job','process','thread')), 'all suspended child resources required')
        child = _effect(root, 'child_identity', root['escrow']); identity(child)
        require(child not in (request['host_identity'], request['broker_identity']), 'distinct suspended child identity')
        root['child'][0] = canonical(child);_seal_artifacts(root)
        header = header_bytes(built['descriptor'], child)
        require(_effect(root, 'endpoint_commit', root['escrow'], header) is True, 'endpoint commit rejected')
        require(_effect(root, 'endpoint_read', root['escrow']) == header+b'\0'*(69632-4096), 'complete initial endpoint readback')
        require(canonical(_effect(root, 'child_identity', root['escrow'])) == root['child'][0], 'suspended child identity bookend')
        binding = canonical(dict(schema='staged_saved_F_full_host_binding_v1', authority=AUTHORITY, scope=SCOPE,
            request_sha=pin(request_raw)['sha256'], offer_sha=pin(root['offer'][0])['sha256'], ack_sha=pin(root['ack'][0])['sha256'],
            context_sha=pin(context_raw)['sha256'], descriptor=built['descriptor'], header_pin=pin(header),
            argv_pin=pin(canonical(built['argv'])), command_utf16_units=built['utf16_units'], child=child,
            command_pin=pin(built['command'].encode('utf-16-le')+b'\0\0'), manifest_receipt=decode(root['publication'][0]),
            host_identity=request['host_identity'], broker_identity=request['broker_identity'],
            invocation_started=root['started'], deadline=root['deadline']))
        root['binding'][0] = binding;_seal_artifacts(root); root['state'][0] = 'BOUND'
        _entry(host, ('BOUND',)); return binding
    except BaseException as primary: return _abort(host, primary)
    finally: _finish(root)


def _publication_bookend(root):
    receipt=decode(root['publication'][0]); observed=_effect(root,'published_read',receipt['path'])
    require(type(observed) is tuple and len(observed)==2 and observed[0]==root['built'][0]['manifest']
        and canonical(observed[1])==root['publication'][0], 'published manifest bytes/identity changed')


def release_ack_bytes(binding_raw):
    binding = decode(binding_raw, 16384)
    require(binding.get('schema') == 'staged_saved_F_full_host_binding_v1', 'full binding required')
    return canonical(dict(schema='staged_saved_F_full_host_release_ack_v1',authority=AUTHORITY,scope=SCOPE,binding_pin=pin(binding_raw),
        host_identity=binding['host_identity'], broker_identity=binding['broker_identity'],
        invocation_started=binding['invocation_started'], deadline=binding['deadline']))


def release(host, release_ack):
    root = _begin(host, 'release', ('BOUND',))
    try:
        _entry(host, ('BOUND',))
        require(release_ack == release_ack_bytes(root['binding'][0]), 'exact binding release ACK required')
        _capture(root)
        require(canonical(_effect(root, 'child_identity', root['escrow'])) == root['child'][0], 'pre-release actual child identity')
        built = root['built'][0]
        expected = header_bytes(built['descriptor'], decode(root['child'][0]))+b'\0'*(69632-4096)
        require(_effect(root, 'endpoint_read', root['escrow']) == expected, 'pre-release endpoint changed')
        require(_effect(root, 'check_context', root['immutable'][1]) is True, 'pre-release full source bookend')
        _publication_bookend(root)
        _entry(host, ('BOUND',))
        require(root['release']==['IDLE',0] and root['acceptance']==['IDLE',0], 'one host acceptance/resume attempt required')
        root['acceptance'][:]=['ISSUED',1]
        require(_effect(root, 'accept_binding', root['binding'][0], release_ack) is True, 'external host acceptance required')
        root['acceptance'][0]='DONE'
        _entry(host, ('BOUND',))  # Acceptance is retained if its return exhausted the original reservation.
        root['state'][0] = 'RELEASE_ISSUED'; root['release'][:] = ['ISSUED',1]
        require(_effect(root, 'resume', root['escrow']) == 1, 'ResumeThread must return original suspended count one')
        root['release'][0] = 'DONE'; root['state'][0] = 'ACTIVE'; _entry(host, ('ACTIVE',))
    except BaseException as primary:
        if root['acceptance'][0]=='ISSUED':root['acceptance'][0]='UNCERTAIN'
        if root['release'][0] == 'ISSUED': root['release'][0] = 'UNCERTAIN'
        return _abort(host, primary)
    finally: _finish(root)


def _abort(host, primary):
    return _close(dict(object.__getattribute__(host,'_anchor')), primary)


def close(host, primary=None):
    """Single-attempt cleanup. Original failure objects and resource roots survive."""
    require(type(host) is Host, 'exact retained host required')
    root = dict(object.__getattribute__(host, '_anchor'))
    require(root['host'] is host and root['creator'] == creator(), 'creating cleanup owner required')
    if root['operation'][0]!='IDLE':
        error=ValueError('reentrant host cleanup');root['reentry'][0]+=1;root['errors'].append(('reentry',error));raise error
    root['operation'][0]='close'
    try:return _close(root,primary)
    finally:_finish(root)


def _close(root, primary):
    host=root['host']
    ledger = root['cleanup']
    if ledger[0] in ('CLOSED','UNRESOLVED'):
        if ledger[1] is not None: raise ledger[1]
        try:
            require(primary is None, 'closed host cannot accept another failure')
            require(root['escrow'] == {name:root['acquisitions'].get(name) for name in RESOURCES}
                and all(root['close_states'][name] == ['CLOSED',1] for name in root['acquisitions']), 'terminal resource ledger drift')
        except BaseException as error:
            root['errors'].append(('terminal_drift',error)); failure = HostUnresolved(host,primary,root['errors'])
            ledger[:] = ['UNRESOLVED',failure]; root['state'][0] = 'UNRESOLVED'; raise failure from error
        return
    if ledger[0] != 'IDLE':
        error = ValueError('reentrant host cleanup'); root['errors'].append(('reentry',error)); raise error
    ledger[0] = 'ISSUED'; root['state'][0] = 'CLOSING'
    root['primary'][0] = primary
    errors = root['errors']
    try:require(_artifact_image(root)==root['artifact_seal'][0], 'held artifact drift on cleanup')
    except BaseException as error:errors.append(('artifact_drift',error))
    try:
        now=_clock(root);root['cleanup_deadline'][0]=min(root['deadline'],now+15.0)
    except BaseException as error:
        errors.append(('cleanup_clock',error));root['cleanup_deadline'][0]=root['deadline']
    try: _capture(root)
    except BaseException as error: errors.append(('resource_capture',error))
    held = root['acquisitions']; quiet = not any(name in held for name in ('job','process','thread'))
    if not quiet:
        try:
            require('job' in held, 'partial child has no held Job')
            root['termination'][:] = ['ISSUED',1]
            require(_effect(root, 'terminate', {name:held.get(name) for name in RESOURCES}) is True, 'TerminateJob failed')
            root['termination'][0] = 'DONE'
        except BaseException as error:
            root['termination'][0] = 'UNCERTAIN'; errors.append(('termination',error))
        try:
            require('job' in held, 'Job identity missing; retain every resource')
            if any(name in held for name in ('process','thread')) and root['child'][0] is None:
                require('process' in held,'partial thread has no authenticated process identity')
                observed=_effect(root,'child_identity',{name:held.get(name) for name in RESOURCES});identity(observed)
                root['child'][0]=canonical(observed);_seal_artifacts(root)
            now = _clock(root); limit = min(root['cleanup_deadline'][0], now+5.0)
            require(root['started'] <= now <= root['deadline'], 'no remaining original quiet budget')
            witness = _effect(root, 'quiet', {name:held.get(name) for name in RESOURCES}, limit)
            keys(witness, 'complete job_handle member_identities active_processes retained_handles_signaled observed_total observed_count final_pids')
            members=witness['member_identities']
            require(type(members) is list and len(members)<=CAPS['member_handles'] and witness['job_handle']==held['job'], 'held Job quiet identity and member cap')
            for member in members:identity(member)
            require(len({canonical(member) for member in members})==len(members), 'unique retained process identities')
            if root['child'][0] is not None:require(decode(root['child'][0]) in members,'original child missing from quiet witness')
            child_present=any(name in held for name in ('process','thread'))
            require(witness['complete'] is True and type(witness['active_processes']) is int and witness['active_processes'] == 0
                and witness['retained_handles_signaled'] is True and type(witness['observed_total']) is type(witness['observed_count']) is int
                and witness['observed_total'] == witness['observed_count'] == len(members)
                and len(members)>=(1 if child_present else 0) and witness['final_pids'] == [], 'complete Job quiet witness required')
            require(_clock(root) <= limit, 'quiet exceeded remaining original budget'); quiet = True
        except BaseException as error: errors.append(('quiet',error))
    # Keep every handle/endpoint if Job quiet is unproven. Never tear down live communication.
    if quiet:
        for name in ('thread','process','job','view','mutex','mapping'):
            if name not in held: continue
            state = root['close_states'][name]
            try:
                require(state == ['IDLE',0], 'resource close was already issued')
                state[:] = ['ISSUED',1]
                require(_effect(root, 'close', name, held[name]) is True, 'native close failed')
                require(_effect(root, 'closed_witness', name, held[name]) is True, 'physical close witness failed')
                state[0] = 'CLOSED'
            except BaseException as error:
                state[0] = 'UNCERTAIN'; errors.append(('close_'+name,error))
            try:require(_clock(root)<=root['cleanup_deadline'][0], 'cleanup exceeded original remaining reservation')
            except BaseException as error:errors.append(('close_deadline_'+name,error))
    failure = None if primary is None and not errors else HostUnresolved(host, primary, errors)
    ledger[:] = ['CLOSED' if not errors else 'UNRESOLVED', failure]
    root['state'][0] = ledger[0]
    if failure is not None: raise failure from primary
