# C：successor 静态数据校验实现范围

2026-10-25，DRAFT_NONAUTHORITATIVE，接续[runtime交接](continuation_handoff_20261025_saved_fresh_runtime_binding.md)，起始HEAD `eb9c1a3de1d736a37b6c5ecb8ca96428e81e11f6`。root唯一writer、独立只读PRE_SEAL。本轮在原ENTRY追加31字段successor静态数据validator及原测试文件中的针对性测试；不改旧函数/类语义、scientific src、SF49集合、原F合同、guard/outer、P1及历史记录。

## API、独立输入与返回边界

`validate_saved_successor_data(context_raw, request_raw, *, expectation_raw, host_basis_raw, anchor_raw, runtime_contract_raw, deadline_contract_raw, request_contract_raw, now)`只解析标准库数据，不访问文件/目录/kernel、不导入scientific adapter、不运行capture/hold/replay，也不创建context文件或发行capability。

所有raw必须为exact bytes，并在解析前核对应byte cap；context/expectation/host basis各≤2MiB、request≤32768B、合同≤65536B、历史外锚≤8MiB。canonical JSON遵循既有ASCII/sort/duplicate/nonfinite/depth/node边界。host basis为独立caller数据的exact六键：source_pins、executable、environment、host_identity、broker_identity、output_parent_directories；不是从incoming context重建的expected。expectation是独立host捕获的原canonical envelope，外锚原字节须命中固定c6a25c... SHA；三份合同raw命中runtime spec v3的固定bytes/SHA。

实现全部31字段类型/上下界、20字段request域、5+2摘要等式、两个profile固定SHA、12项cross-field约束、来源数据一致性、实际683外锚map和独立E完整canonical子树匹配。broker/host及EXE/目录identity只检查数据形状与独立basis一致，绝不冒充kernel调用；source map只核独立basis/49闭集/Pin/预算，不冒充当前磁盘hash。E内部科学判断沿用原producer/full hold/replay合同，本函数不重写科学审计。

返回exact静态结果type，仅强持canonical context/request/expectation raw及SHA、独立basis/外锚/合同SHA和commit，不暴露可变解析树；每次entry重核commit，普通constructor与序列化拒绝。data_only=true；actual_sources_verified、actual_kernel_identity_verified、actual_clock_verified、actual_executable_verified、actual_environment_verified、actual_filesystem_identity_verified、deadline_enforced、full_P1_content_verified、run_authority、F_launch_admitted及全部科学/资源/正式gates均false。now是caller声明的finite float，只校验start<=now<=deadline并标declared_time_consistent=true，不证明当前未过期。即使自洽的caller声明通过，也只有数据一致性意义；该exact type被现有/未来issuer、owner、bootstrap默认拒绝，后续能力协议须另行实现。旧域和issuer不开放，runtime profile的UNDECIDED_BLOCKING不由此关闭。

实现与结果commit固定successor spec v3原字节pin：18167B / b151876e286f24dca3571134e4506e55978f0fe1dee949b76005f3e3c24b2f90；不把caller提供的spec当可变真值。测试及保存oracle独立核该pin。

## 验证与预算

独立普通预算240s：所有pytest attempt累计≤200s，baseline/collection/静态/保存核验≤40s；单次≤40s。先固定nodeids/组帽，保存失败/超时的raw、exit、source epoch和实际helper/script前后pin及snapshot；不自动重试任何actor，不新增actual F/solver/native owner。结果在`results/tables/staged_rts24_saved_fresh_successor_data_v1_non_authoritative/checks_01`，保存证据≤12MiB/192文件（普通检查包，原F的8MiB/64files/17targets不变）。

测试使用独立stdlib fixture builder，读取冻结spec v3/三合同/外锚及少量已固定SHA的P1 JSON/metadata，从journal genesis取历史fixture_sha，不import validator或复用其canonical/field/摘要helper；独立表驱动12个cross-field和闭集负例。broker/host/output metadata与时间是显式合成声明，不生成真实owner/kernel证明。测试覆盖代表性保存P1元数据、31字段/20字段闭集、精确类型（尤其bool/int）、float/时间、路径/身份、source/input Pin、独立E、profile bytes/SHA、所有摘要/cross-field、duplicate/noncanonical/oversize/depth、immutable结果/commit/默认拒绝域，以及不访问文件/模型/实际owner。重跑相关现存63节点，新的SOURCE epoch不继承旧63通过。静态核原全部顶层函数/类AST不变、其他47路径及全部前序证据/P1逐字保持。

pytest使用独立标准库harness，在任何仓库import前对既有NumPy lscpu调用安装上轮固定pin/stack/args的审计阻断，抛专用OSError走原fallback；记录该受控环境与每个进程attempt/blocked数。任何其他process launch拒绝；不得将此测试策略推作生产import政策，不宣称任意native副作用均为零。不再单独运行RAM反例或科学费用诊断；普通旧fixture仍可按已绑定合同读取保存P1并禁止scientific/native/write操作。

collection_03已终态7.844/8s；其全局profile观察器有明显开销。首个pytest前将Native guard改为预装import hook：固定source的process_guard_v1完成import、返回调用者前仅替换OwnedChild.__init__为拒绝器，保留原class供exact-type拒绝测试，finally精确恢复；不在整个测试期间保留全局profile。该47条非mutable source在每次检查首尾pin保持；这是测试插桩，不能作为生产runtime绑定。P1/actual树guard覆盖声明的open写与mkdir/remove/unlink/rmdir/rename/replace/link/symlink/chmod/chown/utime/truncate路径事件，仍不声称任意native改写均不可发生；最终独立核原字节。

开测前admission固定全部nodeids/分组/单组帽，计划累计帽≤200；预留至少一次窄组失败的重验空间。静态40s内先预留finalizer≤4s、保存checker≤10s和一次必要修正/末次核验≤10s，不靠运行后延长总帽。全部attempt均记账；不足即保存未完成事实，不启动F。

完成后仅新增静态数据接口与开发证据；角色专用bootstrap/store/owner、实际G0/H3、传递runtime闭包、NumPy生产政策、source6500/180s/失败/wire/host硬停止及actual F仍OPEN。下一步沿38节点协议补实际角色能力，不能把static结果字典当issuer或kernel证明。

首轮3+58节点终态后，仅补强两个新测试定义：tamper从7项扩到全部9项（增加anchor_sha/commit），局部无I/O拒绝器增加列明的metadata API。ENTRY未改，原61节点保留为旧测试epoch；refine_admission逐AST核仅这两个新定义变化，显式增加两个参数nodeid，固定新121+旧63=184节点及新source epoch后完整重跑。重新准入的组帽178s与先前已花18.922s合计196.922s≤200s，未增加总预算；不以旧61替代当前184。结果见[报告](../../results/tables/staged_rts24_saved_fresh_successor_data_v1_non_authoritative/validation_report.md)。

finalizer14在4s帽超时，实花4.031s计入静态账；已写出的navigation/document索引、当时三份文档snapshot和全部raw/exit/helper快照保留。新v2 finalizer仅核旧partial索引和文档image、生成当前v2文档索引及缺失support pins，不重复3518库存读取；完整库存仍由保存oracle核查。静态已花15.546/40s，剩24.454s；事前固定后续finalizer17≤2s、saved15≤12s、terminal16≤10s（共24s），仍在原40s总帽内。任何后续失败均保存，未达终态不称保存链完成。
