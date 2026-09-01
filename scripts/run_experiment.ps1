<#
.SYNOPSIS
    跨机科研实验闭环的固定入口脚本（Windows 执行器调用）。

.DESCRIPTION
    本脚本是 docs/plan/科研实验闭环流程.md 第 3.4/3.5/5/7/8 节约定的“固定实验入口”。
    它在执行器创建的独立 worktree 内运行，读取 configs/experiment.yaml 决定要跑什么，
    并按第 7 节规范产出 status.json / metrics.json / summary.md / run-info.txt /
    manifest.json（失败或超时也生成，只描述运行状态，绝不推断科研结论）。

    当前默认配置 kind=pytest-smoke，只运行本仓库自带的确定性单元测试子集，用于验证
    闭环管道是否连通；它不需要 Gurobi 或原始数据，也绝不触发 repair-010 等正式求解链。

    另支持 kind=rq2-formal-batch：调用 experiments/run_rq2_formal_batch.py 跑 RQ2
    正式规模批处理（L5 λ 前沿 + H2 生成式场景外 + 3-source 消融，及其冻结种子/机制邻域
    敏感性）。该批处理是已过 R3 审查的合成/trace 派生机制入口，使用开源 HiGHS、单次
    求解、秒级到分钟级，不需要 Gurobi、不触碰冻结的 B3/B4/B5 基线、绝不启动 repair-010
    多阶段长求解，且 security_certified 恒为 false。批产物统一写入 $runDir 下由执行器
    上传，其性质仍是机制证据，绝不构成工程/合同/经验-VMA 认证。

    kind=rq2-public-pilot 是 RQ2 v6 的受限执行机 successor，只按固定顺序调用
    verify -> preflight -> pilot -> package-pilot。该入口不接受任意 command，也不能触达
    activate/grid/pairwise/identification。完整工件缺失时即使子进程退出 0 也失败。

    若要跑正式多阶段（Gurobi、--stage、repair-010）实验，请改用 docs/plan/
    科研实验闭环流程.md 第 3.5 节“两类实验入口”所述的专用 runner，不要把它塞进本脚本。

.NOTES
    由 D:\research\agent\run-pending-experiment.ps1 通过环境变量注入运行上下文：
      RUN_ID, RUN_TAG, RUN_COMMIT, RUN_DIR, RUN_ARTIFACT_DIR。
    可选：PYTHON_EXE（缺省回退到 PATH 上的 python）、SMOKE_TIMEOUT_SECONDS（缺省 3600）。
    rq2-public-pilot 必须另行显式提供绝对普通文件 RQ2_EXECUTOR_PYTHON_EXE，并使用
    RQ2_PILOT_TIMEOUT_SECONDS（缺省 21600）；它不会回退到 PYTHON_EXE 或 smoke timeout。
    脚本假设当前工作目录为 worktree 根。
#>

$ErrorActionPreference = "Stop"

# UTF-8 无 BOM，供所有工件写入使用（PS5.1 的 -Encoding UTF8 会带 BOM，破坏严格 JSON 解析）。
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Write-Utf8Lines {
    param([string]$Path, [string[]]$Lines)
    [System.IO.File]::WriteAllLines($Path, [string[]]$Lines, $script:Utf8NoBom)
}

function Write-Utf8Text {
    param([string]$Path, [string]$Text)
    [System.IO.File]::WriteAllText($Path, $Text, $script:Utf8NoBom)
}

# finally 中每个写入步骤各自兜底，确保 manifest 与 exit 不会因单点异常被跳过。
function Try-Step { param([scriptblock]$Body) try { & $Body } catch {} }

# 把可能为相对路径的目录归一为绝对路径，统一 .NET File API 与 PS cmdlet 的基准目录。
function Resolve-Dir {
    param([string]$Path)
    if ([System.IO.Path]::IsPathRooted($Path)) {
        return [System.IO.Path]::GetFullPath($Path)
    }
    return [System.IO.Path]::GetFullPath((Join-Path (Get-Location).Path $Path))
}

function Assert-OrdinaryFile {
    param([string]$Path, [string]$Label)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "$Label 缺失：$Path"
    }
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "$Label 不是非reparse普通文件：$Path"
    }
    return $item
}

# PS5.1-compatible timeout containment. A timeout is not considered contained until
# Kill (when needed), bounded WaitForExit, Refresh and HasExited jointly prove exit.
function Stop-ChildProcessAndConfirm {
    param(
        [System.Diagnostics.Process]$Process,
        [int]$GraceMilliseconds = 5000
    )
    $confirmed = $false
    $details = New-Object System.Collections.Generic.List[string]
    try {
        $Process.Refresh()
        if ($Process.HasExited) {
            $confirmed = $true
            $details.Add("already_exited")
        }
        else {
            try {
                $Process.Kill()
                $details.Add("kill_requested")
            }
            catch {
                $details.Add("kill_error=$($_.Exception.Message)")
            }
        }
    }
    catch {
        $details.Add("pre_kill_refresh_error=$($_.Exception.Message)")
    }
    if (-not $confirmed) {
        try {
            $waited = $Process.WaitForExit($GraceMilliseconds)
            if ($waited) {
                # Drain redirected stdout/stderr before the process handle is released.
                $Process.WaitForExit()
            }
            $Process.Refresh()
            $confirmed = [bool]$Process.HasExited
            $details.Add("bounded_wait=$waited")
            $details.Add("has_exited=$confirmed")
        }
        catch {
            $details.Add("exit_confirmation_error=$($_.Exception.Message)")
            $confirmed = $false
        }
    }
    return [PSCustomObject]@{
        Confirmed = [bool]$confirmed
        Detail = ($details -join ";")
    }
}

