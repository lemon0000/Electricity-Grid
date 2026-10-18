"""Render only a terminal, postchecked synthetic integration report."""
import hashlib
import json
from pathlib import Path
import re
import sys

EVIDENCE=Path(__file__).resolve().parent


def read(path):return json.loads(path.read_bytes())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main(label):
    if not re.fullmatch(r'chain_[0-9]+',label):raise ValueError('exact chain label required')
    attempt=EVIDENCE/label
    terminal=read(attempt/'terminal.json')
    assert terminal['exit_code']==0 and terminal['before']==terminal['after']
    launch=read(attempt/'postcheck_launch/terminal.json')
    assert launch['exit_code']==0 and launch['unchanged'] is True
    complete=read(attempt/'postcheck/completed.json')
    assert all(complete[k] is True for k in ('complete_synthetic_hour0_chain',
        'fresh_process_saved_replay','dependency_inventory_preimages_bound','timing_reconciled'))
    post=read(attempt/'postcheck/chain_postcheck.json')
    replay=read(attempt/'postcheck/fresh_process_replay/result.json')
    replay_terminal=read(attempt/'postcheck/fresh_process_replay/terminal.json')
    assert replay_terminal['exit_code']==0 and replay_terminal['artifact_bytes_unchanged'] is True
    assert replay_terminal['implementation_bytes_unchanged'] is True
    assert replay_terminal['supplemental_bytes_unchanged'] is True
    report=read(Path(post['report_path']))
    assert (report['synthetic_N0_jobs'],report['canonical_selector_jobs'],report['real_native_calls'])==(3,0,0)
    assert replay['completed_hours']==1 and replay['paired_lanes']==3
    lines=['# 三 arm hour-0 完整合成集成报告','',
        '状态：完整合成集成及独立进程保存记录重放通过；证据为 non-authoritative development。','',
        '三个独立 N0 经 common、Rref、逐 lane 业务映射与 Actual 到达 paired commit；关闭后重开，保存记录中的 heads、projection 和 carry 核对一致。',
        '本例使用合成 source/enrollment/registry 与 fabricated solver adapter：N0 Windows Jobs 为 3，canonical selector Jobs 和真实 native 调用均为 0。','',
        '## 完整链耗时','',
        '| 阶段（原始 trace label） | 秒 |','|---|---:|']
    for row in post['timing']:lines.append(f"| `{row['label']}` | {row['interval_seconds']:.6f} |")
    lines += [f"| collection 与剩余 teardown | {post['collection_and_remaining_teardown_seconds']:.6f} |",
        f"| pytest 总墙钟时间 | {terminal['elapsed_seconds']:.6f} |",'',
        f"独立进程保存记录重放及引用字段检查：{replay_terminal['elapsed_seconds']:.6f} 秒，其中六次新鲜历史校验与字段检查为 {replay['copied_reference_validation_seconds']:.6f} 秒。",'',
        '计时包含测试专用 implementation identity bookends；并行检查记录见 chain_postcheck.json 的 timing_conditions。该计时不构成 native 运行预算或资源准入。','',
        '## 保存记录与边界','',
        f"- carry SHA256：`{replay['carry_sha256']}`",
        f"- projection SHA256：`{replay['projection_sha256']}`",
        f"- holder head：`{replay['holder_head']}`",
        '- 三个 N0 Job 均 exit 0 且 whole_job_quiescent；具体 PID、creation identity 和原始 observation 在 chain_postcheck.json。',
        '- 完整测试包含缺 Actual 的拒绝检查；补充失败窗口证据须按各自测试范围阅读。',
        '- 本报告只覆盖该 hour-0 合成输入。跨小时/192h、正式资源准入、封存、official review 和正式实验仍需各自出口。','',
        '## 核验入口','']
    names=('terminal.json','postcheck/chain_postcheck.json','postcheck/fresh_process_replay/terminal.json',
        'postcheck/fresh_process_replay/result.json','postcheck/postcheck_manifest.json')
    for name in names:
        path=attempt/name
        lines.append(f'- [{name}](<{path.as_posix()}>)，SHA256 `{sha(path)}`')
    path=attempt/'complete_integration_report.md'
    with path.open('x',encoding='utf-8') as stream:stream.write('\n'.join(lines)+'\n')
    print(path)


if __name__=='__main__':main(sys.argv[1])
