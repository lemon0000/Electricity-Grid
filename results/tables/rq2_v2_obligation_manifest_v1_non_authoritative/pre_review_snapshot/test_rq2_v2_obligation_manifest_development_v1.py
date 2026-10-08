from collections import Counter
import copy
from dataclasses import FrozenInstanceError
from fractions import Fraction as Q
import json
from math import prod

import pytest

from experiments import rq2_v2_obligation_manifest_development_v1 as m


@pytest.fixture(scope='module')
def resolver(): return m.build()


@pytest.fixture(scope='module')
def catalog(resolver): return resolver.data()['catalog']


def coordinate(catalog,family,**indices):
    return {name:values[indices.get(name,0)] for name,values in catalog['axes'][family].items()}


def resolved(resolver,catalog,family,**indices):
    point = coordinate(catalog,family,**indices)
    return resolver.resolve(family,resolver.encode_coordinate(family,point))


@pytest.mark.parametrize('family',tuple(m.MISSING))
def test_actual_radix_boundaries_and_roundtrip(resolver,catalog,family):
    order = catalog['axis_order'][family]
    lengths = [len(catalog['axes'][family][a]) for a in order]
    count = catalog['identity_counts'][family]
    points = {0,count-1}
    # Every digit boundary, in both the first and last higher-digit context.
    for i,length in enumerate(lengths):
        stride = prod(lengths[i+1:])
        for prefix in (0,count-length*stride):
            for digit in range(1,length):
                for delta in (-1,0,1):
                    point = prefix+digit*stride+delta
                    if 0 <= point < count: points.add(point)
    for point in points:
        value = resolver.resolve(family,point)['record']['payload']
        assert resolver.encode_coordinate(family,value['coordinate']) == point
        oracle = m.inventory.obligation_at(catalog,family,point)
        assert m.io.same(value['coordinate'],oracle['coordinate'])
        assert value['axis_order'] == order
        assert value['obligation_sha256'] == m.io.digest(m.io.encode(dict(schema=m.SCHEMA,
            catalog_sha256=m.CATALOG_PIN,family=family,ordinal=point,axis_order=order,coordinate=value['coordinate'])))


def test_all_cells_all_arms_truth_table(resolver,catalog):
    hits,unknown = 0,0
    for ti,theta in enumerate(catalog['axes']['training_lb']['theta']):
        for ai,alpha in enumerate(catalog['axes']['training_lb']['alpha']):
            excluded = Q(alpha) >= (Q('0.05') if Q(theta['flexible_fraction']) == Q('0.5') else Q('0.03'))
            for arm in range(4):
                lb = resolved(resolver,catalog,'training_lb',theta=ti,alpha=ai,arm=arm,power=8,workload=17)
                payload = lb['record']['payload']
                applies = excluded and arm != 0
                assert payload['disposition'] == ('direct_analytic_witness' if applies else 'unresolved_no_certificate')
                assert (payload['missing_dependency'] is None) == applies
                assert payload['individual_pair_failure'] is False
                hits += applies
                unknown += not applies
                holdout = resolved(resolver,catalog,'holdout',theta=ti,alpha=ai,arm=arm)['record']['payload']
                assert holdout['disposition'] == ('conditional_prerequisite_false_not_executed' if applies else 'unresolved_no_certificate')
                assert holdout['frozen_training_ub'] is None
                assert holdout['native_status'] is None
            actual = resolved(resolver,catalog,'training_b6_actual',theta=ti,alpha=ai)['record']['payload']
            assert actual['disposition'] == ('conditional_prerequisite_false_not_executed' if excluded else 'unresolved_no_certificate')
    assert (hits,unknown) == (5568,2032)


def test_direct_pair_complete_window_match_and_D_preserved(resolver,catalog):
    lb = resolved(resolver,catalog,'training_lb',alpha=99,arm=1,power=8,workload=17)
    other = resolved(resolver,catalog,'training_lb',alpha=99,arm=1,power=9,workload=17)
    assert lb['record']['payload']['disposition'] == 'direct_analytic_witness'
    assert other['record']['payload']['disposition'] == 'not_scheduled_due_to_parent_cell_proof'
    assert lb['record']['edges'] == other['record']['edges']
    assert lb['node_id'] != other['node_id']
    probes = [resolved(resolver,catalog,'training_ub',alpha=99,arm=1,power=8,workload=17,capacity=i) for i in (0,100)]
    assert probes[0]['record']['edges'] == probes[1]['record']['edges'] == lb['record']['edges']
    assert [p['record']['payload']['coordinate']['capacity'] for p in probes] == ['0','1']
    assert probes[0]['node_id'] != probes[1]['node_id']
    assert 'capacity' not in lb['record']['payload']['coordinate']
    for probe in probes: assert probe['record']['payload']['disposition'] == 'direct_analytic_witness'


