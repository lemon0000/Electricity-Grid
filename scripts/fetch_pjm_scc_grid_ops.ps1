param(
    [string]$SocksProxy = "127.0.0.1:7897",
    [string]$PjmIp = "156.154.237.70",
    [string]$SccIp = "108.156.22.83",
    [string]$UserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

# Re-attempt for the grid-ops files that www.pjm.com / www.scc.virginia.gov still withhold
# from the local network (2026-11-11 acquisition).
#
# Why SOCKS5 with a pinned origin IP: verge-mihomo routes by domain, and these hosts come back
# as DIRECT (blocked). Sending only an IP over SOCKS5 makes mihomo match on GEOIP, so the request
# actually leaves through the selected proxy node. www.pjm.com additionally drops TLS for
# non-US exits, so a US node must be selected in Clash Verge before this script can succeed.
#
# Usage:  pwsh scripts/fetch_pjm_scc_grid_ops.ps1
#         pwsh scripts/fetch_pjm_scc_grid_ops.ps1 -SocksProxy 127.0.0.1:7897 -PjmIp 1.2.3.4

$ErrorActionPreference = "Stop"
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))

$files = @(
    @{ Url = "https://www.pjm.com/-/media/DotCom/markets-ops/rpm/rpm-auction-info/2026-2027/2026-2027-bra-report.pdf";
       Path = "data/raw/pjm_bra/v2026_2027/upstream/2026-2027-bra-report.pdf"; Host = "www.pjm.com"; Ip = $PjmIp; Kind = "pdf" },
    @{ Url = "https://www.pjm.com/-/media/DotCom/markets-ops/rpm/rpm-auction-info/2026-2027/2026-2027-bra-results.xlsx";
       Path = "data/raw/pjm_bra/v2026_2027/upstream/2026-2027-bra-results.xlsx"; Host = "www.pjm.com"; Ip = $PjmIp; Kind = "zip" },
    @{ Url = "https://www.pjm.com/-/media/DotCom/markets-ops/rpm/rpm-auction-info/2025-2026/2025-2026-base-residual-auction-report.pdf";
       Path = "data/raw/pjm_bra/v2025_2026/upstream/2025-2026-base-residual-auction-report.pdf"; Host = "www.pjm.com"; Ip = $PjmIp; Kind = "pdf" },
    @{ Url = "https://www.pjm.com/-/media/DotCom/markets-ops/rpm/rpm-auction-info/2025-2026/2025-2026-base-residual-auction-results.xlsx";
       Path = "data/raw/pjm_bra/v2025_2026/upstream/2025-2026-base-residual-auction-results.xlsx"; Host = "www.pjm.com"; Ip = $PjmIp; Kind = "zip" },
    @{ Url = "https://www.pjm.com/-/media/DotCom/markets-ops/rpm/rpm-auction-info/2027-2028/2027-2028-bra-report.pdf";
       Path = "data/raw/pjm_bra/v2027_2028/upstream/2027-2028-bra-report.pdf"; Host = "www.pjm.com"; Ip = $PjmIp; Kind = "pdf" },
    @{ Url = "https://www.pjm.com/-/media/DotCom/markets-ops/rpm/rpm-auction-info/2027-2028/2027-2028-bra-results.xlsx";
       Path = "data/raw/pjm_bra/v2027_2028/upstream/2027-2028-bra-results.xlsx"; Host = "www.pjm.com"; Ip = $PjmIp; Kind = "zip" },
    @{ Url = "https://www.pjm.com/-/media/DotCom/markets-ops/settlements/network-integration-trans-service-october-2026-xls.xlsx";
       Path = "data/raw/pjm_nits/v2026_10/upstream/network-integration-trans-service-october-2026.xlsx"; Host = "www.pjm.com"; Ip = $PjmIp; Kind = "zip" },
    @{ Url = "https://www.pjm.com/-/media/DotCom/markets-ops/settlements/network-integration-trans-service-2025.pdf";
       Path = "data/raw/pjm_nits/v2025/upstream/network-integration-trans-service-2025.pdf"; Host = "www.pjm.com"; Ip = $PjmIp; Kind = "pdf" },
    @{ Url = "https://www.scc.virginia.gov/docketsearch/DOCS/89g601!.PDF";
       Path = "data/raw/va_scc_pur2025_00058/v1/upstream/89g601-final-order-2025-11-25.pdf"; Host = "www.scc.virginia.gov"; Ip = $SccIp; Kind = "pdf" },
    @{ Url = "https://www.scc.virginia.gov/docketsearch/DOCS/854_01!.PDF";
       Path = "data/raw/va_scc_pur2025_00058/v1/upstream/854_01-order-for-notice-and-hearing-2025-04-24.pdf"; Host = "www.scc.virginia.gov"; Ip = $SccIp; Kind = "pdf" }
)

