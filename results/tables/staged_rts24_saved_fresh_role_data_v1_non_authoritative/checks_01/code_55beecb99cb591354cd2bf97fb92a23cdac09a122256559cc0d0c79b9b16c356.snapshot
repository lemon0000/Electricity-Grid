# C：保存 actual 前缀与 trusted journal 的只读连接合同

2026-10-24，DRAFT_NONAUTHORITATIVE。接续[四代表行交接](continuation_handoff_20261024_saved_contract_replay.md)，推进[科学采用DAG](staged_deliverability_c_scientific_adoption_dag_v1.md)的保存P1局部E。仅新增普通集成测试与保存证据，不修改原B/C/D、journal、模型、输入、容差、生产runner或运行权限。

## 固定范围与输入

原P1为683文件/2,950,863B，其中journal为137文件/427,629B，含genesis、五个hour entry、一个terminal entry和130个CAS对象；实际路径为-2..2五模拟小时/21点。外部锚为原postcheck_03.stdout.json固定SHA及其683文件pins；start、launcher、request_schedule、trusted_binding、prefix0..5及所有CAS均须先绑定该锚。最终trusted binding为closed=true、known_entries=6、publication=committed、scientific_outcome=missing_input、failure_sha=null。

完整quiet先于worker数据读取。固定45个选定source文件首尾pins；沿原journal runtime_identity的28仓库来源、10外部入口与executable，共39内容读取/次、两次校验，保留Python/六包版本核对。不宣称完整运行时闭包。

## 有界DAG与等价核对

先核全部P1库存/pins/files/directories及根/祖先identity，读取期望只能使用该原始库存中的锚定字节。原fixture与initialize→原B逐小时政策生成query→原C重建21点raw/KKT/typed SHA→接受state→原journal_v2.reopen，按trusted genesis/head/state/CAS/failure重建原政策、功率、债务和期限。逐小时prefix SHA与原entry after-state核对，最终B状态与重开状态的digest和typed CAS根均相同；重开state中reference/raw/recovery/actual的21个PointEvidence typed根及query SHA逐一匹配B的原C重建输出，不能只比较CAS自报摘要。

终态须保持missing_input/committed/known、六entry、130对象、accepted小时5、最后接受hour2、resume=false，且无pending/未引用CAS/unaccepted attempt/failure/pending terminal。summary与独立audit核对，coveragefalse、两条件null、余额和已观察期限状态保持；不生成未来小时。全部P1库存/root/source/caller期望末次复核，包含完整683 pins map、fixture digest与source期望的冻结canonical image；P1外部锚另重读原始字节/SHA、文件及祖先identity。调用方可信绑定九字段被篡改时，原reopen必须拒绝，不以重新计算的值替代期望。

真实保存集成禁止SolverFactory、Highs构造、backend make_model/call_highs、Popen、CAS put/publish和journal create/begin/commit/finish；不调用native或writer/resume。相关原journal普通回归可按原测试合同写自己的pytest tmp解析fixture，不能触及保存P1。新检查不生成production manifest/lease/receipt/seal。

## 调用量与停止预算

原B成功路径：compile42/snapshot21/import21、prepare/propose各10、execution audit16/历史row40、typed pack105、source1912内容读、point2152内容读（185CAS）。journal reopen不构模/求解：prepare/propose各10、execution audit17/历史row45、直接typed pack14，加EvidenceReadView首次get的13个根规范化重编码（fixture/初始state、五对payload/state、terminal payload；末次state已验证），共27；两次runtime_identity共78内容读。CAS M=130、全部U=130被使用时，四次全inventory及两次used/decode为4M+2U=780内容读，七root两遍＋genesis一次＋六entry一次=21，故journal内容读801。

连接另pack21个重开PointEvidence及两状态根，共23次；总typed pack155、execution audit33/历史row85，构模仍42/import21。全P1库存首尾各683内容读，共1366；选定source首尾各45内容读，共90。含B与runtime源内容读合计2080，P1内容读取合计1366+2152+801=4319；外部锚末次另读1次。caller首次取得外部锚、launcher、fixture及Python模块导入/metadata读、目录stat、canonical/digest编码另计，不把逻辑计数或测试时间当OS调用及整体资源实测。

只共用同一次初始库存里的绑定字节和原operation内CAS缓存，不跨点/小时省略原审计；保留B与journal独立政策重算及全部parent/KKT。固定单个五小时保存轨迹，不扩大到全319/十小时；每组普通pytest硬超时90s，无自动重试，source前后pins、终态和失败输出保存在独立non-authoritative目录。原journal_v2的24个相关nodeid按collection顺序固定拆为两组互斥12项，仍各90s，核并集恰为24；原近帽成功日志保留，不扩大超时。全P1读取沿原8MiB单文件、64MiB/8192文件与目录/metadata帽；实际固定约2.82MiB，RAM峰值仍未知。超过范围或任何锚/identity/数值不一致立即失败，不新增或补写数据。

## 验收与剩余边界

须观察上述实际调用计数、21证据与最终状态的精确typed SHA、完整库存/source书挡；覆盖genesis/head/state/CAS集合/entry数量/outcome/publication/failure/closed九字段可信绑定错误，failure反例须使用内部自洽的persistence_failure tuple以实际检查缺少的failure文件；以主链共用的末次caller seam覆盖files map、fixture、外部锚字节/同字节identity、source期望漂移；冻结image也包含anchor的identity/祖先期望，替换文件并同步篡改identity期望仍须拒绝。运行相关原journal回归覆盖pending、unknown、unaccepted、实际拒绝、retention和终态失败。独立只读PRE_SEAL、836旧路径/三导航旧正文和P1全部683文件、diff/hash/process检查闭合后提交。

只报告saved_P1_journal_reopened和保存21点的连接一致性；全P2 journal_replayed、scientific_evidence_adopted、全P2 expected provenance、完整139/F-X、resource/formal保持false。原D四代表行不替代actual政策轨迹。F还需同输入fresh及最终父采用/失败发布；全319、昂贵失败/十小时增长/full wall/RAM/storage、65s父端余量、C整体与D/E现实输入/方案选择/敏感性/冻结后留出仍OPEN。
