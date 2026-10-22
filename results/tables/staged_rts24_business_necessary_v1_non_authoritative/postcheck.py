"""Read-only saved arithmetic verification; CLI emits a create-only observation."""
from hashlib import sha256
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import stat
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
PROJECT_NAMES = {
    "src/staged_rts24_business_necessary_v1.py","src/staged_rts24_business_necessary_audit_v1.py",
    "experiments/staged_rts24_business_necessary_audit_v1.py","tests/test_staged_rts24_business_necessary_v1.py",
    "docs/plan/staged_deliverability_c_business_necessary_audit_contract_v1.md",
    "src/__init__.py","experiments/__init__.py","src/staged_rts24_development_v1.py",
    "experiments/staged_c_workflow_budget_v1.py","docs/model_spec/staged_deliverability_network_development_v1.md",
    "configs/staged_deliverability_rts24_v1.DRAFT.yaml","configs/staged_deliverability_small_case_v1.DRAFT.yaml",
    "configs/staged_deliverability_network_v1.DRAFT.yaml",
}
BOOTSTRAP = {
    "src/__init__.py":"ad4caa31a8bd5d534f5c65b38b67a393b740a5efd947988f47e1b55642c4cfc0",
    "experiments/__init__.py":"f67a437b3910b0400486a45167d0001163081e3b8b3f1d6166df4e3a3adf3581",
    "experiments/staged_c_workflow_budget_v1.py":"5bc19005ef1f0812a7d566dfc30bb6cef05f43ef21b9ed4f50262917034cfa82",
}


def require(condition,message):
    if not condition: raise ValueError(message)


def owned_module(name,source):
    module=importlib.import_module(name)
    require(Path(module.__file__).resolve() == ROOT/source,"imported project module origin")
    return module


def fresh_scope(package,modules):
    require(package in (None,"") and not any(name == p or name.startswith(p+".")
        for name in modules for p in ("src","experiments","yaml")),"file-path CLI and fresh repo/parser module scope required")


def bootstrap_sources():
    pins={}
    for name,digest in BOOTSTRAP.items():
        path=ROOT/name
        require(path.resolve(strict=True).is_relative_to(ROOT),"bootstrap path escaped")
        for parent in (path,*path.parents):
            info=parent.lstat()
            require(not stat.S_ISLNK(info.st_mode) and not getattr(info,"st_file_attributes",0)&0x400,"linked bootstrap")
            if parent == ROOT:break
        before=path.stat()
        require(stat.S_ISREG(before.st_mode) and before.st_size <= 2*1024**2,"bootstrap size")
        with path.open("rb") as stream:
            opened=os.fstat(stream.fileno());raw=stream.read(before.st_size+1);after=os.fstat(stream.fileno())
        require(os.path.samestat(before,opened) and os.path.samestat(opened,path.stat())
            and before.st_size == after.st_size == len(raw) and sha256(raw).hexdigest() == digest,"bootstrap SHA before import")
        pins[name]=dict(bytes=len(raw),sha256=digest)
    return pins


def check_scope(report):
    require(report["authority"] == "DRAFT_NONAUTHORITATIVE" and report["formal_result"] is False
        and report["resource_admission"] is False and report["source_and_environment_bookends"] is True,"authority mismatch")
    require(report["review_stage"] == "PRE_SEAL_AUDIT"
        and report["scope"] == "source_bound_public_business_one_hour_necessary_relaxations"
        and report["overall_performance_review_complete"] is False and report["imported_project_module_paths_checked"] is True
        and report["fixed_repository_cwd"] is True and set(report["input_pins"]) == PROJECT_NAMES,"exact scope/project input set")


