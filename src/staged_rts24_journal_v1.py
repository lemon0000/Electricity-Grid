"""Single-writer development journal with read-only saved-evidence replay.

No solver callbacks, writable resume, production lease, receipt, or durability claim.
"""
from dataclasses import dataclass, replace
import importlib
from importlib.metadata import version
from pathlib import Path
import re
import sys

from src import staged_rts24_causal_v2 as policy
from src import staged_rts24_development_v1 as c
from src.staged_rts24_causal_audit_v2 import audit_execution
from src.staged_rts24_reference_queries_v1 import reference_requests
from src.staged_rts24_evidence_store_v1 import (
    EvidenceStore, EvidenceReadView, PublicationError, SCHEMA as CODEC, canonical, sha, parse, read_bytes,
    publish, require, directory_chain, directory_identity,
)


SCHEMA = "staged_rts24_development_journal_v1"
REPO = Path(__file__).absolute().parents[1]
SOURCE_PATHS = (
    "src/staged_rts24_reference_queries_v1.py", "src/staged_rts24_causal_v2.py",
    "src/staged_rts24_causal_audit_v2.py", "src/staged_rts24_evidence_store_v1.py",
    "src/staged_rts24_journal_v1.py", "src/staged_rts24_development_v1.py",
    "src/staged_rts24_causal_v1.py", "src/staged_rts24_audit_v1.py",
    "src/staged_rts24_child_optimality_v1.py", "src/staged_deliverability_development_v1.py",
    "src/rq2_joint_deliverability_boundary_v1/debt_cohorts.py", "src/grid/rts24.py",
    "src/__init__.py", "src/rq2_joint_deliverability_boundary_v1/__init__.py", "src/grid/__init__.py",
    "src/grid/ac_case.py", "src/grid/ac_validation.py", "src/grid/ac_restoration.py",
    "src/grid/contingency.py", "src/grid/chronological_dispatch.py", "src/grid/dc_opf.py",
    "src/grid/network_grid_need.py", "src/grid/rts_gmlc.py", "src/grid/rts_gmlc_scuc.py", "src/grid/scopf.py",
    "configs/staged_deliverability_rts24_v1.DRAFT.yaml", "configs/staged_deliverability_small_case_v1.DRAFT.yaml",
    "configs/staged_deliverability_network_v1.DRAFT.yaml",
)
EXTERNAL_MODULES = (
    "pypower.case24_ieee_rts", "pypower.idx_bus", "pypower.idx_gen", "pypower.idx_brch", "pypower.idx_cost",
    "pypower.api", "yaml", "pyomo.environ", "pyomo.opt.base.solvers", "highspy",
)
ENTRY = re.compile(r"entry_([0-9]{6})\.json\Z")


def runtime_identity():
    """Explicit selected source/import pins, not a complete production environment seal."""
    sources = {name: sha(read_bytes(REPO/name, allow_links=True)) for name in SOURCE_PATHS}
    external = {}
    for name in EXTERNAL_MODULES:
        path = Path(importlib.import_module(name).__file__).absolute()
        external[name] = dict(path=str(path), sha256=sha(read_bytes(path, allow_links=True)))
    return dict(sources=sources, external=external, python=sys.version, executable=str(Path(sys.executable).absolute()),
                executable_sha256=sha(read_bytes(sys.executable, allow_links=True)),
                versions={name: version(name) for name in ("PYPOWER", "PyYAML", "pyomo", "highspy", "numpy", "scipy")},
                scope="selected_semantic_and_import_entry_sources_not_production_closure")


@dataclass(frozen=True)
class Session:
    root: Path
    fixture: c.Fixture
    state: policy.ExecutionState
    pins: dict
    genesis_sha: str
    head_sha: str
    ordinal: int
    directories: tuple
    closed: bool = False
    scientific_outcome: str | None = None
    publication_outcome: str = "committed"
    failure: dict | None = None


@dataclass(frozen=True)
class PendingHour:
    ordinal: int
    head_sha: str
    before_sha: str
    prepared: policy.PreparedHour
    proposal: policy.Proposal


class SessionClosed(ValueError):
    def __init__(self, session):
        super().__init__(session.scientific_outcome or "closed journal")
        self.session = session


