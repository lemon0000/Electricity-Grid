"""Zero-solver algebraic shape evidence and an unadmitted resource candidate."""
from contextlib import contextmanager, ExitStack
from dataclasses import asdict
from hashlib import sha256
from math import isfinite
from pathlib import Path
from time import perf_counter
from unittest.mock import patch
import gc
import sqlite3
import platform
import pyomo.version

from pyomo.environ import Constraint, Objective, Var, SolverFactory, minimize, value
from pyomo.repn import generate_standard_repn

from . import normal_h1_current_solve as current
from . import normal_h1_source_binding as binding
from . import normal_h1_source_episode as episode

model_api = current.source.model_api
SCHEMA = 'h1_algebraic_shape_resource_candidate_v1'


@contextmanager
def solver_calls_forbidden():
    attempts = []
    def denied(*args, **kwargs):
        attempts.append(1)
        raise RuntimeError('solver entry forbidden in H1 shape probe')
    with ExitStack() as stack:
        for owner, name in ((type(SolverFactory),'__call__'), (current,'solve_current'),
                (current.native,'run_h1_chain'), (current.native.capture,'solve_once'),
                (current.native.capture.provenance.adapter,'create_solver')):
            stack.enter_context(patch.object(owner,name,denied))
        yield attempts
        if attempts:
            raise RuntimeError('shape probe attempted a solver entry')


def implementation_identity():
    return model_api._digest(SCHEMA, binding.implementation_identity(),
        current.native.implementation_identity(),
        tuple((m.__name__,sha256(Path(m.__file__).read_bytes()).hexdigest()) for m in (episode,)),
        sha256(Path(__file__).read_bytes()).hexdigest())


def runtime_versions():
    return dict(python_version=platform.python_version(),python_implementation=platform.python_implementation(),
        pyomo_version=pyomo.version.__version__,sqlite_version=sqlite3.sqlite_version)


def _linear_terms(expression):
    repn = generate_standard_repn(expression, compute_values=True)
    if not repn.is_linear():
        raise ValueError('H1 shape probe requires linear algebraic expressions')
    coefficients = [float(value(c)) for c in repn.linear_coefs]
    if any(not isfinite(c) for c in coefficients):
        raise ValueError('finite algebraic coefficients required')
    return sum(c != 0 for c in coefficients)


def algebraic_shape(model):
    variables = list(model.component_data_objects(Var, active=True, descend_into=True))
    classes = dict(binary=0,general_integer=0,continuous=0)
    for variable in variables:
        if variable.is_binary(): classes['binary'] += 1
        elif variable.is_integer(): classes['general_integer'] += 1
        elif variable.is_continuous(): classes['continuous'] += 1
        else: raise ValueError('unknown variable domain in algebraic shape')
    rows = list(model.component_data_objects(Constraint,active=True,descend_into=True))
    terms = [_linear_terms(row.body) for row in rows]
    locks = [(row,n) for row,n in zip(rows,terms) if row.parent_component().name == 'h1_prior_objective_locks']
    objectives = list(model.component_data_objects(Objective,active=True,descend_into=True))
    if len(objectives) != 1:
        raise ValueError('one active shape objective required')
    objective = objectives[0]
    return dict(active_var_data=len(variables),variable_classes=classes,fixed_var_data=sum(v.fixed for v in variables),
        active_constraint_data=len(rows),ranged_constraint_data=sum(c.has_lb() and c.has_ub() and not c.equality for c in rows),
        linear_constraint_terms=sum(terms),lock_constraint_data=len(locks),lock_linear_terms=sum(n for _,n in locks),
        objective_linear_terms=_linear_terms(objective.expr),objective_sense='minimize' if objective.sense==minimize else 'maximize',
        linear_term_scope="standard_repn_after_fixed_substitution",
        native_matrix_measured=False,feasibility_checked=False,assignment_present=False,decision_present=False)


def unadmitted_content_envelope(stages, hours):
    if type(stages) is not int or stages < 1 or type(hours) is not int or not 1 <= hours <= 192:
        raise ValueError('positive stage count and bounded mechanism horizon required')
    metadata = episode.base.MAX_METADATA_BYTES + len(episode.base.FRAME) + 8
    raw = episode.replay.native.MAX_PAYLOAD_BYTES
    archive = episode.replay.MAX_ARCHIVE_BYTES
    calls = stages*hours
    return dict(kind='counterfactual_unadmitted_content_envelope',stages_per_hour=stages,hours=hours,
        stage_slots=calls,single_event_bytes=metadata+max(archive,stages*raw,episode.MAX_SOURCE_AUDIT_BYTES),
        journal_content_bytes=2*hours*metadata+hours*archive+calls*raw+hours*episode.MAX_SOURCE_AUDIT_BYTES,
        within_existing_short_call_domain=calls<=20,within_existing_short_hour_domain=hours<=24,
        instantiated=False,physical_space_reserved=False,measured_archive_bytes=None,run_authorized=False)


