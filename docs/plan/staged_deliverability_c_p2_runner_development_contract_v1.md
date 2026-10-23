# C：P2执行器无原生开发合同

2026-10-23，DRAFT_NONAUTHORITATIVE。接续[P2准备](continuation_handoff_20261023_p2_preparation.md)，本轮实现独立P2 controller、point/fresh/worker接线及监控准入后继；仅作普通解析/fake API/受控微进程检查，不创建P2公共执行目录、执行注册、native实例、production seal/lease/receipt或运行权限。

## 固定执行与验收

原319槽packet及P1/B1–B3/科学源码保持。原core/codec/journal/numeric/backend、数值阈值及journal runtime原样复用；P2执行器、监控后继与准备packet由外层执行pins绑定，不能将新执行来源伪装成原genesis身份。plain_v2继续是未接线候选。

| 验收项 | 具体检查 |
|---|---|
| 槽与父身份 | 固定顺序、319上限、静态request SHA、动态actual仅由proposal生成；child绑定parent_slot的已导入完整父point/economic；运行身份另存point request，不修改准备packet |
| actual时域 | next_hour < observation_end覆盖h=-2..7，不被registration_end4截短；每小时参考完整后begin/proposal，actual后commit；只有十个actual均接受、未停止、循环完成才进合同 |
| 合同枚举 | h1/2 normal各一次，69事故按F/raw串行；firm与raw审计由原数值接口兑现，合法证据上的legal_X=false继续枚举；合同不改变actual状态 |
| 失败 | 首次数值/协议失败停止依赖且attempt不退款；参考未决不造HourEvidence，actual未决保存non-adopted attempt；transport/quiet未知禁止commit/finish/fresh；已知策略停止保留并finish |
| 保存与fresh | 原trusted binding、finish→fresh、父端reopen metrics一致；fresh不调用solver；观测或终态保存失败不报告成功 |
| 监控 | 新版显式允许P2拟议帽，旧版不改；沿用1024成员HANDLE、Job归零且HANDLE signaled、5秒收束；没有降报帽值或扩大内存限 |
| 身份与权限 | 核P2 packet、源码、原环境/科学pins和历史字节；新执行注册与旧准备包分开；CLI无参数/缺注册拒绝，不生成注册或公共attempt |

## 工作量与边界

成功数值路径仍319点、160QP/159LP，每点父子两次显式compile和两次import重编译，合计1276构模/638import。新cursor增加槽/父身份与接受阶段核对，合同保存138份raw child-LP独立重审；该审计不调用compile/import，包含point/parent/reduction遍历。具体fingerprint、保存、replay、失败和收尾工作量随实现记录；旧P1成本不能直接外推。

P2整体停止帽继续是准备包中的提案：3600s/无进展65s，point10s，solver5s，fresh60s/无进展60s，RSS1GiB、进程commit1GiB/Job2GiB、64MiB/8192文件，串行、零重试。开发监控检查只使用fake owner或短时Python进程，不运行上述P2包。尚未形成十小时writer增长、完整合同/昂贵失败的代表成本，不称资源准入、ETA或139数值证据。

本轮完成条件为：具体代码接线、针对性失败/身份/控制测试、相关回归、只读PRE_SEAL实现与领域检查、旧字节核验及交接。后继仍需完整性能/资源审查、具体稳定包独立审查和新的专项native授权；P1一次授权不继承，用户“不启动长实验”保持。
