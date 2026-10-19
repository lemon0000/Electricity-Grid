# Consumer registry 历史重建调用量补充审计

状态：DRAFT_NONAUTHORITATIVE / PRE_SEAL findings。以当前 Common7/8 控制流机械延续到拟议 Common9/10 为条件，属于静态调用量审计；未执行 genuine 三臂图，未得到整链时间估计。本文补充 `typed_successor_graph_design_02.md`，旧文件字节保留。

## 遗漏的调用层

一次 Common `_prepare_locked` 调用五次 Roster `_replay`，每次 replay 调用两次 `_view`，每次 view 调用一次 Bootstrap4 `_registry`。每个 session attach 另调用一次 replay。若 C 为 Common calls、S 为独立 sessions、k 为已保留 local terminal 的 release 数，则：

- registry traversals = `10*C + 2*S`；
- foreign N0 prepares = `k*(10*C + 2*S)`；
- full / within = 各 `4*k*(10*C + 2*S)`；
- contexts = `16*k*(10*C + 2*S)`。

Bootstrap4 `_registry` 对每个此类 release 重建 N0 terminal。Common 阶段 bootstrap nonce 已清空，producer `RegistryValidationScope3` 不存在；即使持 owner guard，仍回退到逐次 full-only 验证。不能把持锁等同于持有 producer 数值证明。

| 三臂候选路径 | 47 calls / 7 sessions | 53 calls / 10 sessions |
| --- | ---: | ---: |
| foreign registry traversals | 484 | 550 |
| 遗漏的 foreign N0 prepares | 1,452 | 1,650 |
| 遗漏的 full / within，各 | 5,808 | 6,600 |
| 遗漏的 contexts | 23,232 | 26,400 |
| 加回 source wrapper 后 full / within，各 | 5,976 | 6,840 |
| source wrapper cross-common reuse | 1,920 | 2,064 |
| 加回 source wrapper 后 contexts | 27,744 | 31,488 |

以上仍未包含三臂 producer，以及 Roster create/attach/inspect/reopen。旧预算中的 `564/636 registry preparations` 属于 source wrapper 的另一项计数，不能替代这里的 foreign N0 prepares。91/拟议95的 empty-registry header 路径 k=0，不能测量本表的历史重建成本。

## 最小复用合同与实现前提

只在一次同步 Common 调用内保留 consumer-bound retained-registry 数值证明：每个 exact root 首次完整重建，其余九遍继续完整读取 terminal、执行 `_observe_N0`、检查所有 context 和 typed 结果，复用已确认数值证明。return 前销毁；不跨 Common、caller callback、journal write 或 session。session attach 的一次两遍 replay 使用独立小 scope。

该合同的 registry 理论 full / within 各为 `4*k*(C+S)`，reuse 为 `8*k*(9*C+S)`；contexts 和读取次数保持上述数值。

| 尚未实现的复用合同 | 47 / 7 / 3 | 53 / 10 / 3 |
| --- | ---: | ---: |
| registry full / within，各 | 648 | 756 |
| registry reuse | 10,320 | 11,688 |
| 加回 source wrapper 后 full / within，各 | 816 | 996 |
| 加回 source wrapper 后 reuse | 12,240 | 13,752 |

这些是设计目标，不是实测提速或已经实现的能力。还需证明单个 Common 内完整 dependency closure、freshness、失效条件和失败窗口，再确定实现切口；不得直接向 Bootstrap4 guarded route 注入 `registry_scope`，不得借 producer nonce、改旧 verifier exact-type 或以 diagnostic-only receipt 冒充 consumer receipt。

下一步需要单独 retained-reader operation、精确 Roster/Bootstrap guards 与 caller 绑定、root/pin 固定、build limit、首次完整 body commit、first/middle/tail 漂移及 nested/reentry/thread/cleanup/poison/proof-escape 测试，以及独立 PRE_SEAL 审查。不能缓存整个 registry dict，也不能从 saved JSON 恢复 live credential。

整体性能审查、genuine 优化整链与正式验收保持 OPEN。当前不重复83的四Parent前缀，不启动新的长整链。
