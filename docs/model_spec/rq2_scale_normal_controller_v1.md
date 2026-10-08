# Source-bound normal父控制器草案

状态：DRAFT_NONAUTHORITATIVE，2026-09-28。实现为
`src/rq2_joint_deliverability_boundary_v1/scale_normal_controller.py`，测试为
`tests/test_rq2_scale_normal_controller_v1.py`。

## 范围与事务

复用既有Job监督、来源核验及normal worker。完整原始资源计划与请求、环境、实现字节进入身份。
normal envelope覆盖execute、audit、两次Job静默及controller allowance；execute还须覆盖数值内核
总wall和显式来源/归档余量。父端独立回放计入controller allowance，不能借未用solver时间。

父root lease覆盖整个流程。各phase先持久化intent，创建挂起子进程后持久化PID/creation-time，
再核已有证据并release。退出码、Job静默及观察字段通过后才读取receipt。
execute后保存来源记录/intent的文件身份和SHA，以及证据目录与锁的身份；释放证据锁供audit worker
取得。audit退出后父端重新独占证据，比较跨phase身份与字节，完整重算来源/数值审计并比较报告。
父端审计阻断四个执行入口，finally恢复。证据锁保持至终态写入。

最后一次全链检查在终态构造前；result使用exclusive/fsync/exact-readback写入，随后不再做可能失败的
全链校验。finally仍关闭两层lease；关闭异常会传播，单独发现result文件不等于调用正常完成。
本草案不提供自动重试或可执行resume。

## 返回语义

- 完整调用且独立回放接受：`replayed_accepted_normal`。
- 完整调用且回放一致但不接受（包括未达到最优门）：`replayed_unresolved_normal`。
- 数值记录未完整复现：`unresolved_normal_record_not_reproduced`。
- 缺少normal返回或调用计数不完整：`normal_invocation_unknown_not_replayed`。

保留`solver_calls`及`call_count_complete`，所有分支均保留完整`reserved_solver_seconds`。
未知调用不转换成零调用；TIME_LIMIT不转换成数学不可行。所有结果保留formal/resource authority为false。

## 当前验证

此前17项实现、预算、父端零solver重算及篡改反例通过（31.10秒）。新增subprocess测试在pytest临时
目录显式装配合成RTS/pair来源替身，调用真实worker入口及Windows Job；native求解上限一秒。
首轮真实流程已返回接受结果，测试因Python tuple与JSON list直接比较失败；改为canonical bytes比较。
随后真实流程及execute intent/launch写失败3项通过（37.30秒）。

修复终态窗口并补目录/锁跨phase身份后，真实流程加5个audit窗口6项通过（106.30秒）：audit
intent/launch写失败、launch前intent改写、同字节record替换、同字节lock替换。断言只有execute
被release、失败不发布result且两层lease可重新取得；正例实测audit receipt读取与终态写入时证据锁
仍被持有，且终态写入后没有全链校验。限定独立pre-seal未发现开放实质finding。

命令使用compute Python `-B -m pytest -q -p no:cacheprovider`，新窗口筛选
`tests/test_rq2_scale_normal_controller_v1.py -k 'real_subprocess or audit_failure_window'`。
这些证据不验证真实RTS来源端到端执行、长求解收敛、父进程硬资源上限或正式科学协议。
H25最优性、完整研究任务/预算、机制参数和右删失登记、正式审查及运行许可仍分别开放。

最终相关回归：同一命令运行本测试文件及`test_rq2_declared_task_process_v1.py`、
`test_rq2_normal_task_process_v1.py`，筛选`not real_subprocess and not audit_failure_window`，
69项通过、6项未选择（47.53秒）。这与上述6项组成当前新controller全部25项及相关process的50项；
是两个分批命令，不合称单次全组。`git diff --check`通过。
