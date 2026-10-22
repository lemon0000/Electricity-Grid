# Constructor inspect结果复用：DRAFT设计与验收矩阵

2026-10-21，DRAFT_NONAUTHORITATIVE。此设计未实现，不接入owner，不创建production config、outer、lease、receipt或运行权限。

原HistoricalSnapshot构造器在验证declaration、anchor/journal、源与network后动态调用self.inspect，并检查returned state为完整accepted prefix；batch caller随后再次reader.inspect，重复同一prefix科学重放。最窄后继只私有保存构造器这次返回的state和已有captured frames，由caller取回，原后置views/inventory/_observe_prefix/_observe_sources/implementation观察照常执行。临时state在return/失败/close时释放；不得输出live capability或保留跨operation结果。

后继需新historical schema及implementation identity、source batch schema/entry和validator。旧cross-hour owner v2要求每Reader两次traversal，应继续拒绝后继metric=1；接线必须独立versioned owner并先完成以下证据。双独立Reader必须保留，materialize前后仍从N/Job/clock重新重放；不把第二Reader替换为SHA摘要。

| 不变量/失效类别 | 必须验证的窗口与oracle |
|---|---|
| 科学输出 | 同一保存prefix原完整函数与后继对照：packet/normal decision/projection/scientific量及精确Fraction相同；只允许明确列出的validation schema/provenance字段不同 |
| constructor state/capture | 只接受构造器唯一完整inspect所得state和0..H-1顺序capture，禁止二次dispatch、伪造state、缺hour、重复/乱序、错误type或额外公开cache入口 |
| obligation与外部pins | constructor返回后到后置bookend，改binding/header、selected terminal链、job link、budget、family/ordinal/manifest/enrollment；不得接受来自另一root/prefix的state |
| parent拓扑/identity | 同窗口对anchor/journal metadata/payload/commit、child reference、inode/path替换、删除/添加/alias、partial suffix与锁身份逐类fault；原支持的条件suffix语义须一致 |
| Job/worker/stage | 同窗口改request、launch/child/consumed/result/observation、worker binding/terminal、stage raw/commit/metadata及文件身份；不得只比较最终projection相同 |
| clock/process | 改clock binding/intent/job/terminal、前驱时序、PID/create-time/thread/clock或parent anchor correspondence；后置错误须保留 |
| source/registry | config、source支持文件/目录清单及内容、当前source字段和registry逐小时prefix必须fresh；缺必要源仍unresolved，不补未来或跨split行 |
| runtime/依赖 | constructor返回窗口内改函数alias/code/default/closure、module/class/global/descriptor、dataclass字段、可变常量、package metadata/version与同字节非确定性；需给出完整适用闭包或拒绝后继准入，不能只核源文件SHA |
| 资源/拒绝 | 维持原H<=192、retained bytes、stage上限和输入拒绝；测真实总wall/RSS/storage，不将原重复工作删除当作已节约wall |
| 失败/清理 | constructor/后置观察/Reader close/lease close失败均清空私有capture并尝试全部关闭；保留primary异常与附加cleanup错误，不伪报clean success |
| 整合 | 新batch仍独立双Reader，materialize窗口N/Job/source/registry/runtime漂移拒绝；paired前fresh及append后完整replay继续执行；真实terminal/close/reopen与整链预算另验 |

先用小型明确stand-in覆盖操作与失效控制流，再用已保存3h原件作完整数值oracle和两个独立Reader的净总路径对照；不新开N或selector。每个新诊断需预先固定调用数、预算、资源和停止条件。当前只有原路径一次profile；尚未形成后继性能或完整异常等价证据。

如果无法证明删除第二traversal仍保留适用依赖检测，停止依赖该证明的接线并按agent第7节升级处理；记录候选不能替代问题修复。不因局部节省预设放宽阈值/guard。任意反射和未观察ABA仍保持未证明，不能转换为生产安全、资源准入或科学认证。
