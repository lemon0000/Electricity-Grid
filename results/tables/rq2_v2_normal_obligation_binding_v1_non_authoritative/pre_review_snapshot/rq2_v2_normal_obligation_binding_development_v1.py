"""Join one enrollment obligation to a fresh existing pending N request.

Read-only, zero solver. This is a controller/audit binding, not a launch request,
solver task inventory, reusable result, policy input or durable live handoff.
"""
from copy import deepcopy
from dataclasses import asdict
from fractions import Fraction
import json
from pathlib import Path

from experiments import rq2_v2_obligation_manifest_development_v1 as manifest
from experiments import h1_timed_job_snapshot_development_v1 as snapshot
from src.rq2_joint_deliverability_boundary_v1 import normal_task_process as process

io, replay, source_binding = snapshot.io,snapshot.old.replay,snapshot.old.binding
ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'rq2_v2_normal_obligation_binding_development_v1'
MANIFEST = 'results/tables/rq2_v2_obligation_manifest_v1_non_authoritative/obligation_manifest_v2_final.json'
MANIFEST_PIN = 'befcfab8180a0124f15ad7652b085514c7aec6278e2b9d967e9885fc5a65fdd7'
BASELINE = 'results/tables/rq2_v2_obligation_manifest_v1_non_authoritative/development_checks.json'
BASELINE_PIN = 'fadec65f40904ed4a7a2ec484767a3bd6d14b6e4a5e9ab759d47fd798a72f246'
SOURCE_CONFIG_PIN = '0cca33dbfbd934881be3c4e375c76eb668c2ec41ff9bbc7392c2eb3947de18a5'
CAP = 128 * 1024
FLAGS = dict(formal_result=False,formal_execution_ready=False,resource_admission=False,
    native_execution_authorized=False,solver_reuse_verified=False,complete_executable_task_inventory=False,
    live_parent_state_at_use_verified=False,writer_lease_authenticated=False,
    bookkeeping_labels_are_policy_inputs=False,training_UB_proven=False)


def open_manifest():
    return manifest.inspect(ROOT/MANIFEST,expected_sha256=MANIFEST_PIN)


def precheck(resolver,declaration,*,family,ordinal,relative_hour):
    """Static join checks for use BEFORE an enclosing controller writes intent."""
    if type(resolver) is not manifest.Resolver or resolver.identity != MANIFEST_PIN:
        raise ValueError('exact fresh-inspected manifest snapshot required')
    if family != 'training_ub' or type(family) is not str:
        raise ValueError('only unresolved training UB enrollment supported')
    if type(relative_hour) is not int or not 0 <= relative_hour < 168:
        raise ValueError('explicit enrollment hour in [0,168) required')
    node = resolver.resolve(family,ordinal)
    payload = node['record']['payload']
    if (payload['disposition'] != 'unresolved_no_certificate'
            or payload['missing_dependency'] != 'named_causal_policy_full_training_witness_missing'):
        raise ValueError('obligation already has cell proof or incompatible scope')
    if type(declaration) is not dict: raise ValueError('exact parent declaration required')
    origin = source_binding.H1SourceDeclaration(**declaration['origin'])
    point = payload['coordinate']
    expected = source_binding.H1SourceDeclaration('training',point['power']['source_start'],
        point['workload']['source_start'],point['power']['outage_seed'],SOURCE_CONFIG_PIN)
    if origin != expected or point['workload']['outage_seed'] is not None:
        raise ValueError('parent origin does not match complete catalog pair')
    if type(declaration['hours']) is not int or not relative_hour < declaration['hours'] <= 192:
        raise ValueError('hour outside declared parent horizon')
    for kind in ('power','workload'):
        window = point[kind]
        if (window['split'] != 'training' or window['enrollment_end_inclusive'] != window['source_start']+167):
            raise ValueError('complete pinned training enrollment required')
    return node


def prevalidate_enrollment(resolver,declaration,*,family,ordinal,relative_hour):
    """Whole E prevalidation; no future rows or error positions enter N inputs."""
    node = precheck(resolver,declaration,family=family,ordinal=ordinal,relative_hour=relative_hour)
    point = node['record']['payload']['coordinate']
    windows = {}
    for kind in ('power','workload'):
        coordinate = point[kind]
        value = source_binding.windows.load_source_window(kind,'training',coordinate['source_start'],168,
            outage_seed=coordinate['outage_seed'],config_path=declaration['config_path'],
            expected_config_sha256=SOURCE_CONFIG_PIN)
        if value['chain']['chain_id'] != coordinate['chain_id'] or len(value['rows']) != 168:
            raise ValueError('complete enrollment chain differs from catalog')
        windows[kind] = value
    if any(not 0 <= Fraction(row['cfe_call_fraction']) <= 1 for row in windows['power']['rows']):
        raise ValueError('whole enrollment CFE source domain unresolved')
    projections = [source_binding.h1.workload_projection.project_workload_power(row['workload_fraction'],
        '250',decimal_places=12) for row in windows['workload']['rows']]
    if any(v['status'] != 'projected' or v['exact_interface_identity_verified'] is not True for v in projections):
        raise ValueError('whole enrollment workload mapping unresolved')
    return dict(phase='enrollment',hours=168,source_config_sha256=SOURCE_CONFIG_PIN,
        windows={kind:dict(window_identity=value['window_identity'],raw_start=value['raw_start'],
            chain_id=value['chain']['chain_id'],package_manifest_sha256=value['package_manifest_sha256'])
            for kind,value in windows.items()},
        workload_projection_sha256=io.digest(io.encode(projections)),
        whole_enrollment_mapping_checked=True,policy_visible=False)


