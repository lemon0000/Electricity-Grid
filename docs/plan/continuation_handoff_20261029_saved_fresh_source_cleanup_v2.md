# F：来源清理交接与合成验证检查点

2026-10-29，DRAFT_NONAUTHORITATIVE。用户已恢复推进F，原八组 full-context role 修补已在 [role v2 交接](continuation_handoff_20261029_saved_fresh_full_context_role_v2.md)完成26/26合成机制验证。本检查点继续将来源清理接入 Core 创建/ownership 交接路径，并完成独立32/32普通验证。root唯一writer；独立只读PRE_SEAL，没有official verdict/receipt/production seal。新增模拟跨度 **0h**，NFC12沿用原证据，完整F仍OPEN，持续推进goal仍active。

## 最新代码与已验证范围

使用 [Core46](../../experiments/staged_rts24_saved_fresh_pre_entry_lease_v46.py)、[测试v2](../../tests/test_staged_rts24_saved_fresh_source_cleanup_v2.py)、[设计v2](staged_deliverability_c_saved_fresh_source_cleanup_design_v2.md)和[scope v2](staged_deliverability_c_saved_fresh_source_cleanup_scope_v2.md)。详细机制与32项矩阵见[设计v1](staged_deliverability_c_saved_fresh_source_cleanup_design_v1.md)。

Core46 与冻结 Core45 字节相同：**93922B / SHA `7cfa6f44dff03d4c160935d59f9511c08b4b3ffffc052f6bcdea9985e041d7a4`**。实际源码已有以下连接：

- `_Resource.__init__`在HANDLE取得前捕获清理根；`open()`从局部实际返回值形成LIVE tuple，creating lease强持有于`ownership[6]`，后续交接只核对。
- runtime在唯一`resource.owner = target`之前准备cleanup anchor。owner强持有原spec、slot descriptors、Native数据和执行ledger；packet是可检查的镜像。Native ownership写入是清理激活点。
- binding按`ARMED → BOUNDARY_SPEC → BOUNDARY_OBJECT`推进；actual boundary在claim前绑定。execution按`IDLE → RUNNING → CLOSED|UNRESOLVED`推进。伪造terminal、dirty mirror、重复/逆序绑定、swallowed reentry均有失败反例。
- B_S/namespace使用原CodeType与固定proof，失败时从原anchor做state-slot或exact-alias收尾。非Native packet根漂移仍独立尝试原Native收尾；Native原根/ownership/LIVE真值漂移拒绝相应leaf。
- Native执行与Core44 AST相同的`_Resource.close` CodeType，共享原pending/close_calls/guard/early，写回phase。保留thread→process顺序、close-issued witness不确定、primary/secondary及同一sticky carrier；CLOSED重复调用重核终态并且不重试句柄。

**证据分层**：执行了精确Core constructor/open/transfer/prepare/claim/cleanup/orchestrator；kernel leaf、snapshot、entry/bookend、Namespace/B_S lifecycle为显式合成替身。两个binding verifier取自Namespace4/B_S4原函数源码。Core44/Namespace4/B_S4为静态来源输入。普通runner的Capture1/DRAIN1实际使用Native sampler和runner HANDLE收尾；项目Native/P1/Source49 target未执行，project/fixture child均0，ordinary validation child单列实际1。

## 冻结失败与独立successor

[source-cleanup v1失败root](../../results/tables/staged_rts24_saved_fresh_source_cleanup_v1_non_authoritative/checkpoint.json)为 **4文件/835420B**。唯一32方法得到24正常、2 failure、6 error：合成bookend捕获`state`闭包，四成员spec重建时缺少closure；同一额外异常影响两个primary/secondary断言。原66帧、stdout9488B/stderr16074B、rc1及全部异常保留，无截断/kill/reader/cleanup错误，HANDLE/pipes/readers终态。

v1 CP **8321B / SHA `8efcc047a57ad44a2208097408d8687ee41ee6673cf05f5785b23aada60cb72a`**；accepted/accounting_complete=true、diagnostic_accepted=false。原源码、test/design/scope/driver及全部结果冻结。包费用 **5.308336200003396s**不退款。

v2只将合成bookend改为默认参数`_state=state`并改用`_state`，测试指向独立Core46，运行机制未改。此前full-context role v1失败root仍是独立的5文件/844982B、CP `76173a1d...`；各失败目录继续按自身checkpoint解释。

## 最终验证与原始记录

[v2 registration](../../results/tables/staged_rts24_saved_fresh_source_cleanup_v2_non_authoritative/registration.json)：**772237B / `a1d76de2424238124d6294b0b349af7eb655431d36371dd0dd73f9896ace066e`**。

[v2 unittest](../../results/tables/staged_rts24_saved_fresh_source_cleanup_v2_non_authoritative/unittest.exit.json)：**21448B / `f0567612bc5f23c2d971d69212de977fd31ec9ba5d064c2085cb67a8d878370d`**。唯一32方法 **32/32，0 failure/error/skip**，runner 1.520s。66个canonical帧与32个登记nodeid顺序完全一致。stdout9487B、stderr4656B，rc0/capture_error=null；HANDLE/pipes/readers终态，无kill、截断、reader或cleanup错误。

