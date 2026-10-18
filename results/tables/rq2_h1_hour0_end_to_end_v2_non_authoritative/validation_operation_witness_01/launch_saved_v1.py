"""Compile the fixed verified monitor bytes, without importing a cached module."""
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
mode,label,expected=sys.argv[1:]
manifest=(HERE/'diagnostic_source_manifest_v1.json').read_bytes()
if sha256(manifest).hexdigest()!=expected:raise ValueError('explicit diagnostic manifest SHA differs')
members=json.loads(manifest)['files_sha256']
for name,pin in members.items():
    if Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('relative diagnostic member required')
    if sha256((REPO/name).read_bytes()).hexdigest()!=pin:raise ValueError('diagnostic member differs: '+name)
path=HERE/'run_saved_bounded_v1.py';raw=path.read_bytes()
if sha256(raw).hexdigest()!=members[path.relative_to(REPO).as_posix()]:raise ValueError('monitor byte pin differs')
sys.argv=[str(path),mode,label,expected]
exec(compile(raw,str(path),'exec'),dict(__name__='__main__',__file__=str(path)))
