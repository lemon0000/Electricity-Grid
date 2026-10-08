# H1 单小时完整阶段校准运行包

这是 R3 calibration candidate 的验收规格。生命周期状态以对应 canonical outer 为准；开发、pre-seal、production seal、official review 和运行分别验证，此文件不授予执行权限。

## 范围与实现

`normal_h1_full_collector.py` 使用完整 H1 workload、resource envelope 和 full anchor；保持 cost → 73 commitment UID → 158 generation UID 的严格顺序、原 normal numeric predicate、assignment residual/integrality 1e-9、native gap 1e-8 和严格等式锁。逐阶段顺序仍是已持久 intent → native raw → 数值审计 → checkpoint/anchor → raw 原子提交与 fresh readback → 下一阶段。没有修改旧短预算或冻结模块。

`normal_h1_full_job.py` 将独立 full collector 接入已有 `declared_task_process` Windows Job。具体 calibration package 强制单小时 training、232=1+73+158 stages；通用 collector/Job core 可接受较小的合成开发例。worker 从固定 current-source declaration 重建原点 packet；全部创建、native、存档、close/fresh reopen、来源复验均处于同一个受监督 Job。重开使用独立最终 anchor SHA，且显式禁止 solver。

父控制器在 child release 前持久写 request、intent、launch identity 和 PID/creation filetime，完全静默后才读取 worker result。原始 typed process observation 在关系检查前保存；exact observation type、process identity、PID、creation、资源字段类型、退出原因、Job commit peak 和权限位均检查。身份错配、deadline、非零退出、非静默、资源错误和错误结果均不写 `job_checks.json`。结果只报告本次开发/校准观察，`whole_task_resources_verified`、`native_execution_authenticated`、`formal_execution_ready`、`formal_result` 均为 false。

## 单次执行门

`normal_h1_calibration_gate.py` 验证 exact sealed outer、独立 inner manifest、canonical request、完整本地 `src/**/*.py` 闭包、worker、prepare script、定向测试、pre-seal evidence 和 immutable one-shot lease。inner 成员与 outer 去除 inner 本身后的成员精确一致，避免循环 hash。所有成员均核验 SHA256。具体包在 core 声明检查之外强制完整 232-stage training inventory。

public controller 另需独立 pin 的 official PASS receipt 与单次用户运行授权；二者绑定同一 outer，授权还绑定 request、root、具体 action，禁止 retry。成功复核后 exclusive-create、fsync、fresh-read 独立 claim 文件；不修改 sealed lease。claim 写入不确定、controller 失败或 child 中止都不会自动重试或恢复。worker CLI 在读取来源/调用 collector 前复核 consumed claim，父进程在读取结果后再次检查 sealed bytes。

receipt 和 authority 是由调用者在本地受信根保留的独立 pin 记录，不是密码学签名。official review 必须由新的只读 reviewer 对实际 sealed outer 给出；pre-seal 审查不能产生该 receipt。临时测试 gate 位于 pytest tmp，不能用于真实运行。

共享 worker core、supervisor、full collector 的两个 native 入口均强制 consumed gate；没有仅凭私有函数命名放行的路径。full collector 另核对具体 work/resource/serial/limits、fresh source packet、request SHA、来源身份及 collector/anchor root。合成测试显式 mock gate 校验并禁止 solver，隔离 test-only worker 仅消费保存的 raw。实际 worker 使用既有 licensed environment allowlist，仅传 Windows/Python 必需路径、scratch、固定线程项和显式本地 GRB_LICENSE_FILE，不继承父进程其他凭据。

`job_checks.json` 绑定 request、intent、launch、child identity、process observation 的独立 SHA，保留实际 Job elapsed 与 commit peaks。它尚不包含物理磁盘配额证明或完整多日预算认证。

## 具体校准草案

复用已有 shape 的来源选择：training power/workload raw hour 0、outage seed 20260822、dc_bus 108。该选择只服务于资源校准，不构成完整支持、共同观测配对或工程可交付结论。

| 项目 | 草案值 |
|---|---:|
| 完整阶段数 | 232 |
| 每阶段 TimeLimit / threads | 5 s / 1 |
| solver 全库存 | 1,160 s |
| non-solver allowance | 2,440 s |
| task wall / elapsed / quiescence | 3,600 / 3,598 / 2 s |
| process / Job commit | 2 GiB / 2 GiB |
| archive content cap | 4,031,840,256 bytes |
| archive overhead / scratch | 256 MiB / 256 MiB |
| commit / disk reserve | 2 GiB / 2 GiB |
| controller allowance | 60 s |
| actual model variables / terminal constraints | 891 / 1,211 |

这些时间和 overhead 是校准 proposal，不是已测充分性。Job 强制 commit，轮询 deadline/host reserve；磁盘没有 hard quota。准备脚本仅重验固定来源和首末 shape，solver_calls=0。保留全部原始结果、scratch、claim 和失败状态。

## 冻结验收矩阵

1. 完整声明与实际 source/shape 一致，资源精确绑定；旧预算/类型不能偷接。
2. exact full anchor 的 intent、stage checkpoint、terminal checkpoint、outcome 写前/已持久后异常均阻断后续效应；重开不重试。
3. 保存的三阶段 raw 通过 worker 完整重放、独立最终 anchor 重开及来源复验；无新增 solver。
4. 真实 Windows Job 使用隔离 test-only worker 覆盖正常退出及 `os._exit`；失败仅保留 unknown。
5. Job observation 身份、数值字段类型、权限位和结果 receipt 的反例均 fail closed；非静默时不读结果。
6. 真实 RTS 232-stage inventory 能创建完整 collector，首个模拟 capture 异常后持久 pending_unknown、无 projection、不可重试。
7. gate 覆盖闭包漂移、错误 outer/receipt/authority pin、非 PASS、非 fresh review、缺授权、错 root、重复 consume、部分 claim、短 inventory 与 holdout 拒绝。
8. source/code/test/旧封存成员 hash 保全、相关回归、独立 pre-seal 闭合后才 seal；official review 使用新的 reviewer。

## 保持开放的研究门

单小时校准不解决完整研究资源库存、父多日运行扩展成本、共同 Rref/A 发布、完整支持 LB/UB 或正式实验结果。校准失败、timeout、缺 raw、strict lock 数值拒绝不得改写为数学不可行，不得放宽冻结数值门或自动申请重试。
