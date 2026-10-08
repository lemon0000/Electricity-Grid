# H25 原生目标/界诊断执行记录

2026-09-28。依据用户“修复好问题开始正式实验吧”的修复授权，执行一次非正式来源诊断。
没有重试，没有覆盖旧协议、配置或结果。此诊断不改变原验收谓词。

代码：`src/solvers/rq2_objective_provenance_run_v1.py`；入口：
`experiments/audit_rq2_h25_native_provenance_v1.py`。
复用既有 Windows Job 进程监督，native 上限600秒、worker wall900秒、process/Job commit各1GiB，
输出payload上限16MiB。父进程commit和disk没有硬配额，whole_task_resources_verified=false。
使用原H25 source packet及其600秒spec，25小时、158 UID、22275变量、28004约束。

执行前限定预审修复了父端exact record/schema、进程观测交叉核验、完整外层文件身份/hash绑定。
真实tiny子进程闭环与record同bytes替换、intent篡改、7类观测伪造均覆盖。
最终入口24项通过（8.77s）；其中首次隔离子进程测试因夹具导入pytest缺pygments而失败，
去除子进程的测试框架依赖后通过。该次组合shell的末尾Get-Process无匹配返回1，pytest自身24项通过。
限定预审findings闭合；无单一incumbent时direct_provenance_observed=false且不重试。

```text
D:/Miniconda3/envs/compute/python.exe -B experiments/audit_rq2_h25_native_provenance_v1.py --execute-development --expected-script-sha256 d1125fe93deaf741db319602306aa5119fdc3bb3b014e79d704c1d6960873b97 --expected-runner-identity 6befe7cc582bd33d35f2af8e56a3cf89966cfcd25d3a6551233632dffbdc8bbd
```

已完成，solver_calls=1。worker PID12004，exit0且whole Job quiet；wall227.921秒。
原生Runtime176.74699997901917秒；Job峰值commit564776960 bytes。原生SolCount记录9，
仅加载并检查其中一个incumbent，不代表验证9个解。结果payload4435500 bytes。

| 通道 | 直接保存/重算证据 |
|---|---|
| ObjBound、ObjBoundC | `0x1.53125e9f2afa1p+20` |
| ObjVal | `0x1.53125e9f2afa2p+20` |
| canonical objective | `0x1.53125e9f2afa0p+20` |
| direct→Pyomo LB/UB | hex相同 |
| native/canonical目标代数 | 相同 |
| 新旧H25完整assignment | 22275项逐hex相同 |
| canonical残差 / 整数违约 | `2.788453912216937e-10` / `0` |
| 旧严格lower<=canonical | false，原结果保持unresolved |

来源诊断目录：`results/tables/rq2_h25_native_provenance_attempt1_non_authoritative/`。
result SHA `a3832900d078a569cb0f9862cf0dbfafac17f0cc2c4ca9aa80aa6edccf8608f0`；
record SHA `87cefb0f180f49d0315de24b761e85f4fa8dd27c85310ca944652e184f49979d`。
manifest同时绑定intent、launch、observation、record hashes及process/request/script/runner身份。
所有formal/normal acceptance标志仍false。

随后执行 `experiments/replay_rq2_h25_native_provenance_v1.py`，先在7个tiny正反例中验证
零solver重建及assignment、残差、目标项、reference inventory和comparison篡改拒绝（1.97s），
再从实际source重新构模，加载归档完整赋值，重算结构、约束/变量界残差、整数性、canonical目标、
精确目标项及通道关系。回放不调用solver，所有禁止入口在finally恢复。
保存于 `results/tables/rq2_h25_native_provenance_replay_v1_non_authoritative/replay.json`，
SHA `bcaef6a3d35c30e8e5f15f296689565c24f7b8472d6f28a5a1cfd86163f1aa0f`；
绑定生成器SHA `87c6e80db3a6737bcb5d78b7ecb263db8f3c6bfd37026e18c92c8ce3bcffa4ea`。

限定结果复核未发现hash/来源绑定断链，数值关系重现。两项解释边界明确保留：

- 回放字段 `objective_channels_recomputed=true` **仅表示归档通道之间的关系已重算**，
  不表示零solver重获ObjVal/ObjBound/ObjBoundC。后继字段应命名
  `archived_objective_channel_relations_recomputed`；本次已绑定产物不改写。
- 这是独立执行的fresh source/model重建，**不是独立算法实现**。它复用producer的结构、
  残差、整数性、algebra及comparison helpers；不能发现这些共享kernel的系统性错误。
  native-term arithmetic是对归档数据复算，canonical algebra才来自fresh模型。

数值验收候选见 `rq2_normal_numerical_acceptance_candidate_v1.md`。
其条件谓词对本次真实记录通过，但改变正式验收前仍需具体科学授权及完整successor验收。
完整服务合同、全支持计算及训练容量/holdout证书继续是其它开放门。
