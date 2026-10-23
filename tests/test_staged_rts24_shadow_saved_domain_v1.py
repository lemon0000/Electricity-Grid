"""One saved-query regression for the strict shadow's observed domain gap."""
from hashlib import sha256
import json
from pathlib import Path

import pytest

from src import staged_rts24_development_v1 as legacy
from src import staged_rts24_evidence_store_v1 as codec
from src import staged_rts24_child_optimality_v1 as child
from src import staged_rts24_plain_v1 as candidate

ROOT=Path(__file__).resolve().parents[1]
P1=ROOT/'results/tables/staged_rts24_native_v1_non_authoritative/p1_01'


def test_saved_child_reduction_exceeds_strict_domain_and_keeps_public_fallback(monkeypatch):
    def inventory():
        return {p.relative_to(P1).as_posix():dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
            for p in P1.rglob('*') if p.is_file() for raw in [p.read_bytes()]}
    expected=json.loads((P1.parent/'p1_execution_review_01/postcheck_03.stdout.json').read_bytes())['p1_files']
    assert inventory()==expected
    point=P1/'points/point_0002'
    request=json.loads((point/'request.json').read_bytes());result=json.loads((point/'result.json').read_bytes())
    assert request['hour']==-2 and request['role']=='recovery_min_meter'
    view=codec.EvidenceReadView(codec.EvidenceStore(point/'cas'))
    query=view.get(request['query_ref']);evidence=view.get(result['evidence_ref'])
    reduced=child.reduction(query)
    bounds=reduced['generation_bounds']
    assert bounds and len(bounds)==len(query.request.data.generators) and all(type(k) is int for k in bounds)
    assert legacy.digest(reduced)==evidence.child_lp.reduction_sha
    # The saved query root supports the strict path; its temporary reduction does not.
    assert candidate._walk(query,0,set())==legacy.plain(query)
    with pytest.raises(candidate._Unsupported):candidate._walk(reduced,0,set())
    calls=[]
    def fallback(value):calls.append(value);return legacy.plain(value)
    monkeypatch.setattr(candidate,'_legacy_plain',fallback)
    old=json.dumps(legacy.plain(reduced),sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
    assert candidate.canonical_bytes(reduced)==old
    assert len(calls)==1 and calls[0] is reduced
    view.bookend()
    assert inventory()==expected
