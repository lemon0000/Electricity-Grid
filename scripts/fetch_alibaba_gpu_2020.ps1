param(
    [string]$Destination = "data/raw/alibaba_gpu_2020/v2020/upstream"
)

$ErrorActionPreference = "Stop"
$documentationCommit = "0d0f3f1efdbf1add6a7bcc63676eafbd1eb11f71"
$ossBase = "https://aliopentrace.oss-cn-beijing.aliyuncs.com/v2020GPUTraces"
$githubBase = "https://raw.githubusercontent.com/alibaba/clusterdata/$documentationCommit/cluster-trace-gpu-v2020"

$archives = @(
    [pscustomobject]@{
        Name = "pai_group_tag_table.tar.gz"
        Size = 55064781
        Sha256 = "722fef30b7fb7aa50dabd79155614b5423a9d65cf45a9b26c590d57725423a14"
    },
    [pscustomobject]@{
        Name = "pai_job_table.tar.gz"
        Size = 62065432
        Sha256 = "5aad7f7caac501136d14ed6a48e40546f825d7b0617a3a4f337e2348fe0a6cb0"
    },
    [pscustomobject]@{
        Name = "pai_machine_spec.tar.gz"
        Size = 30449
        Sha256 = "cc0d38a4045af1b1af8179de8b1b54b1ddd995e6160d6d061a6b1000f1276c2d"
    },
    [pscustomobject]@{
        Name = "pai_task_table.tar.gz"
        Size = 35514117
        Sha256 = "cd1d6dc3215d2a8607ccf6b6dd952b5db776df86926c73259fea7c1499ac40e5"
    }
)

$headers = @(
    [pscustomobject]@{
        Name = "pai_group_tag_table.header"
        Sha256 = "320470fa8f77182bc6052c95ff359b75542c748e9516b3d8148a6e2bafc1798d"
    },
    [pscustomobject]@{
        Name = "pai_job_table.header"
        Sha256 = "3ac33aefab9a4d81338794fa145fe280594a379444961a9c639f00181c508567"
    },
    [pscustomobject]@{
        Name = "pai_machine_spec.header"
        Sha256 = "4c9ea25914ff3f0b73be9ff223fb91002e787138165abd3f584ba37281448e1c"
    },
    [pscustomobject]@{
        Name = "pai_task_table.header"
        Sha256 = "978bbaabfc8695874c605c01c144b2977f611ceca73aeb72189988cdfbfb0a9c"
    }
)

function Save-VerifiedArtifact {
    param(
        [string]$Uri,
        [string]$OutputPath,
        [string]$ExpectedSha256,
        [long]$ExpectedSize = 0
    )

    if (Test-VerifiedArtifact $OutputPath $ExpectedSha256 $ExpectedSize) {
        return
    }

    $partialPath = "$OutputPath.partial"
    if (Test-VerifiedArtifact $partialPath $ExpectedSha256 $ExpectedSize) {
        Move-Item -Force -LiteralPath $partialPath -Destination $OutputPath
        return
    }
    if ((Test-Path -LiteralPath $partialPath) -and
        $ExpectedSize -gt 0 -and
        (Get-Item -LiteralPath $partialPath).Length -ge $ExpectedSize) {
        Remove-Item -Force -LiteralPath $partialPath
    }

    & curl.exe --fail --location --silent --show-error --retry 3 `
        --retry-all-errors --continue-at - --output $partialPath $Uri
    $resumeSucceeded = $LASTEXITCODE -eq 0 -and
        (Test-VerifiedArtifact $partialPath $ExpectedSha256 $ExpectedSize)
    if (-not $resumeSucceeded) {
        if (Test-Path -LiteralPath $partialPath) {
            Remove-Item -Force -LiteralPath $partialPath
        }
        & curl.exe --fail --location --silent --show-error --retry 3 `
            --retry-all-errors --output $partialPath $Uri
        if ($LASTEXITCODE -ne 0 -or
            -not (Test-VerifiedArtifact $partialPath $ExpectedSha256 $ExpectedSize)) {
            if (Test-Path -LiteralPath $partialPath) {
                Remove-Item -Force -LiteralPath $partialPath
            }
            throw "Verified download failed after a clean retry: $Uri"
        }
    }
    Move-Item -Force -LiteralPath $partialPath -Destination $OutputPath
}

function Test-VerifiedArtifact {
    param(
        [string]$Path,
        [string]$ExpectedSha256,
        [long]$ExpectedSize = 0
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $false
    }
    if ($ExpectedSize -gt 0 -and (Get-Item -LiteralPath $Path).Length -ne $ExpectedSize) {
        return $false
    }
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant() -eq $ExpectedSha256
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

foreach ($archive in $archives) {
    Save-VerifiedArtifact `
        -Uri "$ossBase/$($archive.Name)" `
        -OutputPath (Join-Path $destinationRoot $archive.Name) `
        -ExpectedSha256 $archive.Sha256 `
        -ExpectedSize $archive.Size
}
foreach ($header in $headers) {
    Save-VerifiedArtifact `
        -Uri "$githubBase/data/$($header.Name)" `
        -OutputPath (Join-Path $destinationRoot $header.Name) `
        -ExpectedSha256 $header.Sha256
}

Save-Atomic -Uri "$githubBase/README.md" -OutputPath (Join-Path $documentationRoot "README.md")
Save-Atomic -Uri "$githubBase/data/README.md" -OutputPath (Join-Path $documentationRoot "DATA_README.md")
Save-Atomic -Uri "$githubBase/LICENSE" -OutputPath (Join-Path $documentationRoot "LICENSE")

$sourceMetadata = [ordered]@{
    dataset = "Alibaba PAI GPU Cluster Trace v2020"
    profile = "stage1_core"
    data_base_url = $ossBase
    documentation_repository = "https://github.com/alibaba/clusterdata"
    documentation_commit = $documentationCommit
    archives = @(
        $archives | ForEach-Object {
            [ordered]@{
                name = $_.Name
                size = $_.Size
                sha256 = $_.Sha256
            }
        }
    )
    headers = @(
        $headers | ForEach-Object {
            [ordered]@{
                name = $_.Name
                sha256 = $_.Sha256
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

$totalBytes = ($archives | Measure-Object -Property Size -Sum).Sum
Write-Output "Alibaba GPU v2020 stage1_core downloaded to $destinationRoot"
Write-Output "Archives: $($archives.Count); compressed bytes: $totalBytes"
Write-Output "SHA256 manifest: $(Join-Path $destinationRoot 'SHA256SUMS')"
