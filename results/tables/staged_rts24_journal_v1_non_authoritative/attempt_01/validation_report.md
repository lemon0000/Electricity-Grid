# C保存与重放后继：开发验证记录

最终R3领域复核发现F14：v1 writer没有绑定完整已保留CAS集合，外部删除旧对象后仍可能采用下一小时，fresh才拒绝。本次保存工件当前完整，下面的一次测量与数值重放事实仍成立；通用writer鲁棒性不能据此认定闭合。v1源码/合同及核心工件保留原字节，修复进入journal_v2后继；当前问题见[findings](preseal_findings.json)。

2026-10-23，`DRAFT_NONAUTHORITATIVE / PRE_SEAL`。按[固定合同](../../../../docs/plan/staged_deliverability_c_journal_probe_contract_v1.md)仅执行一次attempt_01，exit0，未触发停止条件。公共网络方向保持RTS-24；本诊断数据为显式解析三母线，未取得公共数值点或启动native/长实验。

## 已观察结果

三种方法各覆盖5个模拟小时h0…4，分别有完整内存baseline、journal/检查点关闭和独立fresh子进程。三fresh重建全部白名单类型、完整网络/父子见证，重算策略、actual和所有carry；完整state科学SHA及typed根、summary和独立audit均与各自baseline相同。

| 方法 | 列表编译：baseline / journal / fresh | journal wall | fresh：脚本 / 外层wall | 方法判断 / 完整约束回放 | 登记任务期限缺口 |
|---|---:|---:|---:|---|---:|
| instantaneous | 40 / 55 / 55 | 10.2567s | 3.3296 / 3.5928s | true / false | 40 |
| fixed_headroom | 40 / 55 / 55 | 15.1851s | 4.5846 / 4.8360s | true / false | 0 |
| full_temporal | 40 / 55 / 55 | 15.4018s | 4.3236 / 4.5911s | false / false | 40 |

fixed在h2恢复40却出现实际小时CFE不足；full等待至h4补做，但h3已经发生的40期限缺口保留。instantaneous不恢复。三条覆盖完成均不意味着完整履约通过。full有5个actual_accepted小时；两个approx的该数为0，其账本明确为hypothetical。

每个成功journal仅保存1个Rts24Data对象；instantaneous共79个CAS final，另两方法各129个。相同frame/父证据按typed SHA复用，跨session仍分别保存。Fraction、float hex、tuple/list及完整见证无损，科学摘要保持原口径。当前完整state的历史引用、prefix审计和hash工作仍随Σt增长。

## 五个关闭/失败分支

| 分支 | writer / reader编译 | fresh确认的hour前缀 | 保存结果 |
|---|---:|---:|---|
| reference=None | 2 / 2 | 0 | reference_unresolved attempt；当前工作量100保留，无动作/after-state |
| actual=None | 3 / 3 | 0 | actual_unresolved attempt；有效proposal保留，ledger不推进 |
| entry rename前异常 | 3 / 3 | 0 | not_published；有效pending为observed_pending_unaccepted |
| entry rename后异常 | 3 / 5 | 1 | writer不采用，fresh凭可信failure及final字节确认一条；仍为incomplete_journal，没有伪造终态 |
| 两步后缺输入 | 13 / 13 | 2 | missing_input检查点；仅两项已到达任务，债务40右删失 |

核心包含3个fresh child；五个failure分支为同进程只读重开。更多终态/CAS发布阶段、尾删、failure篡改、无final/pending的unknown及cache freshness由普通临时目录反例覆盖；不把这些测试升级为真实坏盘/掉电/阻塞I/O证据。

## 实际会计与资源

[report.json](report.json)精确闭合selective编译500次/返回列表描述1324个：P0=500、raw=124、恢复min/max各350。外部解析证据提供者另做15次旧full compiler/83描述；journal/fresh复用这些证据，fresh旧full调用为0。它们是重复构造/审计会计，不是独立样本或求解次数；solver/native请求为0。完整公共合同139节点层不属于此次actual路径执行。

脚本报告前elapsed为72.9916099s；[watchdog](launcher.json)从启动至退出/收尾outer为75.1157866s。0.2s轮询下进程树采样最大RSS417968128B，低于512MiB上限。终态扫描为535文件657668B，另为launcher自身保守预留16384B/1文件；最终核心manifest为531文件558007B，全部SHA读回一致。两种统计的角色集合不同：核心排除活跃日志和watchdog，末端扫描包含其已完成日志。追加的本报告、verification、postcheck、findings不属于原core，另在Git检查点核对。

父进程计数为335 selective/897描述、474个CAS publish及35个journal publish尝试，后者33次正常返回、两次声明异常；两个failure witness也属于journal出版计数。父bounded读16881次/96199735B；该读计数不含所有Python import、直接普通文件写入或外层scanner，不能称总磁盘I/O。三个fresh另有自己的读取计数。源码/目录首尾检查及CAS读写占主要wall，约1.07s的三baseline计算不能代表保存路径预算。

## 普通检查、审查与字节保护

共有358项不同普通检查通过：48项请求/多步等价；journal/CAS共41项，最终38项全轮67.73s及5项watchdog/进程快照窄轮1.84s覆盖（两个watchdog重复）；269项相关回归13.00s。普通测试wall不作为本probe或公共整链预算。选中公共旧测试仅装载/缩放，未选solver测试。

独立只读PRE_SEAL reviewer在启动前审查、修复后复核；编码规范/类型、资源前检、目录身份、final/pending冲突、可信head/failure、attempt/terminal区别、watchdog扫描及终态限额、逐角色会计和进程参数保存边界均已补对应检查。另明确路由sol_reviewer进行本检查点的最终领域复核。状态仅为PRE_SEAL findings，未创建official receipt或seal。

[verification.json](verification.json)与[只读postcheck](postcheck.py)核对13个直接文件、28个genesis仓库源/配置、十个外部入口及版本，旧B1–B3 118保存/42repo pin/7external、旧C三源、build_01核心/追加角色、旧causal八源和三份检查记录全部保持。启动HEAD为9bbe732751ba41102708ffe5de67b21baf858aea；这是并行论文清理提交后的快照。此前无关README/插图清理属于另一任务，本包未改动其文件。

Git机械检查保留绑定源码`causal_v2.py`已有的额外末尾空行；采用关闭blank-at-eof提示的diff检查，其余空白错误仍检查。两份stdout/stderr日志按完整保存范围显式加入，不改变运行字节。

## 仍待解决

这次只关闭上述解析5小时路径的保存/重放开发缺口。公共normal C/P0、child/actual真实数值点和g、69事故完整合同层、完整反事实F/X任务时序、长cohort/矩阵和真实native失败成本仍未知；不能由75s线性外推D/E或192小时。C整体性能、D/E点数/资源准入、native执行权、formal、rigorous bound和工程结论仍OPEN。
