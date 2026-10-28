"""Bounded byte/AST checks for the new transport; never launch the bootstrap."""
import ast
from hashlib import sha256
import importlib.util
import inspect
import lzma
from pathlib import Path
from random import Random
import tempfile
import unittest

ROOT=Path(__file__).absolute().parents[1]
path=ROOT/'experiments/staged_rts24_saved_fresh_utf16_transport_v1.py'
spec=importlib.util.spec_from_file_location('_unicode_transport_unit',path)
transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)


class Utf16TransportTests(unittest.TestCase):
    def test_01_exact_round_trip_across_bit_and_max_boundaries(self):
        random=Random(20261029)
        for size in (*range(80),127,128,255,1024,26214):
            raw=random.randbytes(size);encoded=transport.encode14(raw)
            self.assertEqual(len(encoded),(8*size+13)//14)
            self.assertTrue(all(0x4e00<=ord(c)<=0x8dff for c in encoded))
            self.assertEqual(transport.unpack14(encoded,size),raw)
            self.assertEqual(len(encoded.encode('utf-16-le'))//2,len(encoded))

    def test_02_noncanonical_padding_alphabet_length_and_caps_reject(self):
        good=transport.encode14(b'\x01')
        for encoded,size in ((good,True),(good,-1),(good,26215),(good+'\u4e00',1),('x',1),
                (chr(ord(good)+1),1),('',1)):
            with self.subTest(size=size,encoded=encoded),self.assertRaises(ValueError):transport.unpack14(encoded,size)
        with self.assertRaises(AssertionError):transport.encode14(bytes(26215))

    def test_03_xz_bytes_hash_crc_and_trailing_data_are_checked(self):
        raw=b'exact held source\n'*100
        packed=lzma.compress(raw,format=lzma.FORMAT_XZ,check=lzma.CHECK_CRC64,preset=6)
        expected=(len(raw),sha256(raw).hexdigest())
        self.assertEqual(transport.decode(transport.encode14(packed),len(packed),expected),raw)
        with self.assertRaises(AssertionError):transport.decode(transport.encode14(packed),len(packed),(len(raw),'0'*64))
        extra=packed+b'x'
        with self.assertRaises(AssertionError):transport.decode(transport.encode14(extra),len(extra),expected)

    def test_04_emitted_decoder_matches_the_tested_source_ast(self):
        with tempfile.TemporaryDirectory(prefix='transport_source_') as folder:
            core=Path(folder)/'core.py';probe=Path(folder)/'probe.py'
            core.write_bytes(b'import sys\nimport builtins\nVALUE=1\n');probe.write_bytes(b'VALUE2=2\n')
            script=transport.build(core,probe,lambda prefix:prefix)
            tree=ast.parse(script)
            emitted=next(node for node in ast.walk(tree) if type(node) is ast.FunctionDef and node.name=='_u14')
            expected=ast.parse(inspect.getsource(transport.unpack14)).body[0];expected.name='_u14'
            self.assertEqual(ast.dump(expected),ast.dump(emitted))
            namespace={};exec(compile(ast.Module(body=[emitted],type_ignores=[]),'<isolated transport decoder>','exec'),namespace)
            call=next(node.value for node in ast.walk(tree) if type(node) is ast.Assign
                and any(type(target) is ast.Name and target.id=='_packed14' for target in node.targets))
            encoded,size=[ast.literal_eval(arg) for arg in call.args]
            packed=namespace['_u14'](encoded,size)
            self.assertEqual(lzma.decompress(packed),transport.payload(core,probe)[1])

    def test_05_source_payload_transform_is_unchanged(self):
        old=ast.parse((ROOT/'experiments/staged_rts24_saved_fresh_xz_transport_v1.py').read_bytes())
        new=ast.parse(path.read_bytes())
        def payload(tree):return next(node for node in tree.body if type(node) is ast.FunctionDef and node.name=='payload')
        self.assertEqual(ast.dump(payload(old)),ast.dump(payload(new)))
