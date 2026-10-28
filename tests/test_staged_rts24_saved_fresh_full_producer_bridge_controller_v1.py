"""Controller fault injection in temporary roots; no P1 or native child calls."""
import copy
from contextlib import redirect_stdout
import importlib.util
import io
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).absolute().parents[1]
DRIVER=ROOT/'results/tables/staged_rts24_saved_fresh_full_producer_bridge_v1_non_authoritative/driver.py'


class BridgeControllerTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('_bridge_controller_under_test',DRIVER)
        self.driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.driver)
        temp=tempfile.TemporaryDirectory(prefix='bridge_controller_');self.addCleanup(temp.cleanup)
        self.base=Path(temp.name);self.prior=self.base/'prior';self.prior.mkdir()
        self.cp=dict(accepted=True,diagnostic_accepted=True,all_cumulative_total_seconds=1088.9926936999939,
            prior_not_accepted_count=39,all_cumulative_charged_seconds=dict(static=529.8727752999941,
                pytest=366.48897970000326,unittest=192.63093869999648))
        raw=self.driver.canonical(self.cp);(self.prior/'checkpoint.json').write_bytes(raw)
        self.own=[]
        for index in range(7):
            path=self.base/('own_'+str(index));path.write_bytes(str(index).encode());self.own.append(path)
        for name,value in dict(OUT=self.new_root('initial'),PRIOR=self.prior,CHECKPOINT_SHA=self.driver.pin(raw)['sha256']).items():
            scope=patch.object(self.driver,name,value);scope.start();self.addCleanup(scope.stop)
        scope=patch.object(self.driver,'own',return_value=tuple(self.own));scope.start();self.addCleanup(scope.stop)

    def new_root(self,name):
        path=self.base/name;path.mkdir();(path/'driver.py').write_bytes(b'# temporary controller fixture\n');return path

    def seed(self,phases,failed=()):
        for action in phases:
            row=dict(accepted=action not in failed,authority='DRAFT_NONAUTHORITATIVE',action=action,
                kind='unittest' if action=='unittest' else 'static',charged_seconds=.2 if action=='unittest' else .1,
                cap_seconds=self.driver.CAPS[action],error='injected failure' if action in failed else None,payload={},**self.driver.flags())
            self.driver.output(action).write_bytes(self.driver.canonical(row))

    def invoke(self,action,accepted):
        clock=iter((10.,10.25))
        with patch.object(self.driver,'time',SimpleNamespace(perf_counter=lambda:next(clock))),redirect_stdout(io.StringIO()):
            if accepted:self.driver.run(action)
            else:
                with self.assertRaises(SystemExit) as caught:self.driver.run(action)
                self.assertEqual(caught.exception.code,1)
        return self.driver.read(self.driver.output(action))

    def inherited(self):
        result={str(self.base/('inherited_'+str(index))):self.driver.pin(b'i') for index in range(1178)}
        result.update({str(path):self.driver.pin(path.read_bytes()) for path in self.own[:2]})
        return result

    def test_01_archive_rejects_duplicate_paths_before_and_after_dict(self):
        paths=[]
        for index in range(155):
            path=self.base/('archive_'+str(index));path.write_bytes(b'a');paths.append(path)
        expected={str(path):self.driver.pin(b'a') for path in paths}
        with patch.object(self.driver,'ARCHIVE_BYTES',155):
            self.assertEqual(self.driver.archive_map(paths,expected),expected)
            for bad in (paths[:-1]+[paths[0]],paths[:-1]+[paths[0].with_name(paths[0].name.upper())]):
                with self.subTest(paths=bad[-1]),self.assertRaisesRegex(AssertionError,'unique'):
                    self.driver.archive_map(bad,expected)

    def test_02_archive_rejects_equal_size_foreign_set_and_byte_drift(self):
        paths=[]
        for index in range(155):
            path=self.base/('archive_'+str(index));path.write_bytes(b'a');paths.append(path)
        expected={str(path):self.driver.pin(b'a') for path in paths}
        foreign=self.base/'foreign';foreign.write_bytes(b'a')
        with patch.object(self.driver,'ARCHIVE_BYTES',155):
            with self.assertRaisesRegex(AssertionError,'exact set'):self.driver.archive_map(paths[:-1]+[foreign],expected)
            with self.assertRaisesRegex(AssertionError,'exact set'):self.driver.archive_map(paths,dict(list(expected.items())[:-1]))
            paths[0].write_bytes(b'aa')
            with self.assertRaisesRegex(AssertionError,'bounds'):self.driver.archive_map(paths,expected)

    def test_03_connected_and_own_input_relations_are_fixed(self):
        connected={str(index):self.driver.pin(b'i') for index in range(1157)}
        direct={**dict(list(connected.items())[:350]),**{'new_'+str(index):self.driver.pin(b'n') for index in range(10)}}
        registration=dict(input_pins=direct,effective_input_count=1167,inherited_effective_pins_pin=self.driver.pin(self.driver.canonical(connected)))
        self.assertEqual(len(self.driver.connected_inputs(connected,registration)),1167)
        for field in ('input_pins','effective_input_count','inherited_effective_pins_pin'):
            bad=copy.deepcopy(registration)
            if field=='input_pins':bad[field].pop('0')  # The inherited union is still 1167.
            elif field=='effective_input_count':bad[field]=1166
            else:bad[field]=self.driver.pin(b'foreign')
            with self.subTest(field=field),self.assertRaises(AssertionError):self.driver.connected_inputs(connected,bad)
        inherited=self.inherited();inputs,own=self.driver.input_maps(inherited)
        self.assertEqual(len(inputs),1185);self.assertEqual(len(own),7);self.assertEqual(len(inherited),1180)
        for bad in (dict(list(inherited.items())[1:]),{**inherited,'extra':self.driver.pin(b'x')}):
            with self.assertRaises(AssertionError):self.driver.input_maps(bad)
        inherited[str(self.own[0])]=self.driver.pin(b'foreign')
        with self.assertRaises(AssertionError):self.driver.input_maps(inherited)

    def test_04_check_rebuilds_input_archive_and_own_sets(self):
        inherited=self.inherited();inputs,own=self.driver.input_maps(inherited);archive={'a':self.driver.pin(b'a')}
        reg=dict(accepted=True,python_optimized=False,input_pins=inputs,effective_input_count=1185,archive_pins=archive,
            prior_archive_files=155,prior_archive_bytes=14350165,previous_checkpoint_pin=self.driver.pin((self.prior/'checkpoint.json').read_bytes()),
            derivation={'derived':True},unit_nodes=['synthetic'],own_input_pins=own,**self.driver.flags())
        builder=SimpleNamespace(current=lambda:(None,reg['derivation']))
        with patch.object(self.driver,'previous',return_value=(self.cp,inherited,archive)),patch.object(self.driver,'load',return_value=builder),patch.object(self.driver,'nodes',return_value=['synthetic']):
            self.assertIs(self.driver.check(reg),reg)
            for field in ('input_pins','archive_pins','own_input_pins','effective_input_count','prior_archive_files','prior_archive_bytes','previous_checkpoint_pin'):
                bad=copy.deepcopy(reg)
                if field.endswith('_pins'):bad[field].pop(next(iter(bad[field])))
                elif field=='previous_checkpoint_pin':bad[field]=self.driver.pin(b'foreign')
                else:bad[field]-=1
                if field=='input_pins':bad['effective_input_count']=len(bad['input_pins'])
                with self.subTest(field=field),self.assertRaises(AssertionError):self.driver.check(bad)
            bad=copy.deepcopy(reg);key=next(iter(bad['input_pins']));bad['input_pins']['foreign']=bad['input_pins'].pop(key)
            with self.assertRaisesRegex(AssertionError,'exact input set'):self.driver.check(bad)

    def test_05_phase_prefix_and_rejection_block_work(self):
        cases=(('unittest',(),()),('pre_seal',('register',),()),
            ('saved',('register','unittest'),()),('pre_seal',('register','unittest'),('unittest',)),
            ('unittest',('register',),('register',)))
        for index,(action,phases,failed) in enumerate(cases):
            with self.subTest(action=action,failed=failed),patch.object(self.driver,'OUT',self.new_root('prefix_'+str(index))):
                self.seed(phases,failed)
                with patch.object(self.driver,'previous') as previous,patch.object(self.driver,'check') as check,patch.object(self.driver,'load') as load:
                    row=self.invoke(action,False);self.assertFalse(row['accepted'])
                    previous.assert_not_called();check.assert_not_called();load.assert_not_called()

    def test_06_checkpoint_previous_error_keeps_charge_pins_and_record_count(self):
        self.seed(('register','unittest'),('unittest',))
        with patch.object(self.driver,'previous',side_effect=ValueError('previous failed')):
            row=self.invoke('checkpoint',False)
        self.assertEqual(row['error'],'ValueError:previous failed');self.assertTrue(row['accounting_complete'])
        self.assertEqual(row['charged_seconds'],.25);self.assertAlmostEqual(row['scope_charged_seconds']['static'],.35)
        self.assertAlmostEqual(row['scope_charged_seconds']['unittest'],.2);self.assertEqual(row['prior_not_accepted_count'],41)
        self.assertEqual(row['known_scope_not_accepted_records'],['unittest.exit.json'])
        self.assertIn(str(self.prior/'checkpoint.json'),row['known_pins']);self.assertIn(str(self.driver.output('unittest')),row['charged_record_pins'])
        self.assertAlmostEqual(row['all_cumulative_total_seconds'],1088.9926936999939+.55)

    def test_07_checkpoint_replay_and_canonical_errors_still_save(self):
        for index,mode in enumerate(('replay','canonical')):
            with self.subTest(mode=mode),patch.object(self.driver,'OUT',self.new_root('replay_'+str(index))):
                self.seed(self.driver.PHASES)
                replay=patch.object(self.driver,'saved',side_effect=ValueError('replay failed')) if mode=='replay' else patch.object(self.driver,'saved',return_value=object())
                with patch.object(self.driver,'previous',return_value=(self.cp,{},{})),patch.object(self.driver,'check',return_value={}),replay:
                    row=self.invoke('checkpoint',False)
                self.assertTrue(row['accounting_complete']);self.assertFalse(row['diagnostic_accepted'])
                self.assertEqual(row['charged_seconds'],.25);self.assertEqual(row['prior_not_accepted_count'],40)
                self.assertTrue(row['error'].startswith('ValueError:' if mode=='replay' else 'TypeError:'))

    def test_08_unprovable_predecessor_does_not_fabricate_cumulative(self):
        self.seed(('register',),('register',))
        with patch.object(self.driver,'previous',side_effect=OSError('prior missing')),patch.object(self.driver,'predecessor_accounting',side_effect=OSError('prior missing')):
            row=self.invoke('checkpoint',False)
        self.assertFalse(row['accounting_complete']);self.assertTrue(row['scope_accounting_complete'])
        self.assertIsNone(row['previous_cumulative']);self.assertIsNone(row['all_cumulative_total_seconds'])
        self.assertIsNone(row['all_cumulative_charged_seconds']);self.assertIsNone(row['prior_not_accepted_count'])
        self.assertAlmostEqual(row['package_charged_seconds'],.35);self.assertTrue(row['accounting_errors'])

    def test_09_malformed_record_marks_partial_accounting_and_keeps_raw_pin(self):
        for index,mode in enumerate(('noncanonical_success','noncanonical_failure','invalid_json','duplicate_key')):
            with self.subTest(mode=mode),patch.object(self.driver,'OUT',self.new_root('partial_'+str(index))):
                self.seed(('register','unittest'),('unittest',) if mode=='noncanonical_failure' else ())
                path=self.driver.output('unittest');raw=path.read_bytes()
                path.write_bytes(b'{' if mode=='invalid_json' else raw[:-1]+b',"charged_seconds":9}' if mode=='duplicate_key' else raw+b'\n')
                expected=self.driver.pin(path.read_bytes());row=self.invoke('checkpoint',False)
                self.assertFalse(row['scope_accounting_complete']);self.assertTrue(row['prior_accounting_complete'])
                self.assertIsNone(row['all_cumulative_total_seconds']);self.assertIsNone(row['prior_not_accepted_count'])
                self.assertEqual(row['charged_record_pins'][str(path)],expected)
                self.assertAlmostEqual(row['scope_charged_seconds']['static'],.35)
                self.assertEqual(row['scope_charged_seconds']['unittest'],.2 if mode.startswith('noncanonical') else 0.)
                self.assertEqual(row['known_scope_not_accepted_records'],['unittest.exit.json'] if mode=='noncanonical_failure' else [])

    def test_10_checkpoint_cannot_accept_unfinished_successful_prefix(self):
        self.seed(('register',))
        with patch.object(self.driver,'previous') as previous:
            row=self.invoke('checkpoint',False);previous.assert_not_called()
        self.assertFalse(row['diagnostic_accepted']);self.assertEqual(row['acceptance_scope'],'rejection_metadata_only')
        self.assertIn('unfinished accepted prefix',row['error'])

    def test_11_rejected_record_metadata_closes_without_rewriting_history(self):
        self.seed(('register',),('register',))
        with patch.object(self.driver,'previous',return_value=(self.cp,{},{})):
            row=self.invoke('checkpoint',True)
        self.assertTrue(row['accepted']);self.assertFalse(row['diagnostic_accepted']);self.assertEqual(row['prior_not_accepted_count'],40)
        self.assertEqual(row['previous_not_accepted_count'],39)
        before={path.name:path.read_bytes() for path in self.driver.OUT.iterdir()}
        with self.assertRaisesRegex(AssertionError,'terminal scope'):self.driver.run('unittest')
        self.assertEqual(before,{path.name:path.read_bytes() for path in self.driver.OUT.iterdir()})

    def test_12_checkpoint_own_cap_rejection_is_counted(self):
        self.seed(self.driver.PHASES)
        with patch.object(self.driver,'CAPS',{**self.driver.CAPS,'checkpoint':.01}),patch.object(self.driver,'previous',return_value=(self.cp,{},{})),patch.object(self.driver,'check',return_value={}),patch.object(self.driver,'saved',return_value={}):
            row=self.invoke('checkpoint',False)
        self.assertEqual(row['error'],'phase_cap_exceeded');self.assertEqual(row['charged_seconds'],.25)
        self.assertEqual(row['prior_not_accepted_count'],40);self.assertFalse(row['diagnostic_accepted'])
