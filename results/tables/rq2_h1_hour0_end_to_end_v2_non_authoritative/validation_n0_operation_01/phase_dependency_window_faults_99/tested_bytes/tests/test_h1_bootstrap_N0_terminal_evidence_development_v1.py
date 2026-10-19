"""Exact N0 evidence preparation; synthetic Job only, no terminal publication."""
import json
import os
from pathlib import Path

import pytest

from tests.test_h1_owned_bootstrap_numerical_development_v1 import (
    m, example, setup, environment, supplied, no_solver, saved, synthetic_reports,
    test_owned_n0_synthetic_job_and_independent_historical_replay as run_n0,
)

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='bounded synthetic Windows Job')


def test_N0_preparation_requires_live_bootstrap_operation(setup):
    owner=setup.open()
    try:
        with pytest.raises(ValueError,match='active bootstrap operation'):
            owner._prepare_N0_terminal()
    finally:owner.close()


def test_N0_preparation_replays_and_rejects_protocol_suffix(
        setup,environment,synthetic_reports,tmp_path,monkeypatch):
    continuation=m.BootstrapOwner._continue_owned_development
    prepared_bodies=[]
    def prepare_after_close(owner):
        result=continuation(owner)
        rows=owner._bootstrap.rows();global_rows=owner._global.rows()
        root=Path(owner.roots['controller'])
        (root/'job_000_non_authoritative/scratch_non_authoritative/retained_synthetic_scratch.bin').write_bytes(b'opaque')
        prepared=[];prepare=m.historical.prepare
        def capture_prepare(*args,**kwargs):
            value=prepare(*args,**kwargs);prepared.append(value);return value
        with monkeypatch.context() as context:
            context.setattr(m.historical,'prepare',capture_prepare)
            body=owner._prepare_N0_terminal()
        prepared_bodies.append(body)
        assert body['controller_terminal_sha256']==result['obligation_terminal_sha256']
        assert body['parent_head']==result['parent_head']
        assert body['completed_hours']==1 and body['scratch_contents_audited'] is False
        assert all(body[k] is False for k in m.FLAGS)
        assert owner._bootstrap.rows()==rows and owner._global.rows()==global_rows
        # Every legal future stream name must still fail an exact N0 terminal.
        suffixes=[('job_001_non_authoritative',True),
            ('clock_bridge_non_authoritative/001',True),
            ('obligation_non_authoritative/001.binding.json',False),
            ('source_parent_non_authoritative/hour_001_non_authoritative',True),
            ('source_parent_non_authoritative/parent_events_non_authoritative/003',True),
            ('source_parent_non_authoritative/parent_anchor_non_authoritative/003.json',False)]
        for index,(name,directory) in enumerate(suffixes):
            path=root/name
            if directory:path.mkdir()
            else:path.write_bytes(b'{}')
            with pytest.raises(ValueError):owner._prepare_N0_terminal()
            path.rename(tmp_path/f'preserved_suffix_{index}')
        # A retained-head callback cannot replace the original operation nonce
        # while the historical reader runs and then obtain a terminal body.
        nonce=owner._operation_nonce
        def changed_nonce(*args,**kwargs):
            owner._operation_nonce=object()
            return prepared[0]
        with monkeypatch.context() as context:
            context.setattr(m.historical,'prepare',changed_nonce)
            with pytest.raises(ValueError,match='N0 evidence operation changed'):
                owner._prepare_N0_terminal()
        owner._operation_nonce=nonce
        # The final observation itself is also an effect boundary. Cached
        # evidence is a test-only seam here; the positive case above performed
        # the real double numerical replay before capturing this envelope.
        observe=owner._observe_N0
        for fault in ('nonce','local_head','global_head'):
            calls=[];local_head=owner._bootstrap.head;global_head=owner._global.head
            def change_after_observation(*args):
                observe(*args);calls.append(1)
                if len(calls)==2:
                    if fault=='nonce':owner._operation_nonce=object()
                    elif fault=='local_head':owner._bootstrap.head='0'*64
                    else:owner._global.head='0'*64
            with monkeypatch.context() as context:
                context.setattr(owner,'_observe_N0',change_after_observation)
                context.setattr(m.historical,'prepare',lambda *a,**k:prepared[0])
                with pytest.raises(ValueError,match='operation changed|retained journal head'):
                    owner._prepare_N0_terminal()
            assert len(calls)==2
            owner._operation_nonce=nonce
            owner._bootstrap.head=local_head;owner._global.head=global_head
        assert owner._bootstrap.rows()==rows and owner._global.rows()==global_rows
        return result
    monkeypatch.setattr(m.BootstrapOwner,'_continue_owned_development',prepare_after_close)
    run_n0(setup,environment,synthetic_reports,tmp_path,monkeypatch,'n0')
    assert len(prepared_bodies)==1
