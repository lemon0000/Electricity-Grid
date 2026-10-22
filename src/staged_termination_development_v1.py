"""B3 single-writer simulation journal and explicit termination, never authority."""
from dataclasses import dataclass, replace
from fractions import Fraction as Q
import hashlib
import importlib.metadata
import json
from math import isfinite
import os
from pathlib import Path
import stat
import sys

from src.staged_deliverability_development_v1 import plain, task_balances, assessment, _unique_pairs
from src.staged_network_development_v1 import initialize_network, advance_network
from src.staged_network_audit_v1 import audit_network

ROOT=Path(__file__).resolve().parents[1]
SCOPE="B3 filesystem_visible_simulation_only"
MAX_BYTES=2*1024**2


def require(condition,message):
    if not condition: raise ValueError(message)


def encoded(value):
    return (json.dumps(plain(value),sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode("utf-8")


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def read_json(path):
    require(not path.is_symlink() and stat.S_ISREG(path.lstat().st_mode),"nonregular journal file")
    require(path.stat().st_size<=MAX_BYTES,"journal file size limit")

    def finite(value):
        number=float(value); require(isfinite(number),"nonfinite JSON"); return number

    return json.loads(path.read_text(encoding="utf-8"),object_pairs_hook=_unique_pairs,
                      parse_float=finite,parse_constant=lambda v:require(False,"invalid JSON constant"))


class PublicationError(OSError):
    def __init__(self,path,phase,may_have_published,cause,expected_sha):
        super().__init__(str(cause))
        self.path,self.phase,self.may_have_published=str(path),phase,may_have_published
        self.expected_sha=expected_sha


def publish(path,value,hook=None):
    """Only this function performs journal writes. Never replaces a final file."""
    payload=encoded(value)
    require(len(payload)<=MAX_BYTES,"journal file size limit")
    pending=path.with_name(path.name+".pending")
    require(not path.exists() and not pending.exists(),"existing journal object; reopen required")
    phase,uncertain="open",False

    def point(name):
        nonlocal phase
        phase=name
        if hook is not None: hook(name,path)

    try:
        point("open")
        with pending.open("xb") as stream:
            point("write"); stream.write(payload)
            point("flush"); stream.flush()
            point("fsync"); os.fsync(stream.fileno())
            point("close")
        point("pending_readback")
        require(read_json(pending)==plain(value) and pending.read_bytes()==payload,"pending bytes differ")
        uncertain=True
        point("publish")
        # Windows rename rejects an existing destination. Local single writer only.
        require(not path.exists(),"final journal object appeared")
        os.rename(pending,path)
        point("readback")
        require(read_json(path)==plain(value) and path.read_bytes()==payload,"published bytes differ")
        return hashlib.sha256(payload).hexdigest()
    except (OSError,ValueError) as error:
        raise PublicationError(path,phase,uncertain,error,hashlib.sha256(payload).hexdigest()) from error


def implementation_pins():
    report=ROOT/"results/tables/staged_deliverability_b2_v1_non_authoritative/attempt_01/report.json"
    completion=read_json(report.parent/"completion.json")
    recorded=completion["artifacts"]["report.json"]
    require(report.stat().st_size==recorded["bytes"] and hashlib.sha256(report.read_bytes()).hexdigest()==recorded["sha256"],
            "bound B2 report changed")
    fingerprint=json.loads(report.read_text(encoding="utf-8"))["fingerprints"]
    bound=fingerprint["repository_sha256"]
    for name,sha in bound.items():
        require(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,"B2 source drift: "+name)
    names=("src/staged_termination_development_v1.py","src/staged_termination_audit_v1.py",
           "docs/model_spec/staged_termination_development_v1.md")
    for item in fingerprint["external_selected"].values():
        require(hashlib.sha256(Path(item["path"]).read_bytes()).hexdigest()==item["sha256"],"external dependency drift")
    for name,version in fingerprint["versions"].items():
        require(importlib.metadata.version(name)==version,"runtime package drift")
    return dict(reused_b2=bound,b2_report_sha=hashlib.sha256(report.read_bytes()).hexdigest(),
                b3={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names},
                external_selected=fingerprint["external_selected"],versions=fingerprint["versions"],python=sys.version)


@dataclass(frozen=True)
class Session:
    root: Path
    state: object
    genesis_sha: str
    head_sha: str
    state_sha: str
    registration_end: int
    expected_last_hour: int
    reason: str | None=None
    pending: dict | None=None
    io_error: dict | None=None
    closed: bool=False
    reopened: bool=False
    audit_validity: str="not_established"
    audit_result: dict | None=None


def header(config,parameters,plan,identity,first_hour,registration_end,expected_last_hour):
    require(type(first_hour) is int and type(registration_end) is int and type(expected_last_hour) is int
            and first_hour<=0<registration_end<=expected_last_hour+1 and expected_last_hour-first_hour<10,
            "invalid declared boundaries")
    state=initialize_network(config,parameters,plan,identity,first_hour)
    value=dict(schema=1,status="DRAFT_NONAUTHORITATIVE",scope=SCOPE,config=config,parameters=parameters,
               plan=plan,identity=identity,first_hour=first_hour,registration_end=registration_end,
               expected_last_hour=expected_last_hour,initial_state_sha=digest(state),implementation=implementation_pins())
    return state,plain(value)


class CreateError(ValueError):
    def __init__(self,session,error):
        super().__init__(str(error)); self.session=session


def create_session(root,config,parameters,plan,identity,first_hour=-2,registration_end=4,expected_last_hour=7,hook=None):
    root=Path(root).resolve()
    state,value=header(config,parameters,plan,identity,first_hour,registration_end,expected_last_hour)
    root.mkdir(parents=True,exist_ok=False)
    try: sha=publish(root/"genesis.json",value,hook)
    except PublicationError as error:
        initial=Session(root,state,error.expected_sha,error.expected_sha,digest(state),registration_end,expected_last_hour)
        failure=replace(failed(initial,error,None,"genesis"),reason="initialization_failure")
        raise CreateError(failure,error) from error
    return Session(root,state,sha,sha,digest(state),registration_end,expected_last_hour)


def entries(root):
    paths=sorted(root.iterdir())
    require(all(not p.is_symlink() and stat.S_ISREG(p.lstat().st_mode) for p in paths),"nonregular journal entry")
    allowed={"genesis.json","checkpoint.json","attempt.json","terminal.json","audit_failure.json"}
    for path in paths:
        name=path.name.removesuffix(".pending")
        require(name in allowed or (len(name)==14 and name.startswith("step_") and name[5:9].isdigit()
                                   and name.endswith(".json")),"unknown journal entry")
    return paths


def writable(session):
    require(not session.closed and session.reason is None,"session closed; no further steps")
    paths=entries(session.root)
    require(not any(p.name.endswith(".pending") for p in paths),"pending evidence requires reopen")
    require(not any(p.name in {"attempt.json","terminal.json","audit_failure.json"} or (p.name=="checkpoint.json" and not session.reopened) for p in paths),
            "stored session closed or checkpointed; reopen required")
    steps=[p for p in paths if p.name.startswith("step_")]
    require([p.name for p in steps]==[f"step_{i:04d}.json" for i in range(len(session.state.records))],"stale session or ordinal gap")
    require(hashlib.sha256((session.root/"genesis.json").read_bytes()).hexdigest()==session.genesis_sha,"genesis head changed")
    head=steps[-1] if steps else session.root/"genesis.json"
    require(hashlib.sha256(head.read_bytes()).hexdigest()==session.head_sha,"accepted disk head changed")
    require(digest(session.state)==session.state_sha,"in-memory state drift")


def failed(session,error,row,role,candidate=None):
    uncertain=role=="step" and error.may_have_published
    pending=session.pending if row is None else dict(role=role,b2_candidate_record=plain(row),
        adoption="unknown" if uncertain else "not_adopted",
        b2_candidate_state=plain(candidate) if candidate is not None else None)
    reason="commit_outcome_unknown" if uncertain else "publication_outcome_unknown" if error.may_have_published else "persistence_failure"
    return replace(session,reason=reason,closed=True,
                   pending=pending,io_error=dict(operation=role,phase=error.phase,error=str(error),
                       may_have_published=error.may_have_published,planned_reason=session.reason,
                       target=Path(error.path).name,expected_sha=error.expected_sha))


def recovery_witness(session):
    require(session.io_error is not None and session.io_error["operation"] in {"genesis","step","attempt","checkpoint","terminal"},
            "publication failure required")
    e=session.io_error
    row=(session.pending or {}).get("b2_candidate_record")
    return dict(operation=e["operation"],target=e["target"],expected_sha=e["expected_sha"],
                may_have_published=e["may_have_published"],planned_reason=e["planned_reason"],
                observation=None if row is None else row["input"])


def validate_witness(w):
    require(isinstance(w,dict) and set(w)=={"operation","target","expected_sha","may_have_published","planned_reason","observation"},"invalid publication witness")
    require(w["operation"] in {"genesis","step","attempt","checkpoint","terminal"} and isinstance(w["target"],str)
            and Path(w["target"]).name==w["target"] and type(w["may_have_published"]) is bool
            and isinstance(w["expected_sha"],str) and len(w["expected_sha"])==64
            and all(v in "0123456789abcdef" for v in w["expected_sha"]),"invalid publication witness")
    target=w["target"]
    require((w["operation"]=="step" and len(target)==14 and target.startswith("step_") and target[5:9].isdigit()
             and target.endswith(".json")) or target==w["operation"]+".json","witness target differs")
    require(w["planned_reason"] is None or w["planned_reason"] in {"observation_complete","missing_input","followup_horizon_insufficient","network_unresolved","policy_or_admission_rejected"},"invalid witness termination")
    require(w["observation"] is None or (isinstance(w["observation"],dict) and type(w["observation"].get("hour")) is int),"invalid witness observation")
    require(w["operation"]!="genesis" or w["observation"] is None,"genesis cannot observe an arrival")


def commit_hour(session,observation,counts=None,hook=None):
    writable(session)
    require(type(observation.hour) is int,"integer observation hour required")
    require(observation.hour<=session.expected_last_hour,"observation beyond declared horizon")
    require(observation.hour>=session.state.business.next_hour,"duplicate or backward input")
    if observation.hour!=session.state.business.next_hour:
        return replace(session,reason="missing_input",closed=True,
                       pending=dict(role="out_of_order_input",provided_hour=observation.hour,adoption="not_adopted"))
    candidate=advance_network(session.state.business.parameters,session.state,observation,counts)
    row=candidate.records[-1]
    common=dict(schema=1,status="DRAFT_NONAUTHORITATIVE",scope=SCOPE,ordinal=len(session.state.records),
                hour=observation.hour,observation=observation,genesis_sha=session.genesis_sha,
                parent_sha=session.head_sha,before_state_sha=session.state_sha,record=row)
    if candidate.stopped:
        reason="network_unresolved" if row["status"]=="upstream_network_unresolved" else "policy_or_admission_rejected"
        try: publish(session.root/"attempt.json",dict(common,reason=reason),hook)
        except PublicationError as error: return failed(session,error,row,"attempt")
        return replace(session,reason=reason,closed=True,
                       pending=dict(role="network_attempt",b2_candidate_record=plain(row),adoption="not_adopted"))
    require(row["committed"] is True and row["status"]=="conditional_operating_point_committed"
            and row["proposal"].ledger_applied and candidate.business.next_hour==session.state.business.next_hour+1,
            "invalid actual-trajectory acceptance")
    after=digest(candidate)
    try:
        sha=publish(session.root/f"step_{len(session.state.records):04d}.json",dict(common,after_state_sha=after),hook)
    except PublicationError as error: return failed(session,error,row,"step",candidate)
    return replace(session,state=candidate,head_sha=sha,state_sha=after)


def summary(session,reason=None):
    s=session.state
    reason=reason or session.reason
    require(reason is not None,"terminal reason required")
    row=(session.pending or {}).get("b2_candidate_record")
    observation=(row or {}).get("input") or (session.pending or {}).get("observation")
    uncertain=reason in {"commit_outcome_unknown","reopen_failure"}
    tasks=task_balances(s.business)
    evidence_unresolved=(session.pending or {}).get("evidence_status")=="unreadable"
    publication="unresolved" if reason in {"commit_outcome_unknown","publication_outcome_unknown","reopen_failure"} else "not_published" if reason in {"persistence_failure","incomplete_publication"} else "not_applicable"
    if reason=="initialization_failure": publication="unresolved" if session.io_error["may_have_published"] else "not_published"
    return plain(dict(schema=1,status="DRAFT_NONAUTHORITATIVE",scope=SCOPE,termination_reason=reason,
        state_certainty="unresolved" if uncertain else "known",resume_permitted=False,
        audit_validity=session.audit_validity,
        publication_outcome=publication,
        last_accepted_hour=None if uncertain else s.business.next_hour-1,
        last_verified_accepted_hour=s.business.next_hour-1,next_required_hour=s.business.next_hour,
        attempted_hour=None if observation is None else observation["hour"],
        declared_registration_end=session.registration_end,declared_observation_last_hour=session.expected_last_hour,
        observation_end_reached=s.business.next_hour-1>=session.expected_last_hour,
        policy_outcome="unresolved" if row is not None and row["status"]=="upstream_network_unresolved" else "rejected" if row is not None and row["status"]!="conditional_operating_point_committed" else "unresolved" if uncertain or evidence_unresolved
            or reason in {"network_unresolved","publication_outcome_unknown","independent_audit_failure"} else "not_rejected_in_accepted_prefix",
        pending_arrival=dict(status="observed_pending_unaccepted",observation=observation) if observation is not None
            else dict(status="evidence_unresolved" if evidence_unresolved else "none" if reason in {"observation_complete","followup_horizon_insufficient"} else "not_observed",observation=None),
        future_arrivals_unobserved=None if evidence_unresolved else (s.business.next_hour-1 if observation is None else observation["hour"])<session.expected_last_hour,
        business_prefix_assessment=assessment(s.business,session.registration_end,session.expected_last_hour),
        all_arrived_tasks=tasks,primary_remaining_debt=sum((v["remaining"] for v in tasks if 0<=v["birth"]<session.registration_end),Q(0)),
        pending=session.pending,io_error=session.io_error,last_verified_state=s,genesis_sha=session.genesis_sha,
        head_sha=session.head_sha,state_sha=session.state_sha,aggregate_contract_release=False))


def finish(session,hook=None,counts=None):
    if session.reason in {"initialization_failure","persistence_failure","commit_outcome_unknown","publication_outcome_unknown","incomplete_publication","independent_audit_failure"}: return session
    if session.reason is None:
        if session.state.business.next_hour<=session.expected_last_hour: reason="missing_input"
        elif assessment(session.state.business,session.registration_end,session.expected_last_hour)["primary_right_censored"]:
            reason="followup_horizon_insufficient"
        else: reason="observation_complete"
        session=replace(session,reason=reason,closed=True)
    if (session.root/"terminal.json").exists():
        terminal=canonical_file(session.root/"terminal.json")
        session=replace(session,audit_validity=terminal["audit_validity"])
        require(session.audit_validity=="passed" and encoded(terminal)==encoded(summary(session)),"existing terminal differs")
        return session
    session=audit_current(session,counts,persist_failure=True)
    if session.reason=="independent_audit_failure": return session
    try: publish(session.root/"terminal.json",summary(session),hook)
    except PublicationError as error: return failed(session,error,None,"terminal")
    return session


def audit_failed(session,error,persist=True):
    result=replace(session,closed=True,reason="independent_audit_failure",audit_validity="failed",
        io_error=dict(operation="independent_audit",phase="audit",error=str(error),may_have_published=False,
                      planned_reason=session.reason,target="audit_failure.json",expected_sha=None))
    if persist:
        try: publish(session.root/"audit_failure.json",summary(result))
        except (OSError,ValueError): pass  # Best effort; acceptance records are retained.
    return result


def audit_current(session,counts=None,persist_failure=False):
    if counts is not None: counts["independent_audit_calls"]=counts.get("independent_audit_calls",0)+1
    try:
        if session.reason is None:
            result=audit_network(plain(session.state.config),plain(session.state.business.parameters),plain(session.state))
            audits=[result]
        else:
            from src.staged_termination_audit_v1 import audit_termination
            result=audit_termination(summary(session))
            audits=[result["network_audit"]]
            if result["hypothetical_candidate_audit"] is not None: audits.append(result["hypothetical_candidate_audit"])
        if counts is not None:
            counts["network_audit_calls"]=counts.get("network_audit_calls",0)+len(audits)
            for metric,key in (("network_audit_hours","audited_network_hours"),("business_audit_hours","accepted_business_hours"),
                               ("point_audit_visits","audited_pypower_points")):
                counts[metric]=counts.get(metric,0)+sum(a[key] for a in audits)
            row=(session.pending or {}).get("b2_candidate_record")
            if row is not None and row["committed"] is False and row["proposal"] is not None:
                counts["extra_business_audit_step_visits"]=counts.get("extra_business_audit_step_visits",0)+len(session.state.business.records)+1
        return replace(session,audit_result=result,audit_validity="failed" if session.reason=="independent_audit_failure" else "passed")
    except (AssertionError,ValueError,KeyError,TypeError) as error:
        return audit_failed(session,error,persist_failure)


def checkpoint_and_close(session,hook=None):
    writable(session)
    value=dict(schema=1,status="DRAFT_NONAUTHORITATIVE",scope=SCOPE,accepted_steps=len(session.state.records),
               head_sha=session.head_sha,state_sha=session.state_sha,state=session.state)
    try: publish(session.root/"checkpoint.json",value,hook)
    except PublicationError as error: return failed(session,error,None,"checkpoint")
    return replace(session,closed=True)


class ReopenError(ValueError):
    def __init__(self,session,cause):
        super().__init__(str(cause))
        self.session=replace(session,reason="reopen_failure",closed=True,
                             io_error=dict(operation="reopen",phase="integrity",error=str(cause),may_have_published=True,
                                           planned_reason=session.reason,target=None,expected_sha=None))


def canonical_file(path):
    value=read_json(path)
    require(path.read_bytes()==encoded(value),"journal object is not canonical")
    return value


def checkpoint_value(session):
    return dict(schema=1,status="DRAFT_NONAUTHORITATIVE",scope=SCOPE,accepted_steps=len(session.state.records),
                head_sha=session.head_sha,state_sha=session.state_sha,state=session.state)


def incomplete(session,target,witness=None,observation=None,row=None,missing=False,evidence_status="external_witness"):
    role="step" if target.startswith("step_") else target.removesuffix(".json")
    unknown=missing and witness is not None and witness["may_have_published"]
    pending=dict(role="incomplete_publication",target=target,adoption="not_adopted",
                 observation=plain(observation),b2_candidate_record=row,evidence_status=evidence_status)
    return replace(session,closed=True,reason="publication_outcome_unknown" if unknown else "incomplete_publication",pending=pending,
        io_error=dict(operation=role,phase="reopen_missing" if missing else "reopen_pending",error="publication not confirmed",
                      may_have_published=unknown,planned_reason=session.reason if session.reason else (witness or {}).get("planned_reason"),
                      target=target,expected_sha=(witness or {}).get("expected_sha")))


def pending_evidence(path,session):
    """Recover reported input from a complete envelope; never accept its step."""
    try:
        value=canonical_file(path)
        common={"schema","status","scope","ordinal","hour","observation","genesis_sha","parent_sha","before_state_sha","record"}
        target=path.name.removesuffix(".pending")
        require(set(value)==common|({"after_state_sha"} if target.startswith("step_") else {"reason"}),"pending schema differs")
        require(type(value["ordinal"]) is int and value["ordinal"]==len(session.state.records)
                and type(value["hour"]) is int and value["hour"]==session.state.business.next_hour
                and type(value["schema"]) is int and value["schema"]==1 and value["status"]=="DRAFT_NONAUTHORITATIVE" and value["scope"]==SCOPE
                and value["genesis_sha"]==session.genesis_sha and value["parent_sha"]==session.head_sha
                and value["before_state_sha"]==session.state_sha,"pending binding differs")
        row=value["record"]; observation=value["observation"]
        require(type(observation["hour"]) is int and observation["hour"]==value["hour"]
                and encoded(observation)==encoded(row["input"]),"pending observation differs")
        if target.startswith("step_"):
            require(row["committed"] is True and row["status"]=="conditional_operating_point_committed"
                    and isinstance(value["after_state_sha"],str) and len(value["after_state_sha"])==64
                    and all(v in "0123456789abcdef" for v in value["after_state_sha"]),"pending candidate differs")
            return observation,None,"canonical_envelope"
        require(row["committed"] is False,"pending attempt accepted")
        return observation,row,"saved_attempt"
    except (OSError,ValueError,TypeError,KeyError): return None,None,"unreadable"


def reopen(root,config,parameters,prefix,plan,identity,first_hour=-2,registration_end=4,
           expected_last_hour=7,attempt_observation=None,counts=None,publication_witness=None):
    root=Path(root).resolve()
    state=initialize_network(config,parameters,plan,identity,first_hour)
    session=Session(root,state,"","",digest(state),registration_end,expected_last_hour)
    try:
        _,expected=header(config,parameters,plan,identity,first_hour,registration_end,expected_last_hour)
        if publication_witness is not None: validate_witness(publication_witness)
        if publication_witness is not None and publication_witness.get("operation")=="genesis" and not (root/"genesis.json").exists():
            paths=entries(root)
            require(not prefix and attempt_observation is None and all(v.name=="genesis.json.pending" for v in paths),"invalid uninitialized journal")
            w=publication_witness
            require(w["target"]=="genesis.json" and w["expected_sha"]==digest(expected),"genesis witness differs")
            initial=replace(session,genesis_sha=digest(expected),head_sha=digest(expected))
            outcome=incomplete(initial,"genesis.json",w,missing=not (root/"genesis.json.pending").exists())
            return replace(audit_current(replace(outcome,reason="initialization_failure"),counts),reopened=True)
        saved=canonical_file(root/"genesis.json")
        require(encoded(saved)==encoded(expected),"genesis identity/input/implementation drift")
        sha=hashlib.sha256((root/"genesis.json").read_bytes()).hexdigest()
        session=replace(session,genesis_sha=sha,head_sha=sha)
        paths=entries(root)
        steps=[p for p in paths if p.name.startswith("step_") and not p.name.endswith(".pending")]
        checkpoint=canonical_file(root/"checkpoint.json") if (root/"checkpoint.json").exists() else None
        checkpoint_seen=checkpoint is None
        if checkpoint is not None and checkpoint.get("accepted_steps")==0:
            require(encoded(checkpoint)==encoded(checkpoint_value(session)),"zero-step checkpoint differs")
            checkpoint_seen=True
        for i,(path,o) in enumerate(zip(steps,prefix)):
            require(path.name==f"step_{i:04d}.json","journal ordinal gap")
            row=canonical_file(path)
            candidate=advance_network(parameters,session.state,o,counts)
            require(not candidate.stopped,"saved step cannot replay as accepted")
            expected_row=dict(schema=1,status="DRAFT_NONAUTHORITATIVE",scope=SCOPE,ordinal=i,hour=o.hour,
                 observation=o,genesis_sha=session.genesis_sha,parent_sha=session.head_sha,
                 before_state_sha=session.state_sha,record=candidate.records[-1],after_state_sha=digest(candidate))
            require(encoded(row)==encoded(expected_row),"journal row/state digest replay differs")
            session=replace(session,state=candidate,state_sha=expected_row["after_state_sha"],head_sha=hashlib.sha256(path.read_bytes()).hexdigest())
            if checkpoint is not None and checkpoint.get("accepted_steps")==i+1:
                require(encoded(checkpoint)==encoded(checkpoint_value(session)),"checkpoint differs")
                checkpoint_seen=True
        require(len(prefix)==len(steps),"caller prefix must match exact accepted journal length")
        require(checkpoint_seen,"checkpoint does not bind an accepted prefix")
        tails=[p for p in paths if p.name.endswith(".pending")]
        require(len(tails)<=1 and all(not p.with_name(p.name.removesuffix(".pending")).exists() for p in tails),
                "contradictory pending and final evidence")
        if publication_witness is not None:
            w=publication_witness
            require(not tails or tails[0].name.removesuffix(".pending")==w["target"],"witness and pending target contradict")
            target=root/w["target"]
            if target.exists():
                require(w["may_have_published"] and hashlib.sha256(target.read_bytes()).hexdigest()==w["expected_sha"],"publication witness differs")
            elif w["operation"]=="step" and w["may_have_published"] and not tails:
                require(False,"unknown commit has no confirmed final record")
        row=None
        if (root/"attempt.json").exists():
            require(attempt_observation is not None,"attempt observation required separately from prefix")
            attempt=canonical_file(root/"attempt.json")
            row=attempt["record"]
            reason="network_unresolved" if row["status"]=="upstream_network_unresolved" else "policy_or_admission_rejected"
            expected_attempt=dict(schema=1,status="DRAFT_NONAUTHORITATIVE",scope=SCOPE,ordinal=len(prefix),
                hour=session.state.business.next_hour,observation=attempt_observation,genesis_sha=session.genesis_sha,
                parent_sha=session.head_sha,before_state_sha=session.state_sha,record=row,reason=reason)
            require(row["committed"] is False and encoded(attempt)==encoded(expected_attempt)
                    and encoded(row["input"])==encoded(attempt_observation),"attempt binding differs")
            session=replace(session,closed=True,reason=reason,
                pending=dict(role="network_attempt",b2_candidate_record=row,adoption="not_adopted"))
        if tails:
            target=tails[0].name.removesuffix(".pending")
            if target.startswith("step_"): require(target==f"step_{len(prefix):04d}.json","pending ordinal differs")
            observation=(row or {}).get("input") or (publication_witness or {}).get("observation") or plain(attempt_observation)
            evidence_status="saved_attempt" if row is not None else "external_witness"
            if target.startswith(("step_","attempt")):
                saved_observation,saved_row,saved_status=pending_evidence(tails[0],session)
                if publication_witness is None:
                    require(attempt_observation is None or (saved_observation is not None
                            and encoded(attempt_observation)==encoded(saved_observation)),"caller and pending observation differ")
                    observation,row,evidence_status=saved_observation,saved_row,saved_status
                elif saved_observation is not None:
                    require(hashlib.sha256(tails[0].read_bytes()).hexdigest()==publication_witness["expected_sha"],
                            "pending bytes and publication witness differ")
                    require(encoded(observation)==encoded(saved_observation),"witness and pending observation differ")
                    observation,row,evidence_status=saved_observation,saved_row,saved_status
            return replace(audit_current(incomplete(session,target,publication_witness,observation,row,evidence_status=evidence_status),counts),reopened=True)
        if publication_witness is not None and not (root/publication_witness["target"]).exists():
            return replace(audit_current(incomplete(session,publication_witness["target"],publication_witness,
                publication_witness["observation"],row,missing=True),counts),reopened=True)
        if row is None: require(attempt_observation is None,"unexpected attempt observation")
        if (root/"audit_failure.json").exists():
            failure=canonical_file(root/"audit_failure.json")
            require(failure["termination_reason"]=="independent_audit_failure","invalid audit failure record")
            session=replace(session,reason="independent_audit_failure",closed=True,audit_validity="failed",io_error=failure["io_error"])
            require(encoded(failure)==encoded(summary(session)),"audit failure record differs")
        if (root/"terminal.json").exists():
            terminal=canonical_file(root/"terminal.json")
            if session.reason is None:
                require(terminal["termination_reason"] in {"observation_complete","missing_input","followup_horizon_insufficient"},"invalid saved termination")
                session=replace(session,reason=terminal["termination_reason"],closed=True)
            session=replace(session,audit_validity=terminal["audit_validity"])
            require(session.audit_validity=="passed","terminal audit validity differs")
            require(encoded(terminal)==encoded(summary(session)),"terminal differs from accepted state")
        return replace(audit_current(session,counts),reopened=True)
    except (OSError,ValueError,AssertionError,KeyError,TypeError) as error:
        raise ReopenError(session,error) from error
