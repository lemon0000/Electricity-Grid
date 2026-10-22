"""Independent Fraction arithmetic and offline recovery checks for the B1 fixture.

Consumes primitive dictionaries; imports neither dispatch nor its power/ledger code.
Offline flow uses future inputs and is never a causal policy or network certificate.
"""
from collections import deque
from fractions import Fraction as Q
from itertools import combinations


def _require(condition, message="independent arithmetic audit failed"):
    if not condition:
        raise AssertionError(message)


def audit_records(parameters, records, method):
    _require(method in ("instantaneous", "fixed_headroom", "full_temporal"), "unknown audit method")
    p = parameters
    a = Q(p["facility_factor"]) * Q(p["beta"])
    eta, alpha = Q(p["eta"]), Q(p["alpha"])
    balances, misses, calls = {}, {}, []
    first_rejection, compliant_prefix_debt = None, Q(0)
    last = None
    rejected = False
    previous, energy, events, duration, rest = Q(0), Q(0), 0, 0, p["minimum_rest"]
    for row in records:
        _require(not rejected, "records continued after a rejected action")
        o = row["observation"]
        t = o["hour"]
        if last is not None:
            _require(t == last + 1, "nonconsecutive audit input")
        last = t
        w, k, y, supply = (Q(o[name]) for name in
                           ("workload", "compute_capacity", "clean_mwh", "supply_mw"))
        g, c, r = (Q(row[name]) for name in ("grid_served", "cfe_served", "recovery"))
        q = g + c
        base = Q(p["facility_factor"]) * (Q(o["idle_mw"]) + Q(p["beta"]) * w) + Q(p["auxiliary_mw"])
        power = base + a * (r - q)
        grid = max(base - supply, Q(0))
        green = max(base - y / alpha, Q(0)) if alpha else Q(0)
        _require(Q(row["reference_mw"]) == base and Q(row["power_mw"]) == power)
        _require(Q(row["activity"]) == w - q + r)
        _require(Q(row["grid_request_mw"]) == grid and Q(row["cfe_request_mw"]) == green)
        _require(0 <= a * g <= grid and 0 <= a * c <= green)
        _require(Q(row["grid_shortfall_mw"]) == grid - a * g)
        _require(Q(row["cfe_call_shortfall_mw"]) == green - a * c)
        _require(Q(row["cfe_shortfall_mwh"]) == max(alpha * power - y, Q(0)))
        _require(Q(row["attributed_clean_mwh"]) == min(y, max(power, Q(0))))
        _require(q + r <= Q(p["capacity"]) and not (q and r))
        _require(q <= w * Q(o["flexible_fraction"]))
        _require(sum((Q(amount) for _, amount in row["allocations"]), Q(0)) == eta * r)
        _require(len({birth for birth, _ in row["allocations"]}) == len(row["allocations"]))
        new_events = events + int(q > 0 and previous == 0)
        new_duration = duration + 1 if q else 0
        before_debt = sum((b["remaining"] for b in balances.values()), Q(0))
        failures = []
        for failed, code in (
            (grid != a * g, "grid_service_shortfall"),
            (green != a * c, "cfe_call_shortfall"),
            (not 0 <= w - q + r <= k, "device_capacity"),
            (power > supply, "scalar_supply"),
            (alpha * power > y, "hourly_cfe"),
            (abs(q - previous) > Q(p["call_ramp"]), "call_ramp"),
            (new_events > p["max_events"] or new_duration > p["max_duration"]
             or (q > 0 and previous == 0 and rest < p["minimum_rest"]), "event_envelope"),
            (energy + q > Q(p["max_call_energy"]), "call_energy"),
            (before_debt + q - eta * r > Q(p["max_debt"]), "recovery_debt"),
        ):
            if failed:
                failures.append(code)
        _require(list(row["violations"]) == failures, "event/budget/physical violation flags differ")
        blocked = any(v not in {"hourly_cfe", "cfe_call_shortfall"} for v in failures)
        expected_applied = not (method == "full_temporal" and blocked)
        _require(row["ledger_applied"] is expected_applied, "ledger application differs from method scope")
        compliant = (a * g == grid and a * c == green and 0 <= w - q + r <= k
                     and power <= supply and alpha * power <= y and not row["violations"])
        if not compliant and first_rejection is None:
            first_rejection = t
            compliant_prefix_debt = before_debt
        if not row["ledger_applied"]:
            _require(not compliant)
            rejected = True
            continue
        if q:
            balances[t] = dict(due=o["due"], incurred=q, remaining=q)
            calls.append(dict(birth=t, due=o["due"], work=q))
        for birth, amount in row["allocations"]:
            amount = Q(amount)
            _require(birth < t and birth in balances)
            _require(0 <= amount <= balances[birth]["remaining"])
            balances[birth]["remaining"] -= amount
        for birth, b in balances.items():
            _require(0 <= b["remaining"] <= b["incurred"])
            if b["due"] == t:
                misses[birth] = b["remaining"]
        previous, energy, events, duration, rest = (
            q, energy + q, new_events, new_duration, 0 if q else rest + 1)
    return dict(balances=balances, deadline_misses=misses, calls=tuple(calls),
                envelope=dict(previous_call=previous, call_energy=energy, events=events,
                              duration=duration, rest=rest),
                first_full_contract_rejection=first_rejection,
                debt_before_full_contract_rejection=compliant_prefix_debt)


