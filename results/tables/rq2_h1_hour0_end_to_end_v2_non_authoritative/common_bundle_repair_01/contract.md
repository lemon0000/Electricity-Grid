# Common 单 arm 双投影校验草案

范围：未封存 development v2，仅用于保持科学输出的校验优化。没有 native、正式运行、
资源准入或完整 192 小时覆盖的新增授权。

旧 `_arm` 先调用 historical prepare，再调用 exact-source prepare；两者各自执行两次
独立 prefix 重放。新 `prepare_common_bundle` 从 exact-source 同一调用的两次 prefix
结果分别生成完整 legacy historical 投影及 exact-source 投影，并逐字节比较两个
historical 投影。每次 prefix 仍使用自己的四个 ReadView、Reader 和 witness scope，
按原实现关闭；不在两次 prefix、两个 arm、两轮 common 或不同调用间保存缓存。

每个 arm 的完整数值重放从 8 次变为 4 次，fresh byte/context revalidation 从 8 次
变为 4 次；两轮三 arm 合计从 48/48 变为 24/24。数字描述共享的实际执行，不能将
historical 和 exact-source 两份投影重复计为两次执行。外层 `verification_execution`
明确 active source identity、active historical verifier identity、两个投影的 hash、
共享消费者及实际计数；common 将 active historical identity 与 retained terminal
的历史 identity 比较。legacy scientific audit 的 schema/implementation 继续表示
原科学投影，而非冒充旧 envelope 的执行身份。

保留的观察边界：两次 prefix 及共同 call-local observed map、两次 registry.prepare、
source load、source.validate 的重新读取、最终 source observation、完整 dispatch 与
implementation 检查、两轮完整 arm audit 比较。所有数值阈值、功率/服务平衡、业务
映射、F/X、恢复债务和 paired commit 规则保持不变。

验收要求：

- 合成 prefix 下 historical audit/decision 与独立旧投影逐字节一致，exact science 一致。
- 保存的真实合成 N0 记录上，科学投影与旧 common report 一致；audit 只允许 active
  source implementation identity 和新增共享执行说明的预期变化。
- profiler 实测每 arm 两次 prefix、四次 full 和四次 fresh；无 native/Job 调用。
- helper、类方法、编码器或 public route 被替换时拒绝；second prefix、registry、source
  validation 和最终 observation 故障仍拒绝；retained terminal/payload 漂移拒绝。
- 独立进程串行计时与调用计数分开登记，不将带 profiler 或竞争运行的时长作为提速比例。
- 后半链 helper 的三 Actual/paired/reopen 检查只证明显式 synthetic common/source
  fixture 下的接线，不代替真实三臂 N0/common 的完整长链验收。

跨 `_prepare_locked` 或同调用跨 prefix 的更广泛 witness 复用没有在本草案实现；它需
独立的 scope/type/计数合同与漂移、锁释放、跨线程等故障验证，不能通过扩大旧缓存实现。
