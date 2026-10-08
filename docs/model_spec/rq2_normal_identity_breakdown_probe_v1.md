# H25 输入身份分段诊断

2026-09-27，DRAFT_NONAUTHORITATIVE。目标是定位 fast H25 normal 63.5284186 秒中尚未分离的身份复核成本，为保持原 60 秒门的后续优化提供依据。

新增 `experiments/diagnose_rq2_normal_identity_breakdown_v1.py`，沿用已验证的零 solver cost probe 进程监督结构：完整来源 prepare、独立新目录、固定 argv/environment、PID/FILETIME、120 秒含静默预算、768 MiB Job 上限、启动及静默后实现 pin 核验。旧 probe 和结果不改。

顺序计时包含 deepcopy、旧完整身份、新完整身份、输入 validation、dependency hash、encoding+digest、新 execution identity、fast 模型 build、scale、structure、snapshot、前述新旧身份的末端复核，共 13 段。三段拆分摘要必须等于完整新旧身份和外部声明输入摘要；模型使用 fast builder，数学模型、全来源与 22275/28004 规模保持。

这些段落是独立调用，互不重叠；完整 identity 与其三段拆分是分别执行的两次观测，不能将两者当成一次 identity 的可加分项。单次 fast build 内仍包含身份复核，其时间也不是纯 Pyomo 构建时间。13 段总和加来源 prepare 必须不超过 child elapsed。分段测量不代表 normal 内部精确归因，不能将之前运行和本次运行相减推断 solver 耗时。

所有 solver 入口在子进程内禁止；`solver_calls=0`、`model_builds=1`，无 assignment、完整 normal 或正式结果。此次只解决身份成本定位，solver create/solve/native evidence extraction 仍需独立开发诊断。

验收覆盖：真实 tiny 来源全链与旧摘要 oracle、确定性假时钟验证各计时边界、validation/dependency/digest 失败须在模型构建前拒绝、模型规模与 owned 输入突变、错误 timing inventory/NaN/超时总和、伪造来源元数据/authority、固定子进程上下文与失败边界、existing root 不覆盖。独立只读 pre-seal 审查闭合后才进行一次真实零 solver 开发测量。

## 开发验证

命令前缀：`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider`。

- `tests/test_diagnose_rq2_normal_identity_breakdown_v1.py`：100 passed in 51.97s。
- `tests/test_diagnose_rq2_normal_cost_fast_v1.py tests/test_rq2_identity_stream_fast_v1.py`：136 passed in 42.53s。
- `git diff --check` 通过。当前旧结果绑定的源码和数据保持。

初始实现 pin：`3523e4e42266dd100a8122a45099e39a606f4a5a8f864673e6cba8dc3b35a40e`；脚本 SHA256 `4b160c04179f17f51a9fb9d60d7a5182b0603b37bcfac13d21543547580b8059`；测试 SHA256 `9ae70d5c8512abb03d33a71be2bfe187e0cab2b40f22b92bacec9ae039897b4b`。

独立只读 pre-seal 窄测 8 passed in 9.51s，覆盖旧 oracle、三类分解错误、tiny build 与三个执行 guard。差分、依赖 pin、计时加总和非正式边界审查无实质 finding；不产生 official verdict/receipt。

## 真实零 solver 测量

一次调用已完成，目录 `results/tables/rq2_normal_identity_breakdown_probe1_non_authoritative`，日志 `results/logs/rq2_normal_identity_breakdown_probe1_non_authoritative.log`。使用旧 H25 开发声明（SHA `9a49cccf52e23d91a43511322a5abaf569e6cd2dfbf8d6db67b7d43d3c228aa6`）与上列实现 pin；参数为 `--declaration configs/rq2_normal_task_h25_development_v1.DRAFT.yaml --expected-sha256 <上述摘要> --expected-implementation <上述pin> --diagnostic-root <上述目录> --execute-development`。目录已使用，不可覆盖重跑。

Job 79.734 秒、exit 0、whole_job_quiescent=true，commit 峰 475160576 bytes；child elapsed 77.4739801 秒，来源 prepare 36.6893237 秒，13 段合计 40.3385053 秒。合计 77.0278290 秒未超过 child elapsed。solver_calls=0、model_builds=1。

| 分段 | 秒 |
|---|---:|
| validation | 0.0039583 |
| dependencies | 0.0165303 |
| encoding + digest | 4.7174440 |
| 独立完整 fast identity，前 / 后 | 5.7705556 / 5.0438145 |
| fast model build，内含完整身份复核 | 6.0017263 |

分解和完整摘要均为 `d9959966c52fe618e73974fc53203ad2caed5169bd7f360fc79e0ecafd06780c`，模型结构仍为 `e18f8f95846b33f4c358fe8d2a47082660ea19f161e317ca672ccd657e3f40f0`。数据支持优先优化编码，不支持删减 validation/dependencies 或认定 normal/solver 门已通过。

33 项索引：`results/tables/rq2_normal_task_h25_audit_v1_non_authoritative/normal_identity_breakdown_probe1_evidence.json`，SHA `8520f15d5e7bf787d88865336ae0ce1e037609df62cc5332fb0f595ec27c2152`。独立只读结果审计 33/33 一致，request/launch/observation、日志/summary/costs 和内部 SHA 链闭合，无 finding；未重跑 prepare 或 solver。所有正式性、assignment 和整任务资源认证标志仍为 false。