# 冻结 executor 的 package receipt 使用 str(Path.relative_to(...))，所以 Windows
# 会输出反斜杠。只在验证 receipt 字段时接受原生分隔符，再严格归一为 POSIX 相对路径；
# 绝对、drive-relative、空段和 traversal 一律在路径比较前拒绝。
function ConvertTo-CanonicalRepositoryRelativePath {
    param([string]$Path, [string]$Field)
    if ([string]::IsNullOrWhiteSpace($Path)) {
        throw "package-pilot receipt 的 $Field 路径为空"
    }
    if ([IO.Path]::IsPathRooted($Path) -or $Path -match '^[A-Za-z]:' -or
        $Path -match '^[\\/]{2}') {
        throw "package-pilot receipt 的 $Field 路径不是安全的仓库相对路径：$Path"
    }
    $canonical = $Path.Replace("\", "/")
    if ($canonical.StartsWith("/") -or $canonical.EndsWith("/") -or
        $canonical.Contains("//") -or $canonical -match '(^|/)\.\.?(/|$)') {
        throw "package-pilot receipt 的 $Field 路径不是安全的仓库相对路径：$Path"
    }
    return $canonical
}

function Assert-JsonHashPackage {
    param([string]$Root)
    $manifestPath = Join-Path $Root "SHA256SUMS.json"
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw "缺少结果包 manifest：$manifestPath"
    }
    $manifest = [IO.File]::ReadAllText($manifestPath, [Text.Encoding]::UTF8) | ConvertFrom-Json
    $properties = @($manifest.PSObject.Properties)
    if ($properties.Count -eq 0) { throw "结果包 manifest 为空：$manifestPath" }
    foreach ($property in $properties) {
        $name = [string]$property.Name
        if ([System.IO.Path]::IsPathRooted($name) -or $name -match '(^|[\\/])\.\.([\\/]|$)') {
            throw "结果包 manifest 含不安全路径：$name"
        }
        $member = Join-Path $Root $name
        if (-not (Test-Path -LiteralPath $member -PathType Leaf)) {
            throw "结果包成员缺失：$member"
        }
        $observed = (Get-FileHash -Algorithm SHA256 -LiteralPath $member).Hash.ToLowerInvariant()
        if ($observed -ne ([string]$property.Value).ToLowerInvariant()) {
            throw "结果包成员哈希漂移：$member"
        }
    }
}

function Assert-ExecutorBundleV2 {
    $outerPath = Resolve-Dir "configs/rq2_public_executor_bundle_v2.OUTER.SHA256SUMS.json"
    Assert-OrdinaryFile $outerPath "Windows successor outer authority" | Out-Null
    $outer = [IO.File]::ReadAllText($outerPath, [Text.Encoding]::UTF8) | ConvertFrom-Json
    if ($outer.schema -ne "rq2_public_executor_outer_manifest_v2") {
        throw "Windows successor outer authority schema 漂移"
    }
    $outerProperties = @($outer.files.PSObject.Properties)
    $bundleName = "configs/rq2_public_executor_bundle_v2.SHA256SUMS.json"
    if ($outerProperties.Count -ne 1 -or [string]$outerProperties[0].Name -cne $bundleName) {
        throw "Windows successor outer authority inventory 必须只绑定 v2 bundle"
    }
    $manifestPath = Resolve-Dir $bundleName
    Assert-OrdinaryFile $manifestPath "Windows successor bundle" | Out-Null
    $observedBundleHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash.ToLowerInvariant()
    if ($observedBundleHash -ne ([string]$outerProperties[0].Value).ToLowerInvariant()) {
        throw "Windows successor outer authority 未能验证 v2 bundle"
    }
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw "缺少 Windows successor bundle：$manifestPath"
    }
    $manifest = [IO.File]::ReadAllText($manifestPath, [Text.Encoding]::UTF8) | ConvertFrom-Json
    if ($manifest.schema -ne "rq2_public_executor_bundle_manifest_v2") {
        throw "Windows successor bundle schema 漂移"
    }
    $properties = @($manifest.files.PSObject.Properties)
    if ($properties.Count -eq 0) { throw "Windows successor bundle inventory 为空" }
    foreach ($property in $properties) {
        $name = [string]$property.Name
        if ($name.Contains("\") -or [IO.Path]::IsPathRooted($name) -or
            $name -match '(^|/)\.\.?(/|$)') {
            throw "Windows successor bundle 路径不是 canonical POSIX relative path：$name"
        }
        $member = Resolve-Dir $name
        if (-not (Test-Path -LiteralPath $member -PathType Leaf)) {
            throw "Windows successor bundle 成员缺失：$name"
        }
        $observed = (Get-FileHash -Algorithm SHA256 -LiteralPath $member).Hash.ToLowerInvariant()
        if ($observed -ne ([string]$property.Value).ToLowerInvariant()) {
            throw "Windows successor bundle 成员哈希漂移：$name"
        }
    }
}

