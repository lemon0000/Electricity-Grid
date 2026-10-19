"""Execute only the exact development package bytes named below."""
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
MANIFEST_SHA='798c51f2aa4c372c72721971e13cba4a3848cf71e70f8f806c7f8292a7c33192'
raw=(HERE/'package_manifest_v1.json').read_bytes()
if sha256(raw).hexdigest()!=MANIFEST_SHA:raise ValueError('fixed package manifest differs')
manifest=json.loads(raw);sources={}
for name,pin in manifest['files_sha256'].items():
    if Path(name).name!=name:raise ValueError('flat exact package members required')
    member=(HERE/name).read_bytes()
    if sha256(member).hexdigest()!=pin:raise ValueError('fixed package member differs: '+name)
    sources[name]=member
entry=HERE/'validation_entry.py';launcher=Path(__file__).read_bytes()
scope=dict(__name__='__main__',__file__=str(entry),_pinned_sources=sources,
    _bootstrap_sources={'launch_validation.py':launcher,'package_manifest_v1.json':raw},
    _manifest_sha256=MANIFEST_SHA,_launcher_sha256=sha256(launcher).hexdigest())
exec(compile(sources['validation_entry.py'],str(entry),'exec'),scope)
