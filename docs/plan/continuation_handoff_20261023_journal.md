# C保存证据与只读重放开发交接

## 最新：以journal_v2继续

最终独立sol_reviewer发现v1的F14（旧CAS缺失后仍可能采用），随后在v2草稿定位F15（旧root条目发布窗口缺失）。旧v1源码/合同/531核心工件保持原字节；原测量有效，但旧writer不作为后续保存API。后继见[retention规格](../model_spec/staged_rts24_journal_retention_v2.md)、[journal_v2](../../src/staged_rts24_journal_v2.py)与[短探针合同](staged_deliverability_c_journal_retention_probe_v2.md)。

v2绑定完整CAS/root inventories和previous SHA链；写前纯pack期望全集，采用前精确核旧闭包加新增对象、旧root加新entry、原目录身份，最后核runtime。fresh重算累计key集并核可信前缀。删除旧对象/条目或依赖漂移均不能采用，缺口不自动修复。新24项无solver检查通过，连同旧358项为382项不同检查。

唯一closure_probe_01复用旧前两小时证据，未重新生成点。一个fresh child的完整state科学/typed SHA、summary、audit和结果逐字段与旧prefix相同；原观察结束仍为5，当前missing_input、债务40右删失。三个失败分支覆盖begin前删fixture、entry后删fixture、闭包完整的unknown；前两者writer不采用/fresh拒绝，后者fresh只确认1行，不伪造terminal。37次子图编译/121描述，0旧full compiler/solver/native。

新probe outer27.9132234s、脚本27.1709143s、采样tree RSS418926592B；核心138文件286322B，终态含已完成日志142文件311956B并预留launcher16KiB。60s/20s无进展/512MiB/8MiB/600文件均未触发。见[新报告](../../results/tables/staged_rts24_journal_v2_non_authoritative/closure_probe_01/validation_report.md)、[核验](../../results/tables/staged_rts24_journal_v2_non_authoritative/closure_probe_01/verification.json)与[只读postcheck](../../results/tables/staged_rts24_journal_v2_non_authoritative/closure_probe_01/postcheck.py)。新6源、旧13源/旧531核心及B1–B3字节首尾保持。

完整key表/root链/前缀检查仍有O(T²)增长，此两小时full方法不能替代公共整链测量，也不与旧三方法五小时wall直接比较。下一步先分析这一保存成本和公共数值证据获取包；真实native仍须具体登记及专项授权。公共g、139节点合同层、完整F/X时序及C/D/E资源仍OPEN。以下v1部分保留测量历史含义，后续API以v2为准。

2026-10-23，`DRAFT_NONAUTHORITATIVE / PRE_SEAL`。继续[causal交接](continuation_handoff_20261022_causal.md)、[C总计划](staged_deliverability_c_scope_and_budget_plan_v1.md)及agent.md。用户已确认公共网络方向：RTS-24为最小公共后继，小网络保留机制回归。根代理唯一writer；本轮未运行native或长实验，目标“推进计划”继续active。

## 已完成的独立后继

新增reference子集编译、causal_v2/audit_v2、typed CAS和journal五模块。旧causal八源、build源、B1–B3及C绑定字节全部保留。完整合同compiler不变，子集在有效fixture域内保持请求字段/身份与消费元数据；public120帧及多步三方法/跨版本状态等价有普通检查。

[规格](../model_spec/staged_rts24_journal_development_v1.md)定义固定20类型、Fraction/float hex和tuple/list保真，frame/父点/证据无损去重。同一ReadView可复用解码，末端重读所用对象、inventory、目录身份和runtime；不跨操作缓存。不覆盖已有pending或失败工件，没有可写resume/并发lease或耐久性保证。

journal分别保存hour、未决attempt及terminal检查点。缺reference/actual保持旧ledger和当前已观察输入；实际已知拒绝仍由内核形成stopped记录。begin→固定策略→显式actual→accept→独立candidate audit→CAS/条目发布→读回后采用；finish保存summary/audit。可信重开绑定外部genesis/head/count/state、关闭/结果和failure SHA，不能仅依赖genesis。尾删/篡改拒绝；publication unknown由final字节与可信failure裁决；pending terminal不当成arrival。

## 唯一有界诊断

按[合同](staged_deliverability_c_journal_probe_contract_v1.md)只运行attempt_01一次，exit0。三方法各5个模拟小时、三个顺序fresh child，完整state科学/typed SHA、summary、独立audit与baseline一致。另五个same-process失败/缺输入重开分支裁决符合合同。

500次selective编译/1324描述与逐阶段、逐角色会计闭合；外部解析provider另15次旧full编译/83描述，0 solver/native请求。脚本报告前72.9916099s，outer75.1157866s，采样tree RSS417968128B；核心531文件558007B逐SHA一致，watchdog终态含已完成日志535文件657668B并预留自身16KiB。限180s/30s无进展/512MiB/64MiB/5000文件均未触发。

解析late-Y例：fixed方法判断通过但恢复时实际CFE不足；full等待后补做仍保留40期限缺口；instantaneous不恢复。物理网络在本例中不随投运标志改变，没有公共工程跨期数值执行或公共g。358项不同普通检查通过；这些unit时间不是公共整链预算。

[完整报告](../../results/tables/staged_rts24_journal_v1_non_authoritative/attempt_01/validation_report.md)、[机器报告](../../results/tables/staged_rts24_journal_v1_non_authoritative/attempt_01/report.json)、[保存核验](../../results/tables/staged_rts24_journal_v1_non_authoritative/attempt_01/verification.json)及[只读postcheck](../../results/tables/staged_rts24_journal_v1_non_authoritative/attempt_01/postcheck.py)记录实际结果。只读PRE_SEAL审查不是official review、receipt或seal。

## 接下来按依赖推进

1. 使用v2保存路径，保留已绑定source/contract与所有pending/orphan原件。下一后继先分析逐文件首尾核验、state/hash和引用列表增长：旧v1父bounded读16881次/96199735B，新v2父bounded读5591次/36973173B，二者规模/路径不同，不作提速比较，也不是总磁盘I/O。公共frame、长cohort与真实失败还未测，不能按小例缩放。
2. 准备具体公共数值证据获取包：正常C/P0经济primal/KKT、corrective最优性与恢复端点、策略后actual点、solver终止/完整dual提取。先固定代码、输入、次数/call cap、线程、wall/RAM/存储、失败收尾和独立核验；真实native校准必须另获专项授权，不能由此次PRE_SEAL推导。
3. 接通公共完整合同139节点层并保持与实际轨迹层区分；完整反事实F/X业务时序另定事件/恢复/期限证据，不以actual接受授予整体合同交付。
4. 根据公共完整路径及代表失败实测，闭合C整链会计、合法复用和资源预算，再确定有限D点数与固定策略E留出。F方法写作同步，结论等待D/E。现实合同/设备/阶段参数来源及原H1门禁按blocker保持。

## 工作区与Git

启动HEAD为9bbe732751ba41102708ffe5de67b21baf858aea；中途并行论文清理已单独提交，同步前必须刷新HEAD/index/remote，不重打包该任务文件。当前检查点仅本后继源码/规格/测试/合同/runner、完整attempt和当前导航。最终提交号以远端读回为准，不把本段历史HEAD当最新。

新对话先读本页、AGENTS.md、agent.md第7–9节与C计划/当前blocker，刷新Git和相关进程；复用保存证据，不重跑attempt。所有被start/completion/verification绑定的bytes保持，后续行为变化使用明确successor。C整体性能、D/E资源、public/native、完整F/X时序及formal等门仍OPEN。
