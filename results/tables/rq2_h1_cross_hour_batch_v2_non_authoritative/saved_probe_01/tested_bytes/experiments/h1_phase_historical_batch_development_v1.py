"""Rebuild all selected N prefix frames in one bounded historical observation.

DRAFT_NONAUTHORITATIVE. Frames are detached replay data, never live authority.
No cache survives this call. Original controller/storage/math remain unchanged.
"""
from dataclasses import asdict, fields, is_dataclass
from datetime import datetime
from fractions import Fraction
from pathlib import Path
import re
import sys

from experiments import h1_phase_obligation_controller_development_v1 as old
from experiments import h1_historical_parent_prefix_development_v1 as history
from experiments import h1_current_grid_information_development_v1 as current
from experiments import h1_phase_historical_controller_development_v1 as predecessor

io,binding,bridge,base=old.io,old.binding,old.bridge,old.base
SCHEMA='h1_phase_historical_batch_development_v1'
MAX_RETAINED_BYTES=128*1024**2


def retained_size(value):
    """Conservative reachable Python data size; separate from process RSS."""
    seen=set();total=0
    def visit(item,depth=0):
        nonlocal total
        if depth>48 or len(seen)>2_000_000:raise ValueError('bounded batch data topology required')
        if id(item) in seen:return
        seen.add(id(item));total+=sys.getsizeof(item)
        if total>MAX_RETAINED_BYTES:raise ValueError('batch retained data byte cap exceeded')
        if is_dataclass(item) and not isinstance(item,type):
            if hasattr(item,'__dict__'):total+=sys.getsizeof(vars(item))
            for field in fields(item):visit(getattr(item,field.name),depth+1)
        elif type(item) is dict:
            for key,val in item.items():visit(key,depth+1);visit(val,depth+1)
        elif type(item) in (tuple,list,set,frozenset):
            for val in item:visit(val,depth+1)
        elif type(item) is Fraction:
            visit(item.numerator,depth+1);visit(item.denominator,depth+1)
        elif item is not None and type(item) not in (str,bytes,int,float,bool,datetime):
            raise ValueError('unsupported retained batch data type: '+type(item).__name__)
    visit(value)
    if total>MAX_RETAINED_BYTES:raise ValueError('batch retained data byte cap exceeded')
    return total


def prefix_evidence(evidence,hour):
    selected={}
    for name,pin in evidence.items():
        parts=Path(name).parts
        if parts[0]=='obligation_non_authoritative':
            include=parts[1]=='binding.json' or int(parts[1][:3])<=hour
        elif parts[0]=='clock_bridge_non_authoritative':include=int(parts[1])<=hour
        elif re.fullmatch(r'job_([0-9]{3})_non_authoritative',parts[0]):include=int(parts[0][4:7])<=hour
        else:raise ValueError('unexpected batch evidence namespace')
        if include:selected[name]=pin
    return selected


def _fingerprint(value):
    if isinstance(value,bytes):return ['bytes',io.digest(value)]
    if isinstance(value,(tuple,list)):return [_fingerprint(v) for v in value]
    return value


def _observe(observed,key,value):
    pin=io.digest(io.encode(_fingerprint(value)))
    if key in observed and observed[key]!=pin:raise ValueError('retained observation changed: '+key)
    observed[key]=pin


def _source_paths(declaration):
    return predecessor._source_paths(declaration)


def _observe_sources(observed,declaration):
    files,directories=_source_paths(declaration)
    _observe(observed,'source support paths',sorted(str(p) for p in files|directories))
    for path in sorted(files):
        history.chunks.base.local._file_identity(path)
        _observe(observed,'source file '+str(path),io.identity(path))
    for path in sorted(directories):
        info=history.chunks.base.local._path(path).stat()
        names=history.bounded.prior.hour_api._names(path,4096)
        _observe(observed,'source directory '+str(path),(info.st_dev,info.st_ino,sorted(names)))


