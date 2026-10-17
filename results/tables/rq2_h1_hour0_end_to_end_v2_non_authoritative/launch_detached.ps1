param(
    [Parameter(Mandatory=$true)][ValidateSet('probe','chain','supervisor')][string]$Role,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-z][a-z0-9_]+$')][string]$Label,
    [Parameter(Mandatory=$true)][string]$ReceiptDirectory
)
$ErrorActionPreference = 'Stop'
$evidenceRoot = $PSScriptRoot
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $evidenceRoot '../../..')).Path
$pythonPath = 'D:\Miniconda3\envs\compute\python.exe'
$receiptRoot = [IO.Path]::GetFullPath($ReceiptDirectory)
if (-not $receiptRoot.StartsWith($evidenceRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Launch receipts must stay inside the non-authoritative evidence root'
}
if (Test-Path -LiteralPath $receiptRoot) { throw 'Fresh receipt directory required' }
[IO.Directory]::CreateDirectory($receiptRoot) | Out-Null
function Save-Receipt($Name, $Body) {
    $path = Join-Path $receiptRoot $Name
    $stream = [IO.File]::Open($path, [IO.FileMode]::CreateNew)
    $writer = [IO.StreamWriter]::new($stream, [Text.UTF8Encoding]::new($false))
    try { $writer.Write(($Body | ConvertTo-Json -Depth 8)); $writer.Flush(); $stream.Flush($true) }
    finally { $writer.Dispose() }
}
$result = $null
try {
    switch ($Role) {
        'probe' { $entry = Join-Path $evidenceRoot 'detached_host_probe.py'; $arguments = @($receiptRoot) }
        'chain' {
            if ($Label -notmatch '^chain_[0-9]+$') { throw 'Chain label required' }
            if ($receiptRoot -ne (Join-Path $evidenceRoot ('host_' + $Label))) { throw 'Canonical synthetic launch receipt required' }
            if ((Test-Path -LiteralPath (Join-Path $evidenceRoot $Label)) -or
                (Test-Path -LiteralPath ('D:\h1_' + $Label + '_non_authoritative'))) { throw 'Fresh chain roots required' }
            $entry = Join-Path $evidenceRoot 'run_validation.py'
            $arguments = @($Label, 'tests/test_h1_hour0_end_to_end_development_v2.py')
        }
        'supervisor' {
            if ($Label -notmatch '^chain_[0-9]+$') { throw 'Chain label required' }
            $chainRoot = Join-Path $evidenceRoot $Label
            $chainHost = Join-Path $evidenceRoot ('host_' + $Label)
            foreach ($required in @("$chainRoot/request.json", "$chainRoot/started.json", "$chainHost/launch_complete.json")) {
                if (-not (Test-Path -LiteralPath $required)) { throw 'Verified started chain required' }
            }
            if (Test-Path -LiteralPath "$chainHost/launch_error.json") { throw 'Unverified chain launch; inspect before continuing' }
            $hostReceipt = Get-Content -Raw -LiteralPath "$chainHost/launch_complete.json" | ConvertFrom-Json
            if ($hostReceipt.status -ne 'LAUNCHED_OBSERVED' -or $hostReceipt.automatic_retry_allowed -ne $false -or
                $hostReceipt.formal_result -ne $false -or @($hostReceipt.PSObject.Properties).Count -ne 5) { throw 'Chain completion schema differs' }
            $expectedReceiptPaths = @('launch_request.json','wmi_result.json','process_observation.json') | ForEach-Object { Join-Path $chainHost $_ }
            if (@($hostReceipt.receipt_pins.PSObject.Properties).Count -ne 3) { throw 'Chain receipt inventory differs' }
            foreach ($property in $hostReceipt.receipt_pins.PSObject.Properties) {
                if ($property.Name -notin $expectedReceiptPaths) { throw 'Foreign chain receipt path' }
                if ((Get-FileHash -LiteralPath $property.Name -Algorithm SHA256).Hash.ToLowerInvariant() -ne $property.Value) { throw 'Chain launch receipt drift' }
            }
            $hostRequest = Get-Content -Raw -LiteralPath "$chainHost/launch_request.json" | ConvertFrom-Json
            $chainEntry = Join-Path $evidenceRoot 'run_validation.py'
            $expectedArgv = @($pythonPath,'-B',$chainEntry,$Label,'tests/test_h1_hour0_end_to_end_development_v2.py')
            if ($hostRequest.role -ne 'chain' -or $hostRequest.label -ne $Label -or $hostRequest.cwd -ne $repoRoot -or
                $hostRequest.formal_result -ne $false -or @($hostRequest.argv).Count -ne $expectedArgv.Count -or
                (Compare-Object -ReferenceObject $expectedArgv -DifferenceObject @($hostRequest.argv) -SyncWindow 0)) { throw 'Chain launch request differs' }
            $expectedPinPaths = @($pythonPath,$chainEntry,$PSCommandPath)
            if (@($hostRequest.pins.PSObject.Properties).Count -ne 3) { throw 'Chain source pin inventory differs' }
            foreach ($property in $hostRequest.pins.PSObject.Properties) {
                if ($property.Name -notin $expectedPinPaths -or
                    (Get-FileHash -LiteralPath $property.Name -Algorithm SHA256).Hash.ToLowerInvariant() -ne $property.Value) { throw 'Chain source pin differs' }
            }
            $identity = Get-Content -Raw -LiteralPath "$chainHost/process_observation.json" | ConvertFrom-Json
            $wmiResult = Get-Content -Raw -LiteralPath "$chainHost/wmi_result.json" | ConvertFrom-Json
            $expectedCommand = ($expectedArgv | ForEach-Object { '"' + $_ + '"' }) -join ' '
            if ($identity.pid -ne $hostReceipt.process_id -or $wmiResult.process_id -ne $identity.pid -or
                $wmiResult.return_value -ne 0 -or $identity.command_line -ne $expectedCommand -or
                $identity.formal_result -ne $false -or $identity.parent_name -ne 'WmiPrvSE.exe' -or
                $identity.parent_pid -isnot [int] -or $identity.parent_pid -le 0) { throw 'Chain launch process correspondence differs' }
            if (-not (Test-Path -LiteralPath "$chainRoot/terminal.json")) {
                $running = Get-CimInstance Win32_Process -Filter "ProcessId = $($identity.pid)"
                if (-not $running -or $running.CommandLine -ne $identity.command_line -or
                    $running.CreationDate.ToUniversalTime().ToString('o') -ne $identity.creation_date) { throw 'Chain wrapper identity lost; no automatic retry' }
                $started = Get-Content -Raw -LiteralPath "$chainRoot/started.json" | ConvertFrom-Json
                $child = Get-CimInstance Win32_Process -Filter "ProcessId = $($started.pid)"
                if (-not $child -or $child.ParentProcessId -ne $identity.pid -or $child.ExecutablePath -ne $pythonPath -or
                    $child.CommandLine -notmatch 'pytest.*test_h1_hour0_end_to_end_development_v2.py') { throw 'Chain pytest identity not observed' }
                Save-Receipt 'chain_observation.json' @{wrapper_pid=$identity.pid; child_pid=$child.ProcessId; child_creation=$child.CreationDate.ToUniversalTime().ToString('o'); command_line=$child.CommandLine; launch_receipt_sha256=(Get-FileHash -LiteralPath "$chainHost/launch_complete.json" -Algorithm SHA256).Hash.ToLowerInvariant()}
            }
            $entry = Join-Path $evidenceRoot 'supervise_completion_v2.py'; $arguments = @($Label)
        }
    }
    $argv = @($pythonPath, '-B', $entry) + $arguments
    if ($argv | Where-Object { $_ -match '["\r\n]' -or $_.EndsWith('\') }) { throw 'Unsupported command argument' }
    $command = ($argv | ForEach-Object { '"' + $_ + '"' }) -join ' '
    $pins = @{}
    foreach ($file in @($pythonPath, $entry, $PSCommandPath)) { $pins[$file] = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() }
    Save-Receipt 'launch_request.json' @{role=$Role; label=$Label; argv=$argv; cwd=$repoRoot; pins=$pins; launcher_pid=$PID; formal_result=$false}
    $startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}
    $result = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$command; CurrentDirectory=$repoRoot; ProcessStartupInformation=$startup}
    Save-Receipt 'wmi_result.json' @{return_value=$result.ReturnValue; process_id=$result.ProcessId; formal_result=$false}
    if ($result.ReturnValue -ne 0) { throw "WMI launch failed: $($result.ReturnValue)" }
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $($result.ProcessId)"
    if (-not $process -or $process.CommandLine -ne $command) { throw 'Launched process identity not observed' }
    $parent = Get-CimInstance Win32_Process -Filter "ProcessId = $($process.ParentProcessId)"
    if (-not $parent -or $parent.Name -ne 'WmiPrvSE.exe' -or $parent.ProcessId -le 0) { throw 'Independent WMI host parent not observed' }
    Save-Receipt 'process_observation.json' @{pid=$process.ProcessId; parent_pid=$process.ParentProcessId; parent_name=$parent.Name; creation_date=$process.CreationDate.ToUniversalTime().ToString('o'); command_line=$process.CommandLine; formal_result=$false}
    foreach ($file in $pins.Keys) { if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() -ne $pins[$file]) { throw 'Launch source drift' } }
    $receiptPins = @{}
    $receiptNames = @('launch_request.json','wmi_result.json','process_observation.json')
    if (Test-Path -LiteralPath (Join-Path $receiptRoot 'chain_observation.json')) { $receiptNames += 'chain_observation.json' }
    foreach ($name in $receiptNames) {
        $path = Join-Path $receiptRoot $name
        $receiptPins[$path] = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    Save-Receipt 'launch_complete.json' @{status='LAUNCHED_OBSERVED'; process_id=$result.ProcessId; receipt_pins=$receiptPins; automatic_retry_allowed=$false; formal_result=$false}
    Write-Output "Launched $Role PID $($result.ProcessId); receipt $receiptRoot"
} catch {
    $mayRun = $null -ne $result -and $result.ReturnValue -eq 0
    $status = if ($mayRun) {'LAUNCHED_UNVERIFIED'} else {'NOT_CONFIRMED_LAUNCHED'}
    Save-Receipt 'launch_error.json' @{error=$_.ToString(); status=$status; process_may_be_running=$mayRun; process_id=$result.ProcessId; automatic_retry_allowed=$false; formal_result=$false}
    throw
}
