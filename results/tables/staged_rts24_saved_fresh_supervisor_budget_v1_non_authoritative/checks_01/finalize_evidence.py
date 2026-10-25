"""Bind design evidence, keep old navigation bodies, and record bound Python bytes."""
import json
from pathlib import Path
import re
import sys
from capture_static import ROOT, OUT, pin


def save(name, value): (OUT/name).write_bytes((json.dumps(value, sort_keys=True, indent=2)+'\n').encode())


before = json.loads((OUT/'navigation_before.json').read_bytes())
handoff = 'continuation_handoff_20261025_saved_fresh_supervisor_budget.md'
for name, expected in before.items():
    path = ROOT/name; raw = path.read_bytes()
    assert pin(raw[-expected['body']['bytes']:]) == expected['body']
    target = handoff if Path(name).parent.as_posix() == 'docs/plan' else '../plan/'+handoff
    prefix = ('2026-10-25 saved supervisor事前设计：见[最新交接]('+target+')。源码不变的条件账本显示P1读12736/13419超过12500、source/exe/anchor下界6513超过6500、完整名义stage至少185s超过180s；须先做依赖复用/失效证明和逐边deadline。wire component oracle已核新slot提案，guard/最大四record和实际actor未证明；真实F/科学采用/资源/正式门禁保持关闭。\n\n').encode()
    header, separator, body = raw.partition(b'\n\n')
    if prefix not in raw: path.write_bytes(header+separator+prefix+body)

owner = ROOT/'results/tables/staged_rts24_saved_fresh_owner_v1_non_authoritative/checks_01'
line = next(line for line in (owner/'owner_bounded_01.stdout.log').read_text(encoding='utf-8').splitlines()
    if line.startswith('SAVED_OWNER_UNIT '))
executable = json.loads(line.removeprefix('SAVED_OWNER_UNIT '))['record']['startup']['executable']
path = Path(executable['path']); info = path.stat()
assert Path(sys.executable).absolute() == path and sys.version == executable['python']
assert pin(path.read_bytes()) == executable['pin']
assert [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns] == executable['identity']
save('runtime_pin.json', dict(executable=executable, independent_runtime_closure_verified=False,
    actual_saved_F_execution=False))

e_root = ROOT/'results/tables/staged_rts24_saved_journal_check_v1_non_authoritative/checks_01'
observed = next(json.loads(line) for line in (e_root/'chain_04.stdout.log').read_text(encoding='utf-8').splitlines()
    if line.startswith('{'))
save('E_observed_baseline.json', dict(authority='DRAFT_NONAUTHORITATIVE', observed_io=observed['io'],
    observed_compile=observed['compile'], observed_snapshot=observed['snapshot'],
    observed_import=observed['import_snapshot'], replayed_now=False,
    provenance_pins={p.relative_to(ROOT).as_posix():pin(p.read_bytes())
        for p in (e_root/'chain_04.stdout.log', e_root/'chain_04.exit.json')}))
documents = [ROOT/'docs/plan'/handoff,
    ROOT/'docs/plan/staged_deliverability_c_saved_fresh_supervisor_scope_budget_v1.md', OUT.parent/'validation_report.md']
for path in documents:
    for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
        if '://' not in target: assert (path.parent/target.split('#')[0]).resolve().exists(), (path, target)
save('document_checks.json', dict(authority='DRAFT_NONAUTHORITATIVE', links_resolve=True,
    document_pins={p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in documents}))
save('support_pins.json', {p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in OUT.rglob('*')
    if p.is_file() and p.name != 'support_pins.json'})
assert not (ROOT/'results/tables/staged_rts24_saved_fresh_adoption_v1_non_authoritative').exists()
print(json.dumps(dict(document_links_resolve=True, Python_bytes_identity_unchanged=True, actual_saved_F_execution=False)))
