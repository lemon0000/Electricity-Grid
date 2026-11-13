"""Bounded diagnostic; fixed-policy evidence only, no formal authority."""
import dataclasses as dc
import hashlib
import json
from pathlib import Path
import sys
import time
import tracemalloc
from fractions import Fraction as Q

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.min_fraction_misalignment_v1 import build_fixture
from src.staged_deliverability_d_grid_v2 import load_grid_case
from src.staged_deliverability_development_v1 import execute, assessment, power_mapping, plain, task_balances


def main():
    start = time.perf_counter()
    tracemalloc.start()
    resume = '--remaining' in sys.argv
    out = ROOT / ('results/tables/min_fraction_misalignment_v2_non_authoritative/' + ('attempt_02_remaining' if resume else 'attempt_01'))
    out.mkdir(parents=True, exist_ok=False)
    report = {'authority': 'DRAFT_NONAUTHORITATIVE', 'formal_result': False, 'rows': []}
    deps = ['experiments/min_fraction_misalignment_v1.py', 'experiments/min_fraction_misalignment_v2.py',
            'src/staged_deliverability_development_v1.py', 'src/staged_deliverability_d_grid_v2.py',
            'docs/plan/min_fraction_misalignment_v2_admission.md',
            'results/tables/min_fraction_misalignment_v1_non_authoritative/attempt_01/report.json']
    report['hashes'] = {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in deps}
    try:
        case_index = 0
        for grid in (8, 10, 12, 16):
            for equip in (0, 12, 18):
                fixture = out / f'base_g{grid}_e{equip}.yaml'
                build_fixture(fixture, ramp_hour=8, expand_hour=grid)
                params, base = load_grid_case(fixture, 'fast', 'on_time', 'early')
                # Extend observations, retaining original untruncated deadlines.
                base = tuple(dc.replace(base[min(h,29)], hour=h, due=h+3,
                    compute_capacity=Q(4,5)+(Q(2,5) if h>=equip else 0),
                    idle_mw=Q(2,25)+(Q(1,25) if h>=equip else 0)) for h in range(36))
                for clean in ('zero_recovery', 'adequate_recovery'):
                    for budget in ('original', 'nonbinding'):
                        case_index += 1
                        if resume and case_index <= 41:
                            continue
                        p = dc.replace(params, capacity=Q(2),
                            max_call_energy=params.max_call_energy if budget=='original' else Q(100),
                            max_debt=params.max_debt if budget=='original' else Q(100))
                        obs = tuple(dc.replace(o, clean_mwh=p.alpha*(power_mapping(p,o)[2]+
                            (p.slope*p.max_recovery if clean=='adequate_recovery' else 0))) for o in base)
                        need = max(max(power_mapping(p,o)[2]-o.supply_mw,0)/p.slope/o.workload for o in obs)
                        fractions = sorted(set([Q(i,32) for i in range(33)]+[max(Q(0),need-Q(1,1000)),need,min(Q(1),need+Q(1,1000))]))
                        row = dict(grid=grid,equipment=equip,clean=clean,budget=budget,instant_bound=str(need),
                                   parameters=plain(p),observations=plain(obs),runs=[])
                        for f in fractions:
                            for method in ('instantaneous','fixed_headroom','full_temporal'):
                                if time.perf_counter()-start>60:
                                    raise TimeoutError('60s diagnostic budget')
                                state=execute(p,tuple(dc.replace(o,flexible_fraction=f) for o in obs),method,'diagnostic')
                                a=assessment(state,registration_end=30,expected_last_hour=35)
                                tasks=task_balances(state)
                                assert all(t['immediate']+t['recovered']+t['remaining']==t['original'] for t in tasks)
                                assert sum((t['deadline_miss'] or 0) for t in tasks if 0<=t['birth']<30)==a['observed_primary_deadline_miss']
                                row['runs'].append(dict(f=str(f),method=method,assessment=plain(a)))
                        row['minimum']={m: next((str(f) for f in fractions if any(r['f']==str(f) and r['method']==m and r['assessment']['method_conditions_satisfied'] is True for r in row['runs'])),None) for m in ('instantaneous','fixed_headroom','full_temporal')}
                        report['rows'].append(row)
        report['status']='completed'
    except Exception as exc:
        report['status']='failed'; report['error']=repr(exc)
        raise
    finally:
        report['wall_seconds']=time.perf_counter()-start
        report['python_peak_bytes']=tracemalloc.get_traced_memory()[1]
        report['dependencies_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in report['hashes'].items())
        path=out/'report.json'; path.write_text(json.dumps(report,indent=2),encoding='utf-8')
        (out/'report.sha256').write_text(hashlib.sha256(path.read_bytes()).hexdigest(),encoding='utf-8')
        assert json.loads(path.read_text())['status']==report['status']
        print(report['status'],len(report['rows']),report['wall_seconds'],report['python_peak_bytes'])


if __name__=='__main__':
    main()
