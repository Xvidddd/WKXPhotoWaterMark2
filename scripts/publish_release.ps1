Param(
    [Parameter(Mandatory=$true)][string]$RepoOwner,
    [Parameter(Mandatory=$true)][string]$RepoName,
    [Parameter(Mandatory=$true)][string]$TagName,
    [string]$ReleaseName = $TagName,
    [string]$Body = "",
    [Parameter(Mandatory=$true)][string]$AssetPath,
    [string]$Token = $Env:GITHUB_TOKEN
)

$ErrorActionPreference = "Stop"

if (-not $Token) {
    throw "GitHub Token 未提供。请设置环境变量 GITHUB_TOKEN 或通过 -Token 传入。"
}

# 规范化路径
$AssetFullPath = Resolve-Path -Path $AssetPath
if (-not (Test-Path $AssetFullPath)) {
    throw "资产文件不存在: $AssetPath"
}

# GitHub API 头
$Headers = @{ 
    Authorization = "Bearer $Token" 
    Accept = "application/vnd.github+json" 
    "X-GitHub-Api-Version" = "2022-11-28"
    "User-Agent" = "WKXPhotoWaterMark-ReleaseScript"
}

# 创建 Release
$createUrl = "https://api.github.com/repos/$RepoOwner/$RepoName/releases"
$createBody = @{ 
    tag_name = $TagName 
    name     = $ReleaseName 
    body     = $Body 
    draft    = $false 
    prerelease = $false 
} | ConvertTo-Json

Write-Host "[Release] 创建 release: $ReleaseName ($TagName)"
$release = Invoke-RestMethod -Method Post -Uri $createUrl -Headers $Headers -Body $createBody

# 上传资产
$assetName = [System.IO.Path]::GetFileName($AssetFullPath)
$uploadUrl = $release.upload_url -replace "\{\?name,label\}", "?name=$assetName"
$ContentType = if ($assetName -match "\.zip$") { "application/zip" } else { "application/octet-stream" }

Write-Host "[Release] 上传资产: $assetName"
Invoke-WebRequest -Method Post -Uri $uploadUrl -Headers $Headers -ContentType $ContentType -InFile $AssetFullPath | Out-Null

Write-Host "[Release] 发布完成: https://github.com/$RepoOwner/$RepoName/releases/tag/$TagName"