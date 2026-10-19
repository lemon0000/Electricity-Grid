from collections import Counter
import gc
import os
from types import SimpleNamespace
import unittest
import weakref

from performance.profile_code_counter_v1 import CodeCallCounter


def code(path, body='return 1'):
    namespace={}
    exec(compile('def observed():\n '+body+'\n',path,'exec'),namespace)
    return namespace['observed'].__code__


class ProfileCounterTests(unittest.TestCase):
    def test_counts_match_uncached_oracle_for_mixed_events_and_distinct_codes(self):
        path=os.path.abspath('observed_counter.py')
        codes=[code(path),code(path,'return 2'),code(os.path.abspath('excluded_counter.py'))]
        profiler=CodeCallCounter([path]);expected=Counter()
        events=[(codes[i%3],event) for i in range(21) for event in ('call','return','c_call')]
        for value,event in events:
            filename=os.path.normcase(value.co_filename)
            if event=='call' and filename==os.path.normcase(path):
                expected[(filename,value.co_name,value.co_firstlineno)]+=1
            profiler(SimpleNamespace(f_code=value),event,None)
        self.assertEqual(profiler.rows,expected)
        receipt=profiler.close()
        self.assertEqual(receipt['call_events'],21)
        self.assertEqual(receipt['filename_normalizations'],3)
        self.assertTrue(receipt['all_code_metadata_cache_entries_cleared'])

    def test_strong_references_prevent_code_id_reuse_until_close(self):
        value=code('ephemeral.py');reference=weakref.ref(value)
        profiler=CodeCallCounter([]);profiler(SimpleNamespace(f_code=value),'call',None)
        del value;gc.collect();self.assertIsNotNone(reference())
        profiler.close();gc.collect();self.assertIsNone(reference())

    def test_bound_refuses_before_recording_an_additional_code(self):
        profiler=CodeCallCounter([],max_codes=1)
        profiler(SimpleNamespace(f_code=code('a.py')),'call',None)
        with self.assertRaisesRegex(ValueError,'bound exceeded'):
            profiler(SimpleNamespace(f_code=code('b.py')),'call',None)
        self.assertEqual(profiler.call_events,1)
        self.assertEqual(len(profiler.codes),1)
        self.assertTrue(profiler.close()['all_code_metadata_cache_entries_cleared'])

    def test_closed_counter_refuses_further_events(self):
        profiler=CodeCallCounter([]);profiler.close()
        with self.assertRaisesRegex(ValueError,'already closed'):
            profiler(SimpleNamespace(f_code=code('a.py')),'call',None)
