# C：保存 P1 的 F fresh 与最终父端采用范围、预算

2026-10-25，DRAFT_NONAUTHORITATIVE，设计阶段。接续[保存 journal 交接](continuation_handoff_20261024_saved_journal_check.md)、[E 合同](staged_deliverability_c_saved_journal_check_contract_v1.md)和[科学采用 DAG](staged_deliverability_c_scientific_adoption_dag_v1.md)。本页固定下一步的验证对象、费用上限与准入问题；本轮只维护文档、复核保存证据和进行只读 PRE_SEAL 审阅。当前实现文件、执行 context、真实 fresh 测量和采用记录均未创建。原发布字节、P2 七输入及原 guard/outer 合同保持。

## 1. 验证对象与可报告结论

固定 scope 为 `saved_P1_actual_21_and_journal_5h`：原 P1 的 h=-2..2、21 个 actual/reference/recovery 保存点、五个 accepted hour、一个 terminal 和 130 个 CAS 对象。输入目录是 `results/tables/staged_rts24_native_v1_non_authoritative/p1_01`，683 文件、2,950,863B，其中 journal 为 137 文件、427,629B。

独立外部锚为同级 `p1_execution_review_01/postcheck_03.stdout.json`，SHA256 为 `c6a25cd96c8a4a2cf293d41fe51bc7905db63fbc35253076f97e9239a4f22473`。每次读取均持有完整 683 pins、文件 metadata、目录及祖先 identity；launcher、start、schedule、trusted_prefixes 和 trusted_binding 只能取自该锚绑定的字节。caller 的 fixture、全部预期 pins/query/state、source、锚原字节及 identity 一并冻结为 canonical image，末次复核不能用当时重算的期望替代。

本次 F 的科学重算仅连接 E 的 actual 轨迹和 journal。P1 points22..31、四代表 F/X 行及历史 fresh 文件仍在完整库存保护内；四行的科学证据沿用[原 D 检查](continuation_handoff_20261024_saved_contract_replay.md)，不计入本次 fresh 的科学重算或局部采用范围。原 `fresh.json` 只是历史对照，不承担新增 fresh 进程的证据角色。

未来最多报告局部 `saved_P1_fresh_process_verified` 和 `saved_P1_parent_adoption_verified`，两者须带上述 scope。当前两项均为未执行。全 P2 的 `journal_replayed`、`scientific_evidence_adopted`、`expected_query_provenance_independently_verified`、`independent_139_verified`、`full_fx_contract_verified`、`resource_admission`、`formal_result` 继续 false。未观测小时、完整319/139/F-X、方案选择和留出不进入本次结论。

## 2. 父端持有的来源与进程边界

继承 E 的[45 项源码 pins](../../results/tables/staged_rts24_saved_journal_check_v1_non_authoritative/checks_01/component_source_pins.json)，另预留以下四个 provisional 路径，形成固定 49 项选定来源集合：

- `src/staged_rts24_saved_fresh_adoption_v1.py`：只读 B/C/E 编排与完整 metrics 投影。
- `experiments/staged_rts24_saved_fresh_adoption_v1.py`：标准库 supervisor 及受控 parent/fresh CLI。
- `tests/test_staged_rts24_saved_fresh_adoption_v1.py`：范围、失败和发布窗口检查。
- 本页：`docs/plan/staged_deliverability_c_saved_fresh_adoption_scope_budget_v1.md`。

前三个文件尚不存在，不允许把路径预留称为 source 注册或 seal。实际写入后，必须先取得 exact bytes/SHA，逐进程核 loaded module 的绝对路径及源码 bytes，完成首尾书挡；49 项之外新增来源需重新审查。E 已含 guard v1/v3、normal_process 与 parent observation v1/v2，不再重复收费为新来源。journal 自身两次 runtime_identity 的 28 仓库来源、10 外部入口、executable 及 Python/六包版本检查完整保留，仍仅是 selected runtime/import entry closure。

