# WKX Photo Watermark

一个基于 PySide6 的图片水印工具，支持文本水印与图片水印，提供描边、阴影、旋转、位置枚举与自定义定位等功能，预览与导出效果一致。

## 主要功能
- 文本水印：
  - 即时预览，支持字体、大小、颜色、透明度
  - 描边与阴影开关与参数即时生效（无需切换图片）
  - 旋转角度居中应用，支持九宫格枚举位置与自定义位置
- 图片水印：
  - 即时缩放与旋转，位置枚举与自定义定位
- 批量导出：在 <mcfile name="export_panel.py" path="app/ui/export_panel.py"></mcfile> 中配置导出选项

## 环境要求
- 建议使用 Conda 环境（已提供 <mcfile name="environment.yml" path="environment.yml"></mcfile>）
- 必要依赖详见 <mcfile name="requirements.txt" path="requirements.txt"></mcfile>

## 安装与运行
1. 创建并激活 Conda 环境（可直接用 environment.yml）
   - conda env create -f environment.yml
   - conda activate wkx-photo-watermark
2. 在项目根目录运行应用：
   - python -m app.main
   - 入口文件：<mcfile name="main.py" path="app/main.py"></mcfile>

## 打包为可执行文件（Windows）
已提供打包脚本：<mcfile name="build_exe.ps1" path="scripts/build_exe.ps1"></mcfile>
- 默认使用环境名 wkx-photo-watermark，可按需调整
- 执行示例：
  - powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1
  - 指定环境名：powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1 -EnvName zxy_watermark
- 输出位置：dist\WKXPhotoWaterMark.exe

## 发布 Release（GitHub）
已提供发布脚本：<mcfile name="publish_release.ps1" path="scripts/publish_release.ps1"></mcfile>
- 依赖环境变量 GITHUB_TOKEN（建议仅授予 repo 权限）
- 示例：
  - $env:GITHUB_TOKEN = "你的GitHub令牌"
  - powershell -ExecutionPolicy Bypass -File .\scripts\publish_release.ps1 -RepoOwner Xvidddd -RepoName WKXPhotoWaterMark2 -TagName v1.0 -ReleaseName "WKX Photo Watermark v1.0" -Body "首个版本发布，包含单文件 exe。" -AssetPath .\releases\WKXPhotoWaterMark-v1.0-win64.zip

## 项目结构
- <mcfile name="main.py" path="app/main.py"></mcfile> 应用入口
- <mcfile name="preview_view.py" path="app/ui/preview_view.py"></mcfile> 预览画布与水印绘制
- <mcfile name="watermark_panel.py" path="app/ui/watermark_panel.py"></mcfile> 水印参数面板
- <mcfile name="export_panel.py" path="app/ui/export_panel.py"></mcfile> 导出设置与操作
- <mcfile name="build_exe.ps1" path="scripts/build_exe.ps1"></mcfile> 打包脚本
- <mcfile name="publish_release.ps1" path="scripts/publish_release.ps1"></mcfile> 发布脚本
- <mcfile name="requirements.txt" path="requirements.txt"></mcfile> 依赖列表
- <mcfile name="environment.yml" path="environment.yml"></mcfile> Conda 环境描述

## 常见问题
- 首次启动 EXE 较慢：单文件模式需解压运行，属正常现象。
- 体积较大：PySide6 依赖较多，已在脚本中使用 --collect-all 以确保可移植性。
- 数据库驱动警告（OCI.dll/LIBPQ.dll）：与本工具无关，可忽略。

如需自定义图标、应用名或增加版本信息，请告诉我你的具体要求，我会更新打包与发布脚本。