"""Exact declared solver-reservation accounting for a verified clock window.

Read-only, zero-native, conditional evidence. Aggregate credit is only a descriptive lower bound;
per-stage excess is a contract candidate, not an acceptance verdict. Complete lifecycle and observer coverage are absent.
"""
from dataclasses import asdict
from fractions import Fraction
from pathlib import Path
import os

from experiments import h1_job_clock_bridge_development_v1 as bridge
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_full_resource_contract_v3 as contract

io, base, worker = bridge.io, bridge.base, bridge.worker
SCHEMA = 'h1_overshoot_accounting_development_v1'
FLAGS = dict(bridge.FLAGS, complete_lifecycle_measured=False,
    legacy_non_solver_charge_verified=False, physical_clock_error_bound_proven=False,actual_solver_time_limit_authenticated=False)


def implementation_identity():
    return io.digest(io.encode([SCHEMA,bridge.implementation_identity(),contract.implementation_identity(),
        io.digest(Path(__file__).read_bytes()),io.digest(Path(contract.__file__).read_bytes())]))


def ratio(value):
    return [value.numerator,value.denominator]


def account(*,wall_ns,actual_ns,reserved_ns):
    """Integer/Fraction arithmetic; callers must establish all provenance."""
    worker._integer(wall_ns)
    if (type(actual_ns) is not tuple or type(reserved_ns) is not tuple
            or not 2 <= len(actual_ns) <= 232 or len(actual_ns) != len(reserved_ns)):
        raise ValueError('complete bounded stage vectors required')
    for actual,reserved in zip(actual_ns,reserved_ns):
        worker._integer(actual)
        if (type(reserved) is not Fraction or reserved <= 0
                or max(reserved.numerator.bit_length(),reserved.denominator.bit_length()) > 2048):
            raise ValueError('bounded exact positive reservation required')
    total = sum(actual_ns)
    if total > wall_ns: raise ValueError('native durations exceed observed window')
    reserved = sum(reserved_ns,Fraction(0))
    excess = tuple(max(Fraction(0),Fraction(a)-r) for a,r in zip(actual_ns,reserved_ns))
    unused = tuple(max(Fraction(0),r-Fraction(a)) for a,r in zip(actual_ns,reserved_ns))
    outside = wall_ns-total
    aggregate = max(Fraction(0),total-reserved)
    conservative = sum(excess,Fraction(0))
    return dict(window_wall_ns=wall_ns,native_total_ns=total,outside_native_ns=outside,
        reserved_total_ns_ratio=ratio(reserved),aggregate_overshoot_descriptive_lower_bound_ns_ratio=ratio(aggregate),
        aggregate_charge_descriptive_lower_bound_ns_ratio=ratio(outside+aggregate),
        stagewise_overshoot_ns_ratio=ratio(conservative),
        stagewise_charge_contract_candidate_ns_ratio=ratio(outside+conservative),
        unused_stage_reservation_ns_ratio=ratio(sum(unused,Fraction(0))),
        stages=[dict(index=i,actual_ns=a,reserved_ns_ratio=ratio(r),
            overshoot_ns_ratio=ratio(e),unused_ns_ratio=ratio(u))
            for i,(a,r,e,u) in enumerate(zip(actual_ns,reserved_ns,excess,unused))])


def _clock_root_view(root):
    names=set()
    with os.scandir(root) as entries:
        for entry in entries:
            names.add(entry.name)
            if len(names)>194: raise ValueError('clock root entry cap')
    if not {'binding.json','execution.lock'} <= names or not names <= {'binding.json','execution.lock',*(f'{i:03d}' for i in range(192))}:
        raise ValueError('clock root topology differs')
    return worker.hour._directory(root,names),frozenset(names)


