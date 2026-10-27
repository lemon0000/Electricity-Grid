# F：真实1024窗口与完整保存终态

2026-10-28，DRAFT_NONAUTHORITATIVE，起点bae0a39c4a2c70c5aee2c3798aac124bd415b31b。承接[上一完整单测交接](continuation_handoff_20261028_saved_fresh_census1024_unit_terminal_v1.md)。本轮是progress：首次完成真实1024窗口及saved/checkpoint，宽goal仍active，完整F未完成。root唯一writer，wire_root_review只读PRE_SEAL，无official verdict、receipt或production seal。

## 当前真实端点

先读results/tables/staged_rts24_saved_fresh_nfc_v6_non_authoritative的checkpoint.json，再读registration、所有phase exits、两个plan/receipt和startup_profile。Root精确**16文件965896B**；checkpoint SHA **5c5a2e47010031bb6b0da99fc9cd928917a590c91e04db2f9db88ea00d7daad3**，accepted=true、diagnostic_accepted=true，scope仅为packed metadata及有限import诊断。所有已执行源码、scope、policy、inputs与原记录冻结，不原位修改或重跑。

真实唯一import child PID40400，1024个guard-passed open，最终entered=observed=passed=1024、rejected=diagnostic_error_count=0，reason=prefix_complete。预设stop在第1024次guard通过后、该次physical open之前，窗口内最多1023次physical open。child exit1是预设diagnostic stop的完整失败记录，不是timeout；primary/secondary及self-close witness完整。close_calls=[1,1]、self HANDLE和DLL directory关闭，父端HANDLE/pipes/readers/writer/stdin全部终态，无kill、truncate、timeout、reader/cleanup错误。

原异常链完整保留：AuditCensusStop → LocalRuntimeUnresolved → BootstrapImportUnresolved → ValueError(import policy did not complete)。stderr为3个stage、34个graph frame、10个census frame；after_adapter_import_attempt只表示因诊断stop离开该次尝试，不表示正常返回。

**尚未自然返回**：adapter_import_return_observed=false、cold_import_acceptance_complete=false；runtime=UNRESOLVED、boundary=FAULTED、resource=CLOSED，runtime_was_live=false。不能写成B_S完整import、OBSERVED/LIVE、真实F或正式资源准入。窗口中阻断一次既定NumPy可选Popen尝试，未创建该可选子进程。

本次machinery_observed_stage从0到2，authenticated_stage=0、authentication_pending=true；仅说明两个finder按声明顺序进入并被结构观察，不能表示其函数metadata/registry/native行为已认证。完整runtime、producer/owner/Job/bootstrap、ACK/issuer/permit、quiet/返回与最终父端采用仍待闭合。

## 开销与观察

Actual audit phase **8.768902099996922/10s**；其中parent import receipt为5.7917537999892375/8.352371600005426s，child census窗口为**3.5519291999953566s**。三个口径不同，不把窗口秒数当整包或完整import时间。raw stdout4447B、stderr10126B、其中census9188B，均按原caps完整保留。

cache_items从11到117，新增106；最后entry_total1.0656298999674618s，image_digest0.4061146999883931s、cache0.41522720018110704s，分别约38.11%与38.97%的entry_total。它们是本次选定open窗口的嵌套bucket观察，不是无重叠的整链分解，不能与旧512不同路径做配对提速结论。direct child peak WS **129970176B（123.94921875MiB）**，error=null；这不是combined retention、整链RAM或128MiB资源准入。

Size加入11段计时与严格schema/type/finite/charge关系校验，原14节点内追加timing反例。唯一size为1.6256954s：predecessor/archive约0.6759、graph0.2683、migration/source/transport0.2483、codec/command0.1537、runtime origins0.1145s，其余较小。只解释本次size，不倒推NFC5未分段的3.332s，也不把一次观测称为稳定提速。

## 本轮两包与累计账