def _views():
    views = {}
    def read(name,pin=None):
        path = ROOT/name
        raw,stamp = io.read_stable(path,manifest.exclusion.INPUT_CAP)
        if pin is not None and io.digest(raw) != pin: raise ValueError('binding dependency pin differs')
        views[path] = (raw,stamp)
        return raw
    baseline = json.loads(read(BASELINE,BASELINE_PIN))
    outer_name = manifest.exclusion.OUTER
    outer_pin = manifest.exclusion.PINS[outer_name]
    outer = json.loads(read(outer_name,outer_pin))
    for name,pin in {**outer['members'],**baseline['files_sha256']}.items(): read(name,pin)
    read(MANIFEST,MANIFEST_PIN)
    read(__file__)
    return views


def bind(resolver,declaration,*,family,ordinal,relative_hour,expected_parent_identity,
         expected_anchor_record,pending_arguments,expected_pending_receipt_sha256,job_budget):
    """Fresh pinned pending request join. Never writes, launches or commits.

    The caller must still revalidate under its live guard/lease at actual use.
    The returned JSON cannot recreate a PendingWorkerInput or executable carry.
    """
    original = io.encode(dict(declaration=declaration,pending_arguments=pending_arguments))
    declaration,pending_arguments = deepcopy((declaration,pending_arguments))
    node = precheck(resolver,declaration,family=family,ordinal=ordinal,relative_hour=relative_hour)
    for pin in (expected_parent_identity,expected_anchor_record,expected_pending_receipt_sha256): io.pin(pin)
    if io.digest(io.encode(declaration)) != expected_parent_identity: raise ValueError('parent declaration pin differs')
    if type(job_budget) is not process.TaskProcessBudget: raise ValueError('exact proposed Job budget required')
    job_budget.__post_init__()
    budget = asdict(job_budget)
    with replay.guard.solver_calls_forbidden():
        views = _views()
        enrollment = prevalidate_enrollment(resolver,declaration,family=family,ordinal=ordinal,relative_hour=relative_hour)
        owner = snapshot.open_snapshot(declaration,expected_parent_identity=expected_parent_identity,
            expected_anchor_record=expected_anchor_record)
        try:
            item = owner.pending_input(**pending_arguments)
            item.validate(expected_receipt_sha256=expected_pending_receipt_sha256)
            packet = item.packet
            if packet.relative_hour != relative_hour: raise ValueError('pending relative hour differs')
            receipt = json.loads(item.receipt)
            coordinate = node['record']['payload']['coordinate']
            current = source_binding.H1SourceDeclaration('training',coordinate['power']['source_start']+relative_hour,
                coordinate['workload']['source_start']+relative_hour,coordinate['power']['outage_seed'],SOURCE_CONFIG_PIN)
            observed = source_binding.load_pinned_current(current,declaration['upstream_root'],config_path=declaration['config_path'])
            if observed.identity != receipt['source_lineage_identity']:
                raise ValueError('current raw source clock/lineage differs')
            key = replay.request_key(packet,item.specification,item.limits)
            if key != receipt['request_key']: raise ValueError('existing normal request key differs')
            result = dict(schema=SCHEMA,status='DRAFT_NONAUTHORITATIVE',
                role='normal_environment_prerequisite_for_B6_planning' if coordinate['arm']=='joint-B6'
                    else 'normal_environment_prerequisite_for_training_UB',
                manifest_sha256=MANIFEST_PIN,obligation_node=node,
                phase='enrollment',relative_hour=relative_hour,
                raw_source_hours=dict(power=current.power_raw_hour,workload=current.workload_raw_hour),
                display_source_hours=dict(power=current.power_raw_hour+1,workload=current.workload_raw_hour+1),
                model_timestamp=packet.inputs.request.timestamps[0].isoformat(),
                normal_input_identity=packet.input_identity,normal_request_key=key,
                specification=asdict(item.specification),limits=asdict(item.limits),
                source_parent_lineage=dict(parent_declaration=declaration,pending_receipt=receipt,
                    pending_receipt_sha256=item.receipt_sha256),
                enrollment_prevalidation=enrollment,proposed_job_budget=budget,
                proposed_job_budget_sha256=io.digest(io.encode(budget)),
                implementation_sha256=io.digest(views[Path(__file__)][0]),baseline_checks_sha256=BASELINE_PIN,
                runtime_task_id=None,launch_request=None,host_resource_admission=None,solver_calls=0,**FLAGS)
            result['obligation_binding_id'] = io.digest(io.encode(result))
            if len(io.encode(result)) > CAP: raise ValueError('normal binding byte cap exceeded')
            fresh = owner.pending_input(**pending_arguments)
            fresh.validate(expected_receipt_sha256=expected_pending_receipt_sha256)
            if fresh.packet != packet or fresh.receipt != item.receipt:
                raise ValueError('pending input changed during obligation binding')
            owner._check()
            if asdict(job_budget) != budget: raise ValueError('proposed budget changed')
            if io.encode(dict(declaration=declaration,pending_arguments=pending_arguments)) != original:
                raise ValueError('binding declaration changed')
            for path,view in views.items():
                if io.read_stable(path,manifest.exclusion.INPUT_CAP) != view:
                    raise ValueError('binding evidence changed during join')
            return result
        finally: owner.close()


def inspect(path,*,expected_sha256,**arguments):
    raw,stamp = io.read_stable(Path(path),CAP)
    if io.digest(raw) != io.pin(expected_sha256): raise ValueError('external binding pin differs')
    expected = bind(**arguments)
    if io.encode(expected) != raw: raise ValueError('fresh pending obligation binding differs')
    if io.read_stable(Path(path),CAP) != (raw,stamp): raise ValueError('binding file changed')
    return expected
