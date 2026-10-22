"""Bounded B3 journal/termination diagnostic; see its registered development DAG."""
import time

LAUNCH=time.perf_counter()

import argparse
from fractions import Fraction as Q
import hashlib
import json
from math import isfinite
import os
from pathlib import Path
import stat
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

import psutil
import experiments.staged_network_b2_development_v1 as prior
import src.staged_network_development_v1 as network
import src.staged_termination_development_v1 as journal
from src.staged_deliverability_development_v1 import plain
from src.staged_network_audit_v1 import audit_network

BASE=ROOT/"results/tables/staged_deliverability_b3_v1_non_authoritative"
FIXTURE=ROOT/"configs/staged_deliverability_network_v1.DRAFT.yaml"
CONTRACT=ROOT/"docs/plan/staged_deliverability_b3_development_contract_v1.md"
CASES={"on_time_early":("on_time","early"),"on_time_late":("on_time","late"),"delayed_early":("delayed","early")}
PROBES=("missing_input","network_unresolved","save_before_publish","save_after_publish")
LIMITS=dict(wall_seconds=60,child_seconds=15,tree_rss_bytes=512*1024**2,total_bytes=32*1024**2,single_bytes=2*1024**2)
EXPECTED=dict(pypower_flows=599,business_steps=84,network_attempts=86,child_processes=3,input_loads=10,
              independent_audit_calls=17,network_audit_calls=19,network_audit_hours=107,business_audit_hours=103,
              extra_business_audit_step_visits=8,point_audit_visits=745,
              journal_publish_calls=59,journal_publish_return_success=57,journal_publish_errors=2)


def require(value,message):
    if not value: raise ValueError(message)


def fingerprints():
    result=prior.fingerprints()
    extras=(Path(__file__).resolve(),CONTRACT,ROOT/"docs/model_spec/staged_termination_development_v1.md",
            ROOT/"src/staged_termination_development_v1.py",ROOT/"src/staged_termination_audit_v1.py",
            ROOT/"tests/test_staged_termination_development_v1.py",ROOT/"tests/test_staged_termination_runner_v1.py",
            ROOT/"results/tables/staged_deliverability_b2_v1_non_authoritative/attempt_01/report.json",
            ROOT/"results/tables/staged_deliverability_b2_v1_non_authoritative/attempt_01/completion.json")
    result["repository_sha256"].update({str(p.relative_to(ROOT)).replace("\\","/"):hashlib.sha256(p.read_bytes()).hexdigest() for p in extras})
    return result


def meter(counts):
    original_encode,original_publish=journal.encoded,journal.publish

    def encode(value):
        data=original_encode(value)
        counts["writer_canonical_encode_calls"]=counts.get("writer_canonical_encode_calls",0)+1
        counts["writer_canonical_bytes"]=counts.get("writer_canonical_bytes",0)+len(data)
        if isinstance(value,network.NetworkState):
            counts["state_digest_record_visits"]=counts.get("state_digest_record_visits",0)+len(value.records)
        return data

    def publish(*args,**kwargs):
        counts["journal_publish_calls"]+=1
        try:
            result=original_publish(*args,**kwargs)
            counts["journal_publish_return_success"]+=1
            return result
        except BaseException:
            counts["journal_publish_errors"]+=1
            raise

    journal.encoded,journal.publish=encode,publish
    return lambda:setattr(journal,"encoded",original_encode),lambda:setattr(journal,"publish",original_publish)


def files(output,sampling=False):
    result=[]
    for path in sorted(output.iterdir()):
        require(not path.is_symlink(),"symlink in diagnostic output")
        if path.is_dir():
            require(path.name in {*CASES,*PROBES},"undeclared diagnostic directory")
            result.extend(path.iterdir() if sampling else journal.entries(path))
        else:
            require(stat.S_ISREG(path.lstat().st_mode),"nonregular diagnostic output")
            result.append(path)
    return result


