"""Zero-solver, fixed-inventory H1 shape proof and adversarial carry example.

No reachability, primal feasibility, native export, or formal-run certificate.
"""
from hashlib import sha256
import json
from math import ceil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUEST = 'configs/rq2_normal_h1_calibration_v3.json'
REQUEST_SHA = 'c31c3638695009c65c3e01e2990cbda9a71e5ff66f57c7f636ec88a7fb99fd6f'


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def static_inventory(data, reserve_categories):
    """Pure enumeration of fixed index sets and nonzero cost coefficients."""
    thermal = [g for g in data.generators if g.dispatch_mode == 'committable']
    reserve = [g for g in data.generators if g.enabled and
        g.dispatch_mode in ('committable', 'curtailable') and g.category in reserve_categories]
    names = []
    for component in ('commitment', 'startup', 'shutdown'):
        names.extend(f'{component}[0,{g.uid}]' for g in thermal)
    names.extend(f'generation[normal,0,{g.uid}]' for g in data.generators)
    names.extend(f'angle_degrees[normal,0,{b.uid}]' for b in data.buses)
    names.extend(f'branch_flow[normal,0,{b.uid}]' for b in data.branches)
    names.extend(f'dc_flow[normal,0,{b.uid}]' for b in data.dc_branches)
    names.extend(f'reserve_up[0,{g.uid}]' for g in reserve)
    names.extend(f'segment_power[0,{g.uid},{s}]' for g in thermal for s in range(3))
    coefficients = []
    breakdown = dict(commitment=0, segment_power=0, startup=0, shutdown=0)
    for g in thermal:
        b, c = g.cost_breakpoints_mw, g.cost_values_usd_per_hour
        if len(b) != 4 or len(c) != 4 or any(b[i+1] <= b[i] for i in range(3)):
            raise ValueError('fixed three-segment cost template required')
        values = [('commitment', f'commitment[0,{g.uid}]', c[0]),
                  ('startup', f'startup[0,{g.uid}]', g.cold_start_cost_usd),
                  ('shutdown', f'shutdown[0,{g.uid}]', g.shutdown_cost_usd)]
        values += [('segment_power', f'segment_power[0,{g.uid},{s}]',
                    (c[s+1]-c[s])/(b[s+1]-b[s])) for s in range(3)]
        for kind, name, number in values:
            if number != 0:
                coefficients.append((name, float(number).hex()))
                breakdown[kind] += 1
    eligible = [g.uid for g in thermal if max(ceil(g.minimum_up_time_hours), ceil(g.minimum_down_time_hours)) > 1]
    pairs = [g.uid for g in reserve if g.dispatch_mode == 'committable' and
             10*g.ramp_mw_per_minute < g.p_max_mw-g.p_min_mw]
    if len(names) != len(set(names)):
        raise ValueError('duplicate static variable name')
    C,G,B,L,D,R,A = len(thermal),len(data.generators),len(data.buses),len(data.branches),len(data.dc_branches),len(reserve),len({b.area for b in data.buses})
    stages = 1+C+G
    core_without_conditional = 3*C+4*C+2*C+L+B+R+A
    return dict(counts=dict(thermal=C,generators=G,buses=B,branches=L,dc_branches=D,
                           reserve=R,areas=A,variables=6*C+G+B+L+D+R,stages=stages),
        variable_names=sorted(names), max_name_json_token_bytes=max(len(encoded(n)) for n in names),
        cost_coefficients=sorted(coefficients), cost_term_breakdown=breakdown,
        dwell_eligible_uids=eligible, reserve_commitment_uids=pairs,
        constraints=dict(core_without_conditional=core_without_conditional,
            pinned_loader_origin_final=core_without_conditional+len(pairs)+stages-1,
            pinned_loader_future_final=core_without_conditional+len(pairs)+len(eligible)+stages-1,
            boundary_valid_arbitrary_bounds_final=core_without_conditional+2*C+C+len(eligible)+stages-1,
            generic_initial_arbitrary_bounds_final=core_without_conditional+2*C+C+C+stages-1))


def validate_loader_rows(data, rows):
    generators = {g.uid:g for g in data.generators}
    areas = {b.area for b in data.buses}
    for row in rows:
        if set(row.generator_min_mw) != set(generators) or set(row.generator_max_mw) != set(generators):
            raise ValueError('row inventory differs')
        if set(row.spin_up_requirement_by_area_mw) != areas:
            raise ValueError('reserve area inventory differs')
        for g in generators.values():
            if g.dispatch_mode == 'committable' and not (
                    row.generator_min_mw[g.uid] == g.p_min_mw == g.cost_breakpoints_mw[0] and
                    row.generator_max_mw[g.uid] == g.p_max_mw == g.cost_breakpoints_mw[-1]):
                raise ValueError('row outside pinned-loader thermal bounds family')


