# C：successor 三角色上游数据合同与静态预算

2026-10-25，DRAFT_NONAUTHORITATIVE。接续[冷入口交接](continuation_handoff_20261025_saved_fresh_successor_direct_entry.md)，起始 HEAD/origin `f3b4717973557b04e558485267431cc32556b5b5`。本轮为 actual fresh 与最终父端采用之前的数据合同开发；root 唯一 writer，既有 reviewer 独立只读 PRE_SEAL。ENTRY、tests、SF49、科学 adapter、旧 schema/runner/冻结证据保持原字节。采用已读的 karpathy-guidelines，先固定输入、域、因果和预算。

## 本轮范围与验收

一个 registry 固定 **10** 个 exact data schema：ACK，controller/parent/fresh 各自 permit-binding、entry-packet 和 stage-descriptor。每项列 producer/consumer、数据边、字段类型、canonical 编码上界、拟用 transport、对应 local exact capability 以及 implemented=false。三种角色采用不同 schema literal 和 argv flag，不用 role 字符串决定权限。context 的31字段、request的20字段、deadline/runtime 合同继续复用固定 raw SHA；host/broker READY/START/offer 的 successor 完整域、真实发布与所有运行时校验另列 OPEN，不能由这10域推导完整协议闭合。

产出 registry、从旧38节点展开的角色入口 DAG、规格文件 hash DAG、三种 exact argv grammar 和未来验证矩阵。独立 stdlib oracle 核域闭集、角色对应、禁止未来依赖、两种图无环、编码容量及故意破坏设计时的拒绝。它只检查设计结构与编码约束，不是生产 data validator，也不执行真实 packet、时钟、reservation 或 capability。对实际 bootstrap 的 fault matrix 全部 UNRUN。

## 无环构造顺序与能力

每角色固定：预选 transport name/nonce + 原构造 attempt → local permit → permit-binding bytes → entry packet bytes/SHA → stage descriptor bytes/SHA → 完整 argv → 同一次 create-only allocation attempt → suspended owner → StageChannel.bind_owner header → release → bootstrap。controller 使用 broker-local controller attempt 的 nonce/commit/start/deadline，只有 parent/fresh 使用原 RoleStore reservation。macro edge 的替换及每个细节点的 producer/consumer 由 DAG 给出；跨进程 packet 永远只是 data edge。

packet 不包含自己的 SHA、完整 argv SHA、stage descriptor 实例 SHA、entry header 实例 SHA或未来 child PID/creation。packet 可引用固定独立模板/transport 合同 SHA；这些固定模板不反向 pin registry。descriptor 在 packet 后含 packet SHA、permit-binding SHA和 deadline-profile SHA；argv 在 descriptor 后含两者 SHA。现有 header 绑定创建后身份，因此不增加 post-owner ticket。startup 观察将来再绑定 argv/header/self，不回写 prelaunch bytes。

第一次 create-only allocation 前就 sticky-consume 同一 local permit/原构造 attempt；parent/fresh 同时沿用原 reservation。collision、partial commit 或失败均不得换 nonce 重试。原 cleanup 对象强持至确定终态；失败与 cleanup secondary 保留。真实一次消费与失败清理尚未实现；本轮只有设计义务。emission capability 明确属于 producer 进程，consumer_receives_capability=false，child 只接绑定数据。

descriptor 固定原 production descriptor 的完整阶段、phase_seconds、total/quiesce/terminal 时钟、RSS/process/job commit与member_handles，再增加packet/permit-binding/deadline-profile三SHA及data-only标志；role在各自schema内是固定literal，旧checked_stage_descriptor仍拒绝新schema。固定runtime/deadline/template/transport SHA由机器可读field_equalities绑定exact artifact，runtime交叉验证另保持OPEN。

controller 上游是独立 request/context/ACK/mailbox、broker 的 ACK-verified capability；parent 上游是 controller bootstrap/G0/store/issuer 与原 reservation；fresh 上游是 parent bootstrap/parent hold/store/issuer 与原 reservation，fresh 不产生 issuer。G0/hold/permit 摘要不替代本地完整输入与科学 hold。child 将来核自身、packet/header/argv 一致；producer provenance 必须由外层 exact local issuer/permit/retained owner/transcript 证明，mapping 中自报 producer identity 不构成 child 独立 kernel 认证。

## 编码、deadline 与未决实施

