"""Independent in-memory process/stream faults; no subprocess or native allocation."""
import copy
import io
from threading import Event,current_thread


def snapshot():
    return dict(parent=dict(working_set_bytes=10,peak_working_set_bytes=20,private_bytes=30),
        child=dict(working_set_bytes=5,peak_working_set_bytes=6,private_bytes=7))


def accepted_guard(native=False,child_pid=1001,parent_pid=1000):
    return dict(schema='staged_saved_F_sampled_memory_guard_v1',process_limit_bytes=268435456,pair_limit_bytes=536870912,
        poll_seconds=0.01,max_samples=4096,attempts=1,samples=1,maxima=snapshot(),
        max_sum_peak_working_set_bytes=26,max_sum_private_bytes=37,last=snapshot(),error=None,over_limit=False,sample_limit_reached=False,
        continuous_bound_verified=False,combined_retention_verified=False,resource_admission=False,
        sampler_mode='native' if native else 'injected_test',native_sampler_bound=native,
        binding=dict(parent_pid=parent_pid,child_pid=child_pid,child_handle=123,struct_bytes=80) if native else None,
        drained_child_pid=child_pid,sample_policy='last_live_poll_only',terminal_query_performed=False)


class Process:
    pid=1001
    _handle=1
    def __init__(self,alive=False,out=b'kept stdout',err=b'kept stderr',kill_error=False,wait_error=False):
        self.stdout=io.BytesIO(out);self.stderr=io.BytesIO(err);self.code=None;self.auto_exit=not alive;self.poll_calls=0
        self.kill_calls=0;self.kill_error=kill_error;self.wait_error=wait_error
    def poll(self):
        self.poll_calls+=1
        if self.code is None and self.auto_exit and self.poll_calls>=2:self.code=0
        return self.code
    def kill(self):
        self.kill_calls+=1
        if self.kill_error:raise OSError('fixture kill error')
        self.code=-9
    def wait(self,timeout):
        if self.wait_error:raise TimeoutError('fixture wait error')
        assert self.code is not None
        return self.code


