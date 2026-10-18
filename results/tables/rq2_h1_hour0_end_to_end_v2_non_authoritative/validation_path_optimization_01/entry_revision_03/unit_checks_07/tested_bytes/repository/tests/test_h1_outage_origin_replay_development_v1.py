import pytest

from experiments import audit_h1_outage_origin_replay_development_v1 as m


@pytest.mark.parametrize('field', ['config_sha256', 'grid_source_manifest_sha256',
                                  'cfe_package_manifest_sha256'])
def test_frozen_package_must_correspond_to_config_and_upstreams(monkeypatch, field):
    original = m.json.loads
    def drift_summary(data, *args, **kwargs):
        value = original(data, *args, **kwargs)
        if isinstance(value, dict) and 'n1_chronology_module_sha256' in value:
            value[field] = '0'*64
        return value
    monkeypatch.setattr(m.json, 'loads', drift_summary)
    with pytest.raises(ValueError, match='provenance cross-link differs'):
        m.audit()


@pytest.mark.parametrize('hour', [-1, True, 1.5])
def test_negative_or_noninteger_boundary_not_invented(hour):
    with pytest.raises(ValueError, match='no generated predecessor'):
        m.prefix_overlay((), 7, hour)


def test_prefix_uses_only_requested_horizon(monkeypatch):
    calls = []
    def simulate(components, *, seed, horizon_hours):
        calls.append((components, seed, horizon_hours))
        return (m.chronology.N1OutageEvent(seed, 'test', 'generator', 'G', 0, horizon_hours),)
    monkeypatch.setattr(m.chronology, 'simulate_n_minus_one_events', simulate)
    prefix = m.prefix_overlay(('synthetic',), 7, 2)
    assert calls == [(('synthetic',), 7, 3)]
    assert prefix == (('test', 'generator', 'G'),)*3
    assert not any('end' in field for overlay in prefix for field in overlay)


def test_frozen_generator_provenance_and_unresolved_boundaries():
    result = m.audit()
    assert result['reliability_components'] == 211
    assert result['event_rows_compared'] == 439
    assert result['visible_power_rows_compared'] == 25704
    assert result['source_horizon_hours'] == 8784
    assert result['split_hour'] == 4392
    holdout = [r for r in result['receipts'] if r['split'] == 'holdout']
    assert [r['generated_predecessor']['active_component_uid'] for r in holdout] == ['202_CT_2', '', '']
    assert all(r['horizon_extension_prefix_equal'] for r in holdout)
    training = [r for r in result['receipts'] if r['split'] == 'training']
    assert all(r['generated_predecessor'] is None for r in training)
    assert [r['hour_zero_overlay_for_proposal_only'][2] for r in training] == ['', 'B14', 'A15']
    assert result['unique_operational_inputs_unresolved'] == 6 and result['obligations_removed'] == 0
    assert not result['full_boundary_coverage_verified'] and not result['operational_source_authorized']
    assert not result['formal_execution_ready'] and not result['repair_cap_source_registered']
