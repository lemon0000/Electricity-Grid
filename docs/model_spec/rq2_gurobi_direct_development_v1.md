# 当前 Gurobi normal 接口兼容性检查

状态：DRAFT_NONAUTHORITATIVE。当前安装 Pyomo6.10.1、gurobipy13.0.2。旧跨引擎pilot和license规模记录只用于定位可复用路径，不证明当前H25 normal通过。

## 发现与最小处理

使用已有2小时tiny normal、5秒/1 thread、seed0、原gap1e-8和容差1e-9，直接调用现有numeric kernel时未通过，返回对象的errors字段为 `native_result:ValueError:typed native solution status required`。两次针对检查分别1 failed（2.90秒、2.60秒）；第二次仅增加断言错误详情。这两次为pytest会话观测，未形成H25归档证据。

本机 `pyomo/solvers/plugins/solvers/GUROBI.py` 的Python接口将 `sol['status']` 字符串直接写入solution status；`GUROBI_RUN.py` 返回字符串 `optimal`。现有candidate要求 `SolutionStatus` 枚举，因而正确地拒绝了这个不匹配。该失败不是模型不可行，也不应通过接受任意字符串或跳过原生状态校验消除。

新增 `src/solvers/rq2_gurobi_direct_development.py` 显式通过 `SolverFactory('gurobi', solver_io='direct')` 选择由gurobipy驱动的Pyomo GurobiDirect插件，固定版本、接口类型、5秒/1thread/seed0和原数值选项。保留默认算法；不做状态转换、不修改原生结果或原候选代码。实现身份绑定自身、原adapter、factory路由、direct接口及SolverResults/SolutionStatus/SolverStatus定义模块源码。未来normal后继必须显式绑定此adapter身份。

## tiny 证据及当前边界

`tests/test_rq2_normal_gurobi_tiny_v1.py` 仅在pytest内替换factory，以隔离检验direct接口与已有严格native inventory、canonical assignment、optimality、normal witness逻辑的兼容性。direct路径得到完整tiny assignment和witness，并通过原normal_accepted断言；scope反例在factory前拒绝。补齐结果类型定义源码绑定前为10 passed（2.40秒），此前6项反例/兼容性测试为6 passed（2.53秒）。独立审查指出结果类型定义模块缺少显式绑定，现已补齐并增加5项依赖漂移反例；最终15 passed（2.52秒）。

这是测试注入下的接口检查，未集成任何生产或有界H25执行入口；既有normal的execution identity不绑定该测试注入，因此不能用此测试结果替代新接口的端到端身份、记录和回放证据。旧normal、5秒任务、冻结代码及其全部结果不修改。本次未运行Gurobi H25，也不选择正式引擎。

下一项是在独立审查后，将显式direct接口纳入有独立身份的最小normal后继，并通过相应记录/回放验证；再按预先固定的同模型、同5秒预算执行有界H25交叉验证。原最优性、残差、完整witness及60秒normal门保持。

本接口draft独立pre-seal已闭合，源码依赖binding finding已修复；独立最终15 passed（2.40秒），无开放实质finding。该结论限于上述tiny接口兼容性，不授予H25结果、生产回放或正式权限。下一步为normal后继集成。
