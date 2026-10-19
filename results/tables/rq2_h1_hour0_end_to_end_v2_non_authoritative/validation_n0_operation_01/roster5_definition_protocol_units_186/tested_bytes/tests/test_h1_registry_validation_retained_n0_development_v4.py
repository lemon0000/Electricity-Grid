"""Cold Bootstrap6: one synthetic Job, numerical N0 registration and close."""
from dataclasses import asdict, fields
import os
import json
from pathlib import Path
import sys
import threading
from time import perf_counter

import pytest

from tests import test_h1_hour0_end_to_end_development_v2 as source_fixture
from tests.h1_guarded_common_slice_helpers_development_v1 import fresh_identity_bookends
from tests.test_h1_hour0_end_to_end_development_v2 import (
    example,setup,numerical,environment,synthetic_reports,supplied,no_solver,saved,retained)
from tests.test_h1_guarded_common_slice_development_v2 import diagnostic_stack_observer

ORIGINAL_SYMBOLIC_INSPECT=source_fixture.m.symbolic.inspect


@pytest.fixture
def prepared(numerical,environment,synthetic_reports,tmp_path,monkeypatch):
    monkeypatch.setattr(source_fixture,'identity_bookends',fresh_identity_bookends)
    yield from source_fixture.complete_group.__wrapped__(
        numerical,environment,synthetic_reports,tmp_path,monkeypatch)


