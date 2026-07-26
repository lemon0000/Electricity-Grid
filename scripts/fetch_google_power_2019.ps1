param(
    [string]$Destination = "data/raw/google_power_2019/2019/upstream"
)

$ErrorActionPreference = "Stop"
$bucket = "powerdata_2019"
$documentationCommit = "3f6a61d380dc4ea847416d5414c5fa499f830b9d"
$bucketApi = "https://storage.googleapis.com/storage/v1/b/$bucket/o?maxResults=1000"
$expectedTraceCount = 57
$expectedObjectCount = 58
$expectedTotalBytes = 3254733
$expectedObjectManifestSha256 = "bf820bc974b76432f8aa4c1865336e20833ffd4e961accde6a49cd7ff4881ca4"

function Get-Md5HexFromBase64 {
    param([string]$Digest)

    return ([BitConverter]::ToString(
        [Convert]::FromBase64String($Digest)
    )).Replace("-", "").ToLowerInvariant()
}

function Save-Atomic {
    param(
        [string]$Uri,
        [string]$OutputPath
    )

    $partialPath = "$OutputPath.partial"
    Invoke-WebRequest -UseBasicParsing -Uri $Uri -OutFile $partialPath
    Move-Item -Force -LiteralPath $partialPath -Destination $OutputPath
}

function Get-TextSha256 {
    param([string]$Value)

    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    try {
        $digest = $sha256.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($Value))
        return ([BitConverter]::ToString($digest)).Replace("-", "").ToLowerInvariant()
    }
    finally {
        $sha256.Dispose()
    }
}

function Resolve-DestinationRoot {
    param([string]$Path)

    if ([System.IO.Path]::IsPathRooted($Path)) {
        return [System.IO.Path]::GetFullPath($Path)
    }
    return [System.IO.Path]::GetFullPath(
        (Join-Path (Get-Location).Path $Path)
    )
}

$destinationRoot = Resolve-DestinationRoot $Destination
$documentationRoot = Join-Path $destinationRoot "documentation"
New-Item -ItemType Directory -Force -Path $documentationRoot | Out-Null

$response = Invoke-RestMethod -Uri $bucketApi
$objects = @($response.items | Where-Object { $_.name -like "*.csv.gz" })
$traceObjects = @(
    $objects | Where-Object {
        $_.name -match '^cell[a-j]_(pdu\d+|mvpp\d+)\.csv\.gz$'
    }
)
$mappingObjects = @(
    $objects | Where-Object { $_.name -eq "machine_to_pdu_mapping.csv.gz" }
)
if ($objects.Count -ne $expectedObjectCount) {
    throw "Expected $expectedObjectCount Google PowerData objects, found $($objects.Count)"
}
if ($traceObjects.Count -ne $expectedTraceCount) {
    throw "Expected $expectedTraceCount power-domain traces, found $($traceObjects.Count)"
}
if ($mappingObjects.Count -ne 1) {
    throw "Expected exactly one machine-to-PDU mapping object"
}
$totalBytes = ($objects | Measure-Object -Property size -Sum).Sum
$objectManifestLines = @(
    $objects | Sort-Object name | ForEach-Object {
        "$($_.name)`t$($_.generation)`t$($_.size)`t$($_.md5Hash)"
    }
)
$objectManifestSha256 = Get-TextSha256 (($objectManifestLines -join "`n") + "`n")
if ($totalBytes -ne $expectedTotalBytes) {
    throw "Expected $expectedTotalBytes Google PowerData bytes, found $totalBytes"
}
if ($objectManifestSha256 -ne $expectedObjectManifestSha256) {
    throw "Google PowerData object-generation manifest drifted from the pinned snapshot"
}

foreach ($object in ($objects | Sort-Object name)) {
    $outputPath = Join-Path $destinationRoot $object.name
    $expectedLength = [long]$object.size
    $expectedMd5 = Get-Md5HexFromBase64 $object.md5Hash
    $validExisting = (Test-Path -LiteralPath $outputPath) -and
        ((Get-Item -LiteralPath $outputPath).Length -eq $expectedLength) -and
        ((Get-FileHash -Algorithm MD5 -LiteralPath $outputPath).Hash.ToLowerInvariant() -eq $expectedMd5)
    if (-not $validExisting) {
        Save-Atomic -Uri $object.mediaLink -OutputPath $outputPath
    }
    $actualLength = (Get-Item -LiteralPath $outputPath).Length
    $actualMd5 = (Get-FileHash -Algorithm MD5 -LiteralPath $outputPath).Hash.ToLowerInvariant()
    if ($actualLength -ne $expectedLength -or $actualMd5 -ne $expectedMd5) {
        throw "Google object integrity check failed: $($object.name)"
    }
}

$documentationFiles = @(
    "PowerData2019.md",
    "ClusterData2019.md",
    "power_trace_documentation.pdf",
    "power_trace_analysis_colab.ipynb"
)
$documentationBase = "https://raw.githubusercontent.com/google/cluster-data/$documentationCommit"
foreach ($name in $documentationFiles) {
    Save-Atomic -Uri "$documentationBase/$name" -OutputPath (Join-Path $documentationRoot $name)
}

$sourceMetadata = [ordered]@{
    dataset = "Google PowerData 2019"
    bucket = $bucket
    bucket_api = $bucketApi
    documentation_repository = "https://github.com/google/cluster-data"
    documentation_commit = $documentationCommit
    object_manifest_sha256 = $objectManifestSha256
    total_bytes = $totalBytes
    objects = @(
        $objects | Sort-Object name | ForEach-Object {
            [ordered]@{
                name = $_.name
                generation = $_.generation
                size = [long]$_.size
                md5_base64 = $_.md5Hash
                updated = $_.updated
            }
        }
    )
}
$sourceMetadata | ConvertTo-Json -Depth 5 |
    Set-Content -LiteralPath (Join-Path $destinationRoot "SOURCE_OBJECTS.json") -Encoding UTF8

$manifest = Get-ChildItem -LiteralPath $destinationRoot -Recurse -File |
    Where-Object { $_.Name -ne "SHA256SUMS" -and $_.Name -notlike "*.partial" } |
    Sort-Object FullName |
    ForEach-Object {
        $relativePath = $_.FullName.Substring($destinationRoot.Length + 1).Replace("\", "/")
        $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant()
        "$hash  $relativePath"
    }
$manifest | Set-Content -LiteralPath (Join-Path $destinationRoot "SHA256SUMS") -Encoding ascii

Write-Output "Google PowerData 2019 downloaded to $destinationRoot"
Write-Output "Objects: $($objects.Count); power domains: $($traceObjects.Count)"
Write-Output "SHA256 manifest: $(Join-Path $destinationRoot 'SHA256SUMS')"
