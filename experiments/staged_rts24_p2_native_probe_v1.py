"""Draft P2 transport and internal workers; no launcher or run authority is created."""
import argparse
from contextlib import redirect_stdout,redirect_stderr
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from experiments import staged_rts24_native_probe_v1 as p1
from experiments import staged_rts24_saved_profile_v1 as saved
from src import staged_rts24_p2_controller_v1 as control
from src import staged_rts24_p2_packet_v1 as prep

PLAN,CLEAN,METHOD=prep.PLAN,prep.CLEAN,prep.METHOD
OUTPUT=ROOT/'results/tables/staged_rts24_p2_native_v1_non_authoritative/p2_01'
REGISTRATION=OUTPUT.parent/'registration_v1.json'
PACKET=ROOT/'results/tables/staged_rts24_p2_packet_v1_non_authoritative/packet_01'
MAX_CALLS=319
LIMITS=dict(wall_seconds=3600,no_progress_seconds=65,rss_bytes=1024**3,output_bytes=64*1024**2,files=8192)
POINT_LIMITS={**LIMITS,'wall_seconds':10,'no_progress_seconds':10}
FRESH_LIMITS={**LIMITS,'wall_seconds':60,'no_progress_seconds':60}
SOURCES=('src/staged_rts24_p2_controller_v1.py','src/staged_rts24_process_guard_v2.py',
    'experiments/staged_rts24_p2_native_probe_v1.py','tests/test_staged_rts24_p2_controller_v1.py',
    'tests/test_staged_rts24_p2_native_probe_v1.py','tests/test_staged_rts24_process_guard_v2.py',
    'docs/plan/staged_deliverability_c_p2_runner_development_contract_v1.md')
PACKET_PINS={'packet.json':dict(bytes=255146,sha256='9f53266cd297e3181fdf4c9f78ece30f57a217f9b8a9577e3d80f0a341eb56e6'),
    'context.json':dict(bytes=249557,sha256='96ab0a6b8bfca7567d91c6e5e671cece42ad7209d765342891ee5e117f38bbec'),
    'observation.json':dict(bytes=582,sha256='c13d4cba911b78442c08d9997e5a204e371f2f31b5401abf4a2ec9911b99adfb')}
modules,write,load,stamp,child_path,metrics=p1.modules,p1.write,p1.load,p1.stamp,p1.child_path,p1.metrics
Events,TransportUnresolved,NumericUnresolved=p1.Events,p1.TransportUnresolved,p1.NumericUnresolved


def load_packet(*,validate):
    c,_=modules()
    c.require({p.name:stamp(p) for p in PACKET.iterdir()}==PACKET_PINS,'frozen P2 preparation changed')
    value=json.loads((PACKET/'packet.json').read_bytes())
    if validate:prep.validate_packet(value,c.load_fixture())
    return value


def fingerprints():
    c,_=modules()
    c.require({p.name:stamp(p) for p in PACKET.iterdir()}==PACKET_PINS,'frozen P2 preparation changed')
    expected=json.loads((PACKET/'context.json').read_bytes())['source_pins']
    sources={n:stamp(ROOT/n) for n in expected}
    c.require(sources==expected,'P2 preparation source changed')
    return dict(legacy_scientific_and_P1_runtime=p1.fingerprints(),preparation_sources=sources,P2_sources={n:stamp(ROOT/n) for n in SOURCES},
        preparation_files={n:stamp(PACKET/n) for n in sorted(PACKET_PINS)})


def preserve():
    c,_=modules();c.require(stamp(saved.PRIOR)['sha256']==saved.PRIOR_SHA,'original P1 anchor changed')
    saved.check_p1(saved.read(saved.PRIOR)['p1_files'])
    c.require({p.name:stamp(p) for p in PACKET.iterdir()}==PACKET_PINS,'P2 preparation changed')
    return dict(original=p1.preserve(),P1_anchor=stamp(saved.PRIOR),P2_preparation=PACKET_PINS)


