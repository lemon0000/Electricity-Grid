# 当前研究任务清单与预算缺口核对

日期：2026-09-28。DRAFT_NONAUTHORITATIVE，零solver核算；不登记科学参数或推荐运行预算。
复现入口：`experiments/audit_rq2_current_workload_inventory_v1.py`。
机器证据：`results/tables/rq2_current_workload_inventory_v1_non_authoritative/audit.json`。

## 已有来源与条件算术

脚本先验证H25来源、旧H25配置、旧科学配置和公开交付input_status的四个SHA，再读取实际UID、
小时和旧normal上限。来源是已有training示例：25小时、158 UID、22,275变量/28,004约束；
配对、MW映射和初态仍为机制假设。H25来源不是完整研究支持。

保留全部UID词典序级时，每小时reference为160次、每臂actual为159次，25小时共19,900次，
再加一次normal为19,901次。下表只改变假设的selector每级上限；normal保留旧15秒用于算术，
并不建议继续使用15秒normal，也不声称该时限已通过最优性门。

| 每级秒数 | reference每小时solver预留 | actual每臂每小时solver预留 | H25加normal总预留秒 | reference在3600秒内剩余非solver空间 |
|---:|---:|---:|---:|---:|
| 1 | 160 | 159 | 19,915 | 3,440 |
| 5 | 800 | 795 | 99,515 | 2,800 |
| 15 | 2,400 | 2,385 | 298,515 | 1,200 |
| 22 | 3,520 | 3,498 | 437,815 | 80 |
| 23 | 3,680 | 3,657 | 457,715 | -80 |
| 30 | 4,800 | 4,770 | 597,015 | -1,200 |

3600秒来自当前`normal_task_process.TaskProcessBudget`的逐子进程上限。episode有5H个此类phase；
它们的总wall另由完整envelope约束。余量还须容纳准备、逐级构模/重审、归档及接口开销；quiet另计。
表中总预留不是实测耗时，不能据此推断1秒或15秒足够求解。未选正式每级预算，因此现在无法断言
所有真实任务都需要扩展inner接口；23秒及以上的等额示例则已有明确算术冲突。

## 完整清单尚缺什么

旧科学配置可以机械复算36个factorial加10个OAT，共46个cells；cell不是episode。
该数字也不自动注册连续successor的窗口、容量评估次数或holdout任务。

| 清单组成 | 已有证据 | 需要补齐的具体声明 |
|---|---|---|
| cells与连续窗口 | 旧46-cell；一个H25 development来源 | continuous cell集合、split/seed/window/stride及重叠权重 |
| 来源配对 | 具名training/holdout示例、公开边缘 | coupling集合、权重、raw>1处置及每个输入身份 |
| training容量 | 开放前缀planner及证据工具 | 每臂容量求解/搜索合同、全部评估任务与停止规则；不能默认每cell一次episode |
| fixed-policy holdout | 容量策略与逐小时执行已有实现 | 训练证书→容量→策略身份绑定、评估窗口与风险分母 |
| normal任务 | H25一次超时可行解、新完整短流程 | 每项normal输入及信息发布时间、允许复用的证明、有效最优见证 |
| pilot与重试 | 旧H25开发记录 | 新候选预算、重复次数、事前选择规则；未知调用不得免费重试 |
| 整体资源 | workload与resource contract工具 | 每phase wall/commit/archive/scratch、父端准备/回放/归档和静默预算 |
| 科学登记 | 20项实证null、6项选择unregistered | 明确机制值、完整服务/前缀边界、deadline/会计期、删失与权重 |

因此机器报告的`full_experiment_solver_calls`及`full_experiment_wall_seconds`保持null。
不能以46乘一次H25作为完整实验预算，也不能为了得到一个有限总数而虚构窗口、搜索轮数或复用。

## 验证与下一动作

脚本复用现有`summarize_workload`并以独立整数公式比对每行；AST定位现有3600秒限制；
核对连续时间戳、UID集合、旧设计cell算术以及20项实证仍null。
机器报告经两次重算逐字节一致，solver调用为0。来源文件与冻结配置仅只读。

下一项先准备完整科学候选的参数/窗口/评分登记内容，再据其展开逐项任务清单与资源计划。
normal求解候选可独立准备，但正式长运行、完整服务验收口径及协议注册仍需各自具体授权。
此核对不改变最优性阈值、四臂语义或旧冻结结果。
