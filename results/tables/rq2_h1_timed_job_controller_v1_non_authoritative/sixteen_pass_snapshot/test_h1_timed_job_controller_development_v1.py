import ast
from dataclasses import replace
import importlib.util
import json
import os
from pathlib import Path
import sys

import pytest

from experiments import h1_timed_job_controller_development_v1 as api
from tests.test_h1_saved_source_parent_development_v1 import environment,source_pin
from tests.test_rq2_normal_h1_source_binding_v1 import supplied
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver,spec
from tests.test_h1_attested_saved_hour_development_v1 import synthetic_reports,saved
from tests.test_h1_attested_source_parent_development_v1 import synthetic_next_hour

pytestmark = pytest.mark.skipif(os.name != 'nt',reason='actual Windows Job/source carry integration')


def controller(root,env,hours=2):
    upstream,config,origin,state = env
    return api.Controller(root,api.parent.source.static_network(state['data']),replace(spec(),time_limit_seconds=5.),
        api.old.replay.H1HourReplayLimits(3,100,500),origin=origin,upstream_root=upstream,config_path=config,dc_bus=1,
        hours=hours,budget=api.old.process.TaskProcessBudget(300.,.05,512*api.old.MIB,768*api.old.MIB,2.))


def install_launcher(mp,base,reports,mode='normal',label='origin'):
    raw_root = base/label;raw_root.mkdir()
    for i,raw in enumerate(reports): (raw_root/f'{i:03d}.bin').write_bytes(raw)
    dependency = str(Path(importlib.util.find_spec('pygments').origin).parent.parent)
    code = (f'import sys;sys.path.insert(0,{str(Path.cwd())!r});sys.path.append({dependency!r});'
        'from tests.test_h1_timed_job_controller_development_v1 import child_main;'
        f'child_main({str(base)!r},{str(raw_root)!r},{mode!r},*sys.argv[1:])')
    wrapped = 'try:\n    '+code+'\nexcept BaseException:\n    import traceback\n    from pathlib import Path\n    (Path.cwd()/"error.txt").write_bytes(traceback.format_exc().encode()[:4096])\n    raise\n'
    mp.setattr(api,'_argv',lambda path,pin:[sys.executable,'-I','-B','-c',wrapped,str(path),pin])


def child_main(base,raw_root,mode,path,pin):
    from tests.test_h1_saved_job_development_v1 import install_child_source
    from tests.test_h1_timed_worker_hour_development_v1 import install
    mp = install_child_source(Path(base));no_solver.__wrapped__(mp)
    reports = [(Path(raw_root)/f'{i:03d}.bin').read_bytes() for i in range(3)]
    root = Path(path).parent
    solvers = install(mp,root/'worker_non_authoritative',reports)
    if mode == 'exit7': raise SystemExit(7)
    if mode == 'empty': return
    api.entry.execute(path,pin)
    assert [s.apply_calls for s in solvers] == [1,1,1]
    if mode == 'after_result': raise SystemExit(7)


def step(c,env,hour=0):
    return c.step(expected_source_identity=source_pin(env,hour),expected_head=c.inspect().head)


