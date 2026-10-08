# Selector一次性父控制器

状态：DRAFT_NONAUTHORITATIVE。实现`scale_selector_controller.py`，复用已有Windows Job owner与本地NTFS lease，不改变旧normal控制器、selector或worker。

控制器身份绑定完整请求、Job预算、host声明、父目录资源身份、环境、Python executable与实现依赖。任务目录必须为新建non-authoritative root；scratch创建后再绑定实际目录资源身份。控制器先持久写入请求、完整调用预算intent，再创建suspended child，写PID/creation-time并回读检查后release。只有owned wait确认整个Job静默后才读取worker回执和selector数据库。

回执检查实现/request pin和权限字段；持有store lease检查数据库、完整请求、结果identity、reported status及inspection的一致性。父记录exclusive create、fsync、文件身份和exact canonical readback；已有任务目录不能覆盖或重执行。完成记录仍为returned_unverified，不是数值认证、可执行恢复或正式许可。中途失败保留已有记录；intent后缺失结果不得推断零调用。

当前范围是单selector调用的持久启动顺序与Job监督。没有整体controller wall/峰内存/目录大小验收或硬磁盘quota，没有独立数值回放，没有真实规模normal来源认证，未接episode四臂角色与跨小时事务。任务Job budget由调用者显式提供，不能将声明通过当作完整资源已验证。测试仅采用合成数据和pytest临时目录。

## 验证记录

初轮5项通过（9.80秒），加入完整归档关联后与worker组合23项通过（28.55秒）。独立pre-seal发现早期lease失败异常覆盖、完成记录后的可失败检查及receipt字段inventory缺口；修复后controller最终11项通过（25.10秒），包含真实reference/actual Job、写启动记录失败、intent漂移、错结果/extra/missing receipt、最早lease失败和terminal后不再验证。git diff --check通过。

最后全链检查位于result写入前；result独占写入及exact回读之后不再做结果验证，仅释放任务锁。落盘result本身仍不是正式seal，锁释放/I/O异常或外部读取时须保留不确定性，不提供自动恢复执行。旧episode及hourly transaction要求旧selector结果类型，后继需独立数值回放及事务适配，不能直接将returned_unverified推进业务游标。
