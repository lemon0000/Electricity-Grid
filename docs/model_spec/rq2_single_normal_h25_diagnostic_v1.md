# 单 normal 的 H25 开发诊断候选

状态：DRAFT_NONAUTHORITATIVE。一次真实25小时 normal 求解的准备，不是正式实验协议或运行授权。

当前进度：用户授权的单次诊断已完成，结果保持`replayed_unresolved_normal`；详见末节。

## 本次解决的问题

旧完整 episode 资源清单要求每个 normal 都被真实 episode 引用，不能添加占位 episode 来启动单独诊断。
`scale_normal_budget.SingleNormalResourcePlan`明确只有一个 NormalWork、一个 TaskEnvelope 和一个 SerialResourceBudget。
独立报告 schema 为`rq2_single_normal_resource_contract_v1`，normal_tasks=1、episode_tasks=0、solver_calls=1。
报告完整绑定三项声明；声明一致不代表资源已验证、normal最优或获准执行。旧workload/resource接口保持原样。

新类型通过既有source、固定transport、worker和父控制器传递；不新增求解算法、监督器或恢复路径。
`budget_for_task`精确区分新旧plan类型，重新计算资源身份；`bind_plan`继续核源输入、split、小时与UID。

## 具体候选

- 配置：`configs/rq2_scale_normal_h25_600s_development_v1.DRAFT.yaml`。
- 请求：`configs/rq2_scale_normal_h25_600s_request_v1.DRAFT.json`。
- 入口：`experiments/audit_rq2_scale_normal_h25_v1.py`，默认仅检查；`--execute-development`才进入执行。
- 新目录：`results/tables/rq2_scale_normal_h25_600s_attempt1_non_authoritative`；已存在即拒绝，不重试或覆盖。
- 原始输入和机组初态、来源实现及assembly/binding pins与旧H25声明一致，158 UID、25小时、22275变量/28004约束。
- 保留Gurobi 13.0.2、单线程、gap=1e-8、三项容差1e-9、seed=0；native时限从15秒改为600秒。

这是独立预算下的新开发诊断，不延续旧证书或声称可比性能试验。TIME_LIMIT、缺返回或无接受最优解继续未决。
机组初态与业务参数的证据属性由原声明保留；本次不把机制输入变成真实观测。

## 完整预算

| 分配 | 声明 |
|---|---:|
| native solver | 600秒 |
| 数值内核wall | 720秒 |
| execute worker | 900秒（含额外180秒来源/归档等开销） |
| audit worker | 300秒 |
| 两阶段quiet | 每阶段3秒 |
| 父端核验/第二次零solver回放 | 180秒 |
| pipeline合计 | 1386秒 |
| normal任务envelope | 1500秒，non-solver allowance 900秒 |
| 任务外serial监督 | 额外20秒，总声明1520秒 |
| 每worker Job/process commit | 1 GiB |
| supervisor追加commit / reserve | 各256 MiB，共需1.5 GiB |
| archive / execute scratch / audit scratch | 256 / 16 / 16 MiB |
| disk reserve / 全部额外磁盘 | 64 / 352 MiB |

pipeline非solver投影为1386-600=786秒，小于900秒。任务内父端180秒与任务外20秒分别计入，不重复冒充。
数值及父端working-set各声明1 GiB；working set与commit不同，前者不证明后者充足。
源记录上限32 MiB、数值证据16 MiB；归档预算覆盖既有固定证据上界。
这些是待真实任务检验的分配，不保证600秒可取得所需最优性，也不保证各阶段实测成本均在限内。

## 验证与授权边界

单normal资源及旧数值回归61项通过（55.52秒）。覆盖逐项预算短缺、来源身份、传输伪装/缺字段、
旧plan仍拒绝空episode，以及真实一秒上限微型normal与零solver独立来源回放。
入口与父控制器首组合为37通过、1失败（150.83秒）；失败来自新测试只伪造exists而无真实目录，
不是控制器故障。改为test-owned真实目录后入口13项通过，再补8个外层漂移反例后最终21项通过（13.99秒）。
父控制器25项在该组合中全部通过，包括真实微型子进程execute/audit及失败窗口；未因入口夹具修正重复运行。

真实H25只读来源重建34.7656秒，确认25小时、158 UID、input identity
`d9959966c52fe618e73974fc53203ad2caed5169bd7f360fc79e0ecafd06780c`；四个执行入口封住，solver_calls=0。
产物位于`results/tables/rq2_scale_normal_h25_600s_preparation_v1_non_authoritative/`：

| 文件 | SHA256 |
|---|---|
| preparation.json | `6ebbfe393129f5b29dc1daaef3f31f7a62ccc565585bc39cc66a18fc1b0c6c7c` |
| followup.json | `26d78361f4fab69aed6e569eda64fae1ffba1e79910e21afeede24933f27c693` |
| 候选配置 | `a76b9a31843fbb98c2f1e4eb33c22e7aa7084b9609fd2607241bd962494b5066` |
| 请求packet | `da633e1120ed768ab1b6a8d1030338c328bd9f56e6cd2917e4305bdf48ac2ade` |
| 最终runner | `f928ee049c7443f61303f1b859095319a410a06791680ccb4fc56e6f347a63c5` |

preparation保留修复外层检查之前的runner pin；followup绑定最终runner，并重验旧结果目录25个文件hash全部一致。
runner在调用前及返回后重核自身、配置、packet、旧基线声明，发生漂移时不输出CLI成功报告；
若漂移发生在执行期间，内层控制器已写证据保留，不能将外层核验失败当作无调用或自动重试理由。

短验证命令（compute Python，均带`-B -m pytest -q -p no:cacheprovider`）：