def _name(ordinal):
    require(type(ordinal) is int and 1 <= ordinal <= 999999, "journal ordinal limit")
    return f"entry_{ordinal:06d}.json"


def _root_inventory(root):
    directory_chain(root)
    result = {}
    for path in root.iterdir():
        require(len(result) < 2000, "journal file limit")
        if path.name == "objects": directory_chain(path); continue
        base = path.name.removesuffix(".pending")
        require(base in ("genesis.json", "failure.json") or ENTRY.fullmatch(base), "unknown journal filename")
        result[path.name] = sha(read_bytes(path))
    return result


def _check(session):
    require(not session.closed, "closed journal cannot continue")
    require(directory_identity(session.root/"objects") == session.directories, "journal directory identity changed")
    require(runtime_identity() == session.pins, "runtime dependency changed")
    inventory = _root_inventory(session.root)
    require(not any(name.endswith(".pending") for name in inventory) and "failure.json" not in inventory, "unresolved persistence state")
    require(inventory.get("genesis.json") == session.genesis_sha, "genesis changed")
    genesis = parse(read_bytes(session.root/"genesis.json"))
    require(genesis["fixture_sha"] == c.digest(session.fixture)
            and (genesis["plan"], genesis["clean"], genesis["method"]) ==
            (session.state.plan, session.state.clean_path, session.state.method), "session fixture or trajectory changed")
    require(set(inventory) == {"genesis.json", *(_name(i) for i in range(1, session.ordinal+1))}, "journal suffix/head differs")
    path = session.root/(_name(session.ordinal) if session.ordinal else "genesis.json")
    data = read_bytes(path)
    require(sha(data) == session.head_sha, "journal head differs")
    head = parse(data)
    require(head["after_state_sha"] == c.digest(session.state), "in-memory state differs from disk head")
    require(head["kind"] not in ("attempt", "terminal"), "closed disk head cannot continue")
    return inventory


def create_session(root, fixture, plan, clean, method):
    pins = runtime_identity()
    state = policy.initialize_execution(fixture, plan, clean, method)
    policy.audit_execution_context(fixture, state)
    root = Path(root).absolute()
    directory_chain(root.parent)
    root.mkdir(exist_ok=False)
    (root/"objects").mkdir(exist_ok=False)
    store = EvidenceStore(root)
    fixture_ref, state_ref = store.put(fixture), store.put(state)
    genesis = dict(schema=SCHEMA, kind="genesis", codec=CODEC, fixture_ref=fixture_ref,
        fixture_sha=c.digest(fixture), state_ref=state_ref, after_state_sha=c.digest(state),
        plan=plan, clean=clean, method=method, runtime_identity=pins,
        authority="DRAFT_NONAUTHORITATIVE", resume_permitted=False)
    raw = canonical(genesis)
    identity = publish(root/"genesis.json", raw)
    require(runtime_identity() == pins, "dependency changed during genesis")
    return Session(root, fixture, state, pins, identity, identity, 0, directory_identity(root/"objects"))


def _failed(session, error, kind, payload, candidate, hook, expected_sha):
    target = _name(session.ordinal+1)
    may = isinstance(error, PublicationError) and error.target == target and error.may_have_published
    # An exception after final publication also leaves adoption to fresh replay.
    if (session.root/target).exists(): may = True
    prepared = payload.get("prepared")
    if prepared is None and type(payload.get("row")) is dict: prepared = payload["row"].get("prepared")
    observation = prepared.observation if prepared is not None else payload.get("observation")
    failure = dict(schema=SCHEMA, kind="failure", operation=kind, ordinal=session.ordinal+1,
        previous_sha=session.head_sha, before_state_sha=c.digest(session.state),
        expected_after_state_sha=c.digest(candidate), target=target,
        failed_target=error.target if isinstance(error, PublicationError) else None,
        expected_file_sha=expected_sha,
        phase=error.phase if isinstance(error, PublicationError) else "validation_or_bookend",
        publication_outcome="unknown" if may else "not_published", may_have_published=may,
        error_type=type(error).__name__, error=str(error)[:256],
        observed_hour=observation.hour if observation else None,
        reported_unaccepted_workload=str(observation.workload) if observation else None,
        observed_scope="writer_diagnostic_only_not_an_accepted_arrival", resume_permitted=False)
    try: publish(session.root/"failure.json", canonical(failure))
    except Exception: pass  # Persistence failure may prevent this best-effort diagnostic too.
    return replace(session, closed=True, publication_outcome=failure["publication_outcome"],
                   scientific_outcome="persistence_failure", failure=failure)


