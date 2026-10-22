"""One bounded, non-authoritative B2 diagnostic; no optimization solver."""
import time

LAUNCH = time.perf_counter()

import argparse
import hashlib
import importlib
import importlib.metadata
import json
from math import isfinite
import os
from pathlib import Path
import platform
import subprocess
import stat
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import psutil

from src.staged_deliverability_development_v1 import assessment, plain, task_balances, _unique_pairs
from src.staged_network_development_v1 import (
    advance_network, initialize_network, load_case, load_config,
    read_network_checkpoint, save_network_checkpoint,
)
from src.staged_network_audit_v1 import audit_network

FIXTURE = ROOT / "configs/staged_deliverability_network_v1.DRAFT.yaml"
CONTRACT = ROOT / "docs/plan/staged_deliverability_b2_development_contract_v1.md"
BASE = ROOT / "results/tables/staged_deliverability_b2_v1_non_authoritative"
B1_REPORT = ROOT / "results/tables/staged_deliverability_b1_v1_non_authoritative/attempt_01/report.json"
CASES = (("on_time", "early"), ("on_time", "late"), ("delayed", "early"))
SCOPE = "B2 fixed_balance_DC_only"
LIMITS = dict(wall_seconds=60, child_seconds=15, sampled_tree_rss_bytes=512*1024**2,
              total_output_bytes=16*1024**2, single_file_bytes=2*1024**2)
EXPECTED = dict(pypower_flows=362, business_steps=50, network_attempts=52,
                child_processes=3, network_audit_hours=52, business_audit_hours=50,
                audited_pypower_points=362, input_loads=6)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def dump(path, value):
    data=json.dumps(plain(value),sort_keys=True,indent=2,allow_nan=False)+"\n"
    require(len(data.encode("utf-8"))<=LIMITS["single_file_bytes"],"single output size limit")
    with Path(path).open("x",encoding="utf-8",newline="\n") as stream:
        stream.write(data)


def flat_files(output):
    paths=sorted(output.iterdir())
    require(all(not p.is_symlink() and stat.S_ISREG(p.lstat().st_mode) for p in paths),
            "attempt must contain only regular files")
    return paths


def inventory(output):
    return {p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
            for p in flat_files(output) if p.name not in {"completion.json","completion.pending.json"}}


def verify_completion(output, supplemental=()):
    flat_files(output)
    marker=output/"completion.json"
    require(marker.stat().st_size<=LIMITS["single_file_bytes"],"completion size limit")
    saved=json.loads(marker.read_text(encoding="utf-8"),object_pairs_hook=_unique_pairs,
                     parse_constant=lambda v:require(False,"invalid completion JSON constant"))
    fields={"status","authority","scope","artifacts","artifact_bytes_before_completion",
            "elapsed_before_completion_write","sampled_process_tree_peak_rss_bytes"}
    require(isinstance(saved,dict) and set(saved)==fields,"completion schema differs")
    require(isinstance(saved["artifacts"],dict),"completion artifacts must be a map")
    for name,item in saved["artifacts"].items():
        require(isinstance(name,str) and name not in {".","..","completion.json","completion.pending.json"}
                and Path(name).name==name and not Path(name).is_absolute(),"invalid artifact name")
        require(isinstance(item,dict) and set(item)=={"bytes","sha256"},"artifact schema differs")
        require(type(item["bytes"]) is int and 0<=item["bytes"]<=LIMITS["single_file_bytes"],"invalid artifact size")
        require(isinstance(item["sha256"],str) and len(item["sha256"])==64
                and all(c in "0123456789abcdef" for c in item["sha256"]),"invalid artifact SHA")
    byte_sum=sum(v["bytes"] for v in saved["artifacts"].values())
    require(type(saved["artifact_bytes_before_completion"]) is int
            and saved["artifact_bytes_before_completion"]==byte_sum
            and byte_sum+marker.stat().st_size<=LIMITS["total_output_bytes"],"completion byte sum differs")
    elapsed=saved["elapsed_before_completion_write"]
    require(type(elapsed) in {int,float} and isfinite(elapsed) and 0<=elapsed<=LIMITS["wall_seconds"],
            "invalid completion elapsed")
    peak=saved["sampled_process_tree_peak_rss_bytes"]
    require(type(peak) is int and 0<=peak<=LIMITS["sampled_tree_rss_bytes"],"invalid completion RSS")
    require(not set(supplemental).intersection(saved["artifacts"]),"cannot exclude a bound artifact")
    actual={name:value for name,value in inventory(output).items() if name not in supplemental}
    require(saved["status"]=="development_diagnostic_completed" and saved["authority"]=="DRAFT_NONAUTHORITATIVE"
            and saved["scope"]==SCOPE
            and not (output/"failure.json").exists() and not (output/"completion.pending.json").exists()
            and saved["artifacts"]==actual,
            "B2 completion inventory differs")
    return saved


