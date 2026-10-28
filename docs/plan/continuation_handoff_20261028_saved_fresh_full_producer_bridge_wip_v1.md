# F：完整 producer 桥接草稿交接

2026-10-28，DRAFT_NONAUTHORITATIVE。用户询问当前进度与是否需要新开对话，本检查点保存尚未执行的下一步，供新对话继续。宽 goal“持续推进计划”仍 active；完整 F 尚未完成。root 唯一 writer，既有 wire_root_review 只读 PRE_SEAL；没有 official verdict、receipt、production seal 或新增运行权限。

## 当前进度

原始 [20261026 WIP](continuation_handoff_20261026_saved_fresh_wire_data_wip.md) 指定的两项高风险已在[数据根修复检查点](continuation_handoff_20261026_saved_fresh_wire_data_root_repair.md)完成开发修复：contract 预期根固定在函数代码内；projection raw SHA 与独立能力 image 声明分开连接。其证据和边界属于当时冻结 epoch，不能外推任意 RAM 沙箱或真实 producer。后续 [wire 接口完成交接](continuation_handoff_20261026_saved_fresh_wire_completion.md)保留数据协议开发证据。

最近已执行并发布的完整检查点是 [NFC12 真实同一 LIVE owner 消费](continuation_handoff_20261028_saved_fresh_live_consumer_connected_v1.md)：同一 owner 完成 namespace/import、固定 ENTRY binding consumer、CONSUMED，再将 runtime/resource/boundary 全部关闭；38 图对、7 次 Source49 bookend、原 NF9 profile 逐字匹配、saved canonical replay 和 checkpoint 已通过。本轮补充 3 项配对测试通过，原 48 项仅复用冻结证据。consumer 返回原 adapter、same_live_owner=true、primary=null、secondary=[]、self close_calls=[1,1]。这证明 binding 消费连接；完整 producer 与父端科学采用仍 OPEN。

NFC12 已发布 commit：`1394fcdabed4c9c2e991afd24b9d0fcfef337cd6`。其 root 为 `results/tables/staged_rts24_saved_fresh_nfc_v12_non_authoritative`，16 文件、1849773B；checkpoint SHA `bbe4eaf6a67d5025db498bde68526c3fd2352e3a71edf05a21711505067b70de`。Source49 epoch 仍为 `acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875`。所有已执行 source/scope/input/result bytes 冻结；不重跑 NFC11/NFC12、不恢复旧 PID、不从关闭后的摘要重建能力。

## 本轮尚未执行的草稿

完整下一步必须是同一真实 LIVE owner 内：`expectation53 → context/check_context → adapter.hold(source, expectation.image) → HeldInput/caller-image 精确连接 → 强持到 G2/G3 → cleanup`。`adapter.capture()` 自己生成 image，不能代替外部 expected truth；当前 consume_once 在操作后关闭 runtime，也不能直接承担 G2/G3 retention。

本轮先写出 source-derived prebound expectation code，精确移除原函数内第二次 `_expectation_adapter(source)` 准备，新增显式 binding 参数和 derived 名称，保留其余读取、metadata、anchor、失败 bookend 与返回 AST。未来须使用原 ENTRY globals 和同一 LIVE owner 已强持的 binding；被移除 preparation 的 Source49 freshness、原 code/default/module、EXE/P1/SCOPE 与最后 source bookend 必须由完整 runtime plan 另行替代。

四个当前 draft 文件如下，均未登记，仍可按原 draft 规则修改：

- [scope](staged_deliverability_c_saved_fresh_full_producer_bridge_scope_v1.md)：static 25s、unit 15s、总 40s。
- [构造器](../../experiments/staged_rts24_saved_fresh_prebound_expectation_code_v1.py)：只读冻结源并生成 CodeType，不执行 Source49 目标模块或 P1。
- [4 项测试草稿](../../tests/test_staged_rts24_saved_fresh_prebound_expectation_code_v1.py)：源码连接、可逆性、漂移与 hostile AST、剩余 body/失败 bookend 保全。
- [控制器草稿](../../results/tables/staged_rts24_saved_fresh_full_producer_bridge_v1_non_authoritative/driver.py)：新 root 目前只有 driver.py，尚无 registration、unit exit、PRE_SEAL、saved 或 checkpoint。

**本轮没有运行上述 4 项测试，没有受控 register/unit/child，也没有 P1 读取或新 Source49 epoch。** 交接发布只做语法、链接、hash、Git 和进程检查，不把它们称为该 scope 的执行证据。

## PRE_SEAL 待处理

既有 reviewer 原提出 5 组执行前 must-fix；当前仍不能保存 `must_fix_open: []`。其第 1—4 组已有未验证的源码修补，不能宣称闭合：

