# 下一段完整链的 typed successor 接线设计

状态：DRAFT_NONAUTHORITATIVE。root 唯一写入；独立只读 PRE_SEAL 设计核对已完成，未 seal、未执行本图、未打开正式门。旧 chain07 主体和已完成补验均复用。

当前 Bootstrap4 的类型与执行身份不能直接接进 Roster2/Common2。最小接线图为：

`Bootstrap4/Owned4/verifier3 -> Roster3 -> operation-independent scientific projector`

- Genesis：`witness7/source8/Common7 -> genesis routes2/adapter2 -> 原 Gen2 class`。witness7 静态指向 adapter2；原 witness5 静态指向 adapter1，不能换 alias 复用。
- Handoff：`witness6/source7/Common8 -> common validation4 + parent validation4 + post-negative3 -> Handoff6`。
- Snapshot2/Parent3 保留原类型；在 adapter 安装后 cold import，全部 owner 在 scope 退出前关闭，恢复后进程退出。
- helper、E2E 与 configured entry 需要对应后继。现有 Handoff5 验证只支持当前图，不能代替新图验收。

所有硬名成对更新：adapter2 的 route kernel/consumer list/external-finalizer 属性名，validation4 的 Handoff6 与 witness6/source7/Common8 pins，parent-validation4 的 `_HOST`，post-negative3 的 parent helper，helper/E2E/entry 的 allowlist 与 cold-import 顺序。当前 fake-host unit 的 Genesis 是显式 alias，不能由它推导 canonical Gen2 下 producer setup 与 consumer preload 次序已经正确；该入口次序仍需真实接线检查。

Roster3 必须接受 exact Bootstrap4 owner，拒绝 Bootstrap2；local terminal 以 Bootstrap4 `_N0_body` 的 exact keys/bytes 重建核对，global terminal 继续以 `_global_N0_body` 绑定 local head/body。分别核对 retained verifier3 schema/identity 与嵌套 legacy compatibility metadata。

两条 Common 路由的 active reports 含不同 schema、implementation、call limit 和执行计数，不能跨路由逐字比较。新增纯科学投影应包括 retained roots/heads/references/source bindings、historical/source2 science、decision/exogenous hashes、canonical arm/binding 与共同 science payload；排除 active route identity、session、call number/limit、counts、proof/cleanup 字段。

每条执行证据按 `own execution receipt -> own active validation report -> shared scientific projection SHA` 绑定。Genesis 持久化同一纯科学投影，adapter receipt 另存自身 active report/receipt；Handoff 对照纯科学投影，并另存自身 active report/receipt。合同明确 `genesis_and_handoff_scientific_projection_equal=true` 与 `genesis_and_handoff_operation_reports_equal=false`。

Bootstrap4 当前 local/global terminal 仅绑定 verifier3 identity/schema 与 compatibility metadata。`run()` 返回的 registry execution receipt 未进入 terminal hash；下游不能据此声称原 producer 实际执行计数。若未来必须传播该计数，需新增 producer-bound receipt 后继，不能靠外部 JSON 补成权威。

必须先补的有界证据：Roster3 类型与 shape 漂移拒绝；三层 retained/predecessor/active identity 独立漂移拒绝；Common7/Common8 同 science 投影相等而报告不同；Gen create/inspect/reopen；Handoff6 真正 22-call 对照；parent helper4/post-negative3 host 绑定；至少一个 completed-own-root genuine Common7 和一个 genuine Handoff6 probe。之后才固定整条调用 DAG 与预算。

整链 wall time/RAM/存储预算仍未知，旧 Handoff5 或 source-window 局部时间不作为新整链预测。全部新探针仍受 agent.md 第9节及独立运行权限约束。