def test_two_timed_jobs_continuous_carry_and_readonly_reopen(tmp_path,environment,synthetic_reports,monkeypatch):
    install_launcher(monkeypatch,tmp_path,synthetic_reports)
    c = controller(tmp_path/'controller_non_authoritative',environment)
    try:
        first = step(c,environment)
        assert first.completed_hours == 1 and first.status == 'ready'
        rows,packet = synthetic_next_hour(c._parent,environment,synthetic_reports)
        install_launcher(monkeypatch,tmp_path,rows,label='next')
        final = step(c,environment,1)
        assert final.completed_hours == 2 and final.status == 'complete'
        assert c._parent._journal.inspect().events == 4
        assert not final.formal_result and not final.independent_hour_jobs_integrated
        before = c._parent._restore()[1]
        assert before.completed_hours == 2
        declarations = []
        for h in range(2):
            root = c._lease.root/f'job_{h:03d}_non_authoritative'
            request = json.loads((root/'request.json').read_bytes())
            declarations.append(request['input_receipt'])
            observed = json.loads((root/'observation.json').read_bytes())
            assert observed['exit_code'] == 0 and observed['whole_job_quiescent']
            assert observed['pid'] != os.getpid()
            assert json.loads((root/'worker_result.json').read_bytes())['schema'] == api.entry.SCHEMA
            bound = api.job_content_bound(3)
            files = [p for p in root.rglob('*') if p.is_file() and 'scratch_non_authoritative' not in p.parts]
            assert len(files) == bound['files'] and sum(p.stat().st_size for p in files) <= bound['logical_bytes']
        assert declarations[0]['before_identity'] != declarations[1]['before_identity']
        assert declarations[1]['relative_hour'] == 1
        declaration,identity,anchor = c._parent._declaration,c._parent.identity,c._parent._anchor.inspect().record_sha256
        reader = api.snapshot.open_snapshot(declaration,expected_parent_identity=identity,expected_anchor_record=anchor)
        try:
            reopened = reader.inspect()
            assert reopened == final
            assert reader._restore()[1] == before
            with pytest.raises(ValueError,match='requires Job controller'): reader.step_saved(())
        finally: reader.close()
        # Each fresh reopen must reject missing/drifted fixed records. These
        # mutations are only in the synthetic pytest fixture, then restored.
        job = c._lease.root/'job_000_non_authoritative'
        def reopen():
            return api.snapshot.open_snapshot(declaration,expected_parent_identity=identity,expected_anchor_record=anchor)
        for name in ('consumed.json','worker_result.json'):
            target = job/name;raw = target.read_bytes();stamp = target.stat()
            target.write_bytes(b'['+raw[1:]);os.utime(target,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
            try:
                with pytest.raises(ValueError): reopen()
            finally:
                target.write_bytes(raw);os.utime(target,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
            stash = tmp_path/('stash_'+name)
            target.rename(stash)
            try:
                with pytest.raises(ValueError): reopen()
            finally: stash.rename(target)
        target = job/'worker_non_authoritative/hour_non_authoritative/commits/000.json'
        raw = target.read_bytes();stamp = target.stat();original = api.worker.inspect
        def late(*args,**kwargs):
            value = original(*args,**kwargs)
            target.write_bytes(b'['+raw[1:]);os.utime(target,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
            return value
        try:
            with monkeypatch.context() as mp:
                mp.setattr(api.worker,'inspect',late)
                with pytest.raises(ValueError,match='changed'): reopen()
        finally:
            target.write_bytes(raw);os.utime(target,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
    finally: c.close()


@pytest.mark.parametrize('mode',['exit7','after_result'])
def test_nonzero_exit_never_reads_result_or_publishes_outcome(tmp_path,environment,synthetic_reports,monkeypatch,mode):
    install_launcher(monkeypatch,tmp_path,synthetic_reports,mode)
    c = controller(tmp_path/'controller_non_authoritative',environment,hours=1)
    reads = [];original = api.io.read_stable
    def read(path,*args,**kwargs):
        if path.name == 'worker_result.json': reads.append(path)
        return original(path,*args,**kwargs)
    monkeypatch.setattr(api.io,'read_stable',read)
    try:
        with pytest.raises(ValueError,match='Job unresolved'): step(c,environment)
        assert not reads and c._parent._poisoned
        assert c._parent._journal.inspect().events == 1
        root = c._lease.root/'job_000_non_authoritative'
        assert (root/'worker_result.json').exists() == (mode == 'after_result')
        assert not (c._parent._root/'hour_000_non_authoritative').exists()
        with pytest.raises(ValueError): c.step(expected_source_identity=source_pin(environment),expected_head='a'*64)
    finally: c.close()


def test_entry_successor_preserves_released_worker_algorithm():
    old_path = Path(api.parent.prior.__file__)
    new_path = Path(api.entry.__file__)
    class Normalize(ast.NodeTransformer):
        def visit_Attribute(self,node):
            node = self.generic_visit(node)
            if isinstance(node.value,ast.Name) and node.value.id == 'old' and node.attr == 'snapshot': return ast.Name(id='snapshot',ctx=ast.Load())
            return node
    def functions(path):
        tree = Normalize().visit(ast.parse(path.read_text(encoding='utf-8')))
        return {x.name:ast.dump(x,include_attributes=False) for x in tree.body
            if isinstance(x,(ast.FunctionDef,ast.ClassDef)) and x.name != 'implementation_identity'}
    assert functions(old_path) == functions(new_path)
    command = api._argv(Path('request.json'),'a'*64)
    assert command[1:4] == ['-I','-B','-c'] and 'development_v2 import execute' in command[4]


def test_bounds_cover_new_records_and_no_formal_authority():
    three = api.job_content_bound(3);full = api.job_content_bound(232)
    assert three['logical_bytes'] == 105494530 and three['files'] == 81
    assert full['logical_bytes'] == 7977525250 and full['files'] == 5119
    assert not full['resource_admission'] and not full['scratch_included']
    for n in (0,233,True):
        with pytest.raises(ValueError):api.job_content_bound(n)


def test_distinct_parent_protocol_rejects_legacy_snapshot_and_saved_route(tmp_path,environment):
    c = controller(tmp_path/'controller_non_authoritative',environment,hours=1)
    try:
        p = c._parent
        assert p._declaration['schema'] == api.parent.SCHEMA
        assert p._declaration['child_protocol'] == api.parent.CHILD_SCHEMA
        with pytest.raises(ValueError,match='declaration differs'):
            api.old.snapshot.open_snapshot(p._declaration,expected_parent_identity=p.identity,
                expected_anchor_record=p._anchor.inspect().record_sha256)
        with pytest.raises(ValueError,match='requires Job controller'): p.step_saved(())
        assert p._journal.inspect().events == 0
    finally: c.close()


@pytest.mark.parametrize('fault',['observation_before','observation_after','reference_before','reference_after',
    'outcome_before','outcome_after','anchor_after','source_wait','anchor_wait','job_close_after',
    'subtree_late','child_before_release'])
def test_persistence_source_and_job_close_failures_stop(tmp_path,environment,synthetic_reports,monkeypatch,fault):
    # Observation/anchor-before-output windows only need a real exit0 process;
    # all downstream publication windows execute the full synthetic worker.
    mode = 'empty' if fault in ('observation_before','anchor_wait','child_before_release') else 'normal'
    install_launcher(monkeypatch,tmp_path,synthetic_reports,mode)
    c = controller(tmp_path/'controller_non_authoritative',environment,hours=1)
    root = c._lease.root/'job_000_non_authoritative'
    p = c._parent
    original_write = api.entry.write
    def write(path,doc):
        target = ('observation.json' if fault.startswith('observation_') else
                  'reference.json' if fault.startswith('reference_') else None)
        if path.name == target:
            if fault.endswith('_after'): original_write(path,doc)
            raise OSError(fault)
        pin = original_write(path,doc)
        if fault == 'child_before_release' and path.name == 'release_intent.json':
            target = root/'child.json';raw = target.read_bytes();target.write_bytes(b'['+raw[1:])
        return pin
    monkeypatch.setattr(api.entry,'write',write)
    original_append = p._append
    def append(metadata,*args,**kwargs):
        if metadata['kind'] == 'accepted' and fault.startswith('outcome_'):
            if fault == 'outcome_after': original_append(metadata,*args,**kwargs)
            raise OSError(fault)
        return original_append(metadata,*args,**kwargs)
    monkeypatch.setattr(p,'_append',append)
    original_advance = p._anchor.advance
    def advance(*args,**kwargs):
        result = original_advance(*args,**kwargs)
        if fault == 'anchor_after' and p._journal.inspect().events == 2: raise OSError(fault)
        return result
    monkeypatch.setattr(p._anchor,'advance',advance)
    original_wait = api.old.process.NormalTaskChild.wait
    def wait(child):
        result = original_wait(child)
        assert result.exit_code == 0 and result.whole_job_quiescent
        if fault == 'source_wait': environment[3]['workload'] = '1'
        if fault == 'anchor_wait':
            path = p._root/'parent_anchor_non_authoritative/001.json'
            path.write_bytes(path.read_bytes()+b' ')
        return result
    monkeypatch.setattr(api.old.process.NormalTaskChild,'wait',wait)
    original_inspect = api.parent.inspect_job;inspections = []
    def inspect(*args,**kwargs):
        result = original_inspect(*args,**kwargs);inspections.append(True)
        if fault == 'subtree_late' and len(inspections) == 2:
            path = root/'worker_non_authoritative/hour_non_authoritative/commits/000.json'
            raw = path.read_bytes();stamp = path.stat()
            path.write_bytes(b'['+raw[1:]);os.utime(path,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
        return result
    monkeypatch.setattr(api.parent,'inspect_job',inspect)
    original_close = api.old.bounded.chunks.base.local._Lease.close
    def close(owner):
        original_close(owner)
        if fault == 'job_close_after' and owner.root == root: raise OSError(fault)
    monkeypatch.setattr(api.old.bounded.chunks.base.local._Lease,'close',close)
    reads = [];original_read = api.io.read_stable
    def read(path,*args,**kwargs):
        if path.name == 'worker_result.json': reads.append(path)
        return original_read(path,*args,**kwargs)
    monkeypatch.setattr(api.io,'read_stable',read)
    try:
        with pytest.raises((ValueError,OSError)) as error: step(c,environment)
        if fault not in ('source_wait','anchor_wait','subtree_late','child_before_release'): assert fault in str(error.value)
        if fault == 'subtree_late': assert 'Job changed before child reference' in str(error.value)
        assert p._poisoned
        events = 2 if fault in ('outcome_after','anchor_after') else 1
        assert p._journal.inspect().events == events
        if mode == 'empty' or fault == 'observation_after': assert not reads
        reference = p._root/'hour_000_non_authoritative/reference.json'
        assert reference.exists() == (fault in ('reference_after','outcome_before','outcome_after','anchor_after'))
        if fault == 'observation_before': assert not (root/'observation.json').exists()
        if fault == 'observation_after': assert (root/'observation.json').exists()
        if fault == 'observation_after': assert (root/'worker_result.json').exists()
        if fault == 'child_before_release': assert not (root/'consumed.json').exists()
        with pytest.raises(ValueError): c.step(expected_source_identity='a'*64,expected_head='b'*64)
        assert not (c._lease.root/'job_001_non_authoritative').exists()
    finally: c.close()


@pytest.mark.parametrize('which',['controller','parent','journal','anchor'])
@pytest.mark.parametrize('window',['unlock_before','unlock_after','new_owner_after_close'])
def test_close_detaches_owners_and_preserves_new_registry(tmp_path,environment,monkeypatch,which,window):
    import msvcrt
    c = controller(tmp_path/'controller_non_authoritative',environment,hours=1)
    p = c._parent
    target = {'controller':c._lease,'parent':p._root_lease,'journal':p._journal._lease,'anchor':p._anchor._lease}[which]
    root,fd = target.root,target.stream.fileno()
    Lease = api.old.bounded.chunks.base.local._Lease
    original_close,original_lock = Lease.close,msvcrt.locking
    replacements = []
    if window == 'new_owner_after_close':
        def close(owner):
            original_close(owner)
            if owner is target:
                replacements.append(Lease(root,False))
                raise OSError('after replacement acquired')
        monkeypatch.setattr(Lease,'close',close)
    else:
        def locking(handle,mode,count):
            if handle == fd and mode == msvcrt.LK_UNLCK:
                if window == 'unlock_after': original_lock(handle,mode,count)
                raise OSError('fixed unlock failure')
            return original_lock(handle,mode,count)
        monkeypatch.setattr(msvcrt,'locking',locking)
    try:
        with pytest.raises(OSError): c.close()
        assert c._lease is None and p._root_lease is None and p._journal is None and p._anchor is None
        c.close()
        if replacements:
            replacements[0].check()
            with pytest.raises(Exception): Lease(root,False)
        else:
            monkeypatch.setattr(msvcrt,'locking',original_lock)
            other = Lease(root,False);original_close(other)
    finally:
        monkeypatch.setattr(msvcrt,'locking',original_lock)
        monkeypatch.setattr(Lease,'close',original_close)
        for other in replacements: other.close()
        c.close()
