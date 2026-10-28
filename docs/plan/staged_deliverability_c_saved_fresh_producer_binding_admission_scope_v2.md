# F：同一LIVE owner消费binding的有界真实连接

2026-10-28，DRAFT_NONAUTHORITATIVE。承接[一次性接口开发检查点](continuation_handoff_20261028_saved_fresh_consumer_binding_unit_v1.md)，其checkpoint SHA549fe7b12a498c8fdde4e67e5397a2b4dd137881c42dcd54411436b562e8e509；998.2357513999843s累计费用、不接受38条、128文件11375838B原档及各旧包余量保持，不能转用或重置。本scope为未执行draft，root唯一writer，既有wire_root_review只读PRE_SEAL；无official verdict/receipt/seal。

## 目标、路径与权限

复用冻结core38、namespace consumer helper v2和probe36，首次在重新bootstrap的同一真实child中完成IMPORTING→prepare→原NF9 profile逐字匹配→LIVE→固定ENTRY `_expectation_binding_entry`实际调用→CONSUMED→runtime/resource/boundary CLOSED。仅binding consumer；不调用capture_saved_expectation或P1，不授予producer capability、角色/permit、OwnedChild/Job、模型/solver、长实验或正式运行权限。原Source49 epoch acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875及所有旧源码/输入/结果保持。

包根 `results/tables/staged_rts24_saved_fresh_nfc_v11_non_authoritative`。新parent35、validation v2、constructor、测试、driver/checkpoint均独立后继。DAG固定：size（compile、原archive/1134闭包、exact transport/完整命令/存储/输出帽）→register→唯一unit→只读PRE_SEAL→唯一startup discovery→startup/reference admission→唯一normal→saved全量canonical重放→checkpoint→Git。不递归运行前驱controller；仅重开冻结证据及原v3 leaf。当前scope以实际注册的代码/输入/依赖、命令、Source49、profile和原流pins绑定。

真实normal先原native self owner/namespace transfer，再B_S audit handoff、唯一adapter import（2048 selected-open诊断窗，正常应自然返回）、finder认证和14-root/retention/source bookends，按原NF9 profile501203B/SHA a61fb973180f4031ebc024bb69ab162460955594c4bb53cc182d3da70559d3b6精确commit LIVE，再使用预先固定的同对象consumer计划。消费者不收到owner/runtime，仅收到10-member binding；结果最多2048B canonical data且只在成功close后返回。

调用图预测并冻结验收：Source49 bookends7；namespace graph25、adapter graph13，共38对/76帧（原全局图帽40不变）；auth1、finder_check14、adapter_check12、profile2。prepare增加的两次entry落after_boundary_close；consume两次entry及自身close落after_finish_import，最后probe close为幂等调用。22 stage顺序不变，真实返回前selected census仍≤20帧、≤2048 selected opens；它不计后续Source读取。若真实数量不符，拒绝并保存，不从观察结果重定义本包接受条件。

## 传输与性能选择

原parent34 zlib命令29996/30000 UTF16不能直接加payload。新codec候选固定XZ/CRC64/preset6，已读本地Python3.12 API并核[官方LZMA文档](https://docs.python.org/3.12/library/lzma.html)。单 `LZMADecompressor(FORMAT_XZ,memlimit=64MiB)`、单decompress max_length131073，要求输出≤131072、eof true、unused_data空、check CRC64和payload固定SHA；不自动接受第二stream。即时释放decoder及临时lzma/hash alias，保留probe需要的zlib/base64 alias，compile/exec exact payload。DLL directory cookie只关闭一次，解码/编译/exec失败仍清理；双失败保原primary和cleanup链。64MiB只是decoder限制，非进程/combined retention上限。

新启动路径早期引入lzma/_lzma及hash primitive，虽原NF9最终profile已有这些模块，仍须重做startup实际opens/modules/cache与runtime leaf绑定；不能仅据module集合推等价。prefix继续原token/AST/递归code-image等价；payload raw、位置AST和完整CodeType逐项相等。完整list2cmdline UTF16上限30000须对discovery/normal分别算。测试覆盖无效base85、truncated/CRC corruption/trailing/concatenated stream、131072/131073边界、decoder内存失败、错误SHA/check及DLL清理失败，不能exec科学payload测试。

优化复用原graph reader、memory_drain、Source49与原reference，不减少fresh bookend，不增加P1 I/O或历史replay执行次数。旧真实NFC10包39.6642s、normal阶段10.1975s/30及receipt6.3700s，旧开发41项unit15.0952s/30，作为本包预算依据；新增4次runtime entry/8对graph、98次Source fresh-read及codec/cleanup测试的完整实际成本仍由本包测量，不外推局部压缩耗时或CPU样本。

## 预算、停止及保全

static80s、unittest30s、总110s；size8、register5、唯一unit25、PRE_SEAL5、startup6、profile/reference admission5、normal30、saved5、checkpoint5。名义static69s/unit25s；剩余11s static/5s unit仅同包失败保存。每个阶段一次，不覆盖、不隐式重试。费用包含失败，另保留工程/人工/Git wall边界。新增模拟跨度0h。

沿用256MiB/process、512MiB/pair、10ms sampled parent/direct-child memory guard、最多4096样本、原HANDLE/PID/80B结构；监测异常、超限、stdout>131072/stderr>32768或wall无进展到各phase硬帽时按原actor停止、清理并保存原流/异常/exit和未知状态。该停止帽不证明连续、descendants或128MiB retention。Decode在self owner之前，列入conditional startup TCB和包级RAM，不能声称独立TCB/native行为认证。

root最多17文件/4MiB，registration≤1MiB、单receipt≤1MiB、unit/saved exit各≤128KiB，单manifest≤65536B；size先验证精确worst-case输出和packed保存上界。若任一帽不满足，保留拒绝终态且后继另包登记，旧预算/失败不退款。schema、精确枚举、完整unit终态、真正consumer结果、原profile/raw/context、parent前后reference及saved/checkpoint全部相连才接受本包诊断；所有科学/资源/正式/run/F gates维持false。父端采用和完整生产/资源闭包仍属后续实际要求。

工程准备记录：首次完整命令30153/30150超帽候选的helper及transport原字节、pins、命令计数和1.3473566s工程wall已保存在 `transport_preparation.json`，作为本包初始第三个文件。没有受控phase或child，不把工程wall混入既有capture账；受控不接受38条和本次工程候选拒绝分别保存。随后仅缩短临时别名并补齐全出口释放，不放松任何解码或清理条件。XZ无外部zdict，证据使用prefix_pin和external_compression_dictionary_used=false。