拟固定 executable 为 `D:\Miniconda3\envs\compute\python.exe`；启动前绑定绝对路径、文件 identity、字节 SHA、`sys.executable`、`sys.version`、六包版本和实际外部入口。当前默认 `C:\Python314\python.exe` 不替代该绑定。所有进程 cwd 为仓库绝对路径，采用原 `controlled_environment()` 的 exact canonical 摘要，并核环境来源首尾。

拟定 argv 模板如下；`ENTRY` 是上述 experiments 文件的绝对路径，`O` 是独立输出根，`P1` 是固定原输入根。模板只用于设计；真正启动前必须完全展开并与父端持有的 canonical context、SHA 逐字匹配。

```text
EXE -B -s ENTRY --supervise --context O/context.json --context-sha SHA
EXE -B -s ENTRY --parent --context O/context.json --context-sha SHA --input-root P1 --output-root O/worker
EXE -B -s ENTRY --fresh --context O/context.json --context-sha SHA --input-root P1 --output-root O/worker/fresh
```

`--supervise` 是本方案的 TrustedController，承担最终父端采用；parent 是它持有的科学重建子进程，parent 再持有 fresh。controller 在任何科学 import 前核自身入口、executable、context SHA、scope/预算及允许的目录。监督层持有 parent 的 suspended OwnedChild；parent 持有 fresh 的 suspended OwnedChild。每层都在 release 前直接捕获实际 parent PID、owner PID/creation FILETIME、传入 CreateProcess 的 argv/command line/cwd/environment 和 context SHA。只读 P1 不接旧 P2 的 `Binding`/319 点 context；需要独立 P1 adapter，不能改旧 schema 或给旧 context 加键。

context 的创建、controller 自身启动/退出事实、进程能力与全部资源/超时控制属于外部 trusted invocation boundary。该调用方须持有 context 的 exact bytes/SHA、controller 实际 argv/identity 和从 context 创建前开始的绝对deadline；本轮尚未实现该 OS owner，`F_launch_admitted=false`。controller 的自身stdout/stderr只作外部诊断，不进入本包采用所需的稳定文件库存；其费用仍计入调用方总预算。两层Job及本包记录证明止于controller的create-only observation、同进程读回/末次书挡和返回事实；不宣称controller退出后的日志稳定、掉电持久性或返回后文件不再变化。调用方还须确认controller成功退出、总deadline及全部资源条件，才可消费该局部返回值；后续消费必须重新核返回的exact SHA、identity和source/input书挡，不增设一层自证observer。

两层保留各自 HANDLE 和完整历史身份集合，均受原 1024（含 owner）上限约束。外层 Job 包含科学 parent 和 fresh 后代，内层 Job 另持有 fresh；重叠的 `(pid, creation_filetime)` 在总体资源/身份清点中去重，在各层 witness 中保留。真实 nested Job 关联和短命成员完整性必须先用普通小型进程检查证明；CIM 快照、自报 PID 或一份 JSON 不代替 owner 能力。任一层 cleanup/close/完整清点未知，科学采用保持未决。独立 OS command-line 验证和完整 runtime closure 仍 false。

## 3. 固定的 E→F DAG

