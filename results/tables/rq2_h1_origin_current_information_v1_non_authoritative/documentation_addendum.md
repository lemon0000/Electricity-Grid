

### 2026-10-08 — approved-origin accepted-N current join 开发复核闭合

新增 `experiments/h1_origin_current_information_development_v1.py`、对应测试与
`docs/model_spec/rq2_h1_origin_current_information_development_v1.md`。公开 prepare 仅接收 N root、
binding/terminal pins、completed_hours 和 registry pin；从 fresh accepted-N declaration 派生
source 坐标，内部取得 registry prefix，核对当前 raw power row、package、N before/after、
input/clock、component inventory、repair cap nameplate 与 first/transition 时钟。
返回前重验 N、registry、source observation 与 implementation identity。
返回对象只保留当前 decision/frame/source origin/current action/audit；完整 prefix 留在内部。
PRE_SEAL F1（冗余 chronology_origin 公开字段与规格不一致）已删除并独立复核闭合。

初版根定向 25 passed/14.08s；相关合并 68 passed/35.38s；独立初审 25 passed/11.27s。
修复后根 25 passed/10.82s、独立 25 passed/11.03s，全部 exit0。
独立只读 reviewer `/root/outage_origin_design_review` 的意见仅为 PRE_SEAL findings；
无 official verdict，真实 native=0、Job=0。检查证据目录为
`results/tables/rq2_h1_origin_current_information_v1_non_authoritative/`，保留修复前快照和原检查记录。

此单元测试以 synthetic accepted-N reader/source-loader seam 检验 join，不证明真实 accepted-root
执行集成；accepted_root_integration_verified、detached_consumer_authenticated、persistent_lane_owner、
common publication、192小时执行、resource_admission、formal_execution_ready、formal_result 仍 false。
enrollment 仍为1..168；后续F≤24只服务尚未解决的既有义务，不产生新 enrollment，不重置 debt/budget。

后继顺序：current-only saved-record persistent owner（独立 Rref/actual carry、完整 business cursor、
sticky same-key conflict、外部 retained head、intent-first 和 outer paired commit）；真实 raw ingress/Job/
计时预算；必要的 follow-up producer；完整 manifest/合法复用 DAG/同合同 LB-UB；资源准入与 successor
封存；全新实例 official 独立审查；具体 native 包另获明确授权。
旧 episode_store 绑定完整 future planned hours，不能原样充当 H1 owner。可借鉴 SQLite 单事务、
lease 与 retained-head；科学 key 排除 source labels、raw witness SHA、N audit head 和 clock offset，
audit chain 单独保留这些内容。所有中断、bare intent、冲突和失败记录保留；不自动 retry。
