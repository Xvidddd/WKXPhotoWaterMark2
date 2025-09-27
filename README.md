# WKX Photo Watermark

本项目是一个基于 Python 的 Windows 本地图片加水印工具，使用 PySide6 构建桌面界面，Pillow 进行图像处理。

## 环境准备

建议使用 Conda 环境（已提供 `environment.yml` 与 `requirements.txt`）。

```bash
conda create -n wkx-photo-watermark python=3.11 -y
conda run -n wkx-photo-watermark pip install -r requirements.txt
```

或使用 `environment.yml`（可选）：

```bash
conda env create -f environment.yml
```

## 运行

激活环境后运行：

```bash
conda activate wkx-photo-watermark
python app/main.py
```

首次启动将看到主窗口，支持从菜单“文件→导入图片”选择并预览单张图片。

## 项目结构（当前）

```
app/
  main.py              # 入口
  ui/
    main_window.py     # 主窗口（文件菜单、预览区域）
    preview_view.py    # 预览视图（加载图片）
docs/
  spec.md              # 产品与技术规格
requirements.txt
environment.yml
README.md
```

## 后续计划

- 按 `docs/spec.md` 里程碑逐步实现：
  - 图片列表与缩略图、拖拽导入
  - 文本水印实时预览与参数面板
  - 导出功能（格式、命名、JPEG质量）
  - 模板管理与自动加载