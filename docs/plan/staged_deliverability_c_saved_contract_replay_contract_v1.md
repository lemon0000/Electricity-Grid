# C：四个保存 F/X 代表行的独立重放合同

2026-10-24，DRAFT_NONAUTHORITATIVE。接续[前缀交接](continuation_handoff_20261024_saved_prefix_replay.md)，实现[科学采用DAG](staged_deliverability_c_scientific_adoption_dag_v1.md)的局部D。保留原七输入、B1–B3/P1、guard/outer、单点C和前缀B的全部已发布字节。

## 固定范围与独立输入

仅P1的on_time/early/full_temporal、hours1/2、points22..31、四个代表row。每小时一个normal_contract_C economic root，再各取fixture中编号最小的支路和机组故障：fault_firm_F primal与fault_raw_need child LP。原P1分别为branch_0/generator_0。选择规则在重放前固定；十个查询均来自原core.hour_requests及当小时独立重建的normal证据，不能从当前CAS query或保存audit反推预期。

调用方先持有独立fixture SHA、start pins/registration SHA、十个schedule slot、十个point完整文件pins、contract_rows.json完整字节pin、outer quiet及26个选定来源pins。真实保存回归以原P1外部683文件清单和固定postcheck stdout SHA为锚；不将同一输出目录的自报hash当独立来源。

## 读取DAG、书挡与失败

完整outer quiet→26 source/21 loaded src路径和字节→caller/fixture/预算校验→保存row文件的pin/identity→原compiler每小时一次→normal原C重建→同normal parent绑定的firm/raw原C重建→独立firm audit_point及原audit_legal_x→完整row canonical字节逐项比较→末次point/row/root/source/fixture/caller书挡。

每次C前保存pins/files/directories；返回前逐点比较完整identity（文件dev/ino/size/mtime、目录dev/ino）及pins。points_root及其祖先identity保持；row文件读前核实际size等于held pin且不超8MiB，沿原bounded_file_bytes以size+1/fstat/目录书挡读取，单独保存文件/全部祖先identity和原始字节并再次读取核对。同字节文件或row父目录替换也须拒绝。调用方所有期望首尾相同。

十个point及row文件合计8192文件/64MiB内，单文件沿8MiB帽；网络沿24/33/38帽，selected N-1最多71个且索引通过原binder验证。只读取选定十点和row文件；不读actual prefix、journal、fresh或未来点，不写CAS/manifest/lease/gate，不调用native/solver/子进程。numeric未决不能供应预期成功row，立即报错并停止，不补点、不推不可行、不返回部分采用。slot、类型、来源、row或书挡矛盾均报错，不重试。

## 原合同语义

normal检查完整C=F+X；firm为同一故障独立F点；raw保持未截断的min_curtailment反事实。firm/raw的parent query、point、economic证据均来自该小时normal，不能用actual或另一个小时的根替代。firm的C/primal审计失败立即报错，不能供应成功row；另一次独立firm audit也须通过。legal-X的false判据和minimum_established=false照原输出对照，不强制改成true；raw KKT仍由原C独立导入核对。成功的真实保存回归须获得十点原typed SHA及四行完全相同的audit/残差，包括signed zero。解析负谓词例保持firm primal-valid，仅用故意非最优、未声明KKT的raw stand-in测试原legal-X false；原numeric import对invalid firm的拒绝另测，不放宽原C。

`minimum_established=false`、`independent_firm_point_still_required=true`、`temporal_backing=not_established`沿原audit返回。四行一致只是声明静态DC/固定数值容差下的代表行证据一致性，不建立完整139/F-X、时间预算、工程安全或最小容量。全局scientific_evidence_adopted、expected_query_provenance_independently_verified、full_fx_contract_verified、independent_139_verified、journal_replayed、resource/formal一律false。

## 调用量、优化与普通验证

完整成功图固定10点（2 economic KKT/4 primal/4 child LP KKT），原C带来compile20、snapshot/import各10；D另调用4次独立firm audit_point和4次audit_legal_x（后者内部仍调用audit_point及原parent审计）。原hour_requests固定2次，并保留全selected query生成与校验；每小时normal只重建一次，按两个故障合法共用，不重复求根；不跨点缓存CAS或省略原parent/KKT审计。

每次C source86读，十点860；前缀层26+21=47，双书挡94，合计954次source内容读取，caller首次source_pins的26读另计。每点C为6M+16内容读，D前后两次inventory各M+8，故8M+32；成功typed pack继承C的5次/点，共50次，D不额外pack。row文件首尾另读2次，目录/metadata、core.digest及canonical编码另计。成本是逻辑调用量，不是OS调用、峰值内存/存储或全outer wall测量。尚不能把两小时/四行外推到全十小时/138行。

普通测试先跑手写解析点的编排/拒绝/书挡反例，再只读这一个10点真实保存包；固定每组90s硬超时，不自动重试，失败工件与source pins/日志保留。C stand-in的解析编排测试不冒充raw/KKT导入；真实10点回归须调用原C并统计上述调用量。禁止真实solver/backend、Popen、journal writer/reopen和publication，随后跑原audit/numeric/child及单点相关回归、独立只读PRE_SEAL、787旧路径/三导航旧正文/683 P1文件、hash/diff/process检查。无official verdict/receipt/seal及新增运行权限。

后续E可信journal重开、F fresh/最终父采用、昂贵失败/十小时增长/full wall/RAM/storage、65s父端余量及C整体预算继续OPEN。
