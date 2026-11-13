"""Static artifact audit; does not execute a solver or rerun cases."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder = ROOT/'results/tables/state_retention_probe_v1_non_authoritative/attempt_01'
    hashes = {}
    for name in ('report','summary'):
        raw = (folder/(name+'.json')).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        assert digest == (folder/(name+'.sha256')).read_text().strip()
        hashes[name] = digest
    d = json.loads((folder/'report.json').read_bytes())
    assert d['status']=='completed' and not d['formal_result']
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in d['hashes'].items())
    witnesses = 0
    for b in d['boundaries']:
        trace = b['trace']
        if trace is None: continue
        witnesses += 1
        previous = None
        durable = -1
        for t, rec in enumerate(trace):
            assert rec['t']==t
            before, after = rec['before'], rec['after']
            if previous is not None: assert before == previous
            assert after[0] == before[0]+rec['lost']-rec['work']
            current = 4*(b['max_R']+b['age'])-after[0]-after[1]
            assert current >= durable >= -1
            cap = b['firm_ticks'] if t in (4,5) else 8 if t>=b['upgrade'] else 4
            assert 0 <= rec['batch_power'] <= cap
            durable, previous = current, after
        assert len(trace)==12 and previous[0]==0
    assert witnesses==216
    keys = ('age','save_steps','upgrade','notice','firm_ticks','R','mode')
    lookup = {tuple(r[k] for k in keys):r for r in d['rows']}
    assert len(lookup)==5724
    no_loss_cases = 0
    for r in d['rows']:
        if r['mode']!='forced' and r['firm_ticks']>=2:
            no_loss_cases += 1
            assert r['exact']==r['greedy']==r['capacity_only']
            for L in (0,2,4):
                k = (r['age'],r['save_steps'],r['upgrade'],L,r['firm_ticks'],r['R'],r['mode'])
                assert r['exact']==lookup[k]['exact']
    audit = dict(authority='DRAFT_NONAUTHORITATIVE',formal_result=False,status='passed',
                 source_hashes=hashes,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 boundary_witnesses=witnesses,no_loss_cases=no_loss_cases,
                 checks=['source/dependency hashes','witness continuity','work balance','durable monotonicity',
                         'power limits','original deadline','no-loss exact=greedy=capacity-only and notice invariance'])
    target = folder/'audit.json'
    assert not target.exists()
    encoded = json.dumps(audit,indent=2).encode()
    target.write_bytes(encoded)
    (folder/'audit.sha256').write_text(hashlib.sha256(encoded).hexdigest(),encoding='ascii')
    print(json.dumps(audit,indent=2))


if __name__=='__main__':main()