| 阶段 | 动作与父端持有的期望 | 输出与停止边界 |
|---|---|---|
| F0 装载及外层启动 | 外部锚、全 P1 库存 G0、49 source/exe/runtime、fixture 与预算；冻结 context 和 caller image；捕获外层 owner 后 release | 专用 successor 目录；目标/pending 已存在即拒绝；此时没有采用 |
| P 原 B/C/E 重建 | parent 用原政策从 initialize 重算五小时/21点，再由原 journal_v2.reopen 重建；保留原 query、parent/KKT、accepted state 和全部书挡 | create-only 保存 parent_metrics 候选；任何点或政策未决都不启动 fresh |
| F1 新 fresh 启动 | parent 再核输入/source/context，预扣一次 fresh reservation，直接捕获内层启动事实 | 仅一次 fresh；构造、capture、release 失败不退款、不重试，先收束已创建 owner |
| Q 新进程独立重建 | fresh 从磁盘原锚与相同 context 重新装载，独立执行完整 P 同范围 B/C/E；没有继承 live PointEvidence 或 parent 结果缓存 | 只在独立输出目录保存 fresh_metrics；不写 P1，不调用旧 fresh_worker |
| F2 内层 quiet 与比较 | P1 专用阶段监督后继核 fresh 完整 quiet、成功退出和 caps，保持原 OwnedChild/guard v3 的成员与记录规则；保存内层 launcher/独立父目录观察；比较完整 metrics，来源及 G1 在 F3 统一书挡 | quiet 未知禁读 fresh 工件内容，仍允许有界 metadata 安全会计；成功退出前的文件存在不产生比较成功 |
| F3 parent 候选关闭 | parent 重核 caller image/context/source 和完整 P1 库存，保存 comparison 候选及真实 progress，再退出 | 候选不是最终父端采用；不重复第三次科学重放 |
| F4 外层 quiet | TrustedController 核 parent/fresh 全历史成员、退出、RSS/commit、输出会计并保存外层 launcher | 整个外层 Job quiet 前不读取 parent/fresh 的候选内容；unknown 仅作有界 metadata 安全会计并保存独立 process 诊断 |
| F5 最终父端采用 | supervisor 绑定本次两层启动及 process 记录、parent/fresh 候选 SHA 和完整相等性，核全 P1 库存 G2、source/exe/runtime/caller 与输出精确库存 | 科学一致性、机械完整性、发布状态分别判定；不从历史 terminal 或 candidate 标志推导成功 |
| F6 发布及末次书挡 | create-only 发布独立 parent observation，读回 canonical 原字节；再核全 P1 库存 G3、来源、输入锚和输出最终会计 | 仅全部完成后返回局部 adoption_verified；发布后漂移保留原文件及 expected SHA，返回 unknown |

G0、G1、G2、G3 是原 B/C/E 每侧自身双库存之外的四次完整 P1 内容/metadata/root 检查，不跨进程缓存。若实现要合并任何一次，须先重审其依赖和失败窗口，不能静默减账。

parent 和 fresh 的真实 P1 读取全程禁止 SolverFactory、Highs 构造、backend make_model/call_highs、CAS put、journal create/begin/commit/finish/resume。只允许上述绑定的 fresh spawn，以及输出目录的 create-only publication；不能沿用 E 的“禁止所有 Popen/publication”补丁后再宣称验证了真实 F。能力按角色限制，fresh 不能再 spawn，controller 不执行 native。相关回归的解析 fixture writer 仍只作用于 pytest tmp。

## 4. 同输入、完整 metrics 与终态

两侧必须独立重建并按规范原字节比较以下闭合字段集，不能只比较 state SHA 或挑选成功字段：

`state_sha, state_cas_sha, summary, independent_audit, scientific_outcome, publication_outcome, terminal_entry_present, state_certainty, closed_entry_present, unaccepted_attempt, failure, pending_terminal_checkpoint, pending_cas_objects, unreferenced_final_cas_objects, genesis_sha, head_sha, final_entries, saved_objects, resume_permitted`。

这是[原 metrics 投影](../../experiments/staged_rts24_native_probe_v1.py)的完整字段口径；新 adapter 可独立纯投影，不调用旧 driver/CLI。另逐项比较 21 个 ordinal/role/query SHA/typed evidence SHA、genesis 和五个 accepted state SHA、六个 prefix binding、完整 trusted tuple、scope、source/context/executable 绑定。不得让任一侧从另一侧的 CAS query 或 metrics 反推出独立预期；新进程继续通过原 B 的政策/接受前缀生成 query。

保存终态必须仍为 missing_input/committed/known、accepted=5、last_hour=2、entries=6、CAS=130、next_hour=3、余额0、resume=false，无 pending/unaccepted/failure/未引用 CAS；coverage=false、两个条件 null 原样保持。`state_cas_sha` 为 `29517379c102b40b0f0a0b77711db4d936357025e4f53283f5bdec04fcbc7a41`。历史 fresh metrics 可额外比对，但新 parent/fresh 任一侧缺失、非规范标量或字段漂移都停止本次采用。