# Note on the SCC host: going through scc.virginia.gov (global-accelerator IP 15.197.229.176) yields
# 307 -> www.scc.virginia.gov -> 307 -> /docketsearch/docs/89g601!.pdf (lower-cased) -> 404.
# Requesting www.scc.virginia.gov directly on its CloudFront IP returns the PDF. CloudFront rotates
# edges, so override -SccIp with a current address if this one stops answering.

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
                    $buffer = New-Object byte[] 65536
                    while ($stream.Read($buffer, 0, $buffer.Length) -gt 0) { }
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
    $tail = $latin1.GetString($bytes[[Math]::Max(0, $bytes.Length - 4096)..($bytes.Length - 1)])
    if (-not $tail.Contains("%%EOF")) { return $false }
    $all = $latin1.GetString($bytes)
    $idx = $all.LastIndexOf("startxref")
    if ($idx -lt 0) { return $false }
    $num = ($all.Substring($idx + 9) -split "\s+" | Where-Object { $_ -match '^\d+$' } | Select-Object -First 1)
    if (-not $num) { return $false }
    $off = [int]$num
    if ($off -lt 0 -or $off -ge $bytes.Length - 16) { return $false }
    $seg = $latin1.GetString($bytes[$off..($off + 15)])
    return ($seg.StartsWith("xref") -or $seg -match '^\d+\s+\d+\s+obj')
}

# --- preflight: show the exit country, because PJM drops TLS for non-US exits -------------
try {
    $exitIp = (& curl.exe -sS --max-time 25 --socks5-hostname $SocksProxy "https://api.ipify.org" 2>$null)
    if ($exitIp -match '^\d+\.\d+\.\d+\.\d+$') {
        $geo = (& curl.exe -sS --max-time 25 "https://ipinfo.io/$exitIp/json" 2>$null | Out-String)
        $country = if ($geo -match '"country":\s*"([A-Z]{2})"') { $Matches[1] } else { "?" }
        Write-Output "proxy exit: $exitIp  country: $country"
        if ($country -ne "US") {
            Write-Warning "exit is not US. www.pjm.com resets TLS for non-US exits; select a US node in Clash Verge first."
        }
    }
}
catch { Write-Warning "could not determine proxy exit: $($_.Exception.Message)" }

$results = @()
foreach ($file in $files) {
    $outputPath = Join-Path $repoRoot ($file.Path -replace '/', '\')
    $parent = Split-Path -Parent $outputPath
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    $tmpPath = "$outputPath.part"

    $curlArgs = @("-sS", "-L", "--max-time", "600", "-A", $UserAgent) + $headers +
        @("--resolve", "$($file.Host):443:$($file.Ip)",
          "--resolve", "www.scc.virginia.gov:443:$SccIp",
          "--socks5", $SocksProxy, "-o", $tmpPath, "-w", "%{http_code}", $file.Url)
    # PowerShell 5.1 turns native stderr into a terminating error when ErrorActionPreference is Stop,
    # so relax it for the duration of the curl call and rely on the HTTP code instead.
    $previousEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try { $code = (& curl.exe @curlArgs 2>$null | Out-String).Trim() }
    finally { $ErrorActionPreference = $previousEap }

    $valid = $false
    if ($code -eq "200" -and (Test-Path -LiteralPath $tmpPath)) {
        $valid = if ($file.Kind -eq "zip") { Test-ZipArchive $tmpPath } else { Test-PdfFile $tmpPath }
    }
    if ($valid) {
        Move-Item -LiteralPath $tmpPath -Destination $outputPath -Force
        $bytes = (Get-Item -LiteralPath $outputPath).Length
        Write-Output ("[OK]   {0}  {1} bytes" -f $file.Path, $bytes)
        $results += [pscustomobject]@{ Path = $file.Path; Status = "acquired"; Bytes = $bytes }
    }
    else {
        if (Test-Path -LiteralPath $tmpPath) { Remove-Item -LiteralPath $tmpPath -Force }
        Write-Output ("[FAIL] {0}  http={1}" -f $file.Path, $code)
        $results += [pscustomobject]@{ Path = $file.Path; Status = "failed:$code"; Bytes = 0 }
    }
}

$acquired = @($results | Where-Object { $_.Status -eq "acquired" })
Write-Output ""
Write-Output ("{0}/{1} files acquired" -f $acquired.Count, $results.Count)
if ($acquired.Count -gt 0) {
    Write-Output "Re-run the provenance registration so the hashes and pending list stay consistent:"
    Write-Output "  see data/raw/ENERGY_STORAGE_GRID_TASK_DATA_INDEX_20261111.md section 5"
}
if ($acquired.Count -ne $results.Count) { exit 1 }
