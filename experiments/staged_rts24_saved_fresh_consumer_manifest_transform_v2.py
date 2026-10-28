"""Unexecuted successor: align the core's fixed helper with the consumer parent."""
from pathlib import Path

ROOT=Path(__file__).absolute().parents[1]


def replace(source,pairs):
    for before,after,count in pairs:
        assert source.count(before)==count,(before,source.count(before));source=source.replace(before,after)
    return source.encode()


def core(source):
    return replace(source,[('nfc_v11_non_authoritative','nfc_v12_non_authoritative',2),
        ('staged_rts24_saved_fresh_entry_namespace_post_return_v1.py','staged_rts24_saved_fresh_entry_namespace_consumer_v2.py',1)])


def probe(source):return replace(source,[('nfc_v11_non_authoritative','nfc_v12_non_authoritative',1)])


def parent(source):
    return replace(source,[('nfc_v11_non_authoritative','nfc_v12_non_authoritative',1),
        ('lease_v38.py','lease_v39.py',1),('probe_v36.py','probe_v37.py',1)])


def create():
    for before,after,fn in (
            ('experiments/staged_rts24_saved_fresh_pre_entry_lease_v38.py','experiments/staged_rts24_saved_fresh_pre_entry_lease_v39.py',core),
            ('tests/staged_rts24_saved_fresh_runtime_handoff_probe_v36.py','tests/staged_rts24_saved_fresh_runtime_handoff_probe_v37.py',probe),
            ('experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v35.py','experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v36.py',parent)):
        raw=fn((ROOT/before).read_text(encoding='utf8'));compile(raw,after,'exec',dont_inherit=True,optimize=0)
        path=ROOT/after
        if path.exists():assert path.read_bytes()==raw
        else:path.write_bytes(raw)


if __name__=='__main__':create()
