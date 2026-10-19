"""Fresh detached replay of a pinned selector bridge; no producer or retry."""
import json
import os
from pathlib import Path
import stat

from experiments import h1_selector_raw_science_development_v1 as bridge

io=bridge.io
SCHEMA='h1_selector_raw_science_inspect_development_v1'


def _scope():
    bridge._scope()
    if SCHEMA!='h1_selector_raw_science_inspect_development_v1':
        raise ValueError('selector inspector scope changed')


def implementation_identity():
    _scope()
    return io.digest(io.encode([SCHEMA,io.digest(Path(__file__).read_bytes()),bridge.implementation_identity()]))


def _directory(path,names):
    info=path.stat(follow_symlinks=False)
    if (not stat.S_ISDIR(info.st_mode)
            or getattr(info,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',1024)):
        raise ValueError('plain selector directory required')
    found=set()
    with os.scandir(path) as entries:
        for entry in entries:
            if entry.name not in names or entry.name in found:
                raise ValueError('selector inspector namespace differs')
            found.add(entry.name)
    if found!=names:raise ValueError('selector inspector namespace incomplete')
    return (info.st_dev,info.st_ino,info.st_mtime_ns,info.st_ctime_ns)


def inspect(root,frame,disclosure,before,records,*,expected_terminal_sha256,**args):
    """Verify saved consistency at return; never infer historical call success.

    Only a retained external terminal pin selects a candidate. A returned dict
    conveys no owner, native, retry, paired-commit or formal authority.
    """
    with bridge.science.prior.guard.solver_calls_forbidden():
        if set(args) not in ({'lane','selector','specification','limits'},
                             {'lane','selector','specification','limits','power'}):
            raise ValueError('exact selector inspection arguments required')
        limits=args['limits']
        if type(limits) is not bridge.selector.ReplayLimits:
            raise ValueError('typed selector replay limits required')
        limits.__post_init__()
        own=implementation_identity();io.pin(expected_terminal_sha256)
        root=Path(root)
        if not root.is_absolute() or root!=root.resolve(strict=True):
            raise ValueError('canonical absolute selector root required')
        capture=root/'capture';raw_root=capture/'native_raw';stage=raw_root/'000'
        namespaces={root:{'capture','postsolve.json','observations.json','selector_record.json','terminal.json'},
            capture:{'binding.json','specification.json','export.json','complete.json','native_raw'},
            raw_root:{'binding.json','terminal.json','000'},
            stage:{'intent.json','raw.bin','raw_receipt.json','outcome.json'}}
        directories={p:_directory(p,names) for p,names in namespaces.items()}
        caps={root/'postsolve.json':bridge.science.POST_CAP,root/'observations.json':io.RAW_CAP,
            root/'selector_record.json':limits.max_record_bytes,root/'terminal.json':io.RAW_CAP,
            stage/'raw.bin':io.RAW_CAP}
        for directory,names in namespaces.items():
            for name in names:
                p=directory/name
                if p not in namespaces and p not in caps:caps[p]=io.META_CAP
        views={}
        for p,cap in caps.items():
            if getattr(p.stat(follow_symlinks=False),'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',1024):
                raise ValueError('plain selector file required')
            views[p]=io.read_stable(p,cap)
            doc=json.loads(views[p][0],object_pairs_hook=bridge.selector.native._unique_object,
                parse_constant=bridge.selector.native._reject_constant)
            encoded=bridge.selector.native._encoded(doc) if p==root/'selector_record.json' else io.encode(doc)
            if encoded!=views[p][0]:raise ValueError('canonical selector artifact required')
        def data(p):return views[p][0]
        terminal=data(root/'terminal.json')
        if io.digest(terminal)!=expected_terminal_sha256:
            raise ValueError('external selector terminal pin differs')
        key,identity,locks=bridge._prefix(frame,disclosure,before,records,args)
        model=bridge.selector.build_development_stage(frame,disclosure,before,lane=args['lane'],
            power=args.get('power'),index=len(records),frozen=locks,expected_identity=identity)
        if args['specification'].name!='gurobi':raise ValueError('Gurobi selector capture required')
        bridge._admit_model(model,args['limits'])
        binding=io.digest(data(capture/'binding.json'));export=io.digest(data(capture/'export.json'))
        bridge.science._source_view(stage/'raw.bin',key,model,args['specification'],binding,export)
        native=data(stage/'raw.bin');post=data(root/'postsolve.json');complete=data(capture/'complete.json')
        expected_complete=dict(schema=bridge.capture.SCHEMA,binding_sha256=binding,
            raw_sha256=io.digest(native),raw_terminal_sha256=io.digest(data(raw_root/'terminal.json')),
            callback_sequence_complete=True,**bridge.capture.FLAGS)
        if complete!=io.encode(expected_complete):raise ValueError('selector capture completion differs')
        raw_check=io.inspect(raw_root,expected_request=key,
            expected_binding_sha256=io.digest(data(raw_root/'binding.json')))
        if not raw_check['callback_sequence_complete'] or raw_check['errors']:
            raise ValueError('selector capture chain incomplete')
        observation=bridge._observe(model,args['specification'])
        observations=[observation,observation,observation]
        expected_observations=io.encode(dict(schema=bridge.SCHEMA+'_observations',observations=observations,
            option_basis='declared options checked by completed StageCapture before apply',
            call_basis='one intercepted apply in completed StageCapture',
            evidence_role='reconstructed_selector_view',capture_complete_sha256=io.digest(complete)))
        if expected_observations!=data(root/'observations.json'):
            raise ValueError('selector observations do not reproduce')
        result=bridge._audit_stage(native,post,frame,disclosure,before,records,expected_key=key,
            expected_binding=binding,expected_export=export,observations=observations,**args)
        if result['selector_record']!=data(root/'selector_record.json'):
            raise ValueError('saved selector record differs from fresh replay')
        # _audit_stage already performs the closed full-prefix replay and derives
        # the lock and chain-complete bit from that replay, not stored metadata.
        expected={k:v for k,v in result.items() if k!='selector_record'}
        expected.update(schema=bridge.SCHEMA,request_key=key,evidence_role='reconstructed_selector_view',
            capture_complete_sha256=io.digest(complete),binding_sha256=binding,export_sha256=export,
            observations_sha256=io.digest(expected_observations),selector_record_sha256=io.digest(result['selector_record']))
        if io.encode(expected)!=terminal:raise ValueError('selector terminal reconstruction differs')
        if implementation_identity()!=own or bridge.request_key(frame,disclosure,before,records,**args)!=key:
            raise ValueError('selector inspector dependency/input drift')
        for p,(raw,stamp) in views.items():
            if io.read_stable(p,caps[p])!=(raw,stamp):raise ValueError('selector inspector retained view changed')
        for p,names in namespaces.items():
            if _directory(p,names)!=directories[p]:raise ValueError('selector inspector directory changed')
        if any(io.identity(p)!=stamp for p,(_,stamp) in views.items()):
            raise ValueError('selector inspector final file view changed')
        if (implementation_identity()!=own
                or bridge.request_key(frame,disclosure,before,records,**args)!=key
                or bridge._observe(model,args['specification'])!=observation):
            raise ValueError('selector inspector final dependency/input/observation drift')
        _scope()
        return dict(schema=SCHEMA,implementation_identity=own,state='saved_numerical_consistency',
            request_key=key,terminal_sha256=expected_terminal_sha256,
            selector_record_sha256=io.digest(result['selector_record']),selector_record=result['selector_record'],
            canonical_lock_hex=result['lock_hex'],selector_chain_complete=result['selector_chain_complete'],
            completion_scope='selector_replay_chain_only',fresh_at_return=True,solver_calls=0,
            historical_native_execution_authenticated=False,retry_authorized=False,
            owner_consumption_authorized=False,**bridge.FLAGS)
