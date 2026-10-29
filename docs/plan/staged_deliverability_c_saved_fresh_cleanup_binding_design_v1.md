# F：固定 cleanup anchor 与同 owner 的 role 清理接线

2026-10-30，DRAFT_NONAUTHORITATIVE。root 唯一 writer；R3 依 agent.md §7 做独立只读 PRE_SEAL findings。本后继修改实际 Core ownership/cleanup 路径，沿用 role v2 的八组修补；普通验证不创建项目 Native/P1/Source49 target，不重跑 NFC12。

Core46 的 SPEC/OBJECT 晚绑定先换 anchor，再写 runtime seal；中间异常会在 native finally 之前被 cleanup 拒绝。Core47 在 PREPARING 创建固定 anchor，仍以原 `resource.owner = target` 为唯一 ownership 提交。anchor 强持原 namespace、Native roots、ledger、owner slots 和三条有限 binding journal：ARMED、BOUNDARY_SPEC、BOUNDARY_OBJECT。每条含 generation、前一条对象身份、stage，以及 boundary/spec/proof/initial state/type/slot 完整 tuple。

每个新记录用 held `list.append` 一次提交，之后才写 packet/owner mirror；OBJECT 在 claim 与 B_S addaudithook 之前提交。anchor/image 不再变化。cleanup 使用原 anchor 与最后合法记录；journal、mirror 或 runtime seal 漂移保留为失败，namespace fallback 和 Native finally 继续执行。journal 被截断或丢失时不能捏造已丢失的 boundary 终态；保留 unresolved，即使 Native handles 已关闭。任意协调篡改 anchor/journal/ledger/owner seal、跨线程和真实 Native 等价仍未证明。

role runtime v3 增加 cleanup-only 机械接线：按 Core47 完整 raw pin、唯一 payload 边界、`<pre_entry_payload>` CodeType、original defaults 与现存 binding rows，持有同一个 owner 的 close packet。packet 的 globals 只有空 builtins，close 再使用原 held runner；wrapper class 取自 runner 原 roots。它不复制整个 Core namespace，不创建角色或外部能力。实际入口 factory 仍须独立认证 bootstrap namespace。原六个 effect gate 和 public binding 均保持关闭；关联测试显式使用私有 fixture clone，不能解释为生产授权。

普通验证覆盖原 Core 32 方法、role 26 方法，以及 10 个关联方法。关联矩阵按实际 CodeType CALL 指令，在 SPEC/OBJECT 每项 publication、packet/owner mirror、runtime seal、claim 的前后两条 opcode 边界注入故障；另在两次实际 append 前后注入。检查同 anchor、原 primary、sticky carrier、thread→process 原 close、相同 pending/close_calls、无重试、namespace retirement、已提交 boundary emergency deactivation。补充 journal 空/foreign/倒序/截断/generation/shape、packet loss，以及真实 Core close 与 role `_close_once` 的成功、primary carrier、child abort 失败组合。

Native leaf、entry/bookend、namespace/B_S lifecycle 仍是明确合成域；Core constructor/open/transfer/prepare/claim/cleanup 和 role cleanup orchestration 使用后继精确源码。ordinary Capture1/DRAIN1 的实际 sampler/HANDLE 清理及一个 validation child 单列。源绑定检查只支持 cleanup 函数连接；Guard2、channel/registry retirement、launcher/quiet 仍须成为初始 manifest、IMPORTING 前 role root 及其固定 cleanup 域，不能从 LIVE 后的 JSON 参数升级为权限。

## 冻结 F 合同勘误

历史 [source-cleanup v2 交接](continuation_handoff_20261029_saved_fresh_source_cleanup_v2.md)“剩余F工作”一段把原合同抄成49 metrics、77 targets、380秒、2159。原源码与预算从未改动。正确值为 **19 metrics、17 targets、180秒**；两个条件算式均为 **P1 reads**：`2*5055+3*683=12159`、`2*5002+3*683=12053`，不能当作 Source49 计数或已验证物理复用。

[静态提取器](../../experiments/staged_rts24_saved_fresh_contract_snapshot_v1.py)以 restricted AST 解释原 adapter 的 METRIC_FIELDS、原 runner 的 TARGETS/RECORDS/CAPS/STAGE_SECONDS，不 import/exec 这两个目标模块。registration 保存完整字段、原 source pins/行号/表达式，以及 WIP 中两个条件算式的文字来源。勘误保持历史文件字节，不能改变原 12500/6500 read 帽、180s 绝对时钟、四件128KiB预留或任何 gate。

## 完整 F 的后续依赖

Core `-P -B -s -S -c` pre-entry 与旧 `-B -s adoption_v1.py --saved-entry` 是不同启动画像。后续须保留 Core 入口，由 broker 在初始 full-role manifest 固定 context、role、argv/channel、source epoch、deadline 与一次性 fresh reservation；IMPORTING 前持有不可序列化同 owner entry capability 和默认 DENY Guard2，LIVE 后只 claim 既有对象。Namespace successor 要保持跨 reconstruct→launch/quiet→G3 的 owner 生命周期。当前 Namespace4 的 expectation consumer 在单次调用后关闭 owner，不能直接承担这个生命周期。

再后是 source-specific child launch、inner/outer quiet、supervisor 原完整19 metrics比较、G0–G3、失败保存及整体 physical-read/性能准入。parent/fresh 独立21点、五小时、130CAS与冻结科学合同保持；本包新增模拟跨度0h，actual_F/run/resource/science/formal 全false。
