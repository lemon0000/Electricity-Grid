"""Pinned, zero-solver resource gap audit; no admission, runner or publication."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction
from hashlib import sha256
import json
from itertools import product
from math import prod
from pathlib import Path
import shutil
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
BASE = 'results/tables/rq2_normal_h1_full_job_v3_non_authoritative/'
PINS = {
    'configs/rq2_finite_mechanism_protocol_candidate_v2.DRAFT.yaml':
        '95eb158f0a8e6784d2af401e67164965543c98f42ff02b756c214982601e5430',
    'results/tables/rq2_finite_enrollment_support_v1_non_authoritative/coverage_168_24_verified.json':
        '29ba7f5662c3dee019f183104479d8fa354f726bea0e055ee456b3dd337042c4',
    'configs/rq2_normal_h1_calibration_v3.OUTER.SHA256SUMS.json':
        'e3acc7a6de1c1863ab64a8c1ae67ded9676e01c564a3d4ef2d0be29252f0edcf',
    BASE+'calibration_v3.postrun_inventory.json':
        'e80dacf5c44b39ad71ff29dce980d3e03cee6f4bf9fad6d3be620061e171d596',
    BASE+'calibration_v3.postrun_review.json':
        '51519252f9d570a45625cabf9b2f9e20e5701f530608b9e599d4ccafa0144ff4',
}


def positive_int(value, name, *, zero=False):
    if type(value) is not int or value < (0 if zero else 1):
        raise ValueError('exact bounded integer required: '+name)
    return value


def grid_count(grid, denominator, *, include_zero):
    denominator = positive_int(denominator, 'denominator')
    first = positive_int(grid['first'], 'first', zero=include_zero)
    last = positive_int(grid['last'], 'last')
    step = positive_int(grid['step'], 'step')
    if first > last or last > denominator or (last-first) % step:
        raise ValueError('exact closed declared grid required')
    if include_zero and (first != 0 or last != denominator):
        raise ValueError('capacity grid must retain zero and one endpoints')
    return (last-first)//step+1


def protocol_counts(protocol, coverage):
    if (protocol.get('scientific_parameters_approved') is not True
            or protocol.get('primary_object') != 'full_training_support_causal_minimum_bidirectional_capacity'
            or protocol.get('physical_capacity_rule') != 'q_plus_r_le_D'
            or protocol['design'].get('full_support_retained') is not True):
        raise ValueError('approved full-support bidirectional protocol required')
    window = protocol['window']
    for key, source_key in [('enrollment_hours', 'enrollment_hours'),
                            ('maximum_followup_hours', 'followup_hours'),
                            ('stride_hours', 'stride_hours')]:
        if positive_int(window[key], key) != positive_int(coverage[source_key], source_key):
            raise ValueError('protocol/source window mismatch')
    design = protocol['design']
    theta = 1
    for values in design['primary_factorial'].values():
        decoded = [Fraction(v) for v in values]
        if not decoded or len(set(decoded)) != len(decoded):
            raise ValueError('distinct nonempty factorial coordinates required')
        theta *= len(decoded)
    for name, values in design['oat_non_anchor'].items():
        decoded = [Fraction(v) for v in values]
        if (not decoded or len(set(decoded)) != len(decoded)
                or Fraction(protocol['business_anchor'][name]) in decoded):
            raise ValueError('distinct non-anchor OAT coordinates required')
        theta += len(decoded)
    if design.get('oat_uses_all_alpha_levels') is not True:
        raise ValueError('explicit common alpha grid required')
    alpha = grid_count(design['alpha_numerators'], design['alpha_denominator'], include_zero=False)
    cells = theta*alpha
    if (theta != positive_int(design['expected_theta_count'], 'theta count')
            or cells != positive_int(design['expected_cell_count'], 'cell count')):
        raise ValueError('derived design count mismatch')
    capacity = protocol['capacity_evidence']
    probes = grid_count(capacity['capacity_probe_numerators'],
                        capacity['capacity_probe_denominator'], include_zero=True)
    identities = set()
    counts = Counter()
    complete = Counter()
    for row in coverage['windows']:
        if row['split'] not in ('training', 'holdout') or row['kind'] not in ('power', 'workload'):
            raise ValueError('explicit source split and marginal required')
        key = row['kind'], row['split'], row['chain_id'], row['source_start']
        if key in identities:
            raise ValueError('duplicate source window')
        identities.add(key)
        counts[row['split'], row['kind']] += 1
        available = positive_int(row['available_followup_hours'], 'available tail', zero=True)
        missing = positive_int(row['missing_followup_hours'], 'missing tail', zero=True)
        if available+missing != window['maximum_followup_hours']:
            raise ValueError('source tail accounting mismatch')
        if row['followup_source_complete'] is not (missing == 0):
            raise ValueError('source tail completeness mismatch')
        if missing == 0:
            complete[row['split'], row['kind']] += 1
    splits = {}
    for split in ('training', 'holdout'):
        power, workload = counts[split, 'power'], counts[split, 'workload']
        pairs = power*workload
        full = complete[split, 'power']*complete[split, 'workload']
        summary = coverage['summary'][split]
        if (pairs != positive_int(design[split+'_pairs_per_cell'], split+' pairs')
                or pairs != summary['all_enrollment_pairs_retained']
                or full != summary['both_followup_sources_complete']):
            raise ValueError('source support count mismatch')
        splits[split] = dict(power_windows=power, workload_windows=workload,
            pairs_per_cell=pairs, cell_pair_identities=cells*pairs,
            four_arm_object_identities=4*cells*pairs,
            pairs_with_missing_followup_retained=pairs-full,
            missing_tail_is_automatic_service_failure=False)
    if splits['training']['cell_pair_identities'] != design['expected_training_cell_pair_count']:
        raise ValueError('training identity count mismatch')
    return dict(theta_count=theta, alpha_count=alpha, cell_count=cells,
        capacity_probe_count=probes, maximum_hours_per_pair=window['enrollment_hours']+window['maximum_followup_hours'],
        splits=splits, identity_count_is_required_solver_call_count=False)


def normal_scenarios(counts, *, stages, content_per_pair, hourly_task_seconds):
    """Conditional normal-only slot arithmetic, never an executable task list."""
    for name, value in [('stages', stages), ('content', content_per_pair), ('hour wall', hourly_task_seconds)]:
        positive_int(value, name)
    hours = counts['maximum_hours_per_pair']
    calls = hours*stages
    rows = [dict(name='one_pair_maximum_normal_prefix', pair_copies=1)]
    for split, item in counts['splits'].items():
        rows.extend([
            dict(name=split+'_one_common_prefix_per_pair_if_reuse_verified',
                 pair_copies=item['pairs_per_cell'], reuse_verification_required=True),
            dict(name=split+'_repeat_normal_for_every_cell_pair_one_capacity_probe',
                 pair_copies=item['cell_pair_identities'], reuse_verification_required=False),
        ])
    for row in rows:
        copies = row['pair_copies']
        row.update(normal_hour_slots=copies*hours, normal_solver_slots=copies*calls,
            normal_content_cap_bytes=copies*content_per_pair,
            independent_hour_job_wall_allowance_seconds=copies*hours*hourly_task_seconds,
            actual_execution_count=None, predicted_elapsed_seconds=None,
            admitted=False)
    return dict(scope='conditional normal-only declaration scenarios; excludes reference, actual, capacity proofs and parent overhead',
        source_missing_and_on_demand_followup_can_reduce_actual_visits=True,
        reductions_used_in_slot_arithmetic=False, rows=rows,
        complete_study_solver_calls=None, complete_study_wall_seconds=None,
        complete_study_disk_bytes=None, complete_study_task_manifest=None)


def obligation_catalog(protocol, coverage, counts):
    """Lossless factorized identities; these are obligations, not solver jobs."""
    design = protocol['design']
    anchor = protocol['business_anchor']
    names = tuple(sorted(design['primary_factorial']))
    theta = []
    for values in product(*(design['primary_factorial'][name] for name in names)):
        theta.append(dict(anchor, **dict(zip(names, values))))
    for name in sorted(design['oat_non_anchor']):
        for value in design['oat_non_anchor'][name]:
            theta.append(dict(anchor, **{name:value}))
    if len(theta) != counts['theta_count']:
        raise ValueError('complete theta identity set required')
    def values(grid, denominator):
        return [str(Fraction(n, denominator)) for n in range(grid['first'],grid['last']+1,grid['step'])]
    def windows(split, kind):
        return sorted((row for row in coverage['windows'] if row['split']==split and row['kind']==kind),
                      key=lambda row:(row['chain_id'],row['source_start']))
    arms = ['network-only','CFE-only','joint-correct','joint-B6']
    common = dict(theta=theta,alpha=values(design['alpha_numerators'],design['alpha_denominator']))
    training_lb = dict(common,power=windows('training','power'),workload=windows('training','workload'),arm=arms)
    training_ub = dict(training_lb,capacity=values(protocol['capacity_evidence']['capacity_probe_numerators'],
            protocol['capacity_evidence']['capacity_probe_denominator']))
    training_b6_actual = dict(training_lb,arm=['joint-B6'])
    holdout = dict(common,power=windows('holdout','power'),workload=windows('holdout','workload'),arm=arms)
    families = dict(training_lb=training_lb,training_ub=training_ub,
                    training_b6_actual=training_b6_actual,holdout=holdout)
    return dict(schema='factorized_capacity_obligation_catalog_v1',
        axis_order={name:list(axes) for name,axes in families.items()},axes=families,
        identity_counts={name:prod(len(v) for v in axes.values()) for name,axes in families.items()},
        eligible_execution_counts={name:None for name in families},
        default_status='not_scheduled_no_certificate',
        training_scope='offline LB contributions without D probes; UB-only grid-point witnesses; not required executions or a capacity-search algorithm',
        training_b6_actual_scope='conditional separate shared-policy execution at a frozen training planning UB; no substitute exogenous capacity or D-grid multiplication',
        holdout_scope='conditional evaluation at a training-frozen feasible UB and named policy; no capacity probe multiplication',
        proof_semantics=dict(LB='same-contract all-causal-policy lower-bound proof; resource task unknown',
            UB_N_C_J='complete training causal policy and actual-grid witnesses',
            UB_B6='complete separate causal planning-track witnesses; not actual shared execution',
            B6_actual='separate shared execution evaluation; never a planning UB certificate'),
        bookkeeping_labels_are_policy_inputs=False,causal_request_keys_materialized=False,
        realized_solver_task_ids=None,analytic_exclusion_proofs=[],verified_reuse_edges=[],
        omitted_identities=0,resource_discounts_applied=False,
        dependency_families=[
            dict(parent='current allowed source and prior N carry',child='N projection',causal_key=None),
            dict(parent='N projection, revealed outage and prior Rref carry',child='Rref projection',causal_key=None),
            dict(parent='Rref projection, baseline preallocation and contract',child='business action/debt transition',causal_key=None),
            dict(parent='business action, current allowed source and prior arm A carry',child='arm A projection',causal_key=None)],
        missing_reuse_proof_means_no_discount=True,
        complete_executable_task_inventory=False)


def obligation_at(catalog, family, ordinal):
    """Random access to every identity without creating billions of records."""
    positive_int(ordinal,'ordinal',zero=True)
    if family not in catalog['axes'] or ordinal >= catalog['identity_counts'][family]:
        raise ValueError('ordinal outside explicit family identity space')
    axes = catalog['axes'][family]
    remainder = ordinal
    coordinate = {}
    for name in reversed(catalog['axis_order'][family]):
        remainder,index = divmod(remainder,len(axes[name]))
        coordinate[name] = axes[name][index]
    if remainder:
        raise ValueError('catalog identity count disagrees with axes')
    return dict(family=family,split='holdout' if family=='holdout' else 'training',ordinal=ordinal,coordinate=coordinate,
        status=catalog['default_status'],causal_request_key=None,solver_task_id=None,
        frozen_training_ub=None,numerical_certificate=None)


def pinned_inputs():
    values = {}
    for name, expected in PINS.items():
        raw = (ROOT/name).read_bytes()
        if sha256(raw).hexdigest() != expected:
            raise ValueError('pinned evidence drift: '+name)
        values[name] = yaml.safe_load(raw) if name.endswith('.yaml') else json.loads(raw)
    return values


def audit():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from src.rq2_joint_deliverability_boundary_v1 import normal_h1_calibration_gate_v3 as gate
    from src.rq2_joint_deliverability_boundary_v1 import normal_h1_full_resource_contract_v3 as resources
    evidence = pinned_inputs()
    outer_name = 'configs/rq2_normal_h1_calibration_v3.OUTER.SHA256SUMS.json'
    _, request = gate.verify_package(ROOT/outer_name, PINS[outer_name])
    protocol = evidence['configs/rq2_finite_mechanism_protocol_candidate_v2.DRAFT.yaml']
    coverage = evidence['results/tables/rq2_finite_enrollment_support_v1_non_authoritative/coverage_168_24_verified.json']
    counts = protocol_counts(protocol, coverage)
    catalog = obligation_catalog(protocol,coverage,counts)
    inventory = evidence[BASE+'calibration_v3.postrun_inventory.json']
    run_root = Path(inventory['root'])
    if run_root != Path(request['root']) or not run_root.is_relative_to(ROOT):
        raise ValueError('pinned calibration root required')
    actual = {p.relative_to(run_root).as_posix(): dict(bytes=p.stat().st_size,
              sha256=sha256(p.read_bytes()).hexdigest()) for p in run_root.rglob('*') if p.is_file()}
    if actual != inventory['members']:
        raise ValueError('calibration inventory drift')
    review = evidence[BASE+'calibration_v3.postrun_review.json']
    if review['assessment'] != 'SUFFICIENT_NO_BLOCKING_FINDING' or review['open_findings']:
        raise ValueError('completed independently audited calibration required')
    order = tuple(tuple(x) for x in request['work']['stage_order'])
    stages = resources.validate_stage_order(order)
    hours = counts['maximum_hours_per_pair']
    content = resources.content_inventory(stages, hours)
    scenarios = normal_scenarios(counts, stages=stages,
        content_per_pair=content['total_content_limit_bytes'],
        hourly_task_seconds=request['resource']['envelope']['max_wall_seconds'])
    disk = shutil.disk_usage(ROOT)
    result = dict(schema='h1_resource_readiness_gap_audit_v1',status='NON_AUTHORITATIVE_RESOURCE_GAP_AUDIT',
        evidence_sha256=PINS, script_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        approved_design=counts,obligation_catalog=catalog,
        catalog_boundary_examples={family:[obligation_at(catalog,family,0),
            obligation_at(catalog,family,catalog['identity_counts'][family]-1)] for family in catalog['axes']},
        normal_stage_count=stages, normal_maximum_prefix_content=content,
        normal_only_scenarios=scenarios,
        calibration=dict(scope='one training origin, one hour, one native attempt',
            job_wall_seconds=review['job_elapsed_seconds'],
            job_peak_commit_bytes=review['job_peak_total_commit_bytes'],
            logical_file_bytes=inventory['bytes'], native_calls=review['native_reports'],
            independently_measured_non_solver_seconds=None,
            declared_non_solver_seconds=request['resource']['envelope']['non_solver_seconds'],
            non_solver_allowance_sufficient=None, single_hour_success_generalizes=False),
        disk_snapshot=dict(observed_utc=datetime.now(timezone.utc).isoformat(),
            workspace=str(ROOT),total_bytes=disk.total,free_bytes=disk.free,
            one_pair_content_cap_exceeds_current_free=content['total_content_limit_bytes']>disk.free,
            excess_content_cap_bytes=max(0,content['total_content_limit_bytes']-disk.free),
            comparison_includes_overhead_scratch_reserve=False,physical_reservation=False,
            admission=False,content_cap_is_minimum_storage_requirement=False),
        unresolved_components=['separate measured native capture and non-solver timing',
            'versioned full-stage multi-hour parent and cumulative retained storage bounds',
            'validated common causal-prefix reuse and complete source/task manifest',
            'common Rref and per-arm A publication and measured resource inventory',
            'same-contract full-support capacity LB/UB proof/search workload',
            'host/volume admission and final sealed execution package'],
        solver_calls=0,execution_authorized=False,whole_task_resources_verified=False,
        formal_execution_ready=False,formal_result=False)
    pinned_inputs()
    gate.verify_package(ROOT/outer_name, PINS[outer_name])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or not output.parent.name.endswith('_non_authoritative'):
        raise ValueError('new explicitly non-authoritative output required')
    value = audit()
    output.parent.mkdir(parents=True,exist_ok=True)
    raw = json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
    with output.open('xb') as stream:
        stream.write(raw)
    if output.read_bytes()!=raw:
        raise ValueError('audit readback drift')
    print(json.dumps(dict(path=str(output),sha256=sha256(raw).hexdigest(),solver_calls=0)))


if __name__=='__main__':
    main()