def registration_record():
    """Read-only draft construction; this function does not publish a registration."""
    p1.require_compute();packet=load_packet(validate=True)
    return dict(schema='staged_rts24_P2_execution_registration_v1',authority='DRAFT_NONAUTHORITATIVE',
        native_authorized=False,output=str(OUTPUT),limits=LIMITS,point_limits=POINT_LIMITS,fresh_limits=FRESH_LIMITS,
        max_point_attempts=MAX_CALLS,schedule_sha=packet['schedule_sha'],packet_pin=PACKET_PINS['packet.json'],
        pins=fingerprints(),preserved=preserve(),authorization='separate_explicit_user_instruction_required_not_granted_by_this_file')


def verify_registration(expected_sha,*,full=True):
    p1.require_compute();c,_=modules()
    c.require(type(expected_sha) is str and len(expected_sha)==64 and stamp(REGISTRATION)['sha256']==expected_sha,'P2 registration SHA differs')
    record=load(REGISTRATION)
    fixed=dict(schema='staged_rts24_P2_execution_registration_v1',authority='DRAFT_NONAUTHORITATIVE',native_authorized=False,
        output=str(OUTPUT),limits=LIMITS,point_limits=POINT_LIMITS,fresh_limits=FRESH_LIMITS,max_point_attempts=MAX_CALLS,
        packet_pin=PACKET_PINS['packet.json'],authorization='separate_explicit_user_instruction_required_not_granted_by_this_file')
    c.require(set(record)==set(fixed)|{'schedule_sha','pins','preserved'}
        and prep.digest({k:record[k] for k in fixed})==prep.digest(fixed),'P2 registration scope differs')
    packet=load_packet(validate=full)
    c.require(record['schedule_sha']==packet['schedule_sha'],'P2 registered schedule differs')
    if full:c.require(record['pins']==fingerprints() and record['preserved']==preserve(),'P2 registered dependencies differ')
    return record


def validate_binding(query,binding,slot):
    c,_=modules();q=query.request
    expected=dict(ordinal=slot['ordinal'],slot_sha=prep.digest(slot),request_sha=q.identity,bound_query_sha=query.identity,
        parent_slot=slot['parent_slot'],parent_point_sha=None if query.base_point is None else c.digest(query.base_point),
        parent_economic_sha=None if query.base_economic is None else c.digest(query.base_economic),
        state_after_actual_slot=slot['state_after_actual_slot'],accepted_state_sha=binding.get('accepted_state_sha'))
    c.require(prep.digest(binding)==prep.digest(expected),'P2 materialized binding differs')
    c.require((q.plan,q.clean_path,q.method,q.hour,q.role,q.objective,q.anchor_id)==
        (PLAN,CLEAN,METHOD,slot['hour'],slot['role'],slot['objective'],slot['parent_request_sha'])
        and prep.digest(c.plain(q.outages))==prep.digest(slot['outage']),'P2 materialized slot differs')
    c.require(q.identity==slot['request_sha'] or slot['request_sha'] is None and q.role=='actual_P','P2 request identity differs')
    c.require(binding['accepted_state_sha'] is None if slot['state_after_actual_slot'] is None else
        type(binding['accepted_state_sha']) is str and prep.SHA.fullmatch(binding['accepted_state_sha']),'P2 accepted state identity missing')


