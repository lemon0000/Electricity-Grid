# H1 单操作 historical numerical witness 诊断原型

2026-10-17，DRAFT_NONAUTHORITATIVE，R3 development / PRE_SEAL。

本原型只回答：对同一个已保存 N0 controller 连续进行两次 historical preparation，
第二次是否能安全复用第一次完成的四次数值检查，同时保留每次原有的十六次 context 观察。
它不接入 exact-source、common 或 Handoff，不形成生产凭据。

## 原型合同

`experiments/h1_operation_historical_witness_development_v1.py` 使用独立结果类型和验证身份。
旧 historical audit 仅作为科学投影逐字节比较；实际工作由强制的 execution receipt 记录。
模型、输入、阈值、source/registry/Job/clock/Parent 观察和独立双 prefix 保持原合同。

- operation 限同进程、同线程、同一随机 session、同一精确 canonical root、外部 binding/terminal pins、
  同一明确模式及两次非重入 prepare。内部 once token 不导出；公开 session identity 使用随机值。
- `declared_arm_label` 不认证 arm。生产三 arm 隔离和真实 Handoff token 尚未接入。
- full-only 模式每次实际进行 4 次 full numerical inspection、4 次 prefix 内复核；
  operation 模式第一次相同，第二次为 0 次 full、8 次跨 prepare 复用。
  每次都执行 16 次未改动的原 `_HourScope._context`，不缓存 discovery 或动态输入。
- 两个 prefix 各有独立证明槽，必须完整成功、科学输出相等，才启用后续复用。
  证明绑定完整 context key、frozen numerical result、prefix index、session owner、root/pins 和第一次科学字节。
  context 的前八项递归不可变；两张 snapshot map 使用独立副本。
- module definition 时固定 helper、函数 code/defaults、class dispatch 和完整 project/source view；
  操作进入、prepare 及证明提交前后检查完整 view，adapter 前后检查直接绑定。
  任何失败立即 poison 和清空证明，禁止回退接受。cleanup 不依赖有效 runtime guard。
- receipt 绑定 active validation identity、两个 envelope hashes、canonical proof basis 和诚实的执行次数。
  `prepares_complete` 只说明两次准备完成；最终 `complete` 还要求两个 public envelopes、无失败、
  操作已关闭、证明清空、锁已释放。关闭后的 receipt 仍检查 definition-time bindings。
- 观察之间未被捕获的 change-and-restore、任意第三方内部反射修改、内存中字节来源和完整 DLL provenance
  均不由此原型证明；沿用单 owner、合作式运行和离散观察的开发范围。

## 验证与预算

状态机、prefix 槽、所有权、dispatch、receipt、科学字节和 cleanup 故障检查已在
`validation_operation_witness_01/unit_06/` 终态通过：68 passed，pytest 26.12 秒，
monitor 27.484 秒，sampled process-tree peak 175,173,632 bytes，新工件 72,210 bytes，source pins 稳定。
synthetic unit fixture 在新模块定义前安装，不能代表真实 context 或数值性能。

保存记录性能诊断的输入为 chain_06 的固定 network-only N0；每个模式一个新进程，
一次原 v1 oracle、两次诊断 prepare，每模式最多一次，300 秒 / 512 MiB sampled RSS /
64 MiB 新工件上限。使用固定 `entry_revision_03` 的代码与 metadata parse leases 及显式解释器路径策略；
保留 stock metadata discovery。原始 context 和 `hour.inspect` 必须保持原函数，科学字节须等于 oracle。
诊断记录位于 `results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/validation_operation_witness_01/`。

该代表性单对诊断已取得两个真实终态：full-only 两次 prepare 为 28.540805 / 28.685692 秒，
operation 为 28.098218 / 19.470876 秒。合计节省 16.8758%，第二次节省 32.1234%；
full calls 为 8→4，context 仍为32。783项source与461个保存文件现时核验一致，科学audit逐字节相同，
各mode的33把锁可重获释放，已观察owned进程清空，sampled RSS及新工件未超限。
证据为 `saved_pair_comparison_01.json`（SHA
`7f68d9623510caed209b8b1fa1aacf71c23fc1fc85974b875b6f5dbd5e419515`）及其18项hash引用；
确切诊断包为 `diagnostic_source_manifest_v1.json`（SHA
`5dec7d5766827cb56e3bc441c13d3205f10dd231f48fcab6ce508db298604378`）。
独立只读PRE_SEAL核验未见该诊断范围剩余finding；完整链性能及生产接入仍未证明。

代表性性能结论必须由对应 terminal、pins、实际次数和独立 PRE_SEAL findings 支持。
单元检查、局部比例和静态调用下界均不能替代完整 hour-0 耗时。

## 生产接入出口仍 OPEN

生产证明必须等 exact-source/common 全部返回成功后才启用，覆盖 source 验证、第二次 registry preparation、
末次观察/guards、结果构造及所有失败回调。随后需真实 Handoff token、三个独立 arm 槽、成功提交、
失败停止和关闭重开重放的完整验收。当前原型不能打开长链启动、resource admission、official review、
native 校准或正式运行门禁。
