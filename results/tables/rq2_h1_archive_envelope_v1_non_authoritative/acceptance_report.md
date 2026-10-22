# 整链预算：owner / holder 容量核对

整链性能审查仍未完成，正式准备的 16 项门仍全部 OPEN。本次补齐 logical archive 口径、条件事件计数和原件核对；wall/RSS/总物理存储准入继续为 null。

旧 3h 原件按只读 SQLite `mode=ro` 核验：9 条 events 的 raw body 合计 268799B，SQLite 文件 294912B，holder JSON 合计 362361B，另有 1B lock。465 个 case 文件与 444 个 owned 文件的名称/SHA 均未变；最近 business 69 项、constructor 208 项绑定均匹配。重建的 owner/holder 终点 heads 与外部 preclose checkpoint 相同；这仍是旧 synthetic case 的只读字节审计，未构造新的 owner 或可写凭据。

| T（模拟小时） | clean paired 后 events | 额外 terminal 后 events | 原 source Job replay | business 历史长度下界（3 lane 始终 active） |
|---|---:|---:|---:|---:|
| 168 | 503 | 504 | 458320 | 18966864 |
| 192 | 575 | 576 | 597520 | 28311936 |

表中事件数限定 W=0 且 FSM assessment 已不再 needs_next_hour；168h 仍有 primary pending 或 follow-up debt 时，下一次调用进入 attempt 而非 terminal。source Job replay 均指 saved Job artifact replay，不是 native solves。每个 alternate intent+witness 加 2。现实现没有独立的 W hard cap，仅 archive 容量会拒绝后续追加。完成 H<192 小时后，下一小时缺源/normal 失败可保留 attempt，DB 为 3H+2W；intent 已写而 outcome 未写为 3H+1+2W。holder 在提交失败窗口可领先 DB 一票，两者各受自身 cap 约束，不能在两个已声明 cap 外再加一票。旧 toy `max_events=32` 不适于此目标。

对 holder 自身 N/B/A，令 S=min(A,N×B)，每票 raw 长度为 b_i，n≤N、Σb_i≤S。由 ceil(b_i/3)≤(b_i+2)/3，Base64 总长≤4×floor((S+2N)/3)。加上 N 个最大 wrapper（sequence=N、最长 kind）及 accepted header≤4096B、writer lock=1B，得到有条件 logical file-content 上界。Base64 ASCII 不产生 JSON escape；测试逐字节对照原 encoder。该式不包含 SQLite pages/journal、filesystem allocation、目录元数据或外部 head/checkpoint。

仅以每条 B=1MiB、N=576、A=N×B 举例，raw-body cap 为 603979776B，holder logical bound 为 805537793B，两层内容合计 1409517569B。这是未采用的参数算例，不能作为磁盘准入或实际 192h 占用预测；当前配置没有修改。

原 source producer 与消费 owner 都强制 audit≤131072B 且 canonical。source encoder 为 ensure_ascii=True/no newline，owner 为 ensure_ascii=False/outer newline；对可由 owner UTF8 编码的 plain JSON，内嵌 object 字节数不大于 source ASCII 字节数。Unicode/control/float 小例和 lone-surrogate 拒绝测试支持实现对应；普遍不等式来自编码规则，未声称测试穷尽全部 JSON。

1 个 Rref 与 3 个 Actual 分别享有 max_stages=300、max_record_bytes=1MiB、max_total_bytes=16MiB。计入 source audit 后，pre-owner 声明包络为 89616768B；owner 实际接受的 intent 仍≤1048576B。原 packer 接受的 1MiB pack-only padding 在 Base64 后已超过 event cap，仅说明 producer/packing 的声明不能保证稍后的 append 被接纳；它没有通过数值报告校验，不能视为科学反例或目标报告可达性证明。producer 与转换在 append 检查前已发生，昂贵失败档案仍需预算。

复用的 business 组件观测：单 synthetic training JOINT/cohort、finite-v2 business 参数覆盖，h168/h192 原 validator 各 0.0799385/0.0913091s；full carry 为 1836367/2118971B。owner scientific state 只存 identities/flags，不能拿 full-carry 字节当 owner event 大小。该组件也不能外推整体 wall 或关闭 source/phase 门。

最新 unit_02 为 38 项通过（2.85s，outer 3.939858s），保存 8 个明确执行依赖的运行前后 SHA 及 8 份 tested snapshots；其中 wrapper 长度向量是 accepted bodies 的 superset，canonical 代表票另经原 _ticket 接受。先前 unit_01 的 33 项观察结果缺少自身运行前字节绑定，原件保留，不用它单独证明 exact-byte acceptance。最新 audit_03 退出0（outer 2.773152s，768 bindings），补核外部 checkpoint heads；audit_02 原结果与执行源码保留。audit_01 因 checker 错把 owner genesis 当 header hash 失败，原运行源码与终态也保留；按原 owner_genesis 域分离规则修复后重核。各 audit 均未实例化 owner/source Reader、写旧 DB、启动 normal Job 或调用 native solver。

下一工作仍在预算关键路径：完成适用 source file/runtime/freshness 闭包及合法 source 路径选择；验证目标 cap profile 与 alternate policy，再补 normal/selector、SQLite/holder 外部持久化、失败/terminal/reopen 的完整成本。仅当整链预算有依据后，连接真实 167→168、携 primary debt 进入 follow-up、恢复后终结、上限携债与缺必要 source 的 typed unresolved/right-censor，最后 terminal→checkpoint→close→fresh-process replay。E=168/F≤24 原合同及全部科学验收限保持。

本包为 DRAFT_NONAUTHORITATIVE / PRE_SEAL 开发证据；formal_result、resource_admission、formal_execution_ready、full_192_hour_execution_verified、seal 与 official review 均未开放。具体 native/formal 运行仍需独立权限。