NFC5按[原46s scope](staged_deliverability_c_saved_fresh_census1024_phase_budget_scope_v1.md)唯一size拒绝：3.332350500000757>3s，而command29706/30000和registration_max516434/524288均合格。随后checkpoint为rejection_metadata_only，accepted=true/diagnostic=false，0.7197095000010449/3s；4文件194044B，cp SHA **7177125654559df795938fd722ad46f0ddfdb6276c636a1d3063763c01c7c256**。合计4.052060000001802/46s、0 register/unit/cold，增加一条不接受记录，剩余预算留原包，不退款/转移/重跑。

NFC6采用[独立49s合同](staged_deliverability_c_saved_fresh_census1024_phase_budget_scope_v2.md)，size6/register3/unit10/pre4/startup5/profile4/audit10/saved4/checkpoint3。与旧46s包分别记账；registration文件执行前独立预留589824B，actual525182B，candidate+1024=526206B；命令29705 UTF16。没有放宽任何旧包帽或科学/helper阈值。

| NFC6阶段 | charge秒 | cap秒 |
|---|---:|---:|
| size | 1.6256953999982215 | 6 |
| register | 1.3951422000100138 | 3 |
| 唯一14-node unit | 7.5793666999961715 | 10 |
| PRE_SEAL | 2.9802497000055155 | 4 |
| startup discovery | 3.519030899988138 | 5 |
| profile | 2.763073299996904 | 4 |
| 唯一actual1024 | 8.768902099996922 | 10 |
| saved | 2.8039042000018526 | 4 |
| checkpoint | 1.8652493999979924 | 3 |

NFC6 static **25.72124719999556/39s**、unit **7.5793666999961715/10s**、合计 **33.30061389999173/49s**，余15.699386100008269s留本包。本轮两包合计37.35267389999353s。最新累计static **358.8353753000513**、pytest **366.48897970000326**、unittest **104.80309689999922**，总 **830.1274519000538s**，不接受 **37条**。沿原capture口径，编辑/review/Git/Python初始启动等不在其中，非全部开发wall，模拟小时推进0。

## 实现、保全与核验

core32/probe30/parent29/fixture4/test5/constructor2为NFC5冻结实现；core33/probe31/parent30/fixture5/test6/constructor3为NFC6。core/probe/parent只迁移独立root路径；test01逐层保留原路径oracle，test07更新独立预算fixture并追加timing反例，其余14节点原断言保留。census1024_none_v2原helper未改，pin-memo未接入。

NFC6登记12 helpers、345 direct inputs、1072 effective inputs；继承933→1051→1061的精确无冲突union并绑定新source/size。每次仍完整执行冻结v3 leaf，不执行NFC4/5 checker，不递归扩checker；保留所有fresh点及前驱345+344输入回读。14节点为本包自己的30帧/report14/0/0/0/child exit0，runner2.008s；PID36056及其所有收尾已核。startup child PID22168/exit0及profile为本包新证据。

Source49原raw与epoch acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875保持。旧41文件3054186B，加NFC6共57文件4020082B；这是所列result roots的保全计数，不是工作区总占用或合并storage准入。所有旧失败、NFC5拒绝与各自未用余量完整保留。

独立只读PRE_SEAL在首次执行前核代码/constructor/链账与caps，在完整unit后核345 direct/49 Source、source snapshots、raw streams和30帧，终态再核1024异常链、saved/reopen及全root。它不生成official review状态或任何run authority。Timing结构只支持条件性开发记录，不独立认证时钟或任意FS/RAM防篡改。

## 后续

下一目标是接近完整import自然返回并闭合finder认证与OBSERVED边界，见[2048/自然返回准入草稿](staged_deliverability_c_saved_fresh_census2048_admission_scope_v1.md)。先核实际DAG、command/输出增长、cache和内存/停止策略，再定独立后继；不能直接重跑NFC6、机械翻倍估时或把剩余秒数当新执行授权。完整F没有可靠剩余开发时间。

无实际P1/OwnedChild/Job/F、model/solver、native校准、长实验、外部下载或付费查询；所有科学/资源/正式/run字段false。四导航仅发布新前置段+HEAD正文，39项并行文稿/插图/文献原bytes保留。最终hash以含本交接的commit和remote实时回读为准，不能报告全局clean。
