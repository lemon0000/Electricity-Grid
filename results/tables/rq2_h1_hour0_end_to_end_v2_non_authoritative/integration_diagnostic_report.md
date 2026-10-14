# Hour-0 完整集成诊断：尚未通过

2026-10-13。`chain_02` 到达三个独立合成 N0、三 arm roster 和首次 `common.inspect`
返回后中断。尚无该返回后的整组测试断言完成证据，不能将该 checkpoint 记为测试 PASS。
完整 Rref/Actual → paired commit → 关闭重开重放尚未在这条链上执行，
不能据此关闭第 2 个里程碑，也不能扩大到 192 小时验证。

本次仅为 development 合成诊断：真实 native 调用为 0，没有正式实验、校准、资源准入
或 official review 结论。三个 N0 使用真实 bounded Windows Jobs 和显式 fake adapter；
预定 selector 使用 synthetic lifecycle，不能称为 canonical selector Job 验证。

## 已观测的完整前缀

| 连续计时段 | 秒 |
|---|---:|
| source/fixture setup | 28.0066101 |
| arm 0 open | 14.2419990 |
| arm 0 N0 父链 | 273.6665895 |
| arm 0 roster attach | 495.7816911 |
| arm 0 close | 85.4122766 |
| arm 1 open | 77.5712196 |
| arm 1 N0 父链 | 966.0908591 |
| arm 1 roster attach | 881.0960620 |
| arm 1 close | 148.7311487 |
| arm 2 open | 141.8392195 |
| arm 2 N0 父链 | 1751.7071310 |
| arm 2 roster attach | 1259.4776763 |
| 首次完整 common 重建 | 1112.7325062 |
| 上述连续段合计 | 7236.3549887 |
| collection 与中断前尾段 | 53.1180762 |
| pytest subprocess 总墙钟 | 7289.4730649 |

三个 N0 子进程均 `exit_code=0`、`whole_job_quiescent=true`，各自约 32–34 秒。
父链 N0 时间包含准备、持久记录核验和重放，不能等同于子进程求解时间。
未执行的阶段没有填零；本表不是全链成功耗时。

## 具体阻塞与证据边界

独立只读 PRE_SEAL 调用图检查发现，单次完整 common prepare 至少执行
30 次 historical prepare、60 轮 prefix replay 和 156 次 dependency verifier 扫描。
当前测试从第三 arm attach 到 handoff 至少调用 68 次完整 common prepare。
首次 common 实测用时 18.55 分钟；后续每次的耗时尚未观测，不能把静态倍数当作正式预算。

bounded verifier 已接入 manifest/bootstrap，但 downstream 仍反复重建 registry 和历史科学输入。
现有 `_observed` 不能直接用作缓存凭据：source 部分仅记录 file identity，registry 没有完整
read-path inventory API。每个原边界都保留双遍 byte scan 的 phase witness 也不会减少扫描次数。
后续优化必须先证明输入闭包、fast/full 等价和每个边界的漂移拒绝，不能用 stat-only 或跨解锁
缓存替代现有合同。此诊断尚未实现或证明这样的优化。

完整测试采用纯 implementation-identity 的入口/出口测试缓存；它不覆盖瞬时代码/包版本 ABA，
也不测量 production overhead。期间存在两段辅助测试并发，详见 `chain_02/concurrent_validation*.json`。
这些条件进一步限制了将本次 wall time 用于资源预算的可能。

## 已保留的检查与失败尝试

- `routing_04`：90 passed，exit 0；包括 83 个既有 verifier 检查和 7 个 v2 路由检查。
- `persistence_01`：34 passed，exit 0；包括 29 个 v2 故障窗口检查和 5 个 adapter source identity 检查。
- `selector_routing_01`：3 passed，exit 0；属于单独的 selector/handoff 辅助诊断，不替代本完整链。
  直接旧 helper 有 predecessor 清单的运行前后 hash 证据；四个间接旧测试只有终态 hash，
  边界详见 `selector_routing_review_01.json` 与 `preservation_check_02.json`。
- `chain_01`：中断，896.5008696 秒；132 个工件归档保留。
- `chain_02`：`exit_code=4294967295`，中断；369 个工件归档与原目录逐项 hash 相同，
  before/after 测试代码 hash 相同。只终止经 PID、parent PID、creation time 和命令核对的本次
  pytest；终止前确认三个 N0 Job 都已退出，pytest 没有活动子进程。

中断时的进程退出释放 OS handles，不等于全部正常 close 路径已通过。后续全链仍必须实际检查
正常关闭、锁重新获取、保存记录重放和独立进程重放。

## 复核入口

`chain_02/terminal.json`、`timing.jsonl`、`interruption_intent.json`、`diagnostic_summary.json`、
`artifact_inventory.json`、`tested_bytes/` 和 `artifacts/` 保存本次 exact bytes 与执行前缀。
原目录 `D:/h1_chain_02_non_authoritative` 保留。`repeated_validation_findings_01.json`
记录只读调用图检查；`successor_diff_audit.json` 区分机械路由和实际行为改动。

完整验收仍要求一次成功的三 arm → Rref/Actual → paired commit → close/reopen/replay 终态，
随后执行 `run_postcheck.py` 的依赖 preimage、时间核对和独立保存记录重放检查。
当前中断尝试不满足该 postcheck 的入口条件。