1. 增加完整冻结 ENTRY raw 编译，唯一提取原函数 CodeType，核其与隔离 AST 编译相等，并记录 full-module root pin。
2. 核 binding 从 local cell 到 argument cell 的预期顺序；核嵌套 bookends freevars 与完整代码（仅规范化显式 derived filename/qualname）；禁止剩余 binding Store/Del。
3. source 前置赋值精确匹配 `source = parse(canonical(expected_sources))`；增加 RHS、walrus、loop target 和 delete 反例。
4. 将过强的“未执行项目模块”限定为未执行 Source49 目标模块，并明确 helper/tests 自身正常执行。

**第 5 组 controller 修复尚未实施，首次 register 前必须处理：**

- checkpoint 的 previous/replay/canonical 检查抛错时，当前 payload 可能为空，try 外再读取 scope usage 会丢失失败记录。需要安全、独立的 fallback，保存真实 charge、已知 pins 与错误；不能证明累计账时明确 accounting incomplete，不能捏造累计。
- 增加严格 phase prefix、前序 accepted 和拒绝后的停止条件，阻止失败后继续调用其他阶段。历史 39 的口径为受控不接受 **record 数**；reviewer 曾按 rejected package 解释，下一轮应先澄清，不能追溯改写旧账。
- archive 转 dict 后也要核路径唯一、精确 155 项、14350165B 和完整 set；registration/check 重建精确 archive/input set，并固定 effective_input_count 的预期关系，不能仅核当前 union 的动态长度或接受被删减的登记集合。

先完成第 5 组及必要反例，再对第 1—4 组当前修补和 controller 一并做只读 PRE_SEAL。不要将此 WIP Git 保存当作执行准入。首次受控登记会冻结实际执行字节；若后续失败，保留原 source、输入、原流和费用，按 successor 规则继续。

既有 wire_root_review 已独立只读核对本交接与当前草稿：未发现会误导接手者的文档 must-fix，并确认历史 39 为 record 数。该结论仅允许如实保存 WIP；上述代码 findings 尚未闭合，也不构成 scope PRE_SEAL 通过。

## 预算与失败保留

NFC12 结束后累计 static `529.8727752999941s`、pytest `366.48897970000326s`、unittest `192.63093869999648s`，总 `1088.9926936999939s`；受控不接受 39 条。历史 archive 155 文件、14350165B 原样保留，NFC11 manifest 失败、工程超帽候选、所有旧预算和未用余量不退款、不重置、不转用。上述累计是受控 capture 费用，不是工程编辑、审查和 Git 的全部墙钟时间。

新 bridge scope 尚未登记，已用受控费用 0，预留 static25/unit15/总40s。拟定 register5、unit10、PRE_SEAL5、saved5、checkpoint5，另有 static5/unit5 同包失败保存余量；必须先核完整失败保存和性能预算。root 上限 10 文件/4MiB、单 record 1MiB。unit 子进程拟复用 sampled capture 的 8s child wall、stdout128KiB/stderr32KiB、256MiB/process 与 512MiB/pair 采样停止带；这不证明连续/descendant/128MiB retention。

实际 producer 的 I/O 也尚未执行：expectation53 与 G0 full hold 共 736 次 P1 内容读；再加一次 full bookend 为 1419；原 controller G0/G2/G3 为 2102。Source49、fixture、外部 case、runtime bookend 及 replay 自带 bookend 另计。完整闭包、retained owner、33 legacy roots 的 replacement、父端采用、资源与科学门禁仍有后续工作；本轮新增模拟跨度 0h。

## 恢复顺序与当前现场

1. 先读本交接、NFC12 交接、当前 scope，再核 `agent.md` 第 7—9 节、执行计划和 blocker；按需阅读原数据根修复记录，复用未变上下文。
2. 核 Git、进程、四份 draft 实际字节和 NFC12/Source49 pins。当前没有研究 child、solver 或测试任务运行；进程检查只见 VS Code Jedi language server。历史 PID 仅作证据。
3. 先修 controller 第 5 组，再验证现有四组修补、更新 meaningful tests/节点/预算并完成只读 PRE_SEAL；随后才按已授权开发范围登记并做一次普通 unit、saved、checkpoint，失败原样保存。
4. 此 bridge 即使通过，也只证明一个必要的源码连接。后续仍须完整 producer closure、context、HeldInput、G2/G3 retention、父端 reopen replay 和全路径 wall/RAM/storage 准入。P1/actual role/native 校准/模型/solver/长实验遵守各自既有授权边界。

所有 producer/full-P1/full-runtime/role/permit/OwnedChild/Job/独立 TCB/资源/科学/正式/run/F 权限仍 false 或 OPEN。Git 同步只保存本轮 WIP 和导航前置段，不打开上述 gate。

现场有 39 项并行论文、插图、文献 dirty（35 tracked、4 untracked），必须保持原字节。四个共享导航只发布“本轮前置段＋原 HEAD 正文”，工作区保留其余 dirty 正文。Git 提交本 WIP 后仍应有这 39 项，index 为空、本轮自有范围 clean；最终提交与远端 hash 以实际同步读回为准。预算和失败记录跨新对话保留。
