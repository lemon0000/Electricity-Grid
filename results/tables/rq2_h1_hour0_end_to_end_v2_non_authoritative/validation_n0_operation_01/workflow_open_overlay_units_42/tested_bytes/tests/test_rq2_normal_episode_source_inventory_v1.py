from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.normal_episode_source_fixture import packages
from src.rq2_joint_deliverability_boundary_v1 import normal_episode_transport as api


@pytest.fixture
def indirect(tmp_path, monkeypatch):
    config = packages(tmp_path/'packages')
    audit = api.binding.source_pair.source_window.audit
    monkeypatch.setattr(audit, 'ROOT', tmp_path)
    monkeypatch.setattr(audit, '_load_config', lambda path: config)
    source = SimpleNamespace(config_path=str(tmp_path/'config'), upstream_root=str(tmp_path/'upstream'),
        normal_record_path=str(tmp_path/'normal'), pair_declaration_path=str(tmp_path/'pair'))
    return SimpleNamespace(normal_request=SimpleNamespace(source=source)), config


def test_all_indirect_reads_pinned_and_outputs_isolated(indirect, tmp_path):
    inputs, config = indirect
    roots, files = api._indirect_sources(inputs)
    assert len(roots) == 2 and len(files) == 16
    for kind in ('power', 'workload'):
        with pytest.raises(ValueError, match='isolated'):
            api.isolate_outputs(inputs, Path(config['inputs'][kind]['package'])/'episode_non_authoritative')
    for path in files:
        with pytest.raises(ValueError, match='isolated'):
            api.isolate_outputs(inputs, path)
    api.isolate_outputs(inputs, tmp_path/'separate_output')


def test_consumed_member_must_be_declared(indirect):
    inputs, config = indirect
    del config['inputs']['power']['members']['power_system_blocks.csv.gz']
    with pytest.raises(ValueError, match='consumed package members'):
        api._indirect_sources(inputs)


def test_member_escape_refused(indirect, tmp_path):
    inputs, config = indirect
    config['inputs']['workload']['members']['../outside'] = 'a'*64
    with pytest.raises(ValueError, match='package member path'):
        api._indirect_sources(inputs)
