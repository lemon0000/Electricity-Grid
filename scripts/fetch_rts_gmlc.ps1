param(
    [string]$Destination = "data/raw/rts_gmlc/v0.2.3/upstream"
)

$ErrorActionPreference = "Stop"
$commit = "3ece0d3725c844056132393ee252b3083dd4eab4"
$baseUrl = "https://raw.githubusercontent.com/GridMod/RTS-GMLC/$commit"
$files = @(
    "README.md",
    "RTS_Data/SourceData/README.md",
    "RTS_Data/SourceData/branch.csv",
    "RTS_Data/SourceData/bus.csv",
    "RTS_Data/SourceData/dc_branch.csv",
    "RTS_Data/SourceData/gen.csv",
    "RTS_Data/SourceData/reserves.csv",
    "RTS_Data/SourceData/simulation_objects.csv",
    "RTS_Data/SourceData/storage.csv",
    "RTS_Data/SourceData/timeseries_pointers.csv",
    "RTS_Data/timeseries_data_files/README.md",
    "RTS_Data/timeseries_data_files/CSP/DAY_AHEAD_Natural_Inflow.csv",
    "RTS_Data/timeseries_data_files/Hydro/DAY_AHEAD_hydro.csv",
    "RTS_Data/timeseries_data_files/Hydro/DAY_AHEAD_hydro_inflow.csv",
    "RTS_Data/timeseries_data_files/Load/DAY_AHEAD_regional_Load.csv",
    "RTS_Data/timeseries_data_files/PV/DAY_AHEAD_pv.csv",
    "RTS_Data/timeseries_data_files/RTPV/DAY_AHEAD_rtpv.csv",
    "RTS_Data/timeseries_data_files/Reserves/DAY_AHEAD_regional_Flex_Down.csv",
    "RTS_Data/timeseries_data_files/Reserves/DAY_AHEAD_regional_Flex_Up.csv",
    "RTS_Data/timeseries_data_files/Reserves/DAY_AHEAD_regional_Reg_Down.csv",
    "RTS_Data/timeseries_data_files/Reserves/DAY_AHEAD_regional_Reg_Up.csv",
    "RTS_Data/timeseries_data_files/Reserves/DAY_AHEAD_regional_Spin_Up_R1.csv",
    "RTS_Data/timeseries_data_files/Reserves/DAY_AHEAD_regional_Spin_Up_R2.csv",
    "RTS_Data/timeseries_data_files/Reserves/DAY_AHEAD_regional_Spin_Up_R3.csv",
    "RTS_Data/timeseries_data_files/WIND/DAY_AHEAD_wind.csv"
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

Write-Output "RTS-GMLC $commit downloaded to $destinationRoot"
Write-Output "SHA256 manifest: $manifestPath"
