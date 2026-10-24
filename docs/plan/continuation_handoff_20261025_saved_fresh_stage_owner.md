# C：F 阶段监督与 retained owner 开发检查点

2026-10-25，DRAFT_NONAUTHORITATIVE。接续[adapter交接](continuation_handoff_20261025_saved_fresh_adapter.md)，起始HEAD为`06c5c23f24789bca1b8e2efa2e18c2f9a66824a3`。完整F仍按[原范围/预算](staged_deliverability_c_saved_fresh_adoption_scope_budget_v1.md)推进；本轮完成其阶段监督组件，后续发布hash以远端读回为准。

在原provisional ENTRY及测试中实现固定RAM进度通道与retained-owner短进程监督。SF49范围保持；src只读adapter及原B/C/E、P1、guard/outer字节保持。通道为69632B pagefile mapping、16个4096B frame slot；create-only、Open-only attach、随机nonce、真实PID/creation、单writer/thread、mutex、commit-last、历史书挡、partial/bad-SHA不计进展、abandoned永久未决均有检查。记录保存header及frame，可在mapping关闭后重算完整SHA链。

公开探针只收闭集probe_id，源码固定程序及小caps；真实创建进程仍为suspended、原OwnedChild/Job retained HANDLE，header绑定后release。首阶段从监督者时钟开始，后续仅严格下一phase更新；超限/协议错先直接请求kill，再原完整quiet及close。terminal退出截止包含于原active预算，原quiesce和文件发布tail保留。冻结OwnedStage书挡阻止owner/channel/startup/时钟/real标记漂移；fake逻辑与真实process/quiet字段分开。constructor、partial channel、kill、quiesce、close、末次书挡及cause/context链分别保存，保留可继续清理的实际capability。

最终当前源码87项终态通过：68 stage＋19原guard，wrapper16.422s＜30s，SF49前后相同。此前105项组合在65.078s通过，其28项不受影响adapter/bootstrap域经精确前缀/整文件字节对比复用；两个源码epoch分别保存，不将105项当作当前stage字节证据。初轮43通过/6失败、第二轮67通过/1失败及collection缺少user-site pygments的失败全部保留。四组普通测试实耗104.311s，collection合计11.422s；最后必要修正组事前重审，仍在300s开发验证总帽内。

11个真实短探针保存完整启动/阶段/退出/quiet记录：normal与nested quiet成功；其余覆盖缺首帧、阶段/terminal挂起、缺terminal、非零退出、child error及root退出仍有后代等预设失败。记录内所有Job累计成员＝retained身份＝signaled完整清单：九份为2成员，nested quiet为4，root残留后代为3，逐份按完整清单核验。最大采样tree RSS 51,720,192B、Job commit 21,475,328B，最大单记录9,353B；仅描述这些短探针。1024成员容量检查属于单元构造，fake进程验证字段保持false。

原F production入口仍显式非零退出；`F_launch_admitted`、两个局部fresh/process/adoption及整包science/resource/formal均false。当前只有普通短探针，没有新增五模拟小时fresh、native或公共P2。外部constructor/kernel阻塞中断、controller自身资源、受监督terminal文件I/O/发布、完整parent/fresh/controller编排与最终四记录oracle仍待实现和整链验证。不能从本轮小caps推断40/50/180s已经闭合，也不能关闭原65s余量、十小时增长/昂贵失败、319/139/F-X或C整体预算。

下一步直接实现完整F角色编排：复用已测adapter、同一外部caller/context和本轮阶段协议，连接parent一次重建、独立fresh进程及fresh_parent观察目录、父端比较与候选/观察发布。把同步扫描/文件发布放在受上层owner监督的进程内，补足最外部trusted invocation对constructor、阻塞与controller合计资源的能力；固定整条DAG和失败窗口，先普通检查，再判断一次真实F的条件。预算仍为fresh40＋quiesce5＋terminal发布5、整链180s、8MiB/64文件、四份各128KiB；原P1 h=-2..2五模拟小时/21点/五accepted/一个terminal/130CAS及D四行边界保持。

恢复时先核Git/进程，读本页、[本组件合同](staged_deliverability_c_saved_fresh_stage_owner_contract_v1.md)和[报告](../../results/tables/staged_rts24_saved_fresh_stage_owner_v1_non_authoritative/validation_report.md)。用`D:\Miniconda3\envs\compute\python.exe -B results/tables/staged_rts24_saved_fresh_stage_owner_v1_non_authoritative/checks_01/saved_checks.py`做标准库保存检查；该检查区分当前canonical draft与冻结测试snapshot。980旧路径、三导航全部旧body及P1全部683保留；PRE_SEAL只读findings复核没有official verdict、receipt、seal或运行权限。活动目标“持续推进计划”继续，以上为组件检查点。
