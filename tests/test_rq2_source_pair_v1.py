from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as Q

import pytest

from src.rq2_joint_deliverability_boundary_v1 import source_pair as pair


def declaration():
    return pair.PairDeclaration('training',0,0,3,7,'a'*64,'b'*64,'c'*64,'250',12,'1',
        'declared_relative_offset_pairing_v1','mechanism_assumption')


@pytest.fixture
def supplied(monkeypatch):
    power={'window_identity':'a'*64,'package_manifest_sha256':'d'*64,
        'chain':{'chain_id':'power:training:outage_seed=7'},
        'rows':[{'source_hour':str(i),'cfe_call_fraction':'0.8'} for i in range(3)]}
    workload={'window_identity':'b'*64,'package_manifest_sha256':'e'*64,
        'chain':{'chain_id':'workload:training:single_published_trace','trace_identity_basis':{'training_peak':'10'}},
        'rows':[{'source_relative_hour':str(i),'workload_fraction':'0.2'} for i in range(3)]}
    windows={'power':power,'workload':workload}
    monkeypatch.setattr(pair.source_window,'load_source_window',lambda kind,*args,**kw:deepcopy(windows[kind]))
    return windows


def test_complete_pair_full_cfe_and_independent_clock_mapping(supplied):
    r=pair.prepare_source_pair(declaration())
    assert r['status']=='staged' and len(r['hours'])==3
    assert [h['power_source_hour'] for h in r['hours']]==[1,2,3]
    assert [h['workload_source_hour'] for h in r['hours']]==[1,2,3]
    for h,row in zip(r['hours'],r['rows']):
        assert h['grid_request']==0 and h['cfe_request']==pytest.approx(.8)
        assert h['cfe_request']>h['workload_occupancy']
        assert Q(str(h['workload_occupancy']))*250==Q(str(row['workload_projection']['dc_baseline_mw']))
    assert r['joint_probability'] is None
    assert not any(r[k] for k in ('registered_coupling','shared_observed_clock','formal_result','executable_episode_input'))


def test_unresolved_hour_keeps_whole_window_unresolved(supplied):
    supplied['workload']['rows'][1]['workload_fraction']='1.01'
    r=pair.prepare_source_pair(declaration())
    assert r['status']=='unresolved' and r['hours'] is None
    assert len(r['rows'])==3 and r['rows'][1]['source_hour'] is None
    assert r['rows'][1]['workload_projection']['raw_workload_fraction']=='1.01'
    assert r['rows'][2]['relative_offset']==2


def test_positive_to_zero_not_an_inactive_observation(supplied):
    supplied['workload']['rows'][0]['workload_fraction']='0.00000000000001'
    r=pair.prepare_source_pair(declaration())
    assert r['hours'] is None and r['rows'][0]['source_hour'] is None


@pytest.mark.parametrize('field',['power_window_identity','workload_window_identity'])
def test_external_window_pin(supplied,field):
    with pytest.raises(ValueError,match='window identity'): pair.prepare_source_pair(replace(declaration(),**{field:'f'*64}))


@pytest.mark.parametrize('field,value',[('split','other'),('power_raw_start',True),('workload_raw_start',-1),
    ('hours',0),('outage_seed',False),('hourly_cfe_target','0.9'),('normalized_unit_mw','250.0'),
    ('decimal_places',13),('pairing_rule','observed_joint'),('parameter_role','observed')])
def test_explicit_declaration_validation(field,value):
    with pytest.raises(ValueError): replace(declaration(),**{field:value})


def test_real_two_sources_and_all_inherited_cfe_targets():
    config='0cca33dbfbd934881be3c4e375c76eb668c2ec41ff9bbc7392c2eb3947de18a5'
    base=pair.PairDeclaration('training',0,0,25,20260822,
        'b67411c0a354fde54f61ebb922496d260ccbf4cfe0045567278146673277ec62',
        '7f46bde6c7e6ce7e8a9f5c0640a0463b5ab277521d207ec5105d0c48bbbc2b7d',config,'250',12,'1',
        'declared_relative_offset_pairing_v1','mechanism_assumption')
    for alpha in ('0.5','0.7','0.85','1'):
        result=pair.prepare_source_pair(replace(base,hourly_cfe_target=alpha))
        assert result['status']=='staged' and len(result['hours'])==25
        for row,h in zip(result['rows'],result['hours']):
            deficit=float(row['power_source_row']['cfe_call_fraction'])
            expected=max(float(alpha)-(1-deficit),0)/float(alpha)
            assert h['cfe_request']==expected
            assert h['workload_normalization_sha256']==result['mapping']['workload_normalization_sha256']
            assert Q(str(h['workload_occupancy']))*250==Q(str(row['workload_projection']['dc_baseline_mw']))


def test_real_holdout_overload_is_not_dropped():
    config='0cca33dbfbd934881be3c4e375c76eb668c2ec41ff9bbc7392c2eb3947de18a5'
    p=pair.source_window.load_source_window('power','holdout',4440,25,outage_seed=20260822,expected_config_sha256=config)
    w=pair.source_window.load_source_window('workload','holdout',1190,25,expected_config_sha256=config)
    d=pair.PairDeclaration('holdout',4440,1190,25,20260822,p['window_identity'],w['window_identity'],
        config,'250',12,'0.7','declared_relative_offset_pairing_v1','mechanism_assumption')
    result=pair.prepare_source_pair(d)
    assert result['hours'] is None and len(result['rows'])==25
    missing=[r for r in result['rows'] if r['source_hour'] is None]
    assert len(missing)==5
    assert [r['workload_source_row']['source_relative_hour'] for r in missing]==['1198','1206','1207','1208','1209']
