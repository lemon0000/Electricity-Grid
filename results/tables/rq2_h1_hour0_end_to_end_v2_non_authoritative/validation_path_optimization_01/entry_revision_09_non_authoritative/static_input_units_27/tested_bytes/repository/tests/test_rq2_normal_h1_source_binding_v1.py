from copy import deepcopy
from dataclasses import replace
from datetime import timezone
from hashlib import sha256
import json
from pathlib import Path

import pytest

from src.rq2_joint_deliverability_boundary_v1 import normal_h1_source_binding as api
from tests.test_rq2_continuous_grid_normal_v1 import fixture
from tests.test_rq2_normal_h1_short_solve_v1 import budget
from tests.test_rq2_objective_provenance_run_v1 import spec


@pytest.fixture
def supplied(tmp_path, monkeypatch):
    root = tmp_path/'upstream'
    root.mkdir()
    (root/'SHA256SUMS').write_bytes(b'synthetic-current-source\n')
    manifest = sha256((root/'SHA256SUMS').read_bytes()).hexdigest()
    config = tmp_path/'source.yaml'
    config.write_bytes(b'{}')
    state = dict(data=fixture(2).data, workload='0.2', power_change={}, workload_change={})
    monkeypatch.setattr(api.rts, 'RTS_GMLC_MANIFEST_SHA256', manifest)
    monkeypatch.setattr(api.rts, 'verify_sha256_manifest', lambda root: True)
    monkeypatch.setattr(api.rts, 'load_rts_gmlc_chronological_data', lambda root: state['data'])
    monkeypatch.setattr(api.windows.audit, '_load_config', lambda p: {'inputs':{'power':{},'workload':{}}})
    monkeypatch.setattr(api.windows.audit, '_verify_package', lambda b,k: (root,{'grid_source_manifest_sha256':manifest}))
    def load(kind, split, raw_start, hours, **kwargs):
        assert hours == 1
        row = state['data'].hourly_points[raw_start if kind == 'power' else 0]
        if kind == 'power':
            record = dict(split=split,source_hour=str(raw_start), timestamp=row.timestamp.replace(tzinfo=timezone.utc).isoformat(),
                system_load_mw=str(sum(row.demand_by_bus_mw.values())), outage_seed=str(kwargs['outage_seed']),
                cfe_call_fraction='0.4')
            record.update(state['power_change'])
        else:
            record = dict(split=split,source_relative_hour=str(raw_start), workload_fraction=state['workload'])
            record.update(state['workload_change'])
        value = dict(kind=kind, split=split, rows=[record], package_manifest_sha256=manifest,
            raw_start=raw_start,hours=hours,outage_seed=kwargs.get('outage_seed'),config_sha256=kwargs['expected_config_sha256'],
            continuous_power_source_hours=[raw_start+1] if kind=='power' else None,
            chain={'split':split,'start':raw_start})
        value.update(status='DRAFT_NONAUTHORITATIVE',members={},
            implementation_sha256=sha256(Path(api.windows.__file__).read_bytes()).hexdigest(),
            audit_implementation_sha256=sha256(Path(api.windows.audit.__file__).read_bytes()).hexdigest(),
            python_version='test',pyyaml_version='test',solver_calls=0,formal_result=False,registered_coupling=False,
            shared_observed_clock=False,continuous_dispatch_verified=False,workload_fraction_clipped=False,
            executable_episode_input=False)
        value['window_identity'] = api.windows._hash(value)
        return value
    monkeypatch.setattr(api.windows, 'load_source_window', load)
    d = api.H1SourceDeclaration('training',0,0,7,sha256(config.read_bytes()).hexdigest())
    return root, config, d, state


def load(supplied, declaration=None):
    root, config, d, _ = supplied
    return api.load_pinned_current(declaration or d, root, config_path=config)


def assemble(supplied, value):
    root, config, _, _ = supplied
    return api.assemble_pinned_current(value, root, expected_identity=value.identity,
        relative_hour=0, dc_bus=1, config_path=config)


