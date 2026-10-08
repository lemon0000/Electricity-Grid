"""Explicit marginal pairing and staged business requests, not an episode."""
from dataclasses import asdict, dataclass
from fractions import Fraction as Q
from hashlib import sha256
from pathlib import Path

from ..scenarios import rq2_joint_deliverability as legacy
from . import source_window, workload_projection
from .boundary import ContinuationHour
from .common_request_adapter import CommonRequestMapping


@dataclass(frozen=True)
class PairDeclaration:
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

    def __post_init__(self):
        if type(self.split) is not str or self.split not in ('training','holdout'):
            raise ValueError('explicit same-split pairing required')
        for name in ('power_raw_start','workload_raw_start','outage_seed'):
            if type(getattr(self,name)) is not int or getattr(self,name)<0:
                raise ValueError('nonnegative integer required: '+name)
        if type(self.hours) is not int or self.hours<=0:
            raise ValueError('positive integer hours required')
        for name in ('power_window_identity','workload_window_identity','config_sha256'):
            source_window._sha(getattr(self,name))
        workload_projection.project_workload_power('0',self.normalized_unit_mw,decimal_places=self.decimal_places)
        if type(self.hourly_cfe_target) is not str or self.hourly_cfe_target not in ('0.5','0.7','0.85','1'):
            raise ValueError('explicit inherited CFE target required')
        if (type(self.pairing_rule) is not str or type(self.parameter_role) is not str
                or self.pairing_rule!='declared_relative_offset_pairing_v1' or self.parameter_role!='mechanism_assumption'):
            raise ValueError('explicit relative-offset mechanism declaration required')


def prepare_source_pair(declaration, *, config_path=source_window.audit.DEFAULT_CONFIG):
    """Rebuild both windows; expose complete staged hours only if every row maps.

    Relative positions are paired by declaration. No probability, common clock,
    population support, or formal coupling rule is inferred.
    """
    if type(declaration) is not PairDeclaration:
        raise ValueError('typed pair declaration required')
    declaration.__post_init__()
    d=declaration
    power=source_window.load_source_window('power',d.split,d.power_raw_start,d.hours,
        outage_seed=d.outage_seed,config_path=config_path,expected_config_sha256=d.config_sha256)
    workload=source_window.load_source_window('workload',d.split,d.workload_raw_start,d.hours,
        config_path=config_path,expected_config_sha256=d.config_sha256)
    if power['window_identity']!=d.power_window_identity or workload['window_identity']!=d.workload_window_identity:
        raise ValueError('independent window identity mismatch')
    normalization={'source_basis':workload['chain']['trace_identity_basis'],
        'source_package_manifest_sha256':workload['package_manifest_sha256'],
        'numerical_projection_rule':'exact_decimal_half_even_then_str_float_identity_v1',
        'decimal_places':d.decimal_places,'normalized_unit_mw':d.normalized_unit_mw,
        'power_rule':'linear_workload_power_no_idle_offset_v1'}
    normalization_id=source_window._hash(normalization)
    mapping=CommonRequestMapping(d.normalized_unit_mw,normalization_id,
        'linear_workload_power_no_idle_offset_v1',
        'declared_power_source_and_workload_pairing_mechanism_v1','mechanism_assumption')
    rows=[]
    hours=[]
    for index,(p,w) in enumerate(zip(power['rows'],workload['rows'],strict=True)):
        projected=workload_projection.project_workload_power(w['workload_fraction'],d.normalized_unit_mw,
            decimal_places=d.decimal_places)
        cfe_source=float(p['cfe_call_fraction'])
        cfe=legacy.raw_cfe_request(cfe_source,float(d.hourly_cfe_target))
        row={'relative_offset':index,'power_source_row':p,'workload_source_row':w,
            'workload_projection':projected,'cfe_request':cfe,
            'cfe_source_float_hex':cfe_source.hex(),'cfe_request_float_hex':cfe.hex(),
            'cfe_source_decimal_projection_error_exact':workload_projection._ratio(Q(str(cfe_source))-Q(p['cfe_call_fraction'])),
            'source_hour':None}
        if projected['status']=='projected':
            hour=ContinuationHour(arm_id='joint_correct_shared',track_id='shared',split=d.split,
                power_source_hour=int(p['source_hour'])+1,workload_source_hour=int(w['source_relative_hour'])+1,
                power_trajectory_id=power['chain']['chain_id'],workload_trace_id=workload['chain']['chain_id'],
                workload_normalization_sha256=normalization_id,power_outage_seed=d.outage_seed,
                grid_request=0.,cfe_request=cfe,workload_occupancy=projected['workload_occupancy'],
                power_provenance_sha256=power['package_manifest_sha256'],
                workload_provenance_sha256=workload['package_manifest_sha256'])
            row['source_hour']=asdict(hour)
            hours.append(asdict(hour))
        rows.append(row)
    complete=len(hours)==d.hours
    result={'status':'staged' if complete else 'unresolved','declaration':asdict(d),
        'normalization':normalization,'mapping':asdict(mapping),'rows':rows,
        'hours':hours if complete else None,
        'grid_request_slot_role':'empty_slot_for_common_reference_not_observed_zero',
        'source_clock_mapping':'raw_zero_based_to_business_one_based_for_each_independent_clock',
        'cfe_rule':'legacy_full_target_deficit_without_workload_or_flexibility_truncation',
        'source_correspondence_only':True,'joint_probability':None,'registered_coupling':False,
        'shared_observed_clock':False,'formal_result':False,'executable_episode_input':False,'solver_calls':0,
        'implementation_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
        'source_window_sha256':sha256(Path(source_window.__file__).read_bytes()).hexdigest(),
        'projection_sha256':sha256(Path(workload_projection.__file__).read_bytes()).hexdigest(),
        'boundary_implementation_sha256':sha256(Path(__file__).with_name('boundary.py').read_bytes()).hexdigest(),
        'mapping_implementation_sha256':sha256(Path(__file__).with_name('common_request_adapter.py').read_bytes()).hexdigest(),
        'cfe_implementation_sha256':sha256(Path(legacy.__file__).read_bytes()).hexdigest()}
    result['pair_identity']=source_window._hash(result)
    return result
