"""Read-only byte/graph accounting of already bound journals; no scientific replay."""
import hashlib
import json
from pathlib import Path
import stat
import time

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/"results/tables/staged_rts24_saved_cost_v1_non_authoritative/audit_01"
INPUTS = {
    "results/tables/staged_rts24_journal_v1_non_authoritative/attempt_01/completion.json":
        "dbb0200384c5706bc43001981f943308c5f612f5402ac51e623944718a6f3620",
    "results/tables/staged_rts24_journal_v2_non_authoritative/closure_probe_01/completion.json":
        "2826a634b43be911b3911c1666e295d98edc07d7185e0a5fcd08ad9e71fac6ae",
}
JOURNAL = "results/tables/staged_rts24_journal_v2_non_authoritative/closure_probe_01/success/journal"
SOURCES = ("src/staged_rts24_journal_v2.py", "src/staged_rts24_evidence_store_v1.py",
           "src/staged_rts24_causal_v2.py", "src/staged_rts24_causal_audit_v2.py",
           "experiments/staged_rts24_saved_size_audit_v1.py",
           "docs/plan/staged_deliverability_c_retained_cost_review_v1.md")


def check(condition, message):
    if not condition: raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")


def sha(raw): return hashlib.sha256(raw).hexdigest()


def fields(wire, kind):
    check(wire[:2] == ["class", kind], "unexpected typed class")
    return dict(wire[2])


def references(wire):
    """Walk typed nodes, not untagged user list/string contents."""
    if not isinstance(wire, list): return set()
    tag = wire[0]
    if tag == "ref": return {wire[1]}
    if tag in ("Q", "float"): return set()
    if tag == "class": children = [v for _, v in wire[2]]
    elif tag == "dict": children = [v for _, v in wire[1]]
    elif tag in ("tuple", "list"): children = wire[1]
    else: raise ValueError("unknown typed node")
    return set().union(*(references(v) for v in children))