def verify():
    require(Path.cwd().resolve() == ROOT and sys.dont_write_bytecode and sys.flags.no_user_site == 1,"fixed cwd and -B -s required")
    fresh_scope(__package__,sys.modules)
    started = time.perf_counter()
    bootstrap=bootstrap_sources()
    Reader=owned_module("experiments.staged_c_workflow_budget_v1","experiments/staged_c_workflow_budget_v1.py").Reader
    project = Reader(ROOT)
    report_name = (HERE/"audit_01/audit.json").relative_to(ROOT).as_posix()
    raw_report = project.read(report_name)
    report = json.loads(raw_report)
    check_scope(report)
    require(report["bootstrap"]["pins"] == bootstrap,"bootstrap source pin set")
    for key in ("actual_trajectory","raw_network_g","normal_C_network_point","fault_F_network_points",
            "complete_139_network_conditions","complete_temporal_backing","capacity_release"):
        require(report[key] is None,"unevaluated layer acquired a result")
    require(report["counters"]["primary_rows"] == report["counters"]["independent_rows"] == 40
        and all(report["counters"][k] == 0 for k in ("scientific_compiler_calls","model_builds","native_calls")),"scope counters")
    require(report["counters"]["explicit_bounded_reads"] <= 480 and report["counters"]["explicit_bounded_bytes"] <= 12*1024**2
        and report["prepublication_wall_seconds"] < 30 and len(raw_report) <= 1024**2,"recorded budget")
    for name,pin in report["input_pins"].items(): project.read(name,pin)
    require(report["input_pins"]["experiments/staged_c_workflow_budget_v1.py"]["sha256"] ==
        "5bc19005ef1f0812a7d566dfc30bb6cef05f43ef21b9ed4f50262917034cfa82","frozen reader identity")
    distribution=importlib.metadata.distribution("PyYAML")
    selected={str(p).replace("\\","/") for p in distribution.files
        if (str(p).replace("\\","/").startswith("yaml/") and str(p).endswith((".py",".pyd")))
        or (".dist-info/" in str(p).replace("\\","/") and p.name in ("METADATA","RECORD","WHEEL"))}
    require(distribution.version == report["parser"]["version"] == "6.0.3" and report["parser"]["name"] == "PyYAML"
        and len(selected) == 21 and set(report["parser"]["pins"]) == selected
        and Path(report["parser"]["root"]).resolve() == Path(distribution.locate_file("")).resolve(),"exact selected parser footprint")
    parser = Reader(report["parser"]["root"])
    for name,pin in report["parser"]["pins"].items(): parser.read(name,pin)
    require(Path(report["interpreter"]["executable"]).resolve() == Path(sys.executable).resolve(),"different interpreter")
    interpreter = Reader(Path(sys.executable).parent)
    for name,pin in report["interpreter"]["pins"].items(): interpreter.read(name,pin)
    independent=owned_module("src.staged_rts24_business_necessary_audit_v1","src/staged_rts24_business_necessary_audit_v1.py").verify
    for function,source in ((Reader.read,"experiments/staged_c_workflow_budget_v1.py"),
            (independent,"src/staged_rts24_business_necessary_audit_v1.py")):
        require(Path(function.__code__.co_filename).resolve() == ROOT/source,"function origin differs")
    for name,source in (("src","src/__init__.py"),("experiments","experiments/__init__.py")):
        owned_module(name,source)
    names = ("configs/staged_deliverability_rts24_v1.DRAFT.yaml","configs/staged_deliverability_small_case_v1.DRAFT.yaml",
        "configs/staged_deliverability_network_v1.DRAFT.yaml")
    inputs = {name:project.read(name,report["input_pins"][name]) for name in names}
    oracle = independent(inputs,dict(rows=report["rows"],summary=report["summary"]))
    require(oracle == report["oracle"],"saved oracle record differs")
    for name,module in list(sys.modules.items()):
        require(not any(name == p or name.startswith(p+".") for p in ("pyomo","pypower","highspy","gurobipy",
            "src.staged_rts24_development_v1")),"scientific import during postcheck")
        if name == "yaml" or name.startswith("yaml."):
            path = Path(module.__file__).resolve()
            require(path.is_relative_to(parser.root) and path.relative_to(parser.root).as_posix() in parser.pins,"parser provenance")
    for reader in (project,parser,interpreter): reader.bookend()
    require(not (ROOT/"results/tables/staged_rts24_native_v1_non_authoritative/p1_01").exists(),"P1 appeared")
    return dict(authority="DRAFT_NONAUTHORITATIVE",scope="independent_saved_arithmetic_readback",
        audit=dict(bytes=len(raw_report),sha256=sha256(raw_report).hexdigest()),oracle=oracle,
        all_input_parser_interpreter_hashes_matched=True,bookends=True,
        exact_project_and_parser_keysets_checked=True,project_module_and_function_origins_checked=True,
        bootstrap_sources_checked_before_helper_import=True,
        unique_project_inputs=len(project.pins)-1,parser_files=len(parser.pins),interpreter_files=len(interpreter.pins),
        explicit_bounded_reads=sum(r.operations for r in (project,parser,interpreter)),
        explicit_bounded_bytes=sum(r.bytes for r in (project,parser,interpreter)),
        wall_seconds=time.perf_counter()-started,native_calls=0,scientific_compiler_calls=0,
        p1_attempt_created=False,official_verdict=None,seal=None,receipt=None,formal_result=False)


if __name__ == "__main__":
    require(len(sys.argv) == 1,"no postcheck options")
    target = HERE/"verification_01.json"
    require(not target.exists(),"create-only verification exists")
    result = verify()
    with target.open("x",encoding="utf-8",newline="\n") as stream:
        json.dump(result,stream,sort_keys=True,separators=(",",":")); stream.write("\n")
    print(json.dumps(result,sort_keys=True))
