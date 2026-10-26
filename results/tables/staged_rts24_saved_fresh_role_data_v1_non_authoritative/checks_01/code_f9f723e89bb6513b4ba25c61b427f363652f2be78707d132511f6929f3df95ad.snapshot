"""Read-only single-point raw/numeric replay under caller-held query and pins."""
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import sys

from src import staged_rts24_development_v1 as core
from src import staged_rts24_evidence_store_v1 as codec
from src import staged_rts24_numeric_interface_v1 as numeric
from src import staged_rts24_highs_backend_v1 as backend
from src import staged_rts24_audit_v1 as audit
from src import staged_rts24_child_optimality_v1 as child
from src import staged_rts24_p2_package_check_v1 as mechanical
from src import staged_rts24_p2_outer_observation_v2 as parent
from src.staged_rts24_causal_v1 import PointEvidence

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ('src/staged_rts24_saved_point_replay_v1.py', 'tests/test_staged_rts24_saved_point_replay_v1.py',
    'docs/plan/staged_deliverability_c_saved_point_replay_contract_v1.md', 'docs/plan/staged_deliverability_c_scientific_adoption_dag_v1.md',
    'src/staged_rts24_numeric_interface_v1.py', 'src/staged_rts24_highs_backend_v1.py',
    'src/staged_rts24_audit_v1.py', 'src/staged_rts24_child_optimality_v1.py', 'src/staged_rts24_evidence_store_v1.py',
    'src/staged_rts24_development_v1.py', 'src/staged_rts24_causal_v1.py', 'src/staged_deliverability_development_v1.py',
    'src/rq2_joint_deliverability_boundary_v1/debt_cohorts.py', 'src/grid/rts24.py',
    'src/staged_rts24_p2_package_check_v1.py', 'src/staged_rts24_p2_outer_observation_v1.py',
    'src/staged_rts24_p2_outer_observation_v2.py', 'src/staged_rts24_process_guard_v1.py', 'src/staged_rts24_process_guard_v3.py',
    'src/rq2_joint_deliverability_boundary_v1/normal_process.py', 'src/__init__.py', 'src/grid/__init__.py',
    'src/rq2_joint_deliverability_boundary_v1/__init__.py')
ROOT_FILES = {'request.json', 'result.json', 'native.json', 'native.log', 'process.json',
    'point.stdout.log', 'point.stderr.log', 'point_observations.json'}
RAW_FIELDS = set('schema problem_sha problem options version_expected stage run_invoked run_returned api_calls cleanup_error api_version api_githash api_version_parts model_status model_status_value solution info native_run_seconds objective_value cleanup_status elapsed_seconds log_pin'.split())
RAW_DIAGNOSTICS = {'error', 'artifact_error', 'extraction_errors'}
OBSERVATION_SCOPE = 'selected_inclusive_calls_not_additive_wall_or_total_OS_IO_excludes_observation_write_and_terminal_manifest_scan_and_completion_publication'
require = codec.require


def source_pins():
    return {name: mechanical.pin(codec.read_bytes(ROOT/name)) for name in SOURCES}


def _sources(expected):
    require(type(expected) is dict and set(expected) == set(SOURCES), 'closed replay source group required')
    for value in expected.values(): mechanical.checked_pin(value)
    actual = source_pins()
    require(actual == expected, 'replay source bytes changed')
    for name in SOURCES:
        if not name.startswith('src/') or not name.endswith('.py'): continue
        module_name = name[:-3].replace('/', '.').removesuffix('.__init__')
        module = sys.modules.get(module_name)
        require(module is not None and type(getattr(module, '__file__', None)) is str
            and Path(module.__file__).absolute() == (ROOT/name).absolute(), 'loaded replay module path differs')
        require(mechanical.pin(codec.read_bytes(module.__file__)) == actual[name], 'loaded replay source differs')
    return actual


