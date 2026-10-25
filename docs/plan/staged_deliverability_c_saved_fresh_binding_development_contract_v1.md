# C：F saved 子角色入口与建构输入开发合同

2026-10-25，DRAFT_NONAUTHORITATIVE。接续[文件入口交接](continuation_handoff_20261025_saved_fresh_entry.md)，起始HEAD `bdeebb784575824742f89b76be7e11ad5a730a1c`。root唯一writer，复用只读PRE_SEAL reviewer；原三draft可迭代，所有旧snapshot、失败、超时及冻结字节保持。

本轮推进实际saved context的接口：parent/fresh唯一canonical argv、独立saved bootstrap、RoleStore/execution_context对同一held context/tree/channel的强绑定，以及未来owner构造所需的封闭输入。只有接口和建构输入可在本轮完成；实际saved constructor/watcher、trusted supervise、CLI接通、保存P1真实fresh与最终科学采用继续待实现。不会执行production preflight/spawn、科学重放、solver、seal或正式运行。

## 范围与不变量

- `argv_for`成为唯一saved parent/fresh builder：`EXE -B -s ENTRY --saved-entry --parent|fresh --context PATH --context-sha SHA --tree-sha SHA --channel NAME --nonce NONCE`。context已持有input/output root，不再另收这两项argv。descriptor由role派生，不接收外部override。旧模板仍作为设计历史保存；当前supervise没有saved trusted-invocation绑定，builder必须拒绝。
- saved parser在读context、attach或import前拒绝未知、缺失、重复、乱序、缩写、NUL、非规范路径/SHA/transport。ordinary grammar/schema与saved grammar/schema双向隔离，不将SCHEMA加入ordinary bootstrap。
- `SavedFileBootstrap`与ordinary能力分域，持有原raw context、role、tree SHA、transport、完整argv/orig_argv、main/module/path、source/executable的字节及file identity、环境和creator/thread。不能只因全局对象存在就允许RoleStore或科学分支。
- RoleStore初始化核同一raw context/role/tree；完整protected check和execution_context另要求同一Open-only stage writer，固定name/nonce/context/descriptor。未绑定、替换、关闭或跨角色/树/上下文复用均拒绝。只有未来saved role入口可在正确顺序绑定该writer；本轮公共main仍拒绝saved flags。
- owner建构输入为不可变、creating-process数据，不是owner、lease、run authority或可执行factory。只接parent/fresh的精确production descriptor和canonical argv，无factory/callback/descriptor/argv override。保留原ordinary constructor/watch的mode拒绝，不把saved label列入ordinary conhost cache例外。
- owner输入必须从同一held saved RoleStore及其原reservation派生tree/context/writer，不收外部tree SHA；生成数据即消费该reservation，不退款、不重置开始时间。consume的最后一次store检查后重新核context/source/EXE/environment及`invocation_started <= reservation.start <= now <= deadline`，之后仅做纯内存提交；输入后续check也核相同书挡。实际constructor尚未实现，未来还须强持同一数据对象、原开始时刻及真实launch capability，不能把当前data当成执行许可。
- saved受控环境同时核冻结键集合与每个实际os.environ键值，既拒绝绑定后新增allowed键，也捕获六个forced键被归一化掩盖的漂移。ENTRY文件identity与完整父链进入proof/commit并在protected check核验；原始source字节书挡和executable identity继续保留。这些是已观察书挡，不声称原子文件系统快照或覆盖未观察ABA。
- 保留SF49集合、原科学adapter、原F范围/预算文档、旧guard/outer/P1、17 targets、四份128KiB记录、一次parent/一次fresh、零solver/重试、40+5+5及180s。proof只保存有界identity/SHA，完整context不嵌入record；不增加输出target。

## 有界验证

新successor预算仍为300s：pytest累计≤240s，collection/静态/保存核验≤60s；每组预登记节点与cap，单组≤45s，必要affected组≤30s，无actor自动重试。普通role回归按预登记互斥短组执行，旧45s超时保持，不能写成成功。只使用原ordinary进程fixture和纯接口/注入的单位测试。

可为接口测试在内存构建SCHEMA context bytes，使用当前P1锚与SF49的只读capture；不创建真实OUTPUT、不重放B/C/E、不构造真实saved owner、不执行真实fresh。真实输出父目录尚不存在；单位夹具显式替代该目录identity并输出logical标记，不能称为实际context的物理身份核验。正例中替代main/transport/native边界只证明单位接口行为，不是实际文件入口、OS身份或科学采用证据。禁止借测试输出mode进入saved execution_context。测试覆盖context/tree/channel交叉、writer角色、重放与creator/thread、main/argv/orig_argv/alias/path/EXE identity漂移、Open-only与closed endpoint、proof长度和不可序列化、public CLI保持拒绝。

本轮还增加terminal image冲突后sticky unresolved的直接单位检查，并有限分组核角色回归；真实root-exit残留helper窗口仍OPEN，不通过强制系统console挂起、伪造kernel PID sample或重复试跑制造正例。保存检查直接核旧字节、冻结source snapshot与原P1，历史通过数不计当前epoch。

## 出口

保存所有attempt的stdout/stderr/source snapshot、节点/预算、输入/source首尾、diff/link和独立PRE_SEAL findings；更新报告、导航及交接，完成授权Git同步。整体调用量/最大合法context与四record编码、昂贵失败/发布成本、实际saved owner/watcher、trusted supervisor、arming/最终I/O硬中断及全流程资源仍按原顺序闭合。局部saved verified、F_launch_admitted与整包science/resource/formal/public P2全false；本轮数据能力不授权实际F。
