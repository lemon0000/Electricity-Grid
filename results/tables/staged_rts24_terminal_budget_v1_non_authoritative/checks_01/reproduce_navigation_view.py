"""Reproduce old stdlib audit with its exact historical navigation-byte view.

Only the three deliberately prepended navigation files use historical bytes.
Every historical view is reconstructed from the unchanged live header/tail and
checked against its saved original hash. No workspace bytes are changed.
"""
from hashlib import sha256
import json
from pathlib import Path
import runpy
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
original=Path.read_bytes
prior=json.loads(original(OUT/'navigation_original_bytes.json'))
tails=json.loads(original(OUT/'navigation_tail_inventory.json'))


def read_view(path):
    raw=original(path)
    try:name=path.absolute().relative_to(ROOT).as_posix()
    except ValueError:return raw
    if name not in prior:return raw
    held=tails[name];header=held['header'].encode('utf-8');body=raw[-held['body']['bytes']:]
    assert raw.split(b'\n\n',1)[0]==header
    assert dict(bytes=len(body),sha256=sha256(body).hexdigest())==held['body']
    historical=header+b'\n\n'+body
    assert dict(bytes=len(historical),sha256=sha256(historical).hexdigest())==prior[name]
    return historical


if __name__=='__main__':
    script=ROOT/'results/tables/staged_rts24_p2_package_check_v1_non_authoritative/postcheck_01/postcheck.py'
    with patch.object(Path,'read_bytes',read_view):runpy.run_path(str(script),run_name='__main__')
