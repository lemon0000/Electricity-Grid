from dataclasses import asdict
import importlib.util
import json
import os
from pathlib import Path
import sys

import pytest

from experiments import h1_timed_released_worker_development_v1 as api
from tests.test_h1_parent_snapshot_development_v1 import owner,pending,snapshot
from tests.test_h1_saved_source_parent_development_v1 import environment
from tests.test_rq2_normal_h1_source_binding_v1 import supplied
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver
from tests.test_h1_attested_saved_hour_development_v1 import synthetic_reports,saved

pytestmark = pytest.mark.skipif(os.name != 'nt',reason='actual short Windows Job')


def child_main(base,raw_root,mode,path,pin):
    """Test-only launcher: real Job/process/clock, no real native solver."""
    from tests.test_h1_saved_job_development_v1 import install_child_source
    from tests.test_h1_timed_worker_hour_development_v1 import install
    mp = install_child_source(Path(base))
    no_solver.__wrapped__(mp)
    root = Path(path).parent
    reports = [(Path(raw_root)/f'{i:03d}.bin').read_bytes() for i in range(3)]
    solvers = install(mp,root/'worker_non_authoritative',reports)
    if mode == 'identity': mp.setattr(api.old,'_current_process',lambda:(os.getpid(),1))
    if mode == 'consumed': (root/'consumed.json').write_bytes(b'partial')
    if mode in ('release_drift','science_drift','result_write'):
        original = api.worker.inspect
        def inspect(*args,**kwargs):
            checked = original(*args,**kwargs)
            # Only the released consumer's inspect, after owned completion.
            if (root/'worker_non_authoritative'/'terminal.json').exists():
                import inspect as inspect_module
                if inspect_module.currentframe().f_back.f_code is api.execute.__code__:
                    if mode == 'release_drift':
                        (root/'release_intent.json').write_bytes(b'{}')
                    elif mode == 'science_drift':
                        target = root/'worker_non_authoritative/hour_non_authoritative/commits/000.json'
                        data = target.read_bytes(); stamp = target.stat()
                        target.write_bytes(data.replace(b'0',b'1',1))
                        os.utime(target,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
                    else:
                        original_write = api.write
                        def write(path,doc):
                            if path.name == 'worker_result.json': raise OSError('injected result write failure')
                            return original_write(path,doc)
                        mp.setattr(api,'write',write)
            return checked
        mp.setattr(api.worker,'inspect',inspect)
    result = api.execute(path,pin)
    assert [s.apply_calls for s in solvers] == [1,1,1]
    assert [s.close_calls for s in solvers] == [1,1,1]
    assert api.read(root/'worker_result.json',result)[0]['schema'] == api.SCHEMA
    # A successful worker cannot consume the same request twice.
    try: api.execute(path,pin)
    except FileExistsError: pass
    else: raise AssertionError('request reused')


def run_job(base,parent,item,args,reports,mode):
    old,io = api.old,api.io
    lease = old.bounded.chunks.base.local._Lease(base/'job_non_authoritative',True)
    try:
        root = lease.root; scratch = root/'scratch_non_authoritative'; scratch.mkdir()
        raw_root = base/'raw';raw_root.mkdir()
        for i,raw in enumerate(reports): (raw_root/f'{i:03d}.bin').write_bytes(raw)
        budget = old.process.TaskProcessBudget(180.,.05,512*old.MIB,768*old.MIB,2.)
        request = dict(schema=api.SCHEMA,root=str(root),implementation=api.implementation_identity(),
            parent_declaration=parent._declaration,parent_identity=parent.identity,
            anchor_record=parent._anchor.inspect().record_sha256,pending_arguments=args,
            input_receipt=json.loads(item.receipt),input_receipt_sha256=item.receipt_sha256,
            budget=asdict(budget),route='owned_timed_hour_development',**api.FLAGS)
        request_pin = api.write(root/'request.json',request)
        dependency = str(Path(importlib.util.find_spec('pygments').origin).parent.parent)
        code = (f'import sys;sys.path.insert(0,{str(Path.cwd())!r});sys.path.append({dependency!r});'
            'from tests.test_h1_timed_released_worker_development_v1 import child_main;'
            f'child_main({str(base)!r},{str(raw_root)!r},{mode!r},*sys.argv[1:])')
        wrapped = 'try:\n    '+code+'\nexcept BaseException:\n    import traceback\n    from pathlib import Path\n    (Path.cwd()/"error.txt").write_bytes(traceback.format_exc().encode()[:4096])\n    raise\n'
        argv = [sys.executable,'-I','-B','-c',wrapped,str(root/'request.json'),request_pin]
        env = old.runtime.development_environment();env.update(TEMP=str(scratch),TMP=str(scratch))
        env = dict(sorted(env.items()));old.runtime._environment(env)
        resources = old.process.resources
        host = resources.HostResourceBudget(1024*old.MIB,32*old.MIB,(
            resources.DirectoryDemand('synthetic_job',str(root),256*old.MIB,32*old.MIB),))
        arguments = dict(cwd=scratch,environment=env,budget=budget,host_budget=host,
            expected_host_identity=resources.resource_identity(host))
        identity = old.process.task_process_identity(argv,**arguments)
        launch_pin = api.write(root/'launch.json',dict(request_sha256=request_pin,process_identity=identity,
            argv=argv,cwd=str(scratch),environment_sha256=io.digest(io.encode(env)),budget=asdict(budget),host=asdict(host)))
        with old.process.normal_task_child(argv,**arguments,expected_process_identity=identity) as child:
            pid,creation = child.pid,child.creation_filetime
            initial = json.loads(io.encode(asdict(child.initial_observation)))
            old._validate_initial(initial,host)
            initial_pin = api.write(root/'initial_observation.json',initial)
            child_pin = api.write(root/'child.json',dict(pid=pid,creation_filetime=creation,
                process_identity=identity,request_sha256=request_pin,initial_observation_sha256=initial_pin))
            api.write(root/'release_intent.json',dict(request_sha256=request_pin,
                launch_sha256=launch_pin,child_sha256=child_pin))
            child.release(); observed = child.wait()
        api.write(root/'observation.json',asdict(observed))
        assert observed.whole_job_quiescent
        return root,observed,identity,pid,creation,budget
    finally: lease.close()


@pytest.mark.parametrize('mode',['success','identity','consumed','release_drift','science_drift','result_write'])
def test_released_worker_in_real_job(tmp_path,environment,synthetic_reports,mode):
    p = owner(tmp_path/'parent_non_authoritative',environment,hours=1,create=True)
    try:
        packet,args = pending(p,environment)
        reader = snapshot(p)
        try: item = reader.pending_input(**args)
        finally: reader.close()
        root,observed,identity,pid,creation,budget = run_job(tmp_path,p,item,args,synthetic_reports,mode)
        assert p._journal.inspect().events == 1
        assert p._restore()[0].status == 'pending_unknown'
        result_path = root/'worker_result.json'
        error = root/'scratch_non_authoritative/error.txt'
        if mode == 'success':
            assert observed.exit_code == 0,error.read_text() if error.exists() else observed
            api.old._validate_observation(observed,identity,pid,creation,budget)
            result = json.loads(result_path.read_bytes())
            assert result['pid'] == pid != os.getpid() and result['creation_filetime'] == creation
            assert not any(result[k] for k in api.FLAGS)
            checked = api.worker.inspect(root/'worker_non_authoritative',packet,item.specification,item.limits,
                expected_binding_sha=result['worker_binding_sha256'],expected_terminal_sha=result['worker_terminal_sha256'],
                expected_implementation=result['worker_implementation'])
            assert api.io.digest(checked['projection_payload']) == result['projection_sha256']
        else:
            assert observed.exit_code != 0 and not result_path.exists()
            expected = {'identity':'released exact timed worker identity','consumed':'FileExistsError',
                'release_drift':'released worker evidence changed','science_drift':'worker output changed',
                'result_write':'injected result write failure'}[mode]
            assert expected in error.read_text(),error.read_text()
            if mode == 'identity': assert not (root/'consumed.json').exists()
            if mode in ('release_drift','science_drift','result_write'):
                assert (root/'consumed.json').exists()
                assert (root/'worker_non_authoritative/terminal.json').exists()
    finally: p.close()


def test_fixed_view_detects_same_length_restored_mtime(tmp_path):
    path = tmp_path/'record.json';pin = api.write(path,{'x':1})
    _,view = api.read(path,pin)
    stamp = path.stat();path.write_bytes(b'{"x":2}\n')
    os.utime(path,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
    with pytest.raises(ValueError,match='evidence changed'): api.unchanged({path:(api.CAP,view)})


def test_noncanonical_and_overcap_rejected(tmp_path):
    path = tmp_path/'record.json';path.write_bytes(b'{ "x":1 }')
    with pytest.raises(ValueError,match='canonical'): api.read(path,api.io.digest(path.read_bytes()))
    with pytest.raises(ValueError,match='cap'): api.write(tmp_path/'large.json',{'x':'x'*api.CAP})
    assert not (tmp_path/'large.json').exists()
