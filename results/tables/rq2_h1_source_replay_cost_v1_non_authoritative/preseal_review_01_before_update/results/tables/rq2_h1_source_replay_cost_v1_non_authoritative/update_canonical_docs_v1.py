"""Insert source-cost evidence while retaining every prior dirty document byte."""
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
TEXT = ('2026-10-21 source成本分解：保存3h prefix的单原Reader profile_02已exit0，reader74.837764s/outer79.578s（含cProfile），'
        '1302pins未变、465case/444owned SHA一致、三份normal audit/proof与旧intent相同，0新Job/native。'
        '实测两次parent inspect→12次Job科学重放/60次stage检查；1560次normal_input_identity、10922次顶层metadata.version，嵌套计时不相加。'
        '失败profile_01为toy source下错误重建真实manifest及空profile报告错误，原件保留；后继只编译原pin-bound manifest fixture，未重验真实源。\n'
        '原192h调用量进一步展开：M=5时源层597520次Job replay、2987600次stage replay（不是native求解）；constructor首次inspect结果复用是独立versioned候选，'
        '需保留双Reader、完整后置bookends并证明逐类fault/依赖/异常等价，当前未实现、未采纳。整链wall/RSS/storage及真实phase terminal/reopen仍未闭合，长链/resource/native/formal/seal/official各门false。'
        '证据：`results/tables/rq2_h1_source_replay_cost_v1_non_authoritative/{acceptance_report.md,call_dag_and_work_units.json,constructor_inspection_successor_design_v1.md,final_verification.json}`。以下先前记录保留。\n\n')


def main():
    output = HERE / 'canonical_doc_updates.json'
    if output.exists() or (HERE / 'canonical_before').exists():
        raise ValueError('fresh canonical document snapshot roots required')
    changes = []
    for path in (REPO / 'docs/plan/科研项目执行步骤.md', REPO / 'docs/model_spec/blocker_register.md'):
        before = path.read_bytes()
        offset = before.index(b'\n\n') + 2
        snapshot = HERE / 'canonical_before' / path.relative_to(REPO)
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        with snapshot.open('xb') as stream:
            stream.write(before)
        addition = TEXT.replace('\n', '\r\n' if b'\r\n' in before else '\n').encode('utf-8')
        after = before[:offset] + addition + before[offset:]
        path.write_bytes(after)
        assert after[:offset] + after[offset + len(addition):] == before
        changes.append(dict(path=str(path), before_sha256=sha256(before).hexdigest(),
            before_snapshot=str(snapshot), after_sha256=sha256(after).hexdigest(),
            insertion_offset=offset, insertion_length=len(addition), all_preexisting_bytes_recoverable=True))
    with output.open('x', encoding='utf-8') as stream:
        json.dump(dict(status='DRAFT_NONAUTHORITATIVE', updates=changes, formal_result=False), stream, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()
