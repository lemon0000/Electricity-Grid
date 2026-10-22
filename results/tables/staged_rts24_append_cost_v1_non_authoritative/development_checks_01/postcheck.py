"""Read-only development evidence check; grants no experiment authority."""
from hashlib import sha256
import ast
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
HERE = Path(__file__).resolve().parent


def read(path): return json.loads(Path(path).read_bytes())


def stamp(path):
    raw = Path(path).read_bytes()
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def log(path):
    raw = Path(path).read_bytes()
    return raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")


def main():
    from experiments import staged_rts24_append_cost_probe_v1 as probe
    from experiments.staged_rts24_append_cost_observer_v1 import Observation
    record = read(HERE/"development_checks.json")
    assert record["authority"] == "DRAFT_NONAUTHORITATIVE" and record["formal_result"] is False
    assert record["performance_attempt_created_at_checkpoint"] is False
    assert record["native_highs_constructions"] == record["solver_calls"] == 0
    assert record["preseal"]["remaining_high_medium_implementation_findings"] == 0
    assert all(record["preseal"][key] is None for key in ("official_verdict", "seal", "receipt"))
    assert all(stamp(ROOT/path) == pin for path, pin in record["source_pins"].items())
    assert all(stamp(HERE/path) == pin for path, pin in record["artifacts"].items())
    for item in record["checks"]:
        assert item["exit_code"] == 0 and str(item["passed"])+" passed" in log(HERE/item["log"])
    assert "5 failed, 14 passed" in log(HERE/"pytest_probe_01.log")
    assert record["distinct_ordinary_checks"] == 46
    for name in record["source_pins"]:
        if name.endswith(".py"): ast.parse((ROOT/name).read_text(encoding="utf-8"))
    runpy.run_path(str(ROOT/"results/tables/staged_rts24_append_batch_v1_non_authoritative/development_checks_01/postcheck.py"), run_name="__main__")
    with Observation() as obs:
        assert probe.pins(obs.m) == read(HERE/"binding_snapshot_v2.json")
        assert obs.counts.get("forbidden_calls", 0) == obs.counts.get("selective.started", 0) == 0
    assert not (probe.P1.parent/"p1_01").exists()
    present = [path.name for path in (probe.PREP, probe.REGISTRATION, probe.OUTPUT) if path.exists()]
    if "--allow-cost-attempt" not in sys.argv: assert present == [], present
    print(json.dumps(dict(scope="read_only_saved_append_cost_development", source_pins=len(record["source_pins"]),
        distinct_ordinary_checks=46, preserved_historical_files=len(read(HERE/"binding_snapshot_v2.json")["historical_trees"]),
        solver_calls=0, native_highs_constructions=0, p1_attempt_created=False,
        cost_paths_present=present, official_verdict=None, seal=None, receipt=None), sort_keys=True))


if __name__ == "__main__": main()
