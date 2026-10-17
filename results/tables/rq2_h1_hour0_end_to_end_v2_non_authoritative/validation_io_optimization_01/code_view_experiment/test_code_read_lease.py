import importlib
import importlib.util
import os
from pathlib import Path
import py_compile
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from hashlib import sha256
from performance.code_read_lease import CodeReadLease
from performance import code_read_lease as candidate


class CodeLeaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='lease_',dir=Path(__file__).parent)
        self.root=Path(self.temp.name);self.file=self.root/'a.py'
        self.file.write_bytes(b'value = 1\n');self.original=Path.read_bytes
    def tearDown(self):
        self.assertIs(Path.read_bytes,self.original);self.temp.cleanup()
    def lease(self,**kw):
        return CodeReadLease({self.file:sha256(self.original(self.file)).hexdigest()},root=self.root,**kw)

    def test_code_values_match_and_inputs_remain_fresh(self):
        other=self.root/'input.json';other.write_bytes(b'one')
        with self.lease() as scope:
            self.assertEqual(self.file.read_bytes(),b'value = 1\n')
            self.assertEqual(other.read_bytes(),b'one');other.write_bytes(b'two')
            self.assertEqual(other.read_bytes(),b'two')
            self.assertEqual(scope.receipt()['code_read_hits'],1)
            self.assertEqual(scope.receipt()['fallback_reads'],2)
        self.file.write_bytes(b'value = 2\n')

    def test_same_size_mtime_restored_write_replace_delete_rename_are_denied(self):
        replacement=self.root/'replacement.py';replacement.write_bytes(b'value = 2\n')
        saved=self.file.stat()
        with self.lease():
            for action in (lambda:self.file.write_bytes(b'value = 2\n'),
                           lambda:os.replace(replacement,self.file),
                           lambda:self.file.unlink(),lambda:self.file.rename(self.root/'renamed.py')):
                with self.assertRaises(PermissionError):action()
            os.utime(self.file,ns=(saved.st_atime_ns,saved.st_mtime_ns))
            self.assertEqual(self.file.read_bytes(),b'value = 1\n')

    def test_existing_writer_fails_closed_and_cleans_handles(self):
        scope=self.lease()
        with self.file.open('r+b'):
            with self.assertRaises(OSError):scope.__enter__()
        self.assertEqual(scope._handles,[])
        self.assertIs(Path.read_bytes,self.original)
        self.file.write_bytes(b'value = 3\n')

    def test_existing_delete_handle_fails_closed(self):
        handle=candidate._kernel.CreateFileW(str(self.file),0x10000,7,None,3,0x80,None)
        self.assertNotEqual(handle,candidate._INVALID)
        try:
            with self.assertRaises(OSError):self.lease().__enter__()
        finally:candidate._kernel.CloseHandle(handle)

    def test_hash_mismatch_and_byte_cap_fail_closed(self):
        scope=CodeReadLease({self.file:'0'*64},root=self.root)
        with self.assertRaisesRegex(ValueError,'expected code bytes'):scope.__enter__()
        self.assertEqual(scope._handles,[])
        scope=self.lease(max_bytes=1)
        with self.assertRaisesRegex(ValueError,'byte bound'):scope.__enter__()
        self.assertEqual(scope._handles,[])

    def test_ancestor_directory_rename_is_denied(self):
        with self.lease():
            with self.assertRaises(PermissionError):self.root.rename(self.root.with_name(self.root.name+'_moved'))

    def test_exception_restores_hooks_and_releases_handles(self):
        scope=self.lease()
        with self.assertRaisesRegex(RuntimeError,'injected'):
            with scope:raise RuntimeError('injected')
        self.assertEqual(scope._handles,[])
        self.file.write_bytes(b'value = 4\n')

    def test_dispatch_mutation_invalidates_context_and_restores_original(self):
        scope=self.lease()
        with self.assertRaisesRegex(ValueError,'dispatch changed'):
            with scope:scope._cached_read.__defaults__=(None,)
        self.assertEqual(scope._handles,[])

    def test_read_binding_replacement_is_rejected_and_original_restored(self):
        with self.assertRaisesRegex(ValueError,'dispatch changed'):
            with self.lease():Path.read_bytes=lambda self:b'foreign'

    def test_key_binding_replacement_is_rejected(self):
        with self.lease():
            with patch.object(candidate,'_key',lambda path:'foreign'):
                with self.assertRaisesRegex(ValueError,'dispatch changed'):self.file.read_bytes()

    def test_mapping_replacement_is_rejected_and_handles_released(self):
        scope=self.lease()
        with self.assertRaisesRegex(ValueError,'dispatch changed'):
            with scope:scope._data={}
        self.assertEqual(scope._handles,[])

    def test_reparse_file_is_rejected(self):
        alias=self.root/'alias.py'
        try:os.symlink(self.file,alias)
        except OSError as error:self.skipTest('symlink unavailable: '+str(error))
        with self.assertRaisesRegex(ValueError,'regular local'):
            CodeReadLease({alias:sha256(self.original(self.file)).hexdigest()},root=self.root).__enter__()

    def test_real_junction_ancestor_is_rejected(self):
        target=self.root/'target';target.mkdir();(target/'code.py').write_bytes(b'value = 1\n')
        alias=self.root/'junction'
        made=subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(alias),str(target)],capture_output=True)
        self.assertEqual(made.returncode,0,made.stderr)
        try:
            path=alias/'code.py'
            with self.assertRaisesRegex(ValueError,'regular local'):
                CodeReadLease({path:sha256(self.original(path)).hexdigest()},root=self.root).__enter__()
        finally:alias.rmdir()

    def test_reparse_handle_observed_after_open_is_rejected(self):
        actual=candidate._kernel.GetFileInformationByHandleEx
        def raced(handle,kind,buffer,size):
            result=actual(handle,kind,buffer,size)
            if result and kind==9:
                candidate.ctypes.cast(buffer,candidate.ctypes.POINTER(candidate._Attributes)).contents.attributes|=0x400
            return result
        scope=self.lease()
        with patch.object(candidate._kernel,'GetFileInformationByHandleEx',raced):
            with self.assertRaisesRegex(ValueError,'reparse handle'):scope.__enter__()
        self.assertEqual(scope._handles,[])

    def test_hardlinks_and_parent_aliases_are_rejected(self):
        alias=self.root/'alias.py';os.link(self.file,alias)
        with self.assertRaisesRegex(ValueError,'regular local'):self.lease().__enter__()
        alias.unlink()
        invalid=self.root/'..'/self.root.name/'a.py'
        with self.assertRaisesRegex(ValueError,'exact repo code'):
            CodeReadLease({invalid:sha256(self.original(self.file)).hexdigest()},root=self.root)

    def test_stale_pyc_is_bypassed_by_fresh_prefix(self):
        package=self.root/'stale_case.py';package.write_bytes(b'value = 1\n')
        saved=package.stat();py_compile.compile(str(package),doraise=True)
        package.write_bytes(b'value = 2\n');os.utime(package,ns=(saved.st_atime_ns,saved.st_mtime_ns))
        def load(name):
            spec=importlib.util.spec_from_file_location(name,package)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            return module.value
        self.assertEqual(load('stale_before'),1)
        prefix=self.root/'empty_pycache';prefix.mkdir()
        old=sys.pycache_prefix;sys.pycache_prefix=str(prefix)
        try:
            expected={package:sha256(self.original(package)).hexdigest()}
            with CodeReadLease(expected,root=self.root):self.assertEqual(load('fresh_under_lease'),2)
        finally:sys.pycache_prefix=old

    def reader_fixture(self):
        path=self.root/'reader.py'
        path.write_text('''import os
from pathlib import Path
def stamp(value):
    return (value.st_dev,value.st_ino,value.st_size,value.st_mtime_ns,value.st_ctime_ns)
def read_stable(path,cap):
    before=stamp(path.stat())
    with path.open('rb') as stream:
        opened=stamp(os.fstat(stream.fileno()))
        if before[:4]!=opened[:4]:raise ValueError('replaced before open')
        raw=stream.read(before[2]+1)
        after=stamp(os.fstat(stream.fileno()))
    if len(raw)>cap or len(raw)!=before[2] or after!=opened or stamp(path.stat())!=before:
        raise ValueError('fresh metadata drift')
    return raw,before
''',encoding='utf-8')
        expected={p:sha256(self.original(p)).hexdigest() for p in (self.file,path)}
        scope=CodeReadLease(expected,root=self.root,code_views=True)
        def load():
            name='code_reader_'+self.root.name
            spec=importlib.util.spec_from_file_location(name,path)
            module=importlib.util.module_from_spec(spec);sys.modules[name]=module
            spec.loader.exec_module(module);self.addCleanup(lambda:sys.modules.pop(name,None))
            scope.bind_readers((module.read_stable,));return module
        return scope,load

    def test_code_views_preserve_real_stat_fstat_and_bytes(self):
        scope,load=self.reader_fixture()
        original_stat=Path.stat;original_fstat=os.fstat;seen=[]
        def stat_(path,*a,**kw):
            if path==self.file:seen.append('stat')
            return original_stat(path,*a,**kw)
        def fstat_(fd):seen.append('fstat');return original_fstat(fd)
        with scope:
            module=load()
            with patch.object(Path,'stat',stat_),patch.object(os,'fstat',fstat_):
                raw,view=module.read_stable(self.file,1024)
            self.assertEqual(raw,b'value = 1\n')
            self.assertEqual(seen,['stat','fstat','fstat','stat'])
            self.assertEqual(scope.receipt()['code_view_hits'],1)
            with self.file.open('rb') as stream:self.assertNotIsInstance(stream,candidate._CodeBytes)
            self.assertEqual(scope.receipt()['code_view_hits'],1)

    def test_non_code_inputs_still_use_real_stream_and_detect_drift(self):
        scope,load=self.reader_fixture();source=self.root/'input.json';source.write_bytes(b'one')
        with scope:
            module=load();self.assertEqual(module.read_stable(source,1024)[0],b'one')
            source.write_bytes(b'two');self.assertEqual(module.read_stable(source,1024)[0],b'two')
            self.assertEqual(scope.receipt()['code_view_hits'],0)

    def test_code_metadata_change_is_detected_by_original_reader(self):
        scope,load=self.reader_fixture();original=os.fstat;calls=[]
        def changed(fd):
            calls.append(fd)
            if len(calls)==2:
                saved=self.file.stat();os.utime(self.file,ns=(saved.st_atime_ns,saved.st_mtime_ns+1_000_000_000))
            return original(fd)
        with scope:
            module=load()
            with patch.object(os,'fstat',changed):
                with self.assertRaisesRegex(ValueError,'metadata drift'):module.read_stable(self.file,1024)

    def test_reader_binding_replacement_invalidates_view_context(self):
        scope,load=self.reader_fixture()
        with self.assertRaisesRegex(ValueError,'bound code reader changed'):
            with scope:
                module=load();module.read_stable=lambda *a:None


if __name__=='__main__':unittest.main(verbosity=2)
