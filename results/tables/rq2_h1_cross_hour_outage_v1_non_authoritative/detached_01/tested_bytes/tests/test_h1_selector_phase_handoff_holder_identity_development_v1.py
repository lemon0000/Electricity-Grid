"""Holder identity across the closed-owner gap; explicit synthetic Parent."""
import shutil

import pytest

from tests import test_h1_selector_phase_handoff_faults_development_v1 as cases
from tests.test_h1_selector_phase_handoff_faults_development_v1 import (
    make,rows,context,case,setup,legacy_setup,no_solver)

pytestmark=pytest.mark.parametrize('context',['business_unresolved'],indirect=True)


@pytest.fixture
def drift_case(context,monkeypatch,tmp_path):
    faults={};original_load=cases.load
    def load(*args,**kwargs):
        cls=cases.canonical.common.CommonOwnerGenesis;original_close=cls._close_handles
        def close(owner):
            result=original_close(owner)
            if owner is context.owner and faults:
                root=owner.holder_root
                root.resolve().relative_to(tmp_path.resolve())
                if faults['target']=='directory':
                    preserved=tmp_path/'preserved_holder';root.rename(preserved);shutil.copytree(preserved,root)
                else:
                    path=root/('header.json' if faults['target']=='header' else 'execution.lock')
                    replacement=tmp_path/'holder_same_bytes.tmp'
                    replacement.write_bytes(path.read_bytes());replacement.replace(path)
            return result
        monkeypatch.setattr(cls,'_close_handles',close)
        return original_load(*args,**kwargs)
    monkeypatch.setattr(cases,'load',load)
    generator=cases.fault_case.__wrapped__(context,monkeypatch,tmp_path)
    f=next(generator)
    try:yield f,faults
    finally:generator.close()


@pytest.mark.parametrize('target',['header','lock','directory'])
def test_holder_same_bytes_replacement_cannot_be_adopted(drift_case,target):
    f,faults=drift_case;faults['target']=target
    with make(f) as owner:
        with pytest.raises(ValueError):owner.consume()
        assert f.c.owner.closed and len(f.retained)==1
        assert rows(f.c.owner.owner_root/'owner.sqlite')==[]
        assert owner._phase is None
        if owner._holder is not None:assert owner._holder._lease_object.stream is None
        assert owner._lease.stream is None and owner._journal._original_lease.stream is None
        assert not f.ref._guard.locked() and not f.c.case.guard.locked()