def audit():
    started, cache, read_bytes, reads = time.monotonic(), {}, 0, 0

    def read(relative, fresh=False):
        nonlocal read_bytes, reads
        if relative in cache and not fresh: return cache[relative]
        check(time.monotonic()-started < 30, "static audit wall cap")
        path = ROOT/relative
        check(path.resolve().is_relative_to(ROOT), "input outside repository")
        current = path
        while current != ROOT:
            mode = current.lstat()
            check(not stat.S_ISLNK(mode.st_mode) and not getattr(mode, "st_file_attributes", 0)&0x400,
                  "linked audit input")
            current = current.parent
        check(path.is_file() and path.stat().st_size <= 1024**2, "static audit file cap")
        raw = path.read_bytes()
        read_bytes, reads = read_bytes+len(raw), reads+1
        check(read_bytes <= 8*1024**2, "static audit read cap")
        if fresh: check(raw == cache[relative], "audit input changed")
        else: cache[relative] = raw
        return raw

    cores = []
    for relative, expected in INPUTS.items():
        raw = read(relative)
        check(sha(raw) == expected, "completion anchor differs")
        manifest = json.loads(raw)
        base = Path(relative).parent
        total = 0
        for name, item in manifest["files"].items():
            data = read((base/name).as_posix())
            check(len(data) == item["bytes"] and sha(data) == item["sha256"], "bound core differs")
            total += len(data)
        check(total == manifest["logical_bytes"] and len(manifest["files"]) == manifest["manifest_files"],
              "completion accounting differs")
        cores.append(dict(completion=relative, sha256=expected, core_files=len(manifest["files"]),
                          core_bytes=total, completion_bytes=len(raw)))
    source_hashes = {p: dict(bytes=len(read(p)), sha256=sha(read(p))) for p in SOURCES}
    saved_bindings = json.loads(read("results/tables/staged_rts24_journal_v2_non_authoritative/closure_probe_01/report.json"))["bindings"]
    for p in SOURCES[:4]:
        check(source_hashes[p]["sha256"] == saved_bindings["runtime"]["sources"][p], "analysis source differs from saved runtime")
    prefix = JOURNAL+"/"
    objects = {Path(p).stem: json.loads(data) for p, data in cache.items()
               if p.startswith(prefix+"objects/")}
    sizes = {key: len(cache[prefix+"objects/"+key+".json"]) for key in objects}
    for key, obj in objects.items():
        check(sha(cache[prefix+"objects/"+key+".json"]) == key, "CAS identity differs")
        check(obj["schema"] == "staged_rts24_typed_cas_v1", "CAS schema differs")

    def closure(root):
        wanted, pending = set(), [root]
        while pending:
            key = pending.pop()
            if key in wanted: continue
            check(key in objects, "missing retained reference")
            wanted.add(key)
            pending.extend(references(objects[key]["payload"]))
        return wanted

    rows, known, root_bytes, head_bytes, totals = [], set(), 0, 0, dict(cas_inventory_bytes=0, root_check_bytes=0)
    previous_sha = None
    names = ["genesis.json"]+sorted(Path(p).name for p in cache if p.startswith(prefix+"entry_"))
    for name in names:
        raw = read(prefix+name)
        entry = json.loads(raw)
        keys = {k.removesuffix(".json") for k in entry["after_cas_keys"]}
        check(len(keys) == len(entry["after_cas_keys"]) and known <= keys, "nonmonotone retained keys")
        is_genesis = name == "genesis.json"
        if is_genesis: added = closure(entry["fixture_ref"]) | closure(entry["state_ref"])
        else:
            check(entry["previous_sha"] == previous_sha, "root chain differs")
            added = closure(entry["payload_ref"]) | closure(entry["state_ref"])
        check(keys == known | added, "retained key closure differs")
        B, N = sum(sizes[k] for k in known), sum(sizes[k] for k in keys)
        J, J_new = root_bytes, root_bytes+len(raw)
        component = None
        if not is_genesis:
            payload_keys = known | closure(entry["payload_ref"])
            P = sum(sizes[k] for k in payload_keys)
            terminal = entry["kind"] == "terminal"
            component = dict(cas_inventory_calls=8 if terminal else 10,
                root_inventory_calls=4 if terminal else 6, check_calls=2 if terminal else 4,
                cas_inventory_bytes=(3 if terminal else 5)*B+2*P+3*N,
                root_check_bytes=(5 if terminal else 9)*J+J_new+(2 if terminal else 4)*head_bytes)
            for metric in totals: totals[metric] += component[metric]
        state = fields(objects[entry["state_ref"]]["payload"], "ExecutionState")
        ledger = fields(state["ledger"], "DebtLedger")
        check(state["records"][0] == ledger["cohorts"][0] == "tuple", "state tuple shape differs")
        rows.append(dict(name=name, kind=entry["kind"], keys=len(keys), new_keys=len(keys-known), cas_bytes=N,
            new_cas_bytes=N-B, root_file_bytes=len(raw), root_total_bytes=J_new,
            key_list_bytes=len(canonical(entry["after_cas_keys"])), state_blob_bytes=sizes[entry["state_ref"]],
            state_records=len(state["records"][1]), state_cohorts=len(ledger["cohorts"][1]),
            state_closure_objects=len(closure(entry["state_ref"])),
            state_closure_bytes=sum(sizes[k] for k in closure(entry["state_ref"])),
            payload_closure_objects=None if is_genesis else len(closure(entry["payload_ref"])),
            payload_closure_bytes=None if is_genesis else sum(sizes[k] for k in closure(entry["payload_ref"])),
            payload_reused_keys=None if is_genesis else len(known & closure(entry["payload_ref"])),
            structural_component=component))
        known, root_bytes, head_bytes, previous_sha = keys, J_new, len(raw), sha(raw)
    check(known == set(objects), "unaccounted success CAS")
    kinds = {}
    for key, obj in objects.items():
        group = kinds.setdefault(obj["kind"], dict(objects=0, bytes=0))
        group["objects"] += 1
        group["bytes"] += sizes[key]
    for relative in tuple(cache): read(relative, fresh=True)
    return dict(authority="DRAFT_NONAUTHORITATIVE", mode="saved_byte_and_graph_accounting_no_replay",
        sources=source_hashes, bound_cores=cores, success_journal=JOURNAL, entries=rows, cas_kinds=kinds,
        structural_component_totals=totals,
        component_excludes="genesis, fresh, publication/readback/get, runtime/source fingerprints, other cases, report",
        input_files=len(cache), successful_logical_reads=reads, successful_logical_read_bytes=read_bytes,
        solver_calls=0, numeric_point_generation=0, overall_performance_review_complete=False, resource_admission=False)


if __name__ == "__main__":
    report = audit()
    raw = canonical(report)
    check(len(raw) <= 128*1024, "audit output cap")
    OUTPUT.mkdir(parents=True, exist_ok=False)
    with (OUTPUT/"report.json").open("xb") as out: out.write(raw)
    print(json.dumps(dict(files=report["input_files"], cores=report["bound_cores"],
                         entries=report["entries"], component=report["structural_component_totals"])))
