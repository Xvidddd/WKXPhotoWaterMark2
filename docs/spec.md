# WKX Photo Watermark（Windows 本地应用）产品与技术规格

本文档用于指导后续 Python 桌面应用开发，聚焦“图片水印本地处理”。涵盖需求、技术选型、架构设计、交互与测试打包等内容，作为实现与验收依据。

## 1. 项目综述

- 目标：提供稳定、易用的本地图片批量加水印工具，支持文本与图片水印，实时预览与灵活导出。
- 平台：Windows 桌面。
- 语言与框架：Python 3.10+；GUI 建议 `PySide6`（或 `PyQt6`），图像处理使用 `Pillow`。
- 打包：`PyInstaller` 生成单文件或安装包。

## 2. 技术选型

- GUI：
  - 首选：`PySide6`（LGPL，许可证友好）或备选：`PyQt6`。
  - 组件建议：`QMainWindow` + `QDockWidget`/`QSplitter` 布局；`QListView`/`QListWidget` 显示缩略图；`QGraphicsView` 实现高性能预览与水印交互。
- 图像处理：
  - `Pillow` 支持 JPEG、PNG、BMP、TIFF，PNG 透明通道；文本渲染用 `ImageDraw`+`ImageFont`。
  - 旋转、缩放、透明叠加由 `Pillow` 完成。
- 缩略图：`Pillow` 生成，缓存至内存（必要时磁盘缓存）。
- 并发：批量导出使用 `concurrent.futures.ThreadPoolExecutor`。
- 配置存储：JSON 文件；路径建议：`%AppData%/WKXPhotoWaterMark2/`。
- 日志：`logging`，滚动文件日志，便于问题定位。

## 3. 功能规格

### 3.1 文件处理

- 导入图片：
  - 支持单张拖拽或文件选择器导入。
  - 支持批量导入与导入整个文件夹（递归可选）。
  - 界面展示已导入图片列表：缩略图 + 文件名。
- 支持格式：
  - 输入：必须支持 JPEG、PNG；强烈建议支持 BMP、TIFF。PNG 必须支持透明通道。
  - 输出：用户可选择 JPEG 或 PNG。
- 导出：
  - 用户指定输出文件夹，默认禁止与原文件夹相同（避免覆盖）。
  - 文件命名规则：保留原文件名／自定义前缀（如 `wm_`）／自定义后缀（如 `_watermarked`）。
  - JPEG 质量：0-100 滑块（可选高级）。
  - 尺寸调整：按宽度／高度／百分比缩放（可选高级）。

### 3.2 水印类型

- 文本水印：
  - 内容：任意文本输入。
  - 字体：选择系统字体、字号、粗体、斜体（可选高级）。
  - 颜色：调色板选择字体颜色（可选高级）。
  - 透明度：0-100%。
  - 样式：阴影与描边（可选高级）。
- 图片水印（可选高级）：
  - 选择本地图片（如 Logo），PNG 透明通道必须支持。
  - 缩放：按比例或自由调整。
  - 透明度：0-100%。

### 3.3 布局与样式

- 实时预览：所有调整即时显示，点击图片列表切换预览目标。
- 位置：
  - 预设：九宫格（四角、正中心）。
  - 手动拖拽：预览中鼠标拖拽到任意位置。
- 旋转：滑块或输入框设置任意角度（可选高级）。

### 3.4 配置管理

- 水印模板：保存当前全部水印参数（内容、字体、颜色、位置、大小、透明度等）。
- 模板管理：加载、重命名、删除。
- 启动行为：自动加载上次关闭时的设置或默认模板。

## 4. UI 与交互设计

- 主界面布局（建议）：
  - 左侧：图片列表（缩略图 + 文件名，支持多选、右键移除）。
  - 中间：`QGraphicsView` 预览区（原图缩放适配；水印图层可拖拽、旋转、透明叠加）。
  - 右侧：设置面板（分页或折叠面板）：
    - 文本水印：文本输入、字体、字号、粗体/斜体、颜色、透明度、阴影/描边。
    - 图片水印：选择文件、缩放、透明度、替换/移除。
    - 布局：九宫格按钮、精细坐标（x,y）、旋转角度、对齐基准（相对图片、相对裁剪后区域）。
    - 导出：输出格式、质量、尺寸调整、命名规则、输出目录选择。
    - 模板：保存、加载、删除、默认模板管理。
