"""Execute the real v4 finally AST with explicit fake completed-body resources.

This isolates failure-after-success cleanup; it is not a cold Handoff test.
"""
import ast
from pathlib import Path
from types import SimpleNamespace
import weakref

import pytest


def test_real_handoff_supports_weak_receipt_storage_without_opening_resources():
    from experiments import h1_selector_phase_handoff_development_v4 as handoff
    from experiments import h1_selector_parent_validation_operation_development_v2 as parent_validation
    owner=object.__new__(handoff.Handoff)
    assert handoff.parent_validation is parent_validation
    assert weakref.ref(owner)() is owner


def cleanup_driver():
    path = Path(__file__).resolve().parents[1] / 'experiments/h1_selector_phase_handoff_development_v4.py'
    tree = ast.parse(path.read_bytes(), filename=str(path))
    owner, = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Handoff']
    consume, = [node for node in owner.body if isinstance(node, ast.FunctionDef) and node.name == 'consume']
    original, = [node for node in consume.body if isinstance(node, ast.Try) and node.finalbody]
    module = ast.parse('''def run(c, body_error=None):
    self=c.owner
    common_held=parents_held=attempted=True
    common_guards=c.common_guards
    parent_guards=c.parent_guards
    parent_marks=c.marks
    bundle=c.bundle
    guard=c.outer
    token=c.token
    end=c.end
    validation_abort=c.abort
    parent_optimized=True
    parent_finish=c.parent_finish
    parent_abort=c.parent_abort
    cleanup=c.cleanup
    try:
        if body_error is not None:
            raise body_error
        return 'completed body'
    finally:
        pass
''')
    module.body[0].body[-1].finalbody = original.finalbody
    ast.fix_missing_locations(module)
    namespace = {}
    exec(compile(module, str(path), 'exec'), namespace)
    return namespace['run']


@pytest.mark.parametrize('fault', ['common0', 'parent0', 'end', 'outer', 'mark', 'parent_scope'])
@pytest.mark.parametrize('body_failed', [False, True])
@pytest.mark.parametrize('abort_failed', [False, True])
def test_every_outer_cleanup_edge_attempts_all_resources_and_invalidates_receipt(fault, body_failed, abort_failed):
    events = []
    class Guard:
        def __init__(self, name):
            self.name, self.held = name, True
        def release(self):
            self.held = False
            events.append(self.name)
            if self.name == fault:
                raise RuntimeError('cleanup ' + self.name)
    class Mark:
        def __setattr__(self, name, value):
            object.__setattr__(self, name, value)
            if name == '_reference_held' and value is False:
                events.append('mark')
                if fault == 'mark':
                    raise RuntimeError('cleanup mark')
    guards = [Guard(name) for name in ('common0', 'common1', 'parent0', 'parent1', 'outer')]
    mark = Mark()
    mark._reference_held = True
    c = SimpleNamespace(owner=SimpleNamespace(_state='complete'), token=object(),
        common_guards=guards[:2], parent_guards=guards[2:4], outer=guards[4], marks=(mark,),
        bundle=SimpleNamespace(held=guards[2:4], marked=[mark]), receipt={'complete': False},
        handles_closed=False)
    def end(owner, token):
        assert owner is c.owner and token is c.token
        events.append('end')
        if fault == 'end':
            raise RuntimeError('cleanup end')
    def abort(owner, error):
        assert owner is c.owner
        c.receipt['complete'] = False
        events.append('abort')
        if abort_failed:
            raise RuntimeError('validation abort failure')
    def close(owner):
        c.handles_closed = True
        events.append('handles')
    def parent_finish(owner):
        events.append('parent_finish')
        assert all(guard.held for guard in guards)
        if fault=='parent_scope':raise RuntimeError('Parent scope finish failed')
    def parent_abort(owner,error):
        events.append('parent_abort')
        if fault=='parent_scope':raise RuntimeError('Parent scope abort failed')
    c.end, c.abort, c.cleanup = end, abort, close
    c.parent_finish,c.parent_abort=parent_finish,parent_abort
    body = ValueError('original body') if body_failed else None
    with pytest.raises(ValueError if body_failed else RuntimeError) as caught:
        cleanup_driver()(c, body)
    if body_failed:
        assert caught.value is body and body.__notes__
    assert set(events) == {'common0', 'common1', 'parent0', 'parent1', 'outer', 'mark', 'end', 'abort', 'handles',
        'parent_abort', *([] if body_failed else ['parent_finish'])}
    assert events[0]==('parent_abort' if body_failed else 'parent_finish')
    assert all(not guard.held for guard in guards)
    assert not mark._reference_held and not c.bundle.held and not c.bundle.marked
    assert c.handles_closed and not c.receipt['complete'] and c.owner._state == 'failed'
