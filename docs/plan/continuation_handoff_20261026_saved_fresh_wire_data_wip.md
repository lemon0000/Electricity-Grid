# C：wire 数据实现中途交接（WIP，未跑pytest）

2026-10-26，DRAFT_NONAUTHORITATIVE。本交接为用户切换新对话保存；宽goal仍active，并非完成或暂停。最近完整协议合同检查点为 `cdcc931c9fee0939ec004e2f6de4aa380f663f80`，见[45域交接](continuation_handoff_20261026_saved_fresh_wire_contract.md)；本轮沿用[实施范围预算](staged_deliverability_c_saved_fresh_wire_data_scope_budget_v1.md)。root唯一writer，既有独立reviewer只读PRE_SEAL，没有official verdict/receipt/seal/run authority。

## 当前真实状态

ENTRY在旧CLI guard前追加512行、40个class/function symbol。已有固定五组contract SHA、只处理bytes的44B codec、45域私有shape/type匹配、immutable data对象/本征DAG和逐入边检查、header/handshake、projection/entry core及三个固定role wire-data API。所有auth、actual kernel/FS/clock/runtime/quiet/read/issuer/F/science/resource/formal flags恒false。四份本地basis只作声明，不进wire，不证明producer。原45/21 schema、Source49集合、旧定义AST、科学adapter和CLI guard AST保留。

**只做过AST parse/compile（不exec、不import生产模块）和4333路径/Source保全。** 没有新fixture、pytest、cold probe、实际角色或科学运行。此前480节点只属于已冻结旧Source；本轮当前执行0。startup join类名已定义，但公开验证函数尚未写，parent/fresh当前不能通过正常完整链构造。不能把已有函数声明称为整条协议已接通。

第一次wip_static_02发现本轮追加末尾多了一行无body的重复if，exit1/accepted=false；原source `67a7d62046a4ac667f2cf270b92f2b63fab82f42a9101ee6736bf91dfb443821` snapshot及完整stderr保留。删除重复行后wip_static_retry_03为exit0/accepted=true，旧guard AST重新相等。修正后ENTRY SHA `44d54e9250c030c8830addfcb87ad5e5f55251a0b7583eb7631d4c1c4edce569`；Source49-map epoch `6a0d1d2b97469dd4bcf0b456b7a050f01bf79ef996ce4504796d1f2b087ec712`。静态通过不证明模块可导入、功能正确或回归通过。

原baseline在生产源码编辑前保存，4333精确路径包括旧4290 + wire root41 + 两份外部新文档；Source49旧raw直接复用已保全的content-addressed snapshots。当前只修改ENTRY，tests和其他48个Source仍为原字节。检查入口/原records在 `results/tables/staged_rts24_saved_fresh_wire_data_v1_non_authoritative/checks_01`，读baseline.json、wip_snapshot.json和三个exit。

## 已用预算与恢复顺序

| 普通检查 | 终态 | charge秒 |
|---|---|---:|
| baseline_01 | accepted/0 | 3.2642644 |
| wip_static_02 | failed/1，语法错误 | 2.9809804 |
| wip_static_retry_03 | accepted/0，syntax only | 3.2110161 |
| 累计static | 含失败，≤120 | 9.4562609 |
| pytest | 未开始，≤420 | 0 |

预算跨会话保留：static余110.5437391、pytest余420，总540余530.5437391；不重置账。原剩余collection20/admission15/saved30/terminal30合计95，仍落原static内。旧480重分十组caps289，新smoke18+三组23=87，合计376，pytest留44失败余量。原计划先新smoke/其余新测试及审查，最终Source稳定后再跑旧480。

恢复先核Git/进程/实际draft字节，再补以下缺口：

1. 三个固定 `validate_saved_controller_startup_join_data` / parent / fresh，独立parent capture与child self proof、原owner声明/argv/header/descriptor/时序逐项join。
2. stage transcript及early failure，bootstrap first、逐phase序列、previous chain、absorbing terminal/error和16帧完整zero suffix。
3. 五类failure关系、JSONL预留/一次失败record，controller binding、两种return、constructor diagnostic。
4. 独立stdlib fixture、追加原tests、受控pytest_harness、exact collection/admission、saved oracle及完整封装。当前 `run.py` 的saved/terminal只预留路由，package checker/freeze支持尚不存在，**不可直接调用**。

`wip_snapshot.json`列11个缺失函数：三个startup join、`validate_saved_stage_transcript_data`、`validate_saved_stage_failure_data`、`validate_saved_wire_failure_data`、`compose_saved_failure_event_data`、`validate_saved_controller_binding_data`、`validate_saved_controller_return_data`、`validate_saved_broker_return_data`、`validate_saved_constructor_diagnostic_data`。

## 必须继续的审查点

- 节点visited仅去重本征校验；每条入边仍核type/field/id/commit/creator及同context，gray防环且成功后才done。需要别名边两种顺序、错误slot、cycle、首检异常后的反例。
- **高，未闭合：contract expected truth根。** 当前五组值保存在可重绑定的模块global `SAVED_WIRE_CONTRACT_PINS`，factory和entry都动态读取它；尚未证明同步替换global/registry/basis并重哈希仍拒绝。scope要求尚未达成，新上下文须固定不由调用方/运行时global替换决定的验证根并加反例，也不能宣称任意RAM沙箱已建立。context原类型没有creator，本轮不证明其来源。
- **高，未闭合：依赖image语义。** 当前 `_saved_wire_projections`把dependency `bootstrap_image_sha/G0_image_sha/hold_image_sha/store_image_sha`解释为对应projection canonical raw SHA；reviewer指出这会与packet既有projection-SHA重复并丢失依赖能力image链。应先决定按前一projection的`source_image_sha`等独立能力摘要连接，或建立versioned successor/改名以明确raw-SHA语义；不得静默重解释旧45域。bootstrap域没有`source_image_sha`也需明确处理，不能补造或把local object id跨进程当truth。`source_image_sha`本身仍只是caller独立opaque声明，完整runtime/issuer连接未实现。先解决此项与contract根，再补后续API。
- shape层command_line目前仅做字符串/总帽，startup join还需原25/19/19-token argv重建、list2cmdline一致性及对应上界。所有quiet/full-content声明均不授予读取/采用。
- 旧RoleStore/FileBootstrap/OwnerInputs/issuer/constructor继续拒绝这些data对象；三公开role API不替换成generic role权限入口。旧Source49历史map不能当作当前Source期望。

现场另有范围外文稿/文献改动：`paper/drafts/project_introduction.md`、`project_introduction_en.md`、`docs/literature/research_gap.md`、`introduction_reference_map_20261022.csv`，以及README的介绍正文。保持原样；共享README只将本轮WIP前置段暂存，工作区其他正文仍由并行修改保留。Git同步只覆盖已审本轮范围，不能报告全局工作区clean。新会话重新核实际dirty状态，不回滚或清理。

本次WIP checkpoint与syntax记录由Git逐blob承接，未建立完成版execution freeze/saved package。actual fresh、最终父端采用、整包科学采用、33根闭包/NumPy政策、source6500/180s、完整资源/硬停止均未完成，相关运行、资源、科学和正式门禁维持false。
