"""Create-once real RTS static/bootstrap probe; all N/Job/solver entry denied.

This script does not execute a calibration or admit a formal experiment.
The old v3 config contributes only already-declared static network/stage inputs.
"""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from contextlib import ExitStack
from dataclasses import asdict
from hashlib import sha256
import json
import time
from unittest.mock import patch
from experiments import h1_bootstrap_integration_development_v1 as m


def main():
    directory=Path(__file__).with_suffix('')
    directory.mkdir(exist_ok=False)
    retention=directory/'head_retention';retention.mkdir()
    files=[Path(m.__file__),ROOT/'tests/test_h1_bootstrap_integration_development_v1.py',
        ROOT/'docs/model_spec/rq2_h1_bootstrap_integration_development_v1.md',Path(__file__)]
    pins={str(p):sha256(p.read_bytes()).hexdigest() for p in files}
    heads={};retained=[];denials=[];owner=None;start=time.perf_counter()
    record=dict(status='PROBE_UNRESOLVED',jobs=0,real_native_calls=0,
        current_N_loaded=False,native_authority_consumed=False,implementation_complete=False,**m.FLAGS)
    def deny(*a,**kw):
        denials.append('forbidden execution/current source entry')
        raise AssertionError(denials[-1])
    def retain(root,before,after):
        previous=heads.get(str(root),sha256((root/'header.json').read_bytes()).hexdigest())
        if previous!=before:raise ValueError('external head changed')
        value=dict(root=str(root),before=before,after=after)
        raw=m.encode(value);path=retention/f'{len(retained)+1:04d}.json'
        m.storage._new(path,raw)
        if m.storage._read(path,65536)[0]!=raw:raise ValueError('retention readback differs')
        heads[str(root)]=after;retained.append(value)
        return after
    try:
        old_path=ROOT/'configs/rq2_normal_h1_calibration_v3.json';old_raw=old_path.read_bytes()
        if sha256(old_raw).hexdigest()!='c31c3638695009c65c3e01e2990cbda9a71e5ff66f57c7f636ec88a7fb99fd6f':
            raise ValueError('retained static declaration changed')
        old=json.loads(old_raw)
        config=m.RunConfiguration(old['upstream_root'],old['config_path'],m.phase.binding.SOURCE_CONFIG_PIN,
            old['network_identity'],old['dc_bus'],m.Rq2SolverSpec(**old['work']['specification']),
            m.phase.base.old.replay.H1HourReplayLimits(232,891,1272),
            m.phase.base.old.process.TaskProcessBudget(300.,.05,2*1024**3,2*1024**3,2.),
            tuple(tuple(v) for v in old['work']['stage_order']))
        manifest=m.symbolic.build(m.symbolic.StaticProfile(**config.declared_profile()))
        manifest_path=directory/'symbolic_manifest.json';m.storage._new(manifest_path,manifest.raw)
        declaration=m.BootstrapDeclaration(str(directory/'study_non_authoritative'),str(manifest_path),
            manifest.identity,'training_ub',0,3,65536,config)
        m.storage._new(directory/'declaration.json',m.encode(asdict(declaration)))
        with ExitStack() as stack:
            for obj,name in ((m.phase.binding.source_binding,'load_pinned_current'),
                    (m.phase.Controller,'_step_development'),(m._BootstrapController,'_step_development'),
                    (m.phase.Controller,'_job'),(m.phase.base.Controller,'step'),(m.phase.bridge.Controller,'step')):
                stack.enter_context(patch.object(obj,name,deny))
            stack.enter_context(m.phase.base.old.replay.guard.solver_calls_forbidden())
            owner=m.BootstrapOwner(declaration,create_study=True,create=True,
                retain_global_head=retain,retain_bootstrap_head=retain)
            try:owner.bootstrap()
            except ValueError as error:
                if str(error)!='bootstrap release/capability entry not implemented; controller retained':raise
                record['deliberate_stop']=str(error)
            else:raise AssertionError('probe unexpectedly returned from bootstrap')
            root_global,root_bootstrap=owner._global.root,owner._bootstrap.root
            record['actual_stage_count']=len(owner._network.data.generators)+1+sum(
                g.dispatch_mode=='committable' for g in owner._network.data.generators)
            record['hourly_points_in_static_network']=len(owner._network.data.hourly_points)
            owner.close();owner=None
            owner=m.BootstrapOwner(declaration,create_study=False,create=False,
                global_head=heads[str(root_global)],bootstrap_head=heads[str(root_bootstrap)],
                retain_global_head=retain,retain_bootstrap_head=retain)
            observed=owner.inspect()
            if observed['state']!='controller_ready_unreleased' or denials:
                raise AssertionError('probe state/denials differ')
            record.update(status='REAL_STATIC_AND_EMPTY_CONTROLLER_VERIFIED_ONLY',inspection=observed,
                retained_heads=heads,symbolic_sha256=manifest.identity,
                declaration_sha256=sha256((directory/'declaration.json').read_bytes()).hexdigest())
    except BaseException as error:
        record.update(error_type=type(error).__name__,error=str(error))
    finally:
        if owner is not None:owner.close()
        record.update(wall_seconds=round(time.perf_counter()-start,3),denied_entry_attempts=denials,
            files_sha256=pins,files_unchanged=all(sha256(Path(p).read_bytes()).hexdigest()==pin for p,pin in pins.items()))
        m.storage._new(directory/'probe_observation.json',m.encode(record))
    print(json.dumps(record,indent=2))
    return 0 if record['status']=='REAL_STATIC_AND_EMPTY_CONTROLLER_VERIFIED_ONLY' else 1


if __name__=='__main__':raise SystemExit(main())
