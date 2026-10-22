"""Preserve current dirty document bytes and insert this diagnostic outcome."""
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
TEXT = ('2026-10-20 业务record复用诊断后继：同operation/同record对象复用原数值重放的DRAFT已通过22项窄单元（10.65s，outer13.172s）；'
        '但固定4/16/32h完整validator对照中每个block均更慢，32h原1.166528/1.469459s、后继4.763573/5.333247s，'
        '1056个baseline record工作量降为32次原重放仍无净收益，此点不采用且未接owner。profile_02为1passed20.50s、outer23.094s，'
        '0新normal Job/real native，原1303/1305 pins未变，失败profile_01原件保留。\n'
        '整链预算和真实168h/≤24h phase/episode terminal/reopen仍未闭合；下一步复用旧3h source/normal调用DAG，证明同operation合法减少重复prefix/parent验证的freshness边界。'
        'source/current/registry/外部heads不能跨operation缓存。证据：`results/tables/rq2_h1_business_record_replay_v1_non_authoritative/{acceptance_report.md,whole_workflow_budget_status_v2.md,development_acceptance_v1.json}`。'
        'resource/native/formal/full192及seal/official review均保持未开放。以下先前记录保留。\n\n')


def main():
    output = HERE / 'canonical_doc_updates.json'
    if output.exists() or (HERE / 'canonical_before').exists():
        raise ValueError('fresh document update roots required')
    paths = [REPO / 'docs/plan/科研项目执行步骤.md', REPO / 'docs/model_spec/blocker_register.md']
    changes = []
    for path in paths:
        before = path.read_bytes()
        offset = before.index(b'\n\n') + 2
        snapshot = HERE / 'canonical_before' / path.relative_to(REPO)
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        with snapshot.open('xb') as stream:
            stream.write(before)
        insertion = TEXT.replace('\n', '\r\n' if b'\r\n' in before else '\n').encode('utf-8')
        after = before[:offset] + insertion + before[offset:]
        path.write_bytes(after)
        assert after[:offset] + after[offset + len(insertion):] == before
        changes.append(dict(path=str(path), before_sha256=sha256(before).hexdigest(),
            before_snapshot=str(snapshot), after_sha256=sha256(after).hexdigest(),
            insertion_offset=offset, insertion_length=len(insertion),
            all_preexisting_bytes_recoverable=True))
    with output.open('x', encoding='utf-8') as stream:
        json.dump(dict(status='DRAFT_NONAUTHORITATIVE', updates=changes, formal_result=False), stream, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()
