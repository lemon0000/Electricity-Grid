# 快速编码normal整任务控制器

日期：2026-09-27。状态：DRAFT_NONAUTHORITATIVE。

`normal_task_controller_stream_fast.py`连接已验证的fast worker、日志、独立replay和有界
capture。相对stream前驱仅使用新模块、独立schema/request/observation/report类型；
两阶段监督、身份与资源检查保持。父进程只消费compact声明，不构造年度输入或assignment。

## 顺序与报告门

持久化controller intent→挂起execute Job握手→执行→整Job静默/退出与completion验证→
独立capture保留pins→新replay Job重建来源并零solver回放→静默后完整有界报告→
再次capture对比pins→复读报告及最终deadline检查。已有root拒绝，不重试或resume。

新报告类型`DeclaredFastNormalRecordReplay`、嵌套`FastSourceRecordReplay`与native JSON
逐项验证字段、标量类型、identity、调用数、assignment/witness、三层有限error词表及
完整错误投影。旧stream报告tag即使重算摘要和claim也拒绝；新类型不改变三态解释。
completed只表示开发流程完成，数值可能仍unresolved；authority字段仍false。

保留原process/Job commit cap、deadline、host reserve、父进程peak、文件树/bytes门及
静默后双capture。仍不声称硬磁盘配额、恶意同权限替换防护或正式资源认证。
最终observation是写入前检查快照，不能替代API返回完成的证据。

## 独立H25声明

runner为`experiments/audit_rq2_normal_task_stream_fast_v1.py`；新声明为
`configs/rq2_normal_task_stream_fast_h25_development_v1.DRAFT.yaml`。
保持来源、完整8784小时、H25/22275变量/28004约束、HiGHS1.15.1、1线程/1秒、normal60秒门，
execute/replay各240秒、process/Job768 MiB、总任务600秒。只换新root、schema和执行pins。
读取旧独立声明及pinned pair声明重算新pins，不在声明生成阶段prepare年度来源或求解。

新root：`results/tables/rq2_normal_task_stream_fast_h25_attempt1_non_authoritative`。
声明SHA：`807fcffd90ec05f2fdc6893b1b8be079aa53be8d4e80ebce7e94a46cbad6bb95`。
controller pin：`22e4c62e6f3b653aaadab0ca103666c0cb01d6e0dbfc498bdc7fe3e97797c013`。
normal pin：`0ab376211021edb3f48bf471abd799c3436fb231151bf006fbbad73def11ce67`；
source pin：`f7667787f5cd784e9f882d396ca1551d1632f3988d44de99c1b108d536c21322`；
declared pin：`e0f41c3c40d42e9ae1291a2825c8fb2b8ffefeb01ba1f294fd821deac987a864`；
replay pin：`65b297e9662cdb335c2a31f06d1f0acfb60ff3ec243b1e267285e53a834a95f1`。

## 验证记录

主命令使用`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider`。
只读runner7 passed in2.24s；新增旧stream报告tag反例1 passed,23 deselected in2.86s。
controller/reports首轮81 passed,3 failed in219.16s，另-x定向复现2 passed,1 failed in37.76s。
原因是新增测试的synthetic bootstrap四处仍引用旧日志类名，导致故障注入未进入预期阶段。
修正为DevelopmentDeclaredFastNormalStore，仅改新测试，controller源码和声明预算不变。
受影响退出/父死亡窗口及最终回归终态另记。

tiny双Job正例使用显式合成来源，不能证明真实H25有效解或整任务资源充分。
真实开发调用须在本轮测试与独立pre-seal findings闭合后进行一次；结果独立留存，
不回写旧attempt或声明旧失败得到修复。初态与业务功率映射保持机制参数，
current/episode、完整UID/四臂资源、恢复右删失、风险分母、科学注册及正式启动门继续开放。

受影响child退出/父死亡窗口6 passed,55 deselected in60.44s。独立runner/旧tag/两真实tiny
Job共9 passed in26.34s，外层及嵌套报告自洽重hash篡改34 passed in36.48s，限定差分
pre-seal无实现性finding；最终整组待终态。未生成official verdict/receipt。

| 文件 | 本轮SHA256 |
|---|---|
| normal_task_controller_stream_fast.py | `f4c77512e24e7592d8b31c73741d0d523ea285a1fa39b6fccf16bc100ce1d73a` |
| audit_rq2_normal_task_stream_fast_v1.py | `96d872bf0b6460a42fce17de3c5d51a8d222ab36d27207f8898f3655b192b182` |
| test_rq2_normal_task_controller_stream_fast_v1.py | `f9c4011b8ee5759ec40e2aad2eb3402465b471cf32cd9821150f6be8bfa322dd` |
| test_rq2_normal_task_controller_stream_fast_reports_v1.py | `9d2419926df4ec2026c1e6f0af5810c54755366adb6cb1e7312905db9919fcb2` |
| test_audit_rq2_normal_task_stream_fast_v1.py | `fd7234d8c007895241c9475ecffaf7d1da821a27af6b40d87506a14286a789a5` |

controller在src/rq2_joint_deliverability_boundary_v1，runner在experiments，测试在tests。
八批历史188项bytes/SHA复核一致，未清理仓库。

修正后最终整组命令：
`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_normal_task_controller_stream_fast_v1.py tests/test_rq2_normal_task_controller_stream_fast_reports_v1.py tests/test_audit_rq2_normal_task_stream_fast_v1.py`。
92 passed in223.37s，exit0。独立pre-seal所要求的最终终态验证已满足，无开放实质finding；
新controller/runner/config字节与上述身份保持，旧结果未改。该结论只支持已授权受限开发验证，
不构成production seal、official review receipt或正式实验授权。
