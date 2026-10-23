"""Serializer equivalence only; no scientific runner, solve or publication."""
from collections import Counter,namedtuple
from dataclasses import dataclass,fields,is_dataclass
from enum import IntEnum
from fractions import Fraction as Q
from hashlib import sha256
import inspect
import json
from pathlib import Path
import sys

import pytest

from src import staged_rts24_development_v1 as legacy,staged_rts24_plain_v2 as candidate
from src import staged_rts24_evidence_store_v1 as codec

ROOT=Path(__file__).resolve().parents[1]
P1=ROOT/'results/tables/staged_rts24_native_v1_non_authoritative/p1_01'


def old_bytes(value):
    return json.dumps(legacy.plain(value),sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')


@pytest.fixture(autouse=True)
def deny_science_effects(monkeypatch):
    import highspy
    import pyomo.environ as pyo
    from src import staged_rts24_numeric_interface_v1 as numeric
    def denied(*a,**kw):pytest.fail('model, solver or evidence publication in serializer test')
    for module,name in [(highspy,'Highs'),(pyo,'SolverFactory'),(legacy,'build_point_model'),
                        (numeric,'compile_problem'),(codec.EvidenceStore,'put'),(codec,'publish')]:
        monkeypatch.setattr(module,name,denied)


@pytest.mark.parametrize('value',[None,True,7,-3,1.25,'\u4e2d\u6587',Q(2,3),[],(),{},
    {'q':Q(1,3),'sequence':(None,True,{'zero':0})}])
def test_supported_exact_bytes_without_fallback(value,monkeypatch):
    def denied(root):pytest.fail('supported tree fell back')
    monkeypatch.setattr(candidate,'_legacy_plain',denied)
    assert candidate.canonical_bytes(value)==old_bytes(value)
    assert candidate.digest(value)==legacy.digest(value)


@pytest.mark.parametrize('pairs',[
    [(1,'first'),('1','last'),('tail',3)], [('1','first'),('tail',3),(1,'last')],
    [(0,'zero'),(-17,'negative'),(10**100,'large')],
])
def test_integer_key_conversion_and_collision_order(pairs,monkeypatch):
    value=dict(pairs)
    monkeypatch.setattr(candidate,'_legacy_plain',lambda value:pytest.fail('exact key tree fell back'))
    assert list(candidate.plain(value).items())==list(legacy.plain(value).items())
    assert candidate.canonical_bytes(value)==old_bytes(value)
    assert candidate.digest(value)==legacy.digest(value)
    nested={'outer':value}
    cls=codec.CLASSES['Bus'];obj=object.__new__(cls)
    for field in fields(cls):object.__setattr__(obj,field.name,nested)
    assert candidate.plain(obj)==legacy.plain(obj)
    assert candidate.canonical_bytes(obj)==old_bytes(obj)


@pytest.mark.parametrize('shape',['bool','none','float','fraction','enum','int_subclass','str_subclass','raising_key'])
def test_nonexact_or_unadmitted_keys_remain_whole_root_fallback(shape,monkeypatch):
    events=[]
    class IntChild(int):
        def __str__(self):events.append('int_str');return 'child'
    class StrChild(str):
        def __str__(self):events.append('str_str');return 'child'
    class Raising:
        def __str__(self):events.append('raising_str');raise RuntimeError('key conversion failed')
    keys=dict(bool=True,none=None,float=1.25,fraction=Q(1,3),enum=IntEnum('Key',{'ONE':1}).ONE,
        int_subclass=IntChild(1),str_subclass=StrChild('s'),raising_key=Raising())
    value={keys[shape]:'value'}
    with pytest.raises(candidate._Unsupported):candidate._walk(value,0,set())
    assert events==[]
    calls=[]
    def fallback(root):calls.append(root);return legacy.plain(root)
    monkeypatch.setattr(candidate,'_legacy_plain',fallback)
    if shape=='raising_key':
        with pytest.raises(RuntimeError,match='key conversion failed'):candidate.plain(value)
        assert events==['raising_str']
    else:
        assert candidate.canonical_bytes(value)==old_bytes(value)
    assert len(calls)==1 and calls[0] is value


def test_integer_digit_limit_error_propagates_once_without_fallback(monkeypatch):
    limit=sys.get_int_max_str_digits()
    if not limit:pytest.skip('interpreter integer conversion limit disabled')
    value={10**limit:1}
    monkeypatch.setattr(candidate,'_legacy_plain',lambda root:pytest.fail('conversion failure retried'))
    for function in (legacy.plain,candidate.plain):
        with pytest.raises(ValueError,match='Exceeds the limit'):function(value)


def test_all_saved_child_reductions_have_strict_equal_bytes_and_SHA(monkeypatch):
    from src import staged_rts24_child_optimality_v1 as child
    monkeypatch.setattr(candidate,'_legacy_plain',lambda root:pytest.fail('saved reduction fell back'))
    prior=json.loads((P1.parent/'p1_execution_review_01/postcheck_03.stdout.json').read_bytes())['p1_files']
    def inventory():
        return {p.relative_to(P1).as_posix():dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
            for p in P1.rglob('*') if p.is_file() for raw in [p.read_bytes()]}
    assert inventory()==prior
    seen=0
    for point in sorted((P1/'points').iterdir()):
        request=json.loads((point/'request.json').read_bytes());result=json.loads((point/'result.json').read_bytes())
        view=codec.EvidenceReadView(codec.EvidenceStore(point/'cas'))
        query=view.get(request['query_ref']);evidence=view.get(result['evidence_ref'])
        if evidence.child_lp is not None:
            value=child.reduction(query);bounds=value['generation_bounds']
            assert bounds and all(type(k) is int for k in bounds)
            assert candidate._walk(value,0,set())==legacy.plain(value)
            assert candidate.canonical_bytes(value)==old_bytes(value)
            assert candidate.digest(value)==legacy.digest(value)==evidence.child_lp.reduction_sha
            seen+=1
        view.bookend()
    assert seen==15 and inventory()==prior


def test_known_classes_have_plain_field_access():
    assert {cls for cls,_ in candidate._KNOWN_FIELDS}==set(codec.CLASSES.values())
    for cls,_ in candidate._KNOWN_FIELDS:
        assert cls.__getattribute__ is object.__getattribute__
        for field in fields(cls):assert not hasattr(inspect.getattr_static(cls,field.name,None),'__get__')


@pytest.mark.parametrize('shape',['dataclass','dict_key','dict_subclass','list_subclass','tuple_subclass',
    'fraction_subclass','metaclass','known_class_unknown_leaf','known_class_subclass'])
def test_unknown_behavior_is_only_observed_in_whole_root_fallback(shape,monkeypatch):
    events=[]
    class Spy:
        def __deepcopy__(self,memo):events.append('deepcopy');return Q(1,3)
        def __str__(self):events.append('str');return 'spy'
    @dataclass
    class Unknown:item:object
    class Mapping(dict):
        def items(self):events.append('items');return super().items()
    class Sequence(list):
        def __iter__(self):events.append('iter');return super().__iter__()
    class TupleChild(tuple):
        def __iter__(self):events.append('tuple_iter');return super().__iter__()
    class FractionChild(Q):
        def __str__(self):events.append('fraction_str');return super().__str__()
    class Meta(type):
        def __hash__(self):events.append('meta_hash');return super().__hash__()
        def __eq__(self,other):events.append('meta_eq');return super().__eq__(other)
    class UnknownType(metaclass=Meta):pass
    known=codec.CLASSES['Bus'];bus=object.__new__(known)
    class KnownChild(known):pass
    child=object.__new__(KnownChild)
    for obj in (bus,child):
        for field in fields(known):object.__setattr__(obj,field.name,None)
    object.__setattr__(bus,fields(known)[0].name,Spy())
    roots={'dataclass':Unknown(Spy()),'dict_key':{Spy():1},'dict_subclass':Mapping(a=1),
           'list_subclass':Sequence([1]),'tuple_subclass':TupleChild([1]),'fraction_subclass':FractionChild(1,3),
           'metaclass':UnknownType(),'known_class_unknown_leaf':bus,'known_class_subclass':child}
    root=roots[shape]
    # Original isinstance(Fraction) populates ABC negative caches on first use.
    # Compare equally warm legacy calls; the candidate probe must add no event.
    legacy.plain(root)
    events.clear();expected=legacy.plain(root);expected_events=list(events);events.clear()
    calls=[]
    def fallback(value):calls.append(value);events.append('fallback');return legacy.plain(value)
    monkeypatch.setattr(candidate,'_legacy_plain',fallback)
    actual=candidate.plain(root)
    assert calls==[root] and actual==expected
    assert events==['fallback']+expected_events


@pytest.mark.parametrize('value',[namedtuple('Pair','a b')(1,Q(1,2)),
    codec.CLASSES['Bus'],IntEnum('Choice',{'ONE':1}).ONE,b'bytes',{1,2},Path('path')])
def test_unsupported_root_keeps_value_or_exception(value,monkeypatch):
    calls=[]
    def fallback(root):calls.append(root);return legacy.plain(root)
    monkeypatch.setattr(candidate,'_legacy_plain',fallback)
    def outcome(function):
        try:return ('value',function(value))
        except Exception as exc:return ('exception',type(exc))
    assert outcome(candidate.canonical_bytes)==outcome(old_bytes)
    assert calls==[value]


@pytest.mark.parametrize('depth',[63,64,65])
def test_depth_boundary_only_changes_fast_admission(depth,monkeypatch):
    value=0
    for _ in range(depth):value=[value]
    calls=[]
    def fallback(root):calls.append(root);return legacy.plain(root)
    monkeypatch.setattr(candidate,'_legacy_plain',fallback)
    assert candidate.canonical_bytes(value)==old_bytes(value)
    assert len(calls)==int(depth>64)


def test_cycle_falls_back_and_shared_alias_is_not_memoized(monkeypatch):
    cycle=[];cycle.append(cycle);calls=[]
    def fallback(root):calls.append(id(root));return legacy.plain(root)
    monkeypatch.setattr(candidate,'_legacy_plain',fallback)
    for function in (old_bytes,candidate.canonical_bytes):
        with pytest.raises(RecursionError):function(cycle)
    assert calls==[id(cycle)]
    shared={'q':Q(1,2)};value=[shared,shared]
    result=candidate.plain(value)
    assert result==legacy.plain(value) and result[0] is not result[1]
    shared['q']=Q(3,4)
    assert candidate.canonical_bytes(value)==old_bytes(value)


@pytest.mark.parametrize('value',[float('nan'),float('inf'),-float('inf')])
def test_nonfinite_json_keeps_original_failure(value):
    for function in (old_bytes,candidate.canonical_bytes):
        with pytest.raises(ValueError,match='Out of range float values'):function({'value':value})


def test_every_saved_P1_CAS_root_and_JSON_mapping_has_exact_bytes(monkeypatch):
    prior_path=P1.parent/'p1_execution_review_01/postcheck_03.stdout.json'
    assert sha256(prior_path.read_bytes()).hexdigest()=='c6a25cd96c8a4a2cf293d41fe51bc7905db63fbc35253076f97e9239a4f22473'
    expected=json.loads(prior_path.read_bytes())['p1_files']
    def inventory():
        return {p.relative_to(P1).as_posix():{'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
                for p in P1.rglob('*') if p.is_file() for raw in [p.read_bytes()]}
    assert inventory()==expected
    before_plain,before_digest=legacy.plain,legacy.digest
    def denied(root):pytest.fail('saved P1 tree fell back')
    monkeypatch.setattr(candidate,'_legacy_plain',denied)
    seen=set();counts=Counter()
    def classes(value):
        if is_dataclass(value):
            seen.add(type(value));[classes(getattr(value,f.name)) for f in fields(value)]
        elif type(value) is dict:[classes(v) for v in value.values()]
        elif type(value) in (tuple,list):[classes(v) for v in value]
    for directory in sorted(p.parent for p in P1.rglob('objects') if p.is_dir()):
        view=codec.EvidenceReadView(codec.EvidenceStore(directory))
        for name in sorted(view.before):
            assert name.endswith('.json') and not name.endswith('.pending')
            value=view.get(name.removesuffix('.json'));classes(value)
            assert candidate.canonical_bytes(value)==old_bytes(value)
            assert candidate.digest(value)==legacy.digest(value)
            counts['typed_CAS_roots']+=1
        view.bookend()
    for p in P1.rglob('*.json'):
        value=json.loads(p.read_bytes())
        if type(value) is dict:
            assert candidate.canonical_bytes(value)==old_bytes(value)
            assert candidate.digest(value)==legacy.digest(value)
            counts['JSON_mapping_roots']+=1
    assert counts['typed_CAS_roots']==403
    assert seen==set(codec.CLASSES.values()), sorted(cls.__name__ for cls in set(codec.CLASSES.values())-seen)
    assert legacy.plain is before_plain and legacy.digest is before_digest
    assert inventory()==expected
    print(json.dumps({'serializer_equivalence_counts':dict(counts),'known_classes_seen':len(seen)},sort_keys=True))
