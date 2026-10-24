# C：保存 P1 的 F fresh／最终父端采用设计交接

2026-10-25，DRAFT_NONAUTHORITATIVE。本轮接续[保存 journal 交接](continuation_handoff_20261024_saved_journal_check.md)，只完成 F 的[范围与预算设计](staged_deliverability_c_saved_fresh_adoption_scope_budget_v1.md)、保存核验和只读 PRE_SEAL 设计审阅。起始 HEAD/origin 为 `c2bc1de732f83a576b9c5158b30f32b0deddb2fc`；本轮发布 hash 以最终远端读回为准。

固定 `saved_P1_actual_21_and_journal_5h`：原 h=-2..2、21点、五 accepted hour、一个 terminal、130 CAS。完整683文件保护包含四代表行及历史fresh，但本次 F 科学重算范围只含原 B/C/E actual 与 journal，D 四代表行继续引用已有独立证据。原 missing_input/committed/known、coverage=false、双null、余额0、resume=false保持。全 P2 科学采用及 journal、完整139/F-X、resource/formal均仍false。

拟采用 parent 和新增 fresh 各一次完整 B/C/E、两层 owned Job 与完整 owner/argv/exe/source 绑定，最终 supervisor 在全外层 quiet 后核全部 metrics、21个证据、六prefix和完整库存，create-only发布后再书挡。选定来源为原45项＋四个预留路径共49项；只创建了本设计文档，三个潜在实现文件均未创建，也没有执行context、注册、lease、receipt或seal。

事前上限为单次180s；fresh请求40s、两层各5s收束及各自terminal/发布分别收费，四份128KiB收尾记录共512KiB已纳入8MiB/64新输出帽。最多四组90s普通检查＋30s静态核验，后续验证批次共570s。均是尚未执行的设计上限。原 P2 的60+5相对65s余量仍OPEN；不能用新的40s设计或普通测试时间推断其已闭合。

`F_launch_admitted=false`。下一步先在root唯一writer下编写最小独立 P1 adapter/受控入口及普通解析测试，证明 exact source/executable/展开argv、nested Job完整成员、父/子/supervisor合计资源、可执行deadline（尤其父端同步I/O）、17 target＋精确pending输出白名单、四记录长度和完整失败/发布窗口，再按实际证据判断那一次短验证是否具备既有授权与安全条件。内层父观察目录为worker/fresh_parent，与fresh worker互不包含。原guard单一wall不能直接执行40+5+5；须独立stage-aware监督后继，旧guard/P2字节不改。当前未开展真实F、native、公共P2或长实验。

`--supervise` 明确定义为TrustedController，外部trusted invocation负责context创建前起算、controller实际启动/退出、全部资源及尾部I/O停止能力；该边界尚未实现，不能从180s表格推导硬截止已受控。controller自身日志只作外部诊断，局部发布/返回不宣称返回后文件稳定。quiet未知时仅允许有界metadata安全会计，禁止工件内容与全内容SHA库存/科学采用。

本轮[保存核验记录](../../results/tables/staged_rts24_saved_fresh_adoption_plan_v1_non_authoritative/validation_report.md)包含两次标准库检查：默认 `C:\Python314\python.exe` 在递归prior比较处exit1，原始stderr保留；原绑定 `D:\Miniconda3\envs\compute\python.exe -B` 下exit0，stdout与前轮保存值逐字节一致。没有重新运行前轮40个pytest或科学轨迹。911个旧发布路径与三导航旧正文保存，P1全部683文件及前轮836路径由原检查器复核。

恢复先读本页、设计、最新E交接与C计划/blocker顶部，刷新Git/进程，并用上述compute解释器运行原 `results/tables/staged_rts24_saved_journal_check_v1_non_authoritative/checks_01/saved_checks.py`。本轮精确文档pins、保存库存及PRE_SEAL findings见新证据目录 `checks_01`。独立审阅仅形成设计findings，不是official审查或运行授权。昂贵失败/十小时增长/full wall/RAM/storage、原65s余量、C整体及D/E现实输入/方案比较/选择/敏感性/冻结后留出继续OPEN。
