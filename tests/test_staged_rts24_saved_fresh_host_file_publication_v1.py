"""Ordinary file-I/O and fake-leaf Host recovery validation; no F launch."""
import ast
from contextlib import contextmanager
import copy
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import threading
import time
import unittest

ROOT=Path(__file__).absolute().parents[1]
spec=importlib.util.spec_from_file_location('_host_file_fixture',ROOT/'tests/saved_fresh_host_file_fixture_v1.py')
F=importlib.util.module_from_spec(spec);spec.loader.exec_module(F)
FAULTS=set()
REAL=set()
EXPECTED_FAULTS={'write_zero','write_negative','write_boolean','write_oversize','write_budget','read_short','read_extra',
    'fsync_before','fsync_after','write_after','read_before','seek_after','close_before','close_after',
    'host_constructor_check','host_constructor_snapshot','host_constructor_clock','host_native_and_file_close',
    'host_quiet_and_file_close','host_unknown_open'}


@contextmanager
def real_case(raw):
    base=Path(tempfile.gettempdir()).resolve()/'electricity-grid-file-publication-v1-nonauthoritative'
    base.mkdir(exist_ok=True);base=base.resolve()
    with tempfile.TemporaryDirectory(prefix='case_',dir=base) as directory:
        owned=Path(directory).resolve();assert owned.is_relative_to(base) and owned!=base
        nonce='5'*64;parent=owned/'transport'/nonce;parent.mkdir(parents=True)
        path=str(parent/'controller.plan.json');module=F.clone(F.PUBLICATION,'_real_file_private','_mechanical_publication')
        value=F.binding(module,path,raw,nonce);value['invocation_started']=float(time.perf_counter());value['deadline']=value['invocation_started']+180.0
        clock=time.perf_counter
        try:yield module,value,clock,path,owned
        finally:assert owned.resolve().is_relative_to(base) and owned!=base


