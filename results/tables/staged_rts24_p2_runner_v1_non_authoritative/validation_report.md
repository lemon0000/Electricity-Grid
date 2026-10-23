# P2内部执行器开发检查

2026-10-23，DRAFT_NONAUTHORITATIVE。按[开发合同](../../../docs/plan/staged_deliverability_c_p2_runner_development_contract_v1.md)实现Cursor、actual/完整合同循环、point transport/worker、fresh与内部worker CLI，以及监控准入v2。没有outer launcher、新执行注册、公共P2 attempt、native调用或资源准入；原准备三文件保持execution_supported=false。

## 已实现与验证

Cursor在采用前核顺序、角色/请求SHA、事故、完整父point/economic、已接受前小时state SHA、参考集合及证据族。静态packet不回填；实际request/BQ/父point/KKT身份进入每点request的独立execution_binding。任一槽/接受/结束阶段协议异常永久锁死，reservation不退款；不能修补输入后重试。

actual按fixture.observation_end结束，不被registration_end截短。只有全部actual接受、未stopped且到观察末端才进入h1/2 normal→69×(F,raw)。firm point、raw child-LP独立重审及normal/firm/raw点/economic/child SHA保存到合同行。有效负面legal_X继续枚举；证据审计失败则停止依赖。合同不修改actual ledger。transport/quiet未知后不继续finish/fresh；异常记录禁止采用，不否认可能已存在的terminal。

数值传输保留父子compile、raw/log绑定、两次import及quiet后采用。fresh继续调用原journal.reopen，比较完整原metrics且零solver。原journal/runtime、codec、core、numeric/backend源码不变；P2新七输入及冻结context的55来源另由执行pins核对。此身份范围继承原selected runtime边界，不宣称完整OS/stdlib闭包。

监控v2仅改变P2提案上限（3600s/65s/8192文件）及错误信息；函数其余字节与原v1对应段一致，直接复用原OwnedChild/controlled_environment/scan_output，进程commit1GiB/Job2GiB、HANDLE1024及5秒收束保持。提案仍未准入。

- 最终`units_03`：50 passed/88.16s，外wall89.291569s，七输入首尾相同。包含三母线5模拟小时actual/fresh、明确注入的负面legal-X控制分支、FakeApi双重导入、来源漂移在point/quiet/fresh拒绝、永久失败锁存、状态篡改、terminal存在后的失败诊断、注册类型/额外字段拒绝及短Python Job清点。5模拟小时和普通检查wall不能作为公共P2成本。
- 相关`related_01`：原numeric/backend/Win32 owner共110 passed/6.96s；没有修改旧源码或调用真实Highs。两次早期35/45通过记录保留，但不作为最终源码覆盖。
- 只读实现/领域PRE_SEAL指出的失败证人、来源闭包、协议重试、raw最优性与state freshness问题均已修复；没有official verdict、seal、receipt或运行许可。
- [独立stdlib后核验](postcheck_01/postcheck.py)exit0：七新输入与55旧来源匹配、监控后继机械差异闭合；原P1683文件2950863B、B1–B3118文件及685前序路径保持，前五次发布259路径保持。原P1与准备包两份旧postcheck stdout精确复现，没有新科研重放。公共P2执行目录与新执行注册均不存在。

## 下一成本步骤

[结构成本表](../../../docs/plan/staged_deliverability_c_p2_runner_cost_review_v1.md)核内部条件满成功路径：319槽、1276构模/638import，新增138次raw KKT重审；load_packet960、P2 fingerprints1281、preserve3。准备三工件hash读取子量1781129625B，加两种JSON读取后逻辑读取2345752302B，未包含旧指纹、CAS/journal/原审计等。它们是源码会计，实际执行量为零，没有P2 wall/RAM实测或提速结论。

接下来先登记一次无solver的来源/packet核验诊断，再证明合法复用/优化，补outer launcher/quiet后采用与完整DAG及昂贵失败/十小时保存成本。当前完成的是内部接线开发；1431/4273、139数值/F-X时序、C整体性能与D/E现实输入/选择/留出仍OPEN。P1一次native授权已用，新P2/native/长实验未授权。
