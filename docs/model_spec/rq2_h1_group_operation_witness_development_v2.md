# H1 三 arm common 操作内校验复用草案

状态为 `DRAFT_NONAUTHORITATIVE`。这是有限范围的验证合同后继，不改变模型、输入映射、
阈值、LB/UB/gap、power/service balance、`q+r≤D`、恢复债务或 censoring。
尚未取得真实三 arm common slice、完整 hour-0 或完整工作流的性能准入证据。

2026-10-17 实测状态：`entry_revision_05` 的 fresh slice 在 258.859 秒以访问违例退出，
第一个 N0 尚未完成，未触达本组复用路径。失败不能归因于本组代码，也不证明本组可用。
`common_slice_crash_01/postcheck.json` 保留 788 项原输入、副本、2 锁及已观察进程退出核验。
短 frame-churn 差分支持 C 定时 traceback dump 竞态；Python sampler 的清理后继 13 项检查通过。
实际 slice 稳定性及两 common 完整科学/audit/次数对照继续待验，后继使用独立诊断包。

## 实际接线

- `h1_common_validation_operation_development_v1.py` 从原 registered Handoff 自行取得
  `_BEGIN` token，持有原 Parent bundle、common、roster 和 bootstrap guards。
  token 保存在闭包；caller 不能提交任意 token。入口只做两次 common 诊断，不 consume，
  不创建 handoff journal，也不产生 producer/运行权限。正常退出少于两次仍须清理并失败。
- bridge 内部固定自身 canonical 路径及定义时 SHA，并通过 `_PINNED_ROUTES` 固定三个 sibling
  后继的路径和 SHA；公开入口不接受 caller 路径、hash、callback 或 loader。
  operation receipt 绑定四个源文件和 canonical route manifest SHA。持有原 guards 后，拒绝预载的三个后继模块，
  从 pinned raw bytes 按 witness → source → common 编译加载；每个入口前后检查
  package attribute、`sys.modules`、origin/spec/loader、entry code/defaults 与当前文件 SHA。
  返回值须是固定路由中的 exact typed result，并来自同一 session。编译、执行或末次加载检查失败时，
  逆序移除本次创建且仍指向原 module 的绑定；foreign replacement 保留。成功模块留至隔离解释器退出。
  单元测试只在定义前以明确 AST seam 替换固定常量，不表示生产字节准入。
- `h1_operation_historical_witness_development_v2.py` 为真实 roster 认证的三个 arm 分别
  保留两个 independent prefix slot。沿用 v1 的原 `_HourScope._context/_check/inspect`
  与完整历史 replay body；每次 historical preparation 仍执行 16 次原 context。
- `h1_phase_exact_source_current_development_v3.py` 复用未经修改的 source v2 `_prepare`
  core，同时承接原 guard inventory 和完整 dispatch/source bookends。原两次 prefix、
  两次 registry、load/validate source、末次 source observation 和 return checks 保留。
  新 `PreparedCurrent`、`ExactSourceCurrent`、`CommonSourceBundle` 使用新 audit 和强制 receipt。
- `h1_group_n0_common_input_binding_development_v3.py` 保留原两轮、跨 arm 科学相等、
  fresh manifest 与 roster replay。整个首个 common 的 owned result 和 return bookends
  成功后才激活 proof；同一次 common 内第二轮不使用第一轮 staged proof。

旧 source v2 的中间对象不能作为新结果返回。其固定 `4/4` 字段只进入明确命名的
`predecessor_compatibility`，并标识 `compatibility_counts_describe_actual_execution=False`。
新 source audit 顶层及其 nested `PreparedCurrent.audit_payload` 不保留这些旧执行字段。
本次 full/within/cross、context、registry 与实际 identity 由独立 execution receipt 表示。
common 比较完整科学 audit，执行 receipt 分开保存；不能忽略其他 audit 漂移。

## 两个 common 的验收计数

| 范围 | full numerical inspections | within-prefix | cross-common reuse | 原 context | registry.prepare |
|---|---:|---:|---:|---:|---:|
| 首个 common（完整两轮） | 24 | 24 | 0 | 96 | 12 |
| 第二个 common（完整两轮） | 0 | 0 | 48 | 96 | 12 |
| 合计 | 24 | 24 | 48 | 192 | 24 |

每个 arm/root/thread/session/nonce 独立；任一失败清空全部 provisional/active proof。
cleanup 从定义时闭包 registry 读取创建 PID/thread 和逐个登记的原 owner/guard，不依赖实例的
`_resource_caps`、`_original_arms` 或 `_creator`。它使用定义时保留的 callable code，逐项尝试所有
关闭、mark reset、guard release、bundle reset、`_END` 和终态记录。单项失败不得跳过后续资源，
body error 保持为原异常。全部 arm 释放尝试后移除 live 资源记录，只保留可追加首错的 closed JSON summary；
返回 summary 的副本。foreign thread 的 group cleanup 仍须清空 proof、尝试释放全部 arm 并报告错误。
bridge 的 foreign-thread exit 在外层资源变化前拒绝，原创建线程仍持有合法 token 并负责完成原 `_END` 和释放。
正常返回必须等两个完整 common 与全部 public arm envelopes 关闭。

## 证据范围和剩余出口

当前 counter/ownership 检查 `group_unit_06` 为 49 passed / 103.37 秒，原 Handoff 生命周期的显式
fake-fixture 检查 `bridge_unit_08` 为 52 passed / 4.27 秒；包括固定资源被删除/替换、中途获取失败、
close 后追加首错和真实 foreign-thread 反例。真实固定模块 cold definition probe `02` 全部最终 guard
通过，outer 3.281 秒，没有发行 token/lease 或执行历史数值。窄 PRE_SEAL findings B1–B10 已闭合。
`source_unit_02` 的 6 项历史组合检查使用原有 source fixture，覆盖两次 registry、validate/final source、
owned result 和 return 窗口，witness 为明确 mock。所有 unit fixture seam 都不代表真实历史数值证明或 live Parent admission。
确切 request、tested bytes、terminal、后续回归和 PRE_SEAL finding 状态保存在 hour-0 evidence 根的
`validation_operation_witness_01/`。

chain_06 的 Rref 归档完整，但 `ParentCompletion` 只能在原进程由 live Parent 发行，不能从文件恢复。
原 common reopen 使用 SQLite `mode=rw`/journal-mode 操作，不能宣称严格零写。该保存树继续保留；
真实 Handoff slice 需要在新合成根取得新的 live Rref capability。禁止伪造 completion、使用私有
token 重建旧 authority，或从活跃 chain_07 跨取状态。新诊断的准备成本问题与具体预算已登记在
`validation_operation_witness_01/common_slice_plan_01.json`：单次 600 秒、采样 RSS 1 GiB、新工件 128 MiB。
入口 `entry_revision_05` 149 code/609 test pins，helper 检查 77 pass/1 权限 skip；真实测量仍待闭合。

本草案及其 unit checks 不关闭实际收益、完整 paired commit/close/reopen/replay、192h、
整体性能/资源准入、seal、official review 或正式运行权限。successful consume 的 22 次 common
仍只是静态调用下界，不能变成生产 hard cap。本诊断的 two-common cap 仅固定测试规模。
