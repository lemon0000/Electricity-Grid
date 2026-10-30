# F：host Win32 源码准备与保存重放失败交接

2026-10-30，DRAFT_NONAUTHORITATIVE。承接 [host preentry v1](continuation_handoff_20261030_saved_fresh_host_preentry_v1.md)。持续推进 goal 保持 active，新增模拟跨度 0h；NFC12 未重跑，完整 F 未启动。本版已 terminal，修复必须进入独立后继。

本版完成 [Windows resource source](../../experiments/staged_rts24_saved_fresh_host_windows_resources_v1.py) 与 [Host v2](../../experiments/staged_rts24_saved_fresh_full_role_host_preentry_v2.py) 的准备。资源源码覆盖命名 mapping/mutex、非继承 HANDLE、Job-list suspended 创建、PROCESS_INFORMATION 恢复、header marker-last、resume/terminate、member generation、quiet 与逐资源 issued/witness 清理；Host v2 把资源根和未决责任接回原有协议。public constructor、open factory 和 mechanical issuer 仍关闭。[design](staged_deliverability_c_saved_fresh_host_windows_design_v1.md)、[scope](staged_deliverability_c_saved_fresh_host_windows_scope_v1.md) 保持冻结。

唯一普通 unit 为 **42/42，0 failure/error/skip**，20 个具名 fault cases；原 log 6239B / `c1e5abe598ecbcf79980ba6b4d05ddcdea41a169c90f986aa5af92fda1fbd322`，42 条 ok，`Ran 42 tests in 4.837s`。7 组 ctypes field AST 相等；独立 Win64 oracle 核 8 个 size 和 10 个 offset。测试器内部 4.837 秒与含输入核验的 unit 阶段 7.046250899991719 秒分别记录。仅私有 copy 去掉两个 mechanical 首 raise，其余源码 body 保持；DLL/clock 和注入故障为合成叶、ctypes buffer 为测试自建。无项目 Native API、P1 读取、Source49 模块或 validation/fixture/target child 执行；未执行 Native sampler、Capture1、DRAIN1 或连续 RSS 测量。未重跑前驱 46/99 方法。

独立只读 PRE_SEAL 在有限源码与私有合成 scope 内 must_fix_open=[]、official_review=false；fresh 核 1593 input、348 archive、15 own、8 source，1681 唯一物理路径，无 missing/mismatch。原 42 项并行工作及 NFC12 16 文件/1849773B 均保持。

随后 **saved 被拒绝**，trace 指向 [audit v1](../../experiments/staged_rts24_saved_fresh_host_windows_preparation_audit_v1.py) 的 `snapshot()==report`。源码 pins 未变；静态检查定位到不同解释器下 `ast.dump` 的空字段表示差异：已存 `_IO/_Startup/_Accounting` 摘要为 436/1585/721B，当前 C:\Python314 的默认表示为 428/1577/705B；显式 `show_empty=True` 可逐项复现已存摘要，其余四组相同。原阶段没有记录 executable/version，不能从旧记录反推其运行身份。后继须绑定解释器并显式保持完整 AST 字段，继续严格重放比较。失败后只执行 checkpoint，没有重试或改写冻结文件。

## 当前账源

[checkpoint](../../results/tables/staged_rts24_saved_fresh_host_windows_preparation_v1_non_authoritative/checkpoint.json)：14387B / `cf4d9b5edf15dac5dacc83da2366152eafbf865f0f6ea40dcf7fa5d01d58e6f4`，accepted/accounting_complete=true、diagnostic_accepted=false，scope 为 `rejection_metadata_only`。root7/932397B。

| 阶段 | charge 秒 | bytes | SHA256 |
|---|---:|---:|---|
| register | 4.067677500002901 | 865772 | `b5d2ba4407dcdd3f47ab8ff1be65d1773fb92522858dc6ce888ee25001e2c11b` |
| inspect | 2.335964600002626 | 4359 | `7c6eca8249fa5fb14d777e13148be752c6f8c622fe0c7569f5c3ce28deff78c4` |
| unit | 7.046250899991719 | 13198 | `851137544fdd7eb90db17fa63f3e1b32602593a1a99800caba8980b4196fedf3` |
| pre_seal | 2.152036199986469 | 8202 | `de48801a73a9116a354e2ff016a29a120fa626f9f9252db877f5e4dbcd556c4b` |
| saved（拒绝） | 1.0267654999915976 | 6340 | `e907146e7987f37d3a1c9ba8d83242465a782780042779d1e2073a88fff73840` |
| checkpoint | 0.5138903000042774 | 14387 | `cf4d9b5edf15dac5dacc83da2366152eafbf865f0f6ea40dcf7fa5d01d58e6f4` |

driver20139B / `454765e83b121eabcd689fe0f8bf4866decc91c65db12af90a409681069bea2e`。阶段帽5/6/35/10/8/5，static34+unit35=69秒；本包17.14258499997959秒。root10files/4MiB、record1MiB、CP预留1MiB/1slot保持。累计 static **755.0650378999883**、pytest **366.48897970000326**、unittest **449.31874729998526**，合计 **1570.8727648999768秒**，**62条不接受记录**，全部继承、不退款。这是已登记阶段费用，非协作墙钟或完整 F 耗时。

当前 input1593/91468769B、own15/238889B、archive348/44417283B。后继先取 input1593+root7−driver overlap1=**1599/92381027B**，archive348+root7=**355/45349680B**，再与新 own 做 exact union。本交接在本包登记后生成，后继使用时须显式纳入。

## 仍须保留的边界

Native-return 到首次 Python 标量 HANDLE 捕获窗口保持 OPEN；PROCESS_INFORMATION 已写输出可恢复的测试不覆盖该窗口。短命 Job member 未被保留时必须 UNRESOLVED，尚无接入 Host 的 completion-port/连续成员观测；瞬时 close witness 不构成防止地址/HANDLE 重用的永久证明。source-authenticated issuer/owner seal、真实 manifest/transport 文件 provider、broker acceptance/cancel、完整 context/Core profile/Guard2/parent-fresh launcher 仍待连接。全部 Native、resource admission、run authority、actual F、formal result 和 production seal 门保持 false。

完整 WIP、原八组修补、B1–B3、P2 原七输入、全部失败、原 Source49 epoch 与原 F 保持。原 F：双侧独立 B/C/E21 点 h−2..2、五 accepted 小时、130 CAS、19 metrics、17 targets；原180秒单时钟；P1 reads12500/source-runtime6500；8MiB/64files含四份 terminal512KiB/4slots；阶段10/45/40/5/5/15/5/10/15/15/15，成功165秒，失败只用原剩余额度。12159=`2*5055+3*683`及12053=`2*5002+3*683`仍只是条件 P1 算式。NFC12 CP21591B / `bbe4eaf6a67d5025db498bde68526c3fd2352e3a71edf05a21711505067b70de`保持。

下一步先修复静态重放并复用42方法证据；再推进实际 source provider 与完整入口的准备。真实 Native/P1/Source49 目标或完整 F 仍须具体方案、完整 DAG 和 wall/RSS/storage 预算及 agent.md 第9节专项授权。
