# H1 跨小时连接验收记录

2026-10-20，DRAFT_NONAUTHORITATIVE。已打通一个**2小时、3分支的合成成功前缀**：`N0 → Rref/Actual → paired → owner内attempt/N1 → Rref/Actual → paired → 全部关闭 → 重开重放`。完整168h enrollment及至多24h follow-up尚未执行，整个episode尚未终结。本记录不关闭完整192h里程碑。

`connected_06`终态exit0，pytest为`1 passed in 600.37s`，总墙钟604.266s；其前当前candidate的36项相关回归全部通过91.12s/outer95.469s。2 normal Jobs、6 normal stages、18 selector captures，real native calls=0。

主要证据：[终态](connected_06/terminal.json)、[启动前绑定及预算](connected_06/request.json)、[只读数值/文件补验](connected_06_postcheck.json)、[对照数据库绑定](baseline_projection_bindings.json)、[完整回归](unit_08/junit.xml)、[开发验收矩阵](development_acceptance.json)。原始case保存在`D:/h1_cross_connected_06_non_authoritative/test_two_hour_three_lane_conne0/`。

| 验收范围 | 观察结果 |
|---|---|
| 连续推进 | 相同live owner/controller内部产生第二小时source/N；N、Rref及各Actual各自延续 |
| 持久记录 | `intent → outcome → attempt → intent → outcome`；2个outcome覆盖6个lane-hour，3分支均active，无pending |
| 业务与恢复 | 原exact business及数值replay执行；首小时非零调用，下一小时执行floor12恢复；共享预算逐小时满足 |
| 关闭重开 | 先关闭全部相关handles/leases再取快照；重开constructor完整replay、独立historical及parent snapshot检查通过；随后关闭重开handles |
| 保存文件 | normal/owner/holder三root的212个文件（包括execution.lock）名称及SHA256前后一致；只读补验再次核对 |
| 动态观察 | owner触发fresh共16次：hour0为12次，hour1为4次；source.prepare、historical reader、business、数值replay未替换 |
| 等价性 | hour0科学projection SHA与connected_04相同；两小时科学projection SHA均与connected_05保存主体相同；旧失败attempt终态保持原样 |
| 进程与资源 | 两Job均exit0/whole_job_quiescent；6个观察PID均退出，monitor errors/cleanup events均0；不能据此声称完整未观察进程树证明 |

独立Fraction补验结果如下。单位为normalized business量；它不是实际MW，MW映射另列。

| 分支 | hour0调用q | hour1恢复r | hour1剩余debt | Actual服务功率(MW)，h0→h1 |
|---|---:|---:|---:|---:|
| cfe | 0.02 | 0.023529411764 | 0.0000000000006 | 20 → 30.882352941 |
| joint | 0.02 | 0.023529411764 | 0.0000000000006 | 20 → 30.882352941 |
| network | 0 | 0 | 0 | 25 → 25 |

恢复效率为0.85，剩余debt保留为精确`3/5000000000000`。每个分支每小时均核`q+r ≤ min(D=0.5, f*w=0.05)`。本例两小时Rref request均为0 MW，因此未提供正网络调用或事故延续/修复的整链覆盖。

整链性能审查在启动前记录于[performance_review.md](performance_review.md)，本次固定900s、观察树RSS1024MiB、存储128MiB、120s无进展停止条件；运行中未顺延。峰值采样RSS377.94MiB，峰值logical storage20.44MiB。按trace相邻时间差分解：

| 阶段 | wall秒 |
|---|---:|
| body开始至N0 terminal | 69.388 |
| N0 terminal至hour0 paired | 100.624 |
| hour0 paired至hour1 paired | 304.570 |
| 关闭及首次文件快照 | 0.096 |
| 重开、完整重放、独立历史/snapshot、关闭及文件比对 | 69.179 |
| 入口、fixture及其余收尾差额 | 60.410 |
| 总墙钟 | 604.266 |

分项已四舍五入。嵌套owner stage timings见补验JSON，不能与上述父阶段重复相加。该wall time对应2个模拟小时，不能当作模拟覆盖范围或native运行预算。

采用的优化是：同一次operation合并重复完整replay；同小时共享current供共同Rref及各Actual使用；重开constructor已经完整replay后直接核其产物，省去紧接着的重复inspect；只在明确synthetic测试fixture内复用15个静态code/spec身份键。59448次memo入口对应15个唯一键，退出先恢复全部原函数，再逐键完整原实现复算，bookend一致。源码/config/spec启动快照与结束SHA一致，4份原phase owner/controller/source/business实现与首个诊断相同。

这些优化保持提交前独立fresh、历史和数值重放。test entry及static memo改变开发校验开销，`production_overhead_measured=false`，unobserved runtime dependency ABA未证明。旧chain07主体和独立后验04继续复用；全部失败/停止attempt保留。

[规模审查](scaling_review.md)另行推导并独立复核：在明确成功路径条件下，owner的fresh调用为`T²+5T+2`；T=192时为37826，一层prefix-hour权重为4867460，且尚不含独立postcheck、parent snapshot和完整episode终结的额外工作。它不是实测192h成本；当前动态历史重放不能线性扩跑。

当前主线进入跨小时里程碑的后续部分：先针对这条路径建立有证明的prefix复用/增量校验合同和可执行预算，再补enrollment/follow-up边界、分支独立停止、正网络调用、事故延续/修复、缺输入右删失及episode终结的完整链覆盖。随后才能进入具体科研任务包、资源准入、封存/official独立审查及具体正式运行授权。

本包source/catalog、normal binding和solver-shaped候选为显式synthetic fixture；不证明真实RTS整链、求解最优性或工程安全。只读重开不提供normal writer进程退出后的可写恢复，也不认证持久化atomic-live capability lineage。formal/native/resource各门保持false；旧通用Common/source-factory草稿的未闭合findings保留，不作为本包已完成的事项。

独立只读PRE_SEAL复核在本2h synthetic scope内未发现阻断性未闭合finding，详见[复核记录](preseal_findings.md)。raw Job中的`numerical_evidence_verified`和`whole_task_resources_verified`仍明确为false；Job成功退出与本例开发数值断言不提供正式数值/资源认证。跨attempt对照为补充回归，已绑定数据库及request/terminal SHA，不宣称独立来源鉴真。

新增实现为`experiments/h1_cross_hour_owner_development_v1.py`；对应测试为`tests/test_h1_cross_hour_owner_development_v1.py`，静态身份fixture为`tests/h1_cross_hour_identity_fixture_v1.py`。执行计划、H1里程碑表及blocker register同步记录上述范围和剩余缺口；原phase实现及冻结协议未改。

本次主要核验命令如下，解释器为`D:/Miniconda3/envs/compute/python.exe`：

```text
python -B results/tables/rq2_h1_cross_hour_v1_non_authoritative/run_diagnostic_v1.py unit_07 units_tail
python -B results/tables/rq2_h1_cross_hour_v1_non_authoritative/run_diagnostic_v1.py unit_08 units
python -B results/tables/rq2_h1_cross_hour_v1_non_authoritative/run_diagnostic_v1.py connected_06 connected
python -B results/tables/rq2_h1_cross_hour_v1_non_authoritative/summarize_evidence_v1.py connected_06
```

最后核对通过：三份规范文档的`git diff --check`、5份本次Python文件的AST/空白检查，以及1279个启动绑定源码/config/spec的当前SHA一致性。未改冻结参数或原实现。
