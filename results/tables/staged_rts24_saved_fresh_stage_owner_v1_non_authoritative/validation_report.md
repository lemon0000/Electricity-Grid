# F 阶段监督组件普通验证

2026-10-25，DRAFT_NONAUTHORITATIVE。范围与固定caps见[合同](../../../docs/plan/staged_deliverability_c_saved_fresh_stage_owner_contract_v1.md)，当前执行入口见[交接](../../../docs/plan/continuation_handoff_20261025_saved_fresh_stage_owner.md)。本目录保存开发检查、失败和源码snapshot；原F输出目录尚未创建。

当前epoch为`affected_04`：68项stage与19项原guard回归共87项通过，wrapper wall16.422s、硬帽30s、无timeout、49选定源前后相同。`final_03`的105项在65.078s终态通过；其中28项adapter/bootstrap属于后续未变的域，`unaffected_domain_equivalence.json`核src整文件、ENTRY在STAGE常量前及测试在stage类前的精确字节。当前stage证据仅绑定affected_04源码，两个epoch各有三文件原字节snapshot。

前两组stage_01的43通过/6失败（9.140s）及stage_guard_02的67通过/1失败（13.671s）均保留。问题包括测试SHA初值、native线程结束竞态、sample双错预期、真实Job成员数硬编码及inner KILL_ON_JOB_CLOSE使预设残留后代自动退出。真正残留分支改为受outer Job约束的固定Popen探针。collection_01因隔离user-site缺少pygments退出，保留原日志；pytest根进程使用既有已安装依赖，真实探针始终`-B -s`及闭集受控环境。没有安装依赖或自动重试。

独立PRE_SEAL推动闭合：任意argv改闭集probe ID；fake逻辑字段与真实process/quiet分开；首错/末次书挡及普通context链保留；root最终双sample PID并集；环境一次冻结；Create调用前清LastError；terminal有效截止及单调停止时刻明确；OwnedStage冻结书挡；通道构造/attach双错保留partial capability；header/frame持久记录可独立重建SHA链。`preseal_review.json`绑定审阅源及支持证据，性质为开发findings复核。

11个真实短probe在`ordinary_probe_observations.json`保存。两条正常/嵌套成功，九条预设失败均安全结束并核完整quiet；最大采样tree RSS51,720,192B、Job commit21,475,328B、单记录9,353B。所有实际累计成员与retained身份清单相等且signaled；每份保存记录包含可重算header/frame及kernel观察时刻。普通1024成员oracle与超128KiB保留原观察测试是单元证据。物理进程/quiet字段对fake始终false。真实短probe资源不能外推F或C。

普通测试四组实耗104.311s、collection11.422s，标准库/格式检查另行记录，合计保持300s开发总帽。额外affected-only组在前三组终态及新findings后预登记30s，未扩大F预算或单probe上限。全部原始stdout/stderr保持原字节；Git空白例外仅按`raw_log_whitespace_exceptions.json`的确切路径/pin登记。

980旧发布路径、三导航body、P1全部683、原SF45与新增源集合SF49范围保持。公开production入口仍关闭；新增普通probe只是本组件开发验证。`F_launch_admitted=false`，两个局部F验证及整包科学采用、resource/formal false。完整角色/四文件发布oracle、最外层trusted invocation、同步I/O中断和controller自身资源仍OPEN；没有真实新五小时fresh/native/P2/正式实验。
