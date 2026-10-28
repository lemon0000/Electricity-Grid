"""Bounded UTF-16 transport of exact XZ bytes; native admission remains separate."""
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


def encode14(raw):
    assert type(raw) is bytes and len(raw)<=26214
    result=[];acc=bits=0
    for value in raw:
        acc=(acc<<8)|value;bits+=8
        while bits>=14:
            bits-=14;result.append(chr(0x4e00+((acc>>bits)&16383)))
        acc&=(1<<bits)-1
    if bits:result.append(chr(0x4e00+(acc<<(14-bits))))
    return ''.join(result)


def unpack14(encoded,size):
    if type(encoded) is not str or type(size) is not int or not 0<=size<=26214 or len(encoded)!=(size*8+13)//14:
        raise ValueError('bounded canonical transport length required')
    out=bytearray();acc=bits=0
    for char in encoded:
        value=ord(char)-0x4e00
        if not 0<=value<16384:raise ValueError('fixed BMP transport alphabet required')
        acc=(acc<<14)|value;bits+=14
        while bits>=8 and len(out)<size:
            bits-=8;out.append((acc>>bits)&255)
        acc&=(1<<bits)-1
    if len(out)!=size or acc!=0:raise ValueError('canonical zero padding required')
    return bytes(out)


def decode(encoded,size,expected):
    packed=unpack14(encoded,size)
    decoder=lzma.LZMADecompressor(format=lzma.FORMAT_XZ,memlimit=67108864)
    raw=decoder.decompress(packed,max_length=131073)
    assert type(raw) is bytes and len(raw)<=131072 and decoder.eof is True and decoder.unused_data==b''
    assert decoder.check==lzma.CHECK_CRC64 and (len(raw),sha256(raw).hexdigest())==expected
    return raw


def build(core,probe,minify_prefix):
    before,raw=payload(core,probe);prefix=minify_prefix(before)
    assert len(raw)<=131072 and lzma.is_check_supported(lzma.CHECK_CRC64)
    packed=lzma.compress(raw,format=lzma.FORMAT_XZ,check=lzma.CHECK_CRC64,preset=6)
    encoded=encode14(packed)
    expected=len(raw),sha256(raw).hexdigest();assert decode(encoded,len(packed),expected)==raw
    beginning=(b'\nimport os as _bootstrap_os\n'
        b'if _bootstrap_os.__spec__.origin!="frozen": raise RuntimeError("OS")\n'
        b'_DLL_DIRECTORY=_bootstrap_os.add_dll_directory("D:/Miniconda3/envs/compute/Library/bin")\n'
        b'_DLL_DIRECTORY_CLOSE_STATE=[False]\n_lp=None\n')
    import inspect
    decoder_source=inspect.getsource(unpack14).replace('def unpack14(', 'def _u14(').encode('ascii')
    body=(b'import zlib as _transport_zlib\nimport base64 as _transport_base64\nimport lzma as _xz\n'
        b'from hashlib import sha256 as _hs\n'
        b'_ux=_xz.LZMADecompressor(format=_xz.FORMAT_XZ,memlimit=67108864)\n'
        +decoder_source
        +b'_packed14=_u14('+repr(encoded).encode('utf8')+b','+str(len(packed)).encode('ascii')+b')\n'
        +b'_PAYLOAD_RAW=_ux.decompress(_packed14,max_length=131073)\n'
        +b'if type(_PAYLOAD_RAW) is not bytes or len(_PAYLOAD_RAW)>131072 or _ux.eof is not True or _ux.unused_data or _ux.check!=_xz.CHECK_CRC64: raise RuntimeError("cap")\n'
        +b'if (len(_PAYLOAD_RAW),_hs(_PAYLOAD_RAW).hexdigest())!='+repr(expected).encode()+b': raise RuntimeError("payload")\n'
        +b'del _ux,_xz,_hs,_u14,_packed14\n'
        +b'_PAYLOAD_CODE=compile(_PAYLOAD_RAW,"<pre_entry_payload>","exec",dont_inherit=True,optimize=0)\n'
        +b'exec(_PAYLOAD_CODE,globals())\n')
    ending=(b'except BaseException as _le:\n _lp=_le\n raise\n'
        b'finally:\n try:\n  for _ln in ("_ux","_xz","_hs","_u14","_packed14"): globals().pop(_ln,None)\n'
        b'  if not _DLL_DIRECTORY_CLOSE_STATE[0]:\n   _DLL_DIRECTORY_CLOSE_STATE[0]=True\n'
        b'   try: _DLL_DIRECTORY.close()\n   except BaseException as _lc:\n'
        b'    if _lp is not None: raise _lp from _lc\n    raise\n'
        b' finally:\n  globals().pop("_lp",None)\n  globals().pop("_ln",None)\n')
    result=prefix+beginning+b'try:\n'+b''.join(b' '+line+b'\n' for line in body.splitlines())+ending
    assert result.count(b'\nimport os as _bootstrap_os\n')==1
    return result