canonical 为 ASCII JSON、sorted keys、无空格、无 NaN/重复键。路径类型限定 canonical JSON 单值编码≤4096B，transport name≤192 ASCII字符；因此 Unicode/escaping 已计入帽。标识与嵌套 receipt/identity 使用 exact 有限类型。oracle 对每项字段编码上界逐项求和，含 object key/冒号/逗号/括号；不是拿 representative 实例代替最大合法值。ACK payload≤3072B、framed raw≤4096B；其他 packet≤32768B，permit-binding≤4096B、descriptor≤3072B。slot envelope 借用旧设计的363B保守上界，另计44B physical overhead；successor transport 未实现，不能据此宣布 wire/RSS admission。failure record 和 READY/START/offer 的容量不在本轮闭合集。

时间采用独立原 invocation-start/episode deadline；controller active/closed≤+155/+165，parent≤+110/+125，fresh≤+80/+90，分别再取原 broker-local attempt 或 RoleStore reservation deadline/cap 的更早值。数字类型和相等关系不能证明真实 absolute-deadline enforcement；不重置 start，不追加失败秒数。

## 静态执行预算与保存

仅 ordinary stdlib 静态 subprocess：初始计划 baseline、design+oracle、finalize、saved、terminal 五次，另一次失败余量；最多6次，每次含前后 pin 的 observed command charge≤12s，子目标 timeout≤11s，累计 charge≤90s。PRE_SEAL finding修正已使用原余量，exact六动作固定为baseline_01/design_02/design_03/finalizer_04/saved_05/terminal_06，不再有reserve attempt。六次帽合计72s，剩余18s只作计量/失败清理余量，不扩为新 attempt。每条 capture 以最初 monotonic 时刻起算，含自身/目标快照、pre/post Source/P1-preservation pins；记录 observed wall 与0.25s未实测尾部 reserve，各自明确。Python最初启动、编辑、审查、Git和交互时间不在这个静态命令预算中，不能宣称 actual F 180s 或完整工作流 wall 已验证。超限或 source/历史 pin 漂移立即停止 dependent action，保留 stdout/stderr/exit 和原 helper snapshot，不自动延长预算。

证据根 `results/tables/staged_rts24_saved_fresh_upstream_contract_v1_non_authoritative`。`checks_01`≤32files/2MiB：4 helpers、4设计JSON、baseline inventory/source文件、至多4次capture各4原记录及freeze支持；`final_package_01`≤16files/1MiB：saved oracle、freeze/support及至多2次机械capture各4原记录。失败修复使用剩余 slot，不覆盖旧原记录。新合同、交接、报告另≤4files/1MiB；新增总≤52files/4MiB。修改既有4个导航只前置本轮段落，历史正文保留。逻辑文件帽不等于内存/磁盘分配或资源准入；无需新 pytest，因为生产实现字节不变，本轮设计 oracle 提供有意义的结构负例。

首次baseline对应的helpers/合同和原4设计JSON全部保留：原helper snapshot及stdout/stderr/exit不动，design_attempt_01.snapshot.json以base64保存旧4JSON及原合同exact bytes；draft_revision_02.json绑定旧baseline、旧archive和新4helper/本轮合同pin，只允许这些本轮draft字节变化。old records核初始epoch snapshot，design_03以后核revision_02，不把首轮结构通过当当前语义闭合。execution freeze 后仅写独立 mechanical 包，保存 oracle 不 import 当前 ENTRY/helpers，只执行 exact hash 已核的前序 stdlib archive oracle。它复核当前 SF49、前序全路径/P1全683和冻结282/8普通探针；这些是复用，新增 pytest/真实 probe/模拟小时均为0。导航archive模式允许未来前置段落，但本轮完整body必须仍是exact suffix。最终 raw terminal 原记录由 Git blob readback 承接，oracle不能自证尚未写出的自身 exit。

旧design_02原exit未pin四个生成JSON，因此旧base64 archive只是exact历史恢复材料，historical_design_archive_execution_binding_proved=false；不能声称它们已被该次执行记录认证。revision_02新增design_output_pins逐一绑定当前4JSON，old/new全部helper snapshot逐pin复核；当前结构结果必须来自design_03。缩小raw/physical slot的结构负例与逐域value+363/raw+44组合均须拒绝或满足帽，仍不构成真实transport验证。

actual bootstrap/permit/issuer/OwnedChild/Job、full input/runtime、真实 G0/parent/fresh hold、资源/科学/正式门禁全部 false。source6500/180s、33根传递闭包、生产 NumPy probe政策、whole-workflow成本/host硬停止、真实 timeout 仍 OPEN。完成独立静态审查与 hash/diff/link/process 核验后按既有授权精确 commit/push、远端读回、空 porcelain，宽目标保持 active。