def test_current_source_binding_and_reconstruction(supplied):
    value = load(supplied)
    assert value.network.data.hourly_points == ()
    assert value.raw_workload == '0.2'
    packet = assemble(supplied, value)
    assert packet.inputs.request.dc_requested_mw == (50.,)
    audit = json.loads(value.audit_payload)
    assert audit['source_files_verified'] and audit['source_correspondence_verified']
    assert not any(audit[k] for k in ('source_authenticated','selection_registered','formal_result',
        'native_execution_authenticated','observed_power_mapping','shared_observed_clock'))


@pytest.mark.parametrize('change', ['split','seed','workload_index','power_index','cfe_outage'])
def test_lineage_changes_do_not_enter_normal_computational_key(supplied, change):
    a = load(supplied)
    first = assemble(supplied,a)
    root, config, d, state = supplied
    if change == 'split':
        d = replace(d,split='holdout')
    elif change == 'seed':
        d = replace(d,outage_seed=8)
    elif change == 'workload_index':
        d = replace(d,workload_raw_hour=17)
    elif change == 'power_index':
        d = replace(d,power_raw_hour=1)
    else:
        state['power_change'].update(cfe_call_fraction='0.9')
    b = load(supplied,d)
    second = assemble(supplied,b)
    assert a.identity != b.identity
    assert api.h1.causal_key(first,spec(),budget()) == api.h1.causal_key(second,spec(),budget())


def test_current_physical_change_changes_key_and_old_receipt_is_rejected(supplied):
    a = load(supplied)
    first = assemble(supplied,a)
    supplied[3]['workload'] = '0.3'
    with pytest.raises(ValueError,match='current sources'):
        assemble(supplied,a)
    b = load(supplied)
    assert api.h1.causal_key(first,spec(),budget()) != api.h1.causal_key(assemble(supplied,b),spec(),budget())


@pytest.mark.parametrize('field,value', [('source_hour','1'),('timestamp','2020-01-02T00:00:00+00:00'),('system_load_mw','999')])
def test_current_rts_correspondence_mismatch_rejected(supplied,field,value):
    supplied[3]['power_change'][field] = value
    with pytest.raises(ValueError):
        load(supplied)


def test_workload_index_and_unavailable_rts_rejected(supplied):
    supplied[3]['workload_change']['source_relative_hour'] = '2'
    with pytest.raises(ValueError):
        load(supplied)
    supplied[3]['workload_change'].clear()
    with pytest.raises((ValueError,IndexError)):
        load(supplied,replace(supplied[2],power_raw_hour=2))


def test_raw_above_one_retained_then_mapping_rejects(supplied):
    supplied[3]['workload'] = '1.250000'
    value = load(supplied)
    assert value.raw_workload == '1.250000'
    with pytest.raises(ValueError,match='mapping'):
        assemble(supplied,value)


def test_forged_rehashed_row_cannot_replace_rebuilt_source(supplied):
    value = load(supplied)
    value.row.demand_by_bus_mw[1] += 1
    object.__setattr__(value,'identity',api._identity(value))
    with pytest.raises(ValueError,match='current sources'):
        assemble(supplied,value)
    with pytest.raises(ValueError,match='identity'):
        api.validate_pinned_current(object(),supplied[0],expected_identity='0'*64,config_path=supplied[1])


def test_manifest_config_and_mid_load_drift(supplied,monkeypatch):
    value = load(supplied)
    original = api.rts.load_rts_gmlc_chronological_data
    def change(root):
        result = original(root)
        (root/'SHA256SUMS').write_bytes(b'changed')
        return result
    monkeypatch.setattr(api.rts,'load_rts_gmlc_chronological_data',change)
    with pytest.raises(ValueError,match='manifest'):
        assemble(supplied,value)


def test_future_rows_not_exposed_or_visited_after_loader(supplied):
    class CurrentOnly:
        def __len__(self):
            return 9000
        def __getitem__(self,index):
            assert index == 0
            return fixture(1).data.hourly_points[0]
        def __iter__(self):
            raise AssertionError('future rows iterated')
    state = supplied[3]
    state['data'] = replace(state['data'],hourly_points=CurrentOnly())
    value = load(supplied)
    assert value.network.data.hourly_points == ()
    assert len(assemble(supplied,value).inputs.data.hourly_points) == 1