# --- 运行上下文（由执行器注入，缺失时给出可复现的本地缺省）---------------------
$runId       = if ($env:RUN_ID)  { $env:RUN_ID }  else { "local-smoke" }
$runTag      = if ($env:RUN_TAG) { $env:RUN_TAG } else { $runId }
$runDir      = if ($env:RUN_DIR) { $env:RUN_DIR } else { "runs/$runId" }
$artifactDir = if ($env:RUN_ARTIFACT_DIR) { $env:RUN_ARTIFACT_DIR } else { "artifacts/$runId" }
$pythonExe   = if ($env:PYTHON_EXE) { $env:PYTHON_EXE } else { "python" }
$configPath  = "configs/experiment.yaml"

# 两类 timeout 独立解析。poller 只注入 SMOKE_TIMEOUT_SECONDS=7200 时，RQ2 pilot
# 仍使用自己的 21600 秒缺省，避免把 smoke 的硬终止口径静默带入 solver pilot。
$smokeTimeoutSeconds = 3600
if ($env:SMOKE_TIMEOUT_SECONDS) {
    $parsed = 0
    if ([int]::TryParse($env:SMOKE_TIMEOUT_SECONDS, [ref]$parsed) -and $parsed -gt 0) {
        $smokeTimeoutSeconds = $parsed
    }
}
$rq2PilotTimeoutSeconds = 21600
$rq2PilotTimeoutInvalid = $false
if ($env:RQ2_PILOT_TIMEOUT_SECONDS) {
    $parsed = 0
    if ([int]::TryParse($env:RQ2_PILOT_TIMEOUT_SECONDS, [ref]$parsed) -and $parsed -ge 21600) {
        $rq2PilotTimeoutSeconds = $parsed
    }
    else {
        $rq2PilotTimeoutInvalid = $true
    }
}
$timeoutSeconds = $smokeTimeoutSeconds

# 目录归一为绝对路径（在任何写入前完成）。
$runDir = Resolve-Dir $runDir
$artifactDir = Resolve-Dir $artifactDir

# 运行状态变量（在任何抛错前初始化，保证 finally 与 exit 始终可用）。
$runStatus = "failed"
$exitCode = 1
$failureMessage = $null
$command = $null
$runCommit = $null
$configSha256 = $null
$kind = $null
$passed = $null
$failed = $null
$skipped = $null
$pilotArtifactComplete = $null
$pilotGurobiEligible = $null
$pilotCommands = @()
$pilotCompletedCommands = @()
$pilotPackageReceipt = $null
$pilotTerminationConfirmed = $null
$pilotTerminationDetail = $null
$pilotTimeoutStage = $null
$startedAt = Get-Date -Format o

