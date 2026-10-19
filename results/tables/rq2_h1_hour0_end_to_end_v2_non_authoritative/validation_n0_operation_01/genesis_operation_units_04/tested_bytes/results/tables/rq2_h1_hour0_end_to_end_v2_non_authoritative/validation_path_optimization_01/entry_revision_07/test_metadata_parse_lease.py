from hashlib import sha256
import importlib.metadata as metadata
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from performance.metadata_parse_lease import MetadataParseLease
from performance import metadata_parse_lease as candidate


class MetadataLeaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='metadata_',dir=Path(__file__).parent)
        self.root=Path(self.temp.name);self.info=self.root/'lease_demo-1.0.dist-info'
        self.info.mkdir();self.file=self.info/'METADATA'
        self.file.write_text('Metadata-Version: 2.1\nName: lease-demo\nVersion: 1.0\n',encoding='utf-8')
        self.original=metadata.Distribution.version;sys.path.insert(0,str(self.root))
    def tearDown(self):
        self.assertIs(metadata.Distribution.version,self.original)
        sys.path.remove(str(self.root));self.temp.cleanup()
    def lease(self):return MetadataParseLease({self.file:sha256(self.file.read_bytes()).hexdigest()})

    def test_each_version_call_keeps_native_discovery(self):
        native=metadata.distribution;calls=[]
        def observed(name):calls.append(name);return native(name)
        with patch.object(metadata,'distribution',observed):
            with self.lease() as scope:
                for _ in range(4):self.assertEqual(metadata.version('lease-demo'),'1.0')
                self.assertEqual(calls,['lease-demo']*4)
                self.assertEqual(scope.receipt()['hits'],4)

    def test_sys_path_shadow_and_reordering_fall_back(self):
        shadow=self.root/'shadow';shadow.mkdir();dist=shadow/'lease_demo-2.0.dist-info';dist.mkdir()
        (dist/'METADATA').write_text('Metadata-Version: 2.1\nName: lease-demo\nVersion: 2.0\n')
        with self.lease() as scope:
            self.assertEqual(metadata.version('lease-demo'),'1.0')
            sys.path.insert(0,str(shadow))
            try:self.assertEqual(metadata.version('lease-demo'),'2.0')
            finally:sys.path.remove(str(shadow))
            self.assertEqual(scope.misses,1)

    def test_custom_distribution_and_subclass_fall_back(self):
        class Custom(metadata.Distribution):
            @property
            def metadata(self):return {'Version':'custom'}
            def read_text(self,name):return None
            def locate_file(self,path):return path
        class Derived(metadata.PathDistribution):
            @property
            def metadata(self):return {'Version':'subclass'}
        with self.lease() as scope:
            self.assertEqual(Custom().version,'custom')
            self.assertEqual(Derived(self.info).version,'subclass')
            self.assertEqual(scope.misses,2)

    def test_exact_distribution_instance_read_override_falls_back(self):
        with self.lease() as scope:
            self.assertEqual(metadata.version('lease-demo'),'1.0')
            selected=metadata.PathDistribution(self.info)
            selected.read_text=lambda name:'Name: lease-demo\nVersion: 8.0\n'
            self.assertEqual(selected.version,'8.0')
            self.assertEqual(scope.misses,1)

    def test_new_discovery_window_keeps_getter_identity_and_clears_values(self):
        with self.lease() as scope:
            getter=metadata.Distribution.version
            self.assertEqual(metadata.version('lease-demo'),'1.0')
            self.assertTrue(scope._values)
            scope.begin_discovery_window()
            self.assertIs(metadata.Distribution.version,getter)
            self.assertEqual(scope._values,{})
            self.assertEqual(metadata.version('lease-demo'),'1.0')
            self.assertEqual(scope.receipt()['discovery_windows'],1)

    def test_pkg_info_and_empty_metadata_never_use_cached_version(self):
        egg=self.root/'fallback.egg-info';egg.mkdir()
        (egg/'PKG-INFO').write_text('Name: fallback\nVersion: 3.0\n')
        with self.lease() as scope:
            self.assertEqual(metadata.PathDistribution(egg).version,'3.0')
            self.assertEqual(scope.misses,1)
        self.file.write_bytes(b'');pkg=self.info/'PKG-INFO';pkg.write_text('Name: lease-demo\nVersion: 4.0\n')
        with self.lease() as scope:
            self.assertEqual(metadata.version('lease-demo'),'4.0')
            pkg.write_text('Name: lease-demo\nVersion: 5.0\n')
            self.assertEqual(metadata.version('lease-demo'),'5.0');self.assertEqual(scope.hits,0)

    def test_parser_mutation_is_rejected_even_after_warm_hit(self):
        with self.lease():
            self.assertEqual(metadata.version('lease-demo'),'1.0')
            with patch.object(candidate.email,'message_from_string',lambda text:None):
                with self.assertRaisesRegex(ValueError,'parser or dispatch'):metadata.version('lease-demo')

    def test_direct_helper_substitution_is_rejected(self):
        for name,replacement in (('_key',lambda path:None),('_binding',lambda value:None)):
            with self.subTest(name=name),self.lease():
                self.assertEqual(metadata.version('lease-demo'),'1.0')
                with patch.object(candidate,name,replacement):
                    with self.assertRaisesRegex(ValueError,'parser or dispatch'):
                        metadata.version('lease-demo')

    def test_check_substitution_is_rejected_by_captured_check(self):
        with self.lease():
            with patch.object(MetadataParseLease,'_check',lambda self:None):
                with self.assertRaisesRegex(ValueError,'parser or dispatch'):
                    metadata.version('lease-demo')

    def test_getter_replacement_is_detected_and_restored(self):
        with self.assertRaisesRegex(ValueError,'parser or dispatch'):
            with self.lease():metadata.Distribution.version=property(lambda self:'foreign')

    def test_metadata_cannot_be_written_replaced_or_deleted_during_lease(self):
        other=self.root/'replacement';other.write_bytes(b'changed')
        with self.lease():
            for change in (lambda:self.file.write_bytes(b'changed'),lambda:os.replace(other,self.file),lambda:self.file.unlink()):
                with self.assertRaises(PermissionError):change()
        self.file.write_text('Name: lease-demo\nVersion: 6.0\n')
        self.assertEqual(metadata.version('lease-demo'),'6.0')

    def test_existing_writer_fails_and_releases_all_handles(self):
        scope=self.lease()
        with self.file.open('r+b'):
            with self.assertRaises(OSError):scope.__enter__()
        self.assertEqual(scope._handles,[])

    def test_exception_restores_getter(self):
        with self.assertRaisesRegex(RuntimeError,'injected'):
            with self.lease():raise RuntimeError('injected')


if __name__=='__main__':unittest.main(verbosity=2)
