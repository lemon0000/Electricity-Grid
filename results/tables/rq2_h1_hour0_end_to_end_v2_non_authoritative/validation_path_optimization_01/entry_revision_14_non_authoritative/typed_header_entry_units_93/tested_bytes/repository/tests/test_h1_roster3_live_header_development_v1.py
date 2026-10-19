"""Real Bootstrap4/Roster3 header journals; no N0/source/Job execution."""
from dataclasses import fields
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from threading import Thread
from time import perf_counter

import pytest

from experiments import h1_group_execution_roster_development_v3 as roster
from tests.test_h1_bootstrap_integration_development_v1 import example
from tests.test_h1_selector_configuration_development_v1 import configuration


def test_exact_live_bootstrap4_roster_header_create_guard_close_reopen(example,tmp_path):
    m=roster.bootstrap
    start=perf_counter();stages=[]
    def trace(stage):
        stages.append(dict(stage=stage,elapsed_seconds=perf_counter()-start))
        print(json.dumps(stages[-1]),flush=True)
    _,_,_,prior,_=example
    run=m.RunConfiguration(**{field.name:getattr(prior,field.name) for field in fields(m.RunConfiguration)})
    profile=m.symbolic.build(m.symbolic.StaticProfile(**run.declared_profile()))
    profile_path=tmp_path/'bootstrap4_profile.json';profile_path.write_bytes(profile.raw)
    profile_pin=sha256(profile.raw).hexdigest()
    selector=configuration(tuple(uid for kind,uid in run.stage_order if kind=='generation'),run.network_sha256)
    archive=m.phase_manifest.ArchiveCapacityDeclaration(576,2**20,576*2**20,0)
    declaration=m.BootstrapDeclaration(str(tmp_path/'study_non_authoritative'),str(profile_path),
        profile_pin,'training_ub',0,12,65536,run,selector_configuration=selector,phase_archive=archive)
    trace('declaration_prepared')
    retained={}
    def retain(root,before,after):
        assert retained.get(str(root),before)==before
        retained[str(root)]=after
        return after
    with closing(m.BootstrapOwner(declaration,create=True,create_study=True,
            retain_global_head=retain,retain_bootstrap_head=retain)) as owner:
        trace('Bootstrap4_owner_created')
        assert type(owner) is m.BootstrapOwner
        assert not Path(owner.roots['controller']).exists()
        with closing(roster.GroupRoster(owner,create=True,retain_head=retain,max_record_bytes=65536)) as group:
            trace('Roster3_header_created')
            view=group.inspect()
            trace('Roster3_inspected')
            assert view['schema']==roster.SCHEMA
            assert len(view['entries'])==4 and not view['independent_N0_mapping_complete']
            assert all(row['attachment'] is None and not row['independent_N0_available'] for row in view['entries'])
            assert all(view[name] is False for name in roster.FLAGS)
            assert view['retained_historical_verifier']==dict(schema=m.historical_verifier.VERIFIER_SCHEMA,
                identity=m.historical_verifier.verifier_identity())
            owner._operation.acquire()
            try:
                with pytest.raises(ValueError,match='bootstrap operation active'):group.inspect()
            finally:owner._operation.release()
            errors=[]
            def foreign():
                try:group.inspect()
                except ValueError as error:errors.append(str(error))
            thread=Thread(target=foreign);thread.start();thread.join(timeout=5)
            assert not thread.is_alive() and len(errors)==1
            assert not group._operation.locked() and not owner._operation.locked()
            heads=dict(global_head=owner._global.head,bootstrap_head=owner._bootstrap.head)
            group_head=group._journal.head;group_root=group.root
            assert all(not list(path.glob('[0-9]*.json'))
                for path in (owner._bootstrap.root,owner._global.root,group.root))
            trace('guard_competition_checks_completed')
        assert group.closed and not group._operation.locked() and not owner._operation.locked()
        assert not Path(owner.roots['controller']).exists()
    assert owner.closed
    trace('original_headers_closed')
    with closing(m.BootstrapOwner(declaration,create=False,create_study=False,
            retain_global_head=retain,retain_bootstrap_head=retain,**heads)) as reopened:
        trace('Bootstrap4_owner_reopened')
        with closing(roster.GroupRoster(reopened,create=False,expected_head=group_head,
                retain_head=retain,max_record_bytes=65536)) as re_group:
            assert re_group.root==group_root and re_group.inspect()==view
            assert not list(re_group.root.glob('[0-9]*.json'))
            trace('Roster3_header_reopened_and_inspected')
    assert reopened.closed and re_group.closed
    trace('reopened_headers_closed')
    (tmp_path/'roster3_live_header_observation.json').write_bytes(m.encode(dict(
        exact_live_bootstrap4=True,real_roster_header_create_and_reopen=True,
        guard_competition_rejected=True,foreign_thread_rejected=True,
        stages=stages,
        attached_N0=0,new_N0_Jobs=0,real_native_calls=0,
        completed_N0_attach_positive=False,full_optimized_workflow_accepted=False,formal_result=False)))
