"""Actual Parent-alias archive/source checks after takeover; no native or Job."""
import json
from contextlib import ExitStack

import pytest

from experiments import h1_selector_phase_handoff_development_v1 as canonical
from tests.test_h1_selector_parent_controller_development_v1 import (
    harness,context,case,setup,legacy_setup,sequence_factory,no_solver,load)
from tests.test_h1_selector_phase_handoff_development_v1 import options
from tests.test_h1_selector_phase_handoff_faults_development_v1 import rows

pytestmark=pytest.mark.parametrize('context,role',[
    ('business_unresolved','reference'),('paired','actual')],indirect=['context'])


@pytest.mark.parametrize('target',['science','timing','source'])
def test_post_takeover_parent_or_source_drift_prevents_phase_commit(harness,monkeypatch,target,role):
    h=harness;p=h.module;c=h.context
    m=load(canonical.__file__,'selector_phase_handoff_parent_drift_test_alias',monkeypatch,
        dict(h1_selector_parent_controller_development_v1=p))
    with ExitStack() as stack:
        reference=stack.enter_context(p.Parent(h.root,h.raw,**h.options))
        receipt=reference.run();retained=[];preserved=[]
        pairs={'joint':None};archive_owner=reference
        if role=='actual':
            raw=p.worker.snapshot.capture_actual(c.owner,c.config,max_archive_bytes=c.cap,lane_id='joint',
                reference_root=receipt.scientific_root,reference_terminal_sha256=receipt.scientific_terminal_sha256,
                reference_request_sha256=receipt.scientific_request_sha256,reference_max_archive_bytes=receipt.max_archive_bytes)
            archive_owner=stack.enter_context(p.Parent(h.root.parent/'actual_parent_non_authoritative',raw,
                **h.options,reference_owner=reference,reference_completion=receipt))
            pairs['joint']=(archive_owner,archive_owner.run())
        def retain(root,before,after):
            retained.append(after)
            if len(retained)==2:
                assert c.owner.closed
                if target=='source':
                    current=c.s.currents[0]
                    object.__setattr__(current,'source_projection_audit_payload',current.source_projection_audit_payload+b' ')
                else:
                    path=archive_owner.worker_root/f'{target}_sequence_non_authoritative'/'binding.json'
                    raw=path.read_bytes();replacement=h.root.parent/'replaced_archive_binding.json'
                    replacement.write_bytes(raw);replacement.replace(path);preserved.append((path,raw))
            return after
        with m.Handoff(c.owner,(reference,receipt),pairs,**options(retain)) as owner:
            with pytest.raises(ValueError):owner.consume()
            assert owner._state=='failed' and len(retained)==2 and c.owner.closed
            assert rows(c.owner.owner_root/'owner.sqlite')==[]
            assert list(c.owner.holder_root.glob('[0-9]*.json'))==[]
            assert all(path.read_bytes()==raw for path,raw in preserved)
            assert not reference._guard.locked() and not c.case.guard.locked()
            assert not archive_owner._guard.locked()
            if role=='actual':assert not archive_owner._reference_held
            journal=[json.loads(path.read_bytes())['body']['kind'] for path in
                     sorted((owner.root/'journal_non_authoritative').glob('[0-9]*.json'))]
            assert journal==['takeover_intent','handoff_opened']
            assert owner._phase._lease_object.stream is None and owner._holder._lease_object.stream is None
