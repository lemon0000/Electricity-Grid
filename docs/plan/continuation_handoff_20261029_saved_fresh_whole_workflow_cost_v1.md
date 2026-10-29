# F：完整工作流成本检查点与整合实施入口

2026-10-29，DRAFT_NONAUTHORITATIVE。接续 [Parent40](continuation_handoff_20261029_saved_fresh_complete_parent_v2.md)。宽 goal「持续推进」保持 active，完整 F 未完成。本轮将原完整 F0–F6、双侧 B/C/E 和局部 runtime/Parent 叠加成本写成可核验静态模型，发现 P1 与 source 两项预算缺口；完成唯一16项普通测试、独立只读 PRE_SEAL、saved 原流回放与 checkpoint。root 唯一 writer，无 official verdict、receipt 或 production seal。

## 当前实现与实质发现

- [完整 DAG/成本/授权设计](staged_deliverability_c_saved_fresh_whole_workflow_cost_design_v1.md)、[静态模型](../../experiments/staged_rts24_saved_fresh_workflow_cost_model_v1.py)和[验证合同](staged_deliverability_c_saved_fresh_whole_workflow_cost_scope_v1.md)已冻结。模型绑定20份实际source/spec/旧计数证据，42个函数AST witness；只读/解析目标，不执行目标。
- 完整 F 仍是 parent 与新鲜进程各自独立重建原21点、五小时和130 CAS，比较完整19metrics；两层真实quiet、F.G0–G3、17targets、四份128KiB记录预留、180s单一绝对时钟保持。Parent40 叶片不能代替完整 F。
- 一个 Parent40 条件成功叶片需要14个input_context：7 discovery、4 import、3 producer；generic call内部435、outer wrappers后437，program内部6/含outer7。内部逻辑内容读1332+7D，外部Parent源原字节再加1。D为startup disk文件数0..128/合计32MiB，D=128时仅该部分重读224MiB。它不是P1的683文件。
- receipt核验明确区分open_saved_receipt调用22、物理JSON decode44；child decode调用23。Parent packet物理restore2/decode3/decompress1，不能只报顶层restore callback1。
- LC6叶片entry23/runtime entry29/source bookend24；Helper7完整runtime entry13（前置8+五操作5），局部LC+Helper合计42，Project37 build31（capture1+check30）。Loader/Core/科学回调/其他进程成本仍另计，graph停止帽不等于exact成功图。

## 两项整链预算缺口

原每侧E成功P1读4319=683初始库存+2152单点+801journal+683最终库存；两侧加四次F库存为11370。LC6为2102=53expectation+3×683。原12500帽保持。

| 条件附加场景（未计额外未知费用） | P1逻辑读 | 超12500 |
|---|---:|---:|
| 原完整路径+1LC+独立Parent683 | 14155 | 1655 |
| 原完整路径+2LC+独立Parent683 | 16257 | 3757 |
| 1LC：两项同owner/同窗口库存复用 | 12789 | 289 |
| 1LC：再证明Parent683与同次F库存为同一物理读 | 12106 | 算术余394 |
| 2LC：各复用hold/E final，再共享一次Parent/F库存 | 12842 | 342 |

复用尚未实现，不能用同名G、相同SHA或历史pins抵扣；必须证明同一个live HeldInput/owner/thread、source/root/anchor/caller image、同一次物理读、同一authority/window与完整失败证据。LC.G*与F.G*不同；E/Parent窗口另列。原adapter replay异常catch再做683库存，另有partial reads，失败上界未知。

source/exe/runtime也有缺口：Parent严格子集1191+7D、LC24×49=1176；若保留原两侧4176路径并独立附加，一个LC为 **6543+7D**，D=0已超6500帽43；两个LC为 **7719+7D**。另列source-control14（分类未定）和旧anchor末次2，其他loaded-module/授权/profile/outer/failure/publication成本未闭合。这里是未整合的条件加总，不能宣称未来实现的绝对下界；未知完整上界仍null，所有场景admitted=false。

## 验证与保存证据

[16项测试](../../tests/test_staged_rts24_saved_fresh_workflow_cost_model_v1.py)只执行一次，**16/16、0 failure/error/skip**。runner **1.024s**，受控unit阶段 **4.742344400001457/12s**；34个canonical帧逐nodeid配对，stdout **5148B**、stderr **2638B**，rc=0/capture_error=null，无kill/truncation/reader/cleanup，HANDLE/pipes/readers终态。仅一个ordinary unittest runner，0 toy children；真实项目Native owner、P1内容读取、Source49目标执行、角色/模型/solver均0，新增模拟跨度0h。旧23/70项和NFC12没有重跑。

测试包含独立历史上下文展开、P1与source虚拟read-event oracle、AST核嵌套packet/receipt解析、graph build/source读边数、严格literal/source集合故障、DAG缺阶段/乱序/自依赖、per-file/aggregate/type帽、budget不续期，以及report不exec/import项目目标/P1。它们支持静态模型和反例，不支持真实完整F资源/权限/科学结论。

195个健康native memory samples仅属于这个普通runner：parent peak **104714240B**、child peak **165347328B**，两者peak之和最大 **270061568B**、private和最大 **201244672B**。无超限；continuous_bound_verified/combined_retention_verified/resource_admission均false，不代表完整F或所有瞬时保留峰值。

