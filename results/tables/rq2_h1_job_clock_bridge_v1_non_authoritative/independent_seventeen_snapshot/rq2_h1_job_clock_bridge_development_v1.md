# H1 Job clock bridge development v1

状态：DRAFT_NONAUTHORITATIVE / PRE_SEAL_AUDIT，R3，根代理唯一写入。

新增 Controller 包装已闭合 timed Job/controller；独立 outer guard 串行 step/close，base guard 继续保护原科学事务。旧 parent/worker/protocol bytes 不变。新计时不是旧 parent outcome 的组成部分，只有外部固定的 bridge binding/intent/job/terminal 才能解释新增计时。

平台合同：Windows CPython >=3.10、未替换的 builtin perf_counter_ns、get_clock_info、worker Measurement 默认时钟，双方完整 profile 相等（QPC、monotonic、adjustable、resolution、Python version、integer ns）。同机关系来自既有 live Windows Job 精确 handles、PID/creation 及 source/worker 身份链，不从 profile 字符串推导。Python 明确 Windows 从3.10起 perf_counter 为 system-wide，ns 接口使用纳秒；Microsoft 说明同一机器的 QPC 可跨线程/进程比较，频率在系统启动后固定。
来源：[Python 3.12 time](https://docs.python.org/3.12/library/time.html#time.perf_counter)；[Microsoft QPC](https://learn.microsoft.com/en-us/windows/win32/sysinfo/acquiring-high-resolution-time-stamps)。
本单元没有双端直接 QPF 测量；上述是受信平台合同。跨线程 QPC 近邻读数有量化/排序不确定性，不据 ns 数字声称物理时钟误差已界定。严格包含失败即拒绝，不放宽容差。

测量区间：
- Job envelope 在调用原 _job 前开始，在其 exit0/whole Job quiet、完整输出复核、Job lease 释放返回后结束。
- worker core window 从已固定 binding.start_ns 到 terminal.end_ns；其后 terminal 落盘、fresh inspection、Completion 与退出仍落在 Job envelope 内，但不能由 worker core window 单独恢复。
- transaction envelope 包含当前 step 的 headroom 检查、intent、source/replay、Job、父端 reference/outcome 和随后确认前的工作。
- 全部 native intervals 已由完整 worker science replay 验证，另要求 transaction_start <= job_start <= worker_start <= worker_end <= job_end <= transaction_end，native_total <= worker core duration。observed_non_native = transaction_wall - native_total，只扣一次，仍包含 observer 工作。
- terminal 发布、fresh timing/science/parent 复核和最后检查属于 live confirmation_tail_ns；最后取 tick 后的对象构造、返回、caller、模块导入、controller 初始化和 close 不在已证明的完整生命周期内。磁盘 fresh reader 不重建 live receipt。
- 不与旧 TaskProcessObservation 的 float elapsed_seconds 做精确等式，不证明2440秒预算。

持久顺序：bridge intent → 原 parent intent/Job → bridge job.json → 原 parent reference/outcome → bridge terminal → fresh复核 → 私有token Observation。新记录单向绑定 parent identity、input head/source、Job八records、worker pin链、outcome/head/anchor及前一计时terminal。job.json 写前/写后失败使 parent 保持 pending；terminal或最终复核失败可能留下已完成 parent outcome，但 successor poison、无Observation且不得继续。reader检查完整Job science和历史anchor transition；parent_prefix_verified仍false，不能替代完整parent独立重放。

新增逻辑内容界：(1+3H)*262144+1 bytes，2+3H files，1+H directories。逐step额外headroom观察合并当前Job内容界、parent_updates、剩余clock records和scratch，同卷按既有资源原语聚合。此观察不是预留，也不覆盖FS分配、实际峰值内存或全任务时间，旧Job runtime budget未改。

验证要求：真实受控短Windows Jobs、synthetic三阶段adapter，连续两小时、fresh reader、算术/同域/包含反例、job/terminal写前写后、最终复核及晚漂移、clock替换、lease关闭确认/ABA。零真实native。所有广域FLAGS保持false；无formal seal、official verdict或新的native运行许可。

补充边界：headroom 是当前 live 的同卷 commit/volume 观察，不持久化且 fresh reader 不能证明该次观察；scratch 在该观察中以 controller root 的同卷需求表示，原 Job 启动仍绑定真实 scratch 路径。只接受 exact HostHeadroomObservation、对应 request identity 和全部 false authority flags。step 返回原 parent result，计时 live 凭据为 last_observation；调用者必须同时取得并固定它。fresh inspect 只验证单小时和立即前驱 terminal，不声称完整 clock prefix。外层锁覆盖 step、inspect、close，busy 拒绝不改变正在执行的状态。补测试：并发入口拒绝、错误headroom身份/authority/type、job计时已保存后原source事务失败、重签bridge链的同PID及区间越界反例、最后live tick失败。