def sampled_sizes(output):
    sizes=[]
    for path in files(output,sampling=True):
        try: info=path.lstat()
        except FileNotFoundError: continue  # Child may have renamed a pending file.
        require(stat.S_ISREG(info.st_mode) and not path.is_symlink(),"nonregular diagnostic output")
        sizes.append(info.st_size)
    return sizes


def inventory(output,supplemental=()):
    omitted={"completion.json","completion.pending.json",*supplemental}
    return {str(p.relative_to(output)).replace("\\","/"):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
            for p in files(output) if str(p.relative_to(output)).replace("\\","/") not in omitted}


def expected_artifact_paths():
    names={"start.json","report.json","events.jsonl"}
    for stem in CASES:
        names.update(stem+suffix for suffix in ("_reference.json","_terminal.json","_child.log"))
        accepted=5 if stem=="delayed_early" else 10
        names.update(f"{stem}/step_{i:04d}.json" for i in range(accepted))
        names.update(stem+"/"+name for name in ("genesis.json","checkpoint.json","terminal.json"))
        if stem=="delayed_early": names.add(stem+"/attempt.json")
    for stem in PROBES:
        names.add(stem+"_probe.json"); names.add(stem+"/genesis.json")
        accepted=3 if stem=="network_unresolved" else 5 if stem=="save_after_publish" else 4
        names.update(f"{stem}/step_{i:04d}.json" for i in range(accepted))
        if stem in {"missing_input","network_unresolved"}: names.add(stem+"/terminal.json")
        if stem=="network_unresolved": names.add(stem+"/attempt.json")
        if stem=="save_before_publish": names.add(stem+"/step_0004.json.pending")
    return names


def verify_completion(output,supplemental=()):
    value=journal.read_json(output/"completion.json")
    require(set(value)=={"status","authority","scope","artifacts","artifact_bytes_before_completion",
                        "elapsed_before_completion_write","sampled_process_tree_peak_rss_bytes"},"completion schema differs")
    require(value["status"]=="development_diagnostic_completed" and value["authority"]=="DRAFT_NONAUTHORITATIVE"
            and value["scope"]==journal.SCOPE,"completion status/scope differs")
    require(isinstance(value["artifacts"],dict) and not set(supplemental).intersection(value["artifacts"]),"invalid inventory exclusions")
    actual=inventory(output,supplemental)
    require(set(actual)==expected_artifact_paths(),"registered artifact roles differ")
    for item in value["artifacts"].values():
        require(set(item)=={"bytes","sha256"} and type(item["bytes"]) is int and 0<=item["bytes"]<=LIMITS["single_bytes"],"invalid inventory size")
        require(isinstance(item["sha256"],str) and len(item["sha256"])==64
                and all(c in "0123456789abcdef" for c in item["sha256"]),"invalid inventory SHA")
    require(value["artifacts"]==actual and type(value["artifact_bytes_before_completion"]) is int
            and value["artifact_bytes_before_completion"]==sum(v["bytes"] for v in actual.values()),"completion inventory differs")
    elapsed,peak=value["elapsed_before_completion_write"],value["sampled_process_tree_peak_rss_bytes"]
    require(type(elapsed) in {int,float} and isfinite(elapsed) and 0<=elapsed<=LIMITS["wall_seconds"],"completion elapsed differs")
    require(type(peak) is int and 0<=peak<=LIMITS["tree_rss_bytes"],"completion memory differs")
    require(sum(p.stat().st_size for p in files(output))<=LIMITS["total_bytes"]
            and not (output/"failure.json").exists() and not (output/"completion.pending.json").exists(),"incomplete diagnostic")
    return value


def input_case(c,plan,clean,counts):
    counts["input_loads"]+=1
    return network.load_case(c,plan,clean)


def reference_audit(c,p,state,counts):
    counts["independent_audit_calls"]+=1; counts["network_audit_calls"]+=1
    result=audit_network(plain(c),plain(p),plain(state))
    for metric,key in (("network_audit_hours","audited_network_hours"),("business_audit_hours","accepted_business_hours"),
                       ("point_audit_visits","audited_pypower_points")):
        counts[metric]+=result[key]
    return result


