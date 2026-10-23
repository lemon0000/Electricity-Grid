# P2内部整链结构会计与复用决策

2026-10-23，DRAFT_NONAUTHORITATIVE。按[合同](../../../docs/plan/staged_deliverability_c_p2_workflow_accounting_contract_v1.md)补齐内部成功链的journal/prefix/CAS乘数，并以原P1五小时保存拓扑和进程观察交叉核对；没有执行公共P2、科学编译器、构模、native或reopen。起始HEAD为4c79ad930124d9c7abdd442f82d18fd08ad9785b。

## 优化决定

保留原1281次fingerprints、960次load_packet及3次preserve。完整指纹各处跨native、父端重构模/审计或finish/reopen，删减会改变漂移发现时点；Distribution.files未选路径的PermissionError也属于原失败边界。packet/context解析缓存虽有639/960次、163038294/239574720B逻辑读取削减候选，但单次诊断没有证明总预算收益，Cursor row别名及重复open/parse异常窗口还未闭合。本次暂缓缓存，优先把整链增长计清；没有优化接线、提速或新的资源准入结论。

## 条件成功路径

以下假设原固定319槽、十实际小时h=-2..7全部接受且无stop、一个committed terminal、两个完整reopen；它们不是已执行P2数量，不能套到attempt/pending、缺terminal或传输失败。

| 层 | 内部条件次数 |
|---|---:|
| point槽／QP／LP | 319／160／159 |
| scientific builds／imports | 1276／638 |
| 内部轻核注册／load_packet／fingerprints／preserve | 321／960／1281／3 |
| writer `_check` | 42 |
| journal自身runtime_identity，含两个reopen | 101 |
| 再并入1281次指纹嵌套runtime | 1382 |
| 每次28 source＋10 external＋exe的selected字节读取 | 53898 |
| journal root inventory／CAS inventory | 69／126 |
| point独立CAS inventory／内部合计 | 2552／2678 |
| prepare／propose／accept／summary | 60／60／30／3 |
| audit_execution／audit_execution_context | 97／64 |
| audit prefix历史row访问 | 495 |

journal writer `_check=4T+2`，writer runtime为`9T+7`，两reopen再加4；CAS inventory为`10T+26`。journal每次runtime有39个已选字节读取，metadata版本发现和OS loader未计。point的8次CAS inventory来自query put/get及evidence put/get各自首尾两次；它们扫描319个独立point目录，不能按journal最终库存乘2552。

root读分栏复算：434个root inventory文件实例＋200个check链entry＋84个check genesis/head＋22个reopen顺序entry＋11个append发布读回＋2个reopen genesis＝753次直接journal root读取。publish内部pending/final读回、codec、CAS和completion扫描另计，不能把753当全部文件IO。

reference compiler的575次＝三journal通道555＋hour_evidence10＋worker packet validation10，共1796个请求描述；full compiler的4次＝两合同帧2＋packet validation2，共570描述，合2366。这不是全部PointRequest实例数，未计动态replace和numeric/audit内部构造，也不是求解数。每小时selective权重为98、89、80、71、62、53、44、35、26、17；h1唯一实际事故增加71个raw描述。原P2准备阶段的958对象已经发生，不混入未来worker路径；未来注册构造/full核验、outer及quiet后采用还须另加。

完整[机器会计](audit_01/audit.json)保存公式、来源和未知项。1281次指纹等原图对应的2345752302B准备工件逻辑读取仍保持，不将上一轮0.639/0.00275/1.402秒乘这些次数形成ETA。

## 用已有P1核对CAS增长

原P1的五小时publication完整，但科学终态仍missing_input、coveragefalse、method/full双null。本次只读原genesis、五hour＋一个terminal、130个CAS和33份进程observations。按typed-wire真实ref图求闭包，不实例化科学类型、不pack或重放；entry/hash/head/state、逐步after_cas_keys及最终可信库存均核对。

| P1保存epoch | CAS对象数 | bytes |
|---|---:|---:|
| fixture | 3 | 64165 |
| genesis retained | 4 | 65388 |
| accepted 1 | 28 | 122718 |
| accepted 2 | 52 | 181215 |
| accepted 3 | 76 | 240872 |
| accepted 4 | 105 | 316716 |
| accepted 5 | 129 | 378804 |
| terminal retained | 130 | 381174 |

payload中间态也单列在机器会计中。每append的六次内部扫描为`C_before + 2C_after_payload + 3C_after_state`，此外保留begin/commit/finish的check和create/read-view库存。按此原P1实例，writer＋terminal＋两reopen共76次完整inventory，对应5376个对象读取实例、17465962B逻辑读取；这是保存拓扑的结构投影，没有新IO性能观测。每次reopen的首次decode及bookend还各读used对象，pack/摘要、目录检查、point CAS及publication也未计入该字节数。十小时P2库存大小仍为null，不能线性外推五小时前缀。

原33份observer合计的175 selective/551描述、4 full/570描述、129指纹、185 journal runtime、prepare/propose30、accept15、summary3、audit52、124 builds/62 imports及journal生命周期均与五小时模型吻合；其中185＝journal自身56＋指纹嵌套129。独立只读wire元数据oracle另核各epoch和加权实例/bytes，不复用本工具算法。

## 机械执行与保存检查

[唯一CLI终态](execution_observations_01/command_01.exit.json)exit0，命令wall0.5746741s；该时间只属于元数据工具，不能充作公共整链性能证据。264不同输入首尾相同；Reader533次/5046716B，bootstrap3次/29094B，总536次/5075810B。Reader合作式计时0.4676907s，未包含导入/bootstrap。输出70247B、SHA d6397a1b8ef0d01a218aa86fe412e6e1a69cb05e4e6905c3ddf46e9512347226，close后身份/大小/字节读回一次，再打印绑定pin。输入逻辑读取、输出读回与解释器/模块导入OS IO分开。

40项最终普通检查在CLI之前通过（1.54s），覆盖显式事件展开、AST sites、wire图故障、Reader shadow/code、短写和读回漂移；41项相关旧回归通过（17.78s），其旧代码保持，之后本工具新增书挡由最终40项覆盖。旧20/37/40项中间记录与units_02的36pass/1 AST允许入口更新失败原样保留；不把不同draft的重复测试相加。绑定测试含首次输出缺席的pre-CLI前置，实际输出完成后使用保存后核验，不再通过测试重做唯一CLI。

PRE_SEAL findings闭合，无official verdict/receipt/seal。[stdlib-only后核验](postcheck_01/postcheck.py)核264输入、Reader/bootstrap账本、输出pin、独立wire oracle及351旧发布路径；原P1/B1–B3/685绑定仍按旧postcheck核，原输入成本诊断stdout精确复现。最终以保存exit记录与远端readback为准。

## 仍须推进

本次已把固定成功图的journal/prefix/库存乘数接到保存依据；没有覆盖十小时真实CAS/累计摘要规模、全部codec递归/独立数值审计、昂贵失败路径和outer/quiet采用成本。下一步直接固定昂贵失败矩阵与outer职责，复用当前计数和旧失败证据，先闭合无native开发与合法保存诊断范围，再决定需要哪一次有界成本证据。fresh60s＋最多5s收束与outer无进展65s仍缺父端余量；原停止帽不保证全包完成。完整稳定包/独立审查和新的native专项授权仍是后续门。

RTS-24主比较、两母线机制回归保持；139数值、完整F-X时序、C整体性能及D/E现实业务/设备工程、选择/敏感性/时域、留出来源和总预算仍OPEN。没有新P2注册/执行目录、native或长实验，目标“推进计划”继续active。
