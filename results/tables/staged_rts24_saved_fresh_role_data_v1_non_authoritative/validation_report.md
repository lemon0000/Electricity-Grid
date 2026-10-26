# 三角色 data-only 入口开发验证

2026-10-26，DRAFT_NONAUTHORITATIVE。见[范围预算](../../../docs/plan/staged_deliverability_c_saved_fresh_role_data_scope_budget_v1.md)和[当前交接](../../../docs/plan/continuation_handoff_20261025_saved_fresh_role_data.md)。结果终态以本 root 的 checkpoint_status.json 和保存检查原 exit 为准。

新增 controller、parent、fresh 三个固定数据校验入口与不同 exact immutable result type。校验绑定冻结 registry/templates、原 context/upstream 对象、声明原字节、packet/permit/descriptor 摘要链、episode原start/deadline、声明因果次序与跨祖先 transport 名称/nonce。独立 basis 只支持声明与 pin 一致性。结果数据不能变成实际 permit、owner 或 producer provenance。

同一完整 Source49-map SHA `2ec1638c2c11867100e589073c16271063578d34223979f045e6e04ed1c5befa` 的480目标节点已通过，分为旧282和新198。新节点覆盖三角色正例、closed shape/type/cap、对象/creator/context漂移、同字节换对象、重哈希双侧篡改与独立basis、声明时序、原episode、ancestor别名、状态gate及六个普通 capture 故障逻辑；普通 harness在repo导入前安装guard，精确阻断一次NumPy可选lscpu。

pytest charge242.7843532/360s，含失败role_1 18.2613637s。role_1首次超时只有30个dot，没有harness结果；后继role_1_retry完整重跑48节点，另外三组各47，189互斥节点与已完成291节点精确合成480。collection_02与admission_03的导入/预备超时同样保留，全部失败计费；未缩节点或增加总预算。原admission/run.py与测试期runner snapshots完整保留，最终recovery工具限制closed actions并使用独立helper epoch。

实现仅向原ENTRY追加391行、向原测试追加395行。旧定义AST、其他47 Source路径、scientific adapter、全部4123前序路径和P1全683由保存oracle复核。原10域/59节点/21设计项及旧两次保存失败保持原字节。新21个development declaration schemas只属于本轮声明校验。

checks_01保留全部执行snapshot、raw logs、exit、原/恢复分组与文档索引；final_package_01绑定finalizer外部exit之后的main inventory和自身helper。saved_05、terminal_06各自只核已完成的前序records，本次capture须由外部exit及最终Git逐blob承接；完整charge见checkpoint，不以目标运行时间代替capture计费。

实际 fresh、最终父端采用、真实bootstrap、full projection语义、producer capability、issuer/owner/Job和整包科学采用仍未建立；资源与正式门禁保持false。没有新增科学运行或模拟小时。完整workflow wall/RSS、真实deadline/hard stop和任意native副作用不存在均未由普通测试证明。