```text
tests/test_rq2_single_normal_resource_plan_v1.py tests/test_rq2_scale_normal_v1.py
tests/test_rq2_scale_normal_h25_declaration_v1.py tests/test_rq2_scale_normal_controller_v1.py
tests/test_rq2_scale_normal_h25_declaration_v1.py
```

最终只读核验命令（不执行solver）：

```text
D:/Miniconda3/envs/compute/python.exe -B experiments/audit_rq2_scale_normal_h25_v1.py --declaration configs/rq2_scale_normal_h25_600s_development_v1.DRAFT.yaml --expected-sha256 a76b9a31843fbb98c2f1e4eb33c22e7aa7084b9609fd2607241bd962494b5066 --expected-script-sha256 f928ee049c7443f61303f1b859095319a410a06791680ccb4fc56e6f347a63c5
```

默认只读检查已确认目标目录不存在、当前host余量满足声明；这是瞬时观测，没有预留资源。
独立限定PRE_SEAL复核已闭合外层漂移finding；reviewer独立复跑入口21项通过（14.05秒），
最终只读入口exit 0，并复核followup所列5文件及旧结果25文件hash一致、目标目录不存在。
这是开发诊断的限定预审，不是official verdict或正式实验准入。
启动前必须复查来源/pins、host及活跃任务。依照AGENTS.md的长solver授权规则，须用户明确授权本次长诊断；
该授权也不打开正式实验或科学协议门。全支持计算路线、完整连续服务验收及训练容量/holdout绑定继续开放。

## 已授权单次执行结果（2026-09-28）

用户明确授权后，按上述exact配置与runner pins追加`--execute-development`执行一次。
任务正常结束，execute/audit退出均为0且Job静默；总wall 537.953秒，execute 317.266秒、audit 109.719秒，
父端累计110.968秒。solver_calls=1、call_count_complete=true，无重试。来源独立重建和数值回放一致。
最终结果仍为`replayed_unresolved_normal`，不能据native的optimal终态称normal已认证。

| 数值证据 | 本次记录 |
|---|---:|
| canonical objective | 1388837.913859345 |
| native LB | 1388837.9138593453 |
| native UB | 1388837.9138593455 |
| 报告界差相对目标 | 1.6764421631237928e-16 |
| 最大残差 / 整数违约 | 2.788453912216937e-10 / 0 |
| native termination / solution status | optimal / optimal |
| assignment_valid / 审计optimal标记 | true / false |

拒绝原因是现有严格`lower <= objective`谓词为false：LB比canonical目标高1 ULP
（2.3283064365386963e-10）。记录中native_objectives为空；上界比目标高2 ULP，仍在原1e-9绝对核验限内。
这是界/目标一致性拒绝，不是TIME_LIMIT或数学不可行。

后续零solver诊断重新绑定来源和canonical结构，按保存的binary64系数与赋值对9050个目标项作精确有理数点积。
精确目标仍低于LB约3.37e-10；其最邻float与fsum结果均为原canonical目标。因此不能只改求和顺序、
取min(LB,objective)或加epsilon就宣称修复。赋值通过既有残差门也不等于数学精确可行。
本次不改变旧验收谓词、结果标记或阈值；后继需先形成可解释的界/目标数值合同和独立回放反例，
保留这一attempt，再按风险级别审阅必要变更。没有追加长求解。

证据：

- attempt `result.json` SHA：`63c235412a86c43f92d7a37047ff99b1693e579b323e62794980e25113344103`。
- source `normal_record.json` SHA：`9f40ab3aede1115c0dd229aba410b8f2739f383b26e76c6593d129f7072fa00a`。
- 独立目录`results/tables/rq2_scale_normal_h25_600s_diagnosis_v1_non_authoritative/diagnosis.json`，
  SHA：`2e81a1b937ba6f02fcc67ab4d824d89330fc4c9c96f0ee0931745b87dbd7cd45`；诊断42.47秒、0 solver。
- 同目录`inventory.json`保留已完成attempt文件hash，核旧结果25文件均未改变。

最初`diagnosis.json`为本次ad-hoc派生诊断。已补固定只读生成器
`experiments/audit_rq2_h25_objective_consistency_v1.py`，SHA
`4c420da0e2202c2d75748f982c8341030ccb88b5fa7a8c20d157088854484f86`；固定result/record/packet pins，
重建结构并绑定有序9050项(varname, coefficient.hex, assignment.hex)及constant摘要
`726f778357562db949798e662fa70c0424e52c871f7f76bc8334c4dc6881beb7`。
复现报告同目录`objective_reproduction.json` SHA
`7f9fe487cf662d64ce273b4381d19b48f8d918e8f7cea2fe098bfcb39deff9c8`，与原诊断的精确目标、界差、
项数、原目标/界及fsum逐字段一致，0 solver；原ad-hoc文件保留。只读复现命令：

独立限定复核确认该生成器/输入inventory绑定的复现finding闭合；这不补足native界来源或最优性证书。

```text
D:/Miniconda3/envs/compute/python.exe -B experiments/audit_rq2_h25_objective_consistency_v1.py
```

独立结果审计确认：本次拒绝与数值/来源重放一致。下一项应建立版本化objective/bound provenance合同，
分别记录direct Gurobi ObjVal/ObjBound、Pyomo lower/upper和canonical/exact目标；用tiny例覆盖
最小化方向、负/零目标、optimal/TIME_LIMIT、1 ULP交叉与转换路径，再审查可证明的处理方式。
当前native_objectives为空，不能从本次记录反推未保存的direct native通道，更不能补造这些值。

资源实测仅为本次开发观察：execute/audit Job峰值commit分别667656192/841408512 bytes，
父进程生命周期峰值working set为874049536 bytes。父commit无硬限制且working set不等于commit；
`whole_task_resources_verified`继续false，不能把本次正常退出解释为完整资源认证。
