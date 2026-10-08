import pytest

from experiments import h1_lifecycle_timing_gap_audit_development_v1 as api


@pytest.mark.parametrize('write,read', [(0, 0), (1000, 0), (0, 2000), (1000, 2000)])
def test_terminal_tail_is_outside_real_journal_window(tmp_path, write, read):
    out = api.probe(tmp_path/'journal', terminal_io_ns=write, fresh_inspection_ns=read)
    assert out['journal_recorded_ns'] == 100
    assert out['enclosing_observed_ns'] == 100 + write + read
    assert out['omitted_tail_ns'] == write + read
    assert not out['component_budget_verified']
    # The global test seams must be restored, including when used repeatedly.
    assert api.journal.inspect.__module__ == api.journal.__name__


@pytest.mark.parametrize('value', [True, -1, 1.5, 10**12+1])
def test_invalid_delay_does_not_create_output(tmp_path, value):
    with pytest.raises(ValueError):
        api.probe(tmp_path/'journal', terminal_io_ns=value, fresh_inspection_ns=0)
    assert not (tmp_path/'journal').exists()


def test_exclusive_output_and_patch_restored_on_failure(tmp_path):
    root = tmp_path/'journal'
    api.probe(root, terminal_io_ns=1, fresh_inspection_ns=2)
    write, inspect = api.journal.io.write_metadata, api.journal.inspect
    with pytest.raises(FileExistsError):
        api.probe(root, terminal_io_ns=1, fresh_inspection_ns=2)
    assert api.journal.io.write_metadata is write and api.journal.inspect is inspect
