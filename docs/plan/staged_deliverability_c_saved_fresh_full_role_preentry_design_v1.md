# F：完整角色 pre-entry 接线设计

2026-10-30，DRAFT_NONAUTHORITATIVE。当前账源为 cleanup_binding v4 checkpoint（11886B，SHA `8374da17a1a759ac94f48f9ca55e1479d59476a4256aeb1f799e7840d8ff896f`）。root 是唯一 writer；独立审查只给 PRE_SEAL findings。

## 实际接口与决定

Core50 的真实入口是压缩 payload 的 `-P -B -s -S -c`，prefix 等待 stdin release frame。`DevelopmentNormalChild` 使用 `PROC_THREAD_ATTRIBUTE_JOB_LIST`、`CREATE_SUSPENDED` 和 `bInheritHandles=False`，没有 stdin pipe。Parent40 是 post-spawn owner，不能承担这次创建。旧 SavedFileBootstrap 要求 direct-file `__main__`，也不能成为 Core 入口的创建根。

完整角色采用独立 successor 的 suspended release：broker 在实际 mailbox ACK 后准备 manifest、channel 和 suspended owner，绑定 PID/creation 后才 ResumeThread。旧 Core 的 stdin 路径及其冻结证据保持原样。新 child 进入 stdlib prefix 时只获得启动机会；先用 argv 中独立绑定的字段核实际 Open-only endpoint、committed header 和当前 PID/creation，并持有 endpoint capsule，之后才读 manifest、创建 Core self resource、读取 Source49。manifest/context/argv/ACK 的完整来源关系仍须继续核对。仅把 `_RELEASED` 设为 true 不满足这些条件。

完整接线必须同时覆盖以下缺口，不能用某个局部测试替代：

| 接口 | 现有来源 | 后继要求 |
|---|---|---|
| full context | adoption broker 使用 8s role probe | closed full request/offer/ACK；同一 `started + 180`，不在 child 续期 |
| 创建与 release | suspended Job owner / Core stdin 不兼容 | 实际 owner、原生创建结果、channel header 的绑定先于唯一 release |
| pre-entry 身份 | 旧脚本 argv | Core argv、压缩 transport/payload、manifest、context、role、source epoch、deadline、ACK 一致 |
| capability | StageChannel 只传进度 | broker 与 child 分别持有不可序列化的 source-specific 本地对象；描述数据不发权 |
| ownership transfer | lease → inputs → runtime | 同一 capsule 从 pre-entry 带入 PREPARING anchor，先登记清理，再提交 resource.owner |
| Guard2 | Permission1 只有 ADOPTED 绑定 | ADOPTED 逻辑 DENY；IMPORTING 首个受控动作安装 hook；安装见证之后才能 audit handoff |
| 角色生命期 | expectation consumer 调用后 close | LIVE 单次 claim 既有 root，owner 跨 reconstruct、launch/quiet、G3 保持；不得调用旧 consume_once 冒充完整 F |
| 清理 | Core/namespace/B_S/Native | 原根再包含 Guard revoke、child abort/terminal、channel/registry retirement；partial construction 也保持责任 |

FullRolePreEntryBinding 是整个接口组的名称；完成某个子接口时只能按其实际范围报告。P1 public issue/verify/claim、role 六个 effects、完整 F 运行门禁继续遵循各自授权，不能由本设计或普通测试打开。

## 来源和清理顺序

host 持有原 request/basis → broker 发布 full context offer → host 在 RAM 核对并写 ACK → broker 再核实际 mailbox header、原 ACK/context 字节和自身身份 → 固定一次 parent/fresh reservation → create-only transport manifest → channel create → suspended Job child → header 绑定实际 PID/creation → release。

child stdlib prefix → Open-only endpoint/自身 PID-creation 核对 → 独立 endpoint ownership → manifest read/完整关联核对 → self process/thread ownership → Source49 → lease/input transfer record → namespace → PREPARING cleanup anchor → unique runtime native ownership commitment → ADOPTED → pending B_S ownership → IMPORTING Guard2 hook → audit handoff → 独立 profile 匹配 → LIVE 单次 claim。当前 probe42 先读 manifest 的顺序必须由薄入口后继替换。任何后段失败均从早期根清理；manifest 或 `_Resource` 构造之前失败也须关闭 endpoint。transfer record 同时持 prior/target/capsule/resource，清理根据实际 `resource.owner` 判断 commitment，不能仅从最后 journal 记录推断。数据相等不能代替对象身份、创建顺序或原生状态。

Guard revoke 在所有业务/文件/child 效果前先停止新许可；child 必须先 abort/quiet 并保留 terminal/unresolved；channel/registry 再退休；Core 原有 namespace、B_S、thread/process 清理仍执行。各域失败独立收集，保留原 primary、secondary 和不确定关闭状态，不重复物理 close。

## 合同、成本与验收边界

原 F 保持 parent/fresh 各自独立完整 B/C/E 21 点、五个 accepted 小时、130 CAS、19 metrics、17 targets、180s、P1 12500 和 source/executable/runtime 6500 读帽，四份 terminal 记录共 512KiB/4 slots 包含于总帽。Source49 epoch 保持 `acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875`。transport 独立目录的文件/bytes、启动 helper、context 独立核对与失败清理须另计入完整资源与读取 DAG；不能写零或排除出整体预算。

开始 Native 诊断前，先把实际 successor 的源码闭包、压缩 payload 上限 131072B、XZ上限26214B、完整 UTF-16 command line 项目上限30000 units、descriptor/manifest 大小、原生句柄与清理点、每个读取窗口和停止路径写入具体包。新 pre-source endpoint 会改变启动模块和 Native 图，旧 startup/import profile 不能直接成为新路径的等价证明。普通 source/AST 检查不执行项目 target；后续有界 Native 诊断依 agent.md 第9节取得专项授权，不重跑 NFC12。

路线准备阶段先用实际 frozen Core44/50、probe42、Parent40 minifier 和 UTF-16 builder 得出两组压缩基线及独立解码核对。此处基线拼装仅测字节/编译形状；Parent40 实际闭包仍绑定 Core44，不能据此宣称已支持 Core50。未来薄入口、endpoint kernel、helper pins 和新增 argv 的实际大小必须重新测量，现有余量不是后继准入。

普通 PRE_SEAL 只能证明指定源码/CodeType、closed schema、身份/状态机、调用顺序、预算算术和显式 synthetic fault 的行为。真实 mapping/mutex、PID/creation、suspended release、OS argv、hook 覆盖、Job inventory/两层 quiet、Native 清理及 wall/RSS/commit 必须另验。完整 F gate、资源准入、独立真实性和正式结论仍 OPEN。

## 继承

下一普通验证包首先精确继承 input **1514 / 84266616B** 与 archive **310 / 37900515B**，再 union 实际 own。累计 static **684.9277867000303**、pytest **366.48897970000326**、unittest **414.9035574999798**，总 **1466.3203239000134s**；**57** 条不接受记录、原始流、失败输入和费用全部保留。当前交接在新 own 中显式纳入，不假定已在旧 input map。原42项并行 dirty snapshot、NFC12原16文件、B1–B3、P2七输入和已发布绑定字节保持。