def _append(session, kind, payload, candidate, hook=None):
    expected_sha = None
    try:
        _check(session)
        store = EvidenceStore(session.root, hook)
        payload_ref = store.put(payload)
        state_ref = None if kind == "attempt" else store.put(candidate)
        entry = dict(schema=SCHEMA, kind=kind, ordinal=session.ordinal+1, previous_sha=session.head_sha,
            before_state_sha=c.digest(session.state), after_state_sha=None if kind == "attempt" else c.digest(candidate),
            payload_ref=payload_ref, state_ref=state_ref)
        raw = canonical(entry)
        expected_sha = sha(raw)
        identity = publish(session.root/_name(entry["ordinal"]), raw, hook)
        require(runtime_identity() == session.pins, "dependency changed during append")
        require(read_bytes(session.root/_name(entry["ordinal"])) == raw, "entry changed after publication")
        store.inventory()
        return replace(session, state=candidate, head_sha=identity, ordinal=entry["ordinal"])
    except Exception as error:
        return _failed(session, error, kind, payload, candidate, hook, expected_sha)


def _attempt(session, stage, evidence, pending, actual, error, hook=None):
    observation = c.observe(session.fixture, session.state.plan, session.state.clean_path, session.state.next_hour)
    h = reference_requests(session.fixture, session.state.plan, session.state.clean_path, session.state.method, session.state.next_hour)
    payload = dict(stage=stage, observation=observation, evidence=evidence, prepared=pending.prepared if pending else None,
        proposal=pending.proposal if pending else None, actual=actual, error_type=type(error).__name__, error=str(error)[:256],
        reference_request_ids=tuple(r.identity for r in h["requests"]), adopted=False,
        mathematical_infeasibility_inferred=False, after_state_sha=None)
    result = _append(session, "attempt", payload, session.state, hook)
    if result.closed: return result
    # Attempt itself closes the journal. Its payload is the checkpoint for an unchanged prefix.
    return replace(result, closed=True, scientific_outcome=stage+"_unresolved")


def begin_step(session, evidence, hook=None):
    _check(session)
    require(not session.state.stopped and session.state.next_hour < session.fixture.observation_end, "execution cannot observe another hour")
    try:
        prepared = policy.prepare_hour(session.fixture, session.state, evidence)
        proposal = policy.propose_hour(session.state, prepared)
    except (ValueError, TypeError) as error:
        raise SessionClosed(_attempt(session, "reference", evidence, None, None, error, hook)) from error
    require(runtime_identity() == session.pins, "dependency changed during prepare")
    return PendingHour(session.ordinal+1, session.head_sha, c.digest(session.state), prepared, proposal)


def commit_step(session, pending, actual=None, hook=None):
    _check(session)
    require(type(pending) is PendingHour and (pending.ordinal, pending.head_sha, pending.before_sha) ==
            (session.ordinal+1, session.head_sha, c.digest(session.state)), "pending step belongs to another head")
    try:
        candidate = policy.accept_hour(session.fixture, session.state, pending.prepared, pending.proposal, actual)
    except (ValueError, TypeError) as error:
        return _attempt(session, "actual", pending.prepared.evidence, pending, actual, error, hook)
    try: numeric = audit_execution(session.fixture, candidate)
    except (ValueError, TypeError) as error:
        return _attempt(session, "audit", pending.prepared.evidence, pending, actual, error, hook)
    return _append(session, "hour", dict(row=candidate.records[-1], independent_audit=numeric), candidate, hook)


def _outcome(fixture, state, summary):
    if state.stopped: return "known_rejection"
    if state.next_hour < fixture.observation_end: return "missing_input"
    return "right_censored" if summary["primary_right_censored"] else "complete"


def finish(session, hook=None):
    _check(session)
    summary = policy.execution_summary(session.fixture, session.state)
    numeric = audit_execution(session.fixture, session.state)
    outcome = _outcome(session.fixture, session.state, summary)
    payload = dict(checkpoint_state=session.state, summary=summary, independent_audit=numeric,
                   scientific_outcome=outcome, next_input="not_observed", resume_permitted=False)
    result = _append(session, "terminal", payload, session.state, hook)
    return result if result.closed else replace(result, closed=True, scientific_outcome=outcome)


