"""One cold canonical Handoff6 anchor, without creating an experiment owner."""
import pytest


def test_real_anchor_check_and_guarded_constructor_reach_original_body(monkeypatch,tmp_path):
    from experiments import h1_selector_phase_handoff_development_v6 as handoff
    handoff._CHECK()
    # A genuine guarded method must reach the original argument validation.
    # No Parent, lease, Job, archive or native execution is created.
    with pytest.raises(TypeError,match='genesis|common'):
        handoff.Handoff(None,None,{},retain_head=lambda *a:None,
            max_packet_bytes=4096,max_record_bytes=1024,max_archive_bytes=4096)
    handoff._CHECK()
    wrapped=handoff.Handoff.consume
    captured=dict(zip(wrapped.__code__.co_freevars,wrapped.__closure__))['check'].cell_contents
    with monkeypatch.context() as patch:
        patch.setattr(handoff,'all',lambda *a:False,raising=False)
        with pytest.raises(ValueError,match='definition-time Handoff'):captured()
