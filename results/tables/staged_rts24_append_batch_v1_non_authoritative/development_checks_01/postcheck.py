"""Read-only ordinary-development verification; creates no run authority."""
import ast
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
calls = []


def denied(*a, **kw):
    calls.append("numerical_factory")
    raise AssertionError("numerical factory forbidden in development postcheck")


import highspy
import pyomo.environ as pyo
highspy.Highs = pyo.SolverFactory = denied
from src import staged_rts24_journal_v3 as journal


def read(path): return json.loads(Path(path).read_text(encoding="utf-8"))


def stamp(path):
    data = Path(path).read_bytes()
    return dict(bytes=len(data), sha256=sha256(data).hexdigest())


def log(path):
    raw = Path(path).read_bytes()
    return raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")


def preserved_implementation():
    def nodes(name):
        return {node.name: node for node in ast.parse((ROOT/name).read_text(encoding="utf-8")).body
                if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
    old, new = (nodes("src/staged_rts24_journal_v"+str(v)+".py") for v in (2, 3))
    unchanged = sorted(set(old)-{"_check", "_append"})
    assert set(new) == set(old) | {"_append_inputs"}
    assert all(ast.dump(old[name]) == ast.dump(new[name]) for name in unchanged)
    expected_check = deepcopy(old["_check"])
    expected_check.body[-1].value = ast.Tuple(elts=[ast.Name(id="inventory", ctx=ast.Load()),
                                                 ast.Name(id="cas", ctx=ast.Load())], ctx=ast.Load())
    assert ast.dump(expected_check) == ast.dump(new["_check"])
    return unchanged


def main():
    here = Path(__file__).resolve().parent
    record = read(here/"development_checks.json")
    assert record["authority"] == "DRAFT_NONAUTHORITATIVE"
    assert record["native_highs_constructions"] == record["solver_calls"] == 0
    assert record["formal_result"] is False and record["performance_attempt_created"] is False
    assert record["overall_performance_review_complete"] is False
    assert all(record["preseal"][key] is None for key in ("official_verdict", "seal", "receipt"))
    assert all(stamp(ROOT/path) == pin for path, pin in record["source_pins"].items())
    assert all(stamp(here/path) == pin for path, pin in record["artifacts"].items())
    assert journal.runtime_identity() == read(here/"runtime_identity.json")
    assert len(journal.SOURCE_PATHS) == 29 and preserved_implementation() == record["unchanged_v2_definitions"]
    for check in record["checks"]:
        assert check["exit_code"] == 0 and str(check["passed"])+" passed" in log(here/check["log"])
    old = ROOT/"results/tables/staged_rts24_native_v1_non_authoritative/development_checks_01/postcheck.py"
    runpy.run_path(str(old), run_name="__main__")
    assert stamp(ROOT/record["p1_registration_path"])["sha256"] == record["p1_registration_sha"]
    assert calls == []
    print(json.dumps(dict(scope="read_only_append_batch_development_check", source_pins=len(record["source_pins"]),
        artifacts=len(record["artifacts"]), unchanged_v2_definitions=len(record["unchanged_v2_definitions"]),
        ordinary_checks=sum(check["passed"] for check in record["checks"]),
        solver_calls=0, native_highs_constructions=0, performance_attempt_created=False,
        p1_registration_sha=record["p1_registration_sha"]), sort_keys=True))


if __name__ == "__main__": main()
