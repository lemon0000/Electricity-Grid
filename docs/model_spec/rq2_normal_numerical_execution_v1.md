# Normal 数值执行、持久监督与完整计划归档 v1

候选开发期为 DRAFT_NONAUTHORITATIVE，封存与独立审查由 outer/receipt 记录。
本路径消费已授权且已独立审查的 normal 数值验收及来源投影，不改变目标、约束或容差。

## 执行与计划

NumericalNormalRequest 显式绑定原 ScaleNormalSourceRequest、发出计划的信息声明及数值记录大小限额。
来源、solver options、模型规模和完整任务资源计划沿用现有验证；声明必须不晚于 incoming boundary。
求解前后核对来源与实现，使用通用 solve_once 最多调用一次求解器。collector 抛出异常时调用数保持
unknown，不能据此写成零调用、不可行或自动重试。取得记录后，复用已封存的来源投影组件，保留
原生数值记录、完整 encoded prepared plan、投影报告及其外部绑定，三者在独立回放时逐字节重建。
未通过数值验收时不发布 accepted plan；超时与无 incumbent 继续保持 unresolved。

replay_information 向调用者返回审计报告与重新构造的 typed prepared plan；audit_source 提供
适用于持久 worker receipt 的报告。策略侧仍通过既有 current-hour information 接口获得信息。
发出计划时采用的 forecast、初态和功率映射继续是机制假设。

## 持久执行与监督

transport、worker、controller 使用新的固定类型与 schema，旧路径保持原有 bytes。
worker 先写 durable intent 再进入数值采集；执行根目录为 one-shot，不能重用或恢复。
controller 沿用原 Job 监督、完整预算、release 前 intent/launch 持久化、进程身份和 quiet 检查、
来源文件身份与 hash 检查，以及 audit/final publication 期间持有 evidence lease 的规则。
审计子进程和父进程重放都禁用新旧全部求解入口；审计 receipt 须与父进程独立重建结果逐字节相同。
未归档的返回、持久化失败、source 漂移或进程失败均不能进入成功终态。

完整预算仍按一次 native normal 调用及 execute/audit/controller 开销预留。数值记录限额受既有
core payload 分配约束，外层 archive/receipt/tree/scratch 继续受原有上限约束；不得用观测到的
较短时间自动缩减未完成任务的预留量。

## 验收范围

验证包含短合成求解、持久 execute→audit 进程链、来源与实现漂移、错 pin/类型、完整计划和
报告篡改、missing return、durable failure、文件替换、guard 恢复及旧链回归。
实际短进程例只能证明这一基础设施路径的执行和回放行为，不证明公开数据全支持可计算性。
native 历史执行真实性、完整资源认证、exact 数学认证、安全认证、正式结果和 resume authority
保持 false。完整服务合同、capacity、training/holdout 和完整正式 runner 的跨阶段绑定仍需验收。
