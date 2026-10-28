# F：held bridge 的封闭 builtins 后继

2026-10-29，DRAFT_NONAUTHORITATIVE，登记前草稿。root 唯一 writer，retained_lifecycle_review 只读 PRE_SEAL。完整目标、36-node 矩阵及资源/权限边界沿用[整体合同](staged_deliverability_c_saved_fresh_producer_bootstrap_scope_v1.md)与[完整集合合同](staged_deliverability_c_saved_fresh_producer_bootstrap_scope_v5.md)。

v5 register 接受 0.9906872999854386s；unit 拒绝 5.14706080002361s，36 项中 35 项通过，最后一项在空 builtins 的 held bridge 中因 tuple 未捕获而 NameError。child 已终止，handle/pipes/readers 关闭，无 kill、截断或 reader error。checkpoint 27b800b508deefe082702d2791dd603c0ad03fc8852880cb5e0c042eb51bcd64，4 文件 716877B，包费 6.657212100020843s，原记录及已登记输入冻结。

本后继 B_S v4 只把 tuple 加入 project_bridge_call 的 definition-time defaults，并改为局部 _tuple；tests v4 对同一 36-node suite 增加该 CodeType 无全局名字、错误 spec 在空 builtins 中明确拒绝的断言。原三处接点仍使用 held CodeType/defaults/spec；helper v2、graph v3 与 lifecycle v2 完全复用。B_S 本体只编译和抽取三个 call 表达式，不执行真实 Source49 模块。

controller 固定上述 v5 checkpoint 与其完整 accepted registration，另固定 v4 checkpoint 及其完整 registration payload：1249 inputs 加 v4 root3 得到 1251，加入 v5 own12 后须逐项等于 v5 的 1253 inputs；192 archive 加 v4 root3 须逐项等于 v5 的 195 archive。再加入 v5 root4，得到本包 inherited1256、archive199 文件/20212912B。自身12、重叠8，精确1260 inputs；全部唯一 live 文件仍逐一 hash，pin 冲突、集合差异、alias 或固定 anchor 变化均拒绝。登记前同 v5.previous()+v5 own/root 的独立机械结果逐项核对。

账源累计 static588.3119816000501、pytest366.48897970000326、unittest251.215137900017，总1206.0160992000704s，不接受46条。本包自身0，未登记；旧费用/失败保留，不退款、重置或转用。

DAG 为 register → 唯一36-node unit → 独立 PRE_SEAL 保存 → saved → checkpoint → Git；失败立即终止并保全。预算仍 static25/unit15/总40s，阶段5/10/5/5/5s；child8s、-B/-s/-S、stdout128KiB/stderr32KiB、256MiB/process 与512MiB/pair sampled、root10文件/4MiB、record1MiB 且预留checkpoint1MiB，均不扩大。

没有真实37模块/Source49目标模块、P1、issuer、角色、native校准、模型或solver执行权限。旧NFC12和Source49保持冻结；Core/probe/parent/manifest/profile/40图帽后继、真实兼容性与初始化来源、父端reopen、128MiB retention、whole workflow 和完整F仍OPEN。普通合成接受不能关闭这些门禁。
