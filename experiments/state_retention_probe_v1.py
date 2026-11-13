"""Bounded synthetic control-domain diagnostic; no formal authority."""
from pathlib import Path
from functools import lru_cache
from itertools import product
import hashlib
import json
import time

ROOT = Path(__file__).resolve().parents[1]
MODES = ('forced', 'retain_sync', 'retain_async')
DEADLINE = float('inf')


def cap_at(t, up, firm):
    return firm if t in (4, 5) else 8 if t >= up else 4


def actions(s, cap, mode):
    r, age, stage, writing, snap, sync = s
    if not r or cap < 1:
        return (0,)
    if stage:
        return ('advance', 0) if cap >= 4 else (0,)
    if writing and sync:
        return ('advance', 0) if cap >= 4 else (0,)
    choices = tuple(range(min(cap - 1, r), -1, -1))
    if not writing and age and cap >= 4:
        choices += ('save_sync',)
        if mode == 'retain_async':
            choices += ('save_async',)
    return choices


def transition(t, s, action, c, up, firm, mode):
    r, age, stage, writing, snap, sync = s
    cap = cap_at(t, up, firm)
    lost = work = 0
    dropped = r > 0 and (cap < 1 or (mode == 'forced' and t in (4, 5) and firm < 4))
    if dropped:
        lost = age
        r += age
        age = stage = writing = snap = sync = 0
        action = 0
    power = 0 if not r or dropped else 1
    if r and not dropped:
        if action in ('save_sync', 'save_async'):
            assert not stage and not writing and age and cap >= 4
            stage = c
            sync = int(action == 'save_sync')
        if stage and action != 0:
            assert action in ('advance', 'save_sync', 'save_async') and cap >= 4
            stage -= 1
            power = 4
            if not stage:
                writing, snap = 1, age
        elif writing and sync:
            if action == 'advance':
                power = 4
                age -= snap
                writing = snap = sync = 0
        else:
            assert isinstance(action, int) and 0 <= action <= min(cap - 1, r)
            work = action
            r -= work
            age += work
            power += work
            if writing:
                age -= snap
                writing = snap = sync = 0
        if not r:
            age = stage = writing = snap = sync = 0
    after = (r, age, stage, writing, snap, sync)
    assert r == s[0] + lost - work
    assert min(after) >= 0 and power <= cap
    return after, dict(t=t, before=s, after=after, action=action, lost=lost, work=work, batch_power=power)


def solve(R, a, c, up, L, firm, mode):
    s = (4*R, 4*a, 0, 0, 0, 0)
    prefix = []
    for t in range(4-L):
        act = min(cap_at(t, up, firm)-1, s[0]) if s[0] else 0
        s, rec = transition(t, s, act, c, up, firm, mode)
        prefix.append(rec)
    initial = s
    @lru_cache(None)
    def dp(t, state):
        if time.perf_counter() > DEADLINE:
            raise TimeoutError('fixed wall budget')
        if t == 12:
            return () if state[0] == 0 else None
        if state[0] > sum(max(0, cap_at(h, up, firm)-1) for h in range(t,12)):
            return None
        cap = cap_at(t, up, firm)
        # Drop occurs before action selection; all choices collapse to zero.
        domain = (0,) if mode == 'forced' and t in (4, 5) and firm < 4 else actions(state, cap, mode)
        for act in domain:
            nxt, _ = transition(t, state, act, c, up, firm, mode)
            tail = dp(t+1, nxt)
            if tail is not None:
                return (act,) + tail
        return None
    chosen = dp(4-L, initial)
    trace = list(prefix)
    if chosen is not None:
        for t, act in enumerate(chosen, 4-L):
            s, rec = transition(t, s, act, c, up, firm, mode)
            trace.append(rec)
        assert s[0] == 0
    greedy = initial
    for t in range(4-L, 12):
        act = max(actions(greedy, cap_at(t, up, firm), mode), key=lambda x: x if isinstance(x, int) else -1)
        greedy, _ = transition(t, greedy, act, c, up, firm, mode)
    assert greedy[0] != 0 or chosen is not None
    # Optimistic capacity bound from the same actual prefix (ignores rollback/save).
    relaxed = initial[0] <= sum(max(0, cap_at(t, up, firm)-1) for t in range(4-L, 12))
    assert chosen is None or relaxed
    return dict(exact=chosen is not None, greedy=greedy[0] == 0, capacity_only=relaxed,
                states=dp.cache_info().currsize, trace=trace if chosen is not None else None)


