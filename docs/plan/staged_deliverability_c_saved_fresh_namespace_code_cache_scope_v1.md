# namespace CodeType指纹：单次遍历缓存等价与成本

2026-10-27，DRAFT_NONAUTHORITATIVE，起点fbebf0b518ce7803acc3f94cdb235ea313a7f751。root唯一writer、独立只读PRE_SEAL；所有已执行源码/结果冻结。本scope仅新增namespace v3、等价/回归tests与有界controller，不改Source49、ENTRY、core/parent/probe/BS，也不启动cold。

目标是消除同一次freeze内部重复的immutable CodeType token化。code_cache按id强持原code与IN_PROGRESS/token，命中必须is同一对象；首次递归先强持，异常不留成功token，cycle拒绝。visit(CodeType)直接取token；seen/nodes/objects顺序和全图/身份/可变字段复核均不动。不跨freeze、entry或线程复用，不把结构相等的不同CodeType合并。

冻结v2 reader为独立oracle。对共享nested code、稍后独立visit、相等clone、filename/firstlineno变化、unsupported constant、每次cache重置及实际完整ENTRY模块，核image逐值相等、objects等长且逐项is、错误类型/消息等价。通过unit专用_graph_roots SHA wrapper计数，不把wrapper注入production default、manifest或authority；另核所有nested reader code的LOAD_GLOBAL/STORE_GLOBAL/DELETE_GLOBAL为0。实际ENTRY旧/新各三次顺序交替测量只作本地成本观察；不把wall差异称为整链提速。保留26项原namespace逻辑回归并把其validator适配到已冻结runtime probe v3的真实validator；Source49不变。

完整路径：登记源码/pins/精确unit节点 → 单一bounded unit child（原26项+新cache用例）→ 独立PRE_SEAL → metadata保存。无native self query、solver、模型、adapter import、P1/hold/capture/replay、OwnedChild/Job/F。实际ENTRY只顶层exec用于逻辑namespace，不运行main/CLI。

static≤8s、unittest≤12s、总≤20s；登记≤2s、unit≤12s、metadata保存≤3s，余static3s。并发1、unit最多1个capture child，无自动repair或扩帽；任一失败保存raw/exit/费用并停止。新root results/tables/staged_rts24_saved_fresh_namespace_code_cache_v1_non_authoritative ≤12文件/2MiB，stdout65536/stderr16384沿冻结capture；RAM仅观察。若真实ENTRY计数无收益或任何图/异常/零global不等价，不能接冷路径，另做成本调查。

前驱累计static188.98202860001697、pytest366.48897970000326、unittest44.763771399997495、合计600.2347797000177s及20条意外不接受记录续记。旧static120/总540/import8MiB超帽保持。新独立帽不称全累计落旧帽；编辑/审查/Git、Python初始启动及最终exit序列化不计capture，不是完整wall，无模拟小时推进。

这只验证缓存等价和局部成本。单次1秒栈不足证明其会解决原9秒超时；下一cold必须重新整体路径/预算准入。E/U/独立TCB/native/完整runtime/P1/role/permit/F/科学/资源/正式/run authority均false。保留39项并行dirty，发布仅本scope与四导航前置段。
