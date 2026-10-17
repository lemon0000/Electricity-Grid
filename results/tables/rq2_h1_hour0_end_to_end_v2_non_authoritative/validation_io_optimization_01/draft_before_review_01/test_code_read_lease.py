import importlib
import importlib.util
import os
from pathlib import Path
import py_compile
import sys
import tempfile
import unittest
from hashlib import sha256
from performance.code_read_lease import CodeReadLease


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


if __name__=='__main__':unittest.main(verbosity=2)
