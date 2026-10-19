"""A successor implementation needs its own symbolic profile, preserving science."""
from dataclasses import fields
from hashlib import sha256

from experiments import h1_bootstrap_integration_development_v4 as m
from tests.test_h1_bootstrap_integration_development_v1 import example


def test_successor_symbolic_profile_binds_new_implementation_without_relabelling_predecessor(example,tmp_path):
    prior_path,prior_pin,prior_snapshot,prior_config,_=example
    configuration=m.RunConfiguration(**{f.name:getattr(prior_config,f.name) for f in fields(m.RunConfiguration)})
    before=prior_snapshot.data()['declared_static_profile'];after=configuration.declared_profile()
    assert {key for key in before if before[key]!=after[key]}=={'implementation_sha256'}
    snapshot=m.symbolic.build(m.symbolic.StaticProfile(**after))
    path=tmp_path/'successor_symbolic_profile.json';path.write_bytes(snapshot.raw)
    inspected=m.symbolic.inspect(path,expected_sha256=sha256(snapshot.raw).hexdigest())
    assert inspected.data()['declared_static_profile']==after
    assert inspected.resolve('training_ub',0)['kind']=='potential_N_slot'
    assert sha256(prior_path.read_bytes()).hexdigest()==prior_pin