def inspect_window(clock_root,index,packet,specification,limits,*,binding_pin,intent_pin,terminal_pin):
    """Bind the same stage vector/spec/options to fresh science and clock pins.

The configured TimeLimit is a declared reservation, not a hard solver bound.
The bridge's persisted window excludes its confirmation/return tail.
"""
    if type(index) is not int or not 0 <= index < 192: raise ValueError('bounded exact hour required')
    own = implementation_identity()
    request = worker.hour.request_key(packet,specification,limits)
    spec_raw = io.encode(asdict(specification))
    root = Path(clock_root).absolute()
    order = worker.hour.prior.native.model_api.stage_order(packet.inputs)
    count,seconds = contract.validate_work(contract.H1NormalWork('observed_clock_window',1,order,specification))
    reserved = seconds*10**9
    directory = root/f'{index:03d}'
    directory_identity = worker.hour._directory(directory,{'intent.json','job.json','terminal.json'})
    clock_root_view = _clock_root_view(root)
    terminal,tv = base.entry.read(directory/'terminal.json',terminal_pin)
    paths = {root/'binding.json':binding_pin,directory/'intent.json':intent_pin,
        directory/'job.json':terminal['job_record_sha256'],directory/'terminal.json':terminal_pin}
    clock_views = {p:(bridge.CAP,base.entry.read(p,h)[1]) for p,h in paths.items()}
    job = root.parent/f'job_{index:03d}_non_authoritative'
    before = base.parent.job_view(job,count)
    checked = bridge.inspect(root,index,packet,specification,limits,
        binding_pin=binding_pin,intent_pin=intent_pin,terminal_pin=terminal_pin)
    hour = job/'worker_non_authoritative/hour_non_authoritative'
    intervals,views = worker._intervals(hour,count)
    expected_options = worker.hour.stage.capture.old.audit.solver_options(specification)
    if (specification.name != 'gurobi' or 'TimeLimit' not in expected_options
            or Fraction(expected_options['TimeLimit']) != seconds):
        raise ValueError('same declared native TimeLimit reservation required')
    stage_pins=[]
    for i in range(count):
        path = hour/'stages'/f'{i:03d}'/'specification.json'
        doc,view = worker._read(path)
        binding,bv = worker._read(path.parent/'binding.json')
        views[path.parent/'binding.json']=bv
        if (set(doc) != {'specification','options','binding_sha256'}
                or doc['binding_sha256'] != io.digest(bv[0])
                or not io.same(doc['specification'],asdict(specification))
                or not io.same(doc['options'],expected_options)):
            raise ValueError('stage reservation declaration differs')
        views[path]=view;stage_pins.append(io.digest(view[0]))
    actual=tuple(row['native_end_ns']-row['native_start_ns'] for row in intervals)
    arithmetic=account(wall_ns=checked['transaction_wall_ns'],actual_ns=actual,reserved_ns=(reserved,)*count)
    if arithmetic['native_total_ns'] != checked['native_total_ns'] or arithmetic['outside_native_ns'] != checked['observed_non_native_ns']:
        raise ValueError('clock interval vector differs')
    worker._unchanged(views);base.entry.unchanged(clock_views)
    if (base.parent.job_view(job,count) != before or implementation_identity() != own
            or worker.hour.request_key(packet,specification,limits) != request
            or io.encode(asdict(specification)) != spec_raw
            or not io.same(worker.hour.prior.native.model_api.stage_order(packet.inputs),order)
            or worker.hour._directory(directory,{'intent.json','job.json','terminal.json'}) != directory_identity
            or _clock_root_view(root) != clock_root_view):
        raise ValueError('accounting evidence changed')
    result=dict(schema=SCHEMA,implementation=own,clock_pins=dict(binding=binding_pin,intent=intent_pin,terminal=terminal_pin),
        hour_request_sha256=request,relative_hour=index,stage_order=[list(row) for row in order],stage_order_sha256=io.digest(io.encode(order)),
        specification_sha256=io.digest(spec_raw),
        stage_specification_sha256=stage_pins,interval_vector_sha256=io.digest(io.encode(intervals)),
        declared_seconds_per_stage_ratio=ratio(seconds),arithmetic=arithmetic,
        scope='single persisted transaction window',reservation_role='declared TimeLimit, not hard runtime enforcement',
        acceptance_policy_selected=False,threshold_comparison_performed=False,live_authority_reconstructed=False,**FLAGS)
    if len(io.encode(result)) > bridge.CAP: raise ValueError('accounting report content cap')
    return result
