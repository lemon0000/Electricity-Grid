# C：保存短前缀的独立 query 与 accepted state 合同

2026-10-24，DRAFT_NONAUTHORITATIVE。接续[单点交接](continuation_handoff_20261024_saved_point_replay.md)和[科学采用DAG](staged_deliverability_c_scientific_adoption_dag_v1.md)。本轮连接B→C→B；原C、P2七输入、guard/outer、B1–B3/P1及其已发布绑定字节保持。

## 固定问题与范围

只读P1的实际路径前缀，plan=`on_time`、clean=`early`、method=`full_temporal`，从原fixture的hour=-2和`initialize_execution`开始。最多连续五个模拟小时（-2..2）、21个slot：每小时reference economic root、可选故障raw child、recovery min/max child、动态actual primal。当前保存轨迹为4+4+4+5+4=21点；全部请求来自原reference compiler。4个F/X代表行和points22..31不在本轮范围。

调用方先持有独立fixture SHA、初始及逐小时accepted state SHA、保存schedule的选定slot、point完整文件pins、start的pins/registration SHA、outer quiet记录及选定source pins。原P1外部683文件锚及其postcheck stdout SHA在测试入口核对；不能从当前point CAS反推预期query或从保存state构造政策状态。所有SHA沿原`core.digest`定义；typed evidence的精确SHA继续由原C核对。

## DAG、停止及书挡

1. 完整outer quiet先于source或point读取；校验29来源和24个实际loaded src模块路径/字节。固定fixture、预算、caller expectations。
2. 原initialize→初始state SHA；每小时从已接受state生成reference requests，并逐slot核对独立schedule。以重建reference evidence绑定raw/recovery child，经原C执行raw→compile→snapshot→import→独立代数审计→精确typed SHA。
3. 原prepare/propose从已核reference/recovery和当前state生成actual功率；actual query由这些输入物化，再经原C。原accept及独立`causal_audit_v2.audit_execution`重算候选state；只有actual_accepted且ledger applied时才以核对后的state SHA推进下一小时。
4. numeric未决立即停止，不拼HourEvidence、actual或未来query，不推不可行；原政策拒绝保留attempted state/SHA、独立audit与attempted_summary，accepted state保持在拒绝前。返回的accepted_prefix_summary只描述已接受前缀。所有终态要求visited slot数等于held slots/point_files数，失败当前及后续state锚全为null；与已持有成功锚或未来slot矛盾时直接报错。输入/hash/transport/来源漂移直接报错。
5. 每次C前保存完整point pins/files/directories；返回前比较全部已访问point库存与文件/目录identity，且持有points_root及全部祖先identity。另复查29来源/24 loaded模块、fixture及调用方全部期望；不读取未访问point、journal或未来输入。固定五小时帽与完整前缀state SHA比较不等于可信journal chain验证。

选定point pins合计最多8192文件/64MiB；单点继续沿原C的24 buses/33 generators/38 branches和完整process/raw/observer合同。外部point目录只能包含原C文件族；完整目录/HANDLE防替换沿codec/mechanical原实现。失败不重试，不写CAS、journal、manifest、lease或gate。

## 调用量与验证预算

成功21点：42次compile、21次snapshot/import、21次C显式audit；five小时prepare显式5次，accept内部再prepare5次、propose显式5次且accept内部再propose5次。每次prepare先audit当前prefix，长度0..4；accept内部重复同路径；每次accept后独立audit长度1..5；最终summary再audit长度5，因此独立execution audit调用16次，重审历史row共40次，不能按每点常量成本外推十小时。reference_requests调用还包括每个历史row的独立重算；以计数测试核对，不隐去原audit中的parent/KKT递归。

每次C：86 source内容读取、point `6M+16`内容读取、成功typed pack 5次。前缀层首尾29+24=53，各两次106次source读取；21点C合计1806，故总1912（caller首次source_pins的29读另计）。C前及末次全部已访问point inventory各读`M+8`，故每成功点合计`8M+32`；points_root/祖先identity另作metadata校验，不跨点缓存CAS或审计。前缀初始化/每次accept的state digest、fixture/caller canonical书挡另计；这些是逻辑调用量，不是OS调用或wall/RAM/storage实测。前缀层不额外构建模型。拒绝路径增加一次attempted_summary的独立execution审计，按其完整attempt row长度另计。

普通测试固定解析小例与这一个保存五小时轨迹，不调用真实solver、native、子进程、journal writer或publication。单组pytest硬超时90s、不自动重试；日志、失败工件及source前后pins保存在独立non-authoritative目录。先运行定向测试，再运行相关causal/reference/单点回归，按唯一nodeid去重；PRE_SEAL只读独立审查与保留字节核验完成后提交。

## 验收及边界

须验证：独立root/child/actual查询、动态功率/parent/accepted-state依赖、五次接受与state SHA、故障调用和恢复余额、numeric/拒绝停止及terminal锚矛盾、拒绝attempt摘要与独立audit、未知quiet禁读、预算/序号/来源/fixture/caller/早期point末次漂移与同字节文件/目录/root替换；保存683文件与732旧路径/三导航旧正文不变。独立审查输出仅为PRE_SEAL findings，不生成official verdict/receipt/seal。

只报告所访问短前缀的expected query provenance及原政策状态一致性。`scientific_evidence_adopted`、全P2 expected provenance、trusted journal replay、独立139/F-X、resource/formal均为false。D firm/legal-X、E外部trusted genesis/head/state/CAS/failure和read-only reopen、F fresh/最终父采用继续分别验收。完整319、十小时增长/昂贵失败/full wall/RAM/storage、65s父端余量及C整体预算仍OPEN。原missing_input、coveragefalse、双null与专项native授权边界保留。
