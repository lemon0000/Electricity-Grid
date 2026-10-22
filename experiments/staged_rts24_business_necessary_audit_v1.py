"""One create-only, bounded exact arithmetic audit. No scientific construction."""
from hashlib import sha256
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import stat
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/"results/tables/staged_rts24_business_necessary_v1_non_authoritative"
OUT = BASE/"audit_01"
SOURCES = (
    "src/staged_rts24_business_necessary_v1.py",
    "src/staged_rts24_business_necessary_audit_v1.py",
    "experiments/staged_rts24_business_necessary_audit_v1.py",
    "tests/test_staged_rts24_business_necessary_v1.py",
    "docs/plan/staged_deliverability_c_business_necessary_audit_contract_v1.md",
)
CONTEXT = {
    "src/staged_rts24_development_v1.py":"d0c61bda61bfe4d275d2230533f2ecd74fa4fbf480f358c819f8cb86e1ba7add",
    "experiments/staged_c_workflow_budget_v1.py":"5bc19005ef1f0812a7d566dfc30bb6cef05f43ef21b9ed4f50262917034cfa82",
    "docs/model_spec/staged_deliverability_network_development_v1.md":"2ebc49850224bf513568c945b51abaf6dc1d6c23b80c7251ab185208b118fdbb",
}
CONFIGS = {
    "configs/staged_deliverability_rts24_v1.DRAFT.yaml":"6897979b6394a20b406031e9bcc8fadf5751c7815c996dc177956535679b7791",
    "configs/staged_deliverability_small_case_v1.DRAFT.yaml":"5b334398b2894da70c81baaad74da2dfcecde490ab539bacf3fdb0c988eb4ac5",
    "configs/staged_deliverability_network_v1.DRAFT.yaml":"c6bb0cc30a330fed07a9d0b7f22dea7ce5096f20f1f58a8dc79dddc58059686b",
}
FORBIDDEN = ("pyomo", "pypower", "highspy", "gurobipy", "src.staged_rts24_development_v1")
BOOTSTRAP = {
    "src/__init__.py":"ad4caa31a8bd5d534f5c65b38b67a393b740a5efd947988f47e1b55642c4cfc0",
    "experiments/__init__.py":"f67a437b3910b0400486a45167d0001163081e3b8b3f1d6166df4e3a3adf3581",
    "experiments/staged_c_workflow_budget_v1.py":CONTEXT["experiments/staged_c_workflow_budget_v1.py"],
}


def require(condition, message):
    if not condition: raise ValueError(message)


def owned_module(name, source):
    module = importlib.import_module(name)
    require(Path(module.__file__).resolve() == ROOT/source, "imported module differs from pinned repo path")
    return module


def fresh_scope(package, modules):
    require(package in (None,"") and not any(name == p or name.startswith(p+".")
        for name in modules for p in ("src","experiments","yaml")),"file-path CLI and fresh repo/parser module scope required")


def bootstrap_sources():
    """Read/hash the helper and package entries without importing repo packages."""
    pins={}
    for name,digest in BOOTSTRAP.items():
        path=ROOT/name
        require(path.resolve(strict=True).is_relative_to(ROOT),"bootstrap path escaped")
        for parent in (path,*path.parents):
            info=parent.lstat()
            require(not stat.S_ISLNK(info.st_mode) and not getattr(info,"st_file_attributes",0)&0x400,"linked bootstrap source")
            if parent == ROOT:break
        before=path.stat()
        require(stat.S_ISREG(before.st_mode) and before.st_size <= 2*1024**2,"bootstrap size/type")
        with path.open("rb") as stream:
            opened=os.fstat(stream.fileno())
            require(os.path.samestat(before,opened),"bootstrap replaced before read")
            raw=stream.read(before.st_size+1)
            after=os.fstat(stream.fileno())
        require(os.path.samestat(opened,path.stat()) and after.st_size == before.st_size == len(raw)
            and sha256(raw).hexdigest() == digest,"bootstrap source SHA differs before import")
        pins[name]=dict(bytes=len(raw),sha256=digest)
    return pins


def publish(payload, out, started):
    """Create-only development artifact; every post-mkdir failure preserves output."""
    require(len(payload) <= 1024**2 and time.perf_counter()-started < 30, "output/time cap")
    require(not out.exists(), "create-only audit output exists")
    for parent in out.parents:
        if parent.exists():
            require(parent.resolve() == parent and not getattr(parent.stat(),"st_file_attributes",0)&0x400, "linked output parent")
    out.mkdir(parents=True,exist_ok=False)
    with (out/"audit.json").open("xb") as stream:
        require(stream.write(payload) == len(payload), "short output write")
    require((out/"audit.json").read_bytes() == payload, "output readback differs")
    require(time.perf_counter()-started < 30, "cooperative terminal wall cap; preserve output")
    return dict(sha256=sha256(payload).hexdigest(),bytes=len(payload),wall_seconds=time.perf_counter()-started)