def inspect_shapes(packet):
    """Build only first/last algebraic shapes; placeholder locks have no provenance."""
    current.source.validate_current(packet)
    implementation = implementation_identity()
    order = model_api.stage_order(packet.inputs)
    samples = []
    with solver_calls_forbidden():
        for index in sorted({0,len(order)-1}):
            request = model_api.H1StageRequest(packet.inputs,(0.0,)*index)
            identity = model_api.h1_stage_identity(request)
            start = perf_counter()
            model = model_api.build_h1_stage_model(request,expected_identity=identity)
            construction = perf_counter()-start
            start = perf_counter()
            shape = algebraic_shape(model)
            count_seconds = perf_counter()-start
            samples.append(dict(stage_index=index,objective=list(order[index]),stage_model_identity=identity,
                placeholder_locks=index>0,placeholder_lock_count=index,lock_provenance_verified=False,
                shape_only=True,shape=shape,model_construction_seconds=construction,shape_count_seconds=count_seconds))
            del model
            gc.collect()
    first,last = samples[0]['shape'],samples[-1]['shape']
    if (first['active_var_data'] != last['active_var_data']
            or last['active_constraint_data']-first['active_constraint_data'] != len(order)-1
            or last['lock_constraint_data'] != len(order)-1):
        raise ValueError('H1 first/last shape lock-count invariant failed')
    current.source.validate_current(packet)
    if implementation_identity() != implementation:
        raise ValueError('H1 shape implementation drift')
    connection=sqlite3.connect(':memory:')
    try:
        sqlite_limit=connection.getlimit(sqlite3.SQLITE_LIMIT_LENGTH)
    finally:
        connection.close()
    envelope=unadmitted_content_envelope(len(order),192)
    return dict(schema=SCHEMA,runtime_versions=runtime_versions(),implementation_identity=implementation,normal_input_identity=packet.input_identity,
        current_source_audit_identity=packet.audit_identity,network_identity=packet.network.identity,
        stage_order=[list(x) for x in order],stage_count=len(order),measured_stage_shapes=samples,
        counterfactual_unadmitted_content_envelope=envelope,
        sqlite_length_limit_bytes=sqlite_limit,
        counterfactual_single_event_fits_observed_sqlite_length_limit=envelope['single_event_bytes']<=sqlite_limit,
        causal_key=None,accepted_normal_carry=None,
        sharing=dict(reuse_eligible_iff_complete_causal_key_equal=True,
            labels_alone_establish_key_equality=False,observed_hit_count=None,observed_hit_rate=None,
            future_carry_keys_enumerated=False),
        unmeasured=dict(native_solve_seconds=None,all_stage_build_seconds=None,assignment_audit_seconds=None,
            archive_encode_seconds=None,archive_bytes=None,replay_seconds=None,complete_episode_wall_seconds=None,
            complete_episode_peak_commit_bytes=None,complete_episode_peak_rss_bytes=None),
        formal_resource_contract=dict(per_stage_time_limit_seconds=None,task_wall_seconds=None,
            threads=None,process_commit_bytes=None,job_commit_bytes=None,archive_storage_bytes=None,
            input_selection_registered=False,host_volume_binding=None),
        solver_calls=0,shape_only=True,formal_result=False,formal_execution_ready=False,
        numerical_certificate=False,resource_contract_approved=False)


def pinned_shape_probe(declaration, upstream_root, *, config_path, expected_source_identity, dc_bus):
    binding.windows._sha(expected_source_identity)
    start=perf_counter()
    with solver_calls_forbidden():
        receipt=binding.load_pinned_current(declaration,upstream_root,config_path=config_path)
        if receipt.identity != expected_source_identity:
            raise ValueError('independently retained shape source pin mismatch')
        packet=current.source.assemble_current_normal(receipt.network,receipt.row,receipt.raw_workload,
            relative_hour=0,dc_bus=dc_bus,source_time_basis=receipt.source_time_basis)
        loading=perf_counter()-start
        report=inspect_shapes(packet)
        checking=perf_counter()
        binding.validate_pinned_current(receipt,upstream_root,expected_identity=expected_source_identity,config_path=config_path)
        revalidation=perf_counter()-checking
    report.update(source_binding_identity=receipt.identity,source_binding_audit_sha256=sha256(receipt.audit_payload).hexdigest(),
        source_declaration=asdict(declaration),dc_bus=dc_bus,source_load_and_assembly_seconds=loading,
        source_revalidation_seconds=revalidation,
        source_authenticated=False,selection_registered=False)
    return report
