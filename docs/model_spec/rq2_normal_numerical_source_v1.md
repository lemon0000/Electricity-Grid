# Normal 数值验收的来源绑定与计划投影 v1

本候选是通用只读连接层，复用已批准的数值验收、来源重建及normal信息投影。
开发期间为DRAFT_NONAUTHORITATIVE；封存及独立审查状态由outer和单独receipt记录。
它不执行求解，也不改旧normal record的接受状态。

## 输入及验收链

`normal_numerical_source.prepare_information`接收通用`solve_once`输出的canonical原生数值记录bytes、
既有`ScaleNormalSourceRequest`、`PlanInformationDeclaration`以及调用者独立保留的record SHA、
binding identity和byte上限。binding覆盖完整source request、信息声明、记录摘要、大小限额及实现身份。
复用direct Gurobi的`validate_spec`，保持1e-9残差/整数/目标一致性和1e-8原生界gap口径。

严格核对原生报告inventory、类型、options、状态跨通道一致性及false authority字段；
重建已绑定的source/pair/normal inputs，检查实际模型structure，按封存数值验收重算完整赋值、
原生目标代数关系及连续时序见证。只有数值接受时才调用已有`prepare_normal_information`。
投影与新验收必须使用相同source/assignment身份和terminal carry，投影见证也须通过1e-9限额。
连接层另外独立重建完整静态网络、逐小时出力/启停/前期启停及forecast、初态、planning参数，
复算allowed plan identity；逐字段投影不符、漏小时、双层计划标识一起替换均拒绝。
Prepared/Witness须为精确类型，causal/formal authority保持空/false。
返回前再次重建来源、读取声明并检查实现与binding。

未取得完整provenance或未通过数值最优性时返回unresolved及None计划；超时、无incumbent和未决
不解释为数学不可行。schema、外部pin、来源或模型不符则拒绝调用，不发布投影。
信息声明必须在首动作前发出，继续标注mechanism_assumption；策略侧仅消费已有current-hour view。

## 证据边界

输出证明归档数值记录与当前锁定来源及计划投影之间的对应关系，不能认证这些native通道的历史OS来源。
外部控制器仍负责durable intent、process监督和记录来源链。本组件不产生新的normal执行worker、
capacity证书或formal runner，也不将固定H25记录变成其他来源的求解证据。
report绑定prepared audit identity和allowed plan identity；调用者归档时仍须独立保存它们。

mechanism初态、forecast和功率映射的角色保持，registered coupling、native authentication、
完整资源、exact数学、安全及formal认证均false。上层正式工作流还需把此证据与每次normal调用及
episode初始输入一起绑定，并完成真实规模成本、完整科学合同、capacity及training/holdout验收。

## 验收

使用小型源数据夹具的真实短求解产生输入，再禁用求解入口完成投影；覆盖正常与未决路径、
错源/错hash/错binding、旧阈值与接口误配、重复字段和错误metadata、缺赋值、来源及实现中途漂移、
投影见证与完整计划/网络替换、未来信息及策略侧隔离。
`experiments/verify_rq2_h25_normal_projection_v1.py`对已有H25档案只作零solver重放，
核对外部归档pin，生成完整25小时/158UID投影，不重复长求解。
准确测试、交付包hash和pre-seal状态另记closure与blocker register。