def _expect_failure(call, error_type, message):
    try: call()
    except (ValueError, TypeError) as error:
        require(type(error).__name__ == error_type and str(error)[:256] == message, "unresolved exception differs")
        return
    raise ValueError("saved unresolved evidence now succeeds")


def _replay_attempt(fixture, state, payload):
    require(type(payload) is dict and set(payload) == {"stage", "observation", "evidence", "prepared", "proposal", "actual",
        "error_type", "error", "reference_request_ids", "adopted", "mathematical_infeasibility_inferred", "after_state_sha"}, "attempt fields differ")
    require(payload["adopted"] is False and payload["mathematical_infeasibility_inferred"] is False
            and payload["after_state_sha"] is None, "attempt claims adoption")
    require(payload["observation"] == c.observe(fixture, state.plan, state.clean_path, state.next_hour), "attempt observation differs")
    h = reference_requests(fixture, state.plan, state.clean_path, state.method, state.next_hour)
    require(payload["reference_request_ids"] == tuple(r.identity for r in h["requests"]), "attempt request identities differ")
    stage = payload["stage"]
    if stage == "reference":
        require(payload["prepared"] is payload["proposal"] is payload["actual"] is None, "reference attempt fabricated action")
        _expect_failure(lambda: policy.prepare_hour(fixture, state, payload["evidence"]), payload["error_type"], payload["error"])
    else:
        require(stage in ("actual", "audit"), "unknown attempt stage")
        prepared = policy.prepare_hour(fixture, state, payload["evidence"])
        proposal = policy.propose_hour(state, prepared)
        require((prepared, proposal) == (payload["prepared"], payload["proposal"]), "attempt policy differs")
        call = lambda: policy.accept_hour(fixture, state, prepared, proposal, payload["actual"])
        if stage == "actual": _expect_failure(call, payload["error_type"], payload["error"])
        else:
            candidate = call()
            _expect_failure(lambda: audit_execution(fixture, candidate), payload["error_type"], payload["error"])
    return stage+"_unresolved"


def trusted_binding(session):
    """Caller must retain this outside the journal before starting a fresh reader."""
    return dict(genesis_sha=session.genesis_sha, known_head_sha=session.head_sha, known_entries=session.ordinal,
        known_state_sha=c.digest(session.state), closed=session.closed, scientific_outcome=session.scientific_outcome,
        publication_outcome=session.publication_outcome,
        failure_sha=sha(canonical(session.failure)) if session.failure is not None else None)