最终记录只保存有界摘要及 candidate/process/context 的 SHA 引用，完整 metrics、source map 和库存分别保存在已绑定的 core 文件。controller 的 create-only observation 与同进程规范原字节读回构成 publication commitment，局部 adopted 的返回事实还依赖发布后 G3/source/accounting；记录内不预写自证末次检查完成的 bool。文件可存在而 publication/采用仍 unknown，科学 missing_input 与验证程序失败分别保存。该commitment只证明本次调用观察到的发布，不证明controller返回后的未观察变化；下次采用须重验exact record SHA/identity及输入来源。

## 5. 调用量、复用和费用上限

原 E 成功路径的[实际计数](../../results/tables/staged_rts24_saved_journal_check_v1_non_authoritative/validation_report.md)只作为两侧相同代码路径的基数，非本次实测、wall 预算依据或成功保证：

| 项目 | 每侧原 B/C/E 基数 | 两侧条件合计 |
|---|---:|---:|
| compile / snapshot / import | 42 / 21 / 21 | 84 / 42 / 42 |
| prepare / propose | 20 / 20 | 40 / 40 |
| execution audit / 历史 row 重审 | 33 / 85 | 66 / 170 |
| typed pack（含 E 的13次 get 规范化重编码） | 155 | 310 |
| 原45来源/runtime 内容读 | 2080 | 4160 |
| P1 内容读 | 4319 | 8638 |
| 外部锚末次复读 | 1 | 2 |

四个新增 source 在每侧外部双书挡另加 16 次内容读取，条件来源基数为4176；四次 G 库存另加2732次 P1 内容读取，条件 P1 基数为11370。bootstrap、外层/内层启动和最后采用 source/runtime/anchor 复读、候选发布/读回、目录/stat、摘要及 canonical 编码另外收费。拟定硬逻辑上限：compile84/import42/snapshot42；typed pack≤320；P1 内容读≤12500；source/exe/外部锚内容读≤6500。新增路径须逐阶段计数后证明落帽，未知调用不能写成零。新输出内容读取和 metadata/编码成本另由字节、条目及 wall 帽约束，并须单列实测，不冒称 OS I/O 上界。

只复用同一次 operation 内原 CAS 缓存、冻结输入字节和已经返回的 metrics；不跨点/小时减少 parent/KKT、政策或 runtime 检查。parent 与 fresh 两侧各自重建，最终采用只比较其已绑定候选和末次书挡，避免第三次整链。保留重复政策计算是跨进程独立性的费用；D 的十点/四行科学重算是明确的后续范围，未藏入本次预算。

## 6. 事前时间、内存和存储预算

以下是待实现、待验证的设计上限，当前不构成运行准入或 ETA。一次真实 F 只允许一个保存输入、一个 parent 重建、一个新增 fresh、零 native、零自动重试。目标整链绝对帽为180s，由待实现的trusted invocation从context创建前计至controller退出，含F0、两侧科学路径、收束/发布、失败和controller自身费用；子阶段不能反复续期。下表冻结费用分配，并不表示当前已有可执行的整链deadline。

| 互斥阶段 | wall 上限/s | 覆盖内容 |
|---|---:|---|
| F0 准备及外层 capture/release | 10 | 从context创建前计；调用方/controller启动、input/source/exe/context、G0、启动事实 |
| P 科学 parent | 45 | 原 B/C/E、typed joins、parent metrics 保存 |
| F1/Q 新 fresh | 40 | 从内层构造前开始计时，包含 capture/import、B/C/E、metrics 发布 |
| 内层收束 | 5 | quiesce、post-quiesce commit、close |
| 内层 terminal/发布 | 5 | 最后扫描、编码、launcher/内层观察读回 |
| F2/F3 parent 比较和退出 | 15 | G1、source/caller、metrics 全比较、候选保存 |
| 外层收束 | 5 | 全外层 Job quiet/close |
| 外层 terminal/launcher | 10 | 最后扫描、完整 witness、编码/发布 |
| F5 最终父端检查 | 15 | G2、两层 owner、全部候选、source/exe/输出库存 |
| F6 最终发布和末次检查 | 15 | create-only/readback、G3、完整最后会计、controller返回/退出捕获 |
| 失败诊断与终态保留预留 | 15 | 只消费尚余总预算；不重跑科学路径或补写成功 |
| 总上限 | 180 | 成功和失败共享，不在失败后额外加180s |

