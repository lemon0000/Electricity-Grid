# H1 真实网络零求解规模与资源候选

状态：DRAFT_NONAUTHORITATIVE；仅开发构造探针。独立 schema、controller、worker 和结果目录；原 20 calls / 60 秒短求解门保持原值。

## 输入与测量边界

固定 RTS v0.2.3，training 两侧 raw hour 0、seed 20260822，来源凭据沿用已保存的独立 pin。DC bus 108 仅为本探针声明，依据旧公开 pilot 配置；不构成 v2 正式地点或样本选择登记。载入前后核验固定源文件；只将当前行送入 H1。

仅构造 stage 0 和 stage 231，后者使用 231 个零占位 lock，没有已验收锁值来源，可能不可行。计数对象为 Pyomo VarData / ConstraintData / standard_repn_after_fixed_substitution 的非零线性项；ranged row 计一个 ConstraintData。不是 native matrix、presolve、求解耗时、assignment 或数值证书。

报告绑定 Python/Pyomo/SQLite 版本、来源、网络、模型和实现哈希。parent 独立检查已知 232 stages、network pin、两端 stage identity、变量分类、锁行增量、全部负权限、时间、存储公式和本地 SQLite 上限。共享只在完整 causal key 相同时成立；没有测得命中率，也没有枚举未来 carry。

## 有界进程

Windows Job 原子关联后以 suspended 状态登记 PID/creation time，再 release；全过程 commit/headroom 观测，整个 Job 静止后才读取结果。探针预算 wall 60 秒、单进程 commit 1 GiB、Job commit 1.5 GiB、采样 0.1 秒、quiescence 2 秒；host commit reserve 512 MiB、disk demand 8 MiB、disk reserve 512 MiB。磁盘并非硬 quota，RSS 非硬限。request 64 KiB、结果 1 MiB；exclusive 写入并保留失败目录。

已知 solver 入口由 guard 拒绝；没有 native 调用。原 Job 原语的超时、后代进程、资源限制测试单独复用。该有限构造检查不授权任何真实 native 或正式运行。

## 本次观测

结果：`results/tables/rq2_normal_h1_shape_v1_non_authoritative/`。

- Python 3.12.12 / Pyomo 6.10.1 / SQLite 3.51.1。
- 两端均 891 variables：73 binary、818 continuous；1 fixed（包含在分类计数内）。
- 首阶段 980 constraints / 2789 linear terms；末阶段 1211 / 3381。
- 末阶段 231 lock rows / 592 lock terms。
- 两次模型构造分别约 0.1015 和 0.0977 秒；这不是全部阶段构造或 native 时间估计。
- Job elapsed 5.407 秒，peak process commit 257871872 bytes，peak Job commit 259145728 bytes；worker lifetime peak working set 285310976 bytes。只对应本次两个模型和来源校验。

## 已确认的架构 blocker

保持每阶段 16 MiB raw payload 上限的反事实公式，232 stages 单事件最坏为 3892576270 bytes；本机 SQLite SQLITE_LIMIT_LENGTH 为 1000000000 bytes。`current_one_blob_worst_case_persistence_blocked=true`：现单 BLOB 设计无法承诺保存该最坏事件。

192 小时内容外推为 753917760768 bytes（44544 stage slots）；这是超出现有短调用/24h域的未准入反事实内容上界，不是实测、磁盘预留、已实例化合同或执行授权。需要独立分块 journal/archive 设计及总量准入；不能通过加大短门或删除 raw reports 解决。

正式 per-stage/wall/threads/commit/storage/host 合同仍为 null。native 时间、全部阶段 build、audit、archive、replay、完整 episode 内存与 wall 仍未知。下一步优先开发版本化分块存储及故障恢复规格，然后才可形成具体 native 校准运行包。selection_registered / source_authenticated / formal_result / formal_execution_ready 均 false。
