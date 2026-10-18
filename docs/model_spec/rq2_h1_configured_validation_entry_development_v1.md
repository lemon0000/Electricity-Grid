# H1 显式解释器路径校验入口

2026-10-17，DRAFT_NONAUTHORITATIVE；R3 development / PRE_SEAL。
对应六里程碑第 2 步的重复依赖身份开销。模型、输入、数值验收限、逐小时重放、
source/registry 观察点、lane carry、提交与恢复语义沿用原合同。

## 实现与边界

候选固定包位于
`results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/validation_path_optimization_01/entry_revision_03/`。
后继保留既有 CodeReadLease、MetadataParseLease、CanonicalPathLease，使用
`-I -B` 启动、明确登记依赖支持目录，并仅去除完全相同的 `sys.path` 字符串。
五个原隔离路径和 REPO/tests、支持目录形成八项固定搜索向量；路径新增、重排、
非等字节别名及错误解释器均拒绝。pytest 使用显式 importlib 模式，关闭外部插件
自动加载，拒绝未固定的 `PYTEST_ADDOPTS` / `PYTEST_PLUGINS`。

配置绑定实际入口 manifest、path policy/helper 的 SHA，形成独立
`active_validation_identity`。旧 scientific identity 只能说明原科学投影，不能代表新执行入口。
旧固定包、失败 attempt、原 chain_07 的 36 项启动 pins 保持原样；本后继没有对其进程发出控制命令。

原 `importlib.metadata.version/distribution` 与 stock resolver 每次仍实际执行，
不缓存 discovery 或 distribution 选择结果。既有 MetadataParseLease 仅在每个 discovery
window 内，对持有 no-write/delete lease 的八个 exact PathDistribution METADATA
复用 parsed version value；重置窗口时清空这些值。标准库已有内部缓存语义保持原样。
本版本没有采用固定 D-root metadata dispatch，也没有采用目录通知作 namespace 缓存失效证明。

## Origin admission

- 在 repo 导入前检查 planned stock `PathFinder` 解析的十个 top-level origin 和当前文件 SHA；
  尚未加载的模块仅记录为 `resolved_not_loaded`，不主动导入 SDK。
- 在 pytest configure、collection、setup/call/teardown 进出、pytest 返回和 entry 退出
  检查实际已加载模块的 object/spec/loader、inner loader、name/path、package paths、
  origin 及当前文件 SHA。未加载与已加载的两类记录明确区分。
- 绑定 PathFinder/FileFinder 委托函数、path hooks、importer-cache/container 及固定路径
  对应的 exact FileFinder。额外 finder 仅允许有固定 owner SHA、class、object 和函数绑定的
  Pyomo callback / 最后位 MovedModuleFinder，以及当前 config 的 pytest assertion hook。
- C 支持目录仅允许明确登记的 Pygments、Colorama 源文件；模块名称须与相对文件路径
  一一对应，并核 spec/loader/SHA。既检查指向 C 的其他 namespace，也检查这些
  namespace 指向其他根或缺失 origin 的情况。跨观察点替换或删除已见模块均拒绝。

上述 admission 只证明离散边界的 planned route 与 loaded origin 元数据、当前文件字节。
它不证明已经装入内存的代码字节、完整 SDK/submodule/native DLL provenance、
连续导入路径或修改后恢复的并发 ABA。沿用单 owner、无敌对并发 import mutation 的验证范围。

首次失败保留 boundary/reason 并 poison 后续 admission。teardown 即使在进入时已
poison，也必须先允许 fixture finalizers 执行，再报告守卫错误。receipt 写入失败不得
阻止解释器设置、cwd、搜索路径恢复或后续 pin 检查。

## 验证及预算

保存 raw-audit 对照仅各一次，60 秒 / 512 MiB sampled RSS / 64 MiB 存储上限：
Rref 11.463455→9.821175 秒，Actual 7.658076→6.800654 秒。
1,883 个共有模块 origin/文件 SHA、140 个保存文件、764 个 source/package pins
及科学投影、selector record、bridge identity 一致。结果详见
`validation_selector_incremental_01/configured_entry_comparison_02.json`。
该比例仅覆盖该 raw-audit 输入；它不代表本固定包、完整链或正式实验的总提速。

