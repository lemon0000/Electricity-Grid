"""Pure pin-method and controlled-loader fixtures; no native hook or scientific import."""
import builtins
import hashlib
import importlib.util
from pathlib import Path
import types
import unittest

ROOT=Path(__file__).absolute().parents[1]
SOURCE=ROOT/'experiments/staged_rts24_saved_fresh_pin_memo_v1.py'
spec=importlib.util.spec_from_file_location('_pin_memo_fixture',SOURCE)
method=importlib.util.module_from_spec(spec);spec.loader.exec_module(method)


def pin(raw):return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


MODULE_SOURCE=b'''from hashlib import sha256
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def load(path,name):return factory(path,name)
def check(provider,rows):
    for path,expected in rows:
        assert pin(provider(path))==expected,path
'''


def module(path='fixture.py',factory=None):
    value=types.ModuleType('_memo_fresh_module');value.__file__=path
    exec(compile(MODULE_SOURCE,path,'exec',dont_inherit=True,optimize=0),vars(value))
    value.factory=factory
    return value


class PinMemoTests(unittest.TestCase):
    def test_01_equal_raw_fresh_dict_and_bounded_fallback(self):
        for caps in ((8,1024),(0,1024),(8,0)):
            memo=method.PinMemo(*caps);calls=[]
            def original(raw):calls.append(bytes(raw));return pin(raw)
            a=memo.pin(b'abc',original);a['bytes']=999;a['sha256']='changed'
            b=memo.pin(bytes(bytearray(b'abc')),original)
            self.assertEqual(b,pin(b'abc'));self.assertIsNot(a,b)
            self.assertEqual(len(calls),1 if caps==(8,1024) else 2)
            self.assertEqual(memo.pin(bytearray(b'abc'),original),pin(b'abc'))
            before=memo.metrics();self.assertLessEqual(before['resident_bytes'],caps[1]);self.assertLessEqual(before['entries'],caps[0])
            memo.close();self.assertEqual(memo.metrics()['entries'],0)
            with self.assertRaises(ValueError):memo.pin(b'abc',original)

    def test_02_every_duplicate_mutation_and_ABA(self):
        for changed_at in range(1,6):
            rows=[('D:/same',pin(b'A'))]*6
            def run(new):
                trace=[];memo=method.PinMemo()
                for index,(path,expected) in enumerate(rows):
                    raw=b'A' if index<changed_at else b'B';trace.append((path,raw))
                    actual=memo.pin(raw,pin) if new else pin(raw)
                    if actual!=expected:return index,trace
                raise AssertionError('mutation not observed')
            self.assertEqual(run(False),run(True))
        memo=method.PinMemo();calls=[]
        def original(raw):calls.append(raw);return pin(raw)
        self.assertEqual([memo.pin(raw,original) for raw in (b'A',b'B',b'A')],[pin(raw) for raw in (b'A',b'B',b'A')])
        self.assertEqual(calls,[b'A',b'B'])

    def test_03_read_exception_each_position_preserves_primary(self):
        for failed_at in range(6):
            primary=OSError('read failure')
            def run(new):
                memo=method.PinMemo();trace=[]
                try:
                    for index in range(6):
                        trace.append(index)
                        if index==failed_at:raise primary
                        value=memo.pin(b'A',pin) if new else pin(b'A')
                        self.assertEqual(value,pin(b'A'))
                except OSError as error:return error,trace
            old,new=run(False),run(True);self.assertIs(old[0],primary);self.assertIs(new[0],primary);self.assertEqual(old[1],new[1])

    def test_04_conflicting_expected_and_path_aliases(self):
        for rows in ([('D:/same',pin(b'A')),('D:/same',pin(b'B'))],[('D:/same',pin(b'B')),('D:/same',pin(b'A'))]):
            a=module();b=module();trace=[]
            def provider(path):trace.append(path);return b'A'
            with self.assertRaises(AssertionError):a.check(provider,rows)
            old=list(trace);trace.clear()
            with method.MetadataPinSession({'fixture.py':method.function_references(MODULE_SOURCE,'fixture.py')}) as session:
                session.attach(b)
                with self.assertRaises(AssertionError):b.check(provider,rows)
            self.assertEqual(trace,old)
        rows=[('D:/alias',pin(b'A')),('D:/ALIAS',pin(b'B')),('D:/other',pin(b'A'))]
        trace=[]
        def provider(path):trace.append(path);return b'B' if path=='D:/ALIAS' else b'A'
        refs={'fixture.py':method.function_references(MODULE_SOURCE,'fixture.py')}
        with method.MetadataPinSession(refs) as session:session.attach(module()).check(provider,rows)
        self.assertEqual(trace,[p for p,_ in rows]);self.assertEqual(session._last_metrics['hits'],1)

    def test_05_sha_failure_does_not_create_cache_entry(self):
        memo=method.PinMemo();primary=RuntimeError('first SHA failure')
        def broken(raw):raise primary
        with self.assertRaises(RuntimeError) as caught:memo.pin(b'A',broken)
        self.assertIs(caught.exception,primary);self.assertEqual(memo.metrics()['entries'],0)
        self.assertEqual(memo.pin(b'A',pin),pin(b'A'));self.assertEqual(memo.metrics()['entries'],1)

    def test_06_fresh_loader_modules_and_restore_after_error(self):
        loaded=[]
        def factory(path,name):
            value=module(path,factory);loaded.append(value);return value
        a=module('a.py',factory);original=(a.pin,a.load)
        refs={p:method.function_references(MODULE_SOURCE,p) for p in ('a.py','b.py')}
        primary=LookupError('caller failure')
        with self.assertRaises(LookupError) as caught:
            with method.MetadataPinSession(refs) as session:
                session.attach(a);b=a.load('b.py','first');c=a.load('b.py','second')
                self.assertIsNot(b,c);self.assertEqual(len(loaded),2)
                self.assertEqual(b.pin(b'X'),pin(b'X'));self.assertEqual(c.pin(b'X'),pin(b'X'))
                raise primary
        self.assertIs(caught.exception,primary);self.assertIs(a.pin,original[0]);self.assertIs(a.load,original[1])
        self.assertTrue(session.memo.metrics()['closed']);self.assertEqual(session.memo.metrics()['resident_bytes'],0)
        self.assertEqual(session._modules,[])

    def test_07_global_and_function_bookends(self):
        refs={'fixture.py':method.function_references(MODULE_SOURCE,'fixture.py')}
        for kind in ('extra','binding','code','defaults','managed'):
            a=module();original=(a.pin,a.load)
            with self.assertRaises(ValueError):
                with method.MetadataPinSession(refs) as session:
                    session.attach(a)
                    if kind=='extra':a.extra=True
                    elif kind=='binding':a.factory=object()
                    elif kind=='managed':a.pin=pin
                    elif kind=='defaults':original[0].__defaults__=(None,)
                    else:original[0].__code__=pin.__code__
            self.assertIs(a.pin,original[0]);self.assertIs(a.load,original[1]);self.assertTrue(session.memo.metrics()['closed'])
        a=module();a.pin.__defaults__=(None,)
        with method.MetadataPinSession(refs) as session:
            with self.assertRaises(ValueError):session.attach(a)
        different=MODULE_SOURCE.replace(b'sha256=sha256(raw).hexdigest()',b'sha256="different"')
        with self.assertRaises(ValueError):method.function_references(different,'fixture.py')
        for target,kind in (('pin','code'),('pin','defaults'),('pin','closure'),('load','code'),('load','closure')):
            a=module();original=(a.pin,a.load)
            with self.assertRaises(ValueError):
                with method.MetadataPinSession(refs) as session:
                    session.attach(a);wrapped=getattr(a,target)
                    if kind=='code':wrapped.__code__=wrapped.__code__.replace(co_name=wrapped.__code__.co_name+'_changed')
                    elif kind=='defaults':wrapped.__defaults__=(None,)
                    else:
                        cell=next(cell for cell in wrapped.__closure__ if cell.cell_contents is session);cell.cell_contents=object()
            self.assertIs(a.pin,original[0]);self.assertIs(a.load,original[1]);self.assertTrue(session.memo.metrics()['closed'])

    def test_08_primitives_and_primary_cleanup_order(self):
        refs={'fixture.py':method.function_references(MODULE_SOURCE,'fixture.py')}
        native_error=ValueError
        dependencies=((hashlib,'sha256'),(builtins,'len'),(builtins,'dict'),(builtins,'type'),(builtins,'bytes'),(builtins,'vars'),(builtins,'set'),(builtins,'str'),(builtins,'int'),(builtins,'globals'),(builtins,'reversed'),(builtins,'BaseException'),(builtins,'ValueError'),(builtins,'zip'),(builtins,'tuple'),(builtins,'any'),(builtins,'BaseExceptionGroup'),(method,'_SET'),(method,'builtins'),(method,'hashlib'))
        for owner,name in dependencies:
            original=getattr(owner,name);a=module();session=method.MetadataPinSession(refs);session.__enter__();session.attach(a);failure=None
            try:
                setattr(owner,name,lambda *args:0)
                try:session.__exit__(None,None,None)
                except native_error as error:failure=error
            finally:setattr(owner,name,original)
            self.assertIsInstance(failure,ValueError)
            self.assertTrue(session.memo.metrics()['closed'])
        a=module();primary=OSError('read primary')
        with self.assertRaises(OSError) as caught:
            with method.MetadataPinSession(refs) as session:
                session.attach(a);a.factory=object();raise primary
        self.assertIs(caught.exception,primary);self.assertIsInstance(primary.__cause__,ValueError)
        a=module();primary=OSError('read primary with cause');cause=LookupError('original cause');primary.__cause__=cause
        with self.assertRaises(OSError) as caught:
            with method.MetadataPinSession(refs) as session:
                session.attach(a);a.factory=object();raise primary
        self.assertIs(caught.exception,primary);self.assertIs(primary.__cause__.exceptions[0],cause)


if __name__=='__main__':unittest.main()
