# C：独立科学采用的读取DAG与费用边界

2026-10-24，DRAFT_NONAUTHORITATIVE。接续[outer交接](continuation_handoff_20261024_outer_binding.md)。原七输入、outer/checker/guard/parent已发布版本、B1–B3/P1均保持；本页不改变协议、容差、F/X定义或运行权限。

## 顺序与独立来源

| 节点 | 输入及其独立锚 | 输出/验收 | 失败边界 |
|---|---|---|---|
| A 所有权和机械包 | 父端持有context/startup/process；选定源/注册/三packet；完整quiet | 两库存、completion、319/138/10引用及内部Job集合 | quiet未知不读worker；transport/保存未知不当数值不可行 |
| B 预期科学query图 | 独立冻结fixture、schedule；上小时已接受state和当前参考点 | 逐ordinal预期完整BoundQuery与parent/accepted-state绑定 | 不能从同一CAS query反推“独立”预期；actual只由原政策/已接受前缀物化 |
| C 单点raw科学重建 | B的预期query/请求frame；A持有的完整point文件pins | typed CAS→独立compile→raw snapshot→import→独立点/KKT审计→精确证据SHA | quiet未知禁读取，硬读界超限停止；原raw/options/API/getter/cleanup规则；numeric未决无evidence |
| D F/X逐行 | 经C重建的normal、独立firm和raw child最优点；原rights | firm点审计＋raw `audit_legal_x`；逐行与保存audit相同 | legal-X为false仍保留，不截断raw或冒称minimum/完整时序 |
| E journal/政策/余额 | 外部持有trusted head/state/CAS/failure binding；C已核轨迹点 | 原read-only reopen独立重建政策、设备/功率、债务/期限、失败/右删失 | accepted/pending/unaccepted/observed failure分开；禁resume/CAS put/publication |
| F fresh与最终采用 | E的完整metrics与同输入fresh；父端前后完整库存和来源 | science/metadata/发布三层状态分别报告 | source、库存或发布漂移转未决；terminal存在不等于父采用完成 |

顺序为A→B→C；C的actual证据支撑B的下一小时；C→D，C＋独立trusted binding→E→F。D及完整F/X时序和E的actual业务轨迹各自验收，不能相互替代。独立性指原代数审计/政策重算及外部预期锚，仍复用冻结compiler/codec；不是第二个solver或不同算法认证。

## 调用量与复用

P2完整成功图为319点（12 economic KKT、159 child LP KKT、148 primal-only）和138合同row。新增C每个成功点显式compile一次，`import_snapshot`内部再compile一次，即新增638次构模、319次snapshot转换和319次import；不能遗漏import内部构模。每点还执行一次显式独立audit以返回残差/容差；import自身的audit和其parent递归审计仍保留，不跨点缓存。原worker已有1276构模/638 import，新增C后条件算术为1914/957，尚未含其他未来构模路径，不是实测。

第i点numeric未决若发生于snapshot：本点1次compile/0 import；若发生于import则最多2/1。之前已核点不退款，后续不生成。quiet未知禁止读取，point自报资源/transport不合规在构模前拒绝；global失败但已quiet的包可作有界局部数值诊断，不能因此采用整个包。之前已核点不退款，不补点或推不可行。失败行、terminal、fresh、父采用和保存成本仍须分别核算。

D额外138次firm审计、138次legal-X（各含原point/parent审计）；重审LP与KKT包含于C，不用原保存的`child_lp_audit`替代C。E使用现有journal.reopen；其每hour的prepare/propose/accept、audit_execution前缀及CAS/摘要增长复用[既有会计](staged_deliverability_c_p2_workflow_accounting_contract_v1.md)，不能当线性十小时常量。P1已保存五小时前缀的reopen证据只覆盖原范围。

单点文件reader采用两次完整库存，并以单次EvidenceReadView读query与evidence、完成其CAS书挡；expected pins来自调用方先持有的A结果，预期query来自B。该operation内CAS缓存是原codec已有行为，不能跨点/跨小时复用。全部文件、source和调用方预期frame/query首尾相同，不减少原API/getter、目标、行活动、reduced-cost、KKT或容差检查。

当前选定源组23文件，每个source书挡另复读20个实际loaded src module：两次书挡共86次内容读取；319点对应27434次源内容读取，调用方首次持有source pins的23读另计。单点CAS有M个普通对象且闭包完整时，双point库存读2M＋16个root文件，原EvidenceReadView的inventory/decode/used-bookend/末inventory另读4M，合计6M＋16次point内容读取。成功路径直接typed pack为5次（预期query、decode query、decode保存evidence、重建evidence、预期query末次书挡）；numeric路径为3次。以上为代码逻辑调用量，不是OS系统调用、实测IO或whole-package资源上界；目录/stat/字符串/摘要和临时Pyomo对象另计。

## 本轮出口与后续门禁

本轮先实现C的单点只读组件及三类解析小例，原P1代表点可作为普通只读回归；不执行公共P2、native、新的full-journal科学运行或长实验。C只证明“在调用方预期query和pins下，单点保存证据可重建”，不证明B的完整前缀独立来源、全319、D/E/F或整个包科学采用。

完成C后仍须连接B的动态actual query与已接受state、D的合法X对照、E的trusted reopen和F的一致结果/失败发布；再做具体有界整链代表测量。模型构建、raw/CAS/规范编码、重复parent审计、journal增长、最终发布的wall/RAM/storage目前都不能由局部测试外推。fresh60s＋最多5s收束相对65s无进展帽的父端余量仍OPEN。所有resource/formal、独立139/F-X及C整体保持未准入。