class PublicationTests(unittest.TestCase):
    def test_01_public_gates_and_no_implicit_close_or_delete(self):
        for path,gate,names in [(F.PUBLICATION,'_mechanical_publication',('BoundPublication','open_publication','_mechanical_publication')),
            (F.HOST,'_mechanical_host',('Host','open_full_role_host','_mechanical_host'))]:
            module=F.load(path,'_closed_'+gate)
            for name in names:
                with self.assertRaises(RuntimeError):getattr(module,name)()
        tree=ast.parse(F.PUBLICATION.read_bytes())
        names=[n.name for n in ast.walk(tree) if type(n) in (ast.FunctionDef,ast.AsyncFunctionDef)]
        self.assertNotIn('__del__',names)
        forbidden={'unlink','remove','rmdir','fdopen','FileIO','set_inheritable'}
        self.assertFalse([n for n in ast.walk(tree) if type(n) is ast.Attribute and n.attr in forbidden])

    def test_02_path_aliases_and_closed_binding_reject(self):
        h=F.Harness();nonce=h.binding['nonce'];tail='\\transport\\'+nonce+'\\controller.plan.json'
        paths=['D:relative'+tail,'\\\\server\\share'+tail,'\\\\?\\D:\\base'+tail,'D:\\base:ads'+tail,
            'D:\\base. '+tail,'D:\\base\\..'+tail,'D:\\base\\.'+tail,'D:\\base\\'+tail,
            'D:\\CON.txt'+tail,'D:\\CON .txt'+tail,'D:\\LPT\u00b9.txt'+tail,'D:\\CONIN$'+tail,
            'D:\\nul'+tail,'D:\\ba\0se'+tail,'D:\\b?se'+tail,'D:/base'+tail]
        for path in paths:
            value=dict(h.binding,path=path,parent=path.rpartition('\\')[0])
            with self.subTest(path=path),self.assertRaises(ValueError):h.m.binding_data(h.m.canonical(value))
        value=dict(h.binding,extra=True)
        with self.assertRaises(ValueError):h.m.binding_data(h.m.canonical(value))
        self.assertEqual(h.fs.events,[])

    def test_03_capsule_binding_clock_and_copy_reject(self):
        h=F.Harness();clock=h.root()['clock'];raw=h.m.canonical(h.binding)
        self.assertIs(h.m.check_binding(h.cap,raw,clock),h.cap)
        for fake in ({},object(),copy.copy(h.binding)):
            with self.assertRaises(ValueError):h.m.check_binding(fake,raw,clock)
        with self.assertRaises(TypeError):copy.copy(h.cap)
        clone=object.__new__(h.m.BoundPublication);object.__setattr__(clone,'_anchor',object.__getattribute__(h.cap,'_anchor'))
        with self.assertRaises(ValueError):h.m.snapshot(clone)
        with self.assertRaises(ValueError):h.m.check_binding(h.cap,raw,lambda:100.0)
        self.assertTrue(h.close());self.assertEqual(h.fs.events,[])

    def test_04_descriptor_zero_retained_through_two_bookends(self):
        h=F.Harness();receipt=h.publish()
        self.assertEqual(h.root()['fd'][0],0);self.assertEqual(h.fs.closed,[])
        self.assertEqual(receipt['content_pin'],h.m.pin(h.raw));self.assertFalse(receipt['role_authority'])
        for _ in range(2):self.assertEqual(h.m.published_read(h.cap,h.path),(h.raw,receipt))
        self.assertEqual(h.fs.events.count('open.before'),1)
        self.assertTrue(h.close());self.assertTrue(h.m.closed_witness(h.cap));self.assertEqual(h.fs.closed,[0])
        with self.assertRaises(ValueError):h.publish()
        with self.assertRaises(ValueError):h.m.published_read(h.cap,h.path)
        before=list(h.fs.events);self.assertTrue(h.close());self.assertEqual(h.fs.events,before)
        self.assertEqual(bytes(h.fs.data[h.path]),h.raw)

    def test_05_short_positive_writes_keep_monotonic_offsets(self):
        h=F.Harness(b'123456789012');h.fs.write_limit=2;h.publish()
        self.assertEqual(h.root()['write_offsets'],[2,4,6,8,10,12]);self.assertTrue(h.close())

    def test_06_bad_write_progress_rejects_without_retry(self):
        for value,name in [(0,'write_zero'),(-1,'write_negative'),(True,'write_boolean'),(1000,'write_oversize')]:
            h=F.Harness();h.fs.write_return=value
            with self.subTest(value=value),self.assertRaises(ValueError):h.publish()
            self.assertEqual(h.fs.events.count('write.before'),1);self.assertTrue(h.close());FAULTS.add(name)

    def test_07_write_call_bound_preserves_partial_file(self):
        h=F.Harness(b'123456789');h.fs.write_limit=1
        with self.assertRaises(ValueError):h.publish()
        self.assertEqual(bytes(h.fs.data[h.path]),b'12345678');self.assertEqual(h.fs.events.count('write.before'),8)
        self.assertTrue(h.close());FAULTS.add('write_budget')

    def test_08_read_requires_complete_bytes_and_eof(self):
        for attr,name in [('read_empty','read_short'),('read_extra','read_extra')]:
            h=F.Harness();setattr(h.fs,attr,True)
            with self.subTest(attr=attr),self.assertRaises(ValueError):h.publish()
            self.assertTrue(h.close());self.assertEqual(bytes(h.fs.data[h.path]),h.raw);FAULTS.add(name)

    def test_09_write_flush_and_read_exceptions_keep_primary(self):
        for point,name in [('fsync.before','fsync_before'),('fsync.after','fsync_after'),('write.after','write_after'),
            ('read.before','read_before'),('seek.after','seek_after')]:
            h=F.Harness();h.fs.fail=point
            with self.subTest(point=point),self.assertRaises(OSError) as caught:h.publish()
            self.assertIs(caught.exception,h.fs.error);self.assertIs(h.root()['primary'][0],h.fs.error)
            h.fs.fail=None;self.assertTrue(h.close());self.assertEqual(h.fs.closed,[0]);FAULTS.add(name)

    def test_10_existing_file_is_foreign_and_never_overwritten(self):
        h=F.Harness();h.fs.preexisting()
        with self.assertRaises(FileExistsError):h.publish()
        self.assertEqual(bytes(h.fs.data[h.path]),b'foreign');self.assertEqual(h.root()['opening'][0],'OPEN_UNCERTAIN')
        with self.assertRaises(h.m.PublicationUnresolved):h.close()
        self.assertEqual(h.fs.closed,[]);self.assertEqual(h.fs.events.count('open.before'),1)

    def test_11_open_return_capture_gap_stays_unknown(self):
        h=F.Harness();h.fs.fail='open.after'
        with self.assertRaises(OSError):h.publish()
        self.assertIsNone(h.root()['fd'][0]);self.assertIn(0,h.fs.fds)
        h.fs.fail=None
        with self.assertRaises(h.m.PublicationUnresolved) as first:h.close()
        before=list(h.fs.events)
        with self.assertRaises(h.m.PublicationUnresolved) as second:h.close()
        self.assertIs(first.exception,second.exception);self.assertEqual(h.fs.events,before);self.assertEqual(h.fs.closed,[])

    def test_12_inheritable_descriptor_rejects_and_closes_once(self):
        h=F.Harness();h.fs.inherit=True
        with self.assertRaises(ValueError):h.publish()
        self.assertTrue(h.close());self.assertEqual(h.fs.closed,[0]);self.assertNotIn('write.before',h.fs.events)

    def test_13_parent_nonordinary_and_reparse_reject_before_open(self):
        for key,value in [('st_file_attributes',0x400),('st_mode',stat.S_IFREG|0o600),('st_ino',0)]:
            h=F.Harness();h.fs.parents[h.binding['parent']][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):h.publish()
            self.assertNotIn('open.before',h.fs.events);self.assertTrue(h.close())

    def test_14_leaf_must_be_regular_nonreparse_single_link(self):
        for key,value in [('st_file_attributes',0x400),('st_mode',stat.S_IFDIR|0o700),('st_nlink',2)]:
            h=F.Harness()
            def callback(point):
                if point=='open.after':h.fs.meta[h.path][key]=value
            h.fs.callback=callback
            with self.subTest(key=key),self.assertRaises(ValueError):h.publish()
            h.fs.callback=None;self.assertTrue(h.close());self.assertEqual(h.fs.closed,[0])

    def test_15_opened_and_named_file_must_match(self):
        h=F.Harness();h.fs.path_ino_delta=1
        with self.assertRaises(ValueError):h.publish()
        self.assertTrue(h.close());self.assertEqual(h.fs.closed,[0])

    def test_16_parent_change_after_open_rejects_and_closes(self):
        h=F.Harness()
        def callback(point):
            if point=='open.after':h.fs.parents[h.binding['parent']]['st_ino']+=1
        h.fs.callback=callback
        with self.assertRaises(ValueError):h.publish()
        h.fs.callback=None;self.assertTrue(h.close());self.assertEqual(h.fs.closed,[0])

    def test_17_retained_identity_and_bytes_bookends_reject_drift(self):
        for kind in ('identity','bytes'):
            h=F.Harness();h.publish()
            if kind=='identity':h.fs.meta[h.path]['st_mtime_ns']+=1
            else:h.fs.data[h.path][0]^=1
            with self.subTest(kind=kind),self.assertRaises(ValueError):h.m.published_read(h.cap,h.path)
            self.assertTrue(h.close())

    def test_18_close_before_or_after_exception_is_sticky(self):
        for point,name in [('close.before','close_before'),('close.after','close_after')]:
            h=F.Harness();h.publish();h.fs.fail=point
            with self.subTest(point=point),self.assertRaises(h.m.PublicationUnresolved) as first:h.close()
            before=list(h.fs.events);h.fs.fail=None
            with self.assertRaises(h.m.PublicationUnresolved) as second:h.close()
            self.assertIs(first.exception,second.exception);self.assertEqual(h.fs.events,before)
            self.assertEqual(h.fs.events.count('close.before'),1);FAULTS.add(name)

    def test_19_descriptor_mirror_change_cleans_original(self):
        h=F.Harness();h.publish();h.root()['fd'][0]=99
        with self.assertRaises(ValueError):h.m.snapshot(h.cap)
        with self.assertRaises(h.m.PublicationUnresolved):h.close()
        self.assertEqual(h.fs.closed,[0]);self.assertEqual(h.root()['closing'][0],'CLOSED')

    def test_20_changed_close_callable_does_not_retry_or_call_it(self):
        h=F.Harness();h.publish();fn=h.root()['io'][-1].__func__;original=fn.__code__
        def different(self,fd):return None
        try:
            fn.__code__=different.__code__
            with self.assertRaises(h.m.PublicationUnresolved):h.close()
        finally:fn.__code__=original
        before=list(h.fs.events)
        with self.assertRaises(h.m.PublicationUnresolved):h.close()
        self.assertEqual(h.fs.events,before);self.assertEqual(h.fs.closed,[])

    def test_21_swallowed_publish_read_snapshot_close_reentry_sticks(self):
        for kind in ('publish','read','snapshot','close'):
            h=F.Harness()
            def callback(point):
                if point!='write.before':return
                try:
                    if kind=='publish':h.publish()
                    elif kind=='read':h.m.published_read(h.cap,h.path)
                    elif kind=='snapshot':h.m.snapshot(h.cap)
                    else:h.close()
                except BaseException:pass
            h.fs.callback=callback
            with self.subTest(kind=kind),self.assertRaises(ValueError):h.publish()
            h.fs.callback=None
            with self.assertRaises(h.m.PublicationUnresolved):h.close()
            self.assertEqual(h.fs.closed,[0]);self.assertGreater(h.root()['reentry'][0],0)

    def test_22_post_open_clock_expiry_preserves_captured_fd(self):
        h=F.Harness()
        def callback(point):
            if point=='open.after':h.now=111.0
        h.fs.callback=callback
        with self.assertRaises(ValueError):h.publish()
        self.assertEqual(h.root()['fd'][0],0);self.assertEqual(h.root()['opening'][0],'OPEN_CAPTURED');h.fs.callback=None
        with self.assertRaises(h.m.PublicationUnresolved):h.close()
        self.assertEqual(h.fs.closed,[0])

    def test_23_post_close_clock_failure_never_recloses(self):
        h=F.Harness();h.publish()
        def callback(point):
            if point=='close.after':h.now=281.0
        h.fs.callback=callback
        with self.assertRaises(h.m.PublicationUnresolved) as first:h.close()
        self.assertEqual(h.root()['closing'][0],'CLOSED');self.assertEqual(h.fs.closed,[0]);before=list(h.fs.events)
        with self.assertRaises(h.m.PublicationUnresolved) as second:h.close()
        self.assertIs(first.exception,second.exception);self.assertEqual(h.fs.events,before)

    def test_24_independent_maximum_path_and_transfer_call_oracle(self):
        path='D:\\'+'\\'.join(['a']*29+['transport','4'*64,'controller.plan.json'])
        h=F.Harness(b'x'*131072,path);h.fs.write_limit=16384;h.fs.read_limit=20000
        h.publish();h.m.published_read(h.cap,h.path);h.m.published_read(h.cap,h.path);h.close()
        self.assertEqual(len(h.fs.parents),32);self.assertEqual(h.root()['io_count'][0],539)
        self.assertEqual(h.fs.events.count('write.before'),8);self.assertEqual(h.fs.events.count('read.before'),24)
        self.assertEqual(h.fs.events.count('close.before'),1)

    def test_25_terminal_state_drift_becomes_sticky_without_io(self):
        h=F.Harness();h.publish();h.close();before=list(h.fs.events);h.root()['state'][0]='NEW'
        with self.assertRaises(ValueError):h.m.closed_witness(h.cap)
        with self.assertRaises(h.m.PublicationUnresolved) as first:h.close()
        with self.assertRaises(h.m.PublicationUnresolved) as second:h.close()
        self.assertIs(first.exception,second.exception);self.assertEqual(h.fs.events,before)

    def test_26_other_thread_and_process_identity_reject(self):
        h=F.Harness();h.publish();seen=[]
        def other():
            try:h.m.published_read(h.cap,h.path)
            except ValueError:seen.append('rejected')
        worker=threading.Thread(target=other);worker.start();worker.join(2)
        self.assertFalse(worker.is_alive());self.assertEqual(seen,['rejected'])
        original=h.m.creator;h.m.creator=lambda:(original()[0]+1,original()[1])
        try:
            with self.assertRaises(ValueError):h.m.snapshot(h.cap)
        finally:h.m.creator=original
        self.assertTrue(h.close())

    def test_27_real_stdlib_create_read_flush_and_retained_file(self):
        raw=b'x'*131072
        with real_case(raw) as (m,value,clock,path,owned):
            cap=m._mechanical_publication(object(),m.canonical(value),clock);m.check_binding(cap,m.canonical(value),clock)
            receipt=m.publish(cap,path,raw);root=dict(object.__getattribute__(cap,'_anchor'))
            info=os.fstat(root['fd'][0]);self.assertFalse(os.get_inheritable(root['fd'][0]))
            self.assertEqual((receipt['file_identity']['dev'],receipt['file_identity']['ino'],receipt['file_identity']['size']),
                (info.st_dev,info.st_ino,info.st_size))
            self.assertEqual(m.published_read(cap,path),(raw,receipt));self.assertEqual(m.published_read(cap,path),(raw,receipt))
            self.assertTrue(m.close(cap,value['deadline']));self.assertTrue(m.closed_witness(cap));self.assertEqual(Path(path).read_bytes(),raw)
        self.assertFalse(owned.exists());REAL.add('create_read_close')

    def test_28_real_stdlib_existing_file_preserved(self):
        with real_case(b'new') as (m,value,clock,path,owned):
            Path(path).write_bytes(b'foreign');cap=m._mechanical_publication(object(),m.canonical(value),clock)
            with self.assertRaises(FileExistsError):m.publish(cap,path,b'new')
            with self.assertRaises(m.PublicationUnresolved):m.close(cap,value['deadline'])
            self.assertEqual(Path(path).read_bytes(),b'foreign')
        self.assertFalse(owned.exists());REAL.add('existing_foreign')

    def test_29_real_stdlib_partial_write_retained_after_failure(self):
        raw=b'partial bytes'
        with real_case(raw) as (m,value,clock,path,owned):
            error=OSError('ordinary fixture after partial write')
            def fail(fd,data):os.write(fd,data[:2]);raise error
            functions=[getattr(os,name) for name in m.IO_NAMES];functions[m.IO_NAMES.index('write')]=fail
            cap=m._mechanical_publication(object(),m.canonical(value),clock,tuple(functions))
            with self.assertRaises(OSError) as caught:m.publish(cap,path,raw)
            self.assertIs(caught.exception,error);self.assertTrue(m.close(cap,value['deadline']));self.assertEqual(Path(path).read_bytes(),raw[:2])
        self.assertFalse(owned.exists());REAL.add('partial_retained')

    def test_30_real_stdlib_external_change_is_detected(self):
        raw=b'original bytes'
        with real_case(raw) as (m,value,clock,path,owned):
            cap=m._mechanical_publication(object(),m.canonical(value),clock);m.publish(cap,path,raw)
            with open(path,'r+b') as stream:stream.write(b'changed!');stream.flush();os.fsync(stream.fileno())
            with self.assertRaises(ValueError):m.published_read(cap,path)
            self.assertTrue(m.close(cap,value['deadline']));self.assertNotEqual(Path(path).read_bytes(),raw)
        self.assertFalse(owned.exists());REAL.add('external_change')

    def test_31_full_private_host_connects_file_and_native_bodies(self):
        w=F.World();binding=w.bound();w.m.release(w.host,w.m.release_ack_bytes(binding));w.m.close(w.host)
        self.assertEqual(w.fs.closed,[0]);self.assertEqual(w.file_root()['reads'][0],2)
        self.assertEqual(w.root()['publication_cleanup'],['CLOSED',1]);self.assertEqual(w.root()['cleanup'][0],'CLOSED')
        self.assertTrue(w.k.unmapped);self.assertTrue({101,102,201,202,203}.issubset(w.k.closed))
        self.assertEqual(w.fs.events.count('open.before'),1)

    def test_32_constructor_check_snapshot_and_clock_failure_cleanup(self):
        for point in ('check','snapshot','clock'):
            w=F.World.__new__(F.World)
            with self.subTest(point=point),self.assertRaises(RuntimeError) as caught:w.__init__(point)
            self.assertTrue(hasattr(caught.exception,'host'));self.assertEqual(w.file_root()['closing'][0],'NEVER_OPENED')
            self.assertEqual(w.file_root()['cleanup'][0],'CLOSED');self.assertEqual(w.fs.events,[])
            with self.assertRaises(w.m.HostUnresolved) as replay:w.m.close(caught.exception.host)
            self.assertIs(replay.exception,caught.exception);self.assertEqual(w.fs.events,[]);FAULTS.add('host_constructor_'+point)

    def test_33_failed_job_quiet_still_closes_file(self):
        w=F.World();w.bound();w.k.accounting_extra=1
        with self.assertRaises(w.m.HostUnresolved):w.m.close(w.host)
        self.assertEqual(w.fs.closed,[0]);self.assertEqual(w.k.closed,set());self.assertEqual(w.root()['cleanup'][0],'UNRESOLVED')
        FAULTS.add('host_quiet_and_file_close')

    def test_34_native_primary_and_file_close_failure_both_survive(self):
        w=F.World();w.bound();w.fs.fail='close.after';primary=w.k.error
        with self.assertRaises(w.m.HostUnresolved) as caught:w.m.close(w.host,primary)
        self.assertIs(caught.exception.primary,primary);self.assertTrue(any(name=='publication_close' for name,error in caught.exception.secondary))
        self.assertEqual(w.fs.closed,[0]);self.assertEqual(w.file_root()['closing'][0],'CLOSE_UNCERTAIN');FAULTS.add('host_native_and_file_close')

    def test_35_failed_publication_snapshot_does_not_suppress_close(self):
        w=F.World();w.bound();w.snapshot_failure=True
        with self.assertRaises(w.m.HostUnresolved):w.m.close(w.host)
        self.assertEqual(w.fs.closed,[0]);self.assertEqual(w.file_root()['cleanup'][0],'CLOSED')
        self.assertTrue(w.k.unmapped)

    def test_36_replaced_capsule_mirror_cleans_original(self):
        w=F.World();binding=w.bound();root=w.root();root['publication_owner']=object()
        object.__setattr__(w.host,'_anchor',tuple(root.items()))
        with self.assertRaises(w.m.HostUnresolved):w.m.release(w.host,w.m.release_ack_bytes(binding))
        self.assertEqual(w.fs.closed,[0]);self.assertEqual(w.root()['cleanup'][0],'UNRESOLVED')

    def test_37_impossible_publication_snapshots_reject(self):
        cases=[(6,'wrong_reservation'),(3,'missing_fd'),(7,'offset_reverse'),(7,'offset_count'),(8,'read_count'),
            (9,'io_count'),(10,'reentry'),(4,'closed_idle'),(5,'cleanup_closed'),(2,'open_rewind'),(6,'reservation_rewind')]
        for index,name in cases:
            w=F.World();w.bound()
            def mutation(value):
                result=list(value)
                changes={'wrong_reservation':(value[6][0],2,value[6][2]),'missing_fd':None,'offset_reverse':(3,1),
                    'offset_count':tuple(range(1,10)),'read_count':3,'io_count':540,'reentry':1,'closed_idle':'CLOSED',
                    'cleanup_closed':'CLOSED','open_rewind':'IDLE','reservation_rewind':None}
                result[index]=changes[name];return tuple(result)
            w.snapshot_mutation=mutation
            with self.subTest(case=name),self.assertRaises(ValueError):w.m._publication_bookend(w.root())
            w.snapshot_mutation=None;w.m.close(w.host);self.assertEqual(w.fs.closed,[0])

    def test_38_host_terminal_replay_has_no_file_io_and_detects_drift(self):
        w=F.World();w.bound();w.m.close(w.host);before=list(w.fs.events);w.m.close(w.host)
        self.assertEqual(w.fs.events,before);w.file_root()['state'][0]='NEW'
        with self.assertRaises(w.m.HostUnresolved) as first:w.m.close(w.host)
        with self.assertRaises(w.m.HostUnresolved) as second:w.m.close(w.host)
        self.assertIs(first.exception,second.exception);self.assertEqual(w.fs.events,before)

    def test_39_unknown_open_prevents_host_closed_and_native_launch(self):
        w=F.World();w.acked();w.fs.fail='open.after'
        with self.assertRaises(w.m.HostUnresolved) as first:w.m.prepare(w.host)
        self.assertEqual(w.root()['cleanup'][0],'UNRESOLVED');self.assertEqual(w.k.count('CreateProcessW'),0)
        self.assertEqual(w.fs.closed,[]);before=list(w.fs.events)
        with self.assertRaises(w.m.HostUnresolved) as second:w.m.close(w.host)
        self.assertIs(first.exception,second.exception);self.assertEqual(w.fs.events,before);FAULTS.add('host_unknown_open')

    def test_40_original_host_budgets_and_source_bytes_preserved(self):
        old=ast.parse((ROOT/'experiments/staged_rts24_saved_fresh_full_role_host_preentry_v2.py').read_bytes());new=ast.parse(F.HOST.read_bytes())
        for name in ('CAPS','STAGES','SOURCE_EPOCH','RESOURCES'):
            def value(tree):return ast.dump(next(n.value for n in tree.body if type(n) is ast.Assign and n.targets[0].id==name),include_attributes=False)
            self.assertEqual(value(old),value(new))
        self.assertEqual(FAULTS,EXPECTED_FAULTS);self.assertEqual(REAL,{'create_read_close','existing_foreign','partial_retained','external_change'})

    def test_41_committed_responsibility_states_cannot_rewind(self):
        for kind in ('opening_issued','opening_unknown','closing_issued','closing_closed','closing_unknown','never_opened','cleanup_issued'):
            w=F.World();active=kind in ('closing_issued','closing_closed','closing_unknown','cleanup_issued')
            if active:w.bound()
            original=w.fm.snapshot(w.pub);future=list(original)
            future[6]=(w.file_binding['path'],1,w.file_binding['manifest_pin']['bytes'])
            if kind.startswith('opening_'):future[2]='OPEN_ISSUED' if kind=='opening_issued' else 'OPEN_UNCERTAIN'
            elif kind=='never_opened':future[4:6]=['NEVER_OPENED','CLOSED']
            elif kind=='cleanup_issued':future[5]='ISSUED'
            else:future[4:6]={'closing_issued':['CLOSE_ISSUED','ISSUED'],'closing_closed':['CLOSED','CLOSED'],
                'closing_unknown':['CLOSE_UNCERTAIN','UNRESOLVED']}[kind]
            future=tuple(future);w.snapshot_mutation=lambda value:future
            self.assertEqual(w.m._publication_snapshot(w.root()),future)
            rewound=list(original);rewound[6]=future[6];rewound=tuple(rewound)
            w.snapshot_mutation=lambda value:rewound
            with self.subTest(kind=kind),self.assertRaises(ValueError):w.m._publication_snapshot(w.root())
            w.snapshot_mutation=None
            with self.assertRaises(w.m.HostUnresolved):w.m.close(w.host)
            self.assertEqual(w.fs.closed,[0] if active else [])


def contract():
    assert FAULTS==EXPECTED_FAULTS and len(FAULTS)==20 and len(REAL)==4
    return dict(schema='staged_saved_F_host_file_publication_contract_v1',methods=41,fault_cases=sorted(FAULTS),real_stdlib_cases=sorted(REAL),
        private_gates_removed=['_mechanical_host','_mechanical_publication','_mechanical_resources'],
        synthetic_host_native_leaves=True,ordinary_filesystem_unit=True,publication_body_connected=True,
        descriptor_capture_gap_unresolved=True,hostile_path_containment_verified=False,system_DLL_identity_authenticated=False,
        source_authenticated_host_issuer=False,full_role_entry_connected=False,physical_host_provider_implemented=False,
        native_authorized=False,native_equivalence_verified=False,hard_filesystem_deadline_verified=False,
        continuous_RSS_measured=False,resource_admission=False,run_authority=False,actual_F=False,formal_result=False,
        source49_modules_executed=0,P1_reads=0,project_target_child_processes=0,validation_child_processes=0,
        win32_file_backend_calls=0,NFC12_reruns=0)
