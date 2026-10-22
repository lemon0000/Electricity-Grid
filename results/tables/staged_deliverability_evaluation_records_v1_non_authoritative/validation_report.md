# D/E开发字段与保存报告投影：验证报告

2026-10-23，DRAFT_NONAUTHORITATIVE / PRE_SEAL_AUDIT。[合同](../../../docs/plan/staged_deliverability_de_evidence_fields_contract_v1.md)、[projection](projection_01/projection.json)、[独立核验](verification_01.json)、[开发记录](development_checks_01/development_checks.json)及[领域/修复说明](development_checks_01/domain_and_preseal_notes.md)。本轮实施结果字段与既有报告读取接口，原D主比较和E留出尚未执行。

唯一投影CLI exit0，144111 B，SHA256 `89c8fdca10dc1a5becd4a3e00f6f3c86be2cb62d18fa5d11f95c1b79e2078bb2`。读取三个原始report，分别为32952、408939、62933 B，固定SHA在解析前核对；保留原authority，不解码CAS、不reopen、不重新科学数值审计。

输出包含三个彼此分开的部分：

- 20个三母线保存视图：旧journal的3个方法例、5个失败例，加cost的12个v2/v3 case。它们是复用轨迹和历史reader观察，均public_D_eligible=false，不是20个独立场景，也不填入D分类槽。
- 公共四层中只复制原40行必要条件及premises；actual、完整静态F/X网络、完整反事实时序分别为not_evaluated/value=null/reason。必要检查true只解释为not_ruled_out，容量释放null。
- 12个业务快/慢×工程按期/延期×三方法分类槽，均planned_schema_only、executed=false，数值输入、D、run/result和两个结论字段均null。它们不是已定义的12个数值方案或预算。

机器合同明确共享外生任务/期限/Y/规则与独立设备/电网计划，方法从自己的连续物理状态生成请求；逐时information-history、五组资源/动作/服务/carry字段、四层和终态轴分别登记。method_conditions_satisfied与full_replay_conditions_satisfied互不替代，mathematical_infeasibility_inferred和stop_reason另列。E只登记selection→freeze→independent reveal→causal execution规则，尚无所选方案、冻结身份、留出split/数量或事件真值/揭示值。

## 保真的保存反例

| 原保存物证 | 投影保留的区别 |
|---|---|
| legacy full_temporal | complete、尾债0，但deadline miss40 MWh_c，原方法及full replay均false；晚补做不擦逾期 |
| legacy instantaneous / fixed_headroom | 原方法true但full replay false，不将简化判断改成完整履约 |
| cost两小时例 | missing_input、primary right-censored、debt40、两种conditions null |
| cost reference_unresolved | tasks为空/accepted_through=-1，但另有未接受observation.workload=100及adopted=false，不制造已接受任务 |
| cost unknown | writer publication unknown/0行和保存fresh committed/known/1行并列，writer_fresh_resolution=null |
| cost deletion | reader明确拒绝、state_adopted=false，没有summary；不补空/零指标 |

显式null的writer_inspection保留writer_observation=null；缺失writer_failure继续缺失。每项附原path/SHA/bytes/JSON pointer；selected source fields逐字段比较。大体量state和嵌套inspection被排除，后者只摘指定诊断。fixture的first/registration/observation header、完整逐时数值点和CAS闭包不由本投影补齐；primary指标沿用原报告定义，重聚合时仍须读取原fixture，不用这20个视图重新划分窗口或推断充分性。

## 检查与预算

49项新针对性检查和74项相关普通回归通过，共123项不同检查。首轮2 failed/17 passed/13 errors来自同一null-inspection假定，已修复，失败日志与全部迭代保留，不重复累计通过数。只读sol_modeler审查范围/语义，sol_reviewer提出的两个Medium（显式双verdict字段、独立完整蓝图核验）修复后无剩余High/Medium；这是PRE_SEAL开发审查，无official verdict/receipt/seal。

五新源、helper、三report、两spec共11项repo输入，另exe一项；首尾24 Reader读/1404846 B，bootstrap另1读/14525 B。core/helper均compile/exec刚读取并核验的确切字节，没有包入口或pyc执行；选定exe和输入bookend一致，不是完整environment seal。

projection-body wall0.0350415 s，发布前0.0312826 s，binding/projection/bookend分组分别0.0163624/0.0061130/0.0088069 s。计时从main函数入口开始，不含解释器启动和此前stdlib加载；Reader账本不包含import/OS加载与输出读回。零科学compiler/model/native、零journal reopen、无子进程。这些只是元数据工具观测，不是公共代表求解成本。

独立postcheck exit0、verify-body0.0284464 s：26次显式读取/1693068 B，20视图全部选定字段、40必要条件、12分类槽完整蓝图及输入/exe首尾一致。它不调用project，独立按pointer与原始报告核字段，并用完整expected精确核信息/匹配/逐时/终态/holdout访问及空预算；另外用pins算术核24 Reader和bootstrap。

create-only、并发mkdir及mkdir/open/部分写/短写/读回错误/读回不同/末端wall均有pytest tmp反例；真实阻塞IO/坏盘/掉电、OS RAM硬限和公共长链未覆盖。五新源随本投影绑定保持字节，后继修复另版。

执行前后旧检查均exit0：B1–B3的118文件、既有公共/journal/batch/cost绑定及731历史文件保持；上一business检查点的5源/19 artifacts和原独立40行oracle另作只读复核通过。P1注册SHA仍`23577e5d79d3284a260decbfe2258a3103252617953452565a9feeffafbd94e2`、p1_01不存在。live_after无相关Python/solver进程。

D/E快慢业务的数值路径、最终计划/设备、D/选择准则、敏感性水平、主时域/尾观察、holdout独立性和数量、公共runtime/真实成本及总预算均未定。P1专项授权继续独立等待。公共方向保留，两母线和三母线保存物证仅作机制回归；本包不关闭C/D/E资源或139/完整F/X时序门。方法写作可引用已固定定义和这些失败语义，后续D/E数值登记及执行仍按原依赖推进。
