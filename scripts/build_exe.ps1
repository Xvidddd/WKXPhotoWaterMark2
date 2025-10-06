Param(
    [string]$EnvName = "wkx-photo-watermark"
)

$ErrorActionPreference = "Stop"

# 切换到项目根目录（脚本位于 scripts/ 下）
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "[Build] 使用 conda 环境: $EnvName"
Write-Host "[Build] 项目根目录: $(Get-Location)"

# 清理旧的构建产物
if (Test-Path .\build) { Remove-Item .\build -Recurse -Force -ErrorAction Ignore }
if (Test-Path .\dist) { Remove-Item .\dist -Recurse -Force -ErrorAction Ignore }

# 安装/更新打包依赖（在指定 conda 环境内执行）
conda run -n $EnvName python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "[Build] 依赖安装失败" }

# 执行打包（收集 PySide6/shiboken6 资源，单文件，无控制台）
$pyiCmd = "python -m PyInstaller --collect-all PySide6 --collect-all shiboken6 -F -w -n WKXPhotoWaterMark app\main.py"
conda run -n $EnvName $pyiCmd
if ($LASTEXITCODE -ne 0) { throw "[Build] 打包失败" }

Write-Host "[Build] 完成，输出文件：$(Resolve-Path .\dist\WKXPhotoWaterMark.exe)"