def test_graph_exact_topology_and_no_solver_reuse(resolver,catalog):
    data = resolver.data()
    assert len(data['cells']) == 1900
    assert len(data['nodes']) == 8019
    assert Counter(n['record']['kind'] for n in data['nodes']) == dict(approved_contract=1,
        obligation_catalog=1,training_source_witness=1,exact_arithmetic_group=300,
        positive_local_contradiction=292,cell_contradiction_binding=1856,arm_cell_implication=5568)
    seen = set()
    for node in data['nodes']:
        assert node['node_id'] == m.io.digest(m.io.encode(node['record']))
        assert node['node_id'] not in seen
        for edge in node['record']['edges']:
            assert edge['parent'] in seen
            assert edge['kind'] in ('logical_implication','proof_reference')
            assert edge['solver_reuse_edge'] is False
        for key in ('solver_task_id','causal_key','runtime_request'): assert node['record'][key] is None
        seen.add(node['node_id'])
    assert all(data[k] is False for k in m.FLAGS)
    assert data['verified_solver_reuse_edges'] == []
    assert data['solver_calls'] == 0
    for family,total in catalog['identity_counts'].items():
        cover = data['coverage']
        assert total == cover['affected_identity_counts'][family]+cover['remaining_identity_counts'][family]
    # Different non-f theta coordinates preserve identities with shared arithmetic.
    cells = [c for c in data['cells'] if c['alpha_index']==99 and Q(c['theta']['flexible_fraction'])==Q('.05')]
    assert len(cells)==3 and len({c['cell_sha256'] for c in cells})==3
    assert len({c['arithmetic_node'] for c in cells})==1


def test_snapshot_has_no_mutable_output_aliases(resolver,catalog):
    before = resolver.resolve('training_lb',0)
    value = resolver.data();value['catalog']['axis_order']['training_lb'].reverse()
    value['cells'][0]['arm_implication_nodes']['network-only'] = 'forged'
    changed = resolver.resolve('training_lb',0);changed['record']['payload']['coordinate']['theta']['flexible_fraction'] = '1'
    assert resolver.resolve('training_lb',0) == before
    with pytest.raises(FrozenInstanceError): resolver._raw = b'{}'
    point = coordinate(catalog,'training_lb')
    point = dict(reversed(list(point.items())))
    assert resolver.encode_coordinate('training_lb',point) == 0


@pytest.mark.parametrize('ordinal',[True,False,1.0,'1',-1,111294400])
def test_ordinal_rejects_noncanonical_values(resolver,ordinal):
    with pytest.raises(ValueError): resolver.resolve('training_lb',ordinal)


@pytest.mark.parametrize('family',['unknown',None,True,1])
def test_unknown_family(resolver,family):
    with pytest.raises(ValueError): resolver.resolve(family,0)


def test_coordinate_rejects_extra_axis_bool_alias_and_changed_window(resolver,catalog):
    point = copy.deepcopy(coordinate(catalog,'training_lb'))
    with pytest.raises(ValueError): resolver.encode_coordinate('training_lb',dict(point,capacity='1'))
    point['power']['source_start'] = False
    with pytest.raises(ValueError): resolver.encode_coordinate('training_lb',point)
    point = copy.deepcopy(coordinate(catalog,'training_lb',power=8))
    point['power']['outage_seed'] += 1
    with pytest.raises(ValueError): resolver.encode_coordinate('training_lb',point)


@pytest.mark.parametrize('path',[m.CATALOG,m.REPORT,'src/rq2_joint_deliverability_boundary_v1/cfe_preallocation.py'])
def test_catalog_report_code_pin_drift(monkeypatch,path):
    original = m.io.read_stable
    def changed(name,cap):
        raw,stamp = original(name,cap)
        return (raw+b' ',stamp) if name == m.ROOT/path else (raw,stamp)
    monkeypatch.setattr(m.io,'read_stable',changed)
    with pytest.raises(ValueError,match='pinned .*input differs'): m.build()


def test_late_source_change_after_compile_rejected(monkeypatch):
    compile_original,read_original = m._compile,m.io.read_stable
    def changed(name,cap):
        raw,stamp = read_original(name,cap)
        target = m.ROOT/'src/rq2_joint_deliverability_boundary_v1/cfe_preallocation.py'
        return (raw+b' ',stamp) if name == target else (raw,stamp)
    def compile_then_change(*args):
        result = compile_original(*args)
        monkeypatch.setattr(m.io,'read_stable',changed)
        return result
    monkeypatch.setattr(m,'_compile',compile_then_change)
    with pytest.raises(ValueError,match='proof source changed during manifest compilation'): m.build()


def test_fresh_inspect_and_reject_graph_or_axis_rewrite(resolver,tmp_path):
    path = tmp_path/'manifest.json';m.io.write_new(path,resolver.raw)
    reopened = m.inspect(path,expected_sha256=resolver.identity)
    assert reopened.raw == resolver.raw
    altered = resolver.data();altered['catalog']['axis_order']['training_lb'].reverse()
    altered['nodes'][-1]['record']['runtime_request'] = {'forged':True}
    raw = m.io.encode(altered);bad = tmp_path/'altered.json';m.io.write_new(bad,raw)
    with pytest.raises(ValueError,match='fresh manifest reconstruction differs'):
        m.inspect(bad,expected_sha256=m.io.digest(raw))
    with pytest.raises(ValueError,match='external manifest pin differs'):
        m.inspect(bad,expected_sha256=resolver.identity)
