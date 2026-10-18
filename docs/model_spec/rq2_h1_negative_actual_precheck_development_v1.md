# Handoff v3 的 missing-Actual 提前拒绝

状态：`DRAFT_NONAUTHORITATIVE`。本稿仅处理缺失 Actual 失败分支的重复重放成本，不授予 seal、review PASS、resource admission 或运行权限。

## 合同与实现边界

`experiments/h1_selector_phase_handoff_development_v3.py` 是 v2 的完整 versioned successor，继续使用原 Parent v2、CommonOwnerGenesis v2、phase/preview v2。唯一成功路径保持原 bundle/common guards、22 次 common observation、source/selector replay、回调、paired commit 和关闭重开要求。模型、业务映射、阈值和 unresolved 语义不变。

在 `consume()` 已取得自身 guard、建立 token 并标记 running 后，若存在 `None` Actual，先作一次充分拒绝检查。它临时取得原 reference guard，核对原 Parent shallow state、lease、creator/registry、issued object/bytes 和 terminal pin；随后重建 reference snapshot，按原 `_Bundle.records()` 中段完成 Rref sequence inspect、request/terminal/record/snapshot-pin 比较。基于同一 reference declaration 重建 manifest/binding、fresh current，并调用原 `_planned_bootstrap`，令所有 Actual prefix 为 `()`。

只有 exact lane roster 匹配、且某个 `None` lane 的 base disposition 既非 `business_input_unresolved` 也非 `business_unresolved` 时，才释放 reference guard 并抛出原 missing-Actual 异常。它不能接受请求、不缓存 hint、不生成 credential、不创建 handoff root/journal，也不调用 retention。无 `None` 时完全跳过；合法 unresolved 继续原完整 consume。

仅纯结构不适用条件可以继续原路径。任何新增 source/read/inspect/fresh/preview/guard 观察异常都必须传播，终止本次 attempt；不能捕获一次性错误后再跑原路径。初稿 broad Exception fallback 会吞掉消费型故障，已由 PRE_SEAL 发现并移除。

## 必须明确的差异

这是新的 negative sufficient-rejection window。它不保持 v2 在复合故障下的首个错误或锁轨迹：例如 present Actual 已损坏、另一 lane 缺失时，新版本可能先报 missing Actual。正常成功请求仍必须经过全部原检查；不能将该版本描述为所有 validation windows 与 v2 逐项相同。跨额外观察窗口的外部 change-and-restore 也不具有透明性保证。

## 验收出口

- 同一 v3 同时覆盖 missing-all、三个 missing-one、完整三 Actual paired commit 和关闭重开重放；不得把成功分支路由回 v2。
- 两类合法 business-unresolved 的 `None` 必须保留原路径并成功；不能只凭 `None` 或 manifest 拒绝。
- one-shot snapshot、sequence、fresh、preview 故障必须 fail-closed，不能通过第二次原路径消耗故障；reference/token/owner guards、single-attempt 与零持久化必须核对。
- malformed roster、替换 receipt、Rref/source/record pin 变化及其他失败窗口沿原错误或更早失败处理；不得产生新接受结果。
- targeted 和相关故障回归、同包代表性 timing、source/tested-byte/process/root 检查及独立 PRE_SEAL 复核完成后，才能纳入完整链性能审查。

unit 中显式 source/native/Job/Parent aliases 只证明对应实现与状态机行为；它们不替代完整三 N0、真实 common、Rref/Actual、paired、reopen 的 M2 出口。完整成功路径的 operation witness 接线仍是单独的开放项。
