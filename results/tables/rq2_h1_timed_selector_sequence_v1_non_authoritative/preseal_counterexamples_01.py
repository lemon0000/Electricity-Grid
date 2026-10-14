"""Reproduce pre-seal F1/F2 in before_test_02 bytes; not acceptance tests."""
import pytest
from tests.test_h1_timed_selector_sequence_development_v1 import factory,no_solver,owner,m


def test_f1_header_failure_leaves_directories(factory,monkeypatch):
    c=factory();kw=c[3]
    args={k:v for k,v in kw.items() if k not in ('max_archive_bytes','max_timing_archive_bytes','run_configuration')}
    config=m.legacy._configuration(*c[2],args,kw['max_archive_bytes'],kw['run_configuration'])
    monkeypatch.setattr(m,'META_CAP',len(m.legacy._header(c[0],config,'0'*32)))
    with pytest.raises(ValueError,match='timing header'):owner(c)
    assert c[0].exists() and c[1].exists() and (c[0]/'binding.json').exists()


def test_f2_rewritten_initial_snapshot_passes_live_check(factory):
    c=factory();o=owner(c);path=c[0]/'binding.json';raw=path.read_bytes()
    path.rename(c[0].parent/'retained_original_header.json');path.write_bytes(raw)
    fresh=o._view(0)
    for old,new in ((o._initial_view[0],fresh[0]),(o._initial_view[1],fresh[1])):
        old[0].update(new[0]);old[1].update(new[1])
    assert o._view(0)==o._initial_view
    assert o._original_operation.acquire(False)
    try:o._check()
    finally:o._original_operation.release()
