"""Independent scheme-A source packet; old source-pair types remain untouched."""
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path

from . import source_pair as old
from . import cfe_preallocation as cfe

SCHEMA = 'draft_preallocated_cfe_source_pair_v1'


@dataclass(frozen=True)
class PreallocatedPairDeclaration:
    split: str
    power_raw_start: int
    workload_raw_start: int
    hours: int
    outage_seed: int
    power_window_identity: str
    workload_window_identity: str
    config_sha256: str
    normalized_unit_mw: str
    decimal_places: int
    hourly_cfe_target: str
    pairing_rule: str
    parameter_role: str
    cfe_rule: str = cfe.RULE

    def __post_init__(self):
        fields = asdict(self)
        if fields.pop('cfe_rule') != cfe.RULE:
            raise ValueError('scheme-A allocation declaration required')
        old.PairDeclaration(**fields)  # Source declarations only; no old request production.


def prepare_source_pair(declaration, *, config_path=old.source_window.audit.DEFAULT_CONFIG):
    if type(declaration) is not PreallocatedPairDeclaration:
        raise ValueError('exact preallocated source-pair declaration required')
    declaration.__post_init__()
    d = declaration
    power = old.source_window.load_source_window('power', d.split, d.power_raw_start, d.hours,
        outage_seed=d.outage_seed, config_path=config_path, expected_config_sha256=d.config_sha256)
    workload = old.source_window.load_source_window('workload', d.split, d.workload_raw_start, d.hours,
        config_path=config_path, expected_config_sha256=d.config_sha256)
    if power['window_identity'] != d.power_window_identity or workload['window_identity'] != d.workload_window_identity:
        raise ValueError('independent source window identity mismatch')
    if len(power['rows']) != d.hours or len(workload['rows']) != d.hours:
        raise ValueError('complete source window row count required')
    rows, hours = [], []
    for index, (p, w) in enumerate(zip(power['rows'], workload['rows'], strict=True)):
        if int(p['source_hour']) != d.power_raw_start+index or int(w['source_relative_hour']) != d.workload_raw_start+index:
            raise ValueError('source clock differs from declared window')
        projected = old.workload_projection.project_workload_power(w['workload_fraction'], d.normalized_unit_mw,
            decimal_places=d.decimal_places)
        row = dict(relative_offset=index, power_source_row=p, workload_source_row=w, workload_projection=projected,
            allocation=None, source_hour=None)
        if projected['status'] == 'projected':
            allocation = cfe.allocate(str(projected['workload_occupancy']), p['cfe_call_fraction'], d.hourly_cfe_target)
            hour = dict(schema='preallocated_cfe_source_hour_v1', split=d.split,
                power_source_hour=int(p['source_hour'])+1, workload_source_hour=int(w['source_relative_hour'])+1,
                power_window_identity=d.power_window_identity, workload_window_identity=d.workload_window_identity,
                outage_seed=d.outage_seed, normalized_unit_mw=d.normalized_unit_mw,
                allocation=allocation.record(), allocation_identity=allocation.identity)
            # No legacy ContinuationHour or free-standing recovery limit is emitted.
            hour['identity'] = cfe._hash(hour)
            row.update(allocation=allocation.record(), source_hour=hour)
            hours.append(hour)
        rows.append(row)
    result = dict(schema=SCHEMA, status='staged_preallocated' if len(hours) == d.hours else 'unresolved',
        declaration=asdict(d), rows=rows, hours=hours if len(hours) == d.hours else None,
        common_allowance_across_arms=True, allowance_depends_on_action=False, interhour_allowance_carry=False,
        executable_episode_input=False, formal_result=False, solver_calls=0, joint_probability=None,
        registered_coupling=False, observed_power_mapping=False,
        source_sha256={m.__name__: sha256(Path(m.__file__).read_bytes()).hexdigest()
            for m in (old, old.source_window, old.workload_projection, cfe)},
        implementation_sha256=sha256(Path(__file__).read_bytes()).hexdigest())
    result['pair_identity'] = cfe._hash(result)
    return result
