# C公共网络有界构建诊断合同

2026-10-22，`DRAFT_NONAUTHORITATIVE / PRE_SEAL`。按agent.md第7/9节承接[RTS-24后继规格](../model_spec/staged_deliverability_rts24_development_v1.md)。本包仅装载数据、生成查询DAG、构造模型和审核解析点；没有native、solver、真实潮流求解、子进程或新物理时序执行。此诊断不关闭公共网络整链性能审查。

唯一入口为[staged_rts24_build_diagnostic_v1.py](../../experiments/staged_rts24_build_diagnostic_v1.py)，固定新目录`results/tables/staged_deliverability_rts24_v1_non_authoritative/build_01`，独占创建，一次保存，不覆盖或自动重试。旧B1–B3、上轮C保存记录和无关paper工作保留。

旧期望根固定为已发布C audit的SHA256 `9a04b13e1778614ecefac1890c0f68ab30d81dd5990b7be2cf6c745763ff6e90`（与Git检查点0f9aed5e中的原blob核对一致）；先核根，再读取其中的旧文件期望。不得用同路径的新audit重解释旧记录。

## 自身DAG、规模与预期计数

1. 源/配置/本合同/规格/测试/解析fixture及环境指纹→依据旧C保存audit核对118工件、42仓库pin（重叠3项一致，共157个唯一文件）及7个选定外部文件/5个旧版本→装载RTS-24及工程前后网络→保存两份完整网络frame。
2. 固定四个输入窗：on_time/early的h=0、1、2以及delayed/late的h=3，各生成三种方法的描述，共12个hour template；保留外生输入、F/X、短缺、69个事故、角色、父request id及完整request id。公共节点均为请求描述，bound_query_identity为空；缺经济父点者显式标记unbound，尚无完整BoundQuery身份。共1699个已描述请求，另12个策略后actual槽，总逻辑求解节点上界1711；它们不是已执行求解。延期h=3的50MW参考接入权缺口保存，未缩小原始业务。
3. 仅构造两个公共正常完整C模型（工程前/后各一次）。公共corrective没有已求经济基准，明确检查缺父点拒绝；不使用占位dispatch构模。
4. 两个独立三母线解析fixture（普通/带tap及shift），各构造base/raw/actual三个模型，共6个，按手给完整点填值并核对提取；审核6个点、2份父经济KKT证据及1个故障支路非零流反例。解析点不代表公共网结果，子raw点不宣称最小削减。
5. 保存模型形状及解析证据→结束指纹/旧字节bookend→计数与资源报告→清单/完成记录→严格读回。顶层8份机器工件（7清单项+completion）先固定；运行后说明/审查/verification另列，不倒写completion。

构模共8次；公共模型各97变量/64约束（含固定参考角的变量），三母线模型各11变量/8约束。每次绑定/构模/子点审计重新核对父点和KKT，均计入阶段wall，不以纯solver调用数代替该成本。受限于缺公共经济基准，139个合同求解节点只保存描述，未构造或运行其余公共故障模型。

## 优化、等价和停止

网络frame只保存一次，query仅保存身份/角色/实际边界及父依赖，避免每节点重复序列化完整24母线数据。不得跨小时缓存网络请求或把真实actual槽补成假点；所有query保留准确F/X和正则化经济目标政策，不能偷换原报价或削减边界。旧B1–B3字节及所选环境符合旧证据时复用，不重跑旧轨迹。

预算依据为当前30项无solver针对检查约5秒；本探针增加1699个描述身份、8次构模、源及保存记录SHA，预计5–30秒，仅为构建诊断的事前估计。固定wall60s、无进展20s、进程采样RSS512MiB、总输出16MiB、单文件4MiB、最多16个文件，串行/无child。每小时模板、模型和文件快照组做心跳与资源检查；合作式检查不是OS硬配额，阻塞I/O/报告本身失败仍best effort。越界保留failure及全部已有文件，不顺延，不重试，不清理旧工件。

源码静态不调用SolverFactory，运行期另将Pyomo及旧DC/need/SCOPF的factory替换为拒绝器并计数；首次请求即失败，finally恢复原对象。这是该受审执行路径的保护，不是任意Python/native隔离。源/环境版本指纹、UTC启动/报告前/完成前时点和elapsed、分阶段采样RSS及结束库存全部保存；全程末次采样峰值及总输出bytes由运行后launcher另存，report字段仅覆盖写report前。选定依赖不是完整生产闭包。

后续native代表包仍须固定完整输入、真实调用上限、失败/保存/关闭重开路径及具体资源预算并获得专项授权。本包不给公共网容量、最小削减、完整F/X时序或工程结论；C及D/E整体预算保持OPEN。
