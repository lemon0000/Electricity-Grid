"""Zero-solver scheme-A necessary-condition audit of every retained training pair."""
import argparse
import csv
from fractions import Fraction as Q
import gzip
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments import audit_rq2_finite_request_feasibility_v1 as declared
from src.rq2_joint_deliverability_boundary_v1 import cfe_preallocation as mapping
from src.rq2_joint_deliverability_boundary_v1 import workload_projection as projection


def first_conflict(factors, workloads, fraction):
    """None means no witness on mapped hours, never full service or feasibility."""
    if len(factors) != len(workloads):
        raise ValueError('paired enrollment horizons differ')
    if not 0 <= fraction <= 1:
        raise ValueError('valid flexibility fraction required')
    threshold = mapping.activity_threshold()
    for offset, (factor, w) in enumerate(zip(factors, workloads, strict=True)):
        if w is None:
            continue  # Kept separately as unresolved projection, never zero.
        q = factor*w
        if q > threshold and q > fraction*w:
            return offset
    return None


def audit():
    mapping.activity_threshold()
    pins = {}
    def read(path, expected=None):
        path = Path(path)
        if not path.is_absolute(): path = ROOT/path
        data = path.read_bytes()
        digest = sha256(data).hexdigest()
        if expected is not None and digest != expected:
            raise ValueError('source/declaration drift: '+str(path))
        pins[path.relative_to(ROOT).as_posix()] = digest
        return data
    read(declared.CANDIDATE, declared.CANDIDATE_SHA)
    support = json.loads(read(declared.COVERAGE, declared.COVERAGE_SHA))
    cells = json.loads(read(declared.CELLS, declared.CELLS_SHA))
    if cells['candidate_sha256'] != declared.CANDIDATE_SHA:
        raise ValueError('cell provenance mismatch')
    if (support['enrollment_hours'], support['followup_hours'], support['stride_hours']) != (168,24,24):
        raise ValueError('conditional support changed')
    if len(cells['candidate_cells']) != 46 or len({c['cell_id'] for c in cells['candidate_cells']}) != 46:
        raise ValueError('unique 46-cell inventory required')
    for module in (declared, mapping, projection): read(module.__file__)
    read('src/rq2_joint_deliverability_boundary_v1/source_pair_preallocated.py')
    read('src/rq2_joint_deliverability_boundary_v1/boundary.py')
    read(__file__)
    windows = {k: [w for w in support['windows'] if w['kind'] == k and w['split'] == 'training']
               for k in ('power', 'workload')}
    sources = {}
    for kind, filename, time_key in (('power','power_system_blocks.csv.gz','source_hour'),
                                     ('workload','workload_blocks.csv.gz','source_relative_hour')):
        binding = support['input_packages'][kind]
        path = ROOT/binding['package']/filename
        read(path, binding['members'][filename])
        table = {}
        with gzip.open(path, 'rt', encoding='utf-8', newline='') as stream:
            for row in csv.DictReader(stream):
                if row['split'] != 'training': continue
                key = (int(row['outage_seed']), int(row[time_key])) if kind == 'power' else int(row[time_key])
                if key in table: raise ValueError('duplicate source clock')
                table[key] = row
        sources[kind] = table
    projected = {}
    unresolved = []
    for hour, row in sources['workload'].items():
        item = projection.project_workload_power(row['workload_fraction'], '250', decimal_places=12)
        projected[hour] = Q(str(item['workload_occupancy'])) if item['status'] == 'projected' else None
        if item['status'] != 'projected':
            unresolved.append(dict(source_hour=hour, raw_workload_fraction=row['workload_fraction'], reason=item['reason']))
    E = support['enrollment_hours']
    workload_vectors = []
    unresolved_window_indices = []
    for index, window in enumerate(windows['workload']):
        if window['enrollment_end_inclusive'] != window['source_start']+E-1:
            raise ValueError('enrollment interval mismatch')
        values = tuple(projected[t] for t in range(window['source_start'], window['source_start']+E))
        workload_vectors.append(values)
        if any(w is None for w in values): unresolved_window_indices.append(index)
    source_vectors = []
    for window in windows['power']:
        if window['enrollment_end_inclusive'] != window['source_start']+E-1:
            raise ValueError('enrollment interval mismatch')
        values = tuple(Q(sources['power'][(window['outage_seed'], t)]['cfe_call_fraction'])
            for t in range(window['source_start'], window['source_start']+E))
        if any(not 0 <= c <= 1 for c in values): raise ValueError('invalid source CFE domain')
        source_vectors.append(values)
    grouped = {}
    for cell in cells['candidate_cells']:
        key = (str(cell['hourly_cfe_target']), str(cell['flexible_fraction']))
        grouped.setdefault(key, []).append(cell['cell_id'])
    groups = []
    for (alpha, fraction), ids in sorted(grouped.items()):
        a, f = Q(alpha), Q(fraction)
        if not 0 < a <= 1: raise ValueError('invalid target')
        matrix = []
        for source in source_vectors:
            factors = tuple(max(Q(0), 1-(1-c)/a) for c in source)
            matrix.append([first_conflict(factors, workload, f) for workload in workload_vectors])
        count = sum(x is not None for row in matrix for x in row)
        groups.append(dict(target=alpha, flexible_fraction=fraction, cell_ids=ids,
            first_conflict_offsets=matrix, pairs_with_witness=count,
            pairs_without_witness=len(source_vectors)*len(workload_vectors)-count))
    retained = len(windows['power'])*len(windows['workload'])
    if retained != support['summary']['training']['all_enrollment_pairs_retained']:
        raise ValueError('training support was changed')
    for path, digest in pins.items():
        if sha256((ROOT/path).read_bytes()).hexdigest() != digest:
            raise ValueError('source changed during audit')
    return dict(schema='preallocated_cfe_training_necessary_conditions_v1', status='DRAFT_NONAUTHORITATIVE',
        mapping_rule=mapping.RULE, split='training', source_sha256=pins,
        enrollment_hours=E, followup_hours=24, stride_hours=24, normalized_unit_mw='250', decimal_places=12,
        scientific_parameters_registered=False, windows=windows, retained_pairs_per_cell=retained,
        original_training_coverage_summary=support['summary']['training'], groups=groups,
        unresolved_workload_source_rows=unresolved, unresolved_workload_enrollment_window_indices=unresolved_window_indices,
        matrix_axes=['power_window_index','workload_window_index'], matrix_value='first mapped CFE flexibility conflict offset or null',
        null_is_feasible=False, source_unresolved_is_failure=False, formal_result=False,
        capacity_certificate=False, solver_calls=0, registered_joint_coupling=False,
        affected_planning_arms=['CFE-only','joint-correct','B6 CFE track'], network_only_conclusion=None,
        scope='all conditional training pairs; necessary CFE condition on enrollment hours only; first witness search',
        omitted_service_checks=['grid','recovery trajectory','deadlines','event/energy budgets','causal policy','followup service'],
        holdout_evaluated=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.output.parent.name.endswith('_non_authoritative'):
        raise ValueError('explicit non-authoritative output directory required')
    result = audit()
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(dict(retained_pairs_per_cell=result['retained_pairs_per_cell'],
        groups=[{k:g[k] for k in ('target','flexible_fraction','pairs_with_witness','pairs_without_witness')} for g in result['groups']],
        solver_calls=0)))
