# Retained registry reader 的最小组合设计

状态：DRAFT_NONAUTHORITATIVE。独立只读审计确认此组合具备可行切口；尚未实现、尚未完成真实 own-root 差分或整链验收。root 为唯一 writer。依据见 `retained_registry_multiplier_audit_01.json`。

## 保留科学内核

保留 Bootstrap4、Owned4、verifier3 的当前字节。新 consumer operation 将 `N0ValidationOperation(diagnostic_only=True, reuse_numerical_proof=True)` 作为 closure 内私有数值状态机；每个 root 独立 engine，Common window 固定10次 build，session attach window 固定2次 build。调用原始 `begin_build(None, 'build_001'...) -> prepare -> confirm_build`。不复制 verifier 的科学重放内核，不改旧 exact-type guards。

inner envelope 继续来自原 private token / exact operation。inner execution 原样保留 `diagnostic_owner_only=True`、`bootstrap_operation_bound=False`、`diagnostic_only=True`、`arm_label_authenticated=False`。这些字段不能改写。它们只构成 numerical kernel evidence；新 outer 的真实 consumer 绑定必须独立证明。不能用 inner diagnostic receipt 本身证明 consumer 身份。

inner engine/envelope/proof 不返回、不写入工件；允许把 execution/closed receipt 的纯bytes或SHA写进外层JSON，并明确其 non-authorizing kernel evidence 角色。关闭后的旧内核资源记录仍按 verifier3 的既有生命周期保留，但必须没有 live proof，不能恢复或跨窗消费。

## 独立读取与最小类型图

新增 versioned retained-registry reader。它对 exact Bootstrap4 owner 独立执行 global claim/release/normal-terminal 状态机、release journal/genesis/namespace交叉验证、N0 topology/lock/obligation/source观察、末尾全量重读。使用原受保护的 `_N0_body/_global_N0_body` 重建 retained terminal。prepared science 来自私有原v3 engine，新 consumer identity 只进入 outer receipt；旧 terminal 的v3 science metadata保持逐字一致。

不调用或注入 Bootstrap4 guarded `_build_N0_terminal`，也不借用 producer nonce。`_release_cross_reference`、`_observe_N0`及其原始 dependency routes 必须在新reader definition-time closure固定；不能只绑定module源码文件而漏掉运行时alias。

优先保持 exact Roster3 和现有journal：Common9/10私有 versioned scoped replay route机械重放 Roster3 的两遍 `_view/rows`，但使用独立 reader。这样无需更改Roster3公共观察语义、重封旧header或引入Bootstrap5。若以后需要把新reader纳入Roster公共合同，则使用自己的Roster4/schema/journal，不接管旧头。

## Window 与 authority

新outer每个window固定：exact roster、exact Bootstrap4、原三个consumer/roster/bootstrap guards及其held状态、creator process/thread、Bootstrap nonce必须为None、固定consumer caller/type/function、window种类、global/roster/bootstrap头、root/pins/slot/claim/release/local/global body关系和ordinal。

Common window的五次 replay、十次 registry traversal全部保留；attach window的一次 replay、两次 traversal全部保留。每次 begin/prepare/confirm 前后与return边界均检查上述绑定。不得跨Common、caller callback、journal write或session复用。调用者不能注入engine/envelope/registry dict，也不能选择扩大build上限。

新Common及Genesis/Handoff operation在cold definition时绑定固定route；运行时不能从caller传入任意check或callback来取得scope。bind/preload/rebind及代码/default/global/closure替换必须拒绝。外层只输出已认证的data view和自己的active/closed receipts，不把旧typed envelope交给Common。

任一outer或inner失败均sticky poison两层；finally独立尝试全部engine close，保留first failure，记录cleanup errors。成功关闭必须核验每root completed/confirmed builds精确等于10或2、proof cleared、所有原inner guards释放，并清除outer active slot与live引用。外层不释放由其调用者持有的三个guards；由对应consumer最终释放并直接断言。

## 必需验证

- 私有kernel状态机的首/中/尾计数、所有context保留；inner diagnostic字段不可改写。
- exact owner/caller、原guard、nonce、root/pin/slot/head/body、build ordinal漂移；foreign thread、nested/reentry、preload/rebind和route替换。
- first complete terminal body前不发布proof；inner成功而outer失败、cleanup first-error、多root中途失败、跨window proof及engine/envelope escape。
- 新reader与一次canonical Bootstrap4 `_registry()`在真实own-root上的逐字差分，原root工件/pins/locks保持；fake协议单元不能替代此项。
- 最终Common9/10与各自report/projector/receipt整合、Genesis/Handoff连接、paired commit、Post与close/reopen，继续独立验收。

理论registry full计数648仍需实测闭合；所有context保持23,232。该组合不改变模型、阈值、N0 history或任何formal/native/resource gate。