def test_real_pinned_current_source_zero_solver():
    config = api.windows.audit.DEFAULT_CONFIG
    d = api.H1SourceDeclaration('training',0,0,20260822,sha256(config.read_bytes()).hexdigest())
    value = api.load_pinned_current(d,Path('data/raw/rts_gmlc/v0.2.3/upstream'))
    audit = json.loads(value.audit_payload)
    assert audit['grid_manifest_sha256'] == api.rts.RTS_GMLC_MANIFEST_SHA256
    assert audit['power_source_row']['source_hour'] == '0'
    assert audit['workload_source_row']['source_relative_hour'] == '0'
    assert value.network.data.hourly_points == ()


@pytest.mark.parametrize('field,value', [('continuous_power_source_hours',[2]),('raw_start',1),('split','holdout'),('hours',2)])
def test_loaded_window_coordinates_are_cross_checked(supplied,monkeypatch,field,value):
    original = api.windows.load_source_window
    def wrong(kind,*a,**k):
        result=original(kind,*a,**k)
        if kind=='power':
            result[field]=value
        return result
    monkeypatch.setattr(api.windows,'load_source_window',wrong)
    with pytest.raises(ValueError):
        load(supplied)


def test_foreign_grid_manifest_rejected(supplied,monkeypatch):
    monkeypatch.setattr(api.windows.audit,'_verify_package',lambda b,k:(supplied[0],{'grid_source_manifest_sha256':'0'*64}))
    with pytest.raises(ValueError,match='manifest differ'):
        load(supplied)


def test_config_change_and_final_package_recheck(supplied,monkeypatch):
    supplied[1].write_bytes(b'changed')
    with pytest.raises(ValueError,match='hash mismatch'):
        load(supplied)
    supplied[1].write_bytes(b'{}')
    original=api.windows.audit._verify_package
    calls=[]
    def changed(binding,kind):
        calls.append(kind)
        if calls==['power','power','workload']:
            raise ValueError('package changed during observation assembly')
        return original(binding,kind)
    monkeypatch.setattr(api.windows.audit,'_verify_package',changed)
    with pytest.raises(ValueError,match='package changed'):
        load(supplied)


def test_implementation_drift_rejected(supplied,monkeypatch):
    original=api.implementation_identity
    calls=[]
    def drift():
        calls.append(1)
        return original() if len(calls)==1 else '0'*64
    monkeypatch.setattr(api,'implementation_identity',drift)
    with pytest.raises(ValueError,match='implementation drift'):
        load(supplied)


@pytest.mark.parametrize('change', ['raw_bool','hour_bool','continuous_bool','row_integer','seed_integer',
    'stale_hash','foreign_schema','positive_authority','foreign_implementation'])
def test_mutable_window_evidence_must_be_canonical_and_self_consistent(supplied,monkeypatch,change):
    original=api.windows.load_source_window
    def wrong(kind,*a,**k):
        value=original(kind,*a,**k)
        if kind != 'power':
            return value
        pin=value.pop('window_identity')
        if change=='raw_bool': value['raw_start']=False
        elif change=='hour_bool': value['hours']=True
        elif change=='continuous_bool': value['continuous_power_source_hours']=[True]
        elif change=='row_integer': value['rows'][0]['source_hour']=0
        elif change=='seed_integer': value['rows'][0]['outage_seed']=7
        elif change=='foreign_schema': value['foreign']=False
        elif change=='positive_authority': value['formal_result']=True
        elif change=='foreign_implementation': value['implementation_sha256']='0'*64
        else: value['rows'][0]['cfe_call_fraction']='0.8'
        value['window_identity']=pin if change=='stale_hash' else api.windows._hash(value)
        return value
    monkeypatch.setattr(api.windows,'load_source_window',wrong)
    with pytest.raises(ValueError):
        load(supplied)
