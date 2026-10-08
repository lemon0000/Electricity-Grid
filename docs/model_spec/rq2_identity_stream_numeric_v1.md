# 数值映射身份编码后继

2026-09-27，DRAFT_NONAUTHORITATIVE。H25 零 solver 分段测量表明编码占主要身份计算成本，见 `rq2_normal_identity_breakdown_probe_v1.md`。新增 `identity_stream_numeric.py`，保留旧 fast 文件及所有结果。

## 字节与验证语义

仅对 exact dict 且所有键为 exact str/int/bool、所有值为 exact float 的映射使用直接局部编码：每个值仍检查 finite，仍用 float.hex（包括 -0），仍对完整 encoded pair 按 repr 排序。任何其他类型回落旧 fast 局部编码。dataclass 优先级、子类拒绝/接纳语义、Unicode 转义、映射碰撞排序均保持。

不缓存内容、字段布局、依赖或摘要，不削减 normal validation。本节编码独立验证时尚未接入 normal kernel，编码级测量不能证明完整 normal 60 秒门通过；后续接入与完整任务结果分别见 `rq2_normal_execution_stream_numeric_v1.md`、`rq2_normal_task_stream_numeric_h25_development_v1.md`。

## 测试与局部观测

compute Python `-B -m pytest -q -p no:cacheprovider tests/test_rq2_identity_stream_numeric_v1.py tests/test_rq2_identity_stream_fast_v1.py tests/test_rq2_identity_stream_v1.py`：118 passed in 3.45s。独立新文件 51 passed in 2.02s，另对 2000 个含 Unicode/surrogate/astral、巨大整数/bool 键和有限 float bit patterns 的数值映射进行旧字节/摘要差分，一致，无 pre-seal finding。

源码 SHA256 `97afd233d5510cf12ab38f2c9cd654f2b28f822a87cf7ef2e2b17e29e18348e3`；新测试 SHA256 `cdaddafbfa3e4576866113e8ad62c37aefd8d22fd7c6cafa85482dc662ce233f`。

本地合成观测使用 1000 个 `Row(hour, values)`，每个含 158 项 `str(k):float(k)`，六轮交替 fast/numeric 与 numeric/fast 次序；全部摘要为 `9ff611d9221845a39e6cacb1c86a0412d0989139cafd8f4311e50931b2172076`。fast 中位 0.21419825 秒、numeric 中位 0.18073240 秒。这只支持该合成结构上的局部改善，不是 H25、完整 kernel 或跨机器性能保证。

## 真实 H25 对照的开发验证

新增 `experiments/diagnose_rq2_normal_numeric_identity_v1.py`，在已保存的 breakdown probe 基础上增添 numeric 完整摘要前后两次测量、外部 numeric 源码 SHA 及 exact metadata 核验；15 段互不重叠。其余来源、fast model build、零 solver、固定子进程上下文、120 秒含静默及 768 MiB Job 边界保持。numeric 尚不参与 model build。

首轮两新文件测试 145 passed、11 failed in 48.31s；失败来自 fast 计时调用误加第三个参数，未到达 numeric/build。已修正新 probe 该调用；独立审查同时发现该问题。首轮不满足真实测量条件，首轮实现 pin 未用于真实测量；修后终态如下。

修后最终命令：`D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_diagnose_rq2_normal_numeric_identity_v1.py tests/test_rq2_identity_stream_numeric_v1.py`，156 passed in 51.25s，exit 0。独立 tiny/时钟/numeric mismatch 4 passed in 8.29s，timing/metadata/分解失败/guard 28 passed in 13.58s，首轮 finding 闭合，无第二项实现问题。

最终 probe SHA256 `7b965bace85cf708e3b980b87481930aafae225a7db84bd66df600bb1a459ef0`，test SHA256 `d7f47c19c478c698820c9b1a10dfe0e2ca1263ab190aaa9f5cb35cf1b6626b6e`，实现 pin `9eb6e34cef89526e4c0ad11c0f7ec9be093435e681ef1be3650671e0e87cf70e`。这些开发核验不构成 official verdict 或正式启动许可。

## 真实零 solver 对照结果

一次调用已结束。结果根 `results/tables/rq2_normal_numeric_identity_probe1_non_authoritative`，日志 `results/logs/rq2_normal_numeric_identity_probe1_non_authoritative.log`；使用 compute Python `-B` 调用上述新 probe，参数为 `--declaration configs/rq2_normal_task_h25_development_v1.DRAFT.yaml --expected-sha256 9a49cccf52e23d91a43511322a5abaf569e6cd2dfbf8d6db67b7d43d3c228aa6 --expected-implementation 9eb6e34cef89526e4c0ad11c0f7ec9be093435e681ef1be3650671e0e87cf70e --diagnostic-root results/tables/rq2_normal_numeric_identity_probe1_non_authoritative --execute-development`。启动、结束及索引前实现 pin 一致，目录已使用，不可覆盖重跑。

| 完整身份调用 | fast 秒 | numeric 秒 | 本次观测降幅 |
|---|---:|---:|---:|
| 模型构建前 | 5.4537921 | 4.3547956 | 20.15% |
| 模型构建后 | 5.1988746 | 4.2227902 | 18.77% |

这些是同一已准备输入上的顺序独立调用，调用次序及机器负载仍可能影响时间；不能视为完整 normal 的受控加速保证。old、fast、numeric、decomposed 和末端摘要全部为 `d9959966c52fe618e73974fc53203ad2caed5169bd7f360fc79e0ecafd06780c`。模型仍用 fast builder，结构保持 `e18f8f95846b33f4c358fe8d2a47082660ea19f161e317ca672ccd657e3f40f0`。

Job 88.078 秒、exit 0、whole_job_quiescent=true，commit 峰 474370048 bytes；15 段合计 48.9791870 秒，prepare 36.4953018 秒，合计 85.4744888 秒不超过 child 85.9144613 秒。solver_calls=0、model_builds=1，所有正式性、数值执行、assignment 和整任务资源认证标志仍为 false。

37 项证据索引 `results/tables/rq2_normal_task_h25_audit_v1_non_authoritative/normal_numeric_identity_probe1_evidence.json`，SHA256 `7ce289bed9a74d99e1e39fc495f8f8813e06443e6ff5f0eb25a7349b57ec4dfe`；绑定新结果、源码、测试和前序索引。numeric 编码器及 probe 现有真实结果绑定，后续保留其 bytes。

独立只读结果审计 37/37 bytes/SHA 一致；request/launch/observation 的 process/PID/FILETIME、log/summary/costs 及内部 SHA 链闭合，计时加总与非正式标志一致，无 finding。未重跑 prepare 或 solver；该审计不是 official verdict。

本次编码对照之后已接入独立 normal 模型/kernel 后继并验证完整链，详见上述后继规格。1 秒求解无可行解的问题仍独立开放；这些零 solver 结果不解决该问题。