def main():
    global DEADLINE
    out = ROOT/'results/tables/state_retention_probe_v1_non_authoritative/attempt_01'
    out.mkdir(parents=True, exist_ok=False)
    deps = [Path(__file__), ROOT/'docs/plan/state_retention_probe_v1_contract.md']
    report = dict(authority='DRAFT_NONAUTHORITATIVE', formal_result=False,
                  hashes={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in deps}, rows=[])
    started = time.perf_counter()
    try:
        s = (20, 8, 0, 0, 0, 0)
        assert transition(4,s,0,1,6,2,'retain_sync')[0] == s
        assert transition(4,s,0,1,6,2,'forced')[0] == (28,0,0,0,0,0)
        assert transition(4,s,0,1,6,0,'retain_async')[0] == (28,0,0,0,0,0)
        staged = transition(3,s,'save_async',1,6,2,'retain_async')[0]
        assert staged == (20,8,0,1,8,0)
        assert transition(4,staged,1,1,6,2,'retain_async')[0] == (19,1,0,0,0,0)
        DEADLINE = started + 5
        times = []
        for i in range(8):
            t = time.perf_counter()
            solve(10+i, 3, 2, 10, 4, (0,2,4)[i % 3], MODES[i % 3])
            times.append(time.perf_counter()-t)
        report['performance'] = dict(samples=8, seconds=times, conservative_projection_seconds=max(times)*5724)
        if max(times)*5724 > 60:
            raise RuntimeError('performance admission exceeds fixed 60s; grid not launched')
        DEADLINE = time.perf_counter()+60
        grid_start = time.perf_counter()
        for a, c, up, L, firm, R in product((0,3), (1,2), (6,10), (0,2,4), (0,2,4), range(27)):
            if R == 0 and a: continue
            for mode in MODES:
                result = solve(R, a, c, up, L, firm, mode)
                report['rows'].append(dict(age=a, save_steps=c, upgrade=up, notice=L, firm_ticks=firm, R=R, mode=mode, **result))
        report['grid_wall_seconds'] = time.perf_counter()-grid_start
        # Keep the largest passing witness for each fixed parameter group.
        keys = ('age','save_steps','upgrade','notice','firm_ticks','mode')
        groups = {}
        for row in report['rows']:
            k = tuple(row[x] for x in keys)
            groups.setdefault(k, []).append(row)
        report['boundaries'] = []
        for k, rows in groups.items():
            passed = [r for r in rows if r['exact']]
            top = max(passed, key=lambda r:r['R']) if passed else None
            assert not rows[-1]['exact'] and rows[-1]['R'] == 26
            report['boundaries'].append(dict(zip(keys,k), max_R=top['R'] if top else None, trace=top['trace'] if top else None))
        lookup = {(tuple(row[x] for x in keys[:-1]), row['R'], row['mode']):row for row in report['rows']}
        for row in report['rows']:
            if row['exact']:
                k = tuple(row[x] for x in keys[:-1])
                if row['mode'] == 'forced': assert lookup[k,row['R'],'retain_sync']['exact']
                if row['mode'] == 'retain_sync': assert lookup[k,row['R'],'retain_async']['exact']
                for column, domain in (('firm_ticks',(0,2,4)), ('notice',(0,2,4))):
                    for value in domain:
                        if value >= row[column]:
                            replacement = dict(row, **{column:value})
                            assert lookup[tuple(replacement[x] for x in keys[:-1]),row['R'],row['mode']]['exact']
            row.pop('trace')
        report['counts'] = {mode:{m:sum(r[m] for r in report['rows'] if r['mode']==mode) for m in ('exact','greedy','capacity_only')} for mode in MODES}
        report['status'] = 'completed'
    except Exception as exc:
        report['status'] = 'failed'
        report['error'] = repr(exc)
        raise
    finally:
        report['wall_seconds'] = time.perf_counter()-started
        report['dependencies_unchanged'] = all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in report['hashes'].items())
        data = json.dumps(report, indent=2).encode()
        assert len(data) <= 12*1024*1024
        (out/'report.json').write_bytes(data)
        (out/'report.sha256').write_text(hashlib.sha256(data).hexdigest(), encoding='ascii')
        assert json.loads((out/'report.json').read_bytes())['status'] == report['status']
        print(json.dumps({k:report.get(k) for k in ('status','error','performance','counts','wall_seconds')}, indent=2))


if __name__ == '__main__': main()
