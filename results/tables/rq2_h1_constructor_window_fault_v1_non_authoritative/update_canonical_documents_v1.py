"""Insert this development checkpoint while preserving both prior dirty files."""
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
TEXT = '''2026-10-21 constructor窗口依赖修复：实际H1 Reader故障注入曾出现旧实现拒绝、候选返回，已补normal模型依赖及source SHA/runtime版本的前后检查，并由source/辅助validator强制bookend metric。171项窄回归通过2.61s（outer4.297s）；alias窗口复验两边均拒绝，外部metadata.distribution模拟numpy版本变化也均拒绝，后者实际由候选post snapshot拒绝。两类故障仅关闭指定窗口，未覆盖完整文件/runtime闭包或同值ABA；所观察Reader/ReadView均正常关闭，不能推广到任意失败。
修复后H3/M5双Reader完整batch83.976012s（outer89.781s），3小时保存科学身份绑定重构与21项辅助拒绝通过；H1固定old→new各一次完整batch56.969790s→28.378482s，科学摘要一致。新增model metric负例来自171项unit；H3/H1为正例。全部attempt运行时/after pins未变，465case/444owned SHA未变，0新Job/native；后续设计文字由tested snapshots解析。H3仍复用原join/projection、saved manifest resolver及单字段stand-in，非独立科学oracle，也未直接读取旧raw science。
整链预算仍未闭合：旧owner未采纳候选，T192源层仍597520次Job重放；候选条件值298760仍属算术，另增加每Reader两次模型依赖snapshot，不能据局部时间外推192h。至少576个operational events、业务历史校验长度下界28311936及完整wall/RSS/storage/失败收尾资源仍待处理。正式准备16门全部OPEN，真实168h/≤24h phase/episode terminal→checkpoint→close→fresh-process replay未验收；formal/native/resource/full192/seal/official继续false。证据：`results/tables/rq2_h1_constructor_window_fault_v1_non_authoritative/{acceptance_report.md,whole_workflow_budget_v4.json,formal_preparation_state_v4.json,development_acceptance_v1.json}`。以下先前记录保留。

'''


def pin(raw):
    return sha256(raw).hexdigest()


updates = []
for relative in ('docs/plan/科研项目执行步骤.md', 'docs/model_spec/blocker_register.md'):
    path = REPO / relative
    raw = path.read_bytes()
    marker = b'\r\n\r\n' if b'\r\n' in raw else b'\n\n'
    offset = raw.index(marker)+len(marker)
    newline = '\r\n' if marker == b'\r\n\r\n' else '\n'
    addition = TEXT.replace('\n', newline).encode('utf-8')
    assert b'constructor' not in raw[:offset]
    before = HERE / 'canonical_before' / relative
    before.parent.mkdir(parents=True, exist_ok=True)
    with before.open('xb') as stream:
        stream.write(raw)
    changed = raw[:offset]+addition+raw[offset:]
    assert changed[:offset]+changed[offset+len(addition):] == raw
    path.write_bytes(changed)
    assert path.read_bytes() == changed
    updates.append(dict(path=str(path), before_snapshot=str(before), before_sha256=pin(raw),
        after_sha256=pin(changed), insertion_offset=offset, insertion_length=len(addition)))
result = dict(status='DRAFT_NONAUTHORITATIVE', updates=updates,
    preserved_scope='exact prior bytes of these two already-dirty canonical progress documents',
    whole_dirty_worktree_preservation_claimed=False, formal_result=False)
with (HERE / 'canonical_doc_updates.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps(dict(updated_documents=len(updates), exact_prior_bytes_preserved=True)))
