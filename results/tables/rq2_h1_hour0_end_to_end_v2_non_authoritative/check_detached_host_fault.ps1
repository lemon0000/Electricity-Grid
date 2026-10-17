param([Parameter(Mandatory=$true)][ValidatePattern('^synthetic_host_fault_[0-9]+$')][string]$Label,
      [ValidateSet('missing_process','wrong_parent')][string]$Fault='missing_process')
$ErrorActionPreference='Stop'
$outputRoot=Join-Path $PSScriptRoot $Label
if (Test-Path -LiteralPath $outputRoot) { throw 'Fresh synthetic fault path required' }
function New-CimInstance { return @{} }
function Invoke-CimMethod { return [pscustomobject]@{ReturnValue=0;ProcessId=424242} }
function Get-CimInstance {
    param($Filter)
    if ($Fault -eq 'missing_process') { return $null }
    if ($Filter -eq 'ProcessId = 424242') {
        $request=Get-Content -Raw -LiteralPath (Join-Path $outputRoot 'launch_request.json') | ConvertFrom-Json
        return [pscustomobject]@{ProcessId=424242;ParentProcessId=424243;CreationDate=[DateTime]::UtcNow;CommandLine=(($request.argv | ForEach-Object {'"'+$_+'"'}) -join ' ')}
    }
    return [pscustomobject]@{ProcessId=424243;Name='powershell.exe'}
}
$failed=$false
try {
    & (Join-Path $PSScriptRoot 'launch_detached.ps1') -Role probe -Label $Label -ReceiptDirectory $outputRoot
} catch { $failed=$true }
$errorReceipt=Get-Content -Raw -LiteralPath (Join-Path $outputRoot 'launch_error.json') | ConvertFrom-Json
if (-not $failed -or $errorReceipt.status -ne 'LAUNCHED_UNVERIFIED' -or
    $errorReceipt.process_may_be_running -ne $true -or $errorReceipt.automatic_retry_allowed -ne $false -or
    (Test-Path -LiteralPath (Join-Path $outputRoot 'launch_complete.json'))) { throw 'Synthetic fault behavior differs' }
$pins=@{}
foreach ($file in @($PSCommandPath,(Join-Path $PSScriptRoot 'launch_detached.ps1')) + @(Get-ChildItem -LiteralPath $outputRoot -File | ForEach-Object {$_.FullName})) {
    $pins[$file]=(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
}
@{mocked=$true; actual_process_created=$false; fake_pid=424242; fault=$Fault; mocks=@('New-CimInstance','Invoke-CimMethod','Get-CimInstance'); command=@('powershell.exe','-NoProfile','-File',$PSCommandPath,'-Label',$Label,'-Fault',$Fault); files_sha256=$pins; expected_failure_observed=$true; formal_result=$false} |
    ConvertTo-Json -Depth 8 | Out-File -LiteralPath (Join-Path $outputRoot 'mocked_fault_evidence.json') -Encoding utf8
Write-Output 'Expected mocked launch failure verified; no process created'