def point_worker(root, relative, expected_request_sha, registration_sha=None):
    from src.staged_rts24_numeric_interface_v1 import compile_problem, import_snapshot, UnresolvedNumeric
    from src.staged_rts24_highs_backend_v1 import call_highs, snapshot_from_raw, BackendFailure
    c, codec = modules()
    point = child_path(root, relative)
    request = load(point/"request.json")
    c.require(stamp(point/"request.json")["sha256"] == expected_request_sha, "point request changed")
    c.require(request.get("registration_sha") == registration_sha, "point registration differs")
    if registration_sha is not None:
        c.require(request["pins_sha"] == c.digest(load(REGISTRATION)["pins"]), "point registered pins differ")
    pins = fingerprints()
    c.require(c.digest(pins) == request["pins_sha"], "point dependency identity differs")
    store = codec.EvidenceStore(point/"cas")
    query = store.get(request["query_ref"])
    slots = load_packet(validate=False)["schedule"]
    validate_binding(query, request["execution_binding"], slots[request["ordinal"]-1])
    problem = compile_problem(query)
    c.require(query.identity == request["query_sha"] and problem.identity == request["problem_sha"], "point model changed")
    status, error, evidence_ref = "transport_unresolved", None, None
    try:
        try: raw = call_highs(problem, point/"native.log")
        except BackendFailure as failure: raw = failure.record
        write(point/"native.json", raw)
        c.require(fingerprints() == pins and stamp(point/"request.json")["sha256"] == expected_request_sha,
                  "point dependency drift before publication")
        c.require((point/"native.log").is_file() and raw.get("log_pin") == stamp(point/"native.log"), "native log not retained")
        try: evidence = import_snapshot(query, problem, snapshot_from_raw(problem, raw))
        except UnresolvedNumeric as exc:
            status = "numeric_unresolved"
            error = dict(type=type(exc).__name__, message=str(exc))
        else:
            evidence_ref = store.put(evidence)
            status = "imported"
    except (Exception,) as exc:
        error = dict(type=type(exc).__name__, message=str(exc))
    write(point/"result.json", dict(status=status, error=error, evidence_ref=evidence_ref,
        raw_pin=stamp(point/"native.json") if (point/"native.json").is_file() else None, request_sha=expected_request_sha,
        query_sha=query.identity, problem_sha=problem.identity, infeasibility_inferred=False))
    return 0 if status == "imported" else 2


class PointTransport:
    def __init__(self, root, pins, events, monitor=None, registration_sha=None):
        from src.staged_rts24_process_guard_v2 import supervise
        self.root, self.pins, self.events, self.monitor = Path(root), pins, events, monitor or supervise
        self.reserved = self.imported = self.run_invoked = self.run_returned = 0
        self.registration_sha = registration_sha

    def __call__(self, query, binding):
        from src.staged_rts24_numeric_interface_v1 import compile_problem, import_snapshot, UnresolvedNumeric
        from src.staged_rts24_highs_backend_v1 import snapshot_from_raw
        c, codec = modules()
        c.require(self.reserved < MAX_CALLS, "P2 call cap reached")
        validate_binding(query,binding,load_packet(validate=False)["schedule"][self.reserved])
        c.require(binding["ordinal"] == self.reserved+1,"P2 reservation ordinal differs")
        self.reserved += 1  # Never refunded, even if directory/spawn fails.
        relative = f"points/point_{self.reserved:04d}"
        point = self.root/relative
        point.mkdir(parents=True, exist_ok=False)
        (point/"cas").mkdir()
        (point/"cas/objects").mkdir()
        store = codec.EvidenceStore(point/"cas")
        problem = compile_problem(query)
        req = dict(ordinal=self.reserved, query_ref=store.put(query), query_sha=query.identity, problem_sha=problem.identity,
                   pins_sha=c.digest(self.pins), role=query.request.role, hour=query.request.hour,
                   registration_sha=self.registration_sha, execution_binding=binding)
        request_sha = write(point/"request.json", req)
        self.events("point_reserved", ordinal=self.reserved, role=query.request.role, hour=query.request.hour)
        argv = [sys.executable, "-B", "-s", str(Path(__file__).resolve()), "--point", relative,
            "--request-sha", request_sha, "--root", str(self.root)]
        if self.registration_sha is not None: argv += ["--registration-sha", self.registration_sha]
        record = self.monitor(argv, cwd=ROOT, output=self.root,
            progress=self.root/"events.jsonl", limits=POINT_LIMITS)
        write(point/"process.json", record)
        if not record["job_quiet_confirmed"]: raise TransportUnresolved("point Job quiescence unknown")
        if (point/"native.json").is_file():
            raw = load(point/"native.json")
            if raw.get("problem_sha") != problem.identity: raise TransportUnresolved("failed raw identity differs")
            self.run_invoked += int(raw.get("run_invoked") is True)
            self.run_returned += int(raw.get("run_returned") is True)
        else: raise TransportUnresolved("native raw record missing")
        if record["stop_reason"] not in (None, "child_exit_nonzero"):
            raise TransportUnresolved("point resource/transport stop: "+str(record["stop_reason"]))
        if not (point/"result.json").is_file(): raise TransportUnresolved("point result missing")
        result = load(point/"result.json")
        c.require(result["request_sha"] == request_sha
                  and result["query_sha"] == query.identity and result["problem_sha"] == problem.identity
                  and stamp(point/"request.json")["sha256"] == request_sha, "point return binding differs")
        if fingerprints() != self.pins: raise TransportUnresolved("point dependency drift")
        if result.get("raw_pin") != stamp(point/"native.json"): raise TransportUnresolved("point raw changed")
        if not (point/"native.log").is_file() or raw.get("log_pin") != stamp(point/"native.log"):
            raise TransportUnresolved("point native log missing or changed")
        if record["exit_code"] == 2 and result["status"] == "numeric_unresolved" and result["error"]:
            try: import_snapshot(query, problem, snapshot_from_raw(problem, raw))
            except UnresolvedNumeric as exc: raise NumericUnresolved(str(exc)) from exc
            raise TransportUnresolved("numeric failure witness did not reproduce")
        if record["exit_code"] != 0 or record["stop_reason"] is not None or result["status"] != "imported":
            raise TransportUnresolved("point protocol incomplete")
        evidence = store.get(result["evidence_ref"])
        fresh = import_snapshot(query, problem, snapshot_from_raw(problem, raw))
        c.require(evidence == fresh and fingerprints() == self.pins, "parent point audit or dependency differs")
        self.imported += 1
        self.events("point_imported", ordinal=self.reserved)
        return fresh


