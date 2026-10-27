# NFC6：完整控制器与分段准备计时

2026-10-28，DRAFT_NONAUTHORITATIVE；实现已形成draft，首次size/登记/单测/cold尚未执行。本文件为独立后继首次执行前合同。前驱[NFC5 scope](staged_deliverability_c_saved_fresh_census1024_phase_budget_scope_v1.md)及所有NFC1–5、trace、memo原字节、费用和失败保持冻结；不修改旧caps或转移余量。

目标仍为唯一真实1024个guard-passed open或其前自然返回的完整诊断终态，再saved/checkpoint重开；不是单测或局部方法分数。NFC5唯一size的command29706/30000与registration_max516434/524288均合格，但charge3.332350500000757/3s拒绝；随后元数据checkpoint accepted=true/diagnostic=false，charge0.7197095000010449/3s。原包4文件194044B、合计4.052060000001802s、0 register/unit/cold；cp SHA 7177125654559df795938fd722ad46f0ddfdb6276c636a1d3063763c01c7c256。当前累计static333.1141281000557、pytest366.48897970000326、unittest97.22373020000305，总796.826838000062s、不接受37条。

没有静态证据可把NFC5的3.332s归因到某一项。已识别的完整size工作包括prerun pins、13份compile-only、固定leaf/前驱输入与archive、迁移AST与source/transport、60模块graph、首次stdlib导入与203 origins、两次全量input pins、两次Source49读取、manifest/codec/command、registration candidate及序列化。原fresh书挡和固定leaf全部保留，不为一次size结果删观察点。NFC6在其唯一size内部记录上述11段耗时，计时器与额外序列化自身也计入size；timings只解释这一次准备路径，不外推cold、完整import、RSS或资源准入。

独立DAG及caps：size≤6 → register≤3 → 唯一14节点unit≤10 → PRE_SEAL≤4 → startup≤5 → profile≤4 → 唯一actual1024/return≤10 → saved≤4 → checkpoint≤3秒。static≤39、unit≤10、总≤49，阶段帽相加等于整包帽，最坏累计845.826838000062s。size6s覆盖已经观测的3.332s完整准备成本及首次导入/系统抖动；其余沿NFC4完整unit7.213s与full-check约1.3–1.5s量级的独立后继分配，不修改原46s包。每check又核NFC5的344项size输入，属于新增fresh工作，预算仍有不确定性，必须以本次唯一终态为准。

新root为results/tables/staged_rts24_saved_fresh_nfc_v6_non_authoritative，初始仅driver.py与import_policy.json。policy沿原4745B/SHA 4b731fc38ed2b52bff727acf0b02e4b8da7396cb17f2354225b34348155d9e9c，进入initial inventory、size/registration inputs、manifest和16文件/4MiB布局。命令≤30000 UTF16、stdout≤131072B、stderr≤32768B/census≤24576B、decoded≤131072B；写前预留phase退出和checkpoint，unit失败raw恢复不扩帽。首次执行前因新增timing validator、反例和绑定源码快照，独立NFC6 registration文件预留589824B（576KiB），实际candidate+1024B须先准入；旧NFC4/5的524288B帽不变，整root仍≤4MiB。

size在写入前、register、每次check及checkpoint均核timing结构：固定11名及顺序、exact row keys、finite非负float秒数（拒绝bool）、总和≤同口径charge，charge为finite float且accepted与size6s/command30000上限一致。test07在原14节点内追加缺项/重排/extra/NaN/Inf/bool/负数/超和/错误type及错误charge接受关系反例。这只核结构和代数一致性；producer时钟和registration前的任意FS篡改仍不获独立真实性认证。

core33/probe31/parent30、native fixture5与test6由experiments/staged_rts24_saved_fresh_census1024_controller_relocate_v3.py精确构造，仅迁移输出与core/probe路径、test01追加本层路径oracle，test07预算fixture39/10/49与越界50。原14节点、其余全部断言、原scientific/source49和census1024_none_v2 helper原bytes保留。Source epoch仍acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875。

前驱ledger固定上述NFC5 cp，另硬绑定NFC4 false cp 774f4978e333bb05b79f6245f86e2e4b6faf4b2d3ff566046712f2dc84be6b4d及其完整unit原记录；明确区分metadata accepted与diagnostic accepted。每check保全前驱41文件3054186B、NFC4直接345项与NFC5 size的344项输入；不执行NFC4/5 checker。固定v3 leaf仍每次完整执行，不增加递归checker链。继承输入933→1051→1061为无冲突精确union，新source/size另外绑定；NFC4 unit只作历史证据，必须跑本包自己的14节点完整30帧/report/exit0。

当前registration按fresh inputs、graph、runtime origins、Source49、迁移、command、helpers/snapshots和全部控制字段重建，并作精确canonical schema/type比较；固定stdlib预载含pickle与unittest.mock传递依赖。Unit父/子前后4次full check，普通phase前后2次，checkpoint一次；每次保留冻结leaf内部约2496次显式Path.read_bytes，另加前驱/当前输入与artifact。pin-memo继续不接入，也不再跑局部基准。

最多1 unit child、2串行cold child；仅startup/profile与唯一1024诊断。任何拒绝保存原raw/partial、费用和checkpoint后停止，无自动重试、顺延或退款。进入cold前必须完成本包尺寸/登记、完整unit及进程收尾、独立PRE_SEAL findings闭合和live process核验；不得仅凭v4/v5字段采用旧accepted结果。

所有F/actual role/P1/OwnedChild/Job/model/solver/native校准、科学/资源/正式与run authority继续false；没有长实验、外部下载或paid query。计费沿原capture口径，不是全部开发wall；本包不授予完整runtime、任意RAM/FS或独立时钟认证。39项并行dirty原bytes和所有历史结果保持，宽goal继续active。
