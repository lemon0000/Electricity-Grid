"""Zero-solver necessary-condition check of the declared finite-window candidate."""
import csv
from fractions import Fraction as Q
from hashlib import sha256
import gzip
import json
from pathlib import Path
import argparse

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = 'configs/rq2_continuous_science_candidate_v1.DRAFT.yaml'
CANDIDATE_SHA = '2a0e7686b9f92355dc421531c2150ecab354a8106abea54c2d2c5d25259c9051'
COVERAGE = 'results/tables/rq2_finite_enrollment_support_v1_non_authoritative/coverage_168_24_verified.json'
COVERAGE_SHA = '29ba7f5662c3dee019f183104479d8fa354f726bea0e055ee456b3dd337042c4'
CELLS = 'results/tables/rq2_continuous_science_candidate_v1_non_authoritative/structure_audit.json'
CELLS_SHA = '6ba0fc07cf551a9fc1d18952849b46e8e8ffb051dca8accb8da41e9b5c4ec884'


def necessary_conflict(alpha, fraction, source_cfe, occupancy):
    alpha, fraction, source_cfe, occupancy = map(Q, (alpha, fraction, source_cfe, occupancy))
    if not (0 < alpha <= 1 and 0 <= fraction <= 1 and 0 <= source_cfe <= 1 and occupancy >= 0):
        raise ValueError('valid normalized source and candidate parameters required')
    request = max(Q(0), (alpha-(1-source_cfe))/alpha)
    effective = request if request > Q('0.000001') else Q(0)
    available = fraction*occupancy
    return dict(effective_cfe_request=str(effective), workload_baseline=str(occupancy),
        available_flexibility=str(available), request_exceeds_baseline=effective > occupancy,
        request_exceeds_available=effective > available)


def audit():
    pins = {}
    def checked(name, expected):
        data = (ROOT/name).read_bytes()
        digest = sha256(data).hexdigest()
        if digest != expected:
            raise ValueError('source or declaration drift: '+name)
        pins[name] = digest
        return data
    checked(CANDIDATE, CANDIDATE_SHA)
    coverage = json.loads(checked(COVERAGE, COVERAGE_SHA))
    cells = json.loads(checked(CELLS, CELLS_SHA))
    checked(str(Path(__file__).resolve().relative_to(ROOT)).replace('\\', '/'),
        sha256(Path(__file__).read_bytes()).hexdigest())
    if tuple(coverage[k] for k in ('enrollment_hours', 'followup_hours', 'stride_hours')) != (168, 24, 24):
        raise ValueError('conditional coverage declaration differs')
    ids = [c['cell_id'] for c in cells['candidate_cells']]
    if len(ids) != 46 or len(set(ids)) != 46:
        raise ValueError('46 unique candidate cells required')
    if cells['candidate_sha256'] != CANDIDATE_SHA:
        raise ValueError('materialized cells belong to a different candidate')
    windows = []
    blocks = {}
    for kind, block, filename in (
        ('power', 'training_s20260822_0000', 'power_system_blocks.csv.gz'),
        ('workload', 'training_0000', 'workload_blocks.csv.gz')):
        selected = [w for w in coverage['windows'] if w['kind'] == kind and w['split'] == 'training'
            and w['source_start'] == 0 and (kind == 'workload' or w['outage_seed'] == 20260822)]
        if len(selected) != 1 or selected[0]['enrollment_end_inclusive'] != selected[0]['source_start']+167:
            raise ValueError('witness block not covered by declared enrollment support')
        windows.append(selected[0])
        binding = coverage['input_packages'][kind]
        name = binding['package']+'/'+filename
        checked(name, binding['members'][filename])
        with gzip.open(ROOT/name, 'rt', encoding='utf-8', newline='') as stream:
            rows = [r for r in csv.DictReader(stream) if r['block_id'] == block]
        rows.sort(key=lambda r: int(r['hour_offset']))
        if [int(r['hour_offset']) for r in rows] != list(range(24)):
            raise ValueError('complete ordered witness block required')
        if any(r['split'] != 'training' for r in rows):
            raise ValueError('witness split differs')
        source_key = 'source_hour' if kind == 'power' else 'source_relative_hour'
        if any(int(r[source_key]) != selected[0]['source_start']+i for i, r in enumerate(rows)):
            raise ValueError('witness source hour differs from enrollment window')
        if kind == 'power' and any(int(r['outage_seed']) != selected[0]['outage_seed'] for r in rows):
            raise ValueError('witness outage seed differs from enrollment window')
        blocks[kind] = rows
    witnesses = []
    for cell in cells['candidate_cells']:
        for power, workload in zip(blocks['power'], blocks['workload'], strict=True):
            result = necessary_conflict(str(cell['hourly_cfe_target']), str(cell['flexible_fraction']),
                power['cfe_call_fraction'], workload['workload_fraction'])
            if result['request_exceeds_baseline']:
                if not result['request_exceeds_available']:
                    raise ValueError('baseline conflict must also exceed available flexibility')
                witnesses.append(dict(cell_id=cell['cell_id'], alpha=cell['hourly_cfe_target'],
                    flexible_fraction=cell['flexible_fraction'], power_row=power, workload_row=workload,
                    arithmetic=result))
                break
    # Evidence is conditional on the explicit candidate mapping and full-service
    # quantifier, not a solver certificate or a claim about all possible mappings.
    for name, digest in pins.items():
        if sha256((ROOT/name).read_bytes()).hexdigest() != digest:
            raise ValueError('source changed during audit: '+name)
    return dict(schema='finite_candidate_request_necessary_conflicts_v1', status='DRAFT_NONAUTHORITATIVE',
        candidate_cell_count=len(cells['candidate_cells']), cells_with_baseline_conflict=len(witnesses),
        witness_enrollment_windows=windows, witnesses=witnesses, source_sha256=pins,
        arithmetic='exact rational reconstruction of published decimal sources',
        mapping='q_C=max(alpha-(1-source_cfe_call_at_alpha_1),0)/alpha; no workload scaling',
        conditional_scope='all declared training pairs must fulfill complete applicable requests',
        necessary_rule='q_C<=baseline and q_C<=flexible_fraction*baseline',
        capacity_recovery_and_deadline_cannot_remove_instantaneous_conflict=True,
        affected_arms=['CFE-only', 'joint-correct', 'B6 CFE planning track'],
        network_only_conclusion=None, formal_arm_status='not_assigned', solver_calls=0,
        formal_result=False, empirical_joint_distribution_claim=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = audit()
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(report['cells_with_baseline_conflict'], '/', report['candidate_cell_count'], 'conditional conflicts; zero solves')