def _outer(record):
    require(type(record) is dict, 'parent-held process record required')
    if 'parent_reserved_bytes' in record:
        checked = parent.assess_process(record, mechanical.CAPS)
        schema = 'guard_v3'
    else:
        projected = dict(record)
        if 'authority' in projected:
            require(projected.pop('authority') == 'DRAFT_NONAUTHORITATIVE', 'legacy process authority differs')
        checked = mechanical.parent.assess_process(projected, mechanical.CAPS)
        schema = 'legacy_guard'
    require(checked['ownership_status'] == 'quiet_verified', 'whole outer Job quiet required before reading')
    members = {(m['pid'], m['creation_filetime']) for m in checked['process_snapshot']['quiescence_witness']['member_identities']}
    return members, schema


def _query_budget(query):
    require(type(query) is core.BoundQuery and type(query.request) is core.PointRequest, 'exact expected query required')
    require(query.base_query is None or type(query.base_query) is core.BoundQuery and query.base_query.base_query is None,
        'query parent depth outside single-point contract')
    for value in (query, query.base_query):
        if value is None: continue
        data = value.request.data
        require(type(data.buses) is type(data.generators) is type(data.branches) is tuple
            and 1 <= len(data.buses) <= 24 and 1 <= len(data.generators) <= 33 and len(data.branches) <= 38,
            'network exceeds bounded replay shape')


