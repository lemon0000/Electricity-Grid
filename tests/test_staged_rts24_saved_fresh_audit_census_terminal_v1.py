"""Terminal schedule supplement and new-root codec; prior 14 nodes are reused."""
import ast
import base64
import copy
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tokenize
import unittest
import zlib

ROOT=Path(__file__).absolute().parents[1]
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
fixture=load(ROOT/'tests/test_staged_rts24_saved_fresh_audit_census_v4.py','_terminal_fixture')
parent=load(ROOT/'experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v16.py','_terminal_parent')

class TerminalTests(unittest.TestCase):
    def frames(self):
        module,sink=fixture.helper();guard,runtime,trace,primary=fixture.guard_for(module);module._census_start(runtime);module.sys.audit('open','D:/allowed','r',0)
        raw=sink.getvalue();return raw,parent.parse_diagnostic_stderr(raw)['census_frames']
    def test_01_terminal_schedule_negative_and_positive(self):
        raw,frames=self.frames()
        for kind,count in (('prefix_complete',64),('import_return_before64',8)):
            terminal=copy.deepcopy(frames[-1]);terminal.update(seq=3,reason=kind,entered=count,passed=count,observed=count,active=False)
            with self.assertRaises(AssertionError):parent.parse_diagnostic_stderr(raw+parent.canonical(('census',terminal))+b'\n')
        terminal=copy.deepcopy(frames[-1]);terminal.update(seq=3,reason='import_return_before64',entered=7,passed=7,observed=7,active=False)
        parsed=parent.parse_diagnostic_stderr(raw+parent.canonical(('census',terminal))+b'\n')
        self.assertEqual(parsed['census_frames'][-1]['passed'],7)
    def test_02_full_prefix_and_partial(self):
        module,sink=fixture.helper();guard,runtime,trace,primary=fixture.guard_for(module);module._census_start(runtime)
        with self.assertRaises(module.AuditCensusStop):
            for _ in range(64):module.sys.audit('open','D:/allowed','r',0)
        raw=sink.getvalue();frames=parent.parse_diagnostic_stderr(raw)['census_frames']
        self.assertEqual(frames[-1]['reason'],'prefix_complete');self.assertEqual([f['passed'] for f in frames],[0,1,8,16,24,32,40,48,56,64])
        partial=parent.parse_diagnostic_stderr(raw[:raw.rfind(b'\n',0,-1)+1]+b'["census",')
        self.assertEqual(partial['census_frames'][-1]['passed'],56)
        self.assertIn(b'["census",',base64.b64decode(partial['non_stage_raw_base64']))
    def test_03_prior_evidence_and_migration(self):
        old=ROOT/'results/tables/staged_rts24_saved_fresh_aoc_v4_non_authoritative'
        raw=(old/'unittest.exit.json').read_bytes();self.assertEqual((len(raw),sha256(raw).hexdigest()),(3518,'b4dd51877c6449933fe6346241a8ba30bc1e3c04b6790dffb1c27e9746984b81'))
        record=json.loads(raw);self.assertTrue(record['accepted'])
        self.assertEqual(json.loads((old/'unittest_report.json').read_bytes()),dict(accepted=True,tests_run=14,failures=0,errors=0,skipped=0))
        for path,value in record['artifact_pins'].items():self.assertEqual(dict(bytes=Path(path).stat().st_size,sha256=sha256(Path(path).read_bytes()).hexdigest()),value)
        for new,previous in ((parent.CORE,ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v18.py'),(parent.PROBE,ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v15.py')):
            expected=previous.read_bytes().replace(b'aoc_v4_non_authoritative',b'aoc_v5_non_authoritative')
            self.assertEqual(new.read_bytes(),expected)
    def test_04_actual_codec_manifest_and_helper(self):
        code=parent.transport();marker=b'\nimport os as _bootstrap_os\n';self.assertEqual(code.count(marker),1);prefix=code.partition(marker)[0]
        node=next(n for n in ast.walk(ast.parse(code)) if type(n) is ast.Call and type(n.func) is ast.Attribute and n.func.attr=='b85decode')
        decoder=zlib.decompressobj(zdict=prefix);payload=decoder.decompress(base64.b85decode(node.args[0].value),131073)
        self.assertTrue(decoder.eof);self.assertFalse(decoder.unused_data or decoder.unconsumed_tail);self.assertLessEqual(len(payload),131072)
        original=parent.CORE.read_bytes()+b'\n'+parent.PROBE.read_bytes();expected=b'import builtins\n'+original.split(b'\nimport builtins\n',1)[1];lines=expected.decode().splitlines(keepends=True)
        for token in tokenize.tokenize(io.BytesIO(expected).readline):
            if token.type==tokenize.COMMENT:
                line,col=token.start;lines[line-1]=lines[line-1][:col]+' '*(token.end[1]-col)+lines[line-1][token.end[1]:]
        self.assertEqual(payload,''.join(lines).encode());self.assertEqual(compile(payload,'<pre_entry_payload>','exec'),compile(expected,'<pre_entry_payload>','exec'))
        argv=[str(parent.EXE),'-P','-B','-s','-S','-c',code.decode(),'--pre-entry-lease',str(parent.OUT/'probe_import_discovery.plan.json'),'0'*64]
        self.assertLessEqual(len(subprocess.list2cmdline(argv).encode('utf-16-le'))//2,30000)
        plan=parent.manifest('discovery',code);self.assertEqual(plan['import_helper']['path'],str(fixture.BS))

if __name__=='__main__':unittest.main()
