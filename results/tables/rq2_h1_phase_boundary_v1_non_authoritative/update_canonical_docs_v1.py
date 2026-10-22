"""Insert this bounded development outcome; retain every prior document byte."""
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ADDITION = '''2026-10-20 phase边界预算审计更新：旧hour0/2h/3h主体按精确绑定复用，1299启动pins、1279继承pins、444 owned及465 case文件SHA重新匹配。新增预算计数覆盖额外terminal和public inspect：T=192需至少576 events、1546 Reader observations/149380 prefix-hour，parent inspect3092/298760；原toy max_events=32在第11小时预留分支即拒绝。三条lane始终活跃时仅ready/post的business validation历史长度下界28311936，且未含normal内部/序列化/收尾。目标整链wall/RSS/storage无依据，overall_performance_review_complete=false、长连接包不准启动。
原E=168/F<=24下的独立业务/phase-body单元unit_04为15passed/84.34s，outer87.656s、sampled RSS180867072B、logical309574B，1305 pins未变、观察PID退出，0 Job/native。9份事实核167→168 need、携primary债followup、primary恢复后保留followup debt、deadline F不被晚恢复擦除及hour192先恢复再snapshot=0。completed/halted标记和heads/binding为明确单元元数据，不建立真实paired/source/owner凭据；完整168h N/Rref/Actual前缀、terminal event→close/reopen及缺必要followup的typed unresolved/right-censor终结仍OPEN。原三次单元失败完整保留。
下一步先为owner/business重复重放设计独立versioned增量验证/operation内复用，证明freshness、依赖闭包和原oracle等价并取得有界整链代表性成本；登记完整event/holder/normal档案及总资源后重审。正式实验、resource/native authority、full192、writer重建、persisted atomic-live、seal/official review均未开放。证据：`results/tables/rq2_h1_phase_boundary_v1_non_authoritative/{whole_workflow_budget.md,budget_audit_v1.json,boundary_acceptance_matrix.md,unit_04/terminal.json}`。以下原记录保留为历史。

'''


def main():
    records = []
    prior = json.loads((HERE.parent / 'rq2_h1_cross_hour_outage_v1_non_authoritative/final_verification_03.json').read_bytes())
    plans = []
    for name in ('docs/plan/科研项目执行步骤.md', 'docs/model_spec/blocker_register.md'):
        path = REPO / name
        before = path.read_bytes()
        if sha256(before).hexdigest() != prior['bindings'][str(path)]:
            raise ValueError('canonical document changed since the inspected handoff')
        offset = before.find(b'\n') + 1
        if offset == 0:
            raise ValueError('missing document title')
        newline = b'\r\n' if before[:offset].endswith(b'\r\n') else b'\n'
        insertion = newline + ADDITION.replace('\n', newline.decode('ascii')).encode('utf-8')
        after = before[:offset] + insertion + before[offset:]
        assert after[:offset] + after[offset + len(insertion):] == before
        snapshot = HERE / 'canonical_before' / name
        if snapshot.exists():
            raise ValueError('document snapshot must be fresh')
        plans.append((path, before, after, snapshot, offset, len(insertion)))
    for path, before, after, snapshot, offset, length in plans:
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        with snapshot.open('xb') as stream:
            stream.write(before)
        path.write_bytes(after)
        records.append(dict(path=str(path), before_sha256=sha256(before).hexdigest(),
            before_snapshot=str(snapshot), after_sha256=sha256(after).hexdigest(),
            insertion_offset=offset, insertion_length=length, all_preexisting_bytes_recoverable=True))
    with (HERE / 'canonical_doc_updates.json').open('x', encoding='utf-8') as stream:
        json.dump(dict(status='DRAFT_NONAUTHORITATIVE', updates=records, formal_result=False), stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(documents=len(records), all_preexisting_bytes_recoverable=True)))


if __name__ == '__main__':
    main()
