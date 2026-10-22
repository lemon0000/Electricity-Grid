# B2有界网络开发诊断执行合同

2026-10-22，`DRAFT_NONAUTHORITATIVE`，按agent.md第7、9节限定本次开发测量。上游为[B2网络规格](../model_spec/staged_deliverability_network_development_v1.md)。只执行一个新增attempt；不创建冻结候选、production manifest/lease、review receipt或正式结果，不启动优化solver、外部下载或新native校准。

## 固定问题、路径与调用量

[网络配置](../../configs/staged_deliverability_network_v1.DRAFT.yaml)绑定未修改的B1业务fixture。固定三例：on_time/early、on_time/late、delayed/early，仅full_temporal当前信息策略。物理时间t=−2…7，t=1末保存checkpoint；delayed在t=3参考接入额度不足时停止，拒绝状态也必须重开一致。

执行入口为[独立B2 runner](../../experiments/staged_network_b2_development_v1.py)。DAG顺序为：

1. 导入及源/环境指纹、旧B1九pin复验→配置装载。
2. 各例装载业务输入→连续执行参考；每小时先合同5个DC点（正常完整C、两个退出各F及C−c_hat），再实际参考点1个；准入通过才调用B1提案和实际点1个→独立Fraction审计→保存完整参考与t=1末checkpoint。
3. 同一解释器新进程→源/环境起始指纹→装载输入→读取checkpoint并重放4小时前缀→逐小时执行后缀至终态/首拒绝→一次完整独立审计→结束指纹→保存终态。父进程读回并对比完整state/audit/两端指纹。
4. 三例完成后父进程结束指纹及实测计数核验→evaluated报告→预完成事件→此前全部工件的size/SHA清单→最后以rename发布`completion.json`。只有清单核验通过且无failure.json的有效completion才标记本开发诊断完成；report自身不作完成标记。失败则仅终止本runner子进程并保存失败及最近父状态，不重试、不覆盖或删除attempt。

| 实际工作 | 单次连续参考：按期早/晚各例 | 单次连续参考：延期 | 父参考+子重放/后缀三例总量 |
|---|---:|---:|---:|
| 网络小时尝试 | 10 | 6 | 52 |
| PYPOWER makeBdc/dcpf点 | 70 | 41 | 362 |
| B1提案步骤 | 10 | 5 | 50 |
| 独立网络审计小时 | 10 | 6 | 52 |
| 独立实际业务账本审计小时 | 10 | 5 | 50 |

另有6次业务输入装载、3个fresh子进程、3次checkpoint保存/读取、3次参考/终态比较。独立审计使用分流/KCL的Fraction实现，不调用PYPOWER或被测上界。成功fixture中审核362个已保存唯一点；正常scenario引用已核normal点，不另算潮流。测试中的异常、边界扰动和oracle调用不混入本表实测诊断计数。

## 重复计算、等价与扩展成本

父连续轨迹在t=1直接留存不可变业务状态，避免为checkpoint再跑4小时。子重放4小时是独立重开证据的必要工作，不作为可省成本。每个完整合同正常点合法复用给正常scenario，故每小时5个合同潮流而非6个；复用局限于同小时同网络/负荷的同一个对象。

独立业务审计只在每条终态执行一次，避免每小时审核增长前缀的二次开销。仅最终有提案但未提交的异常/拒绝路径需再审一次“已接受前缀+候选”的算术，默认延期在提案前拒绝，不触发额外前缀。增长到N条T小时路径时，正常本结构为2NT业务步、最多14NT潮流；每次额外重开重放长度L需单独增加L，不能忽略历史重放。ledger内部批次遍历及序列化增长另测，不据本小例声称一般规模线性。

不跨小时缓存合同、请求或实际点：工程/线路状态、设备、待机和清洁额度可能变化；小例最多362个二母线潮流，缓存依赖审计的成本收益不足。三个子进程顺序运行，以限制RAM并便于归属；暂不并行或扩大网络。B1代码、合同、配置及保存结果九pin起止逐一验证；本包源/配置/规格/测试/runner、实际导入的仓库.py与选定外部PYPOWER/scipy文件及版本均记录。它是实际导入集与选定依赖指纹，不是完整环境闭包或通用生产 freshness 证明。

## 固定资源、观测与停止

依据：B1完整9子进程整路径约3秒，当前B2针对测试（28项）约3.29秒，含实际PYPOWER调用及异常注入；它们仅用于这个小例的保守预算，不提供主实验ETA。预计本次全部路径5–20秒，固定总wall 60秒、每子进程15秒、父+后代采样RSS 512 MiB、所有输出16 MiB、单文件2 MiB。并发仅父+一个child，零优化solver/native校准。最终实测包括导入后至报告前/完成打印时间，工具外层另报。

父在每小时、每阶段及child轮询0.05秒检查资源；child运行每秒写父心跳。child15秒无终态即停止；父60秒或RSS/存储越界即停止并保留失败，无自动延长预算。同步调用/导入/文件I/O不能被这些合作式采样即时中断；这是采样保护而非OS硬配额，阻塞I/O、进程杀止/磁盘故障和异常清理的昂贵成本仍UNKNOWN。日志直接入受限文件，避免PIPE填满死锁。

报告阶段wall、真实调用计数、子PID/退出码、进程树采样RSS、工件大小和SHA；开始/结束、父/子及旧B1 pin均一致才接受该次开发对照。JSON独占创建、禁止NaN，checkpoint限制2 MiB；父/子均只允许`results/tables/staged_deliverability_b2_v1_non_authoritative/attempt_01/`。completion列出此前全部工件（含report/events，不自哈希）；发布后只读机械复核，后加阅读报告单列为运行后说明。它是开发终态，不是production manifest、seal或receipt。输出路径、独占创建、大小/资源拒绝、最后事件失败和清单篡改有普通测试。

该诊断覆盖成功、任务永久逾期、参考接入权拒绝和新进程重开；数值失败/事务回滚/部分结果篡改由普通注入测试覆盖。昂贵真实I/O失败收尾、一般网络/SCED/AC及完整F/X时序任务背书不在已测范围；工作包C的主实验性能审查仍未完成。即便数值网络见证满足，post阶段完整合同需0.4 MW调用而aD=0.25 MW，一小时业务背书应失败，aggregate_contract_release保持false。
