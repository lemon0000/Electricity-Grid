"""Cold static successor: one real synthetic Job through N0 registration only."""
from dataclasses import fields
import json
from pathlib import Path
import sys
from time import perf_counter

import pytest

from tests import test_h1_hour0_end_to_end_development_v2 as source_fixture
from tests.h1_guarded_common_slice_helpers_development_v1 import fresh_identity_bookends
from tests.test_h1_hour0_end_to_end_development_v2 import (
    example,setup,numerical,environment,synthetic_reports,supplied,no_solver,saved,retained)
from tests.test_h1_guarded_common_slice_development_v2 import diagnostic_stack_observer


@pytest.fixture
def prepared(numerical,environment,synthetic_reports,tmp_path,monkeypatch):
    monkeypatch.setattr(source_fixture,'identity_bookends',fresh_identity_bookends)
    yield from source_fixture.complete_group.__wrapped__(
        numerical,environment,synthetic_reports,tmp_path,monkeypatch)


def test_cold_owned_n0_registration_with_registry_validation(prepared,tmp_path,monkeypatch):
    s,prior,_,final=prepared;assert not final
    names=('experiments.h1_historical_n0_verifier_development_v3',
        'experiments.h1_bootstrap_integration_development_v4',
        'experiments.h1_owned_bootstrap_controller_development_v4')
    assert all(name not in sys.modules for name in names)
    start=perf_counter();measurements=[]
    def trace(stage):
        value=dict(stage=stage,seconds=perf_counter()-start);measurements.append(value)
        with (tmp_path/'n0_timing.jsonl').open('a',encoding='utf-8') as stream:stream.write(json.dumps(value)+'\n')
        print(json.dumps(value),flush=True)
    # Source seams and unchanged identity callables precede the definition-time
    # verifier baseline. No candidate is installed under a predecessor name.
    from experiments import h1_bootstrap_integration_development_v4 as m
    trace('static_successor_imported')
    config=m.RunConfiguration(**{f.name:getattr(prior.run_configuration,f.name) for f in fields(m.RunConfiguration)})
    registry=m.RegistryBinding(**{f.name:getattr(prior.registry_binding,f.name) for f in fields(m.RegistryBinding)})
    values={f.name:getattr(prior,f.name) for f in fields(m.BootstrapDeclaration)}
    values.update(run_configuration=config,registry_binding=registry)
    declaration=m.BootstrapDeclaration(**values)
    monkeypatch.setattr(m.BootstrapOwner,'_continue_bootstrap',m.BootstrapOwner._continue_registered_development)
    owner=m.BootstrapOwner(declaration,create=True,create_study=True,
        retain_global_head=s.retain,retain_bootstrap_head=s.retain)
    trace('owner_open')
    try:
        result=owner.bootstrap();trace('N0_registered')
        assert result['state']=='pending_post_N' and all(result[k] is False for k in m.FLAGS)
        receipt=json.loads(result['N0_validation_execution_receipt'])
        assert receipt['complete'] and receipt['confirmed_builds']==4
        assert receipt['full_numerical_hour_replays']==4
        assert receipt['fresh_byte_context_revalidations']==28 and receipt['context_observations']==64
        root=Path(owner.roots['controller'])
        job=json.loads((root/'job_000_non_authoritative/observation.json').read_bytes())
        assert job['exit_code']==0 and job['whole_job_quiescent']
        assert len(owner._bootstrap.rows())==5 and len(owner._global.rows())==3
        heads=retained(owner,s)
        (tmp_path/'n0_registry_execution_receipt.json').write_bytes(result['N0_validation_execution_receipt'])
        (tmp_path/'n0_retained_heads.json').write_bytes(m.encode(heads))
        (tmp_path/'n0_registration_report.json').write_bytes(m.encode(dict(
            state=result['state'],measurements=measurements,synthetic_jobs=1,real_native_calls=0,
            execution_receipt_sha256=m.sha256(result['N0_validation_execution_receipt']).hexdigest(),
            source_identity_cache=False,full_hour0_chain_passed=False,**m.FLAGS)))
    finally:owner.close()
    trace('owner_closed')