def _observe_prefix(observed,root,hours,stages):
    parent=root/'source_parent_non_authoritative'
    def file(path,cap):_observe(observed,'file '+str(path),history._read_single(path,cap))
    def directory(path,names):_observe(observed,'directory '+str(path),bridge.worker.hour._directory(path,names))
    for name in ('parent_events_non_authoritative','parent_anchor_non_authoritative'):
        path=parent/name
        with_view=history.prior.ReadView(path)
        try:_observe(observed,'lease '+str(path),(with_view.directory_identity,with_view.lock_identity))
        finally:with_view.close()
        file(path/'header.json',history.anchor.MAX_RECORD_BYTES)
    anchors=parent/'parent_anchor_non_authoritative';events=parent/'parent_events_non_authoritative'
    for i in range(2*hours+1):file(anchors/f'{i:03d}.json',history.anchor.MAX_RECORD_BYTES)
    for i in range(1,2*hours+1):
        path=events/f'{i:03d}';directory(path,{'metadata.bin','payload.bin','commit.json'})
        for name in ('metadata.bin','payload.bin','commit.json'):file(path/name,history.journal.CONTENT_CAP)
    file(root/'clock_bridge_non_authoritative'/'binding.json',old.CAP)
    for h in range(hours):
        child=parent/f'hour_{h:03d}_non_authoritative';directory(child,{'reference.json'});file(child/'reference.json',old.CAP)
        clock=root/'clock_bridge_non_authoritative'/f'{h:03d}'
        directory(clock,{'intent.json','job.json','terminal.json'})
        for name in ('intent.json','job.json','terminal.json'):file(clock/name,old.CAP)
        job=root/f'job_{h:03d}_non_authoritative'
        _observe(observed,'Job '+str(job),base.parent.job_view(job,stages))


def implementation_identity():
    return io.digest(io.encode([SCHEMA,old.implementation_identity(),history.implementation_identity(),
        current.implementation_identity(),predecessor.implementation_identity(),io.digest(Path(__file__).read_bytes())]))


def _obligation_inventory(root,hours,retained):
    names=history.bounded.prior.hour_api._names(root,578)
    if not {'execution.lock','binding.json'}<=names:raise ValueError('obligation base inventory missing')
    stages={};views={};order=('binding','job','terminal')
    for name in names-{'execution.lock','binding.json'}:
        match=re.fullmatch(r'([0-9]{3})\.(binding|job|terminal)\.json',name)
        if match is None or not 0<=int(match[1])<192:raise ValueError('unexpected obligation suffix name')
        identity=history.chunks.base.local._file_identity(root/name)
        if identity in views.values():raise ValueError('obligation namespace inode alias')
        views[name]=identity;stages.setdefault(int(match[1]),set()).add(match[2])
    if not set(range(hours))<=stages.keys():raise ValueError('obligation prefix missing')
    if stages and set(stages)!=set(range(max(stages)+1)):raise ValueError('obligation namespace gap')
    for hour,kinds in stages.items():
        if kinds!=set(order[:len(kinds)]) or (hour<hours or hour<max(stages)) and kinds!=set(order):
            raise ValueError('obligation publication order differs')
    if any(views.get(name)!=identity for name,identity in retained.items()):
        raise ValueError('observed obligation file removed or replaced')
    retained.update(views)


class HistoricalTimedSnapshot(history.HistoricalSnapshot,binding.snapshot.parent.SourceParent):
    """Retain the timed declaration, Job child and carry replay MRO."""


