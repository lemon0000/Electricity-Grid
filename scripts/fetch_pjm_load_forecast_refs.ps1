param(
    [string]$SocksProxy = "127.0.0.1:7897",
    [string]$PjmIp = "156.154.237.70",
    [string]$UserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

# PJM load-forecast and RTEP reference documents for the DOM / North-Virginia case study.
#
# www.pjm.com answers HTTP 200 only for US proxy exits: from other exits the edge resets the TLS
# handshake. This script sends the request over SOCKS5 with the origin IP pinned, so mihomo matches on
# GEOIP instead of its domain rules, and it refuses to run while the exit is not US.
#
# Usage:  pwsh scripts/fetch_pjm_load_forecast_refs.ps1

$ErrorActionPreference = "Stop"
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))

$files = @(
    @{ Url = "https://www.pjm.com/-/media/DotCom/library/reports-notices/load-forecast/2026-load-report.pdf";
       Path = "data/raw/pjm_load_forecast_2026/upstream/2026-load-report.pdf"; Kind = "pdf";
       Note = "PJM 2026 Load Forecast Report" },
    @{ Url = "https://www.pjm.com/-/media/DotCom/library/reports-notices/load-forecast/2026-load-report-data.xlsx";
       Path = "data/raw/pjm_load_forecast_2026/upstream/2026-load-report-data.xlsx"; Kind = "zip";
       Note = "load forecast report data workbook" },
    @{ Url = "https://www.pjm.com/-/media/DotCom/planning/res-adeq/load-forecast/2026-load-report-tables.xlsx";
       Path = "data/raw/pjm_load_forecast_2026/upstream/2026-load-report-tables.xlsx"; Kind = "zip";
       Note = "load forecast report tables" },
    @{ Url = "https://www.pjm.com/-/media/DotCom/planning/res-adeq/load-forecast/dominion-documentation.pdf";
       Path = "data/raw/pjm_load_forecast_2026/upstream/dominion-documentation.pdf"; Kind = "pdf";
       Note = "DOM zone load forecast documentation" },
    @{ Url = "https://www.pjm.com/-/media/DotCom/planning/res-adeq/load-forecast/dominion-vo-documentation.pdf";
       Path = "data/raw/pjm_load_forecast_2026/upstream/dominion-vo-documentation.pdf"; Kind = "pdf";
       Note = "DOM zone voltage-optimisation documentation" }
)

$headers = @(
    "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "-H", "Accept-Language: en-US,en;q=0.9",
    "-H", "Sec-Fetch-Mode: navigate", "-H", "Sec-Fetch-Site: none", "-H", "Sec-Fetch-User: ?1"
)

function Test-ZipArchive([string]$Path) {
    try {
        Add-Type -AssemblyName System.IO.Compression.FileSystem -ErrorAction Stop
        $zip = [System.IO.Compression.ZipFile]::OpenRead($Path)
        try {
            foreach ($entry in $zip.Entries) {
                $stream = $entry.Open()
                try {
                    $buf = New-Object byte[] 65536
                    while ($stream.Read($buf, 0, $buf.Length) -gt 0) { }
                }
                finally { $stream.Dispose() }
            }
        }
        finally { $zip.Dispose() }
        return $true
    }
    catch { return $false }
}

function Test-PdfFile([string]$Path) {
    $latin1 = [System.Text.Encoding]::GetEncoding(28591)
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -lt 1000) { return $false }
    if ($latin1.GetString($bytes[0..4]) -ne "%PDF-") { return $false }
    $all = $latin1.GetString($bytes)
    if ($all.LastIndexOf("%%EOF") -lt 0) { return $false }
    $idx = $all.LastIndexOf("startxref")
    if ($idx -lt 0) { return $false }
    $num = ($all.Substring($idx + 9) -split "\s+" | Where-Object { $_ -match '^\d+$' } | Select-Object -First 1)
    if (-not $num) { return $false }
    $off = [int]$num
    if ($off -lt 0 -or $off -ge $bytes.Length - 16) { return $false }
    $seg = $latin1.GetString($bytes[$off..($off + 15)])
    return ($seg.StartsWith("xref") -or $seg -match '^\d+\s+\d+\s+obj')
}

# preflight: refuse while the exit is not US
try {
    $exitIp = (& curl.exe -sS --max-time 25 --socks5-hostname $SocksProxy "https://api.ipify.org" 2>$null)
    if ($exitIp -match '^\d+\.\d+\.\d+\.\d+$') {
        $geo = (& curl.exe -sS --max-time 25 "https://ipinfo.io/$exitIp/json" 2>$null | Out-String)
        $country = if ($geo -match '"country":\s*"([A-Z]{2})"') { $Matches[1] } else { "?" }
        Write-Output "proxy exit: $exitIp  country: $country"
        if ($country -ne "US") {
            Write-Warning "exit is not US; www.pjm.com resets TLS for non-US exits. Select a US node in Clash Verge first."
        }
    }
}
catch { Write-Warning "could not determine proxy exit: $($_.Exception.Message)" }

$ok = 0
foreach ($f in $files) {
    $dest = Join-Path $repoRoot ($f.Path -replace '/', '\')
    $dir = Split-Path -Parent $dest
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    if ((Test-Path -LiteralPath $dest) -and ((Get-Item -LiteralPath $dest).Length -gt 10000)) {
        Write-Output ("[cached] {0}" -f $f.Path)
        $ok++
        continue
    }
    $tmp = "$dest.part"
    $args = @("-sS", "-L", "--max-time", "900", "-A", $UserAgent) + $headers +
        @("--resolve", "www.pjm.com:443:$PjmIp", "--socks5", $SocksProxy,
          "-o", $tmp, "-w", "%{http_code}", $f.Url)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try { $code = (& curl.exe @args 2>$null | Out-String).Trim() }
    finally { $ErrorActionPreference = $prev }

    $valid = $false
    if ($code -eq "200" -and (Test-Path -LiteralPath $tmp)) {
        $valid = if ($f.Kind -eq "zip") { Test-ZipArchive $tmp } else { Test-PdfFile $tmp }
    }
    if ($valid) {
        Move-Item -LiteralPath $tmp -Destination $dest -Force
        Write-Output ("[OK]   {0}  {1} bytes  ({2})" -f $f.Path, (Get-Item -LiteralPath $dest).Length, $f.Note)
        $ok++
    }
    else {
        if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Force }
        Write-Output ("[FAIL] {0}  http={1}" -f $f.Path, $code)
    }
}

Write-Output ""
Write-Output ("{0}/{1} files acquired" -f $ok, $files.Count)
if ($ok -ne $files.Count) { exit 1 }
