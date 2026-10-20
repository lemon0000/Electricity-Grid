# RQ2 跨小时验证续接交接（2026-10-20）

当前主线是完成 RQ2 跨小时验证，再准备本轮正式科研实验。旧 hour-0 `chain_07`、两小时链及其已保存开发证据继续复用。此次 Git 同步保存当前仓库开发快照；Common/source-factory 草稿的剩余 findings 保持 OPEN。

仓库：`D:/CUHKSZ/Research Project/electricity-grid`  
分支：`experiment`  
远端：`https://github.com/lemon0000/Electricity-Grid.git`

先按 `AGENTS.md`、`agent.md` 读取适用规则，再读执行计划、blocker register 和本目录证据：

- [开发验收数据](development_acceptance.json)、[验收记录](acceptance_report.md)
- [整链性能复核](workflow_performance_review_readable.md)
- [独立补验](connected_03_postcheck.json)、[最终绑定核对](final_verification_03.json)
- [只读开发复核](documentation_review_summary.json)
- [下一阶段工作清单](phase_boundary_next_step_v1.md)

`connected_03` 已完成 **3 个模拟小时、7 个 paired lane-hour**，包含 3 个 fake normal Windows Jobs、15 个 normal stages 和 34 次 fake selector capture。退出码为0；pytest耗时1307.07s，外层墙钟1314.969s。模拟时域与计算耗时分别报告。

已覆盖事故延续、首个修复小时G1上限24MW，以及h0/h1共同Rref产生的5MW request。h1 CFE Actual的timeout仍有feasible incumbent，但保持`actual_unresolved`；business/Actual两条carry均停在h0，其他lane继续。缺h3 source时保留pending attempt，没有第四个normal Job或额外selector。

关闭前独立checkpoint保存关键heads、科学对照及文件SHA；同进程clean-close后只读重开完整重放通过，444个owned文件名称/SHA一致。unit06六项通过并按AST/原helper字节复用；继承36+23项guards及1279个实现/测试/config pins复用，1299个启动source pins未变。当前三小时范围的独立PRE_SEAL复核无剩余具体finding。

本包`formal_result`、`formal_execution_ready`、`resource_admission`、native authority、`full_192_hour_execution_verified`均为false，real native calls为0。writer冷重建、persisted atomic-live及crash durability仍未证。当前Git同步保存开发证据，seal和正式运行权限按各自门禁处理。

紧接着应完成边界验收矩阵和有依据的整链预算：

1. 从冻结规格、配置和原FSM推导hour167→168、携债进入follow-up、恢复完成后结束、到上限仍携债及缺源等案例；保留`E=168`、`F<=24`合同与诚实右删失。
2. 核对完整任务DAG、重复prefix重放次数、合法证据复用及必须fresh重建的部分，固定总wall/RSS/storage、活动判据与超限停止条件。当前3h API/prefix权重32/64、parent inspect/权重64/128，排除独立historical/snapshot/anchor；单Reader最大33.283s，完整双Reader batch_source最大65.255s。
3. 预算和科学不变量有证据后，按原时域合同连接验证phase边界与episode终结；再完成具体科研包、其余正式门禁、封存、fresh official review及具体运行授权。

已有hour0/两小时/三小时主体及补验按绑定复用；后续实现采用独立DRAFT successor，保持已保存原件、失败记录及冻结科学合同。normal writer尚不支持关闭后的可写重建，当前saved prefix只按其已有只读证据使用。

实际case保存在Git工作树之外，下一对话在同一工作站可继续读取：

`D:/h1_outage_connected_03_non_authoritative/test_three_hour_connected_outa0/`

这里包含`outage_chain_result.json`、`external_preclose_checkpoint.json`、timing、bookends及三个owned roots。旧失败和开发case同样保留在本地；仓库中的request、postcheck与SHA maps记录其路径和作用域。同步时未观察到活动研究Python/solver；新对话先重新核实进程、Git及终态。

```powershell
git status --short --branch
git branch --show-current
git remote get-url origin
git log -1 --format="%H %s"
git ls-remote origin refs/heads/experiment

Get-CimInstance Win32_Process |
    Where-Object {
        $_.Name -match '^(python(w)?|gurobi_cl|cplex|ipopt|highs|scip)(\.exe)?$'
    } |
    Select-Object ProcessId, ParentProcessId, Name, CreationDate, CommandLine
```

以本地HEAD、远端实际hash、工作区状态及PID/creation-time核对同步与进程终态。先阅读现有绑定和保存证据，再执行下一阶段；每次实验启动前完成`agent.md`第9节整体性能审查。