def exercise(test,module):
    def run(process,sample=snapshot,clock=lambda:0.0):return module.test_drain(process,1.0,sample=sample,_clock=clock)
    def closed(row):
        test.assertTrue(row['pipes_closed']);test.assertTrue(row['reader_threads_terminal'])
    with test.subTest(memory='healthy terminal'):
        process=Process();code,out,err,why,row=run(process)
        test.assertEqual((code,out,err,why),(0,b'kept stdout',b'kept stderr',None))
        test.assertEqual(row['memory_guard'],accepted_guard());test.assertEqual(process.kill_calls,0);closed(row)
        test.assertEqual(module.validate_guard(row['memory_guard'],require_native=False),accepted_guard())
        with test.assertRaises(AssertionError):module.validate_guard(row['memory_guard'])
    for role,metric in (('child','peak_working_set_bytes'),('parent','private_bytes')):
        with test.subTest(memory=role+' threshold'):
            value=snapshot();value[role][metric]=268435457;process=Process(alive=True)
            code,out,err,why,row=run(process,lambda:value)
            test.assertEqual((code,why,process.kill_calls),(-9,'memory_limit',1));test.assertTrue(row['killed']);closed(row)
            test.assertEqual((out,err),(b'kept stdout',b'kept stderr'));test.assertTrue(row['memory_guard']['over_limit'])
            with test.assertRaises(AssertionError):module.validate_guard(row['memory_guard'],require_native=False)
    def failed():raise OSError('fixture memory query')
    with test.subTest(memory='query failure while live'):
        process=Process(alive=True);code,out,err,why,row=run(process,failed)
        test.assertEqual((code,why,process.kill_calls),(-9,'memory_observation_failed',1));closed(row)
        test.assertEqual((row['memory_guard']['attempts'],row['memory_guard']['samples']),(1,0))
        test.assertIn('fixture memory query',row['memory_guard']['error'])
    for value in (True,-1,'1'):
        with test.subTest(memory='invalid numeric sample',value=value):
            bad=snapshot();bad['child']['private_bytes']=value;process=Process(alive=True)
            code,out,err,why,row=run(process,lambda:bad)
            test.assertEqual((why,process.kill_calls),('memory_observation_failed',1));closed(row)
    with test.subTest(memory='peak below working set'):
        bad=snapshot();bad['child']['peak_working_set_bytes']=0
        code,out,err,why,row=run(Process(alive=True),lambda:bad)
        test.assertEqual(why,'memory_observation_failed');closed(row)
    with test.subTest(memory='no query after process exit'):
        samples=iter((snapshot(),None))
        def final_failure():
            value=next(samples)
            if value is None:raise OSError('fixture final query')
            return value
        process=Process();code,out,err,why,row=run(process,final_failure)
        test.assertEqual((code,why,process.kill_calls),(0,None,0));closed(row)
        test.assertEqual((row['memory_guard']['attempts'],row['memory_guard']['samples']),(1,1))
    with test.subTest(memory='original timeout'):
        stamps=iter((0.0,2.0));process=Process(alive=True)
        code,out,err,why,row=run(process,clock=lambda:next(stamps))
        test.assertEqual((code,why,process.kill_calls),(-9,'timeout',1));closed(row)
    with test.subTest(memory='original output cap'):
        code,out,err,why,row=run(Process(alive=True,out=b'x'*131073))
        test.assertEqual(why,'output_limit_or_reader_error');test.assertEqual(len(out),131072)
        test.assertEqual(row['stdout_observed_bytes'],131073);test.assertTrue(row['stdout_truncated']);closed(row)
    with test.subTest(memory='reader error'):
        class Broken(io.BytesIO):
            def read(self,size):raise OSError('fixture reader error')
        process=Process();process.stderr=Broken()
        code,out,err,why,row=run(process)
        test.assertEqual(why,'output_limit_or_reader_error');test.assertEqual(len(row['reader_errors']),1);closed(row)
    with test.subTest(memory='sample count bound'):
        guard=accepted_guard();guard.update(attempts=4096,samples=4096)
        def unused():raise AssertionError('sample limit must precede query')
        test.assertEqual(module.observe(guard,unused),'memory_sample_limit');test.assertTrue(guard['sample_limit_reached'])
        module.validate_guard(guard,healthy=False,require_native=False)
    with test.subTest(memory='kill and wait failure preserve memory cause'):
        value=snapshot();value['child']['private_bytes']=268435457
        process=Process(alive=True,kill_error=True,wait_error=True)
        code,out,err,why,row=run(process,lambda:value)
        test.assertEqual(why,'memory_limit');test.assertIsNone(code);test.assertEqual(process.kill_calls,1)
        test.assertEqual(row['cleanup'],['kill:OSError','wait:TimeoutError']);closed(row)
    for field,value in (('process_limit_bytes',268435457),('poll_seconds',1),('resource_admission',True),('samples',True),('over_limit',True)):
        with test.subTest(memory='guard record tamper',field=field):
            bad=copy.deepcopy(accepted_guard());bad[field]=value
            with test.assertRaises(AssertionError):module.validate_guard(bad,require_native=False)
    with test.subTest(memory='exact threshold allowed'):
        value=snapshot()
        for row in value.values():row.update(working_set_bytes=268435456,peak_working_set_bytes=268435456,private_bytes=268435456)
        code,out,err,why,row=run(Process(),lambda:value)
        test.assertIsNone(why);test.assertFalse(row['memory_guard']['over_limit']);closed(row)
    with test.subTest(memory='public native path rejects injected sampler'):
        process=Process()
        try:
            with test.assertRaises(TypeError):module.drain(process,1.0,sample=snapshot)
        finally:process.stdout.close();process.stderr.close()
    for field,value in (('child_pid',1002),('struct_bytes',88),('parent_pid',False)):
        with test.subTest(memory='native binding record mismatch',field=field):
            bad=accepted_guard(native=True);bad['binding'][field]=value
            with test.assertRaises(AssertionError):module.validate_guard(bad)
    for name in ('observe','_drain','Thread'):
        with test.subTest(memory='entry binding drift has zero effects',name=name):
            original=getattr(module,name);process=Process();process.code=0
            try:
                setattr(module,name,lambda *a,**k:None)
                with test.assertRaises(AssertionError):module.drain(process,1.0)
                test.assertEqual((process.poll_calls,process.kill_calls),(0,0))
                test.assertEqual((process.stdout.tell(),process.stderr.tell()),(0,0))
            finally:setattr(module,name,original);process.stdout.close();process.stderr.close()
    with test.subTest(memory='inplace actor keyword-default drift has zero effects'):
        defaults=module._drain.__kwdefaults__;original=defaults['_observe'];process=Process();process.code=0
        try:
            defaults['_observe']=lambda *a,**k:None
            with test.assertRaises(AssertionError):module.drain(process,1.0)
            test.assertEqual((process.poll_calls,process.kill_calls),(0,0))
            test.assertEqual((process.stdout.tell(),process.stderr.tell()),(0,0))
        finally:defaults['_observe']=original;process.stdout.close();process.stderr.close()
    with test.subTest(memory='reader remains pending and is rejected'):
        release=Event()
        class Blocked(io.BytesIO):
            owner=None
            def read(self,size):
                self.owner=current_thread();release.wait();return b''
        process=Process();blocked=Blocked();process.stdout=blocked
        try:
            code,out,err,why,row=run(process)
            test.assertEqual(why,'cleanup_unresolved');test.assertFalse(row['reader_threads_terminal']);test.assertFalse(row['pipes_closed'])
        finally:
            release.set()
            if blocked.owner is not None:blocked.owner.join(.5);test.assertFalse(blocked.owner.is_alive())
            process.stdout.close();process.stderr.close()
    with test.subTest(memory='pipe close error remains rejected'):
        class BadClose(io.BytesIO):
            def close(self):raise OSError('fixture close error')
        process=Process();process.stdout=BadClose(b'kept')
        try:
            code,out,err,why,row=run(process)
            test.assertEqual(why,'cleanup_unresolved');test.assertFalse(row['pipes_closed']);test.assertEqual(row['cleanup'],['pipe_close:OSError'])
        finally:io.BytesIO.close(process.stdout);process.stderr.close()