def audit(root=ROOT):
    started = time.perf_counter()
    require(Path(root).resolve() == Path.cwd().resolve() == ROOT and sys.dont_write_bytecode
        and sys.flags.no_user_site == 1, "fixed root/cwd and -B -s required")
    fresh_scope(__package__,sys.modules)
    require(not OUT.exists(), "create-only audit output exists")
    sys.path.insert(0,str(ROOT))
    bootstrap=bootstrap_sources()
    helper = owned_module("experiments.staged_c_workflow_budget_v1","experiments/staged_c_workflow_budget_v1.py")
    Reader = helper.Reader

    class LimitedReader(Reader):
        def read(self, name, expected=None):
            require(self.operations < 160 and self.bytes+(self.root/name).stat().st_size <= 4*1024**2
                and time.perf_counter()-started < 30, "local arithmetic audit read/time cap")
            raw = super().read(name,expected)
            require(time.perf_counter()-started < 30, "cooperative total wall cap")
            return raw

    project = LimitedReader(root)
    for name in (*SOURCES, "src/__init__.py", "experiments/__init__.py"):
        project.read(name,bootstrap.get(name))
    for name,digest in CONTEXT.items(): project.read(name,digest)
    raw = {name:project.read(name,digest) for name,digest in CONFIGS.items()}
    # Resolve and bind the selected parser bytes before loading yaml or either implementation.
    distribution = importlib.metadata.distribution("PyYAML")
    require(distribution.version == "6.0.3", "only observed parser version")
    parser = LimitedReader(distribution.locate_file(""))
    parser_names = sorted(str(p).replace("\\","/") for p in distribution.files
        if (str(p).replace("\\","/").startswith("yaml/") and str(p).endswith((".py",".pyd")))
        or (".dist-info/" in str(p).replace("\\","/") and p.name in ("METADATA","RECORD","WHEEL")))
    require(len(parser_names) == 21 and len(set(parser_names)) == 21, "only selected parser footprint")
    for name in parser_names: parser.read(name)
    interpreter = LimitedReader(Path(sys.executable).parent)
    interpreter.read(Path(sys.executable).name)
    pinned_at = time.perf_counter()
    primary = owned_module("src.staged_rts24_business_necessary_v1",SOURCES[0])
    independent = owned_module("src.staged_rts24_business_necessary_audit_v1",SOURCES[1])
    for function,source in ((Reader.read,"experiments/staged_c_workflow_budget_v1.py"),
            (primary.evaluate,SOURCES[0]),(independent.verify,SOURCES[1])):
        require(Path(function.__code__.co_filename).resolve() == ROOT/source, "executed function origin differs")
    for name,source in (("src","src/__init__.py"),("experiments","experiments/__init__.py")):
        owned_module(name,source)
    value = primary.evaluate(raw)
    computed_at = time.perf_counter()
    oracle = independent.verify(raw,value)
    checked_at = time.perf_counter()
    for name,module in list(sys.modules.items()):
        require(not any(name == bad or name.startswith(bad+".") for bad in FORBIDDEN), "scientific import forbidden")
        if name == "yaml" or name.startswith("yaml."):
            file = Path(module.__file__).resolve()
            require(file.is_relative_to(parser.root) and file.relative_to(parser.root).as_posix() in parser.pins, "unpinned parser import")
    for reader in (project,parser,interpreter): reader.bookend()
    require(not (ROOT/"results/tables/staged_rts24_native_v1_non_authoritative/p1_01").exists(), "P1 must remain absent")
    result = dict(authority="DRAFT_NONAUTHORITATIVE",review_stage="PRE_SEAL_AUDIT",
        scope="source_bound_public_business_one_hour_necessary_relaxations",**value,oracle=oracle,
        provenance=dict(audit_identity_kind="independent_arithmetic_not_Fixture_source_identity",
            case_metadata="PYPOWER 5.1.19 case24_ieee_rts as declared in pinned public YAML; not reconstructed",
            business_and_rights="mechanism_assumptions_not_empirical_parameters",rows=40,
            dimensions="2 grid plans x 2 development clean paths x 10 hours; no method dimension",
            actual_workload="bound for reference only; full-C w_hat is counterfactual",
            joint_premise="hypothetical simultaneous whole-X and full-C CFE with independent_additive_calls; event eligibility not evaluated",
            normal_premise="hypothetical full-C with g=0; not a network normal-C point",
            unknown_g="nonempty interval only means not ruled out by this one-hour business relaxation; no g selected",
            reference_shortfall="fixed reference policy admission screen, not all-policy infeasibility"),
        input_pins=project.pins,parser=dict(name="PyYAML",version=distribution.version,root=str(parser.root),pins=parser.pins),
        interpreter=dict(python=sys.version,executable=sys.executable,pins=interpreter.pins,
            no_user_site=sys.flags.no_user_site,dont_write_bytecode=sys.dont_write_bytecode,argv=list(sys.orig_argv)),
        counters=dict(primary_rows=40,independent_rows=40,scientific_compiler_calls=0,model_builds=0,native_calls=0,
            explicit_bounded_reads=sum(r.operations for r in (project,parser,interpreter)),
            explicit_bounded_bytes=sum(r.bytes for r in (project,parser,interpreter))),
        read_accounting_scope="explicit Reader calls only; import machinery, metadata discovery, OS loads and output readback not counted",
        bootstrap=dict(pins=bootstrap,explicit_reads=len(bootstrap),explicit_bytes=sum(p["bytes"] for p in bootstrap.values())),
        phases_seconds=dict(input_binding=pinned_at-started,primary=computed_at-pinned_at,independent_oracle=checked_at-computed_at,
            bookend_and_metadata=time.perf_counter()-checked_at),
        prepublication_wall_seconds=time.perf_counter()-started,source_and_environment_bookends=True,
        imported_project_module_paths_checked=True,fixed_repository_cwd=True,
        actual_trajectory=None,raw_network_g=None,normal_C_network_point=None,fault_F_network_points=None,
        complete_139_network_conditions=None,complete_temporal_backing=None,capacity_release=None,
        overall_performance_review_complete=False,resource_admission=False,formal_result=False)
    payload = json.dumps(result,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")+b"\n"
    publication = publish(payload,OUT,started)
    return dict(rows=40,oracle=oracle,**publication,counters=result["counters"])


if __name__ == "__main__":
    require(len(sys.argv) == 1, "fixed scope; no CLI options")
    print(json.dumps(audit(),sort_keys=True))
