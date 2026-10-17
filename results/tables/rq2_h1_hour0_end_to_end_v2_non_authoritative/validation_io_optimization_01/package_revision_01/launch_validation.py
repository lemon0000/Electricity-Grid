"""Execute only the exact development package bytes named below."""
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
MANIFEST_SHA='71da10f21b2b12ec672e8e3eaf6f391ed24773125ce8c7cc499b62b99e88b1a9'
raw=(HERE/'package_manifest_v1.json').read_bytes()
if sha256(raw).hexdigest()!=MANIFEST_SHA:raise ValueError('fixed package manifest differs')
manifest=json.loads(raw);sources={}
for name,pin in manifest['files_sha256'].items():
    if Path(name).name!=name:raise ValueError('flat exact package members required')
    member=(HERE/name).read_bytes()
    if sha256(member).hexdigest()!=pin:raise ValueError('fixed package member differs: '+name)
    sources[name]=member
entry=HERE/'validation_entry.py'
scope=dict(__name__='__main__',__file__=str(entry),_pinned_sources=sources,
    _manifest_sha256=MANIFEST_SHA,_launcher_sha256=sha256(Path(__file__).read_bytes()).hexdigest())
exec(compile(sources['validation_entry.py'],str(entry),'exec'),scope)
