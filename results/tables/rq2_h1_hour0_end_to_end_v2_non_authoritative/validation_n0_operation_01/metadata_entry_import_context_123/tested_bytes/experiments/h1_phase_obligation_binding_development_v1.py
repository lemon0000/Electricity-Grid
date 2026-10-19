"""Join either finite-episode phase to a fresh existing pending N request.

Read-only, zero solver. This is a controller/audit binding, not a launch request,
solver task inventory, reusable result, policy input or durable live handoff.
"""
from experiments import rq2_v2_normal_obligation_binding_development_v1 as enrollment_binding
from experiments import h1_finite_followup_assessment_development_v1 as followup

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
SCHEMA = 'h1_phase_obligation_binding_development_v1'
MANIFEST = 'results/tables/rq2_v2_obligation_manifest_v1_non_authoritative/obligation_manifest_v2_final.json'
MANIFEST_PIN = 'befcfab8180a0124f15ad7652b085514c7aec6278e2b9d967e9885fc5a65fdd7'
BASELINE = 'results/tables/rq2_h1_finite_followup_assessment_v1_non_authoritative/development_checks.json'
BASELINE_PIN = '31b4df0cb63e18047b90552f2858bbdf2bdb377200556de41b86055cafd9433f'
SOURCE_CONFIG_PIN = '0cca33dbfbd934881be3c4e375c76eb668c2ec41ff9bbc7392c2eb3947de18a5'
CAP = 128 * 1024
FLAGS = dict(formal_result=False,formal_execution_ready=False,resource_admission=False,
    native_execution_authorized=False,solver_reuse_verified=False,complete_executable_task_inventory=False,
    live_parent_state_at_use_verified=False,writer_lease_authenticated=False,
    bookkeeping_labels_are_policy_inputs=False,training_UB_proven=False,
    followup_need_authenticated=False,paired_owner_guard_authenticated=False,episode_terminal_verified=False)


def open_manifest():
    return manifest.inspect(ROOT/MANIFEST,expected_sha256=MANIFEST_PIN)


def phase(relative_hour):
    if type(relative_hour) is not int or not 0 <= relative_hour < 192:
        raise ValueError('finite episode hour in [0,192) required')
    return 'enrollment' if relative_hour < 168 else 'followup'


def precheck(resolver,declaration,*,family,ordinal,relative_hour):
    """Catalog/phase correspondence only; no permission to read the next row."""
    phase(relative_hour)
    followup.contract_identity()
    # Reuse the exact whole-enrollment contract at its origin, not another node.
    node=enrollment_binding.precheck(resolver,declaration,family=family,ordinal=ordinal,relative_hour=0)
    if type(declaration['hours']) is not int or declaration['hours'] != 192:
        raise ValueError('new 192-hour parent declaration required; old root cannot be extended')
    return node


def prevalidate_enrollment(resolver,declaration,*,family,ordinal,relative_hour):
    precheck(resolver,declaration,family=family,ordinal=ordinal,relative_hour=relative_hour)
    # Still all and only the original 168 rows, including during followup.
    return enrollment_binding.prevalidate_enrollment(resolver,declaration,
        family=family,ordinal=ordinal,relative_hour=0)


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

    Before requesting a next source row, a live owner must replay its paired
    state under the same guard and establish need. This read-only join only
    audits an already pending N request; it cannot authenticate that earlier gate.
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
                phase=phase(relative_hour),relative_hour=relative_hour,
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
