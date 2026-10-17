"""Real owner persistence with explicit synthetic source and numerical records."""
import json
import pytest
from experiments import h1_phase_owner_development_v2 as owner
from tests import test_h1_phase_owner_development_v1 as cases
from tests.test_h1_persistent_owner_development_v1 import setup as legacy_setup

@pytest.fixture
def setup(legacy_setup,monkeypatch):
    monkeypatch.setattr(cases,'m',owner)
    return cases.setup.__wrapped__(legacy_setup,monkeypatch)

@pytest.fixture
def holder(setup,tmp_path):
    yield from cases.holder.__wrapped__(setup,tmp_path)

def tree(root):
    return {str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}

def test_next_hour_refused_before_any_durable_append(setup,holder,monkeypatch):
    with cases.bootstrap(setup,holder,monkeypatch) as current:
        heads=current.heads
        before=tree(setup.root.parent)
        tickets=holder.inspect()
        report=current.inspect(expected_heads=heads)
        assert report.completed_hours==1 and not report.continuation_available
        assert not report.episode_terminal and not report.pending_attempt
        with pytest.raises(ValueError,match='N0 owner source scope'):
            current.prepare_next(expected_heads=heads)
        assert current.heads==heads and holder.inspect()==tickets
        assert tree(setup.root.parent)==before
        assert not current.poisoned
        header=json.loads(current._header_bytes())
        assert header['declared_episode_hours']==192
        assert header['source_adapter_scope']=='N0_historical_saved_prefix'
    with cases.owner(setup,holder,expected_heads=heads) as reopened:
        assert reopened.inspect(expected_heads=heads).completed_hours==1

def test_halted_N0_can_record_honest_episode_terminal(setup,holder,monkeypatch):
    with cases.bootstrap(setup,holder,monkeypatch,actual=False) as current:
        report=current.prepare_next(expected_heads=current.heads)
        assert report.episode_terminal and not report.continuation_available
        assert not report.pending_attempt

@pytest.mark.parametrize('hour',[1,191,True,-1])
def test_fresh_rejects_outside_N0_before_source(hour,monkeypatch):
    def denied(*a,**kw):raise AssertionError('source must not be called')
    monkeypatch.setattr(owner.source,'prepare',denied)
    with pytest.raises(ValueError,match='N0 owner source scope'):
        owner._fresh(None,hour,'a'*64)