def fresh_worker(root):
    from src import staged_rts24_journal_v2 as journal
    c, _ = modules()
    # Fingerprints may import class definitions; no backend call/construction.
    before = fingerprints()
    c.require(before == load(root/"start.json")["pins"], "fresh dependency differs")
    expected = load(root/"trusted_binding.json")
    result = journal.reopen(root/"journal", c.load_fixture(), PLAN, CLEAN, METHOD, expected)
    c.require(fingerprints() == before, "fresh dependency changed")
    write(root/"fresh.json", dict(metrics=metrics(result), solver_calls=0))
    return 0


def worker(root,registration_sha):
    from src import staged_rts24_journal_v2 as journal
    from src.staged_rts24_process_guard_v2 import supervise
    c,_=modules()
    c.require(Path(root).resolve()==OUTPUT.resolve(),'registered P2 output required')
    launcher=load(root/'launcher_start.json')
    c.require(launcher['limits']==LIMITS and launcher['package']=='staged_rts24_P2_v1'
        and launcher['registration_sha']==registration_sha,'P2 launcher scope differs')
    pins,old=fingerprints(),preserve();registered=load(REGISTRATION)
    c.require(registered['pins']==pins and registered['preserved']==old,'P2 initial bytes differ')
    packet=load_packet(validate=True)
    c.require(packet['schedule_sha']==registered['schedule_sha'],'P2 schedule differs')
    write(root/'start.json',dict(authority='DRAFT_NONAUTHORITATIVE',pins=pins,preserved=old,
        packet_pin=PACKET_PINS['packet.json'],max_point_attempts=MAX_CALLS,registration_sha=registration_sha,
        native_user_authority='external_explicit_user_instruction_not_inferred_from_files'))
    events=Events(root);events('start')
    fixture=c.load_fixture();transport=PointTransport(root,pins,events,registration_sha=registration_sha)
    point=control.Cursor(packet['schedule'],transport)
    session,failure=control.actual_prefix(fixture,root/'journal',point,events)
    contracts=[]
    if failure is None and not session.state.stopped:
        try:control.full_contracts(fixture,point,events,contracts)
        except NumericUnresolved as exc:failure=dict(stage='contract_numeric',type=type(exc).__name__,message=str(exc))
    if fingerprints()!=pins or preserve()!=old:raise TransportUnresolved('P2 dependency or prior drift before finish')
    if not session.closed:
        session=journal.finish(session)
        if not session.closed or session.publication_outcome!='committed' or session.scientific_outcome not in (
                'known_rejection','missing_input','right_censored','complete'):
            write(root/'writer_closed_binding.json',journal.trusted_binding(session))
            raise TransportUnresolved('P2 journal finish unresolved')
    write(root/'contract_rows.json',contracts)
    write(root/'trusted_binding.json',journal.trusted_binding(session))
    if failure is not None:write(root/'numeric_failure.json',dict(**failure,infeasibility_inferred=False))
    events('fresh_reserved')
    argv=[sys.executable,'-B','-s',str(Path(__file__).resolve()),'--fresh','--root',str(root),'--registration-sha',registration_sha]
    fresh_record=supervise(argv,cwd=ROOT,output=root,progress=root/'events.jsonl',limits=FRESH_LIMITS)
    write(root/'fresh_process.json',fresh_record)
    c.require(fresh_record['job_quiet_confirmed'] and fresh_record['stop_reason'] is None
        and fresh_record['exit_code']==0,'P2 fresh process unresolved')
    events('fresh_returned')
    result=journal.reopen(root/'journal',session.fixture,PLAN,CLEAN,METHOD,journal.trusted_binding(session))
    c.require(load(root/'fresh.json')['metrics']==metrics(result),'P2 fresh metrics differ')
    c.require(fingerprints()==pins and preserve()==old,'P2 source or prior bytes changed')
    complete=failure is None and point.actual_finished and not session.state.stopped and len(contracts)==138 \
        and transport.reserved==transport.imported==point.reserved==MAX_CALLS
    write(root/'report.json',dict(authority='DRAFT_NONAUTHORITATIVE',package_complete=complete,failure=failure,
        point_attempts_reserved=transport.reserved,points_imported=transport.imported,
        native_run_invoked_observed=transport.run_invoked,native_run_returned_observed=transport.run_returned,
        fresh_launches=1,metrics=metrics(result),contracts=contracts,full_139_executed=complete,
        actual_accepted_slots=sorted(point.accepted),resource_admission=False,overall_performance_review_complete=False,
        fx_temporal_backing=False,formal_result=False))
    events('report',package_complete=complete)
    return 0 if complete else 2