def replay_prefixes(root,*,expected_binding_sha256,expected_terminal_sha256,completed_hours,expected_terminals,selected_hours,_observed=None):
    old.additional_content_bound(completed_hours)
    if (type(expected_terminals) is not dict or not expected_terminals
            or any(type(h) is not int or not 0 <= h < completed_hours for h in expected_terminals)
            or set(expected_terminals) != set(range(completed_hours))):
        raise ValueError('bounded selected historical terminal map required')
    if (type(selected_hours) is not tuple or not selected_hours or any(type(h) is not int for h in selected_hours)
            or selected_hours != tuple(sorted(set(selected_hours))) or not set(selected_hours)<=set(expected_terminals)):
        raise ValueError('bounded sorted selected hours required')
    expected_terminals = {h:io.pin(pin) for h,pin in expected_terminals.items()}
    if io.pin(expected_terminal_sha256) != expected_terminals[completed_hours-1]:
        raise ValueError('latest and selected terminal pins differ')
    root=history.chunks.base.local._path(Path(root).absolute())
    own=implementation_identity();old_identity=old.implementation_identity()
    directory=root/'obligation_non_authoritative';clock=root/'clock_bridge_non_authoritative'
    observed={} if _observed is None else _observed
    leases=[];views=observed.setdefault('views',{});topology=observed.setdefault('topology',{})
    obligation_names=observed.setdefault('obligation_names',{});identities=observed.setdefault('identities',{})
    captured={};evidence={};seen_hours=[];retained_bytes=0
    def read(path,pin):
        before=history.chunks.base.local._file_identity(path)
        value,view=base.entry.read(path,pin,old.CAP)
        if history.chunks.base.local._file_identity(path)!=before:raise ValueError('historical evidence replaced')
        if path in views and views[path]!=(old.CAP,view):raise ValueError('retained evidence changed')
        views[path]=(old.CAP,view)
        evidence[str(path.relative_to(root))]=pin
        return value
    def inventory():
        for lease in leases:lease.check()
        _obligation_inventory(directory,completed_hours,obligation_names)
        for path,base_names,pattern,low in (
            (root,{'execution.lock','source_parent_non_authoritative','obligation_non_authoritative','clock_bridge_non_authoritative'},r'job_([0-9]{3})_non_authoritative',0),
            (clock,{'execution.lock','binding.json'},r'([0-9]{3})',0),
        ):
            found=history._inventory(path,base_names,pattern=pattern,low=low,high=191,directories=True,retained=topology)
            if not set(range(completed_hours))<=found:raise ValueError('historical Job/clock prefix missing')
    reader=None;completed=False
    try:
        for path in (root,directory,clock,root/'source_parent_non_authoritative'):
            lease=history.prior.ReadView(path);leases.append(lease)
            _observe(identities,'lease '+str(path),(lease.directory_identity,lease.lock_identity))
        inventory()
        header=read(directory/'binding.json',expected_binding_sha256)
        declaration=header['parent_declaration'];budget=base.old.process.TaskProcessBudget(**header['budget'])
        budget.__post_init__()
        _observe_sources(identities,declaration)
        resolver=binding.open_manifest()
        node=binding.precheck(resolver,declaration,family=header['family'],ordinal=header['ordinal'],relative_hour=0)
        if not io.same(header,dict(schema=old.SCHEMA,implementation=old_identity,parent_declaration=declaration,
                parent_identity=io.digest(io.encode(declaration)),manifest_sha256=resolver.identity,
                family=header['family'],ordinal=header['ordinal'],hours=192,budget=asdict(budget),
                clock_binding_sha256=io.pin(header['clock_binding_sha256']),**old.FLAGS)):
            raise ValueError('historical obligation header differs')
        if declaration['hours']!=192 or Path(declaration['root'])!=root/'source_parent_non_authoritative':
            raise ValueError('historical obligation parent path/horizon differs')
        enrollment=binding.prevalidate_enrollment(resolver,declaration,family=header['family'],ordinal=header['ordinal'],relative_hour=0)
        records={};next_pin=io.pin(expected_terminal_sha256)
        for hour in reversed(range(completed_hours)):
            if hour in expected_terminals and next_pin != expected_terminals[hour]:
                raise ValueError('selected terminal does not belong to the pinned N chain')
            terminal=read(directory/f'{hour:03d}.terminal.json',next_pin)
            link=read(directory/f'{hour:03d}.job.json',terminal['job_link_sha256'])
            joined=read(directory/f'{hour:03d}.binding.json',link['obligation_binding_sha256'])
            if (not io.same(link,dict(schema=old.SCHEMA,obligation_binding_sha256=link['obligation_binding_sha256'],job_pins=link['job_pins'],**old.FLAGS))
                    or not io.same(terminal,dict(schema=old.SCHEMA,previous_sha256=terminal['previous_sha256'],
                        job_link_sha256=terminal['job_link_sha256'],clock_terminal_sha256=terminal['clock_terminal_sha256'],
                        parent_head=terminal['parent_head'],parent_anchor_sha256=terminal['parent_anchor_sha256'],
                        relative_hour=hour,controller_live_join_checked=True,**old.FLAGS))):
                raise ValueError('historical obligation chain differs')
            records[hour]=terminal,link,joined;next_pin=terminal['previous_sha256']
        if next_pin!=expected_binding_sha256:raise ValueError('historical obligation genesis differs')

        class Reader(HistoricalTimedSnapshot):
            def inspect(self):
                nonlocal retained_bytes
                # The predecessor constructor already performs one complete
                # inspect. Its explicit second inspect is another traversal.
                # Retain only the latest traversal; both still run in full.
                if seen_hours:
                    if seen_hours!=list(range(completed_hours)):
                        raise ValueError('new traversal before the previous prefix completed')
                    seen_hours.clear();captured.clear();retained_bytes=0
                return super().inspect()

            def _child(self,hour,packet,intent_head,lineage,*,expected_head,create=False):
                terminal,link,joined=records[hour]
                request=read(root/f'job_{hour:03d}_non_authoritative'/'request.json',link['job_pins']['request.json'])
                if not io.same(request['budget'],header['budget']):raise ValueError('historical episode budget differs')
                expected=old._historical_binding(packet,request,node,enrollment)
                if not io.same(joined,dict(schema=old.SCHEMA,implementation=old_identity,obligation=expected,
                        expected_worker_request_sha256=link['job_pins']['request.json'],**old.FLAGS)):
                    raise ValueError('historical obligation packet/request differs')
                ct=read(clock/f'{hour:03d}'/'terminal.json',terminal['clock_terminal_sha256'])
                if (ct['job_pins']!=link['job_pins'] or ct['outcome_head']!=terminal['parent_head']
                        or ct['outcome_anchor_sha256']!=terminal['parent_anchor_sha256']):
                    raise ValueError('historical obligation clock/outcome differs')
                bridge.inspect(clock,hour,packet,self._spec,self._limits,binding_pin=header['clock_binding_sha256'],
                    intent_pin=ct['intent_sha256'],terminal_pin=terminal['clock_terminal_sha256'])
                return super()._child(hour,packet,intent_head,lineage,expected_head=expected_head,create=create)

            def _after(self,packet,result):
                nonlocal retained_bytes
                if type(result) is not current.parent.ChildInspection or result.status!='accepted':
                    raise ValueError('accepted timed child required')
                count=len(binding.replay.native.model_api.stage_order(packet.inputs))
                if (result.stored_reports!=count or type(result.projection) is not current.parent.Projection
                        or result.projection.projection_identity!=io.digest(io.encode([current.parent.CHILD_SCHEMA,io.digest(result.projection.payload)]))):
                    raise ValueError('complete normal projection differs')
                after=super()._after(packet,result)
                hour=packet.relative_hour
                if type(hour) is not int or hour!=len(seen_hours) or not 0<=hour<completed_hours:
                    raise ValueError('one captured frame per chronological N hour required')
                seen_hours.append(hour)
                if hour in selected_hours:
                    value=dict(packet=packet,result=result,after=after,count=count)
                    retained_bytes+=retained_size(value)
                    if retained_bytes>MAX_RETAINED_BYTES:raise ValueError('batch retained data byte cap exceeded')
                    captured[hour]=value

                return after

        terminal=records[completed_hours-1][0]
        with history.replay.guard.solver_calls_forbidden():
            first_request=read(root/'job_000_non_authoritative'/'request.json',records[0][1]['job_pins']['request.json'])
            stages=first_request['input_receipt']['stage_slots']
            if type(stages) is not int or not 1<=stages<=232:raise ValueError('bounded stage count required')
            _observe_prefix(identities,root,completed_hours,stages)
            reader=Reader(declaration,completed_hours=completed_hours,expected_parent_identity=header['parent_identity'],
                expected_parent_head=terminal['parent_head'],expected_anchor_record=terminal['parent_anchor_sha256'])
            state=reader.inspect()
            if (state.completed_hours!=completed_hours or state.status!=('complete' if completed_hours==192 else 'ready')
                    or state.head!=terminal['parent_head'] or seen_hours!=list(range(completed_hours))
                    or set(captured)!=set(selected_hours)):
                raise ValueError('historical accepted controller prefix differs')
            base.entry.unchanged(views);inventory()
            _observe_prefix(identities,root,completed_hours,stages)
            _observe_sources(identities,declaration)
            if implementation_identity()!=own:raise ValueError('historical controller implementation drift')
            proofs={}
            for hour in selected_hours:
                selected=prefix_evidence(evidence,hour)
                proofs[hour]=dict(completed_hours=hour+1,parent_head=records[hour][0]['parent_head'],
                    evidence_identity=io.digest(io.encode(selected)),historical_parent_prefix_verified=True,
                    historical_obligation_prefix_verified=True,historical_job_clock_prefix_verified=True,
                    suffix_chain_verified=False,current_latest_parent_verified=False,current_latest_obligation_verified=False,
                    live_release_authenticated=False,live_handoff_authenticated=False,writer_lock_authenticated=False,
                    persistent_lane_owner_implemented=False,detached_consumer_authenticated=False,
                    common_prefix_publication_verified=False,reference_or_actual_ready=False,
                    replay_contract=SCHEMA,**old.FLAGS)
            completed=True
            return proofs,captured,header
    finally:
        primary=sys.exception()
        errors=[]
        for item in ([reader] if reader is not None else [])+list(reversed(leases)):
            try:item.close()
            except BaseException as error:errors.append(error)
        if not completed:captured.clear()
        if errors:
            if primary is None:raise errors[0]
            try:BaseException.add_note(primary,'batch historical cleanup also failed')
            except BaseException:pass