def test_cold_bootstrap6_retained_n0_registration_and_close(
        prepared,tmp_path,monkeypatch,request,record_property):
    s,prior,_,final=prepared;assert not final
    record_property('registered_development',True)
    record_property('bootstrap_module','experiments.h1_bootstrap_integration_development_v6')
    (tmp_path/'n0_invocation.json').write_text(json.dumps(dict(
        public_call='BootstrapOwner.bootstrap',kwargs=dict(registered_development=True),
        bootstrap_module='experiments.h1_bootstrap_integration_development_v6',
        pytest_nodeid=request.node.nodeid,entry_argv=list(sys.argv),
        diagnostic=True,formal_result=False,resource_admission=False),indent=2),encoding='utf-8')
    names=('experiments.h1_historical_n0_verifier_development_v5',
        'experiments.h1_bootstrap_integration_development_v6',
        'experiments.h1_owned_bootstrap_controller_development_v6')
    assert all(name not in sys.modules for name in names)
    start=perf_counter();measurements=[]
    def trace(stage):
        value=dict(stage=stage,seconds=perf_counter()-start);measurements.append(value)
        with (tmp_path/'n0_timing.jsonl').open('a',encoding='utf-8') as stream:stream.write(json.dumps(value)+'\n')
        print(json.dumps(value),flush=True)
    # Source seams and unchanged identity callables precede the definition-time
    # verifier baseline. No candidate is installed under a predecessor name.
    monkeypatch.setattr(source_fixture.m.symbolic,'inspect',ORIGINAL_SYMBOLIC_INSPECT)
    resolver=[None]
    def open_manifest():
        if resolver[0] is None:raise ValueError('successor symbolic resolver not prepared')
        return resolver[0]
    monkeypatch.setattr(source_fixture.m.owned.binding,'open_manifest',open_manifest)
    from experiments import h1_bootstrap_integration_development_v6 as m
    trace('static_successor_imported')
    config=m.RunConfiguration(**{f.name:getattr(prior.run_configuration,f.name) for f in fields(m.RunConfiguration)})
    registry=m.RegistryBinding(**{f.name:getattr(prior.registry_binding,f.name) for f in fields(m.RegistryBinding)})
    values={f.name:getattr(prior,f.name) for f in fields(m.BootstrapDeclaration)}
    # The static profile binds the bootstrap implementation. The predecessor's
    # synthetic file therefore cannot be relabelled as a successor declaration.
    profile=config.declared_profile()
    snapshot=m.symbolic.build(m.symbolic.StaticProfile(**profile))
    profile_path=tmp_path/'successor_symbolic_profile.json';profile_path.write_bytes(snapshot.raw)
    profile_pin=m.sha256(snapshot.raw).hexdigest()
    assert m.symbolic.inspect(profile_path,expected_sha256=profile_pin).data()['declared_static_profile']==profile
    resolver[0]=m.symbolic.proof._resolver(snapshot._proof_raw)
    values.update(run_configuration=config,registry_binding=registry,
        symbolic_path=str(profile_path),symbolic_sha256=profile_pin)
    declaration=m.BootstrapDeclaration(**values)
    # This is an external diagnostic retention record, written before callback
    # acknowledgement. A later data-only check need not invent owner heads from
    # an unretained journal suffix. Incomplete staging files are never accepted.
    retention_directory=tmp_path/'external_retention_non_authoritative'
    retention_directory.mkdir()
    retention_previous=[None]
    def persist(name,raw):
        staged=retention_directory/(name+'.staging')
        final_path=retention_directory/name
        with staged.open('xb') as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
        staged.rename(final_path)
        assert final_path.read_bytes()==raw
    persist('declaration.json',m.encode(asdict(declaration)))
    retentions=[]
    def retain(root,before,after):
        assert m.phase_manifest.observation._CLEANUP_DIAGNOSTICS()['active_operations']==0
        retentions.append(str(root))
        trace('retention_'+str(len(retentions))+'_'+Path(root).name)
        result=s.retain(root,before,after)
        assert result==after
        raw=m.encode(dict(sequence=len(retentions),root=str(root),before=before,after=after,
            previous_retention_sha256=retention_previous[0],
            retained_heads=dict(s.heads),diagnostic_only=True,formal_result=False))
        persist(f'{len(retentions):04d}.json',raw)
        retention_previous[0]=m.sha256(raw).hexdigest()
        return result
    owner=m.BootstrapOwner(declaration,create=True,create_study=True,
        retain_global_head=retain,retain_bootstrap_head=retain)
    trace('owner_open')
    try:
        # A foreign thread cannot borrow the real owner's held guard and mint
        # a session, even if it obtains this fixture's private opener.
        opener=dict(zip(m._run_registry_operation.__code__.co_freevars,
            (cell.cell_contents for cell in m._run_registry_operation.__closure__)))['open_scope']
        owner._operation.acquire();owner._operation_nonce=object();errors=[]
        def foreign():
            try:opener(owner)
            except ValueError as error:errors.append(str(error))
        thread=threading.Thread(target=foreign);thread.start();thread.join(timeout=5)
        owner._operation_nonce=None;owner._operation.release()
        assert not thread.is_alive() and errors
        result=owner.bootstrap(registered_development=True)
        returned_receipt=result['N0_validation_execution_receipt']
        assert type(returned_receipt) is bytes
        persist('returned_execution_receipt.json',returned_receipt)
        persist('public_bootstrap_return.json',m.encode(dict(result,
            N0_validation_execution_receipt=json.loads(returned_receipt),
            returned_execution_receipt_sha256=m.sha256(returned_receipt).hexdigest(),
            diagnostic_return_format='JSON; exact receipt bytes saved separately')))
        trace('N0_registered')
        assert result['state']=='pending_post_N' and all(result[k] is False for k in m.FLAGS)
        receipt=json.loads(result['N0_validation_execution_receipt'])
        assert receipt['complete'] and receipt['confirmed_builds']==4
        assert receipt['full_numerical_hour_replays']==4
        assert receipt['fresh_byte_context_revalidations']==28 and receipt['context_observations']==64
        builds=receipt['builds'];assert [v['build'] for v in builds]==[1,2,3,4]
        assert [v['caller_site'] for v in builds]==['N0_build','N0_build','registry','registry']
        assert len({v['slot_id'] for v in builds})==len({v['controller_root'] for v in builds})==1
        executions=[v['execution'] for v in builds]
        assert [v['prepare'] for v in executions]==[1,2,3,4]
        assert [v['proof_role'] for v in executions]==['produced','consumed','consumed','consumed']
        assert [(v['full_numerical_hour_replays'],v['reused_numerical_inspections_total']) for v in executions]==[(4,4),(0,8),(0,8),(0,8)]
        assert all(len({v[key] for v in executions})==1 for key in ('proof_basis_identity','active_validation_identity','session_identity'))
        root=Path(owner.roots['controller'])
        job=json.loads((root/'job_000_non_authoritative/observation.json').read_bytes())
        assert job['exit_code']==0 and job['whole_job_quiescent']
        assert len(owner._bootstrap.rows())==5 and len(owner._global.rows())==3
        # Run the predecessor numerical oracle separately on these saved bytes;
        # it does not need to keep the live owner or rerun this synthetic Job.
        heads=retained(owner,s)
        (tmp_path/'n0_registry_execution_receipt.json').write_bytes(result['N0_validation_execution_receipt'])
        (tmp_path/'n0_retained_heads.json').write_bytes(m.encode(heads))
        (tmp_path/'n0_registration_report.json').write_bytes(m.encode(dict(
            state=result['state'],measurements=measurements,synthetic_jobs=1,real_native_calls=0,
            execution_receipt_sha256=m.sha256(result['N0_validation_execution_receipt']).hexdigest(),
            test_only_global_source_identity_cache=False,private_segment_implementation_memo=True,
            public_bootstrap_return_verified=True,predecessor_scientific_oracle_verified=False,
            externally_persisted_retention_callbacks=len(retentions),
            full_hour0_chain_passed=False,**m.FLAGS)))
    except BaseException as primary:
        try:owner.close()
        except BaseException as failure:BaseException.add_note(primary,'diagnostic owner close: '+repr(failure))
        raise
    else:owner.close()
    trace('owner_closed')
    receipt=owner.phase_validation_receipt()
    assert receipt['all_segments_closed'] and receipt['lifecycle_complete']
    assert receipt['pending_cleanup_windows']==0 and retentions
    assert receipt['implementation_observation']=='segment_entry_exit'
    reads=owner.registry_read_validation_receipt()
    assert reads['successful_reads']==1 and reads['failed_read_count']==0
    assert reads['pending_registry_records']==0 and not reads['cached_numerical_proofs_retained']
    empty,=reads['reads']
    assert empty['mode']=='constructor' and empty['numerical_roots']==0
    assert empty['registry_execution']['closed'] and not empty['registry_execution']['complete']
    assert m.historical_verifier.registry_validation_scope(owner) is None
    assert owner._operation_nonce is None and not owner._original_operation.locked()
    (tmp_path/'n0_registry_read_observations_closed.json').write_bytes(m.encode(reads))
    cleanup=m.phase_manifest.observation._CLEANUP_DIAGNOSTICS()
    assert cleanup['active_operations']==cleanup['abandoned_pending_operations']==0
    (tmp_path/'n0_phase_segments_closed.json').write_bytes(m.encode(dict(
        receipt=receipt,retentions=retentions,cleanup=cleanup,
        registered_development_opt_in=True,bootstrap_callable_replaced=False,
        current_source_header_reopen_verified=False,N0_reopen_verified=False,
        synthetic_source_and_Job_seams=True,formal_result=False,resource_admission=False)))
