param([Parameter(Mandatory=$true)][string]$Label)
$ErrorActionPreference = 'Stop'
if ($Label -notmatch '^chain_[0-9]+$') { throw 'exact local chain label required' }
$attempt = Join-Path $PSScriptRoot $Label
$started = Get-Content -LiteralPath (Join-Path $attempt 'started.json') -Raw | ConvertFrom-Json
$candidate = Get-CimInstance Win32_Process -Filter "ProcessId = $($started.pid)"
if (-not $candidate -or $candidate.CommandLine -notlike "*h1_${Label}_non_authoritative*") {
    throw 'test process is absent or has a different command'
}
$process = Get-Process -Id $started.pid
$row = [ordered]@{
    observed_utc = [DateTime]::UtcNow.ToString('o')
    pid = $process.Id
    process_start_utc = $process.StartTime.ToUniversalTime().ToString('o')
    cpu_seconds = $process.CPU
    working_set_bytes = $process.WorkingSet64
    peak_working_set_bytes = $process.PeakWorkingSet64
    private_bytes = $process.PrivateMemorySize64
    direct_child_pids = @(Get-CimInstance Win32_Process -Filter "ParentProcessId = $($started.pid)" | ForEach-Object { $_.ProcessId })
    scope = 'observed_synthetic_pytest_parent_only'
    formal_result = $false
    resource_admission = $false
}
$line = $row | ConvertTo-Json -Compress
[IO.File]::AppendAllText((Join-Path $attempt 'process_observations.jsonl'), $line + "`n", [Text.UTF8Encoding]::new($false))
$line