def replay_point(point_root, expected_query, expected_frame, expected_files, outer_record, expected_sources):
    """No solver, spawn, publication, journal replay or whole-package adoption."""
    outer_members, monitor_schema = _outer(outer_record)
    before_sources = _sources(expected_sources)
    _query_budget(expected_query)
    mechanical.keys(expected_frame, 'ordinal pins_sha registration_sha execution_binding')
    require(type(expected_frame['ordinal']) is int and 1 <= expected_frame['ordinal'] <= 319, 'expected ordinal differs')
    mechanical.sha(expected_frame['pins_sha'])
    if expected_frame['registration_sha'] is not None: mechanical.sha(expected_frame['registration_sha'])
    binding = expected_frame['execution_binding']
    if binding is not None:
        mechanical.sha(expected_frame['registration_sha'])
        mechanical.keys(binding, 'ordinal slot_sha request_sha bound_query_sha parent_slot parent_point_sha parent_economic_sha state_after_actual_slot accepted_state_sha')
        mechanical.sha(binding['slot_sha'])
        require(type(binding['ordinal']) is int and binding['ordinal'] == expected_frame['ordinal']
            and binding['request_sha'] == expected_query.request.identity and binding['bound_query_sha'] == expected_query.identity,
            'expected materialized query binding differs')
        require(binding['parent_slot'] is None if expected_query.base_query is None else type(binding['parent_slot']) is int
            and 1 <= binding['parent_slot'] < expected_frame['ordinal'], 'expected parent slot differs')
        require(binding['parent_point_sha'] == (None if expected_query.base_point is None else core.digest(expected_query.base_point))
            and binding['parent_economic_sha'] == (None if expected_query.base_economic is None else core.digest(expected_query.base_economic)), 'expected parent evidence differs')
        gate = binding['state_after_actual_slot']
        require(gate is None and binding['accepted_state_sha'] is None or type(gate) is int and 1 <= gate < expected_frame['ordinal'], 'expected state gate differs')
        if gate is not None: mechanical.sha(binding['accepted_state_sha'])
    require(type(expected_files) is dict and 1 <= len(expected_files) <= 8192, 'bounded expected point inventory required')
    for name, value in expected_files.items(): mechanical.relative(name); mechanical.checked_pin(value)
    held_frame, held_files, held_sources, held_outer = map(codec.canonical, (expected_frame, expected_files, expected_sources, outer_record))
    query_ref, query_blobs = codec.pack(expected_query)
    root = codec.directory_chain(Path(point_root).absolute())
    before = mechanical.inventory(root)
    require(before['pins'] == expected_files, 'held point inventory differs')
    raw = before['raw']
    require({name for name in raw if '/' not in name} == ROOT_FILES
        and all('/' not in name or name.startswith('cas/objects/') and name.endswith('.json') and not name.endswith('.pending') for name in raw),
        'closed ordinary point file family required')
    require(set(before['directories']) == {'.', 'cas', 'cas/objects'}, 'unknown point directory')
    request, result, native = (codec.parse(raw[name]) for name in ('request.json', 'result.json', 'native.json'))
    fields = 'ordinal query_ref query_sha problem_sha pins_sha role hour registration_sha'
    p2 = expected_frame['execution_binding'] is not None
    mechanical.keys(request, fields+(' execution_binding' if p2 else ''))
    mechanical.keys(result, 'status error evidence_ref raw_pin request_sha query_sha problem_sha infeasibility_inferred')
    require(request['ordinal'] == expected_frame['ordinal'] and type(request['ordinal']) is int
        and request['pins_sha'] == expected_frame['pins_sha'] and request['registration_sha'] == expected_frame['registration_sha'],
        'expected point frame differs')
    require(request['query_ref'] == query_ref and request['query_sha'] == expected_query.identity
        and request['role'] == expected_query.request.role and type(request['hour']) is int and request['hour'] == expected_query.request.hour,
        'expected query frame differs')
    if p2: require(codec.canonical(request['execution_binding']) == codec.canonical(expected_frame['execution_binding']), 'expected execution binding differs')
    require(result['request_sha'] == expected_files['request.json']['sha256'] and result['query_sha'] == request['query_sha']
        and result['problem_sha'] == request['problem_sha'] == native['problem_sha'] and result['infeasibility_inferred'] is False
        and result['raw_pin'] == expected_files['native.json'] and native['log_pin'] == expected_files['native.log'], 'raw/result/log binding differs')
    log_path = native.get('options', {}).get('log_file')
    require(type(log_path) is str and '\0' not in log_path and Path(log_path).is_absolute() and '..' not in Path(log_path).parts
        and str(Path(log_path).absolute()) == log_path,
        'historical raw log path differs')
    numeric_unresolved = result['status'] == 'numeric_unresolved'
    require(numeric_unresolved or result['status'] == 'imported' and result['error'] is None, 'unsupported point return state')
    require(type(native) is dict and RAW_FIELDS <= set(native) <= RAW_FIELDS | RAW_DIAGNOSTICS
        and (numeric_unresolved or set(native) == RAW_FIELDS), 'closed raw record fields differ')
    for name in RAW_DIAGNOSTICS & set(native):
        value = native[name]
        if value is None: continue
        if name == 'extraction_errors':
            require(type(value) is dict and set(value) <= {'model', 'solution', 'info', 'timing'}, 'raw extraction errors differ')
            errors = value.values()
        else: errors = (value,)
        for error in errors:
            mechanical.keys(error, 'type message')
            require(type(error['type']) is type(error['message']) is str, 'raw error scalars differ')
    for name in ('elapsed_seconds', 'native_run_seconds'):
        require(type(native[name]) in (int, float) and isfinite(native[name]) and native[name] >= 0, 'raw timing scalar differs')
    for event in native['api_calls']:
        mechanical.keys(event, 'stage status value')
        require(type(event['stage']) is type(event['status']) is str and type(event['value']) is int, 'raw API scalar differs')
    point_limits = dict(mechanical.POINT_LIMITS, files=8192 if p2 else 5000)
    mechanical.process_ok(codec.parse(raw['process.json']), point_limits, outer_members, numeric=numeric_unresolved)
    process = codec.parse(raw['process.json'])
    local_files = len(before['pins'])-1
    local_bytes = sum(value['bytes'] for name, value in before['pins'].items() if name != 'process.json')
    require(process['terminal_files'] >= local_files and process['terminal_bytes'] >= local_bytes,
        'package-wide process counters below local point inventory')
    observations = codec.parse(raw['point_observations.json'])
    mechanical.keys(observations, 'allow_native counts inclusive_seconds missing_process_observations scope')
    require(observations['allow_native'] is True and observations['missing_process_observations'] == 'unknown_not_zero'
        and observations['scope'] == OBSERVATION_SCOPE, 'saved point observation scope differs')
    require(type(observations['counts']) is type(observations['inclusive_seconds']) is dict, 'observation mappings differ')
    for name, value in observations['counts'].items():
        require(type(name) is str and type(value) is int and 0 <= value <= parent.U64, 'observation counter differs')
    for name, value in observations['inclusive_seconds'].items():
        require(type(name) is str and type(value) in (int, float) and isfinite(value) and value >= 0, 'observation timing differs')
    store = codec.EvidenceStore(root/'cas');view = codec.EvidenceReadView(store)
    saved_query = view.get(request['query_ref'])
    require(type(saved_query) is core.BoundQuery and saved_query == expected_query, 'typed saved query differs from external expectation')
    problem = numeric.compile_problem(expected_query)
    require(problem.identity == request['problem_sha'], 'independently rebuilt problem differs')
    evidence = residuals = None
    try:
        snapshot = backend.snapshot_from_raw(problem, native)
        evidence = numeric.import_snapshot(expected_query, problem, snapshot)
    except numeric.UnresolvedNumeric as exc:
        require(numeric_unresolved and result['evidence_ref'] is None, 'unresolved raw cannot supply imported evidence')
        mechanical.keys(result['error'], 'type message')
        require(result['error'] == dict(type=type(exc).__name__, message=str(exc)), 'saved numeric failure did not reproduce')
        state = 'numeric_unresolved_reproduced'
        family = None
        closure = set(query_blobs)
    else:
        require(not numeric_unresolved and type(evidence) is PointEvidence, 'point return state contradicts raw replay')
        saved = view.get(result['evidence_ref'])
        identity, blobs = codec.pack(evidence)
        require(type(saved) is PointEvidence and saved == evidence and identity == result['evidence_ref'], 'reconstructed exact evidence differs')
        if expected_query.request.anchor_id is None:
            family = 'economic_kkt';residuals = audit.audit_economic_base(expected_query, evidence.point, evidence.economic)
            require(residuals['economic_kkt_satisfied'], 'independent economic audit failed')
        elif expected_query.request.objective != 'economic':
            family = 'child_lp_kkt';residuals = child.audit_child_lp(expected_query, evidence.point, evidence.child_lp)
            require(residuals['lp_optimality_conditions_satisfied'], 'independent child audit failed')
        else:
            family = 'primal_point';residuals = audit.audit_point(expected_query, evidence.point)
            require(residuals['point_constraints_satisfied'] and evidence.economic is evidence.child_lp is None, 'independent primal audit failed')
        closure = set(query_blobs) | set(blobs)
        state = 'imported_replay_matches_saved'
    require(set(view.before) == {key+'.json' for key in closure}, 'point CAS closure differs')
    view.bookend()
    after = mechanical.inventory(root)
    require(before == after, 'point inventory bookend changed')
    require(_sources(expected_sources) == before_sources and codec.pack(expected_query)[0] == query_ref
        and all(codec.canonical(value) == held for value, held in zip((expected_frame, expected_files, expected_sources, outer_record),
            (held_frame, held_files, held_sources, held_outer))), 'source or caller expectation changed')
    return dict(authority='DRAFT_NONAUTHORITATIVE', scope='single_saved_point_numeric_consistency_under_caller_held_expectations',
        replay_state=state, evidence_family=family, evidence=evidence, independent_audit=residuals,
        query_ref=query_ref, problem_sha=problem.identity, evidence_ref=None if evidence is None else result['evidence_ref'],
        point_inventory_sha=sha256(held_files).hexdigest(), outer_record_sha=sha256(held_outer).hexdigest(), outer_monitor_schema=monitor_schema,
        raw_log_path_matches_current=log_path == str(root/'native.log'), selected_source_bookends_verified=True,
        process_package_counters_cover_local_point=True, full_historical_package_storage_reconciled=False,
        expected_query_provenance_independently_verified=False, exact_typed_evidence_match=evidence is not None,
        infeasibility_inferred=False, scientific_evidence_adopted=False, journal_replayed=False, full_139_independently_verified=False,
        fx_temporal_backing=False, rigorous_bound_certified=False, full_runtime_closure_verified=False, resource_admission=False, formal_result=False)
