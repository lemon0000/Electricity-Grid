"""Exact-source XZ bootstrap transport; integrity is conditional on registered inputs."""
import ast
import base64
from hashlib import sha256
import io
import lzma
import tokenize
import sys

if sys.flags.optimize!=0:raise RuntimeError('unoptimized transport checks required')


def payload(core,probe):
    original=core.read_bytes()+b'\n'+probe.read_bytes();marker=b'\nimport builtins\n'
    assert original.count(marker)==1;prefix,tail=original.split(marker,1);source=b'import builtins\n'+tail
    lines=source.decode('utf8').splitlines(keepends=True)
    for token in tokenize.tokenize(io.BytesIO(source).readline):
        if token.type==tokenize.COMMENT:
            row,col=token.start;lines[row-1]=lines[row-1][:col]+' '*(token.end[1]-col)+lines[row-1][token.end[1]:]
    raw=''.join(lines).encode('utf8')
    assert ast.dump(ast.parse(raw),include_attributes=True)==ast.dump(ast.parse(source),include_attributes=True)
    assert compile(raw,'<pre_entry_payload>','exec',dont_inherit=True,optimize=0)==compile(source,'<pre_entry_payload>','exec',dont_inherit=True,optimize=0)
    assert ast.dump(ast.parse(prefix+b'\n'+raw))==ast.dump(ast.parse(original))
    return prefix,raw


def decode(packed,expected):
    assert type(packed) is bytes and len(packed)<=32768
    decoder=lzma.LZMADecompressor(format=lzma.FORMAT_XZ,memlimit=67108864)
    raw=decoder.decompress(base64.b85decode(packed),max_length=131073)
    assert type(raw) is bytes and len(raw)<=131072 and decoder.eof is True and decoder.unused_data==b''
    assert decoder.check==lzma.CHECK_CRC64 and (len(raw),sha256(raw).hexdigest())==expected
    return raw


def build(core,probe,minify_prefix):
    before,raw=payload(core,probe);prefix=minify_prefix(before)
    assert len(raw)<=131072 and lzma.is_check_supported(lzma.CHECK_CRC64)
    packed=base64.b85encode(lzma.compress(raw,format=lzma.FORMAT_XZ,check=lzma.CHECK_CRC64,preset=6))
    expected=len(raw),sha256(raw).hexdigest();assert decode(packed,expected)==raw
    beginning=(b'\nimport os as _bootstrap_os\n'
        b'if _bootstrap_os.__spec__.origin!="frozen": raise RuntimeError("OS")\n'
        b'_DLL_DIRECTORY=_bootstrap_os.add_dll_directory("D:/Miniconda3/envs/compute/Library/bin")\n'
        b'_DLL_DIRECTORY_CLOSE_STATE=[False]\n_lp=None\n')
    body=(b'import zlib as _transport_zlib\nimport base64 as _transport_base64\nimport lzma as _xz\n'
        b'from hashlib import sha256 as _hs\n'
        b'_ux=_xz.LZMADecompressor(format=_xz.FORMAT_XZ,memlimit=67108864)\n'
        +b'_PAYLOAD_RAW=_ux.decompress(_transport_base64.b85decode('+repr(packed).encode()+b'),max_length=131073)\n'
        +b'if type(_PAYLOAD_RAW) is not bytes or len(_PAYLOAD_RAW)>131072 or _ux.eof is not True or _ux.unused_data or _ux.check!=_xz.CHECK_CRC64: raise RuntimeError("cap")\n'
        +b'if (len(_PAYLOAD_RAW),_hs(_PAYLOAD_RAW).hexdigest())!='+repr(expected).encode()+b': raise RuntimeError("payload")\n'
        +b'del _ux,_xz,_hs\n'
        +b'_PAYLOAD_CODE=compile(_PAYLOAD_RAW,"<pre_entry_payload>","exec",dont_inherit=True,optimize=0)\n'
        +b'exec(_PAYLOAD_CODE,globals())\n')
    ending=(b'except BaseException as _le:\n _lp=_le\n raise\n'
        b'finally:\n try:\n  for _ln in ("_ux","_xz","_hs"): globals().pop(_ln,None)\n'
        b'  if not _DLL_DIRECTORY_CLOSE_STATE[0]:\n   _DLL_DIRECTORY_CLOSE_STATE[0]=True\n'
        b'   try: _DLL_DIRECTORY.close()\n   except BaseException as _lc:\n'
        b'    if _lp is not None: raise _lp from _lc\n    raise\n'
        b' finally:\n  globals().pop("_lp",None)\n  globals().pop("_ln",None)\n')
    result=prefix+beginning+b'try:\n'+b''.join(b' '+line+b'\n' for line in body.splitlines())+ending
    assert result.count(b'\nimport os as _bootstrap_os\n')==1
    return result