- 交互细节：
  - 拖拽：在预览中显示拖拽手柄，支持吸附到九宫格位置。
  - 旋转：提供旋转手柄或滑块；显示当前角度。
  - 透明度：统一以 0-100% 显示。
  - 预览性能：水印层单独渲染，缩放预览不重复重算原图。
  - 键盘：删除（移除选中图片）、Ctrl+A（全选）、Ctrl+S（保存模板）、Ctrl+E（导出）。

## 5. 核心架构设计

- 分层结构：
  - UI 层（Qt Widgets）：视图、交互、表单。
  - 业务层（Service）：导入/导出、模板管理、水印渲染协调。
  - 渲染层（Engine）：生成水印图层、合成到目标图像；可独立测试。
  - 存储层（Storage）：本地 JSON 模板与设置、日志。
- 模块划分：
  - `app/ui/`: 主窗口、面板、列表、预览。
  - `app/services/`: 导入、导出、模板、缩略图缓存。
  - `app/engine/`: 文本水印、图片水印、合成、变换。
  - `app/models/`: 数据模型与配置对象。
  - `app/store/`: 本地持久化（JSON）、最近使用记录。
  - `app/utils/`: 路径、EXIF、颜色、校验、日志工具。

## 6. 数据模型（示例）

```json
// WatermarkConfig.json（示意）
{
  "type": "text" | "image",
  "textOptions": {
    "content": "string",
    "fontFamily": "string",
    "fontSize": 24,
    "bold": false,
    "italic": false,
    "color": "#RRGGBB",
    "opacity": 0.7,
    "shadow": { "enabled": true, "offset": [2,2], "blur": 2, "color": "#000000" },
    "stroke": { "enabled": true, "width": 2, "color": "#FFFFFF" }
  },
  "imageOptions": {
    "path": "C:/path/logo.png",
    "scale": 0.5,
    "opacity": 0.7
  },
  "layout": {
    "preset": "center" | "top_left" | "top_right" | "bottom_left" | "bottom_right" | "center_left" | "center_right" | "top_center" | "bottom_center",
    "position": { "x": 100, "y": 80 },
    "rotation": 0
  },
  "exportOptions": {
    "format": "jpeg" | "png",
    "jpegQuality": 85,
    "resize": { "mode": "none" | "width" | "height" | "scale", "value": 0 },
    "naming": { "mode": "keep" | "prefix" | "suffix", "value": "wm_" },
    "outputDir": "D:/output"
  }
}
```

## 7. 渲染与合成流程

- 预览渲染：
  1. 加载原图为 `RGBA`（统一色彩空间，便于合成）。
  2. 生成水印层：文本水印（先绘制到透明画布）或图片水印（读取并按透明度、缩放处理）。
  3. 应用旋转与位置：在单独图层进行仿射变换；记录锚点（中心或左上角）。
  4. 合成：`Image.alpha_composite` 或 `paste(mask=alpha)`，得到预览图；缩放以适配视图。
  5. 拖拽交互：仅更新水印层位置与变换矩阵，避免重算原图。
- 批量导出：
  1. 校验输出目录不与输入目录相同（默认禁止）。
  2. 逐图应用统一水印配置（或每图单独配置，后续可扩展）。
  3. 可选尺寸调整：在合成前或后进行（推荐先调整目标图尺寸，再合成水印，保证视觉一致）。
  4. 输出为 JPEG/PNG；JPEG 应用质量参数，PNG 保留 alpha。
  5. 命名规则：根据 `keep/prefix/suffix` 生成新文件名；处理重名冲突（追加序号）。
  6. 提供进度条与取消操作。

## 8. 模板与设置管理

- 模板保存：序列化 `WatermarkConfig` 到 `%AppData%/WKXPhotoWaterMark2/templates/*.json`。
- 启动加载：优先加载最近使用模板（`last-session.json`）；若不存在则加载默认模板。
- 管理：列出模板、预览摘要（文本片段或图片路径）、重命名、删除；校验模板引用的图片路径是否有效。

