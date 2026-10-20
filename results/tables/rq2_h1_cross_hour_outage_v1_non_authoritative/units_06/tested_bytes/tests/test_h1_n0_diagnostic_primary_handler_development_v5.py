"""Run the original successor test handler on faults, without any N0 execution."""
import ast
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest


def lifecycle(version):
    path=Path(__file__).with_name(f'test_h1_registry_validation_retained_n0_development_v{version}.py')
    tree=ast.parse(path.read_bytes())
    test=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name.startswith('test_cold_'))
    block=next(node for node in test.body if isinstance(node,ast.Try)
        and any(handler.name=='primary' for handler in node.handlers))
    return tree,block


@pytest.mark.parametrize('fault',['none','cleanup','repr','note'])
def test_original_successor_handler_keeps_primary_if_secondary_reporting_fails(fault,tmp_path):
    _,block=lifecycle(5)
    class UnitBase(BaseException):
        @staticmethod
        def add_note(*args):raise UnitBase('injected note failure')
    class BadRepr(OSError):
        def __repr__(self):raise RuntimeError('injected cleanup repr failure')
    alias=UnitBase if fault=='note' else BaseException
    primary=UnitBase('primary') if fault=='note' else RuntimeError('primary')
    cleanup=UnitBase('cleanup') if fault=='note' else BadRepr('cleanup') if fault=='repr' else OSError('cleanup')
    calls=[]
    def close():
        calls.append('close')
        if fault!='none':raise cleanup
    def body():raise primary
    owner=SimpleNamespace(close=close)
    tree=ast.parse('def invoke(owner):\n    try:\n        body()\n    except BaseException:\n        raise\n')
    tree.body[0].body[0].handlers=deepcopy(block.handlers)
    tree.body[0].body[0].orelse=deepcopy(block.orelse)
    space=dict(body=body,BaseException=alias)
    exec(compile(ast.fix_missing_locations(tree),__file__,'exec'),space)
    with pytest.raises(type(primary)) as caught:space['invoke'](owner)
    assert caught.value is primary and calls==['close']
    (tmp_path/'primary_handler_observation.json').write_text(json.dumps(dict(
        fault=fault,primary_identity_preserved=True,close_calls=len(calls),new_N0_Jobs=0,native_calls=0)),encoding='utf-8')


def test_success_path_and_all_other_test_bytes_keep_predecessor_structure(tmp_path):
    before,old=lifecycle(4);after,new=lifecycle(5)
    old.handlers=deepcopy(new.handlers)
    assert ast.dump(before,include_attributes=False)==ast.dump(after,include_attributes=False)
    tree=ast.parse('def invoke(owner):\n    try:\n        body()\n    except BaseException:\n        raise\n')
    tree.body[0].body[0].handlers=deepcopy(new.handlers)
    tree.body[0].body[0].orelse=deepcopy(new.orelse)
    calls=[];space=dict(body=lambda:calls.append('body'))
    exec(compile(ast.fix_missing_locations(tree),__file__,'exec'),space)
    space['invoke'](SimpleNamespace(close=lambda:calls.append('close')))
    assert calls==['body','close']
    (tmp_path/'primary_handler_observation.json').write_text(json.dumps(dict(
        original_success_structure_preserved=True,calls=calls,new_N0_Jobs=0,native_calls=0)),encoding='utf-8')
