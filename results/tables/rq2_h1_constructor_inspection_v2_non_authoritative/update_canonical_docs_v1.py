"""Insert current draft evidence, preserving all earlier dirty document bytes."""
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
TEXT = ('2026-10-21 constructor inspection后继：新增独立capture/historical/source v2及detached validator，旧owner未接入。'
        '110项窄单元通过3.03s（outer6.390s）；保存3h successor完整双Reader科学身份绑定重构通过，batch93.285154s/outer97.985s，21辅助拒绝通过。'
        'H1固定old→new各一次完整batch为57.131095s→27.815387s；只说明本次保存前缀观测，不外推192h或生产。'
        '两成功诊断各1308pins未变、465case/444owned SHA一致、观察PID退出，0新Job/native。无static identity memo，保留saved manifest resolver seam且未重审真实manifest源；H3不是独立科学实现或直接旧raw science bytes对照。\n'
        '初始comparison_01在首old完整call前因120s no-progress停止（outer120.328s/exit15），无科学/性能结论；失败原件及独立after SHA核验保留。'
        '当前真实source文件/metadata/依赖故障等价、适用动态闭包、owner接线、完整168h/≤24h预算和episode terminal/reopen仍OPEN。'
        '正式准备草稿对账保留1900cell、1856个CFE相关cell解析反例/44unknown及全部network-only unknown；8020-node逻辑图没有runtime任务或solver复用，不据此折扣资源。'
        'formal/native/resource/full192/seal/official各门仍false。证据：`results/tables/rq2_h1_constructor_inspection_v2_non_authoritative/{acceptance_report.md,whole_workflow_budget_status_v3.md,development_acceptance_v1.json,formal_preparation_state_v3.json}`。以下先前记录保留。\n\n')


def main():
    changes = []
    if (HERE / 'canonical_before').exists() or (HERE / 'canonical_doc_updates.json').exists():
        raise ValueError('fresh preservation paths required')
    for path in (REPO / 'docs/plan/科研项目执行步骤.md', REPO / 'docs/model_spec/blocker_register.md'):
        raw = path.read_bytes()
        offset = raw.index(b'\n\n')+2
        snapshot = HERE / 'canonical_before' / path.relative_to(REPO)
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        with snapshot.open('xb') as stream:
            stream.write(raw)
        addition = TEXT.replace('\n', '\r\n' if b'\r\n' in raw else '\n').encode('utf-8')
        updated = raw[:offset]+addition+raw[offset:]
        assert updated[:offset]+updated[offset+len(addition):] == raw
        path.write_bytes(updated)
        changes.append(dict(path=str(path), before_sha256=sha256(raw).hexdigest(),
            before_snapshot=str(snapshot), after_sha256=sha256(updated).hexdigest(),
            insertion_offset=offset, insertion_length=len(addition), all_prior_bytes_recoverable=True))
    with (HERE / 'canonical_doc_updates.json').open('x', encoding='utf-8') as stream:
        json.dump(dict(status='DRAFT_NONAUTHORITATIVE', updates=changes, formal_result=False), stream, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()
