# C/F：真实 ENTRY namespace 的连续持有切片

2026-10-27，DRAFT_NONAUTHORITATIVE，起点 `2b1f95b6e70c47cf40e4b70119a59d65c646ff82`。接续 pre-ENTRY v2 交接。root 唯一 writer、只读 PRE_SEAL；不 seal、不发行角色/运行能力。所有前驱61文件、Source49、科学代码、旧失败和预算保留。

完整后续链仍为 L → 真实 ENTRY namespace → versioned B_S 审计/owner handoff → path4 到 path6 / M-D finder 变化 → adapter → transitive live runtime → 角色/issuer/quiet/科学链。本切片实现前两段的连接，剩余段不以此替代或宣告完成。当前 L 固定 path/meta_path，跨 adapter import 必然失效；不得修改其 control image 或直接改 resource.owner 来伪造移交。新 B_S 与 self resource handoff 必须是后续显式接口。

新 bootstrap v3 仅重定位独立 manifest/profile 根并绑定新 helper pin，保留 v2 self/raw/transfer/cleanup 语义。先独立 startup discovery、create-only profile admission，验证 child 再创建并转交真实 LocalPreEntryInputs。读取其已持 ENTRY raw，在不同于 bootstrap globals 的 exact ModuleType 中真实 exec 全文；固定非main名称 experiments.staged_rts24_saved_fresh_adoption_v1、absolute __file__、package=experiments、spec/loader=None与原builtins，exec前注册 sys.modules。这是固定名称下的held-byte执行namespace，不是正常importlib加载或direct-main证明；reference先在同一canonical名下初始化并冻结图，移除自己的校准alias后再create-only注册actual。reference对象随owner强持，不再占用任何alias；私有REFERENCE_NAME保留为冲突检测项。bootstrap 的 main/argv/path/env 不改。ENTRY 自身21个 dataclass、contextmanager/classmethod/property、16次 __init_subclass__ 和 unit seal 内省属于真实初始化，不称仅compile；禁止任何 ENTRY CLI/角色/科学函数调用。

同一已编译 unit 先在reference、再在actual两个对象中执行，生成条件性标准库/编译器下的 namespace 表示 oracle；不是外部 E 或独立角色来源。reference alias只移除自己注册的对象。oracle冻结为不可变有界图，覆盖源函数与dataclass生成方法、decorator wrapper、closure/cell、类/bases/descriptor、常量容器/alias及 dataclass Field/Params；外部stdlib/builtin/module叶按实际对象身份保留并明确仍属条件性TCB。未知类型/深度/节点超帽拒绝，不用repr或任意getter取指纹。

实际 namespace 必须与固定raw生成的图一致，再强持真实所有节点并在每次entry核图及逐对象身份；不能仅对两个可同时改写的当前namespace作相互比较。slots与普通setattr关闭，expected/control不可普通重写；持有helper/class method/code/default/closure和关键module属性，consumer使用原held verifier与cleanup code。object.__setattr__和任意RAM/ABA仍不在保证内。NamespaceLease为LocalPreEntryInputs的同进程组合持有者，native resource.owner仍是原inputs；不声称native owner已转交给runtime。close即使namespace被改也须调用原inputs清理；primary/secondary令namespace保持UNRESOLVED、缓存原failure、重复close重抛，不能用HANDLE已关洗成成功。每次注册前即时核held sys.modules目标为空；foreign/额外alias保留，清理只删除held字典中本次注册且仍指向原module的canonical alias，保留私有冲突项。

执行DAG：登记原/新helper/前驱/Source49/TCB → 普通逻辑测试 → 唯一≤5s startup discovery（无self lease）→ profile admission → 四个独立cold（normal、namespace global替换、alias替换、注册后初始化前注入）→ saved metadata fresh核验。每例仅一个child，最多两次ENTRY namespace exec；无adapter import/P1/OwnedChild/Job/native solver/实际F。audit从release前后一直按原规则保持，ENTRY exec在审计非busy上下文；process/write/project import继续拒绝。namespace图≤50000节点、深度≤256；helper raw≤128KiB、Source49≤2MiB，command≤30000 UTF16。RAM只观测不宣称硬帽。

独立新scope static≤40s、unittest≤20s、总≤60s；登记共享≤2s，unit主组≤10s、唯一显式repair≤8s，discovery≤5s、admission≤2s、四cold合计≤12s（每例≤3s）、saved≤6s。unit的23项逻辑检查包含多次双namespace初始化与完整图遍历，首次登记前将主组预留定为10s；本scope尚无执行和费用，20s总帽不变。编辑/审查/Git/最终exit序列化及Python初始启动不在capture计费内，不冒充整链wall time。前驱累计static161.3614287、pytest366.4889797、unittest2.4766955、总530.3271039与14不接受记录原样续记；新scope不重置旧50/30/80、原120/420/540及资源超帽。

新结果根 `results/tables/staged_rts24_saved_fresh_entry_namespace_v1_non_authoritative`≤32文件/4MiB；helper原bytes打包snapshot，四例receipt用逐次canonical prefix绑定的JSONL，每例plan和所有exit/create-only，raw stdout/stderr无损保存、上限131072/16384。任何失败保留、后继需显式版本登记；不覆盖已执行控制器或 accepted 前驱。普通unit可在独立PRE_SEAL迭代中运行，用于确认图、defaults和清理语义；cold前须闭合执行前must-fix。所有 E/U、Python/native TCB认证、完整runtime/P1、角色/permit/F/科学/资源/正式/运行权限保持false。
