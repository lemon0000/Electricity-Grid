# Journal v2保留闭包：开发验证

2026-10-23，`DRAFT_NONAUTHORITATIVE / PRE_SEAL`。按[短探针合同](../../../../docs/plan/staged_deliverability_c_journal_retention_probe_v2.md)仅启动closure_probe_01一次，exit0。修复使用独立journal_v2；旧v1源码/合同/531个核心工件保持原字节，旧75秒测量没有重跑。

## 修复与普通检查

最终独立sol_reviewer发现v1的F14：删除旧CAS后writer仍可能采用下一小时，fresh才拒绝。v2草稿又定位F15：旧genesis/条目在append窗口消失时，单独核新entry不足。后继现在绑定完整CAS及root inventories，校previous SHA链，预先纯pack得到全部期望新key，采用前核旧全集加新增闭包、旧root加新entry、原目录身份，最后核runtime。fresh从外部Fixture/state重算累计集合，核trusted已知前缀；不以缺口推导不可行，不自动补回或resume。

24项新普通无solver检查通过：19项58.51s、另5项7.08s，覆盖三方法两步正例、旧fixture/payload/state及genesis/hour删除、准备/CAS/entry窗口、额外root、伪造inventory、runtime末段漂移、attempt/terminal及known rejection。连同旧358项不同普通检查，本检查点合计382项；重跑不算新增case。它们不作为公共整链预算。

## 唯一短探针实测

从旧保存CAS读取full_temporal前两小时的完整HourEvidence/actual及期望state，不重新生成任何点。两步后finish保持原观察结束5，显式missing_input；原债务40右删失。一个fresh child退出0，完整state科学/typed SHA、summary、independent_audit、科学/发布结果及terminal状态逐字段与旧两小时结果相同。没有把前缀关闭当作五小时覆盖完成或服务通过。

| 路径 | selective编译 / 列表描述 | 结果 |
|---|---:|---|
| 两步保存/关闭 | 13 / 44 | state与旧保存相同 |
| fresh保存重放 | 13 / 44 | 所有登记指标一致，债务40右删失 |
| begin前移出fixture CAS | 0 / 0 | writer不采用；fresh拒绝缺失retained CAS |
| entry1 rename后移出旧fixture CAS | 3 / 9 | writer保持旧state/ordinal0并标unknown；fresh拒绝缺口 |
| rename后读回unknown、闭包完整 | 8 / 24 | writer不采用；fresh确认1条final，仍为incomplete_journal |
| 合计 | **37 / 121** | P0=37、raw=10、恢复min/max各37 |

每个故障仅移出新case的对象，删除前核SHA并备份为removed_object.json；缺口及原始字节均保留，未恢复对象或重试。旧full compiler、solver/native请求均0。声明删除分支不是现实坏盘/掉电/阻塞I/O耐久性证据。

[report.json](report.json)脚本报告前elapsed27.1709143s；[watchdog](launcher.json)outer27.9132234s，0.2s轮询采样tree最大RSS418926592B。核心138文件286322B逐SHA匹配；终态扫描含已完成日志142文件311956B，另预留launcher16KiB/1文件。60s wall、20s无进展、30s child、512MiB、8MiB/600文件均未触发，进程已退出。核心与后加本报告/postcheck/verification/findings的角色分别记录。

v2新增全集key、root链和额外末核，元数据与prefix工作仍随Σt增长。此27.9s只对应full_temporal两小时及三个失败case，不能与v1三方法五小时75.1s直接作速度比较，也不能外推公共网络或192小时。

新probe父进程bounded读5591次/36973173B，未包含全部import、普通写入或watchdog扫描；它不是总磁盘I/O，也不能使用旧v1的16881次/96199735B代替。

## 绑定与剩余门

6个新直接文件、旧13个直接源、v2的28个runtime仓库源/配置、十个外部入口/版本、旧completion/report以及genesis/hour0/hour1输入角色首尾一致。旧531核心/558007B、B1–B3 118保存/42repo/7external及C/build/causal字节核对保持。见[只读postcheck](postcheck.py)。本检查点审查仅PRE_SEAL findings，未创建official verdict、receipt、seal或运行权限。

推荐后续使用journal_v2保存API，旧journal_v1只保留历史证据和F14记录。公共normal C/P0/child/actual及g、139节点合同层、完整反事实F/X时序、长cohort/真实native失败、C整体性能和D/E点数/资源仍OPEN；native须另登记具体包并获专项授权。