def fingerprints():
    reused=json.loads(B1_REPORT.read_text(encoding="utf-8"))["source_sha256"]
    for name,expected in reused.items():
        require(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,"B1 source pin changed: "+name)
    files={FIXTURE, CONTRACT, Path(__file__).resolve(), B1_REPORT,
           ROOT/"src/staged_network_development_v1.py",ROOT/"src/staged_network_audit_v1.py",
           ROOT/"tests/test_staged_network_development_v1.py",
           ROOT/"tests/test_staged_network_runner_v1.py",
           ROOT/"docs/model_spec/staged_deliverability_network_development_v1.md",
           *(ROOT/name for name in reused)}
    # Actual imported repository modules, not a claim of a hermetic dependency closure.
    for module in tuple(sys.modules.values()):
        filename=getattr(module,"__file__",None)
        if filename:
            path=Path(filename).resolve()
            if path.is_relative_to(ROOT) and path.suffix==".py": files.add(path)
    external={}
    for name in ("pypower.makeBdc","pypower.dcpf","pypower.pplinsolve",
                 "pypower.idx_bus","pypower.idx_brch","scipy.sparse.linalg._dsolve.linsolve",
                 "scipy.sparse.linalg._dsolve._superlu"):
        path=Path(importlib.import_module(name).__file__)
        external[name]=dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    return dict(repository_sha256={str(p.relative_to(ROOT)).replace("\\","/"):hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in sorted(files)}, external_selected=external,
                reused_b1_source_sha256=reused,
                versions={name:importlib.metadata.version(name) for name in ("numpy","scipy","PYPOWER","PyYAML","psutil")},
                python=sys.version,executable=sys.executable,platform=platform.platform())


def audit(p,state):
    return audit_network(plain(state.config),plain(p),plain(state))


def add_audit_counts(counts,report):
    for key,source in (("network_audit_hours","audited_network_hours"),
                       ("business_audit_hours","accepted_business_hours"),
                       ("audited_pypower_points","audited_pypower_points")):
        counts[key]=counts.get(key,0)+report[source]


def child(args):
    checkpoint,result=args.reopen.resolve(),args.result.resolve()
    stem=f"{args.plan}_{args.clean}"
    require(checkpoint.parent==result.parent==BASE.resolve()/"attempt_01"
            and checkpoint.name==stem+"_checkpoint.json" and result.name==stem+"_terminal.json",
            "child paths outside the dedicated declared attempt")
    require((args.plan,args.clean) in CASES,"undeclared child case")
    before=fingerprints()
    stages={}
    counts=dict(input_loads=1)

    def timed(name,operation):
        begin=time.perf_counter(); value=operation()
        stages[name]=time.perf_counter()-begin
        return value

    c=timed("configuration_load",lambda:load_config(FIXTURE))
    p,observations=timed("input_load",lambda:load_case(c,args.plan,args.clean))
    identity=f"{args.plan}:{args.clean}:B2"
    state=timed("checkpoint_read_and_prefix_replay",lambda:read_network_checkpoint(
        checkpoint,c,p,observations[:4],args.plan,identity,counts=counts))
    begin=time.perf_counter()
    for observation in observations[4:]:
        state=advance_network(p,state,observation,counts)
        if state.stopped: break
    stages["suffix_execution"]=time.perf_counter()-begin
    report=timed("independent_audit",lambda:audit(p,state))
    add_audit_counts(counts,report)
    after=timed("source_hash_after",fingerprints)
    require(before==after,"child source/environment drift")
    dump(result,dict(status="DRAFT_NONAUTHORITATIVE",scope=SCOPE,state=state,audit=report,
                     fingerprints_before=before,fingerprints_after=after,counts=counts,
                     stage_wall_seconds=stages,elapsed_before_terminal_write=time.perf_counter()-LAUNCH))


