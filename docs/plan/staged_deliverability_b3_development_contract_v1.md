# B3终结与保存重开有界开发诊断合同

2026-10-22，`DRAFT_NONAUTHORITATIVE`。按agent.md第7、9节承接[B3规格](../model_spec/staged_termination_development_v1.md)及[B3/C计划](staged_deliverability_b3_c_next_steps_v1.md)。仅一个新增attempt，目标为测量当前小例的完整终结、journal保存、重开与数值/存储失败分支；无优化solver、native校准、外部下载、production manifest/lease、seal或official结果。B1/B2源与保存工件均不修改。

## 固定DAG与工作量

入口为[B3 runner](../../experiments/staged_termination_b3_development_v1.py)，固定输出`results/tables/staged_deliverability_b3_v1_non_authoritative/attempt_01`，独占创建、不覆盖或重试。复用B2同一两母线配置及三条固定策略轨迹，物理时间−2…7、注册边界4、每例初始4步在t=1末checkpoint并关闭。

1. 导入→源/依赖指纹→装载网络配置。三例依次装载业务fixture→genesis→前4步逐小时计算与保存→checkpoint关闭。父直接从已接受前缀继续纯内存参考后缀，独立Fraction审计并保存参考。
2. 每例一个fresh子进程→起始指纹/网络与业务输入→完整重放4步及checkpoint核验→前缀独立审计→接受并保存后缀或单列未接受attempt→终态独立审计→保存terminal→结束指纹/报告。父比较完整state、独立network audit及两端指纹。延期在t=3停止，ledger只接受至t=2，不能把当期未接受输入混入prefix。
3. 四个同进程重开探针，均使用on_time/early新journal：missing_input保存4步后finish并重开4步；network_unresolved保存3步后在t=1实际点load=0.5 MW抛声明异常，保存attempt/terminal、恢复数值函数，再只重放接受的3步并审计原失败证据；save_before_publish保存4步后对第5步close注入异常并独立审计旧状态及纯候选，重开4步保留pending；save_after_publish同规模在final读回注入异常，重开5步裁决已接受。两个保存失败以外层probe报告保留，不再写普通terminal。
4. 父结束指纹→严格计数核验→evaluated报告→最后事件→全部既有文件size/SHA清单→completion临时写入和rename→严格库存验证→无写入资源终检查。仅有效completion且无failure才表示该开发诊断完成。失败保存阶段、最近已接受state/head与child PID/退出码，停止本runner拥有的child；不清理或改写失败现场。失败报告本身仍为best effort。

| 实际工作 | 三例父参考+fresh子进程 | 缺输入 | 数值未决 | 发布前失败 | 发布后读回失败 | 总计 |
|---|---:|---:|---:|---:|---:|---:|
| PYPOWER点计算 | 362 | 56 | 48 | 63 | 70 | 599 |
| B1提案步 | 50 | 8 | 7 | 9 | 10 | 84 |
| 网络小时尝试 | 52 | 8 | 7 | 9 | 10 | 86 |
| 顶层独立审计 | 9 | 2 | 2 | 2 | 2 | 17 |
| network audit | 9 | 2 | 2 | 3 | 3 | 19 |
| 网络审计小时访问 | 64 | 8 | 8 | 13 | 14 | 107 |
| 已接受业务审计小时访问 | 62 | 8 | 6 | 13 | 14 | 103 |
| 已保存点审计访问 | 446 | 56 | 54 | 91 | 98 | 745 |
| journal publish调用 | 35 | 6 | 6 | 6 | 6 | 59 |

数值未决路径两次额外审核“3步业务前缀+未提交提案”，另8次业务审计step访问。每小时5个合同点、参考点及适用时实际点；注入实际点异常不计为成功PYPOWER计算。599次计算及745次审核均含重放、候选和重复审核，不是独立样本数。3个child顺序执行，业务fixture装载10次，网络配置另4次；14次header/implementation_pins、8次runner fingerprints覆盖B2 report/completion、32源pin及选定7项外部文件/版本的重复检查。59次journal fsync、58次journal rename；59次publish中57次返回成功、2次注入错误，后者之一已发布final。completion另1次rename。预计59个journal文件（含保留pending）及17个顶层文件，共76个完成前后机器工件；清单不自哈希。

## 优化、等价与增长

父参考复用刚接受的4步前缀，避免为checkpoint另跑；不跨小时缓存网络或请求，工程/设备/故障/clean输入可变化。单文件完整row是本纯模拟接受点，不设双重候选/accept文件。各终态/重开只做一次独立前缀审计，不每小时重复；存储故障额外候选审计与数值未决提案审计按表保留。fresh重放是所验证行为的实际成本，不能折扣为零。

每步仅保存新row，文件条数O(T)；before/after完整state摘要仍遍历增长历史，另有O(T²)编码字节访问，当前T≤10限定预算。每次重开再增加所重放L小时的策略/潮流及审计。`writer_canonical_encode_calls/bytes`只度量journal writer编码，`state_digest_record_visits`只度量直接传入NetworkState的编码，不含嵌套state或独立审计全部序列化；均作为实测观测，不能称完整ledger访问。audit与summary的计算及输出字节一并计入阶段wall。

起止、父子指纹必须相等；绑定B3代码、规格、合同、测试、B2源/配置及report/completion，复用B2/B1原pin。指纹是实际仓库导入集与选定外部依赖，非完整生产环境闭包。独立审计不调用writer或PYPOWER；父参考和子重放比较完整科学state。当前post完整F/X的业务必要条件失败保持，aggregate_contract_release=false，不能由step接受转成完整合同交付。

## 资源与失败边界

依据B2整链12.327秒、B3针对测试约13–21秒及599/362点计算倍数，当前整套预计15–40秒；固定总wall60秒、child15秒、父后代采样RSS512MiB、全部输出32MiB、单文件2MiB。并发仅父+一个child。父每阶段/小时检查、child轮询0.05秒、每秒心跳；child15秒未完成、父60秒或RSS/存储超限即停止本包并保留失败，无自动延期。最终SHA核验后再检查资源，越界即追加failure使completion无效。

资源采样允许child刚rename导致已枚举pending消失；最终inventory仍严格检查全部路径、类型、目录层级、大小和SHA。同步导入/计算/I/O与采样之间可能越界，均为合作式观测，不能声称OS硬配额。记录脚本LAUNCH至最终输出wall及各阶段wall；解释器启动前outer成本单列未知，不以工具等待时间代替。RSS为采样峰值。completion后阅读报告/核查文件单列supplemental，不倒写原清单。

close/readback注入在实际写入、flush、fsync的路径上发生，保存失败证据和关闭重开成本实际测量；它们不是断电或真实坏盘。阻塞I/O、kill/清理、failure报告本身失败、平台目录持久化、一般网络/SCED/AC及完整合同事件时序仍UNKNOWN或未覆盖。普通故障测试覆盖其他发布阶段、初始化失败、证据损坏、未知提交与重复终结；不混入本次测量。单个599点合成例不闭合C的主实验预算，不决定D/E规模或授予正式运行权限。
