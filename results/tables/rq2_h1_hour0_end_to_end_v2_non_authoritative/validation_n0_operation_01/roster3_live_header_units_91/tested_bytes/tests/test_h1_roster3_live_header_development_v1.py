"""Real Bootstrap4/Roster3 header journals; no N0/source/Job execution."""
from dataclasses import fields
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from threading import Thread

import pytest

from experiments import h1_group_execution_roster_development_v3 as roster
from tests.test_h1_bootstrap_integration_development_v1 import example
from tests.test_h1_selector_configuration_development_v1 import configuration


def test_exact_live_bootstrap4_roster_header_create_guard_close_reopen(example,tmp_path):
    m=roster.bootstrap
    _,_,_,prior,_=example
    run=m.RunConfiguration(**{field.name:getattr(prior,field.name) for field in fields(m.RunConfiguration)})
    profile=m.symbolic.build(m.symbolic.StaticProfile(**run.declared_profile()))
    profile_path=tmp_path/'bootstrap4_profile.json';profile_path.write_bytes(profile.raw)
    profile_pin=sha256(profile.raw).hexdigest()
    selector=configuration(tuple(uid for kind,uid in run.stage_order if kind=='generation'),run.network_sha256)
    archive=m.phase_manifest.ArchiveCapacityDeclaration(576,2**20,576*2**20,0)
    declaration=m.BootstrapDeclaration(str(tmp_path/'study_non_authoritative'),str(profile_path),
        profile_pin,'training_ub',0,12,65536,run,selector_configuration=selector,phase_archive=archive)
    retained={}
    def retain(root,before,after):
        assert retained.get(str(root),before)==before
        retained[str(root)]=after
        return after
    with closing(m.BootstrapOwner(declaration,create=True,create_study=True,
            retain_global_head=retain,retain_bootstrap_head=retain)) as owner:
        assert type(owner) is m.BootstrapOwner
        assert not Path(owner.roots['controller']).exists()
        with closing(roster.GroupRoster(owner,create=True,retain_head=retain,max_record_bytes=65536)) as group:
            view=group.inspect()
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
            assert owner._bootstrap.rows()==owner._global.rows()==group._journal.rows()==[]
        assert group.closed and not group._operation.locked() and not owner._operation.locked()
        assert not Path(owner.roots['controller']).exists()
    assert owner.closed
    with closing(m.BootstrapOwner(declaration,create=False,create_study=False,
            retain_global_head=retain,retain_bootstrap_head=retain,**heads)) as reopened:
        with closing(roster.GroupRoster(reopened,create=False,expected_head=group_head,
                retain_head=retain,max_record_bytes=65536)) as re_group:
            assert re_group.root==group_root and re_group.inspect()==view
            assert re_group._journal.rows()==[]
    assert reopened.closed and re_group.closed
    (tmp_path/'roster3_live_header_observation.json').write_bytes(m.encode(dict(
        exact_live_bootstrap4=True,real_roster_header_create_and_reopen=True,
        guard_competition_rejected=True,foreign_thread_rejected=True,
        attached_N0=0,new_N0_Jobs=0,real_native_calls=0,
        completed_N0_attach_positive=False,full_optimized_workflow_accepted=False,formal_result=False)))
