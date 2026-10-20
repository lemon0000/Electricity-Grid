# 跨小时事故延续、修复与分支停止整链验收记录

2026-10-20，DRAFT_NONAUTHORITATIVE。`connected_03` 已完成 **3 个合成小时、7 个 lane-hour 的 paired commit**，并完成缺失下一小时输入的拒绝、外部 checkpoint 留存、全部关闭和同进程只读重开重放。独立文件、日志与 Fraction 算术补验通过。本记录关闭这个有界开发用例；完整 168h enrollment + 至多 24h follow-up 仍 OPEN。

终态为 `exit 0`、`1 passed in 1307.07s`，外层实际耗时 **1314.969s（约 21 分 55 秒）**。3h 是模拟覆盖，1314.969s 是墙钟耗时。原定 wall 1500s、120s 无活动、采样树 RSS 1GiB 和逻辑存储 128MiB 均未顺延。0 real native；没有正式实验结果或运行授权。

主要证据：[启动绑定](connected_03/request.json)、[终态](connected_03/terminal.json)、[JUnit](connected_03/junit.xml)、[独立补验](connected_03_postcheck.json)、[整链性能复核](workflow_performance_review_readable.md)、[PRE_SEAL findings](preseal_findings.md)、[下一阶段工作清单](phase_boundary_next_step_v1.md)。实际 case 保存在 `D:/h1_outage_connected_03_non_authoritative/test_three_hour_connected_outa0/`。

| 验收项 | 观察结果 |
|---|---|
| 正常路径 | 3 个受限 fake Windows normal Jobs 均 exit0/quiescent，完整 15 个 normal stages；34 次 fake selector capture |
| 共同 Rref | h0/h1 事故时可供 DC 20MW、request 5MW；h2 修复后可供 25MW、request 0 |
| 事故延续 | G1 在 h0 已处于事故中，onset unknown；h1 延续同一事件，未把左边界写成新观测跳闸 |
| 修复 | h2 观测 return，首小时 `min(30,60*0.4)=24MW` 上限 binding；所有保存调度满足它；unit oracle 另验证超 1MW 被拒绝 |
| 单分支停止 | capture index17 是 h1 CFE Actual stage0 的 timeout，仍有 1 个 feasible incumbent；保持 `actual_unresolved`，CFE business/actual 两条 carry 都停留在 h0，h2 跳过；Joint/Network 继续 |
| 缺输入 | h3 缺源得到准确 ValueError，保留 pending attempt；不生成第 4 个 normal Job、clock、obligation、source hour 或 selector capture |
| 持久记录 | 9 个 events：intent/outcome/attempt/intent/outcome/attempt/intent/outcome/attempt；3 个 outcome、7 个成对 lane-hour |
| 重开 | 外部 checkpoint 在 live owners 关闭前留存 heads、科学状态及 SHA；关闭后从该文件读取关键对照，fresh constructor、public inspect、独立 historical 与 parent snapshot 均通过 |
| 字节与句柄 | normal/owner/holder 三个 owned roots 共 **444 个文件**，关闭前、关闭后、重开各阶段、最终只读补验名称/SHA 全等；全部捕获的 lease handles 关闭 |
| 边界状态 | 重开报告 completed_hours=3、pending_attempt=true、continuation_available=false、episode_terminal=false；缺输入发生在 enrollment，不提供正式 follow-up 右删失指标 |
| 绑定与资源 | 1299 个启动 source pins 未变；1279 个继承实现/测试/config pins 及已验 36+23 项 guard 证据复用；8 个观察 PID 均退出，monitor/cleanup errors 为空 |

原科学实现、冻结配置和数值验收限没有更改。新增代码为两份 synthetic fixture/test，原 v2 owner/source/history 按原字节复用。N 始终使用两机可用的 base，事故只作用于 Rref/Actual overlay；N0 两机启动，N1/N2 不重复启动。三个 normal 的 G1/G2 为 30/15MW，五阶段 canonical locks 为 60/1/1/30/15。

独立 Fraction 算术仅统计已 paired 的业务动作：

| lane | h0 q | h1 q | h2 recovery r | 最终 debt | Actual MW |
|---|---:|---:|---:|---|---|
| CFE | 0.02 | 未提交 | 未执行 | `1/50 = 0.02` | 20；之后保持 h0 carry |
| Joint | 0.04 | 0.04 | 0.06 | `29/1000 = 0.029` | 15 → 15 → 40 |
| Network | 0.02 | 0.02 | 0.047058823529 | `7/20000000000000 = 3.5e-13` | 20 → 20 → 36.76470588225 |

q/r/debt 是 normalized 业务量。分别验证 `q<=f*w=0.05`、`q+r<=D=0.5`、recovery 的 power/headroom、debt/eta 及适用的 CFE surplus 上限；`power=250*(0.1-q+r)`，`debt_after=debt_before+q-0.85*r`。r 不受 `f*w` 的调用上限约束；Joint 的 0.06 符合冻结合同。Network 的微小未清债务按精确分数保留。timeout 不解释为数学不可行。

checkpoint 使用独立路径、exclusive create、flush/fsync 和精确 readback；两个 live trace marker 绑定相同 SHA。关键 heads/科学对照从文件重新读取，cfg、holder_args、roots 与 toy 环境仍来自同一进程。本例只证明 clean-close 同进程只读重开，未实现进程重启后的 writer rehydration、持久 atomic-live join 或 crash-durability 认证。

失败与补验原件全部保留：connected_01 在 N0 后因 toy selector aggregate budget 不足失败，0 paired/selector；修正为覆盖两机完整 inventory 的 13 次/13s，并以 unit06 验证 12/12 拒绝、13/13 通过。connected_02 已完成三小时主体，但文件活动监视在只读尾部停止它，原外部 heads 未保存，所以原 authenticated reopen 仍未验证；其 462 文件 SHA、detached 补验及失败状态保留。detached_03 仅证明保存投影/算术一致，未代替原重开认证。connected_03 通过新增关闭前 checkpoint 和真实返回阶段 trace 取得完整用例证据。

独立 postcheck 首次因把 owner 带换行 JSON 编码用于 parent 身份而失败，原 script/终态保存在 [postcheck_attempts/01](postcheck_attempts/01/terminal.json)。按原 parent compact JSON 无换行合同修正，并增加逐 3 个 Job request 的 parent 声明/identity 全等检查后补验通过；没有重跑 Job 或修改保存结果。unit01/02/03 的断言与 fake dispatch 错误、detached01/02 的失败也原样保留。

下一步聚焦真实 `E=168`、`F<=24` 的 enrollment/follow-up 边界、episode 终结与诚实右删失。先界定完整调用 DAG、昂贵 prefix 重放和可证明的复用边界，再形成固定预算的连接验证。当前三小时与旧两小时规模不同，不能用墙钟比例宣称优化收益，也不能线性外推 192h 成本。旧 hour0/两小时结果与科学结论继续保留。

`formal_result=false`、`formal_execution_ready=false`、`resource_admission=false`、`full_192_hour_execution_verified=false`。真实 RTS/native、完整生产预算、writer 可写重建、持久 atomic-live 认证、seal 与 fresh official review 仍 OPEN。