def cli():
    parser=argparse.ArgumentParser(description='Internal draft P2 workers; separate native authorization is required.')
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--worker',action='store_true');group.add_argument('--point');group.add_argument('--fresh',action='store_true')
    parser.add_argument('--root',required=True);parser.add_argument('--request-sha');parser.add_argument('--registration-sha',required=True)
    args=parser.parse_args();root=Path(args.root).absolute();c,_=modules()
    c.require(root.resolve()==OUTPUT.resolve() and root.is_dir(),'registered P2 root required')
    logdir=child_path(root,args.point) if args.point else root
    prefix='point' if args.point else 'fresh' if args.fresh else 'worker'
    with (logdir/(prefix+'.stdout.log')).open('x',encoding='utf-8') as out, (logdir/(prefix+'.stderr.log')).open('x',encoding='utf-8') as err:
        with redirect_stdout(out),redirect_stderr(err):
            observations=None
            try:
                verify_registration(args.registration_sha,full=False)
                observations=p1.install_observers(allow_native=bool(args.point))
                if args.point:code=point_worker(root,args.point,args.request_sha,args.registration_sha)
                elif args.fresh:code=fresh_worker(root)
                else:code=worker(root,args.registration_sha)
                write(logdir/(prefix+'_observations.json'),observations())
                if args.worker:p1.complete_core(root)
                return code
            except BaseException as exc:
                import traceback
                traceback.print_exc(file=err);err.flush()
                try:
                    write(logdir/(prefix+'_failure.json'),dict(type=type(exc).__name__,message=str(exc),
                        adoption_prohibited=True,worker_mode=prefix,journal_terminal_status='not_inspected',
                        ownership_status='unknown',resume_permitted=False))
                    if observations is not None and not (logdir/(prefix+'_observations.json')).exists():
                        write(logdir/(prefix+'_observations.json'),observations())
                except BaseException:traceback.print_exc(file=err);err.flush()
                return 3


if __name__=='__main__':sys.exit(cli())
