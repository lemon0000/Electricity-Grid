param(
    [string]$Destination = "data/raw/us_major_power_outages/v1/upstream"
)

$ErrorActionPreference = "Stop"
$pmcid = "PMC6141375"
$doi = "10.1016/j.dib.2018.06.067"
$licenseType = "CC BY"
$licenseUrl = "http://creativecommons.org/licenses/by/4.0/"
$xlinkNamespace = "http://www.w3.org/1999/xlink"
$supplementUrl = "https://www.ebi.ac.uk/europepmc/webservices/rest/$pmcid/supplementaryFiles"
$articleUrl = "https://www.ebi.ac.uk/europepmc/webservices/rest/$pmcid/fullTextXML"
$expectedMembers = @(
    [pscustomobject]@{
        Name = "mmc1.docx"
        Size = 24063
        Sha256 = "968c6ca57fea172f529ef4bb88cee6010a7db272f0e24696e5c93e3ec001b019"
    },
    [pscustomobject]@{
        Name = "mmc2.xlsx"
        Size = 660381
        Sha256 = "0129e24ed7c6872b794d0d2b515ad351a69b469034e3389c63ceda17426e71b2"
    }
)

function Resolve-DestinationRoot {
    param([string]$Path)

    if ([System.IO.Path]::IsPathRooted($Path)) {
        return [System.IO.Path]::GetFullPath($Path)
    }
    return [System.IO.Path]::GetFullPath(
        (Join-Path (Get-Location).Path $Path)
    )
}

function Test-VerifiedSupplement {
    param(
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $false
    }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    try {
        $archive = [System.IO.Compression.ZipFile]::OpenRead($Path)
    }
    catch {
        return $false
    }
    try {
        if ($archive.Entries.Count -ne $expectedMembers.Count) {
            return $false
        }
        foreach ($expected in $expectedMembers) {
            $entry = $archive.Entries | Where-Object { $_.FullName -eq $expected.Name }
            if ($null -eq $entry -or $entry.Length -ne $expected.Size) {
                return $false
            }
            $stream = $entry.Open()
            $sha256 = [System.Security.Cryptography.SHA256]::Create()
            try {
                $digest = $sha256.ComputeHash($stream)
                $actual = ([BitConverter]::ToString($digest)).Replace("-", "").ToLowerInvariant()
            }
            finally {
                $sha256.Dispose()
                $stream.Dispose()
            }
            if ($actual -ne $expected.Sha256) {
                return $false
            }
        }
        return $true
    }
    finally {
        $archive.Dispose()
    }
}

function Save-VerifiedSupplement {
    param(
        [string]$Uri,
        [string]$OutputPath
    )

    if (Test-VerifiedSupplement $OutputPath) {
        return
    }
    $partialPath = "$OutputPath.partial"
    Invoke-WebRequest -UseBasicParsing -Uri $Uri -OutFile $partialPath
    if (-not (Test-VerifiedSupplement $partialPath)) {
        Remove-Item -Force -LiteralPath $partialPath
        throw "Supplement member integrity check failed: $Uri"
    }
    Move-Item -Force -LiteralPath $partialPath -Destination $OutputPath
}

function Test-VerifiedArticle {
    param(
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $false
    }

    $settings = New-Object System.Xml.XmlReaderSettings
    $settings.DtdProcessing = [System.Xml.DtdProcessing]::Ignore
    $settings.XmlResolver = $null
    $reader = $null
    try {
        $reader = [System.Xml.XmlReader]::Create($Path, $settings)
        $document = New-Object System.Xml.XmlDocument
        $document.Load($reader)
    }
    catch {
        return $false
    }
    finally {
        if ($null -ne $reader) {
            $reader.Dispose()
        }
    }

    $pmcidNodes = @($document.SelectNodes(
        "//*[local-name()='article-meta']/*[local-name()='article-id' and @pub-id-type='pmcid']"
    ))
    $doiNodes = @($document.SelectNodes(
        "//*[local-name()='article-meta']/*[local-name()='article-id' and @pub-id-type='doi']"
    ))
    $licenseNodes = @($document.SelectNodes(
        "//*[local-name()='article-meta']/*[local-name()='permissions']/*[local-name()='license']"
    ))

    if ($pmcidNodes.Count -ne 1 -or $doiNodes.Count -ne 1 -or $licenseNodes.Count -ne 1) {
        return $false
    }
    if (-not [System.String]::Equals(
        $pmcidNodes[0].InnerText.Trim(),
        $pmcid,
        [System.StringComparison]::Ordinal
    )) {
        return $false
    }
    if (-not [System.String]::Equals(
        $doiNodes[0].InnerText.Trim(),
        $doi,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
        return $false
    }

    $articleLicense = $licenseNodes[0]
    return [System.String]::Equals(
        $articleLicense.GetAttribute("license-type"),
        $licenseType,
        [System.StringComparison]::Ordinal
    ) -and [System.String]::Equals(
        $articleLicense.GetAttribute("href", $xlinkNamespace),
        $licenseUrl,
        [System.StringComparison]::Ordinal
    )
}

function Save-VerifiedArticle {
    param(
        [string]$Uri,
        [string]$OutputPath
    )

    $partialPath = "$OutputPath.partial"
    try {
        Invoke-WebRequest -UseBasicParsing -Uri $Uri -OutFile $partialPath
        if (-not (Test-VerifiedArticle $partialPath)) {
            throw "Article identity or license verification failed: $Uri"
        }
        Move-Item -Force -LiteralPath $partialPath -Destination $OutputPath
    }
    catch {
        if (Test-Path -LiteralPath $partialPath) {
            Remove-Item -Force -LiteralPath $partialPath
        }
        throw
    }
}

$destinationRoot = Resolve-DestinationRoot $Destination
New-Item -ItemType Directory -Force -Path $destinationRoot | Out-Null

$supplementPath = Join-Path $destinationRoot "supplementary_files.zip"
Save-VerifiedSupplement `
    -Uri $supplementUrl `
    -OutputPath $supplementPath
Save-VerifiedArticle -Uri $articleUrl -OutputPath (Join-Path $destinationRoot "article.xml")

$sourceMetadata = [ordered]@{
    dataset = "U.S. Major Power Outage Events"
    pmcid = $pmcid
    doi = $doi
    article_url = $articleUrl
    supplement_url = $supplementUrl
    supplement_container_byte_stable = $false
    members = @(
        $expectedMembers | ForEach-Object {
            [ordered]@{
                name = $_.Name
                size = $_.Size
                sha256 = $_.Sha256
            }
        }
    )
}
$sourceMetadata | ConvertTo-Json -Depth 3 |
    Set-Content -LiteralPath (Join-Path $destinationRoot "SOURCE_METADATA.json") -Encoding UTF8

$manifest = Get-ChildItem -LiteralPath $destinationRoot -Recurse -File |
    Where-Object { $_.Name -ne "SHA256SUMS" -and $_.Name -notlike "*.partial" } |
    Sort-Object FullName |
    ForEach-Object {
        $relativePath = $_.FullName.Substring($destinationRoot.Length + 1).Replace("\", "/")
        $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant()
        "$hash  $relativePath"
    }
$manifest | Set-Content -LiteralPath (Join-Path $destinationRoot "SHA256SUMS") -Encoding ascii

Write-Output "U.S. major power outage data downloaded to $destinationRoot"
Write-Output "PMCID: $pmcid; DOI: $doi"
Write-Output "SHA256 manifest: $(Join-Path $destinationRoot 'SHA256SUMS')"