固定入口单元预算 120 秒 / 512 MiB sampled RSS / 64 MiB 新工件；
最终单元终态 `entry_revision_03/unit_checks_07/terminal.json` 为 78 tests，
77 通过、1 项 Windows symlink 权限 skip，exit 0。包含真实 pytest 的 call-exit
漂移反例，确认 policy 报错后 fixture finalizer 仍执行。
原 routing 12 项的实际生命周期集成也按 120 秒 / 512 MiB / 64 MiB 单独登记；
任何新字节均须由对应终态重新支持。最终汇总绑定 package/member hashes 和确切终态。
失败、中断及较早 package 字节的结果保持原记录，不能替代最终版本。

## 下一出口

2026-10-17 后续固定包`entry_revision_04`已在独立目录应用D site-packages→C support顺序，
入口代码/leases沿用entry03，stock discovery函数及调用保持；仅path policy末两root交换，
package/launcher绑定更新并保留e5a predecessor。21-member manifest SHA为
`d13a08fe6db35e9c5c70b8204e3fb4d0091e43a3ef483e3951a561eac0667e43`。
同码实际raw-audit对照为Rref 9.686548→9.512673秒、Actual 6.665008→6.367484秒（合计2.8829%），
全部1883 loaded-module集合及origin/fileSHA相同，764 source、140 saved、8 METADATA与science/record一致。
新的77pass/1权限skip、12routing及完整生命周期/终态postcheck通过；详见hour0 evidence根
`validation_operation_witness_01/path_order_comparison_01.json`和
`validation_path_optimization_01/configured_entry_04_checks_01.json`。lookup微测约20.65%只作局部线索；
stdlib自身内部路径缓存未禁用，不能称每次cold filesystem discovery。旧entry03和其结果保持原样。

本工作尚不关闭完整 hour-0、整体性能准入或后续里程碑。启动新长链前仍须完成
common/Parent/handoff 重复工作 DAG 的成本与合法复用审查，覆盖成功提交、
失败分支、回调、关闭重开及独立重放。特别是 successful consume 的现有静态下界
为 528 次 full numerical hour audit 加 528 次 fresh context revalidation，
不能靠局部搜索路径提速消除该调用倍数。
不从本记录推导 official review、resource admission、native 校准或正式运行授权。

## entry07 固定 vendor 代码字节后继（2026-10-17）

当前non-authoritative manifest为
`ab0ad89e7efa04c57185dca779a822ea5ae70fc07c0fbb2cd92f2e03360f1925`，33成员。
原149 repository code与614 test清单保持exact相同；另固定D-compute Pyomo的7个代码文件、
128055bytes。交给未修改CodeReadLease的union为exact156项、root=D:/；其他文件仍走原
fresh-read fallback，不扩大为drive-wide缓存，不缓存输入、数值结果或distribution discovery。
vendor snapshots单列tested_bytes/vendor_code/pyomo，不加入sys.path。双manifest SHA、counts、
root与vendor路径绑定active validation identity；实际模块name/file/spec/loader逐项核对。

在initialize和紧邻实际union lease开启前拒绝vendor预载，code lease提前包住fixture导入和
清理；MetadataParseLease在原fixture/patch完成后进入，按原顺序先退出再patch.undo。退出后
fresh复读原149和7vendor字节；arm/phase退出时必须有完整7模块origin。原identity函数、
SHA256、stock metadata函数和发现调用不变。未增加正式运行权限或生产consume入口。

当前unit09为93pass/1权限skip，actual pytest sampler03为13pass；四个拒绝CLI检查通过，
monitor的7个cleanup/storage runtime helper AST保持前代相同。一对保存common._arm为
38.905162→36.279179秒，outer51.859→48.953秒；science、完整audit和metadata receipt逐字节
相同，461saved/33锁/36旧pins及source/tested copies核对。此为整个入口后继的单对方向性结果，
不把6.75%单独归因给7文件；identity-only四worker micro才隔离该文件集合的效果。
证据位于hour0根`validation_operation_witness_01/vendor_saved_arm_comparison_02.json`和
`vendor_configured_sampler_checks_01.json`。限定范围PRE_SEAL findings闭合；完整hour0、
整体性能准入和后续资源/official/formal门继续OPEN。
