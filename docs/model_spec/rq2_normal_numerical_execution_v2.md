# Normal 数值执行资源门修复 v2

候选开发期为 DRAFT_NONAUTHORITATIVE，封存状态与独立审查结论由 outer/receipt 记录。本 successor 仅修复 execution v1 official REWORK 的三项 finding；继承 v1 的来源绑定、完整计划回放、持久监督、one-shot 和 unknown 语义。数值验收沿用已授权规则，所有旧封存字节保持不变。

## 接受条件

1. 复用原 `_peak_working_set_bytes`，在初始来源准备后、每次建模前后、native 调用前、返回后以及完整 core 序列化后检查进程 lifetime peak working set。测量必须为严格正整数，且不超过原 `max_process_peak_working_set_bytes`。Job commit 限制继续独立执行。
2. core 大小定义为完整 canonical execution record 的字节数，包含原生数值记录、projection、完整 encoded prepared plan、来源快照和资源记录。执行及离线回放均施加原 `max_core_evidence_payload_bytes`，外层 archive 限制不能替代它。
3. 外层 elapsed 必须为预算范围内有限非负 float；有完整 provenance 时须满足 `observed_wall_seconds + 1e-6 >= native Runtime`。这里的 `1e-6` 沿用旧来源审计的计时一致性容差，不改变目标、残差、整数或 gap 限。

记录保留资源采样 `before/after`；回放要求其严格整数、正值、单调且未超限。回放不以审计进程当前资源替代历史测量。序列化后再次采样，并在最终返回前再检查资源与时间。资源门失败禁止生成 accepted receipt；已创建的 durable intent 与 one-shot 根保留，不能重试。collector 返回丢失仍为调用数 unknown。

## 验证与边界

验收覆盖无效/超限初始测量、native 返回后超限、序列化后超限、完整 plan 导致 core 超限、重新编码资源和计时篡改，以及原来源、计划、持久监督、失败窗口和 transport 身份测试。另用短合成来源执行真实 execute→audit 子进程链。

working-set 是采样的进程历史峰值检查；Job commit 是不同资源约束。二者均不使历史测量获得外部真实性认证。`resource_measurements_authenticated`、`whole_task_resources_verified`、`native_execution_authenticated`、exact 数学认证、安全认证、正式结果及 resume authority 均保持 false。此修复不关闭完整服务、capacity、training/holdout 或全支持资源门。