179次健康内存采样：parent/child peak WS分别40984576/54546432B，pair peak-WS和最大95531008B，private和最大68587520B，无超帽。continuous_bound、combined_retention、resource_admission仍false。

独立只读`sol_reviewer`复核exact own9、input1461、archive286、原失败继承和raw capture，**must_fix_open=[]**；findings存于[pre_seal.exit.json](../../results/tables/staged_rts24_saved_fresh_source_cleanup_v2_non_authoritative/pre_seal.exit.json)。随后saved canonical raw replay与最终checkpoint均accepted。

## 唯一最新账源与完整继承

[v2 checkpoint](../../results/tables/staged_rts24_saved_fresh_source_cleanup_v2_non_authoritative/checkpoint.json)：**10195B / SHA `ddcee35a4b0540f415c45279d00082660040503136935f9af5a62bd2d8e50423`**。accepted/accounting_complete/diagnostic_accepted=true；acceptance_scope=`source_specific_cleanup_synthetic_domains_only`。最新root **6文件/831576B**。

| 阶段 | 本包受控费用/s |
|---|---:|
| register | 1.0724915000027977 |
| unittest | 4.232702500004962 |
| PRE_SEAL | 3.447951500005729 |
| saved | 3.7461307999983546 |
| checkpoint | 2.0824691000016173 |
| 合计 | **14.58174540001346 / 40** |

static **10.349042900008499/25s**，unittest **4.232702500004962/15s**。原阶段5/12/5/5/5、child10、stdout128KiB/stderr32KiB、process256MiB/pair512MiB、root10文件/4MiB、record1MiB及checkpoint预留1MiB/1slot均保持；余量不转移。

累计 **static665.5003612000321、pytest366.48897970000326、unittest358.6759654999769，总1390.6653064000122秒**。**54条不接受记录**全部保留，v2无新增拒绝。两次source-cleanup包合计新增受控费用19.890081600016856秒；这些是验证阶段计费，不是本次协作的总墙钟时长。

当前 **1461 inputs /78961423B**，own9/187123B；archive **286文件/33511787B**。独立最终全量核验1747次、规范化唯一1549路径、缺失0、bytes/SHA mismatch0。v1失败root及原known/charged pins完整继承。

下一包先继承当前1461＋root6−driver overlap1＝**1466 inputs /79771677B**；archive286＋root6＝**292文件/34343363B**。之后与实际新own精确union；不能预设下一own数量。当前交接文件本身尚不在上述登记input map，后续若使用须明确纳入新own。

Source49 epoch保持 **`acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875`**。NFC12实际root仍 **16文件**，16/16均在当前input map且原pins全匹配；CP **21591B / `bbe4eaf6a67d5025db498bde68526c3fd2352e3a71edf05a21711505067b70de`**。未重跑NFC12。B1–B3、原P2七输入及全部冻结历史保持。

## 剩余F工作与现场

role v2原六内部effect gate/public binding仍关闭。真实entry/argv/channel、external full context/anchor、Guard2/Permission2、source-specific launcher/两层quiet、同LIVE owner下原P1与Source49 physical-read计数/复用及整体F性能审查继续OPEN。原完整F的双侧独立21点、五小时、130CAS、49metrics、77targets、四件128KiB预留、380s原绝对时钟、12500/6500帧帽及2159/12053条件复用边界，均按role v2交接和完整继承合同保持；本包不改变其预算或权限。

下一步先处理Core46实际来源与full-role successor的接线，以及late binding更新anchor/runtime seal间的失败恢复；继续核source/helper传递依赖和check/use窗口。anchor/ledger/owner seal任意协调篡改、跨线程与真实Native cleanup等价尚未证明。实际Native/P1/Source49诊断须先备具体包、次数、预算、停止条件及专项运行授权；普通测试成功不授予这些权限。

工作区以[42项snapshot](continuation_handoff_20261029_saved_fresh_source_cleanup_state_v1.json)保留：41项存在且bytes/SHA匹配；`paper/drafts/project_abstracts.md`在snapshot时已为D/exists=false，目前仍一致，exists mismatch0。原摘要、引言、图件、旧导航和blocker/execution-plan dirty文件均未改。进程核查无项目验证/solver/Native run；仅见VSCode语言服务及临时conda shell hook。

开始本检查点时HEAD为`8d57f544df155b1c8742edfd528c101c0473dde3`。本次scoped Git只纳入Core45/46、两版test/design/scope、两个result root、snapshot与本交接，共20个新文件。发布核原始blob字节；snapshot保留已登记CRLF，whitespace检查使用`cr-at-eol`。实际提交可用 `git log -1 --format=%H -- docs/plan/continuation_handoff_20261029_saved_fresh_source_cleanup_v2.md` 查询；发布后核远端hash、空index及剩余42项原并行状态。此交接不将持续推进goal改为paused或complete。
