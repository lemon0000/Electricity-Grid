"""Read-only source verification and derived diagnostic summary."""
from pathlib import Path
import hashlib
import json
from itertools import product

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder = ROOT/'results/tables/state_retention_probe_v1_non_authoritative/attempt_01'
    source = folder/'report.json'
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == (folder/'report.sha256').read_text(encoding='ascii').strip()
    data = json.loads(raw)
    assert data['status'] == 'completed' and not data['formal_result']
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in data['hashes'].items())
    keys = ('age','save_steps','upgrade','notice','firm_ticks','R','mode')
    lookup = {tuple(row[k] for k in keys):row for row in data['rows']}
    assert len(lookup) == len(data['rows']) == 5724
    summary = dict(authority='DRAFT_NONAUTHORITATIVE',formal_result=False,source_sha256=digest,
                   source_rows=len(lookup),counts=data['counts'],max_states=max(r['states'] for r in data['rows']),
                   source_bytes=len(raw),by_mode={},retention_rescues=0,async_admission_changes=0,menus=[])
    for mode in ('forced','retain_sync','retain_async'):
        summary['by_mode'][mode] = {}
        for firm in (0,2,4):
            rr = [r for r in data['rows'] if r['mode']==mode and r['firm_ticks']==firm]
            summary['by_mode'][mode][str(firm)] = dict(cases=len(rr),exact=sum(r['exact'] for r in rr),
                capacity_false_pass=sum(r['capacity_only'] and not r['exact'] for r in rr))
    for r in data['rows']:
        if r['mode']=='forced':
            k = tuple(r[x] for x in keys[:-1])
            summary['retention_rescues'] += int(not r['exact'] and lookup[k+('retain_sync',)]['exact'])
            summary['async_admission_changes'] += int(lookup[k+('retain_sync',)]['exact'] != lookup[k+('retain_async',)]['exact'])
    for a,c,up,R,mode in product((0,3),(1,2),(6,10),range(27),('forced','retain_sync','retain_async')):
        if R==0 and a: continue
        minimum = []
        for L in (0,2,4):
            passed = [firm for firm in (0,2,4) if lookup[a,c,up,L,firm,R,mode]['exact']]
            minimum.append(min(passed)/4 if passed else None)
        summary['menus'].append(dict(age=a,save_steps=c,upgrade=up,R=R,mode=mode,
                                     notice_minutes=[0,10,20],minimum_batch_firm=minimum))
    summary['menu_notice_reductions'] = {}
    for mode in ('forced','retain_sync','retain_async'):
        menus = [m for m in summary['menus'] if m['mode']==mode]
        summary['menu_notice_reductions'][mode] = dict(contexts=len(menus),
            finite_reductions=sum(m['minimum_batch_firm'][0] is not None and m['minimum_batch_firm'][2] is not None
                                  and m['minimum_batch_firm'][2]<m['minimum_batch_firm'][0] for m in menus),
            infeasible_to_feasible=sum(m['minimum_batch_firm'][0] is None and m['minimum_batch_firm'][2] is not None for m in menus))
    encoded = json.dumps(summary,indent=2).encode()
    target = folder/'summary.json'
    assert not target.exists()
    target.write_bytes(encoded)
    (folder/'summary.sha256').write_text(hashlib.sha256(encoded).hexdigest(),encoding='ascii')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('menus','by_mode')},indent=2))
    print('example R11 a0 c2 up6:',[m for m in summary['menus'] if (m['age'],m['save_steps'],m['upgrade'],m['R'])==(0,2,6,11)])


if __name__=='__main__':main()
