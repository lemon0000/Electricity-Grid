# 连续服务合成前缀诊断交付 v1

日期：2026-09-13。状态：`DRAFT_NONAUTHORITATIVE`。
本项将已经验证的固定因果策略导出为本地可复核的诊断包，服务于RQ2连续时序机制开发。
配置为`configs/rq2_continuous_prefix_diagnostics_v1.DRAFT.yaml`，入口为
`experiments/export_rq2_continuous_prefix_diagnostics_v1.py`，测试为
`tests/test_rq2_continuous_prefix_diagnostics_v1.py`。

## 固定场景与证据边界

所有数值、初始零状态、deadline及策略均为机制假设；没有把公开数据填入合成模型。
anchor中的来源名称、哈希和holdout标记仅是合成身份，不表示真实文件哈希或已注册数据split。
配置中单一会计期覆盖整个观察窗口，事件、休息时间、调用次数、能量及债务在小时24/25间连续携带。
四臂在每个场景下使用相同当前观测，策略仍逐小时接收输入，输出包生成器持有的后续序列不传给策略。

共同输入：小时23/24/25调用grid=0.125，CFE默认为0；occupancy=1、eta=0.8、恢复headroom=0.3125，
已知deadline默认为出生小时+3。完整参数保存在YAML，以下为预设诊断场景，不是参数搜索或正式对照实验。

| 场景 | 配置变化 | 解析检查（joint-correct） |
|---|---|---|
| normal_recovery | 48小时，使用共同输入 | 小时24/25/26/27债务为1/4、3/8、1/8、0 |
| insufficient_recovery | business headroom始终0 | 末债务3/8，三个cohort逾期；合法零恢复仍提交小时 |
| unknown_deadline | deadline为空 | 恢复清偿后仍保留三个unknown deadline |
| late_recovery | 小时26–29 headroom为0 | 恢复后余额归零，三个历史逾期保留 |
| b6_shared_rejection | 同时CFE调用0.125 | B6小时26分离恢复各0.3125，共享0.625超限，保留小时25债务3/4 |
| censored_prefix | 只配置25小时 | 末债务3/8，三个已接受cohort的deadline均未到达 |

前三个单服务投影场景中，CFE-only没有调用债务；如实保留该结果。B6反例不预设其在其他机制或最优策略下的表现。
每个完整场景48小时，截尾场景25小时；共265条场景输入、24个场景与臂组合。
B6共享拒绝场景提交26条观测、接受25小时、后续22小时未提交；其余组合运行到各自配置窗口末。
因此逐小时记录共1038条。这些计数是软件交付规模，不是独立经验样本量或概率分母。

## 文件与重放合同

交付位置：`results/tables/rq2_continuous_prefix_diagnostics_v1_non_authoritative/`。

| 文件 | 内容 |
|---|---|
| config.json | YAML解析后的完整配置 |
| inputs.jsonl | 每场景完整输入序列与mechanism_assumption标注 |
| records.jsonl | 只含提交前缀：原观测、尝试动作及其轨道范围、已接受物理动作、阶段/错误、动作前状态、规划候选、已提交物理/规划状态与逐时summary |
| summary.json | 按场景与臂分列的submitted/accepted/unsubmitted、最后提交小时、拒绝小时/阶段、末债务与cohort状态 |
| evidence.json | 输入、标识符和派生诊断的来源边界；formal/claim/security均false |
| README.md | 从同一summary机械生成的浏览表 |
| diagnostic_manifest.json | 非权威文件清单、字节数、SHA256、实现依赖及Python/PyYAML版本 |

精确Fraction编码为`{"numerator":"3","denominator":"8"}`，整数使用字符串避免外部JSON读者整数精度损失。
物理状态仍保留原float，不把float近零容差用于抹去cohort精确余额。null deadline与尚未观察的到期短缺均保留null。
快照包含anchor、envelope、事件状态和完整cohort账；不递归序列化B6的全部历史指针。
验证从初始状态逐小时重放，在内存中重建规划历史约束。该文件格式不是恢复运行的checkpoint接口。

`planned_candidate`可以晚于提交状态，但仅是诊断。拒绝时`accepted_physical_actions=null`，两个提交状态均停在此前小时。
拒绝小时及之后实际服务动作和deadline结果为未评价；已接受前缀的right-censoring不替代完整失败轨迹。
错误保留现有状态机的阶段与原文，不从错误字符串推断hard-grid/CFE经验违约类别。

