param(
    [string]$Destination = "data/raw/rts_gmlc/v0.2.3/ac_reference"
)

$ErrorActionPreference = "Stop"
$commit = "3ece0d3725c844056132393ee252b3083dd4eab4"
$relativePath = "RTS_Data/FormattedData/MATPOWER/RTS_GMLC.m"
$expectedSha256 = "10573aee70f793c28a0602516f85c4345e6f171512852f1162c3bb3b02ba575b"
$baseUrl = "https://raw.githubusercontent.com/GridMod/RTS-GMLC/$commit"

$destinationRoot = [System.IO.Path]::GetFullPath(
    (Join-Path (Get-Location) $Destination)
)
New-Item -ItemType Directory -Force -Path $destinationRoot | Out-Null
$outputPath = Join-Path $destinationRoot "RTS_GMLC.m"
Invoke-WebRequest -Uri "$baseUrl/$relativePath" -OutFile $outputPath

$observedSha256 = (
    Get-FileHash -Algorithm SHA256 -LiteralPath $outputPath
).Hash.ToLowerInvariant()
if ($observedSha256 -ne $expectedSha256) {
    throw "RTS-GMLC AC reference SHA-256 drifted: $observedSha256"
}
"$observedSha256  RTS_GMLC.m" | Set-Content (
    Join-Path $destinationRoot "SHA256SUMS"
) -Encoding ascii

Write-Output "RTS-GMLC AC reference downloaded to $destinationRoot"
Write-Output "SHA256: $observedSha256"