def check_child_exit(begin,code):
    require(time.perf_counter()-begin<=LIMITS["child_seconds"],"B3 child time limit")
    require(code==0,"B3 child failed")


def accepted_snapshot(session):
    return dict(scope="last_verified_prefix",journal_root=str(session.root),head_sha=session.head_sha,state_sha=session.state_sha,state=plain(session.state))


def child(stem):
    require(stem in CASES,"undeclared child")
    output=BASE/"attempt_01"; plan,clean=CASES[stem]
    counts={k:0 for k in EXPECTED}; restores=meter(counts)
    try:
        before=fingerprints(); c=network.load_config(FIXTURE)
        p,obs=input_case(c,plan,clean,counts); identity=stem+":B3"
        begin=time.perf_counter()
        s=journal.reopen(output/stem,c,p,obs[:4],plan,identity,counts=counts)
        replay_wall=time.perf_counter()-begin
        require(s.reason is None and not s.closed,"checkpoint did not reopen for suffix")
        begin=time.perf_counter()
        for o in obs[4:]:
            s=journal.commit_hour(s,o,counts)
            if s.reason: break
        suffix_wall=time.perf_counter()-begin
        begin=time.perf_counter(); s=journal.finish(s,counts=counts); finish_wall=time.perf_counter()-begin
        require(s.reason==("policy_or_admission_rejected" if plan=="delayed" else "observation_complete") and s.audit_validity=="passed", "unexpected child termination")
        after=fingerprints(); require(before==after,"child fingerprints changed")
        prior.dump(output/(stem+"_terminal.json"),dict(status="DRAFT_NONAUTHORITATIVE",scope=journal.SCOPE,
            summary=journal.summary(s),state=s.state,audit=s.audit_result,counts=counts,fingerprints=after,
            stage_wall_seconds=dict(replay_and_audit=replay_wall,suffix_and_publications=suffix_wall,finish_audit_and_terminal=finish_wall)))
    finally:
        for restore in restores: restore()