生成入口只接受固定小型配置，最多48小时/场景，无solver或网络操作；目标目录须明确以`_non_authoritative`结尾。
已有目录一律拒绝覆盖，文件以exclusive create写入，manifest最后写入。中断留下的半包不通过验证，程序不自动删除或续写。
这是普通DRAFT交付，不产生production inner/outer、seal、lease、review receipt或运行授权。

离线验证检查固定文件inventory、普通文件类型、依赖字节与成员哈希，然后按绑定的本地配置完整重放，逐字节比较全部六个成员。
因此只修改文件并同步更新其清单哈希仍不足以通过。验证依赖本地实现及相同Python/PyYAML版本；不是独立模型正确性证明或密码学签名。

```text
python -B experiments/export_rq2_continuous_prefix_diagnostics_v1.py
python -B experiments/export_rq2_continuous_prefix_diagnostics_v1.py --verify-existing
```

## 验收与后续

验收包括解析债务/事件边界、unknown/late/censoring、B6失败原子性、
文件缺失/额外文件/半包、依赖变化、重新哈希后的输入或summary篡改，以及拒绝覆盖已有目录。
沿用此前模型的功率平衡、状态和因果性测试；本轮不修改其代码、配置或已记录字节。

本地公开数据交付的7个成员哈希已复核匹配，旧四阶段共12个config/code/test绑定匹配。
该检查不重新执行公开数据处理，也不将真实业务参数的null或正式协议门更改为ready。
旧v5 symlink环境限制本轮未重跑，仍保留未验证状态。

下一项是定义拒绝后的实际服务动作和债务递推合同，再决定如何记录完整失败轨迹；
真实deadline、非零carry-in、异质逐服务deadline和正式split/coupling仍需独立依据。
本交付不关闭连续科学协议、full-input、formal/result/claim/security门。

## 本轮实际验证记录

解释器：`D:/Miniconda3/envs/compute/python.exe -B`。编辑前和生成前检查git状态及相关进程，未发现活跃正式运行。
唯一写入代理新增配置、导出器、测试、本文及7个交付成员；向计划和blocker追加状态，未改此前模型或结果。

主线程针对性命令`python -B -m pytest -q tests/test_rq2_continuous_prefix_diagnostics_v1.py`最终为`12 passed in 8.67s`。
相关七文件回归在新增最后一个篡改负例前为`193 passed in 36.27s`；最终字节的独立只读`sol_reviewer`复核为
`12 passed in 8.33s`及`194 passed in 37.86s`。七文件命令：

```text
python -B -m pytest -q tests/test_rq2_continuous_prefix_diagnostics_v1.py tests/test_rq2_continuous_causal_policy_v1.py tests/test_rq2_continuous_four_arm_replay_v1.py tests/test_rq2_continuous_debt_cohorts_v1.py tests/test_rq2_continuous_multiday_service_v1.py tests/test_rq2_joint_deliverability_boundary_v1.py tests/test_rq2_joint_deliverability_continuation_audit_v1.py
```

独立审查另按arm投影核对1037条accepted记录的功率平衡与`debt_t=debt_(t-1)+call-0.8*recovery`，
唯一B6拒绝记录的execution/planning均未提交。当前未发现开放实现或科学语义finding，结论仅为DRAFT范围的pre-seal findings。
上列生成命令与`--verify-existing`均已运行，返回24组合、1038记录、`replay_matches=true`、`formal_result=false`。
独立审查亦对落盘包运行只读验证：exact 7个regular files、无link，成员hash/bytes及实现依赖匹配，README UTF-8正常，未见新增finding。
`git diff --check`通过。本轮没有正式实验、solver、下载、付费查询或仓库清理。

SHA256开发绑定（不是seal）：

| 文件 | SHA256 |
|---|---|
| configs/rq2_continuous_prefix_diagnostics_v1.DRAFT.yaml | `f1dcb97b2ae1127750d934a4e8929ea4915471940f3b8e1cf0107fe5d9bf43db` |
| experiments/export_rq2_continuous_prefix_diagnostics_v1.py | `b56cfe879c71aae770139a0f81c1d1f7eed5e9665e62a2ae4297eb3d5d189839` |
| tests/test_rq2_continuous_prefix_diagnostics_v1.py | `d896bc3f11d7684f80f9032acd5e653eded322d6b475e9647c09ce4a07377f83` |
| results/tables/rq2_continuous_prefix_diagnostics_v1_non_authoritative/diagnostic_manifest.json | `c67ee1c19c27a27461ca8af73cae67e3a9fbb7b2e2bd00b48c8a9b009d50a263` |