def run(output):
    output=output.resolve()
    require(output==BASE.resolve()/"attempt_01","output outside dedicated registered attempt_01")
    output.mkdir(parents=True,exist_ok=False)
    counts={key:0 for key in EXPECTED}
    stages={}
    peak=0
    current_child=None
    current_state=None
    child_returncodes=[]

    def guard(stage):
        nonlocal peak
        process=psutil.Process()
        rss=0
        for member in (process,*process.children(recursive=True)):
            try: rss+=member.memory_info().rss
            except psutil.NoSuchProcess: pass
        peak=max(peak,rss)
        files=[p.stat().st_size for p in flat_files(output)]
        elapsed=time.perf_counter()-LAUNCH
        if (elapsed>LIMITS["wall_seconds"] or rss>LIMITS["sampled_tree_rss_bytes"]
                or sum(files)>LIMITS["total_output_bytes"]
                or any(size>LIMITS["single_file_bytes"] for size in files)):
            raise RuntimeError("B2 resource limit at "+stage)
        return elapsed

    def event(stage):
        elapsed=guard(stage)
        with (output/"events.jsonl").open("a",encoding="utf-8",newline="\n") as stream:
            stream.write(json.dumps(dict(stage=stage,elapsed=elapsed,counts=counts))+"\n")

    def timed(name,operation):
        begin=time.perf_counter(); value=operation()
        stages[name]=stages.get(name,0)+time.perf_counter()-begin
        event(name)
        return value

    try:
        before=timed("source_hash_before",fingerprints)
        dump(output/"start.json",dict(status="DRAFT_NONAUTHORITATIVE",scope=SCOPE,
             fingerprints=before,limits=LIMITS,expected_counts=EXPECTED,
             contract=str(CONTRACT.relative_to(ROOT)),startup_through_start_record_seconds=time.perf_counter()-LAUNCH))
        c=timed("configuration_load",lambda:load_config(FIXTURE))
        summaries=[]
        for plan,clean in CASES:
            p,observations=timed("input_load",lambda:load_case(c,plan,clean))
            counts["input_loads"]+=1
            identity=f"{plan}:{clean}:B2"; stem=f"{plan}_{clean}"
            current_state=initialize_network(c,p,plan,identity,observations[0].hour)
            prefix=None
            begin=time.perf_counter()
            for observation in observations:
                current_state=advance_network(p,current_state,observation,counts)
                if observation.hour==1: prefix=current_state
                event(stem+":"+str(observation.hour))
                if current_state.stopped: break
            stages["continuous_execution"]=stages.get("continuous_execution",0)+time.perf_counter()-begin
            require(prefix is not None,"diagnostic did not reach its checkpoint")
            if plan=="delayed":
                require(current_state.records[-1]["status"]=="reference_connection_shortfall"
                        and current_state.records[-1]["hour"]==3,"unexpected delayed diagnostic outcome")
            else: require(not current_state.stopped,"unexpected on-time diagnostic stop")
            reference_audit=timed("parent_independent_audit",lambda:audit(p,current_state))
            add_audit_counts(counts,reference_audit)
            timed("reference_save",lambda:dump(output/(stem+"_reference.json"),
                                               dict(status="DRAFT_NONAUTHORITATIVE",scope=SCOPE,state=current_state,audit=reference_audit)))
            checkpoint=output/(stem+"_checkpoint.json"); terminal=output/(stem+"_terminal.json")
            timed("checkpoint_save",lambda:save_network_checkpoint(checkpoint,prefix))
            command=[sys.executable,"-B",str(Path(__file__).resolve()),"--reopen",str(checkpoint),
                     "--result",str(terminal),"--plan",plan,"--clean",clean]
            begin=time.perf_counter(); last_heartbeat=begin
            with (output/(stem+"_child.log")).open("xb") as log:
                current_child=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
                counts["child_processes"]+=1
                while current_child.poll() is None:
                    guard("fresh_child")
                    now=time.perf_counter()
                    if now-begin>LIMITS["child_seconds"]: raise TimeoutError("B2 fresh child exceeded 15 seconds")
                    if now-last_heartbeat>=1:
                        event(stem+":child_heartbeat"); last_heartbeat=now
                    time.sleep(.05)
                code=current_child.wait()
                child_returncodes.append(dict(case=stem,pid=current_child.pid,returncode=code))
                current_child=None
            require(code==0,"B2 child failed; inspect "+stem+"_child.log")
            stages["fresh_process_reopen_audit"]=stages.get("fresh_process_reopen_audit",0)+time.perf_counter()-begin
            saved=timed("terminal_read",lambda:json.loads(terminal.read_text(encoding="utf-8")))
            require(saved["status"]=="DRAFT_NONAUTHORITATIVE" and saved["scope"]==SCOPE
                    and saved["state"]==plain(current_state) and saved["audit"]==plain(reference_audit),
                    "fresh-process state/audit differs from continuous reference")
            require(saved["fingerprints_before"]==saved["fingerprints_after"]==before,"parent/child source drift")
            for key,value in saved["counts"].items(): counts[key]+=value
            summaries.append(dict(plan=plan,clean=clean,last_hour=current_state.records[-1]["hour"],
                 terminal_status=current_state.records[-1]["status"],accepted_hours=len(current_state.business.records),
                 business_prefix_assessment=assessment(current_state.business),tasks=task_balances(current_state.business),
                 full_contract_release=False,child_stage_wall_seconds=saved["stage_wall_seconds"]))
            event(stem+":compared")
        after=timed("source_hash_after",fingerprints)
        require(before==after,"parent source/environment drift")
        require(counts==EXPECTED,"actual work count differs from the registered DAG")
        dump(output/"report.json",dict(status="development_diagnostic_evaluated",authority="DRAFT_NONAUTHORITATIVE",
             scope=SCOPE,counts=counts,stage_wall_seconds=stages,fingerprints=after,
             elapsed_before_report_write=guard("report"),sampled_process_tree_peak_rss_bytes=peak,
             child_returncodes=child_returncodes,summaries=summaries,
             main_experiment_performance_review_complete=False,aggregate_contract_release=False,
             unknown="general network/SCED/AC; temporal full-C backing; expensive I/O failure cleanup; main experiment budget"))
        event("pre_completion")
        artifacts=inventory(output)
        completion=dict(status="development_diagnostic_completed",authority="DRAFT_NONAUTHORITATIVE",scope=SCOPE,
                        artifacts=artifacts,artifact_bytes_before_completion=sum(v["bytes"] for v in artifacts.values()),
                        elapsed_before_completion_write=guard("completion"),sampled_process_tree_peak_rss_bytes=peak)
        completion_bytes=len((json.dumps(completion,sort_keys=True,indent=2,allow_nan=False)+"\n").encode("utf-8"))
        require(completion["artifact_bytes_before_completion"]+completion_bytes<=LIMITS["total_output_bytes"],
                "completion would exceed total output budget")
        dump(output/"completion.pending.json",completion)
        require(not (output/"completion.json").exists(),"completion already exists")
        os.rename(output/"completion.pending.json",output/"completion.json")
        verify_completion(output)
    except BaseException as error:
        if current_child is not None:
            if current_child.poll() is None: current_child.kill()
            current_child.wait(timeout=5)
            child_returncodes.append(dict(pid=current_child.pid,returncode=current_child.returncode))
        dump(output/"failure.json",dict(status="development_diagnostic_failed",error=str(error),counts=counts,
             elapsed_seconds=time.perf_counter()-LAUNCH,child_returncodes=child_returncodes,last_state=current_state))
        raise
    print(json.dumps(dict(status="development_diagnostic_completed",counts=counts,
                          elapsed_seconds=time.perf_counter()-LAUNCH,output=str(output))))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path)
    parser.add_argument("--reopen",type=Path)
    parser.add_argument("--result",type=Path)
    parser.add_argument("--plan",choices=("on_time","delayed"))
    parser.add_argument("--clean",choices=("early","late"))
    args=parser.parse_args()
    if args.reopen:
        require(args.result is not None,"child result path required"); child(args)
    elif args.output: run(args.output)
    else: parser.error("--output or --reopen required")


if __name__=="__main__": main()