def run(output):
    output=Path(output).resolve()
    require(output==BASE.resolve()/"attempt_01","only the registered B3 attempt_01 is allowed")
    output.mkdir(parents=True,exist_ok=False)
    counts={k:0 for k in EXPECTED}; restores=meter(counts)
    stages={}; peak=0; current_child=None; last_session=None; last_verified_accepted=None
    current_phase="initializing"; child_evidence=None; children=[]

    def guard(stage):
        nonlocal peak
        parent=psutil.Process(); rss=0
        for member in (parent,*parent.children(recursive=True)):
            try: rss+=member.memory_info().rss
            except psutil.NoSuchProcess: pass
        peak=max(peak,rss); sizes=sampled_sizes(output)
        elapsed=time.perf_counter()-LAUNCH
        require(elapsed<=LIMITS["wall_seconds"] and rss<=LIMITS["tree_rss_bytes"] and sum(sizes)<=LIMITS["total_bytes"]
                and all(v<=LIMITS["single_bytes"] for v in sizes),"B3 resource limit at "+stage)
        return elapsed

    def event(stage):
        elapsed=guard(stage)
        with (output/"events.jsonl").open("a",encoding="utf-8",newline="\n") as stream:
            stream.write(json.dumps(dict(stage=stage,elapsed=elapsed,counts=counts))+"\n")

    def timed(name,call):
        nonlocal current_phase,last_session,last_verified_accepted
        current_phase=name
        begin=time.perf_counter()
        try: value=call()
        except (journal.ReopenError,journal.CreateError) as error:
            last_session=error.session
            if isinstance(error,journal.ReopenError) and last_session.genesis_sha and last_session.head_sha:
                last_verified_accepted=accepted_snapshot(last_session)
            raise
        if isinstance(value,journal.Session):
            last_session=value; last_verified_accepted=accepted_snapshot(value)
        stages[name]=stages.get(name,0)+time.perf_counter()-begin; event(name)
        return value

    try:
        before=timed("fingerprints_before",fingerprints)
        prior.dump(output/"start.json",dict(status="DRAFT_NONAUTHORITATIVE",scope=journal.SCOPE,fingerprints=before,
                                          limits=LIMITS,expected_counts=EXPECTED,contract=str(CONTRACT.relative_to(ROOT))))
        c=network.load_config(FIXTURE); summaries=[]
        for stem,(plan,clean) in CASES.items():
            p,obs=input_case(c,plan,clean,counts); identity=stem+":B3"
            last_session=timed("create_journal",lambda:journal.create_session(output/stem,c,p,plan,identity))
            for o in obs[:4]: last_session=timed("prefix_commit",lambda:journal.commit_hour(last_session,o,counts))
            closed=timed("checkpoint_close",lambda:journal.checkpoint_and_close(last_session))
            require(closed.closed and closed.reason is None,"checkpoint close failed")
            reference=last_session.state
            for o in obs[4:]:
                reference=timed("continuous_reference_suffix",lambda:network.advance_network(p,reference,o,counts))
                if reference.stopped: break
            audited=timed("reference_audit",lambda:reference_audit(c,p,reference,counts))
            prior.dump(output/(stem+"_reference.json"),dict(state=reference,audit=audited,status="DRAFT_NONAUTHORITATIVE",scope="B2 pure-memory reference for B3"))
            begin=time.perf_counter(); heartbeat=begin
            with (output/(stem+"_child.log")).open("xb") as log:
                current_phase=stem+":fresh_child"
                current_child=subprocess.Popen([sys.executable,"-B",str(Path(__file__).resolve()),"--child",stem],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
                child_evidence=dict(case=stem,pid=current_child.pid,log=stem+"_child.log",returncode=None)
                counts["child_processes"]+=1
                while current_child.poll() is None:
                    guard("fresh_child"); now=time.perf_counter()
                    require(now-begin<=LIMITS["child_seconds"],"B3 child time limit")
                    if now-heartbeat>=1: event(stem+":heartbeat"); heartbeat=now
                    time.sleep(.05)
                code=current_child.wait(); child_evidence["returncode"]=code
                children.append(dict(case=stem,pid=current_child.pid,returncode=code)); current_child=None
            check_child_exit(begin,code); guard("child_exit")
            stages["fresh_process_reopen_suffix"]=stages.get("fresh_process_reopen_suffix",0)+time.perf_counter()-begin
            saved=journal.read_json(output/(stem+"_terminal.json"))
            comparable=json.loads(json.dumps(saved["state"]))
            row=(saved["summary"]["pending"] or {}).get("b2_candidate_record")
            if row is not None: comparable["records"].append(row); comparable["stopped"]=True
            require(comparable==plain(reference) and saved["audit"]["network_audit"]==plain(audited)
                    and saved["fingerprints"]==before,"child/reference evidence differs")
            last_verified_accepted=dict(scope="last_verified_prefix",journal_root=str(output/stem),head_sha=saved["summary"]["head_sha"],
                                        state_sha=saved["summary"]["state_sha"],state=saved["state"])
            for key,value in saved["counts"].items(): counts[key]=counts.get(key,0)+value
            summaries.append(dict(case=stem,reason=saved["summary"]["termination_reason"],
                                  accepted_hour=saved["summary"]["last_accepted_hour"],child_stage_wall_seconds=saved["stage_wall_seconds"]))
            event(stem+":compared")
        for stem in PROBES:
            p,obs=input_case(c,"on_time","early",counts); identity=stem+":B3"
            s=timed("probe_create",lambda:journal.create_session(output/stem,c,p,"on_time",identity))
            length=3 if stem=="network_unresolved" else 4
            for o in obs[:length]: s=timed("probe_prefix_commit",lambda:journal.commit_hour(s,o,counts))
            witness=None; attempt=None
            if stem=="missing_input":
                s=timed("missing_finish",lambda:journal.finish(s,counts=counts))
            elif stem=="network_unresolved":
                original=network.dc_witness

                def unavailable(data,poi,load,*args,**kwargs):
                    if load==Q(1,2): raise ArithmeticError("B3 declared numerical fault")
                    return original(data,poi,load,*args,**kwargs)

                network.dc_witness=unavailable
                try: s=timed("numeric_attempt",lambda:journal.commit_hour(s,obs[3],counts))
                finally: network.dc_witness=original
                s=timed("numeric_finish",lambda:journal.finish(s,counts=counts)); attempt=obs[3]
            else:
                phase="close" if stem=="save_before_publish" else "readback"

                def inject(here,path):
                    if here==phase and path.name=="step_0004.json": raise OSError("B3 declared "+phase+" fault")

                s=timed("save_fault",lambda:journal.commit_hour(s,obs[4],counts,inject))
                s=timed("save_fault_audit",lambda:journal.audit_current(s,counts)); witness=journal.recovery_witness(s)
            last_session=s
            prefix_length=5 if stem=="save_after_publish" else length
            recovered=timed("probe_reopen",lambda:journal.reopen(output/stem,c,p,obs[:prefix_length],"on_time",identity,
                              attempt_observation=attempt,publication_witness=witness,counts=counts))
            require(recovered.audit_validity=="passed","probe reopen audit failed")
            expected={"missing_input":"missing_input","network_unresolved":"network_unresolved",
                      "save_before_publish":"incomplete_publication","save_after_publish":None}[stem]
            require(recovered.reason==expected,"unexpected probe adjudication")
            prior.dump(output/(stem+"_probe.json"),dict(status="DRAFT_NONAUTHORITATIVE",scope=journal.SCOPE,
                before_reopen=journal.summary(s),reopened_state=recovered.state,reopened_reason=recovered.reason,
                reopened_summary=journal.summary(recovered) if recovered.reason is not None else None,
                recovered_audit=recovered.audit_result,witness=witness))
            summaries.append(dict(case=stem,reason=s.reason,recovered_reason=recovered.reason,
                                  recovered_accepted_hour=recovered.state.business.next_hour-1))
        after=timed("fingerprints_after",fingerprints); require(before==after,"source/dependency drift")
        require(all(counts.get(k)==v for k,v in EXPECTED.items()),"B3 work counts differ from registered DAG")
        prior.dump(output/"report.json",dict(status="development_diagnostic_evaluated",authority="DRAFT_NONAUTHORITATIVE",scope=journal.SCOPE,
            counts=counts,stage_wall_seconds=stages,fingerprints=after,summaries=summaries,child_returncodes=children,
            main_experiment_performance_review_complete=False,aggregate_contract_release=False))
        current_phase="completion"; event("pre_completion"); artifacts=inventory(output)
        marker=dict(status="development_diagnostic_completed",authority="DRAFT_NONAUTHORITATIVE",scope=journal.SCOPE,
            artifacts=artifacts,artifact_bytes_before_completion=sum(v["bytes"] for v in artifacts.values()),
            elapsed_before_completion_write=guard("completion"),sampled_process_tree_peak_rss_bytes=peak)
        prior.dump(output/"completion.pending.json",marker)
        require(not (output/"completion.json").exists(),"completion exists")
        os.rename(output/"completion.pending.json",output/"completion.json"); verify_completion(output)
        guard("post_completion_verification")
    except BaseException as error:
        if current_child is not None:
            if current_child.poll() is None: current_child.kill()
            code=current_child.wait(timeout=5)
            if child_evidence is not None: child_evidence["returncode"]=code
        prior.dump(output/"failure.json",dict(status="development_diagnostic_failed",error=str(error),phase=current_phase,
                   child=child_evidence,completed_children=children,counts=counts,last_accepted=last_verified_accepted,
                   last_summary=journal.summary(last_session) if last_session is not None and last_session.reason is not None else None))
        raise
    finally:
        for restore in restores: restore()
    print(json.dumps(dict(status="development_diagnostic_completed",counts=counts,elapsed_seconds=time.perf_counter()-LAUNCH)))


if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--output",type=Path); parser.add_argument("--child",choices=CASES)
    args=parser.parse_args()
    if args.child: child(args.child)
    elif args.output: run(args.output)
    else: parser.error("--output or --child required")