本次拟将 fresh 活跃阶段帽收紧为40s，不修改原 P2 的60s fresh或65s no-progress、3600s总帽。原guard_v3只有一个wall_seconds，quiesce后的terminal扫描也核同一wall；因此不能给它传40却另加10s尾部，也不能仅传50便宣称40s已受硬控制。后续须在上述新P1入口中实现独立stage-aware监督后继：同一retained owner实际执行40s活跃超时停止，并在累计50s内分别约束5s quiesce和5s terminal/发布；外层同样按共享绝对deadline执行阶段停止。复用原OwnedChild及完整HANDLE/记录域，不修改旧guard实现或原P2绑定；该新监督逻辑的普通故障测试及独立审阅是准入条件。

真实 `fresh_reserved` 到 `fresh_returned` 的设计窗口为40+5+5=50s，余下15s仅是待验证的调度/书挡余量，不是实测结论。事件必须对应实际完成阶段，不能用定时空心跳遮住阻塞。capture/启动包含于40s；原 P2 的60+5与父尾部余量仍 OPEN。任何阶段没有可执行的超时/安全终止机制，特别是controller/guard返回后的同步 I/O，均阻止真实 F 启动；trusted invocation须实际覆盖这些外部费用和停止能力，不能由计时注释或线程 timeout 声称已受控。

外层 Job 中科学 parent+fresh 的合计 sampled tree RSS≤1GiB、每进程 commit≤1GiB、Job peak commit≤2GiB；保留收束前采样与收束后 peak commit，不宣称采样覆盖所有瞬时 RSS 峰值。两层 Job 的重叠内存不得相加两次。Job 外 supervisor 的 RSS/commit需独立观测并纳入相同的总预算判定；当前没有全流程合计内存证据，不以 worker 数据替代。总资源执行器如何覆盖 supervisor 以及发布后 I/O 的停止能力是实施前门槛。

输出预留根为 `results/tables/staged_rts24_saved_fresh_adoption_v1_non_authoritative/draft_01`，本轮不创建。输出根及其 worker/fresh/parent 物理路径均须与原 P1 不相交，拒绝重解析点、别名和目录替换；input 指原 P1，只读且不复制。内层worker为`O/worker/fresh`，其观察记录必须在独立的`O/worker/fresh_parent`；两者及外层`O/parent`均持有自己的目录/祖先书挡，满足各自parent/worker物理互不包含的规则。新输出合计设计帽8MiB/64文件，位于原64MiB/8192 envelope内；单文件8MiB、metadata entries≤16384、depth≤12照旧。以下17个相对路径固定为本包输出 target allowlist，不要求失败路径产生成功文件：

```text
context.json
worker/parent_startup.json
worker/events.jsonl
worker/parent.stdout.log
worker/parent.stderr.log
worker/parent_metrics.json
worker/comparison_candidate.json
worker/fresh/startup.json
worker/fresh/events.jsonl
worker/fresh/stdout.log
worker/fresh/stderr.log
worker/fresh/metrics.json
worker/fresh/launcher.json
worker/fresh_parent/parent_observation.json
worker/launcher.json
parent/parent_observation.json
diagnostics/failure.json
```

parent/fresh事件与标准输出/错误日志只用上述固定路径；只有 JSON target 采用原 create-only codec，并允许其精确 `<target>.pending` 失败残留，不接受任意后缀或临时文件。日志、pending、两层记录和诊断均纳入总会计，其他路径拒绝。parent/fresh日志在其对应Job完整quiet后核稳定字节；controller自身诊断由外部trusted invocation捕获并收费，不作为本包稳定库存或局部采用证据。

每一监督层仍各预留128KiB launcher＋128KiB parent observation/两个文件槽；两层共512KiB/四槽，已包含于8MiB/64，不能只为外层留262144B。全局会计区分已发布实际字节和尚未消费的预留，嵌套记录在外层库存只计一次。128KiB记录只放有界摘要/SHA，需独立验证最坏字段编码及实际长度；不得截断1024成员数组以合帽。预算是检测/拒绝条件，不是文件系统硬配额；超帽保留失败实际 bytes，不删证据。quiet未知仍允许原guard式有界lstat/size/file-count安全扫描，但不得读取工件内容、计算全内容SHA库存或作科学/采用检查；其完整worker会计保持unknown，只在独立父目录保存process诊断。

