# 自然返回之后的B_S续接：准入草稿

2026-10-28，DRAFT_NONAUTHORITATIVE；未实现、未登记、未执行、未分配新实验预算。依据[1344 open真实自然返回](continuation_handoff_20261028_saved_fresh_import_return_v1.md)。宽goal仍为持续推进F，不把本草稿或单次return视为完成。

当前前驱NFC7 checkpoint SHA b56159068165115b54866169be5fb228cbaad6079081b79b85291443a8d58ce4，16文件1138658B；累计866.467895100049s、不接受37条。旧73文件5158740B及各自预算/失败保持冻结。本包余26.659556800004793s留原包，不转用；关闭的PID40080不恢复。

## 真实剩余路径

冻结census2048 helper的diagnostic_import_once已经实际得到importer返回，但立即抛AuditCensusStop；pre-import runtime.source_bookend已执行，child source_bookends=2。load_bootstrap_adapter余下路径在本轮未执行：authenticate_machinery → NumPy fallback状态核验 → 13个源码函数与2类shape → freeze_adapter_roots → post-import/final Source49 bookend → sys.modules retained tuple → boundary.close → runtime.finish_import。随后才可能建立本地OBSERVED，再在另一次具独立profile匹配的路径中评估LIVE；两者均不打开role/P1/permit/F/science/resource/formal authority。

下一后继应保留2048前超限stop与所有原失败路径，在自然返回分支允许已验证result交还loader，并单独记录返回后的阶段。import census与后续成本分开，不把停止计数后的未观测open补成旧census事实。原helper/parent/core及NF7 records不动，需独立版本、输入闭包、constructor/oracle与PRE_SEAL。

## 首先完成的审查

1. 按当前source枚举完整调用DAG，计算runtime.entry、boundary._entry、check_adapter_roots、source_bookend及namespace graph重读倍数；不得让历史checker或post-import回调重复隐藏增长。
2. 检查authenticate_machinery在audit callback之外的code/default/closure读取；覆盖getter重入、metadata同对象改写、pending→authenticated顺序、重复认证/错误stage与保留primary/secondary。NF7的observed2/auth0不替代这些证据。
3. freeze_adapter_roots核adapter模块的13函数/2类，并调用held freeze_namespace_graph；当前reader的depth≤256、nodes<50000只是防护帽，不是当前图规模或运行成本。需要实际节点/bytes/retained对象及后续图bookend成本，不能从入口34个graph frame或import3.8277s反推。
4. 分清图image bytes、强持objects、sys.modules retained tuple、Python/native内存、process working set与private commit。NF7的138.8203MiB sampled child peak不证明128MiB retention达标或违规；已有256MiB/process与512MiB/pair sampled stop策略可作后继诊断候选，连续覆盖/descendants/正式资源门槛仍OPEN。
5. 固定新success/failure输出schema、profile/raw/packed/root上界及保存重开；不得要求仍以“未完成policy”的旧异常链作为成功分支。记录close前真实runtime phase与close后终态，明确OBSERVED与LIVE的独立profile前提。

预算须覆盖以上实际新增路径、所有前后source/inputs bookend、失败与清理及checkpoint。成本未知项未界定前不分配或启动完整后继；可按agent.md第9节先固定问题/规模/次数/caps做有界诊断。不能仅沿用NF7的20s actual帽、机械扩大窗口或把剩余秒数视为授权。

所有科学模型、阈值、原Source49、B1–B3/P2与发布绑定字节保持。当前没有新P1/实际role/OwnedChild/Job/F、model/solver、native校准、长实验、外部下载或paid query；production/official/native行为认证/科学/资源/正式/run authority继续false。后续工作仍须唯一writer、独立只读PRE_SEAL及适用的实验准入。
