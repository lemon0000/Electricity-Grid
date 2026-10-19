"""Family obligations survive grouping; zero solver or Job."""
import json

import pytest
from experiments import h1_phase_manifest_group_development_v1 as m


@pytest.fixture(scope='module')
def raw(): return (m.ROOT/m.symbolic.PROOF).read_bytes()


@pytest.mark.parametrize('family', ['training_lb','training_ub','training_b6_actual','holdout'])
def test_family_projection_preserves_all_siblings(raw,family):
    resolver=m.symbolic.proof._resolver(raw)
    result=m._project(raw,family,0,'a'*64)
    axes=json.loads(raw)['catalog']['axes'][family]
    assert result['catalog_arm_order']==axes['arm']
    assert [s['arm_id'] for s in result['siblings']]==sorted(axes['arm'])
    for sibling in result['siblings']:
        node=resolver.resolve(family,sibling['ordinal'])
        assert sibling['obligation_node']==node
        assert m._project(raw,family,sibling['ordinal'],'a'*64)==result
    assert result['candidate_capacity']==('0' if family=='training_ub' else None)
    assert result['execution_lanes'] is None
    assert all(result[k] is False for k in m.FLAGS)


def test_proof_dispositions_and_unresolved_are_not_rewritten(raw):
    value=json.loads(raw); resolver=m.symbolic.proof._resolver(raw)
    cell=next(c for c in value['cells'] if c['arm_implication_nodes'])
    for family in value['catalog']['axes']:
        axes=value['catalog']['axes'][family]
        point={k:cell[k] if k in ('theta','alpha') else v[0] for k,v in axes.items()}
        result=m._project(raw,family,resolver.encode_coordinate(family,point),'a'*64)
        assert result['unresolved_arms']==sorted(set(axes['arm'])-set(cell['arm_implication_nodes']))
        for s in result['siblings']:
            if s['arm_id'] in cell['arm_implication_nodes']:
                assert s['disposition']!='unresolved_no_certificate'


def test_known_fields_and_identity_separation(raw):
    resolver=m.symbolic.proof._resolver(raw)
    point=resolver.resolve('training_ub',0)['record']['payload']['coordinate']
    a=m._project(raw,'training_ub',0,'a'*64)
    point['capacity']='1/100'
    b=m._project(raw,'training_ub',resolver.encode_coordinate('training_ub',point),'a'*64)
    assert a['group_identity']!=b['group_identity']
    assert a['capacity_declaration_ids']!=b['capacity_declaration_ids']
    assert a['known_scientific_fields']==b['known_scientific_fields']
    assert a['known_scientific_fields']['envelope']['minimum_recovery_hours']==point['theta']['minimum_rest_hours']
    a['siblings'].clear()
    assert m._project(raw,'training_ub',0,'a'*64)['siblings']


@pytest.mark.parametrize('family,ordinal', [('unknown',0),('training_ub',True),('holdout',-1),('training_lb',10**30)])
def test_reject_invalid_coordinates(raw,family,ordinal):
    with pytest.raises(ValueError): m._project(raw,family,ordinal,'a'*64)


def test_reject_unpinned_catalog(raw):
    with pytest.raises(ValueError,match='pinned obligation'):
        m._project(raw+b' ','training_ub',0,'a'*64)


def test_fresh_prepare_and_midread_change(monkeypatch):
    result=m.prepare('training_b6_actual',0)
    assert len(result['siblings'])==1
    assert result['siblings'][0]['arm_id']=='joint-B6'
    original=m.io.read_stable; project=m._project; armed=False
    def arm(*args):
        nonlocal armed
        result=project(*args);armed=True
        return result
    def changed(path,cap):
        view=original(path,cap)
        if armed and path==m.ROOT/m.PROTOCOL:return (view[0]+b' ',view[1])
        return view
    monkeypatch.setattr(m,'_project',arm)
    monkeypatch.setattr(m.io,'read_stable',changed)
    with pytest.raises(ValueError,match='changed during'):
        m.prepare('training_b6_actual',0)


def test_initial_protocol_pin_rejected(monkeypatch):
    original=m.io.read_stable
    def changed(path,cap):
        view=original(path,cap)
        return (view[0]+b' ',view[1]) if path==m.ROOT/m.PROTOCOL else view
    monkeypatch.setattr(m.io,'read_stable',changed)
    with pytest.raises(ValueError,match='pinned'):
        m.prepare('training_ub',0)


def test_external_dependency_is_in_implementation_identity(raw,tmp_path,monkeypatch):
    external=tmp_path/'external_dependency.txt';external.write_bytes(b'first')
    def views():
        return {m.ROOT/m.symbolic.PROOF:m.io.read_stable(m.ROOT/m.symbolic.PROOF,m.symbolic.proof.CAP),
            external:m.io.read_stable(external,100)}
    monkeypatch.setattr(m.symbolic,'_views',views)
    first=m.prepare('training_ub',0)
    external.write_bytes(b'second')
    second=m.prepare('training_ub',0)
    assert first['implementation_sha256']!=second['implementation_sha256']
    assert first['group_identity']==second['group_identity']