## 9. 错误处理与日志

- 典型错误：
  - 不支持的格式或损坏文件：提示并跳过。
  - PNG 透明通道缺失：正常处理（仅无透明效果）。
  - 字体不可用：回退到系统默认字体并提示。
  - 输出目录不可写：提示重新选择或申请管理员权限。
- 日志：
  - 级别：INFO/ERROR；错误栈记录到文件，关键提示显示在状态栏。
  - 路径：`%AppData%/WKXPhotoWaterMark2/logs/app.log`，滚动大小 5MB x 3。

## 10. 性能与质量

- 大图优化：
  - 预览使用缩放缓存，避免对原始大图重复操作。
  - 水印层预渲染（文本转位图一次），重复合成时复用。
  - 批量导出并发度可配置（默认 CPU 核数-1）。
- 颜色与 DPI：尊重 EXIF 方向；可选读取 DPI 信息（导出时保持）。

## 11. 打包与部署

- 依赖：`PySide6`, `Pillow`, `piexif`（可选 EXIF 读写）。
- 打包：
  - 使用 `PyInstaller`：`pyinstaller -F -w app/main.py -n WKXPhotoWaterMark2`。
  - 资源文件（图标、默认模板）通过 `--add-data` 打入包内或安装目录。
- 更新策略：提供版本号与检查更新（可选后续迭代）。

## 12. 目录结构建议

```
WKXPhotoWaterMark2/
├─ app/
│  ├─ main.py               # 入口
│  ├─ ui/                   # 界面
│  │  ├─ main_window.py
│  │  ├─ preview_view.py    # QGraphicsView
│  │  ├─ controls/          # 右侧面板
│  │  └─ widgets/
│  ├─ services/
│  │  ├─ importer.py
│  │  ├─ exporter.py
│  │  ├─ templates.py
│  │  └─ thumbnails.py
│  ├─ engine/
│  │  ├─ text_watermark.py
│  │  ├─ image_watermark.py
│  │  └─ compositor.py
│  ├─ models/
│  │  ├─ config.py
│  │  └─ enums.py
│  ├─ store/
│  │  ├─ paths.py
│  │  └─ settings.py
│  └─ utils/
│     ├─ exif.py
│     ├─ image.py
│     └─ logging.py
├─ docs/
│  └─ spec.md               # 本文档
├─ requirements.txt
└─ README.md
```

## 13. 测试与验收

- 单元测试：
  - 渲染层：文本/图片水印合成的像素校验（核心函数）。
  - 命名规则：不同模式输出文件名。
  - 模板序列化/反序列化：字段完整性与默认值。
- 集成测试：
  - 批量导入与导出流程，包含异常与取消。
  - 预览交互：拖拽、旋转、透明度更改即时生效。
- 验收标准（示例）：
  - 输入输出格式满足规格；PNG 透明正确；JPEG 质量生效。
  - 九宫格与手动定位准确；旋转角度应用无锯齿（合理抗锯齿）。
  - 模板保存/加载稳定；重启自动恢复最后设置。
  - 批量导出在 500 张 4K 图片下可在可接受时间内完成（并发与进度反馈正常）。

## 14. 开发里程碑

1) M1：项目初始化与主界面骨架（列表/预览/面板）。
2) M2：导入与缩略图、基本预览。
3) M3：文本水印（内容、位置、透明度）、实时预览。
4) M4：导出（格式/命名/JPEG 质量）。
5) M5：模板管理与自动加载。
6) M6：图片水印与旋转/样式（高级）。
7) M7：性能优化、日志与打包发布。

## 15. 风险与边界

- 超大 TIFF/CMYK 色彩空间的兼容性：优先读取为 `RGBA`，复杂色彩管理暂不支持。
- 字体渲染一致性：不同系统字体文件差异，需提供回退机制并提示。
- 许可与商标：用户提供的素材版权风险由用户自担。

——

附：快速环境准备（示例）

```
python -m venv .venv
.venv\Scripts\activate
pip install PySide6 Pillow piexif pyinstaller
```

后续开发按第 14 节里程碑推进，以本规格为实现和验收基准。