# C：三角色 data-only 入口验证交接

2026-10-26，DRAFT_NONAUTHORITATIVE。起始 HEAD/origin `e4e02343ffceb3605fe839dbe6646ea7fba9cbd1`；接续[上游 archive 交接](continuation_handoff_20261025_saved_fresh_upstream_archive.md)，本轮以[范围预算](staged_deliverability_c_saved_fresh_role_data_scope_budget_v1.md)最新恢复段为准。root 唯一 writer，既有独立只读 PRE_SEAL；完成状态以新 root 的 checkpoint_status.json 与外部 exit 为准，Git 同步另核远端。宽 goal 保持 active。

ENTRY 新增三个固定入口 `validate_saved_controller_entry_data`、`validate_saved_parent_entry_data`、`validate_saved_fresh_entry_data`，以及三种 exact immutable data type。它们校独立 raw 声明、原 context/upstream 对象、packet/permit/descriptor、episode、projection pins、声明时序和 transport ancestor；仅建立本地数据与声明间一致性。独立 basis 不证明独立 producer 的来源或 capability。context 原 creator 未建立；本地对象 id/creator 不进入 wire packet，也不跨进程传递。

当前同一 Source49 epoch `2ec1638c2c11867100e589073c16271063578d34223979f045e6e04ed1c5befa` 下，480 个目标节点完整通过：旧282 + 新198，12 个成功组。pytest 总 charge242.7843532s/360，包含 role_1 首次超时18.2613637s；30个dot未继承。collection_02、admission_03 和 role_1 三个当前失败均原样保存；旧 archive 的两次失败继续保留。Source49 名称集合、其他47路径、旧定义 AST、scientific adapter 和全部4123前序路径由保存检查复核；其中 P1 全683。

所有实际 F 输出仍缺席，未增加模拟小时。status 中 producer capability、full projection semantics、physical clock/kernel/FS、role bootstrap、reservation consume、issuer/owner/Job、run/F/science/resource/formal 均 false。冻结10-schema与59节点设计合同不改；新增21个 development declaration schema不是生产 wire 协议。

本轮保存入口：`D:\Miniconda3\envs\compute\python.exe -B results/tables/staged_rts24_saved_fresh_role_data_v1_non_authoritative/final_package_01/saved_checks.py`。先核进程、Git、[验证报告](../../results/tables/staged_rts24_saved_fresh_role_data_v1_non_authoritative/validation_report.md)、root checkpoint，以及 saved_05/terminal_06 原 stdout/stderr/exit。oracle 不导入当前 ENTRY、fixture 或测试 harness，重核代码 snapshots、exact node sets、完整账、冻结 inventory 和 pin 绑定的前序 stdlib archive。CLI 严格核当前 Source/nav；未来 archive 模式只能保留 frozen480，不能继承当前节点通过数。

预算仍为普通 pytest≤360、static≤120、总≤480s，单组≤45。全部尝试真实 charge 计入；static 在最后三次保存检查前已用45.5662806s，finalizer≤12、saved/terminal各≤22，后续最坏 static101.5662806。bookend I/O、0.5s tail reserve 与未包含的 wrapper Python 启动分别记录；这些不是完整 workflow wall/RSS 或硬停止证明。checks≤160files/12MiB、package≤24files/2MiB；最终 freeze 在 finalizer 外部 exit 落盘后建立，不自证尚未结束的本次 capture。

下一步应先固定 successor mailbox/entry header、failure record、local projection 与 startup 的生产域，再连接真实角色 bootstrap、独立生产者和 retained owner/Job。生产 NumPy probe 政策、33根传递闭包、source6500/180s、完整 workflow 资源、host硬停止和真实timeout仍 OPEN。actual fresh、最终父端采用和整包科学采用尚未完成，不由本轮480节点开放。
