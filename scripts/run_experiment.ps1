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

    若要跑正式多阶段（Gurobi、--stage、repair-010）实验，请改用 docs/plan/
    科研实验闭环流程.md 第 3.5 节“两类实验入口”所述的专用 runner，不要把它塞进本脚本。

.NOTES
    由 D:\research\agent\run-pending-experiment.ps1 通过环境变量注入运行上下文：
      RUN_ID, RUN_TAG, RUN_COMMIT, RUN_DIR, RUN_ARTIFACT_DIR。
    可选：PYTHON_EXE（缺省回退到 PATH 上的 python）、SMOKE_TIMEOUT_SECONDS（缺省 3600）。
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
    return [System.IO.Path]::GetFullPath((Join-Path (Get-Location).Path $Path))
}

# --- 运行上下文（由执行器注入，缺失时给出可复现的本地缺省）---------------------
$runId       = if ($env:RUN_ID)  { $env:RUN_ID }  else { "local-smoke" }
$runTag      = if ($env:RUN_TAG) { $env:RUN_TAG } else { $runId }
$runDir      = if ($env:RUN_DIR) { $env:RUN_DIR } else { "runs/$runId" }
$artifactDir = if ($env:RUN_ARTIFACT_DIR) { $env:RUN_ARTIFACT_DIR } else { "artifacts/$runId" }
$pythonExe   = if ($env:PYTHON_EXE) { $env:PYTHON_EXE } else { "python" }
$configPath  = "configs/experiment.yaml"

# SMOKE_TIMEOUT_SECONDS 数字校验（放在最前，非法值回退而非崩溃）。
$timeoutSeconds = 3600
if ($env:SMOKE_TIMEOUT_SECONDS) {
    $parsed = 0
    if ([int]::TryParse($env:SMOKE_TIMEOUT_SECONDS, [ref]$parsed) -and $parsed -gt 0) {
        $timeoutSeconds = $parsed
    }
}

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
    else {
        throw "本固定入口只支持 kind=pytest-smoke 或 kind=rq2-formal-batch；kind=$kind 属其它正式实验，需使用专用 runner（见流程文档第 3.5 节）。"
    }

    $command = "$pythonExe " + ($procArgs -join " ")
    $logPath = Join-Path $runDir "experiment.log"
    $stderrLog = "$logPath.err"

    # 用 Start-Process 支持超时，并把 stdout/stderr 分别重定向到文件。
    # Start-Process 规避了 $ErrorActionPreference=Stop 下原生命令 stderr 触发
    # NativeCommandError 的陷阱。
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
        $procExit = $proc.ExitCode
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
        else {
            $lines += "- tests: passed=$passed failed=$failed skipped=$skipped"
            $lines += ""
            $lines += "此摘要仅描述跨机闭环管道的冒烟运行状态，不构成模型可行性、安全认证或科研结论。"
        }
        Write-Utf8Lines (Join-Path $runDir "summary.md") $lines
    }

    # 复制上传工件到 artifactDir。批处理另把 batch_manifest.json（科学发现与门状态的
    # 权威载体）纳入上传集，否则公司 Mac 收不到本轮结果，只剩状态壳。
    Try-Step {
        $publish = @("run-info.txt", "status.txt", "status.json", "metrics.json", "summary.md", "error.txt")
        foreach ($name in $publish) {
            $src = Join-Path $runDir $name
            if (Test-Path $src) { Copy-Item $src (Join-Path $artifactDir $name) -Force }
        }
        if ($kind -eq "rq2-formal-batch" -and $batchManifestPath -and (Test-Path $batchManifestPath)) {
            Copy-Item $batchManifestPath (Join-Path $artifactDir "batch_manifest.json") -Force
        }
    }

    # manifest.json —— 第 7 节：列出除自身外每个上传文件的相对路径、字节数与 SHA-256。
    Try-Step {
        $manifestEntries = @()
        Get-ChildItem $artifactDir -File | Where-Object { $_.Name -ne "manifest.json" } | ForEach-Object {
            $manifestEntries += [PSCustomObject]@{
                path       = $_.Name
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
