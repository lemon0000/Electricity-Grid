"""Exact successor types import coherently; unbound registry routes fail closed."""
from pathlib import Path
import sys

import pytest


def test_exact_typed_successor_graph_and_denied_genesis_loader_rollback(tmp_path):
    from experiments import h1_selector_phase_handoff_development_v7 as h
    from experiments import h1_selector_post_negative_validation_development_v4 as post
    from experiments import h1_common_genesis_validation_operation_development_v3 as genesis_bridge
    from experiments import h1_common_genesis_validation_routes_development_v3 as routes
    from experiments import h1_common_owner_genesis_development_v3 as genesis
    from experiments import h1_group_n0_common_input_binding_development_v11 as common_base
    from experiments import h1_group_execution_roster_development_v5 as roster
    from experiments import h1_bootstrap_integration_development_v7 as bootstrap
    from experiments import h1_selector_parent_controller_development_v5 as parent
    from experiments import h1_selector_input_snapshot_development_v3 as snapshot
    assert h.parent is post.parent is parent
    assert h.common is snapshot.common is genesis
    assert genesis.common is common_base and common_base.roster_api is roster
    assert common_base.bootstrap is roster.bootstrap is h.bootstrap is bootstrap
    assert parent.worker is parent.preparation.worker is parent.inspection.worker is parent.lifecycle.worker
    assert parent.worker.snapshot is snapshot
    assert h.validation.__name__=='experiments.h1_common_validation_operation_development_v5'
    assert h.parent_validation is post.kernel
    assert h.parent_validation.__name__=='experiments.h1_selector_parent_validation_operation_development_v5'
    assert tuple(name for name,_ in routes.ROUTES)==(
        'h1_operation_historical_witness_development_v8',
        'h1_phase_exact_source_current_development_v9',
        'h1_group_n0_common_input_binding_development_v9')
    with pytest.raises(ValueError,match='independent Common registry bridge is not yet bound'):
        routes.load(genesis_bridge)
    package=sys.modules['experiments']
    for name,_ in routes.ROUTES:
        assert 'experiments.'+name not in sys.modules and not hasattr(package,name)
    cleanup=bootstrap.phase_manifest.observation._CLEANUP_DIAGNOSTICS()
    assert cleanup['active_operations']==cleanup['abandoned_pending_operations']==0
    assert not list(tmp_path.iterdir())
    assert all(Path(module.__file__).name==module.__name__.split('.')[-1]+'.py'
        for module in (h,post,genesis,common_base,roster,parent,snapshot))