普通解析/故障测试最多四个预先固定互斥 nodeid 组，各90s；静态/保存核验合计30s。真实 F 的180s加上述360+30s，后续完整验证批次最多570s；这是预算，不是本轮已获执行权限。本轮只做文档和保存核验，不消耗那一次真实 fresh。不得因失败增加次数或时间；若确需新一次，保留旧目录并先重审具体范围和预算。

## 7. 成功、失败与发布验收矩阵

| 验收项 | 必须观察的行为 |
|---|---|
| 同输入成功 | 新 parent/fresh 独立 B/C/E；全部 metrics、21证据、六prefix和终态相同；两个真实 owner/full quiet；最终发布后书挡成功 |
| 预期或来源漂移 | source/loaded module/executable/env/context/fixture/query/trusted九字段或完整683 pins map错误立即停止；末次冻结image不能被同步修改期望绕过 |
| 身份与库存漂移 | 锚同字节替换、祖先/根/文件identity变化、额外/缺少路径、候选或输入事后变化拒绝；不声称覆盖未观察到的ABA |
| parent科学失败 | 保存已花费用和未决原因；不启动fresh，不推断数值不可行、不补小时 |
| startup/capture双错 | 保留活owner能力、capture phase/expected SHA/may-have-published和cleanup错误；禁止release/重建，unknown不读该Job输出 |
| fresh失败 | late numeric/metrics/非零/超时/无进展/资源超帽均保留；只有完整quiet后可有限只读诊断，不产生局部verified |
| 任一quiet未知 | 仅允许有界metadata安全扫描；禁止该Job工件内容、全内容SHA库存与科学采用，独立父目录保存process诊断；分别计数并测试安全扫描与内容读取，闭合外层/内层HANDLE与短命成员义务 |
| caps与尾部 | fast exit采样unknown、1025历史身份、双层reserve、嵌套总量和post-completion资源均拒绝成功；父端尾部计入绝对deadline |
| publication窗口 | write前后、flush/fsync、rename前后、readback、G3/source/final accounting失败保留pending/final、phase/expected SHA/may-have-published；不得覆盖、补写成功或自动重试 |
| 返回语义 | science/metadata/publication三层独立；文件存在不证明采用，局部verification不打开全包/资源/正式门禁 |

普通矩阵先用解析小例和现有保存输入的最小只读 seam；真实五小时 fresh 至多一次，不为每个故障重跑21点。尚缺的昂贵失败和十小时增长继续登记，不能用解析注入替代真实资源证据。故障组collection、具体fixture、计数器及独立record oracle在编写实现后固定，未固定前不启动真实 F；完整输出必须满足上述17 target及精确pending白名单。

## 8. 本轮出口与下一步准入

本轮交付本设计、导航、保存核验及独立只读 PRE_SEAL findings；root唯一writer，reviewer不写文件、不分叉。不会生成production manifest/lease、official verdict/receipt/seal或任何run authority。R3依[agent.md §7](../../agent.md)执行；这次审阅只审设计及已有证据。

最小实现须先证明：49 source/exe/runtime与展开argv的确切绑定；external trusted invocation、context创建和controller启动/退出/全部资源/同步I/O停止能力；阶段监督后继的40/50s及整链180s执行；nested Job完整成员与quiet；17 target及四份record长度；实际调用计数；完整失败与发布窗口测试。上述问题仍为真实 F 的实施/测量准入条件，`F_launch_admitted=false`。设计上限不能当成已测得整链成本。完成实现和普通检查后，再依据实际证据判断是否有已授权、可安全执行的那一次短验证；不从本页推导运行许可。

原整包科学采用、完整319/139/F-X、昂贵失败/十小时增长/full wall/RAM/storage、原65s父端余量、C整体以及D/E现实输入、有限比较、方案/容量选择、敏感性和冻结后留出全部保持OPEN。新的native仍需具体包与专项授权。
