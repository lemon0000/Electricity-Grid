# B2开发验证：固定DC走廊、F/X与实际业务轨迹

2026-10-22，`DRAFT_NONAUTHORITATIVE`。按[B2网络规格](../../../../docs/model_spec/staged_deliverability_network_development_v1.md)及[有界执行合同](../../../../docs/plan/staged_deliverability_b2_development_contract_v1.md)完成一次开发诊断。复用仓库网络数据结构与PYPOWER `makeBdc/dcpf`，没有优化solver、外部下载或新native校准。

本包是两母线、两并联线、单源固定平衡的合成DC走廊。t=1为小时开始前已知的计划性单线退出；不提供一般网状网络、突发故障纠正响应、SCED、AC或工程认证。B1 report及其记录的九个source pins保持原字节。

## 连续路径结局

| 给定计划/清洁路径 | 实际业务与网络路径 | 任务结局 |
|---|---|---|
| 按期/早恢复 | t=−2…7共10小时；实际点、X响应及源小时爬坡满足条件 | t=1延期0.2 MWh_c，t=2补完，主要任务无逾期 |
| 按期/晚恢复 | 同样10小时；t=4补做后的P=1.3 MW满足当前接入额度与实际网络条件 | t=3末逾期0.2 MWh_c；t=4补完仍保留永久逾期记录 |
| 延期/早恢复 | 已提交至t=2；t=3参考接入权准入拒绝，不生成业务提案、不推进物理出力/业务/X状态 | 原0.2 MWh_c债务保留；尚未执行到t=3末到期结算，按期限前右删失报告 |

延期t=3的P^0=1.05 MW，而未投运时C=F+X=0.8 MW，接入需求缺口0.25 MW；实际正常网络H=1.35 MW，因此真实网侧请求g=0。不能沿用B1标量替身中的0.25 MW网侧请求，也不能把本固定参考准入策略停止当作所有可能策略不可行。

t=1实际P^0=0.75 MW，单线退出H=0.625 MW，原始g=0.125 MW；活跃X=0.15 MW。网侧与CFE分别延期0.1 MW_c，实际X调用0.125 MW，只有一次X事件、累计0.125 MWh。网侧单独削减后P=0.625≥F=0.6 MW；自主CFE削减使最终P=0.5<F仍合法，F是接入权而非取电下限。背景负荷0.1 MW另计，实际源出力0.6 MW。

## 完整合同与实际轨迹分别解释

| 检查层 | 保存结果与含义 |
|---|---|
| 网络容量边界 | 正常pre/post为1.35/1.9 MW；任一单线退出为0.625/0.9 MW。PYPOWER与独立Fraction分流/KCL核对 |
| 完整F/X网络条件 | 正常核完整C=0.8/1.3 MW；两个声明退出分别核F及C−c_hat。最小调用pre/post为0.175/0.4 MW；本固定平衡下存在数值网络见证，F受保护 |
| 完整合同业务必要条件 | t=1的full-C反事实h_hat=0.175 MW，与实际h=0.125 MW分开；q_hat=(0.175+0.175)/1.25=0.28 MW_c>D。post仅故障调用0.4 MW就超过aD=0.25 MW；登记整段X=0.5 MW也超过aD，即使没有CFE请求仍失败 |
| 时序合同背书/释放 | 没有建立完整F/X的反事实任务与事件时序背书，且已有必要条件失败；所有aggregate_contract_release均false。实际轨迹通过不替代完整合同可交付结论 |

`business_prefix_assessment`及`tasks`沿用未修改B1的账本摘要与scope字段，仅解释已接受业务前缀；其`not_assessed_scalar_stub`不承担本包网侧判断。完整网侧证据位于各reference/terminal中的`records[].contract`、`reference_point`、`actual_point`、X/source状态及独立`audit`。

## 测试、重开与工件

- 最终6文件相关回归：198 passed、1 skipped，pytest 15.24 s。覆盖DC边界、非连续母线ID、孤岛拒绝、阶段投运、独立服务记账、整段X与逐场景必要条件分离、事务回滚、部分结果篡改、账本/预算carry、期限、checkpoint前缀绑定及`python -O`。跳过项是本机缺少创建真实symlink的权限；目录拒绝及lstat普通文件检查已覆盖，未声称实际symlink负例已执行。
- runner测试覆盖错误attempt/stem、独占输出、大小/资源拒绝、最后事件失败、清单篡改、额外文件/目录、严格JSON/schema与数值检查。首次回归命令曾含不存在的测试路径、未收集测试，随后更正；不计为通过或实验失败。
- 三例各保存t=1末checkpoint；3个fresh子进程重放4小时前缀，再运行后缀至观察结束或延期拒绝。全部state/audit及父/子起止指纹一致，三个child均exit0；阶段/重开不重置债务、永久逾期或X预算。
- 实际52个网络小时尝试、50个B1业务步骤、362次PYPOWER潮流；独立审计52网络小时/50业务小时和362次已保存点（181父参考+181子重放，含重复）。6次业务装载，没有隐藏的每小时增长前缀审计。执行合同v1中的“362个已保存唯一点”为措辞错误，按[运行后计数澄清](../../../../docs/plan/staged_deliverability_b2_count_clarification_20261022.md)解释为调用/审计次数，不代表独立数值样本；已绑定合同及运行工件原字节保留。
- 实际32个仓库文件、7个选定外部文件及环境版本绑定，包含未修改B1九pin；起止及读回一致。这是实际导入集和选定依赖指纹，不是完整环境闭包。
- [completion.json](completion.json)绑定15个先前工件的size/SHA，合计784,222 B；加completion自身为16个机器工件、786,700 B。完成标记严格读回校验后才输出completed；[report.json](report.json)自身仅标evaluated。[执行事件](events.jsonl)、[启动绑定](start.json)、各reference/checkpoint/terminal均保留。本阅读报告及后加verification.json是运行后说明，不改动绑定清单。
- 独立只读pre-seal核查与修复均为非权威开发审查，不产生official verdict、receipt、seal或formal-run authority。

## 实测成本与下一步

脚本完成打印elapsed为12.327220 s，completion写前快照12.315431 s；采样父+后代峰值RSS为268,181,504 B，约255.76 MiB。计时从脚本首部开始，包含本脚本导入及子进程启动；解释器启动前开销和启动器完整outer wall未独立计时，不能用工具的单次等待时长替代。

| 父阶段 | wall合计 |
|---|---:|
| 新进程启动、重开、后缀、审计与退出等待 | 8.583161 s |
| 连续执行（含逐小时资源采样/事件） | 0.529100 s |
| 父独立审计 | 0.044656 s |
| 两端源/环境指纹 | 1.304091 s |
| 参考与checkpoint保存 | 0.083131 s |

阶段值不覆盖全部导入、事件和报告开销，不能相加冒充完整wall。预算60 s/每child15 s、采样RSS512 MiB/总输出16 MiB均未越界；合作式保护不是硬配额。昂贵真实I/O失败、杀止/清理成本及主实验规模仍未测。

后续顺序已写入[B3/C及有限比较计划](../../../../docs/plan/staged_deliverability_b3_c_next_steps_v1.md)：先补连续终结与失败窗口，再闭合所选规模的完整成本，随后确定少量阶段方案比较、冻结策略留出和论文结果。当前B2证据只覆盖本走廊、当前策略及绑定规模；主实验资源、现实合同/参数、完整F/X时序背书和历史H1门禁保持各自未决状态。