def audit():
    from pyomo.environ import Var, Constraint
    from pyomo.repn import generate_standard_repn
    from src.grid import rts_gmlc as loader, rts_gmlc_scuc as scuc
    from src.rq2_joint_deliverability_boundary_v1 import normal_h1_full_job_v3 as job
    raw = (ROOT/REQUEST).read_bytes()
    if sha256(raw).hexdigest() != REQUEST_SHA:
        raise ValueError('canonical request pin changed')
    request = json.loads(raw)
    binding = job.source
    h1 = binding.h1
    model_api = h1.model_api
    obs = binding.load_pinned_current(binding.H1SourceDeclaration(**request['source_declaration']),
        request['upstream_root'], config_path=request['config_path'])
    if obs.identity != request['source_identity'] or obs.network.identity != request['network_identity']:
        raise ValueError('current source/network pin mismatch')
    packet0 = h1.assemble_current_normal(obs.network, obs.row, obs.raw_workload,
        relative_hour=0, dc_bus=request['dc_bus'], source_time_basis=obs.source_time_basis)
    inventory = static_inventory(obs.network.data, scuc._THERMAL_RESERVE_CATEGORIES)
    loaded = loader.load_rts_gmlc_chronological_data(Path(request['upstream_root']))
    if h1.static_network(loaded).identity != obs.network.identity:
        raise ValueError('static inventory drift')
    validate_loader_rows(obs.network.data, loaded.hourly_points[:192])
    if len(loaded.hourly_points[:192]) != 192:
        raise ValueError('192-row diagnostic coverage missing')
    first = model_api.H1StageRequest(packet0.inputs)
    model0 = model_api.build_h1_stage_model(first, expected_identity=model_api.h1_stage_identity(first))
    actual_names = sorted(v.name for v in model0.component_data_objects(Var))
    if actual_names != inventory['variable_names']:
        raise ValueError('variable template differs from model')
    repn = generate_standard_repn(model0.operating_cost.expr, compute_values=True)
    actual_terms = sorted((v.name,float(c).hex()) for v,c in zip(repn.linear_vars,repn.linear_coefs))
    if not repn.is_linear() or actual_terms != inventory['cost_coefficients']:
        raise ValueError('static cost template differs from canonical objective')
    order = model_api.stage_order(packet0.inputs)
    expressions = model_api._expressions(model0, order)
    if any(not expr.is_variable_type() for expr in expressions[1:]):
        raise ValueError('later stages must select single variables')
    base = {uid:(on,power,age) for uid,on,power,age in packet0.before.units}
    units = []
    for g in obs.network.data.generators:
        if g.dispatch_mode == 'committable':
            on = ceil(g.minimum_up_time_hours)>1
            units.append((g.uid,on,float(g.p_min_mw) if on else 0.,1))
        else:
            units.append((g.uid,*base[g.uid]))
    before = h1._owned(h1.H1NormalBoundary, network_identity=obs.network.identity,
        completed_hours=1, units=tuple(units), evidence_role='numerical_lex_candidate')
    packet1 = h1.assemble_current_normal(obs.network, loaded.hourly_points[1], obs.raw_workload,
        relative_hour=1, dc_bus=request['dc_bus'], source_time_basis=obs.source_time_basis, before=before)
    last = model_api.H1StageRequest(packet1.inputs, (0.0,)*(len(order)-1))
    model1 = model_api.build_h1_stage_model(last, expected_identity=model_api.h1_stage_identity(last))
    constraint_count = len(list(model1.component_data_objects(Constraint,active=True,descend_into=True)))
    if (constraint_count != inventory['constraints']['pinned_loader_future_final'] or
            len(model1.initial_residual_dwell) != len(inventory['dwell_eligible_uids']) or
            sorted(v.name for v in model1.component_data_objects(Var)) != actual_names):
        raise ValueError('carry counterexample differs from shape derivation')
    modules = (loader,scuc,binding,h1,model_api)
    pins = {Path(m.__file__).resolve().relative_to(ROOT).as_posix():sha256(Path(m.__file__).read_bytes()).hexdigest() for m in modules}
    return dict(schema='h1_producer_shape_development_v1', status='DRAFT_NONAUTHORITATIVE',
        request_sha256=REQUEST_SHA, source_identity=obs.identity, source_pin_equal=True,
        network_identity=obs.network.identity, source_sha256=pins, static_inventory=inventory,
        checked_rows_sha256=sha256(encoded([dict(timestamp=p.timestamp.isoformat(),
            minimum=p.generator_min_mw, maximum=p.generator_max_mw,
            reserve=p.spin_up_requirement_by_area_mw) for p in loaded.hourly_points[:192]])).hexdigest(),
        loader_rows_checked=192, cost_template_matches=True, variable_template_matches=True,
        later_objectives_single_variable=True,
        counterexample=dict(relative_hour=1, constraints=constraint_count,
            dwell_constraints=len(model1.initial_residual_dwell), strict_locks=len(model1.h1_prior_objective_locks),
            old_limit=request['limits']['max_constraints'], old_limit_covers=False,
            synthetic_boundary=True, reachable_assignment_proven=False, scientific_witness=False),
        scope='fixed pinned static inventory; one normal state/hour; fixed reserve area keys',
        pinned_source_shape_conditional=True, native_export_coverage=False,
        future_source_parent_integrated=False, producer_coverage_proven=False,
        solver_calls=0, resource_admission=False, formal_execution_ready=False, formal_result=False)
