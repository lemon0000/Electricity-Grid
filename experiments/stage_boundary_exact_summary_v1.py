"""Rebuild analytical Hall bounds from the saved diagnostic, without scheduling runs."""
import hashlib
import json
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/tables/stage_boundary_validation_v1_non_authoritative/attempt_01'


def main():
    source = OUT / 'report.json'
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    assert digest == (OUT / 'report.sha256').read_text().strip()
    report = json.loads(source.read_bytes())
    rows = []
    for row in report['rows']:
        actual = [min(v[h] for v in row['capacities'].values()) for h in range(8)]
        jobs = [(0,row['debt_due'])] + [(h,h+2) for h in (0,2,4)]
        bounds = {}
        for mode,cap in [('current_frozen',[actual[0]]*8),('terminal_frozen',[actual[-1]]*8),('chronological',actual)]:
            cuts = []
            for mask in range(1,16):
                ids = [j for j in range(4) if mask >> j & 1]
                hours = set(h for j in ids for h in range(jobs[j][0],jobs[j][1]+1))
                fixed = 4 if 0 in ids else 0
                count = sum(j > 0 for j in ids)
                if count:
                    cuts.append((Fraction(sum(cap[h] for h in hours)-fixed,4*count),ids,sorted(hours)))
            bound,ids,hours = min(cuts)
            bounds[mode] = dict(exact_bound=str(bound),binding_jobs=ids,binding_hours=hours)
            for run in row['runs']:
                assert run['results'][mode]['feasible'] == (Fraction(run['scale_quanta'],4) <= bound)
        rows.append(dict(key=[row[k] for k in ['equipment','grid','clean','debt_due']],bounds=bounds))
    summary = dict(authority='DRAFT_NONAUTHORITATIVE',source_sha256=digest,
        derivation='Hall subset inequality: lambda <= (sum capacity - inherited work)/(4 * count new jobs). Exact only for this independent splittable model.',
        all_scanned_feasibilities_match_exact_bounds=True,rows=rows)
    target = OUT / 'exact_boundary_supplement.json'
    data = json.dumps(summary,indent=2).encode('utf-8')
    # The original Windows text writer used CRLF; preserve its exact bytes.
    data = data.replace(b'\n', b'\r\n')
    if target.exists():
        assert target.read_bytes() == data, 'Existing analytical evidence differs; do not overwrite'
    else:
        target.write_bytes(data)
    binding = dict(source_sha256=digest,summary_sha256=hashlib.sha256(data).hexdigest(),
                   generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (OUT/'exact_boundary_binding.json').write_text(json.dumps(binding,indent=2),encoding='utf-8')
    print('Exact summary rebuilt identically; source, summary and generator hashes bound.')


if __name__ == '__main__':
    main()