def reopen(root, fixture, plan, clean, method, expected):
    """Read-only reconstruction under mandatory caller-supplied trusted binding."""
    root = directory_chain(root)
    directories = directory_identity(root/"objects")
    before = _root_inventory(root)
    require(type(expected) is dict and set(expected) == {"genesis_sha", "known_head_sha", "known_entries", "known_state_sha",
        "closed", "scientific_outcome", "publication_outcome", "failure_sha"}, "trusted binding fields differ")
    require(type(expected["known_entries"]) is int and 0 <= expected["known_entries"] <= 1999
            and type(expected["closed"]) is bool, "trusted binding types differ")
    require((expected["failure_sha"] is None and expected["publication_outcome"] == "committed")
            or (expected["failure_sha"] is not None and expected["closed"] is True
                and expected["scientific_outcome"] == "persistence_failure"
                and expected["publication_outcome"] in ("unknown", "not_published")), "trusted binding outcomes contradict")
    expected_genesis_sha = expected["genesis_sha"]
    failure = parse(read_bytes(root/"failure.json")) if "failure.json" in before else None
    require(before.get("failure.json") == expected["failure_sha"], "trusted failure binding differs")
    if failure is not None:
        require(type(failure) is dict and set(failure) == {"schema", "kind", "operation", "ordinal", "previous_sha", "before_state_sha",
            "expected_after_state_sha", "target", "failed_target", "expected_file_sha", "phase", "publication_outcome", "may_have_published",
            "error_type", "error", "observed_hour", "reported_unaccepted_workload", "observed_scope", "resume_permitted"}, "failure fields differ")
        require(failure["schema"] == SCHEMA and failure["kind"] == "failure" and failure["resume_permitted"] is False
                and type(failure["may_have_published"]) is bool and failure["operation"] in ("hour", "attempt", "terminal")
                and failure["publication_outcome"] == ("unknown" if failure["may_have_published"] else "not_published")
                and failure["publication_outcome"] == expected["publication_outcome"]
                and failure["ordinal"] == expected["known_entries"]+1
                and failure["previous_sha"] == expected["known_head_sha"]
                and failure["before_state_sha"] == expected["known_state_sha"]
                and failure["observed_scope"] == "writer_diagnostic_only_not_an_accepted_arrival", "failure witness differs")
    raw = read_bytes(root/"genesis.json")
    require(sha(raw) == expected_genesis_sha, "trusted genesis binding differs")
    genesis = parse(raw)
    require(type(genesis) is dict and set(genesis) == {"schema", "kind", "codec", "fixture_ref", "fixture_sha", "state_ref",
        "after_state_sha", "plan", "clean", "method", "runtime_identity", "authority", "resume_permitted"}, "genesis fields differ")
    require(genesis["schema"] == SCHEMA and genesis["kind"] == "genesis" and genesis["codec"] == CODEC
            and genesis["authority"] == "DRAFT_NONAUTHORITATIVE" and genesis["resume_permitted"] is False, "genesis scope differs")
    pins = runtime_identity()
    require(pins == genesis["runtime_identity"] and (plan, clean, method) == (genesis["plan"], genesis["clean"], genesis["method"])
            and c.digest(fixture) == genesis["fixture_sha"], "trusted context or runtime differs")
    store = EvidenceStore(root)
    object_inventory = store.inventory()
    reader = EvidenceReadView(store)
    require(reader.get(genesis["fixture_ref"]) == fixture, "saved fixture differs")
    state = policy.initialize_execution(fixture, plan, clean, method)
    require(reader.get(genesis["state_ref"]) == state and c.digest(state) == genesis["after_state_sha"], "genesis state differs")
    finals = sorted(name for name in before if ENTRY.fullmatch(name))
    require(finals == [_name(i) for i in range(1, len(finals)+1)], "journal ordinal gap")
    known = expected["known_entries"]
    require(len(finals) == known or (failure is not None and failure["may_have_published"] and len(finals) == known+1), "trusted journal tail differs")
    require((before[_name(known)] if known else expected_genesis_sha) == expected["known_head_sha"], "trusted head differs")
    head, outcome, terminal, unaccepted = expected_genesis_sha, "incomplete_journal", False, None
    last_entry = None
    terminal_result = None
    def replay_entry(data, adopt):
        nonlocal state, head, outcome, terminal, unaccepted, last_entry, terminal_result
        entry = parse(data)
        require(type(entry) is dict and set(entry) == {"schema", "kind", "ordinal", "previous_sha", "before_state_sha",
            "after_state_sha", "payload_ref", "state_ref"}, "entry fields differ")
        require(not terminal and entry["schema"] == SCHEMA and entry["ordinal"] == (last_entry["ordinal"]+1 if last_entry else 1)
                and entry["previous_sha"] == head and entry["before_state_sha"] == c.digest(state), "entry chain differs")
        payload = reader.get(entry["payload_ref"])
        candidate = state
        kind = entry["kind"]
        if kind == "hour":
            require(type(payload) is dict and set(payload) == {"row", "independent_audit"}, "hour payload differs")
            row = payload["row"]
            prepared = policy.prepare_hour(fixture, state, row["prepared"].evidence)
            proposal = policy.propose_hour(state, prepared)
            candidate = policy.accept_hour(fixture, state, prepared, proposal, row["actual"])
            require(candidate.records[-1] == row and audit_execution(fixture, candidate) == payload["independent_audit"], "saved hour replay differs")
        elif kind == "attempt":
            outcome = _replay_attempt(fixture, state, payload)
            require(entry["state_ref"] is None and entry["after_state_sha"] is None, "attempt has after-state")
            unaccepted, terminal = payload, True
        elif kind == "terminal":
            summary, numeric = policy.execution_summary(fixture, state), audit_execution(fixture, state)
            require(payload == dict(checkpoint_state=state, summary=summary, independent_audit=numeric,
                scientific_outcome=_outcome(fixture, state, summary), next_input="not_observed", resume_permitted=False), "terminal checkpoint differs")
            outcome, terminal = payload["scientific_outcome"], True
            if adopt: terminal_result = (summary, numeric)
        else: raise ValueError("unknown entry kind")
        if kind != "attempt":
            require(reader.get(entry["state_ref"]) == candidate and entry["after_state_sha"] == c.digest(candidate), "saved after-state differs")
        if adopt:
            state, head, last_entry = candidate, sha(data), entry
        return payload
    if known == 0: require(c.digest(state) == expected["known_state_sha"], "trusted initial state differs")
    for i, name in enumerate(finals, 1):
        replay_entry(read_bytes(root/name), True)
        if i == known: require(c.digest(state) == expected["known_state_sha"], "trusted prefix state differs")
    pending = [name for name in before if name.startswith("entry_") and name.endswith(".pending")]
    require(len(pending) <= 1 and not (terminal and pending), "pending after terminal or multiple pending")
    publication, certainty, pending_terminal = "committed", "known", None
    if pending:
        require(failure is not None, "pending publication lacks trusted failure witness")
        require(pending == [_name(len(finals)+1)+".pending"], "pending target differs")
        prior_terminal = terminal
        payload = replay_entry(read_bytes(root/pending[0]), False)
        terminal = prior_terminal
        if parse(read_bytes(root/pending[0]))["kind"] == "terminal": pending_terminal = payload
        else: unaccepted = dict(status="observed_pending_unaccepted", payload=payload)
        outcome, publication = "persistence_failure", "not_published"
    if failure is not None:
        require(failure["schema"] == SCHEMA and failure["kind"] == "failure" and failure["resume_permitted"] is False, "failure witness differs")
        n = failure["ordinal"]
        require(type(n) is int and n in (len(finals), len(finals)+1) and failure["target"] == _name(n), "failure target/ordinal differs")
        if n == len(finals):
            require(failure["may_have_published"] and before[_name(n)] == failure["expected_file_sha"]
                    and last_entry["kind"] == failure["operation"]
                    and last_entry["previous_sha"] == failure["previous_sha"]
                    and last_entry["before_state_sha"] == failure["before_state_sha"]
                    and c.digest(state) == failure["expected_after_state_sha"], "published-unknown witness differs")
        else:
            require(failure["previous_sha"] == head and failure["before_state_sha"] == c.digest(state), "failure prior differs")
            if pending:
                require(failure["expected_file_sha"] == before[pending[0]], "pending witness differs")
            elif failure["may_have_published"]: publication, certainty = "unknown", "unresolved"
            else: publication = "not_published"
            outcome = "persistence_failure"
    else:
        require(terminal == expected["closed"] and (not terminal or outcome == expected["scientific_outcome"]), "trusted completion differs")
    if "genesis.json.pending" in before or "failure.json.pending" in before:
        raise ValueError("unresolved genesis/failure publication")
    summary, numeric = terminal_result if terminal_result is not None else (policy.execution_summary(fixture, state), audit_execution(fixture, state))
    reader.bookend()
    require(_root_inventory(root) == before and store.inventory() == object_inventory and runtime_identity() == pins
            and directory_identity(root/"objects") == directories, "replay bookend changed")
    return dict(state=state, state_sha=c.digest(state), summary=summary, independent_audit=numeric,
        scientific_outcome=outcome, publication_outcome=publication, state_certainty=certainty,
        terminal_entry_present=bool(last_entry and last_entry["kind"] == "terminal"), closed_entry_present=terminal,
        unaccepted_attempt=unaccepted, failure=failure,
        pending_terminal_checkpoint=pending_terminal,
        pending_cas_objects=tuple(sorted(name for name in object_inventory if name.endswith(".pending"))),
        unreferenced_final_cas_objects=tuple(sorted(name for name in object_inventory
            if name.endswith(".json") and name.removesuffix(".json") not in reader.used)),
        genesis_sha=expected_genesis_sha, head_sha=head, final_entries=len(finals),
        saved_objects=len(object_inventory), resume_permitted=False,
        scope="read_only_saved_evidence_replay_local_filesystem_visibility")