try {
    # --- 上下文准备（纳入保护：即便这里抛错，finally 仍会尽力产出工件）---------
    if ($env:RUN_COMMIT) {
        $runCommit = $env:RUN_COMMIT
    }
    else {
        # 裸原生命令在 $ErrorActionPreference=Stop 下，stderr 输出会被提升为终止错误，
        # 故显式吞掉 stderr 再校验结果。
        $runCommit = (& git rev-parse HEAD 2>$null | Select-Object -First 1)
        if (-not $runCommit) { throw "无法解析 RUN_COMMIT，且 git rev-parse HEAD 失败" }
        $runCommit = $runCommit.Trim()
    }

    New-Item -ItemType Directory -Force $runDir | Out-Null
    New-Item -ItemType Directory -Force $artifactDir | Out-Null

    if (-not (Test-Path $configPath)) {
        throw "缺少固定入口配置：$configPath"
    }
    $configSha256 = (Get-FileHash -Algorithm SHA256 $configPath).Hash.ToLowerInvariant()

    $configText = Get-Content $configPath -Raw
    $kindMatch = [regex]::Match($configText, '(?m)^\s*kind:\s*([A-Za-z0-9_\-]+)\s*$')
    if (-not $kindMatch.Success) {
        throw "configs/experiment.yaml 未提供合法的 kind 字段"
    }
    $kind = $kindMatch.Groups[1].Value

    # 记录初始 run-info（此后 finally 会追加 finished/status）。
    Write-Utf8Lines (Join-Path $runDir "run-info.txt") @(
        "run_id=$runId"
        "source_tag=$runTag"
        "source_commit=$runCommit"
        "config_sha256=$configSha256"
        "experiment_kind=$kind"
        "started_at=$startedAt"
        "status=running"
    )

    # kind 决定进程参数；两个分支都是 fail-closed 白名单，未知 kind 直接抛错。
    $procArgs = $null
    $timeoutLabel = $null
    if ($kind -eq "pytest-smoke") {
        # 提取 pytest_smoke.selection 与 extra_args（列表末项允许无换行）。
        $selection = @()
        $selBlock = [regex]::Match($configText, '(?ms)^\s*selection:\s*\r?\n((?:[ \t]*-[ \t]*\S+[ \t]*\r?(?:\n|$))+)')
        if ($selBlock.Success) {
            foreach ($line in ($selBlock.Groups[1].Value -split "`n")) {
                $m = [regex]::Match($line, '^\s*-\s*(\S+)\s*$')
                if ($m.Success) { $selection += $m.Groups[1].Value }
            }
        }
        if ($selection.Count -eq 0) {
            throw "configs/experiment.yaml 未提供 pytest_smoke.selection"
        }

        $extraArgs = @()
        $extraBlock = [regex]::Match($configText, '(?ms)^\s*extra_args:\s*\r?\n((?:[ \t]*-[ \t]*\S+[ \t]*\r?(?:\n|$))+)')
        if ($extraBlock.Success) {
            foreach ($line in ($extraBlock.Groups[1].Value -split "`n")) {
                $m = [regex]::Match($line, '^\s*-\s*(\S+)\s*$')
                if ($m.Success) { $extraArgs += $m.Groups[1].Value }
            }
        }

        $procArgs = @("-m", "pytest") + $selection + $extraArgs
        $timeoutLabel = "pytest 冒烟"
    }
    elseif ($kind -eq "rq2-formal-batch") {
        # RQ2 正式规模批处理：只允许固定驱动模块，批清单路径可在配置中声明（缺省
        # configs/rq2_formal_batch.yaml），并把全部产物重定向到 $runDir 下由执行器上传。
        # 这里绝不接受任意 runner/模块名，故通用入口无法借此触达被阻塞的 repair-010 链。
        $batchConfig = "configs/rq2_formal_batch.yaml"
        $bcMatch = [regex]::Match($configText, '(?m)^\s*batch_config:\s*(\S+)\s*$')
        if ($bcMatch.Success) { $batchConfig = $bcMatch.Groups[1].Value }
        if (-not (Test-Path $batchConfig)) {
            throw "kind=rq2-formal-batch 指定的批清单不存在：$batchConfig"
        }
        $procArgs = @(
            "-m", "experiments.run_rq2_formal_batch",
            "--config", $batchConfig,
            "--output-root", $runDir
        )
        $timeoutLabel = "RQ2 正式规模批处理"
    }
    elseif ($kind -eq "rq2-public-pilot") {
        # 该 kind 只允许 frozen v1 executor 的四个 pilot 命令。解释器必须由执行机
        # 显式提供；不能静默复用 compute/PATH，从而保持 rq2-executor 环境身份。
        Assert-ExecutorBundleV2
        if (-not $env:RQ2_EXECUTOR_PYTHON_EXE) {
            throw "kind=rq2-public-pilot 必须显式设置 RQ2_EXECUTOR_PYTHON_EXE"
        }
        if ($rq2PilotTimeoutInvalid) {
            throw "RQ2_PILOT_TIMEOUT_SECONDS 必须是大于等于 21600 的正整数"
        }
        if (-not [System.IO.Path]::IsPathRooted($env:RQ2_EXECUTOR_PYTHON_EXE)) {
            throw "RQ2_EXECUTOR_PYTHON_EXE 必须是绝对路径"
        }
        $rq2PythonItem = Get-Item -LiteralPath $env:RQ2_EXECUTOR_PYTHON_EXE -ErrorAction Stop
        if ($rq2PythonItem.PSIsContainer -or ($rq2PythonItem.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw "RQ2_EXECUTOR_PYTHON_EXE 必须是非符号链接的普通文件"
        }
        $pythonExe = $rq2PythonItem.FullName
        $pilotCommands = @("verify", "preflight", "pilot", "package-pilot")
        $timeoutSeconds = $rq2PilotTimeoutSeconds
        $timeoutLabel = "RQ2 v6 cross-solver pilot"
    }
    else {
        throw "本固定入口只支持 kind=pytest-smoke、kind=rq2-formal-batch 或 kind=rq2-public-pilot；kind=$kind 不在白名单。"
    }

    if ($kind -eq "rq2-public-pilot") {
        $command = ($pilotCommands | ForEach-Object { "$pythonExe scripts/rq2_public_executor.py $_" }) -join " -> "
    }
    else {
        $command = "$pythonExe " + ($procArgs -join " ")
    }
    $logPath = Join-Path $runDir "experiment.log"
    $stderrLog = "$logPath.err"

    # 用 Start-Process 支持超时，并把 stdout/stderr 分别重定向到文件。
    # Start-Process 规避了 $ErrorActionPreference=Stop 下原生命令 stderr 触发
    # NativeCommandError 的陷阱。
    if ($kind -eq "rq2-public-pilot") {
        $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
        $stageLogRoot = Join-Path $runDir "rq2-public-pilot-logs"
        New-Item -ItemType Directory -Force $stageLogRoot | Out-Null
        foreach ($pilotCommand in $pilotCommands) {
            $stageLog = Join-Path $stageLogRoot "$pilotCommand.stdout.json"
            $stageErrorLog = Join-Path $stageLogRoot "$pilotCommand.stderr.log"
            $stageArgs = @("scripts/rq2_public_executor.py", $pilotCommand)
            $proc = Start-Process -FilePath $pythonExe -ArgumentList $stageArgs `
                -NoNewWindow -PassThru `
                -RedirectStandardOutput $stageLog -RedirectStandardError $stageErrorLog
            $remainingMilliseconds = [int64](($timeoutSeconds * 1000) - $stopwatch.ElapsedMilliseconds)
            if ($remainingMilliseconds -le 0 -or -not $proc.WaitForExit([int]$remainingMilliseconds)) {
                $pilotTimeoutStage = $pilotCommand
                $termination = Stop-ChildProcessAndConfirm -Process $proc -GraceMilliseconds 5000
                $pilotTerminationConfirmed = [bool]$termination.Confirmed
                $pilotTerminationDetail = [string]$termination.Detail
                if ($pilotTerminationConfirmed) {
                    $runStatus = "timeout"
                    $exitCode = 124
                    $failureMessage = "$timeoutLabel 在 $pilotCommand 阶段超过独立总时限 $timeoutSeconds 秒；child退出已确认。这是执行超时，不是数学不可行证据。"
                }
                else {
                    $runStatus = "failed"
                    $exitCode = 125
                    $failureMessage = "$timeoutLabel 在 $pilotCommand 阶段超时且 termination_unconfirmed；不能证明 child 已退出，禁止验证或发布成功工件。detail=$pilotTerminationDetail"
                }
                break
            }
            # 带 stdout/stderr 重定向时，PS5.1/.NET 需要无参 WaitForExit 完成异步
            # pipe drain，随后 ExitCode 才是稳定值。
            $proc.WaitForExit()
            $proc.Refresh()
            $stageExitCode = [int]$proc.ExitCode
            if ($stageExitCode -ne 0) {
                $runStatus = "failed"
                $exitCode = $stageExitCode
                $failureMessage = "$timeoutLabel 的 $pilotCommand 阶段失败，退出码：$stageExitCode"
                break
            }
            $pilotCompletedCommands += $pilotCommand
            if ($pilotCommand -eq "package-pilot") {
                $pilotPackageReceipt = Get-Content -LiteralPath $stageLog -Raw | ConvertFrom-Json
            }
        }
        if (-not $failureMessage -and $pilotCompletedCommands.Count -eq $pilotCommands.Count) {
            $runStatus = "success"
            $exitCode = 0
        }
    }
    else {
        $proc = Start-Process -FilePath $pythonExe -ArgumentList $procArgs `
            -NoNewWindow -PassThru `
            -RedirectStandardOutput $logPath -RedirectStandardError $stderrLog

        if (-not $proc.WaitForExit($timeoutSeconds * 1000)) {
            try { $proc.Kill() } catch {}
            $runStatus = "timeout"
            $exitCode = 124
            $failureMessage = "$timeoutLabel 超时（>$timeoutSeconds 秒），已终止。"
        }
        else {
            $proc.WaitForExit()
            $proc.Refresh()
            $procExit = [int]$proc.ExitCode
            if ($procExit -eq 0) {
                $runStatus = "success"
                $exitCode = 0
            }
            else {
                $runStatus = "failed"
                $exitCode = $procExit
                $failureMessage = "$timeoutLabel 失败，退出码：$procExit"
            }
        }
    }
}
catch {
    $runStatus = "failed"
    $exitCode = 1
    $failureMessage = $_ | Out-String
}
finally {
    $finishedAt = Get-Date -Format o

    # 合并 stderr 到主日志尾部（诊断用，放 finally 并判空，绝不影响已判定的状态）。
    Try-Step {
        $logPath = Join-Path $runDir "experiment.log"
        $stderrLog = "$logPath.err"
        if (Test-Path $stderrLog) {
            $errText = Get-Content $stderrLog -Raw -ErrorAction SilentlyContinue
            if ($errText) {
                Add-Content -Path $logPath -Value $errText
            }
            Remove-Item $stderrLog -Force -ErrorAction SilentlyContinue
        }
    }

    # 从 pytest 日志抽取通过/失败计数（仅冒烟入口有意义；用 $script: 回写脚本作用域，
    # 避免 & 子作用域丢值）。
    Try-Step {
        if ($kind -eq "pytest-smoke") {
            $logPath = Join-Path $runDir "experiment.log"
            if (Test-Path $logPath) {
                $tail = (Get-Content $logPath -Raw)
                $pm = [regex]::Match($tail, '(\d+)\s+passed');  if ($pm.Success) { $script:passed  = [int]$pm.Groups[1].Value }
                $fm = [regex]::Match($tail, '(\d+)\s+failed');  if ($fm.Success) { $script:failed  = [int]$fm.Groups[1].Value }
                $sm = [regex]::Match($tail, '(\d+)\s+skipped'); if ($sm.Success) { $script:skipped = [int]$sm.Groups[1].Value }
            }
        }
    }

    # 批处理：定位 run_rq2_formal_batch.py 写在 $runDir 下的 batch_manifest.json，
    # 抽取 batch_gate_passed / job_count 供 metrics 与 summary 使用（只读，不改判状态）。
    $batchManifestPath = $null
    $batchGatePassed = $null
    $batchJobCount = $null
    Try-Step {
        if ($kind -eq "rq2-formal-batch") {
            $found = Get-ChildItem -Path $runDir -Recurse -Filter "batch_manifest.json" -File -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($found) {
                $script:batchManifestPath = $found.FullName
                $bm = Get-Content $found.FullName -Raw | ConvertFrom-Json
                $script:batchGatePassed = [bool]$bm.batch_gate_passed
                $script:batchJobCount = [int]$bm.job_count
            }
        }
    }

    # 正式批次的完整结果树是必需工件。成功进程若缺 aggregate manifest，或复制
    # effective config / summary / arms / leaves / nested manifest 失败，必须在状态
    # 文件落盘前转为 failed，不能只留下成功状态与一个不完整上传目录。
    if ($kind -eq "rq2-formal-batch") {
        if (-not $batchManifestPath) {
            if ($runStatus -eq "success") {
                $runStatus = "failed"
                $exitCode = 1
                $failureMessage = "RQ2 批处理成功退出但缺少 batch_manifest.json"
            }
        }
        else {
            try {
                Copy-Item $batchManifestPath (Join-Path $artifactDir "batch_manifest.json") -Force
                $batchRoot = Split-Path -Parent $batchManifestPath
                $batchArtifactRoot = Join-Path $artifactDir "batch_results"
                if (Test-Path $batchArtifactRoot) {
                    throw "批处理上传目标已存在，拒绝覆盖：$batchArtifactRoot"
                }
                Copy-Item $batchRoot $batchArtifactRoot -Recurse
            }
            catch {
                $runStatus = "failed"
                $exitCode = 1
                $failureMessage = "RQ2 批处理工件复制失败：$($_ | Out-String)"
            }
        }
    }

    # RQ2 pilot 的发布包必须在状态文件落盘前独立复核并递归复制。四个命令即使
    # 全部退出 0，只要任一结果 manifest、transfer manifest/archive 或复制后哈希
    # 不完整，运行仍 fail closed。pilot eligibility 仅记录，不自动激活正式阶段。
    if ($kind -eq "rq2-public-pilot") {
        $pilotArtifactRoot = Join-Path $artifactDir "rq2_public_pilot"
        $pilotLogSource = Join-Path $runDir "rq2-public-pilot-logs"
        try {
            if ($runStatus -ne "success" -or
                $pilotCompletedCommands.Count -ne $pilotCommands.Count -or
                $pilotTerminationConfirmed -eq $false) {
                throw "RQ2 pilot 四阶段未完整成功或 child 退出未获证明；只允许保留诊断日志"
            }
            $requiredStageLogs = @()
            foreach ($requiredCommand in $pilotCommands) {
                foreach ($suffix in @("stdout.json", "stderr.log")) {
                    $sourceLog = Join-Path $pilotLogSource "$requiredCommand.$suffix"
                    Assert-OrdinaryFile $sourceLog "RQ2 pilot stage log" | Out-Null
                    $requiredStageLogs += $sourceLog
                }
            }
            $preflightRoot = Resolve-Dir "results/tables/rq2_public_executor_preflight_v1"
            $pilotRoot = Resolve-Dir "results/tables/rq2_public_solver_pilot_v1"
            $transferRoot = Resolve-Dir "results/transfer"
            $transferArchive = Join-Path $transferRoot "rq2_public_successor_v1_pilot.tar.gz"
            $transferManifestPath = Join-Path $transferRoot "rq2_public_successor_v1_pilot.json"

            Assert-JsonHashPackage $preflightRoot
            Assert-JsonHashPackage $pilotRoot
            if (-not $pilotPackageReceipt) { throw "缺少 package-pilot JSON receipt" }
            if ($pilotPackageReceipt.scope -ne "pilot" -or
                [bool]$pilotPackageReceipt.formal_result_claimed -or
                [bool]$pilotPackageReceipt.security_certified) {
                throw "package-pilot receipt 的范围或声明字段不合法"
            }
            $receiptArchive = ConvertTo-CanonicalRepositoryRelativePath `
                -Path ([string]$pilotPackageReceipt.archive) -Field "archive"
            $receiptManifest = ConvertTo-CanonicalRepositoryRelativePath `
                -Path ([string]$pilotPackageReceipt.manifest) -Field "manifest"
            if ($receiptArchive -cne "results/transfer/rq2_public_successor_v1_pilot.tar.gz" -or
                $receiptManifest -cne "results/transfer/rq2_public_successor_v1_pilot.json") {
                throw "package-pilot receipt 指向未注册路径"
            }
            $transferBindings = @(
                [PSCustomObject]@{ Path = $transferArchive; Expected = [string]$pilotPackageReceipt.archive_sha256 }
                [PSCustomObject]@{ Path = $transferManifestPath; Expected = [string]$pilotPackageReceipt.manifest_sha256 }
            )
            foreach ($bound in $transferBindings) {
                if (-not (Test-Path -LiteralPath $bound.Path -PathType Leaf)) {
                    throw "transfer 工件缺失：$($bound.Path)"
                }
                $observed = (Get-FileHash -Algorithm SHA256 -LiteralPath $bound.Path).Hash.ToLowerInvariant()
                if ($observed -ne $bound.Expected.ToLowerInvariant()) {
                    throw "transfer 工件哈希漂移：$($bound.Path)"
                }
            }

            $transferManifest = Get-Content -LiteralPath $transferManifestPath -Raw | ConvertFrom-Json
            if ($transferManifest.schema -ne "rq2_public_executor_return_package_v1" -or
                $transferManifest.scope -ne "pilot" -or
                [bool]$transferManifest.formal_result_claimed -or
                [bool]$transferManifest.security_certified) {
                throw "transfer manifest 的 schema、范围或声明字段不合法"
            }
            $transferEntries = @($transferManifest.files.PSObject.Properties)
            $expectedTransferPaths = @()
            foreach ($sourceRoot in @($preflightRoot, $pilotRoot)) {
                foreach ($sourceFile in Get-ChildItem -LiteralPath $sourceRoot -File) {
                    $relative = $sourceFile.FullName.Substring((Get-Location).Path.Length)
                    $expectedTransferPaths += $relative.TrimStart([char[]]@(92, 47)).Replace("\", "/")
                }
            }
            $observedTransferPaths = @($transferEntries | ForEach-Object { [string]$_.Name })
            if (@(Compare-Object $expectedTransferPaths $observedTransferPaths).Count -ne 0) {
                throw "transfer manifest 未精确覆盖 preflight 与 pilot 文件"
            }
            foreach ($entry in $transferEntries) {
                $name = [string]$entry.Name
                if ([IO.Path]::IsPathRooted($name) -or $name -match '(^|[\\/])\.\.([\\/]|$)') {
                    throw "transfer manifest 含不安全路径：$name"
                }
                $member = Resolve-Dir $name
                $observed = (Get-FileHash -Algorithm SHA256 -LiteralPath $member).Hash.ToLowerInvariant()
                if ($observed -ne ([string]$entry.Value).ToLowerInvariant()) {
                    throw "transfer manifest 成员哈希漂移：$name"
                }
            }

            if (Test-Path -LiteralPath $pilotArtifactRoot) {
                throw "pilot 上传目标已存在，拒绝覆盖：$pilotArtifactRoot"
            }
            New-Item -ItemType Directory $pilotArtifactRoot | Out-Null
            Copy-Item -LiteralPath $preflightRoot -Destination (Join-Path $pilotArtifactRoot "preflight") -Recurse
            Copy-Item -LiteralPath $pilotRoot -Destination (Join-Path $pilotArtifactRoot "pilot") -Recurse
            New-Item -ItemType Directory (Join-Path $pilotArtifactRoot "transfer") | Out-Null
            Copy-Item -LiteralPath $transferArchive -Destination (Join-Path $pilotArtifactRoot "transfer")
            Copy-Item -LiteralPath $transferManifestPath -Destination (Join-Path $pilotArtifactRoot "transfer")
            Copy-Item -LiteralPath $pilotLogSource -Destination (Join-Path $pilotArtifactRoot "logs") -Recurse
            Assert-JsonHashPackage (Join-Path $pilotArtifactRoot "preflight")
            Assert-JsonHashPackage (Join-Path $pilotArtifactRoot "pilot")
            foreach ($name in @("rq2_public_successor_v1_pilot.tar.gz", "rq2_public_successor_v1_pilot.json")) {
                $source = Join-Path $transferRoot $name
                $copy = Join-Path (Join-Path $pilotArtifactRoot "transfer") $name
                if ((Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash -ne
                    (Get-FileHash -Algorithm SHA256 -LiteralPath $copy).Hash) {
                    throw "pilot transfer 复制后哈希漂移：$name"
                }
            }
            foreach ($sourceLog in $requiredStageLogs) {
                $copiedLog = Join-Path (Join-Path $pilotArtifactRoot "logs") ([IO.Path]::GetFileName($sourceLog))
                Assert-OrdinaryFile $copiedLog "复制后的 RQ2 pilot stage log" | Out-Null
                if ((Get-FileHash -Algorithm SHA256 -LiteralPath $sourceLog).Hash -ne
                    (Get-FileHash -Algorithm SHA256 -LiteralPath $copiedLog).Hash) {
                    throw "RQ2 pilot stage log 复制后哈希漂移：$sourceLog"
                }
            }
            $pilotSummary = Get-Content -LiteralPath (Join-Path $pilotRoot "summary.json") -Raw | ConvertFrom-Json
            $pilotGurobiEligible = [bool]$pilotSummary.gurobi_eligible_for_formal_successor
            $pilotArtifactComplete = $true
        }
        catch {
            $pilotArtifactComplete = $false
            $artifactFailure = "RQ2 pilot 工件不完整：$($_ | Out-String)"
            if ($runStatus -eq "success") {
                $runStatus = "failed"
                $exitCode = 1
                $failureMessage = $artifactFailure
            }
            elseif ($failureMessage) {
                $failureMessage = "$failureMessage`n$artifactFailure"
            }
            else {
                $failureMessage = $artifactFailure
            }
            # 失败时仍尽力保留逐阶段日志；它们只是诊断，不会把 artifact_complete 置真。
            Try-Step {
                if (-not (Test-Path -LiteralPath $pilotArtifactRoot)) {
                    New-Item -ItemType Directory $pilotArtifactRoot | Out-Null
                }
                if (Test-Path -LiteralPath $pilotLogSource) {
                    Copy-Item -LiteralPath $pilotLogSource -Destination (Join-Path $pilotArtifactRoot "logs") -Recurse -Force
                }
            }
        }
    }

    Try-Step {
        if ($failureMessage) {
            Write-Utf8Lines (Join-Path $runDir "error.txt") @($failureMessage)
        }
    }

    Try-Step {
        [System.IO.File]::AppendAllText(
            (Join-Path $runDir "run-info.txt"),
            "finished_at=$finishedAt`nstatus=$runStatus`ncommand=$command`n",
            $script:Utf8NoBom
        )
    }
    Try-Step { Write-Utf8Lines (Join-Path $runDir "status.txt") @($runStatus) }

    # status.json —— 第 7 节：status 只描述进程/工件状态。
    Try-Step {
        $json = [PSCustomObject]@{
            run_id          = $runId
            source_tag      = $runTag
            source_commit   = $runCommit
            status          = $runStatus
            start_time      = $startedAt
            end_time        = $finishedAt
            experiment_kind = $kind
            error           = $failureMessage
        } | ConvertTo-Json -Depth 5
        Write-Utf8Text (Join-Path $runDir "status.json") $json
    }

    # metrics.json —— evidence_status 按 kind 如实标注，绝不把正式批处理误标为冒烟。
    # 冒烟记录测试计数；批处理记录 batch_gate_passed / job_count（只读，不改判状态）。
    # 两分支的 evidence_status 都明确其为“机制/管道证据”，绝不构成工程/安全/科研认证。
    Try-Step {
        if ($kind -eq "rq2-formal-batch") {
            $json = [PSCustomObject]@{
                evidence_status   = "synthetic_or_trace_derived_mechanism_batch_not_engineering_or_contract_evidence"
                batch_gate_passed = $batchGatePassed
                job_count         = $batchJobCount
                security_certified = $false
            } | ConvertTo-Json -Depth 5
        }
        elseif ($kind -eq "rq2-public-pilot") {
            $json = [PSCustomObject]@{
                evidence_status = "nonformal_cross_solver_pilot_execution_receipt_only"
                command_sequence = $pilotCommands
                completed_command_sequence = $pilotCompletedCommands
                artifact_complete = $pilotArtifactComplete
                gurobi_eligible_for_formal_successor = $pilotGurobiEligible
                timeout_seconds = $timeoutSeconds
                timeout_environment_variable = "RQ2_PILOT_TIMEOUT_SECONDS"
                timeout_is_infeasibility_evidence = $false
                timeout_stage = $pilotTimeoutStage
                termination_confirmed = $pilotTerminationConfirmed
                termination_detail = $pilotTerminationDetail
                formal_execution_ready = $false
                security_certified = $false
            } | ConvertTo-Json -Depth 5
        }
        else {
            $json = [PSCustomObject]@{
                evidence_status = "pipeline_plumbing_smoke_only"
                tests_passed    = $passed
                tests_failed    = $failed
                tests_skipped   = $skipped
            } | ConvertTo-Json -Depth 5
        }
        Write-Utf8Text (Join-Path $runDir "metrics.json") $json
    }

    # summary.md —— 人类可读运行摘要，明确其非科研结论性质；按 kind 呈现关键指标。
    Try-Step {
        $lines = @(
            "# Run $runId"
            ""
            "- source_tag: $runTag"
            "- source_commit: $runCommit"
            "- experiment_kind: $kind"
            "- status: $runStatus"
        )
        if ($kind -eq "rq2-formal-batch") {
            $lines += "- batch_gate_passed: $batchGatePassed"
            $lines += "- job_count: $batchJobCount"
            $lines += "- security_certified: false"
            $lines += ""
            $lines += "此摘要仅描述 RQ2 正式规模批处理的运行与门状态。逐 job 的科学发现"
            $lines += "（H1 高估量 / H2 场景外欠交付 / H2 跨来源稳健 / H3 成本-尾部风险单调权衡"
            $lines += "与 Pareto 前沿 + 各 job 有效配置 SHA-256）见随附 batch_manifest.json。本批为"
            $lines += "合成/trace 派生机制证据，绝不构成工程/合同/安全/经验-VMA/CFE 认证。"
        }
        elseif ($kind -eq "rq2-public-pilot") {
            $lines += "- command_sequence: verify -> preflight -> pilot -> package-pilot"
            $lines += "- completed_command_sequence: $($pilotCompletedCommands -join ' -> ')"
            $lines += "- artifact_complete: $pilotArtifactComplete"
            $lines += "- gurobi_eligible_for_formal_successor: $pilotGurobiEligible"
            $lines += "- timeout_seconds: $timeoutSeconds"
            $lines += "- timeout_stage: $pilotTimeoutStage"
            $lines += "- termination_confirmed: $pilotTerminationConfirmed"
            $lines += "- formal_execution_ready: false"
            $lines += "- security_certified: false"
            $lines += ""
            $lines += "此摘要只描述非正式 cross-solver pilot 的执行与工件完整性。超时不是数学不可行证据；"
            $lines += "该入口不能激活或运行 grid、pairwise、identification。"
        }
        else {
            $lines += "- tests: passed=$passed failed=$failed skipped=$skipped"
            $lines += ""
            $lines += "此摘要仅描述跨机闭环管道的冒烟运行状态，不构成模型可行性、安全认证或科研结论。"
        }
        Write-Utf8Lines (Join-Path $runDir "summary.md") $lines
    }

    # 复制上传工件到 artifactDir。批处理除 aggregate manifest 外，必须递归复制
    # 每个 job 的 effective config、summary、arms/leaves 和 SHA manifest；否则只能
    # 看到汇总结论，无法复核 leaf-level H2 证据。
    Try-Step {
        $publish = @("run-info.txt", "status.txt", "status.json", "metrics.json", "summary.md", "error.txt")
        foreach ($name in $publish) {
            $src = Join-Path $runDir $name
            if (Test-Path $src) { Copy-Item $src (Join-Path $artifactDir $name) -Force }
        }
    }

    # manifest.json —— 第 7 节：递归列出除自身外每个上传文件的相对路径、字节数
    # 与 SHA-256。嵌套的 batch_results 也必须完整覆盖。
    Try-Step {
        $manifestEntries = @()
        Get-ChildItem $artifactDir -File -Recurse | Where-Object { $_.FullName -ne (Join-Path $artifactDir "manifest.json") } | ForEach-Object {
            $relativePath = $_.FullName.Substring($artifactDir.Length).TrimStart("\", "/").Replace("\", "/")
            $manifestEntries += [PSCustomObject]@{
                path       = $relativePath
                size_bytes = $_.Length
                sha256     = (Get-FileHash -Algorithm SHA256 $_.FullName).Hash.ToLowerInvariant()
            }
        }
        $json = [PSCustomObject]@{
            run_id        = $runId
            source_commit = $runCommit
            files         = $manifestEntries
        } | ConvertTo-Json -Depth 5
        Write-Utf8Text (Join-Path $artifactDir "manifest.json") $json
    }
}

exit $exitCode
