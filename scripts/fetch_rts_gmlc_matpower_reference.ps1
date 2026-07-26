param(
    [string]$Destination = "data/raw/rts_gmlc/v0.2.3/matpower_reference"
)

$ErrorActionPreference = "Stop"
$commit = "3ece0d3725c844056132393ee252b3083dd4eab4"
$baseUrl = "https://raw.githubusercontent.com/GridMod/RTS-GMLC/$commit"
$files = @(
    "RTS_Data/FormattedData/MATPOWER/README.md",
    "RTS_Data/FormattedData/MATPOWER/RTS_GMLC.m"
)

$destinationRoot = [System.IO.Path]::GetFullPath(
    (Join-Path (Get-Location) $Destination)
)
New-Item -ItemType Directory -Force -Path $destinationRoot | Out-Null

foreach ($relativePath in $files) {
    $outputPath = Join-Path $destinationRoot $relativePath
    $parent = Split-Path -Parent $outputPath
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    Invoke-WebRequest -Uri "$baseUrl/$relativePath" -OutFile $outputPath
}

$manifest = foreach ($relativePath in $files) {
    $outputPath = Join-Path $destinationRoot $relativePath
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $outputPath).Hash.ToLower()
    "$hash  $relativePath"
}
$manifestPath = Join-Path $destinationRoot "SHA256SUMS"
$manifest | Set-Content -LiteralPath $manifestPath -Encoding ascii

Write-Output "RTS-GMLC MATPOWER reference $commit downloaded to $destinationRoot"
Write-Output "SHA256 manifest: $manifestPath"
