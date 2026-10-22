"""Create one bounded, metadata-only report projection; execute verified source bytes."""
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"results/tables/staged_deliverability_evaluation_records_v1_non_authoritative/projection_01"
HELPER="experiments/staged_c_workflow_budget_v1.py"
HELPER_SHA="5bc19005ef1f0812a7d566dfc30bb6cef05f43ef21b9ed4f50262917034cfa82"
CORE="src/staged_deliverability_evaluation_records_v1.py"
SOURCES=(CORE,"experiments/staged_deliverability_evaluation_projection_v1.py",
    "tests/test_staged_deliverability_evaluation_records_v1.py",
    "docs/plan/staged_deliverability_de_evidence_fields_contract_v1.md",
    "results/tables/staged_deliverability_evaluation_records_v1_non_authoritative/postcheck.py")
PINS={
    "results/tables/staged_rts24_journal_v1_non_authoritative/attempt_01/report.json":"2540cde1d16f68971e3fa39191af543c166539c6bc4e6725459bfec3d786a7d4",
    "results/tables/staged_rts24_append_cost_v1_non_authoritative/cost_probe_01/report.json":"7d974a2fe6d34009465be54601524104395e9a301299f9fd2a9dc327369b0c11",
    "results/tables/staged_rts24_business_necessary_v1_non_authoritative/audit_01/audit.json":"c55fbc77676e22ac8aff91f09d801fdc83e4ae0838b47bd215cadfe7637f708d",
    "docs/model_spec/staged_deliverability_minimum_spec_v1.md":"024841d9a13116651d353d1e1f81e1b4bc68de512208e2cb80137e8ca7b77045",
    "docs/plan/staged_deliverability_b3_c_next_steps_v1.md":"208cdf5549142b8219b02a5bc1836d9ca389ac87f3d7d01377e656cf75487f7d",
}


def require(ok,message):
    if not ok:raise ValueError(message)


def verified_namespace(raw,name,path):
    """Compile the bytes already read/hashed, without package or .pyc execution."""
    space=dict(__name__=name,__file__=str(path))
    exec(compile(raw,str(path),"exec"),space)
    return space


def bounded_helper():
    path=ROOT/HELPER
    for parent in (path,*path.parents):
        info=parent.lstat()
        require(not stat.S_ISLNK(info.st_mode) and not getattr(info,"st_file_attributes",0)&0x400,"linked helper")
        if parent == ROOT:break
    before=path.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_size<65536,"helper size/type")
    with path.open("rb") as stream:
        opened=os.fstat(stream.fileno());raw=stream.read(before.st_size+1);after=os.fstat(stream.fileno())
    require(os.path.samestat(before,opened) and os.path.samestat(opened,path.stat())
        and before.st_size == after.st_size == len(raw) and sha256(raw).hexdigest() == HELPER_SHA,"helper SHA before execution")
    return raw


def publish(payload,out,started):
    require(len(payload)<=1024**2 and time.perf_counter()-started<20,"projection size/time cap")
    require(not out.exists(),"create-only output exists")
    for parent in out.parents:
        if parent.exists():require(parent.resolve()==parent and not getattr(parent.stat(),"st_file_attributes",0)&0x400,"linked output parent")
    out.mkdir(parents=True,exist_ok=False)
    with (out/"projection.json").open("xb") as stream:require(stream.write(payload)==len(payload),"short projection write")
    require((out/"projection.json").read_bytes()==payload,"projection readback differs")
    require(time.perf_counter()-started<20,"terminal wall cap; preserve output")


def main():
    started=time.perf_counter()
    require(Path.cwd().resolve()==ROOT and sys.dont_write_bytecode and sys.flags.no_user_site==1
        and __package__ in (None,""),"fixed root/cwd file-path -B -s CLI required")
    require(not OUT.exists(),"create-only output exists")
    raw_helper=bounded_helper()
    Reader=verified_namespace(raw_helper,"_verified_projection_reader",ROOT/HELPER)["Reader"]
    class LimitedReader(Reader):
        def read(self,name,expected=None):
            require(self.operations<40 and self.bytes+(self.root/name).stat().st_size<=4*1024**2
                and time.perf_counter()-started<20,"projection read/time cap")
            return super().read(name,expected)
    reader=LimitedReader(ROOT)
    raw_sources={name:reader.read(name) for name in SOURCES}
    reader.read(HELPER,HELPER_SHA)
    raw_inputs={name:reader.read(name,digest) for name,digest in PINS.items()}
    interpreter=LimitedReader(Path(sys.executable).parent)
    interpreter.read(Path(sys.executable).name)
    core=verified_namespace(raw_sources[CORE],"_verified_evaluation_projection",ROOT/CORE)
    bound_at=time.perf_counter()
    reports={name:raw_inputs[name] for name in core["REPORTS"]}
    value=core["project"](reports)
    projected_at=time.perf_counter()
    reader.bookend()
    interpreter.bookend()
    operations=reader.operations+interpreter.operations
    byte_count=reader.bytes+interpreter.bytes
    require(operations<=40 and byte_count<=4*1024**2,"projection explicit read budget")
    require(not (ROOT/"results/tables/staged_rts24_native_v1_non_authoritative/p1_01").exists(),"P1 must remain absent")
    require(not any(name==p or name.startswith(p+".") for name in sys.modules
        for p in ("pyomo","pypower","highspy","yaml")),"scientific/parser import forbidden")
    value.update(input_pins=reader.pins,source_bookends=True,
        execution=dict(exact_verified_source_bytes=True,python=sys.version,executable=sys.executable,
            interpreter_pins=interpreter.pins,environment_scope="selected_executable_and_stdlib_use_not_full_environment_seal",
            no_user_site=sys.flags.no_user_site,dont_write_bytecode=sys.dont_write_bytecode,argv=list(sys.orig_argv),
            scientific_compiler_calls=0,native_calls=0,journal_reopen_calls=0,model_builds=0,
            explicit_reader_reads=operations,explicit_reader_bytes=byte_count,
            bootstrap_reads=1,bootstrap_bytes=len(raw_helper),
            io_scope="explicit Reader and helper bootstrap; imports OS loads output readback not counted",
            input_and_source_binding_seconds=bound_at-started,projection_seconds=projected_at-bound_at,
            bookend_seconds=time.perf_counter()-projected_at,prepublication_body_seconds=time.perf_counter()-started))
    raw=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()+b"\n"
    publish(raw,OUT,started)
    return dict(sha256=sha256(raw).hexdigest(),bytes=len(raw),body_wall_seconds=time.perf_counter()-started,
        saved_views=len(value["mechanism_regressions"]),public_business_rows=len(value["public_layers"]["one_hour_business_necessary"]["rows"]),
        explicit_reader_reads=operations,explicit_reader_bytes=byte_count,bootstrap_reads=1)


if __name__=="__main__":
    require(len(sys.argv)==1,"fixed projection scope; no options")
    print(json.dumps(main(),sort_keys=True))
