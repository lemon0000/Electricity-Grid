"""Canonical definition binding and preserved scientific algorithms, no solver."""
import ast
import json
from pathlib import Path
import types

import pytest

from experiments import h1_bootstrap_integration_development_v7 as bootstrap
from experiments import h1_group_execution_roster_development_v5 as roster
from experiments import h1_historical_n0_verifier_development_v6 as verifier


def test_final_roster_graph_is_bound_once_without_replacing_wrappers(tmp_path):
    bootstrap._PHASE_RUNTIME();roster._RUNTIME()
    route=roster.GroupRoster._replay
    assert type(route) is types.FunctionType
    assert route.__wrapped__.__wrapped__.__qualname__=='GroupRoster._replay'
    with pytest.raises(ValueError,match='definition caller'):
        bootstrap._bind_roster_registry_reader(roster.GroupRoster)
    assert roster.GroupRoster._replay is route
    bootstrap._PHASE_RUNTIME();roster._RUNTIME()
    (tmp_path/'binding_observation.json').write_text(json.dumps(dict(
        definition_binding_complete=True,manual_rebinding_denied=True,new_Jobs=0,real_native_calls=0)))


def test_direct_foreign_consumer_and_unbound_common_entries_are_denied():
    with pytest.raises(ValueError,match='exact Roster5'):
        bootstrap._run_roster_registry_read(object(),'replay')
    with pytest.raises(ValueError,match='known Common definition'):
        bootstrap._bind_common_registry_reader(types.ModuleType('unregistered_common'))


def test_scientific_projection_functions_are_identical_to_verifier5():
    before=Path(verifier.__file__).with_name('h1_historical_n0_verifier_development_v5.py')
    old=ast.parse(before.read_bytes());new=ast.parse(Path(verifier.__file__).read_bytes())
    names=('_copy_context','_context_key','_identity_literal','_replay_prefix','_projection','prepare')
    for name in names:
        original=next(node for node in old.body if isinstance(node,ast.FunctionDef) and node.name==name)
        current=next(node for node in new.body if isinstance(node,ast.FunctionDef) and node.name==name)
        assert ast.dump(original,include_attributes=False)==ast.dump(current,include_attributes=False),name
    old_class=next(node for node in old.body if isinstance(node,ast.ClassDef) and node.name=='N0ValidationOperation')
    new_class=next(node for node in new.body if isinstance(node,ast.ClassDef) and node.name=='N0ValidationOperation')
    for name in ('_start','_seed','_record_prefix','_basis','_execution','prepare','_finish'):
        original=next(node for node in old_class.body if isinstance(node,ast.FunctionDef) and node.name==name)
        current=next(node for node in new_class.body if isinstance(node,ast.FunctionDef) and node.name==name)
        assert ast.dump(original,include_attributes=False)==ast.dump(current,include_attributes=False),name
