# H1 hour-0 校验优化的合同边界

状态：DRAFT_NONAUTHORITATIVE；已实现并接入未封存 v2 bootstrap/common，完整链尚待新运行终态。

用户已选择先完成保持原合同的校验优化，再重跑完整三 arm 链。该选择不授权真实 native 校准、正式运行，也不授权减少既有科学验收。

## 已取得的具体证据

`results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/historical_profile_04/`
保存一次现有 N0 的只读 historical.prepare 性能剖析。终态 exit 0，耗时
44.1290644 s（带 cProfile，不能当作正常运行预算）。369 个保存文件前后 SHA256 一致，
未创建 Job、未调用真实 native。恢复的是原集成测试已有的合成 source、enrollment 和
manifest resolver 替身；本次未证明真实源完整闭包。
本次没有安装主链的 bootstrap/adapter implementation identity bookend cache，
故调用计数可用于定位，耗时比例不能直接外推到主链。

该次调用实际执行 2 次 `_replay_prefix`、4 次 parent restore、8 次
`inspect_job`、24 次 stage inspect、56 次模型构造和 9475 次包版本查询。
`inspect_job` 累计 34.669 s，包版本查询累计 18.915 s；这些累计时间相互嵌套，不能相加。
前三次诊断失败分别保存在 historical_profile_01、02、03，未标为通过。

完整链 chain_02 仍为 INTERRUPTED_NOT_PASS：三个 N0 已完成，common.inspect 首次返回，
但后续整组断言、Rref/Actual、paired commit、重开重放均没有完成证据。

## 原合同中的实质边界

`docs/model_spec/rq2_h1_timed_job_controller_development_v1.md` 第 7 项明确：

> parent 每次 restore 都按 hour/source 顺序重放完整 Job child；只从已经完整重算的
> timed projection 中取批准转换后的 boundary，再调用 source._boundary 校验。

`h1_phase_historical_controller_development_v1.prepare` 还规定 current-only information
rebuilt twice。只保留文件扫描次数，并不能自动证明保持这两个要求。

因此，复用 ChildInspection 或 historical envelope 即使不改变模型、阈值和科学输出，
也需要独立的版本化验证合同与等价证据；不能把它描述成现有合同下已经闭合的实现优化。
用户在该边界说明后要求继续开发。新增两个 v1 verifier/witness 模块承载版本化验证合同；模型、阈值、source 重建和 carry 转移保持不变。原 historical v1 不修改。

## 可具体审查的窄方案

仅在一次 `_replay_prefix` 的同一个 Reader、同一组仍持有的 ReadView 内形成 witness：

1. 构造阶段保留完整旧顺序：bridge.inspect 的完整 Job 审计，再进行 ChildReference 的完整 Job 审计。
2. 随后的显式 reader.inspect 仍完整重建 source、network、packet、parent journal、anchor 和 carry。
   只有同一个 Job 的重复数值审计可用 fresh witness validation 替代。
3. 每次返回前后重读完整 reference、clock、anchor、Job、worker、hour、stage 的 byte/identity/topology。
   实际重算 request_key、stage_order、environment、resource_identity、executable/process identity、
   clock profile、vendor source/callable/AST 校验、runtime versions、实现 identity 和冻结阈值。
4. 缓存纯数值 payload，不调用旧模块私有 mint token，也不让旧 ChildInspection 冒充新的 fresh inspection。
   新 typed revalidation 结果用自身私有 token 和 scope nonce 绑定；只有首次 `_after` 完整成功才能提升缓存。
   `_after` 的投影检查和 carry 转移原样执行。
5. witness 绑定原 Reader、PID、thread、私有 nonce、完整输入 key 和 lease identity；
   只允许两次复用，随后在 prefix finally 销毁；第三次使用、跨 Reader、跨 replay slot、解锁、异常或关闭后均拒绝。

该方案静态地把每个 prepare 的完整 Job 数值审计从 8 次减到 4 次；
`witness_profile_04` 实测 33.5170197 s，对照为 44.1290644 s；二者均带 profiler，不能外推整链。首次两次审计不合并。

候选模块边界为新建 historical Job witness reader 和 phase historical successor，
再显式转接 v2 bootstrap/common。新 verifier identity 与 predecessor 科学投影必须分开标识；
若新版本改变 audit implementation，audit hash 就应随版本改变，不能同时要求旧 audit 逐字相等。
实现采用独立 `VerifiedHistoricalEnvelope`，保留 predecessor audit 科学投影；bootstrap implementation identity 和 N0 terminal 另行绑定 `historical_verifier_identity`，持久化 `full_numerical_hour_replays=4`、`fresh_byte_context_revalidations=4`、`recomputed_on_revalidation=False`，common 新鲜校验时逐项比较。
旧 v1、src、冻结配置和保存工件保持原字节。
不使用共享 io monkeypatch、全局 active scope、thread-local 或跨操作缓存。

## 必须先关闭的证明与验收项

- 完整遗漏输入审计，特别是 `timing.validate_vendor()` 的安装文件与 callable 检查；
  递归 implementation identity 不能替代它。
- fast/full 决策、projection、carry 和 audit 科学字段等价；变更后的 verifier 身份单独绑定。
  只有明确保留 predecessor audit schema 的部分才能要求 audit 逐字相等。
- 每类原始输入字节、同字节替换、namespace、环境、volume、时钟、版本、阈值、直接 dispatch 的 entry/exit 漂移拒绝。
- Reader/key/nonce/PID/thread/lease 替换、异常 poison、关闭清理和禁止超次使用。
- 无 solver/Job 的小型对照及实际耗时剖析通过，再从全新目录执行完整链。

## 当前证据及限制

`witness_equivalence_03.json` 记录当前候选的真实保存 N0 对照：decision SHA256 为 `1515773f780ef17aa85a27c0eab18eaf11a2c61c53964fbfc974bbba5b79ef85`，predecessor audit SHA256 为 `c07eaba8538ada9ac492d2f5c0aafa41f1efb388480a982393c6909a467934ab`，均与原实现 exact-byte 相等；实际完整 hour.inspect 调用为 4 次。两个生产文件和 369 个保存工件前后 hashes 一致。

62 项针对性检查已终态通过，涵盖作用域、结果构造、文件字节与同字节替换、namespace、packet/spec/limits/pins、阈值、vendor、PID/thread/lease、entry/exit 漂移、verifier/helper/Reader 绑定。接线后固定字节回归另行记录，不用该局部结果代替完整链。

运行时检查覆盖项目 module/direct callable/class/constants 及原有 vendor 检查。任意第三方对象图反射修改与两次观察之间不可见的 ABA 不在证明范围；`complete_dynamic_input_closure_proved=false`。结果不是进程隔离安全凭据。

v2 是可继续迭代的未封存 draft，按 agent.md 第 7 节在原路径修复；旧失败尝试的 exact tested bytes 已保留，新 identity 不用于重新标记旧 root。完整 hour-0 仍须取得新目录运行、paired commit、重开重放和全链耗时终态。