def offline_recovery_check(parameters, observations, calls):
    """Exact maxflow + separate Hall-subset check for fixed, audited obligations.

    No claim is made when deadlines are outside the observed input. This simple
    graph only supports a debt bound redundant with the cumulative call bound.
    """
    if Q(parameters["max_debt"]) < Q(parameters["max_call_energy"]):
        raise ValueError("prefix debt bound requires a different offline oracle")
    if len(calls) > 12 or len(observations) > 256:
        raise ValueError("offline diagnostic size limit")
    times = [o["hour"] for o in observations]
    if not times or times != list(range(times[0], times[-1] + 1)):
        raise ValueError("continuous observed inputs required")
    if any(j["birth"] not in times or j["due"] not in times for j in calls):
        return dict(status="right_censored", flow=None)
    eta, alpha = Q(parameters["eta"]), Q(parameters["alpha"])
    gamma, beta = Q(parameters["facility_factor"]), Q(parameters["beta"])
    active = {j["birth"] for j in calls}
    if len(active) != len(calls) or any(Q(j["work"]) <= 0 or j["due"] < j["birth"] for j in calls):
        raise ValueError("invalid fixed obligations")
    by_hour = {j["birth"]: Q(j["work"]) for j in calls}
    previous, cumulative, events, duration, rest = Q(0), Q(0), 0, 0, parameters["minimum_rest"]
    for o in observations:
        q = by_hour.get(o["hour"], Q(0))
        starts = q > 0 and previous == 0
        events += int(starts)
        duration = duration + 1 if q else 0
        cumulative += q
        if (q > min(Q(parameters["capacity"]), Q(o["workload"]) * Q(o["flexible_fraction"]))
                or abs(q - previous) > Q(parameters["call_ramp"])
                or events > parameters["max_events"] or duration > parameters["max_duration"]
                or (starts and rest < parameters["minimum_rest"])
                or cumulative > Q(parameters["max_call_energy"])):
            raise ValueError("fixed call trajectory violates envelope")
        previous, rest = q, 0 if q else rest + 1
    slots = {}
    for o in observations:
        t, w = o["hour"], Q(o["workload"])
        if t in active:
            slots[t] = Q(0)
            continue
        base = gamma * (Q(o["idle_mw"]) + beta * w) + Q(parameters["auxiliary_mw"])
        caps = [Q(parameters["capacity"]), Q(parameters["max_recovery"]),
                Q(o["compute_capacity"]) - w,
                (Q(o["supply_mw"]) - base) / (gamma * beta)]
        if alpha:
            caps.append((Q(o["clean_mwh"]) / alpha - base) / (gamma * beta))
        if min(caps) < 0:
            return dict(status="unresolved_unserved_baseline", flow=None)
        slots[t] = min(caps)
    jobs = [(j["birth"], j["due"], Q(j["work"]) / eta) for j in calls]
    required = sum((j[2] for j in jobs), Q(0))
    n = len(jobs)
    sink = 1 + n + len(times)
    graph = [dict() for _ in range(sink + 1)]

    def edge(u, v, cap):
        graph[u][v] = cap
        graph[v][u] = Q(0)

    for i, (birth, due, work) in enumerate(jobs):
        edge(0, i + 1, work)
        for j, t in enumerate(times):
            if birth < t <= due:
                edge(i + 1, n + j + 1, work)
    for j, t in enumerate(times):
        edge(n + j + 1, sink, slots[t])
    sent = Q(0)
    while True:
        parent, queue = {0: None}, deque([0])
        while queue and sink not in parent:
            u = queue.popleft()
            for v, cap in graph[u].items():
                if cap > 0 and v not in parent:
                    parent[v] = u
                    queue.append(v)
        if sink not in parent:
            break
        amount, v = required, sink
        while parent[v] is not None:
            u = parent[v]
            amount, v = min(amount, graph[u][v]), u
        v = sink
        while parent[v] is not None:
            u = parent[v]
            graph[u][v] -= amount
            graph[v][u] += amount
            v = u
        sent += amount
    # Different algorithm: enumerate all nonempty job subsets and their hour union.
    deficit = Q(0)
    for size in range(1, n + 1):
        for subset in combinations(jobs, size):
            eligible = {t for t in times if any(b < t <= d for b, d, _ in subset)}
            deficit = max(deficit, sum((e for _, _, e in subset), Q(0))
                          - sum((slots[t] for t in eligible), Q(0)))
    _require(required - sent == deficit, "maxflow disagrees with independent subset cuts")
    return dict(status="offline_fixed_debt_recovery_only", flow=sent,
                required=required, feasible=sent == required, subset_deficit=deficit,
                recovery_slots=slots)
