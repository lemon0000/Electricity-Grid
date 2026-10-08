# 连续策略已验证前缀交接 v1

状态：DRAFT_NONAUTHORITATIVE；`evidence_class=derived_mechanism_state`。

## 范围

`src/rq2_joint_deliverability_boundary_v1/prefix_handoff.py`为既有固定容量策略增加持久化薄层。
它保留canonical zero origin及完整已提交前缀，导入后返回原`CapacityPolicyCursor`，由既有
`advance_capacity_policy`继续消费单小时观测。事件、rest、累计energy、债务、deadline和ramp历史不重置。
适用四臂的physical shared execution，包括B6共享执行；不导入B6分离规划状态。

本项补齐可重放来源的非零状态交接，不提供任意非零初态构造器，不改变已有chunk推进或zero-history初始化。
状态是声明策略和输入下的机制推演；source provenance标识的保留及一致性不证明它们是真实数据或外部来源认证。
`observed_carry_in=false`、`training_capacity_certificate=null`，完整履约和安全认证门保持关闭。

## 接口与完整性

- `export_prefix_handoff(cursor)`只接受非空、全部提交、未停止的capacity前缀。从零起点重新回放，
  要求得到同一个完整cursor后生成canonical UTF-8 JSON bytes。
- `import_prefix_handoff(data, expected_sha256=..., expected_origin=...)`要求调用方独立保留的bytes摘要
  和同一策略/来源/会计期的canonical zero cursor。不能把文件内声明的origin自动当作接收方期待值。
  摘要是本地完整性pin，不是签名；同时替换数据和外部期待值会定义另一机制输入，不能据此认证历史真实性。
- 导入先核对spec/policy_id、zero origin的arm、split、trace、seed、双时钟offset、provenance、envelope和period。
  然后只解析原始观测与current available，逐小时调用既有策略；任何未提交前缀均拒绝。
  原动作、Fraction执行投影、短缺、全cohort末态、物理末态、元数据、源代码hash和Python版本
  必须与重放生成的完整canonical bytes一致。文件中的物理snapshot不会被直接反序列化成可执行状态。
- Fraction分子/分母采用最简整数的canonical字符串编码；原始输入若为Fraction也精确保留。
  重复JSON键、非有限常量、非最简分数、额外字段、截断、字节或依赖漂移均不能通过完整重放匹配。
- `write_prefix_handoff`仅用`xb`创建以`_non_authoritative.json`结尾的新文件；不覆盖既有或部分文件。
  `read_prefix_handoff`只接受普通非符号链接文件并执行同一导入校验。部分写入文件不能当作有效交接。

`implementation_sha256`绑定实际运行时仓库代码（含package初始化文件），不宣称包含测试或外部数据闭包。
fresh Python进程枚举导入模块的测试核对该依赖集合。本组件不生成production manifest、lease或review receipt。
将原cursor完整恢复后，后缀来源断裂仍由原策略拒绝，最后提交状态保持不变。

## 验收矩阵

| 对象 | 验收 |
|---|---|
| 四臂持久化 | 各臂zero→prefix→写入→读回→suffix与完整连续执行逐步相等；另在全新Python进程恢复后继续并比较完整字节摘要 |
| active/ramp | h9/h10各调用1/8，h11在原up-ramp/response下调用1/4，duration=3；h12受max-duration阻止 |
| inactive/rest | energy=.25、debt=.125、rest=1时不能重启；恢复.0625后debt=.075，rest达到2后可重启 |
| deadline | 到期miss快照持久保存，后续晚恢复到0仍为deadline_missed；未知deadline保持unidentified |
| 精确输入 | 原始1/7请求与Fraction执行投影往返后保持精确 |
| 外部期待 | 拒绝跨split/trace/seed/provenance/offset/spec/arm/envelope/period导入 |
| 历史完整性 | 空、stopped、裸state均拒绝；改动动作/投影/cohort/物理量/原请求后即便重算摘要仍须通过完整重放 |
| 文件完整性 | 摘要、截断、重复键、NaN、非canonical分数/bytes、代码依赖漂移及已有文件覆盖均拒绝 |

45项针对性测试通过（1.02s，包含全新进程恢复例）；handoff、capacity policy、aggregate、capacity diagnostics、four-arm、
debt cohorts与multiday共7文件最终195项通过（12.76s）。独立pre-seal审查限定范围无开放finding，
实际复核45项targeted及全部连续模型381项测试（34.14s）通过，包括运行依赖闭包及跨进程恢复。
源码SHA256：`be4ae845374bc760e6c3980be56701b66cb23477dea4ab962c40174c167f866c`；
测试SHA256：`3743aad8bd37296c3dd242ac58e862c2cd747f404094bc41178d7d0312d61fc1`。
旧capacity诊断包36组/1091条仍通过`--verify-existing`完整重放；`git diff --check`无输出。
本次仅为draft pre-seal findings，不构成official verdict或运行授权。

## 剩余正式门

同一nonrolling会计期交接不定义rolling reset或跨period归属；不建立初态经验分布、训练容量证书，
也不决定正式burn-in、enrollment、评分窗、窗口权重或closure。训练末态不能接入holdout。
正式中段评分须先注册科学协议；该机制中可重放的更早holdout前缀不自动成为已注册burn-in。
当前只验证短合成例，没有长窗口性能或正式执行环境认证。
