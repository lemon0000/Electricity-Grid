# F：full-context role 八组机制修补设计

2026-10-29，DRAFT_NONAUTHORITATIVE。接续 [原 WIP 交接](continuation_handoff_20261029_saved_fresh_full_context_role_wip_v1.md)及[完整成本检查点](continuation_handoff_20261029_saved_fresh_whole_workflow_cost_v1.md)。root 唯一 writer，独立代理只读 PRE_SEAL。范围是关闭真实入口的 role engine 与合成失败窗口；完整 F 仍未完成。

## 可证范围与 effect 限定

原 runtime 的 `_invoke/_mechanical_binding/_cleanup_call/_new_session/_time/_entry` 六个首部无条件拒绝和 public `bind_full_role` 均保留。测试读取原 source，逐项确认六个 AST Raise，只在私有内存副本去除这些 Raise，并禁用副本 `current()`。登记 original source pin、精确变换名、变换后 clone pin、固定无 import fixture 文本 SHA。副本的 targets 只能来自该 fixture 唯一 namespace、固定 CodeType 集合、同一个合成 owner、固定合成 clock 和实际捕获的 cleanup packet 身份白名单。原文件不能通过测试副本得到生产能力。

fixture 只改变内存中的 SimpleNamespace、列表、规范 JSON 和异常。无项目 target import、P1 内容读取、Native owner、OwnedChild、Job、模型或 solver；每个 fixture 含一个纯内存 child 对象，不创建 child 进程。唯一新增进程是普通 unittest runner。窗口计数是宏操作 witness，不能当作 P1 物理读量或权限证明。合成 parent/fresh 使用各自 Fixture；不声称运行真实独立 B/C/E。

## 八组验收与实现

| 组 | 修补与可核验问题 | 固定普通测试 |
|---|---|---|
| 1 authority | 原七门均先拒绝；副本拒绝外来 target namespace/owner；副本 provenance 独立 | 01–02 |
| 2 role/context/launch | 同 owner/role/context proof；receipt 精确字段；closed request；拒绝早于 context 的 outer deadline，防止 child 获得更晚时钟 | 05–07 |
| 3 partial launch | create 原结果先保留；capture_failed 同时接收原 primary 与 create result；空 capture 进入恢复；unknown child 不推断 quiet | 08–10 |
| 4 cleanup drift | 同 namespace helper CodeType 克隆进独立 globals；packet 自身镜像逐次检查；probe 故障仍 abort/recheck；区分预期 carrier 与 secondary | 11–14 |
| 5 reentry | callback 吞下递归异常后仍 sticky；包括 cleanup 期间 reentry，关闭后不能返回成功 | 15–16 |
| 6 physical returns | replay/G3/quiet identity/observation/output 在 JSON、比较或 commit 前强持；失败保留原结果、raw/pin 与已提交阶段 | 17–20 |
| 7 sticky registry | 操作前及返回后核 exact row/image；自有 owner 仍只清理一次；foreign active/terminal 不覆盖；构造/发布/fingerprint/physical-image 故障走 primitive emergency | 21–23 |
| 8 window dispatch | 固定 CodeType；runner/closure globals 镜像；不调用可替换 class switch/launch/setattr；乱序拒绝且不可重试 | 24–26 |

资源终态拆为 `_runtime_closed`、`_child_terminal`，`_closed` 只在两者都成立时为 true。已返回 child 丢失或 recovery 未成功时保留 unresolved，不能凭 runtime resource CLOSED 推断全部关闭。成功才释放 binding/held/child/大返回对象；失败保留会话与原事实。

cleanup helper 克隆仅隔离函数 metadata 漂移；context 中可变对象、class/helper 的完整 Native 依赖图等价仍未证明。packet 自身损坏时先拒绝，原 Native owner 关闭不能保证，必须保留 unresolved。真实 approved entry/argv/channel 认证、外部 full context、audit hook、source-specific launcher/quiet、Guard2/Permission2、exact graph/profile/anchor 仍 OPEN，必须用后续实际来源 successor 完成。

## 原 F 的义务继续适用

完整 F 的双侧独立 21 点、五小时/130 CAS、19 metrics、两层 quiet、17 targets、四份 128KiB reserve、180s 原单一绝对时钟与 P1 12500/source 6500 帽保持。静态条件算式 `12159/12053` 仍是待证明复用条件；本次不解决整链 source/P1/resource 准入，不构成性能审查。所有 actual_F、saved_P1 adopted、run/science/resource/formal/production seal 字段继续 false。

具体次数、继承集合、失败会计和预算见[验证 scope](staged_deliverability_c_saved_fresh_full_context_role_scope_v1.md)。登记后修改须保留旧包及费用，进入独立 successor；NFC12 只复用既有证据。
