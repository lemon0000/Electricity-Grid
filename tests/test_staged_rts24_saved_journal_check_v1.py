"""Connect original raw point replay to the original read-only saved P1 journal."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src import staged_rts24_saved_prefix_replay_v1 as b
from src import staged_rts24_journal_v2 as journal

ROOT = Path(__file__).resolve().parents[1]
P1 = ROOT/'results/tables/staged_rts24_native_v1_non_authoritative/p1_01'
SOURCES = tuple(sorted(set(b.SOURCES+journal.SOURCE_PATHS+('tests/test_staged_rts24_saved_journal_check_v1.py',
    'docs/plan/staged_deliverability_c_saved_journal_check_contract_v1.md'))))


@pytest.fixture(autouse=True)
def deny_execution_and_saved_writes(monkeypatch):
    import highspy
    import subprocess
    import pyomo.environ as pyo
    def denied(*a,**kw):pytest.fail('saved integration requested native/spawn/journal write/publication')
    for module,name in ((pyo,'SolverFactory'),(highspy,'Highs'),(b.point.backend,'make_model'),(b.point.backend,'call_highs'),
            (subprocess,'Popen'),(b.codec,'publish'),(journal,'publish'),(b.codec.EvidenceStore,'put')):
        monkeypatch.setattr(module,name,denied)
    for name in ('create_session','begin_step','commit_step','finish'):
        monkeypatch.setattr(journal,name,denied)


def held():
    anchor=P1.parent/'p1_execution_review_01/postcheck_03.stdout.json';raw=b.codec.read_bytes(anchor)
    assert sha256(raw).hexdigest()=='c6a25cd96c8a4a2cf293d41fe51bc7905db63fbc35253076f97e9239a4f22473'
    files=json.loads(raw)['p1_files'];assert len(files)==683 and sum(v['bytes'] for v in files.values())==2950863
    launcher=b.codec.read_bytes(P1/'launcher.json');assert b.mechanical.pin(launcher)==files['launcher.json']
    outer=json.loads(launcher);b.point._outer(outer)
    trusted=b.codec.read_bytes(P1/'trusted_binding.json');assert b.mechanical.pin(trusted)==files['trusted_binding.json']
    info=b.codec.ordinary(anchor)
    return SimpleNamespace(files=files,outer=outer,trusted=json.loads(trusted),fixture=b.core.load_fixture(),
        anchor_path=anchor,anchor_raw=raw,anchor_identity=(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns),
        anchor_directories=b.codec.directory_identity(anchor.parent))


def caller_image(c,expected,source):
    return b.codec.canonical(dict(expected=expected,trusted=c.trusted,outer=c.outer,files=c.files,
        fixture_sha=b.core.digest(c.fixture),source=source,anchor_path=str(c.anchor_path),
        anchor_pin=b.mechanical.pin(c.anchor_raw),anchor_identity=c.anchor_identity,
        anchor_directories=c.anchor_directories))


def caller_bookend(c,expected,source,image):
    raw=b.codec.read_bytes(c.anchor_path);info=b.codec.ordinary(c.anchor_path)
    assert raw==c.anchor_raw and sha256(raw).hexdigest()=='c6a25cd96c8a4a2cf293d41fe51bc7905db63fbc35253076f97e9239a4f22473'
    assert (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns)==c.anchor_identity
    assert b.codec.directory_identity(c.anchor_path.parent)==c.anchor_directories
    assert caller_image(c,expected,source)==image


def test_saved_P1_raw_prefix_and_trusted_journal_reopen_form_one_exact_chain(monkeypatch):
    c=held();phase='source_before'
    io={};packs={};audits={};rows={};prepares={};proposes={};builds={};snapshots={};imports={}
    def add(table):table[phase]=table.get(phase,0)+1
    original_read=b.codec.read_bytes;original_bounded=b.mechanical.bounded_file_bytes;original_pack=b.codec.pack
    def read(path,*a,**kw):
        key=phase+(':P1' if Path(path).is_relative_to(P1) else ':source')
        io[key]=io.get(key,0)+1;return original_read(path,*a,**kw)
    def bounded(path,*a,**kw):
        assert Path(path).is_relative_to(P1)
        key=phase+':P1';io[key]=io.get(key,0)+1;return original_bounded(path,*a,**kw)
    def pack(*a,**kw):add(packs);return original_pack(*a,**kw)
    monkeypatch.setattr(b.codec,'read_bytes',read);monkeypatch.setattr(journal,'read_bytes',read)
    monkeypatch.setattr(b.mechanical,'bounded_file_bytes',bounded)
    monkeypatch.setattr(b.codec,'pack',pack);monkeypatch.setattr(journal,'pack',pack)
    original_audit=b.policy_audit.audit_execution
    def audit(*a,**kw):
        add(audits);rows[phase]=rows.get(phase,0)+len(a[1].records);return original_audit(*a,**kw)
    monkeypatch.setattr(b.policy_audit,'audit_execution',audit);monkeypatch.setattr(journal,'audit_execution',audit)
    def count(module,name,table):
        original=getattr(module,name)
        def wrapped(*a,**kw):add(table);return original(*a,**kw)
        monkeypatch.setattr(module,name,wrapped)
    for module,name,table in ((b.causal,'prepare_hour',prepares),(b.causal,'propose_hour',proposes),
            (b.point.numeric,'compile_problem',builds),(b.point.backend,'snapshot_from_raw',snapshots),
            (b.point.numeric,'import_snapshot',imports)):count(module,name,table)
    def source_pins():return {name:b.mechanical.pin(b.codec.read_bytes(ROOT/name)) for name in SOURCES}
    source=source_pins();assert len(source)==45
    root_identity=b.codec.directory_identity(P1)
    phase='inventory_before';before=b.mechanical.inventory(P1);assert before['pins']==c.files
    raw=before['raw'];start=b.codec.parse(raw['start.json'])
    bindings=[b.codec.parse(raw[f'trusted_prefixes/prefix_{n:06d}.json']) for n in range(6)]
    expected=dict(fixture_sha=b.core.digest(c.fixture),initial_state_sha=bindings[0]['known_state_sha'],
        after_state_shas=tuple(x['known_state_sha'] for x in bindings[1:]),pins_sha=b.core.digest(start['pins']),
        registration_sha=start['registration_sha'],slots=tuple(b.codec.parse(raw['request_schedule.json'])[:21]),
        point_files={str(i):{n[len(f'points/point_{i:04d}/'):]:v for n,v in c.files.items()
            if n.startswith(f'points/point_{i:04d}/')} for i in range(1,22)})
    held_inputs=caller_image(c,expected,source)
    phase='B';prefix=b.replay_prefix(P1/'points',c.fixture,(-2,-1,0,1,2),expected,c.outer,{n:source[n] for n in b.SOURCES})
    phase='E';reopened=journal.reopen(P1/'journal',c.fixture,b.PLAN,b.CLEAN,b.METHOD,c.trusted)
    phase='join'
    assert prefix['state_sha']==reopened['state_sha']==c.trusted['known_state_sha']
    left=b.codec.pack(prefix['state'])[0];right=b.codec.pack(reopened['state'])[0];assert left==right
    nodes=[]
    for row in reopened['state'].records:
        evidence=row['prepared'].evidence
        nodes.extend(item for item in (evidence.reference,evidence.raw,evidence.lower,evidence.upper,row['actual']) if item is not None)
        assert row['actual_accepted'] is row['proposal_ledger_applied'] is True
    assert len(nodes)==len(prefix['visited_points'])==21
    node_refs=[]
    for node,report in zip(nodes,prefix['visited_points']):
        identity=b.codec.pack(node)[0]
        assert identity==report['evidence_ref'] and node.query.identity==report['query_sha']
        node_refs.append(dict(ordinal=report['ordinal'],role=node.query.request.role,evidence_ref=identity,query_sha=node.query.identity))
    assert prefix['accepted_prefix_summary']==reopened['summary']
    assert reopened['scientific_outcome']=='missing_input' and reopened['publication_outcome']=='committed' and reopened['state_certainty']=='known'
    assert reopened['final_entries']==6 and reopened['saved_objects']==130 and reopened['terminal_entry_present'] is reopened['closed_entry_present'] is True
    assert reopened['resume_permitted'] is False and reopened['state'].next_hour==3
    assert reopened['unaccepted_attempt'] is reopened['failure'] is reopened['pending_terminal_checkpoint'] is None
    assert reopened['pending_cas_objects']==reopened['unreferenced_final_cas_objects']==()
    summary=reopened['summary']
    assert summary['coverage_complete'] is False and summary['method_conditions_satisfied'] is summary['full_replay_conditions_satisfied'] is None
    assert summary['actual_accepted_hours']==5 and summary['remaining_debt']==0
    for n,binding in enumerate(bindings):
        assert binding['known_entries']==n and binding['closed'] is False and binding['failure_sha'] is None
        entry=b.codec.parse(raw['journal/genesis.json' if n==0 else f'journal/entry_{n:06d}.json'])
        assert entry['after_state_sha']==binding['known_state_sha']
        assert binding['known_head_sha']==b.mechanical.pin(raw['journal/genesis.json' if n==0 else f'journal/entry_{n:06d}.json'])['sha256']
        assert set(binding['known_cas_keys'])<=set(c.trusted['known_cas_keys'])
    phase='inventory_after';after=b.mechanical.inventory(P1)
    assert before==after and b.codec.directory_identity(P1)==root_identity
    phase='source_after';assert source_pins()==source
    phase='anchor_after';caller_bookend(c,expected,source,held_inputs)
    assert builds=={'B':42} and snapshots==imports=={'B':21}
    assert prepares==proposes=={'B':10,'E':10} and audits=={'B':16,'E':17} and rows=={'B':40,'E':45}
    assert packs=={'B':105,'E':27,'join':23}
    assert io=={'source_before:source':45,'inventory_before:P1':683,'B:source':1912,'B:P1':2152,
        'E:source':78,'E:P1':801,'inventory_after:P1':683,'source_after:source':45,'anchor_after:source':1}
    print(json.dumps(dict(oracle='saved_P1_raw_to_trusted_journal',simulated_hours=5,reconstructed_points=21,
        accepted_hours=5,final_entries=6,saved_objects=130,state_sha=reopened['state_sha'],state_cas_sha=right,
        evidence_refs=node_refs,summary=b.core.plain(summary),independent_audit=b.core.plain(reopened['independent_audit']),
        scientific_outcome=reopened['scientific_outcome'],publication_outcome=reopened['publication_outcome'],
        state_certainty=reopened['state_certainty'],io=io,typed_pack=packs,compile=builds,snapshot=snapshots,
        import_snapshot=imports,prepare=prepares,propose=proposes,execution_audit=audits,historical_rows=rows,
        source_pins=source,P1_683_files_unchanged=True,saved_P1_journal_reopened=True,new_native_calls=0,
        journal_replayed=False,scientific_evidence_adopted=False,full_fx_contract_verified=False,
        independent_139_verified=False,resource_admission=False,formal_result=False)))


@pytest.mark.parametrize('field',['genesis_sha','known_head_sha','known_state_sha','known_cas_keys','known_entries','scientific_outcome','publication_outcome','failure_sha','closed'])
def test_original_reopen_rejects_corrupted_external_trusted_binding(field):
    c=held();expected=deepcopy(c.trusted)
    if field=='known_cas_keys':expected[field]=expected[field][:-1]
    elif field=='known_entries':expected[field]=5
    elif field=='scientific_outcome':expected[field]='complete'
    elif field=='publication_outcome':expected[field]='unknown'
    elif field=='failure_sha':expected.update(failure_sha='0'*64,scientific_outcome='persistence_failure',publication_outcome='not_published')
    elif field=='closed':expected[field]=False
    else:expected[field]='0'*64
    with pytest.raises(ValueError):journal.reopen(P1/'journal',c.fixture,b.PLAN,b.CLEAN,b.METHOD,expected)
    assert all(b.mechanical.pin((P1/n).read_bytes())==v for n,v in c.files.items())


@pytest.mark.parametrize('change',['files','fixture','anchor_bytes','anchor_identity','anchor_identity_and_expectation','source'])
def test_post_reopen_caller_bookend_rejects_external_drift(tmp_path,change):
    from experiments.staged_rts24_causal_examples_v1 import analytic_fixture
    original=P1.parent/'p1_execution_review_01/postcheck_03.stdout.json'
    raw=b.codec.read_bytes(original);path=tmp_path/'external_anchor.json';path.write_bytes(raw)
    info=b.codec.ordinary(path)
    c=SimpleNamespace(anchor_path=path,anchor_raw=raw,anchor_identity=(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns),
        anchor_directories=b.codec.directory_identity(path.parent),files=json.loads(raw)['p1_files'],
        fixture=analytic_fixture(),outer={},trusted={})
    source={'test':{'sha256':'a'*64,'bytes':1}};expected={'test':'held'};image=caller_image(c,expected,source)
    if change=='files':c.files[next(iter(c.files))]['sha256']='0'*64
    elif change=='fixture':object.__setattr__(c.fixture,'source_identity','0'*64)
    elif change=='anchor_bytes':path.write_bytes(raw+b' ')
    elif change=='source':source['test']['sha256']='0'*64
    else:
        saved=tmp_path/'preserved_anchor.json'
        assert path.absolute().is_relative_to(tmp_path.absolute()) and saved.absolute().is_relative_to(tmp_path.absolute())
        path.rename(saved);path.write_bytes(raw)
        assert path.stat().st_ino!=saved.stat().st_ino
        if change=='anchor_identity_and_expectation':
            current=b.codec.ordinary(path);c.anchor_identity=(current.st_dev,current.st_ino,current.st_size,current.st_mtime_ns)
    with pytest.raises(AssertionError):caller_bookend(c,expected,source,image)
