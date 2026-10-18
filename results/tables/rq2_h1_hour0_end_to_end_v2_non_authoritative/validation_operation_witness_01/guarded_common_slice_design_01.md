# 下一接线出口：真实三 arm common 的受保护复用

历史设计，DRAFT_NONAUTHORITATIVE。本设计随后已形成四模块 draft 接线；当前合同见
`docs/model_spec/rq2_h1_group_operation_witness_development_v2.md`，窄 unit/cold PRE_SEAL 记录见
`group_successor_preseal_summary_01.json`，fresh root + live Rref 的有界诊断预算见
`common_slice_plan_01.json`。实际三 arm slice 收益仍待测量；此文件不授予长链准入。

已有单arm historical-only结果支持继续小范围接线。第一common必须完整执行两轮，等其所有source、
第二registry、末次观察/guard及结果构造和返回检查成功后，才激活可用于下一common的三个proof slot。
不以“首轮成功”替代整个common成功。原型v1保持确切字节，不能直接当生产凭据使用。

## 实现边界

1. `h1_operation_historical_witness_development_v2.py`：三个由实际roster认证的独立arm slot，
   每个仍有两个独立prefix；scope仅限本次真实Handoff operation。保留每historical prepare的16次
   原始context观察、source/dispatch/root/pins观察和诚实计数；slot不得跨arm/root/thread/session。
   将staged proof与可消费proof分开，提供全session poison和cleanup-safe清空能力。
2. `h1_phase_exact_source_current_development_v3.py`：内部typed arm/session capability入口。
   v2的两次prefix、两次registry、load/validate source、末次source观察和owned结果/return检查全部保留。
   可评估复用v2 `_prepare` 的内部 `_check/_replay`组合参数；如复用，必须显式承接原全部guard，
   不能绕过原 `_guard_prepare` 的验证而只调用未保护core。旧audit只能标为兼容科学投影，
   新强制execution receipt绑定实际次数与新identity。
3. `h1_group_n0_common_input_binding_development_v3.py`：两个完整round、跨arm科学相等、
   fresh manifest/roster replay、末次check、owned pending结果；比较稳定科学投影和独立执行receipt，
   不用伪造相同full计数维持旧audit相等。整个prepare返回后再原子激活三个slot。
4. test-only scope bridge：使用真实Handoff v2的guard、`_BEGIN`、parent bundle、
   common/roster/bootstrap guards和`_RECORD_PREDECESSOR`；不调用paired consume、不创建handoff journal。
   token只由bridge自身调用真实`_BEGIN`取得并在closure中持有，不接受caller提供的任意token。
   `_VERIFY_OWNER`不单独证明某个传入token等于anchor中的token，不能将它误作token认证API。
   所有清理窗口均须使用捕获的原资源和cleanup capability；最终成功必须等token/guards/handles均清理。

所有source/registry observations保留；无global旧模块别名替换。新wrapper和类型有独立身份，
旧verifier identity只说明predecessor projection。scope bridge不标为production Handoff integrated。

## 确切首切规模

在同一真实scope内调用common两次。第一个common两轮全部full，第二个才复用。

| 项目 | 原两次common | 保守候选两次common |
|---|---:|---:|
| historical prepares | 12 | 12 |
| independent prefixes | 24 | 24 |
| full numerical hour inspections | 48 | 24 |
| within/cross numerical revalidations合计 | 48 | 72 |
| 原context evaluations | 192 | 192 |
| registry.prepare | 24 | 24 |

候选第一common为24full+24within，第二为0full+48cross。首个common第二轮不得消费仅由第一轮产生的proof。
该首切可设max_common_calls=2、每arm最多4prepares；这是诊断规模，不能变成生产统一上限。

旧consume中“至少21 correspondence+1prepare”的22是静态下界，排除了hidden/nested paths，
既不是完整实测次数，也不是上界。不得以“第23次common失败”作为生产合同。
保守首common完整验证下，若最终恰有22次，则为24full+1032reuses；该条件算术不代表已证明实际调用量。

## 在真实有界测量前闭合

- 查明chain_06保存的roster、common及Rref completion是否齐全；缺项不得伪造或从活跃chain_07跨取。
  原保存树只读保留；reopen本身若有任何写入或恢复动作，必须另选新合成根。
- fixture、字节/metadata/path leases先就位，真实Handoff注册并取得scope后，才首次导入新witness/source/common。
  新入口拒绝预载模块，记录导入顺序与exact hashes。旧Handoff的`_OWNERS`等合法生命周期变化
  可能使过早安装的完整dispatch baseline失效；不能因此退化成任意first-use baseline。
- targeted失败矩阵覆盖三slot原子commit、第二registry、末次source观察、结果构造/return、
  跨slot/root/nonce/arm、提前close、同线程重入、token失效与逐项cleanup失败。
- 旧science/normal/current/exogenous/state/request与reference audit兼容投影逐字节oracle核对。
  记录实际full/within/cross/context/registry调用；接通后第一common与复用common分别计时。
- 先估量保存owner/Rref reopen与guard准备成本，再登记单次总cap、RSS/新工件上限和停止条件。
  单arm的28/19秒不能代替三arm、setup或完整scope预算。当前未登记该slice运行资源准入。

只有该首切通过且有实际收益，才考虑Handoff v3及其journal/holder/callback/readback/close/reopen接入。
其后仍须评估snapshot/`CommonOwnerGenesis._correspondence`隐含v2 common重放，不能把仅直接调用的
数字当作整个工作流成本。完整hour-0、192h、资源、seal/official review和正式运行权限均保持原门禁。
