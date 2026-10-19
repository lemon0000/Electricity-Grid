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

    def test_case_alias_duplicate_is_rejected(self):
        pin=sha256(self.original(self.file)).hexdigest()
        with self.assertRaisesRegex(ValueError,'duplicate canonical'):
            CodeReadLease({str(self.file):pin,str(self.file).upper():pin},root=self.root)

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


if __name__=='__main__':unittest.main(verbosity=2)