独立只读reviewer登记前发现的两项must-fix（receipt物理decode命名、source帽条件叠加）已修入draft后冻结；终态核 **1420 inputs /265 archive/own9/20source/42witness**，pin_mismatches=0、must_fix_open=[]，仅PRE_SEAL。记录在[pre_seal.exit.json](../../results/tables/staged_rts24_saved_fresh_whole_workflow_cost_v1_non_authoritative/pre_seal.exit.json)。

## 最新账源与继承

root：`results/tables/staged_rts24_saved_fresh_whole_workflow_cost_v1_non_authoritative`，**6文件/835940B**。[checkpoint](../../results/tables/staged_rts24_saved_fresh_whole_workflow_cost_v1_non_authoritative/checkpoint.json) **10299B**，SHA **0ece179a28a3442e9406d1d3c372ea1e27f1376baf5608c734b41aafefc6a11a**。accepted/accounting_complete/diagnostic_accepted=true，acceptance_scope=`static_source_bound_DAG_and_conditional_arithmetic_only`。

各阶段各一次：register **2.0364475999958813s**、unit **4.742344400001457s**、pre_seal **1.7064524999877904s**、saved **1.8873947999964003s**、checkpoint **0.8752131000219379s**；本包 **11.247852400003467/40s**，static **6.50550800000201s**。原5/12/5/5/5阶段、child10s、static25/unit15/总40、capture128KiB/32KiB、process256MiB/pair512MiB、root10文件/4MiB、record1MiB/checkpoint reserve1MiB全部保持；余量不退款、不转用。

新累计账固定为：static **643.0030709000232s**、pytest **366.48897970000326s**、unittest **332.2220266999684s**，总 **1341.7140772999949s**；**52条不接受记录**保留，无新增拒绝。

当前registration **786087B / c2b5c82486bcf23a8e00f916ea1bc87c8034cd20150ead0642c5f0e7e40e95b0**，unit.exit **12978B / 581bc15d055286c04e2b12b7008273c9729f8d8cd98b24924067fe6e433ea71d**。模型 **23282B / 9f85b7c170b874c273c476b2055009b274768c6698108cea4dca6a8d5e03045a**，test **13487B / 8b93ef2566c001e24a21965e879be047af1fa798fb732147426c34387feb0cd1**。首次register后全部own字节不改。

当前input **1420/75167353B**，archive **265/30192073B**，own9：新model/test/design/scope/driver、Capture1/DRAIN1、补入的原invocation合同与旧E report；后两份保持既有发布字节。20份模型依赖均在exact input中。最终 **1712次pin比较/1512个唯一路径，bad=0**；原39项并行worktree SHA不变。

下一账源必须完整继承当前expanded1420加root6扣driver overlap1，精确 **1425 inputs**；archive **271/31028013B**。再显式union新own，逐pin核全部旧失败和charged/known记录；不能仅用Source49/NFC12子集。Source49 epoch仍 **acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875**，NFC12全16文件及CP **bbe4eaf6a67d5025db498bde68526c3fd2352e3a71edf05a21711505067b70de**保持。B1–B3、原P2七输入与所有旧失败/冻结工件不改。

## 下一步直接推进整合后继

1. **先固定真实完整连接与owner映射。** 明确parent/fresh各用哪些LC/adapter/Parent/outer/profile能力和回调，保持双侧独立B/C/E；不能为了落帽直接选择少一个LC。将上述P1/source缺口、typed pack/compile/import以及全部未知费用带入同一DAG。
2. **实现有证明的复用，处理两个帽。** Parent的actor-local HistoricalDependencyProof先完整核旧receipt/retirement/profile/manifest/admission/registration/source/env/exact graph/external anchor，可消除重复历史审计；capture/pre-release/post-quiet仍要新鲜物理内容和身份书挡。LC与E可在同一owner复用HeldInput、由同次E final inventory履行明确LC.G2义务，Parent683与F.G1共享必须是真实同一次物理读。每项均需版本化源、失败窗口与独立审查；两LC条件场景尚超342，不能自动提高12500或6500帽。
3. **连接真正授权和完整producer/science路径。** 使用既有Host/broker Job/mailbox/context先ACK再controller/parent/fresh的外部能力架构。为Permission/LC/Helper/Coordinator/replay/outer建立固定source/scope、实际child/argv/transport/manifest/context/deadline/nonce的一次性创建与消费；单独定义Parent P1 grant。Parent40仍只接post-spawn child；Permission1 public issue/verify/claim、Source49 legacy issuer及当前None profile/graph/anchor gates继续关闭，旧false schema不能填常量变成genuine许可。
4. **实际诊断前完成具体包与专项授权。** 普通测试和静态实现可继续；真实Native/P1/profile/graph/packet及完整F仍无运行准入。按agent.md §9核完整路径、合法复用和代表性成功/昂贵失败/收尾、全流程wall/RAM/storage及安全停止，再提出具体有界测量包。不要再以普通单元测试数或started run替代整链证据。

本次scoped Git仅发布新模型/测试/合同/设计、6个原流/账文件、本交接和四个导航前置段；四导航仅index使用「新前置段+旧HEAD正文」，原39项worktree字节原样保留。发布终态以remote hash、index与worktree现场读回为准。完整F与所有运行/资源/科学/formal gates保持false，宽goal继续active。
