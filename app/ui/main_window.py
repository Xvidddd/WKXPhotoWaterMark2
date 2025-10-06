from pathlib import Path
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QKeySequence, QIcon, QPixmap
from PySide6.QtWidgets import (
    QMainWindow,
    QFileDialog,
    QMessageBox,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QDockWidget,
    QInputDialog,
    QScrollArea,
)

from .preview_view import PreviewView
from .watermark_panel import WatermarkPanel
from .export_panel import ExportPanel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("WKX Photo Watermark")
        self.resize(1000, 700)
        
        # 左侧图片列表 + 右侧预览
        self.list_widget = QListWidget(self)
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.list_widget.setAcceptDrops(True)
        self.list_widget.setDragDropMode(QListWidget.DragDropMode.DropOnly)
        self.list_widget.setAlternatingRowColors(True)
        # 为左侧列表项显示缩略图（提高密度：更小图标）
        self.list_widget.setIconSize(QSize(48, 48))
        # 统一高度，避免文本换行导致的高度不一致
        self.list_widget.setUniformItemSizes(True)
        self.list_widget.setWordWrap(False)
        self.list_widget.setTextElideMode(Qt.TextElideMode.ElideRight)
        # 缩小行间距提高密度
        self.list_widget.setSpacing(2)

        self.preview = PreviewView(self)

        splitter = QSplitter(self)
        splitter.setOrientation(Qt.Orientation.Horizontal)
        splitter.addWidget(self.list_widget)
        splitter.addWidget(self.preview)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)

        # 右侧水印设置面板
        self.wm_panel = WatermarkPanel(self)
        dock = QDockWidget("水印设置", self)
        dock.setObjectName("DockWatermark")
        # 使用滚动区域包裹面板，避免内容过多时溢出屏幕
        wm_scroll = QScrollArea(self)
        wm_scroll.setWidgetResizable(True)
        wm_scroll.setWidget(self.wm_panel)
        dock.setWidget(wm_scroll)
        # 限制右侧面板最大宽度，避免长路径导致异常变宽
        dock.setMaximumWidth(380)
        
        # 导出设置面板
        self.export_panel = ExportPanel(self)
        export_dock = QDockWidget("导出设置", self)
        export_dock.setObjectName("DockExport")
        export_scroll = QScrollArea(self)
        export_scroll.setWidgetResizable(True)
        export_scroll.setWidget(self.export_panel)
        export_dock.setWidget(export_scroll)
        export_dock.setMaximumWidth(380)
        
        dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        
        export_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, export_dock)

        # 当前选中图片路径与每图自定义位置映射（会话内保存）
        self._current_image_path: str | None = None
        self._per_image_custom_pos: dict[str, dict] = {}

        self._setup_actions()
        self._setup_connections()
        
        # 启动时自动加载上次会话
        # 延迟调用，确保UI已完全初始化
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self._load_last_session_on_start)

    def _setup_actions(self) -> None:
        open_action = QAction("导入图片...", self)
        open_action.setStatusTip("选择并导入多张图片")
        open_action.triggered.connect(self._on_open_images)

        clear_action = QAction("清空列表", self)
        clear_action.setStatusTip("清除已导入的所有图片")
        clear_action.triggered.connect(self._on_clear_list)

        remove_action = QAction("移除选中", self)
        remove_action.setStatusTip("移除列表中选中的图片")
        remove_action.triggered.connect(self._on_remove_selected)

        export_action = QAction("导出当前图片...", self)
        export_action.setStatusTip("将当前预览图片导出为带水印文件")
        export_action.triggered.connect(self._on_export_current)

        export_all_action = QAction("批量导出全部图片...", self)
        export_all_action.setStatusTip("对列表中所有图片进行带水印导出到指定文件夹")
        export_all_action.triggered.connect(self._on_export_all)

        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)

        menu = self.menuBar().addMenu("文件")
        menu.addAction(open_action)
        menu.addSeparator()
        menu.addAction(remove_action)
        menu.addAction(clear_action)
        menu.addSeparator()
        menu.addAction(export_action)
        menu.addAction(export_all_action)
        menu.addSeparator()
        menu.addAction(exit_action)

        # 视图菜单：提供重新显示面板的入口
        view_menu = self.menuBar().addMenu("视图")
        view_menu.addAction(self.findChild(QDockWidget, "DockWatermark").toggleViewAction())
        view_menu.addAction(self.findChild(QDockWidget, "DockExport").toggleViewAction())
        # 缩放相关操作
        zoom_in_action = QAction("放大", self)
        # 兼容不同键盘布局：标准ZoomIn、Ctrl++、Ctrl+=
        zoom_in_action.setShortcuts([QKeySequence.ZoomIn, QKeySequence("Ctrl++"), QKeySequence("Ctrl+=")])
        zoom_in_action.setStatusTip("放大预览")
        zoom_in_action.triggered.connect(self.preview.zoom_in)

        zoom_out_action = QAction("缩小", self)
        # 规避重复映射引发的冲突，仅保留明确的主键盘与小键盘按键
        zoom_out_action.setShortcuts([
            QKeySequence("Ctrl-"),
            QKeySequence("Ctrl+Subtract"),
        ])
        zoom_out_action.setStatusTip("缩小预览")
        zoom_out_action.triggered.connect(self.preview.zoom_out)

        reset_zoom_action = QAction("重置缩放", self)
        reset_zoom_action.setShortcut("Ctrl+0")
        reset_zoom_action.setStatusTip("重置为按窗口适配")
        reset_zoom_action.triggered.connect(self.preview.reset_zoom)

        view_menu.addSeparator()
        view_menu.addAction(zoom_in_action)
        view_menu.addAction(zoom_out_action)
        view_menu.addAction(reset_zoom_action)

        # 模板菜单
        tpl_menu = self.menuBar().addMenu("模板")
        act_save_tpl = QAction("保存当前为模板...", self)
        act_save_tpl.setStatusTip("保存当前水印参数为模板")
        act_save_tpl.triggered.connect(self._on_save_template)
        act_load_tpl = QAction("加载模板...", self)
        act_load_tpl.setStatusTip("从模板列表选择并应用")
        act_load_tpl.triggered.connect(self._on_load_template)
        act_rename_tpl = QAction("重命名模板...", self)
        act_rename_tpl.setStatusTip("修改模板名称")
        act_rename_tpl.triggered.connect(self._on_rename_template)
        act_delete_tpl = QAction("删除模板...", self)
        act_delete_tpl.setStatusTip("删除选定模板")
        act_delete_tpl.triggered.connect(self._on_delete_template)
        tpl_menu.addAction(act_save_tpl)
        tpl_menu.addAction(act_load_tpl)
        tpl_menu.addAction(act_rename_tpl)
        tpl_menu.addAction(act_delete_tpl)

    def _setup_connections(self) -> None:
        self.list_widget.itemSelectionChanged.connect(self._on_list_selection_changed)
        self.wm_panel.settingsChanged.connect(self.preview.set_watermark_settings)
        # 拖拽释放后坐标改变信号：同步到所有图片
        self.preview.positionChanged.connect(self._on_preview_position_changed)

    def _on_open_images(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择图片",
            str(Path.home()),
            "图像文件 (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)"
        )
        if not files:
            return
        self._add_files_to_list(files)

    def _on_clear_list(self) -> None:
        self.list_widget.clear()

    def _on_remove_selected(self) -> None:
        row = self.list_widget.currentRow()
        if row >= 0:
            item = self.list_widget.takeItem(row)
            del item

    def _load_last_session_on_start(self):
        from app.services.templates import load_last_session
        
        # 尝试加载上次会话
        data = load_last_session()
        if data and hasattr(self, 'wm_panel') and hasattr(self, 'preview'):
            # 应用到面板与预览
            self.wm_panel.apply_settings(data)
            self.preview.set_watermark_settings(data)
    
    def _on_list_selection_changed(self) -> None:
        items = self.list_widget.selectedItems()
        if not items:
            return
        item = items[0]
        file_path = item.data(Qt.ItemDataRole.UserRole)
        # 首先保存之前图片的自定义位置（如果存在且为自定义）
        if self._current_image_path:
            prev = getattr(self.preview, "_wm_settings", None)
            if isinstance(prev, dict) and prev.get("position") == "custom":
                saved = {}
                # 像素坐标
                if "pos_x" in prev and "pos_y" in prev:
                    saved["pos_x"] = prev.get("pos_x")
                    saved["pos_y"] = prev.get("pos_y")
                # 百分比坐标
                if "pos_x_pct" in prev and "pos_y_pct" in prev:
                    saved["pos_x_pct"] = prev.get("pos_x_pct")
                    saved["pos_y_pct"] = prev.get("pos_y_pct")
                if saved:
                    self._per_image_custom_pos[self._current_image_path] = saved
        # 更新当前路径
        self._current_image_path = file_path
        
        if not self.preview.load_image(file_path):
            QMessageBox.warning(self, "加载失败", "无法加载所选图片，请检查格式或文件是否损坏。")
        else:
            # 列表选择变化后，重新应用当前水印设置
            panel_settings = self.wm_panel.get_settings()
            # 优先恢复该图片的自定义位置（若曾保存）
            saved_pos = self._per_image_custom_pos.get(file_path)
            if isinstance(saved_pos, dict):
                panel_settings["position"] = "custom"
                if "pos_x" in saved_pos and "pos_y" in saved_pos:
                    panel_settings["pos_x"] = saved_pos.get("pos_x")
                    panel_settings["pos_y"] = saved_pos.get("pos_y")
                if "pos_x_pct" in saved_pos and "pos_y_pct" in saved_pos:
                    panel_settings["pos_x_pct"] = saved_pos.get("pos_x_pct")
                    panel_settings["pos_y_pct"] = saved_pos.get("pos_y_pct")
            # 注意：仅当该图片确有自定义坐标时才强制 position=custom，否则保留面板当前的 position 设置
            self.preview.set_watermark_settings(panel_settings)

    def _add_files_to_list(self, files: list[str]) -> None:
        exts = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
        for f in files:
            p = Path(f)
            if not p.exists():
                continue
            if p.suffix.lower() not in exts:
                continue
            item = QListWidgetItem(p.name)
            item.setToolTip(str(p))
            item.setData(Qt.ItemDataRole.UserRole, str(p))
            # 生成缩略图作为图标（保持比例，平滑缩放）
            pix = QPixmap(str(p))
            if not pix.isNull():
                thumb = pix.scaled(self.list_widget.iconSize(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                item.setIcon(QIcon(thumb))
            # 设置统一的行高（更紧凑：图标高度 + 边距6）
            item.setSizeHint(QSize(0, self.list_widget.iconSize().height() + 6))
            self.list_widget.addItem(item)

    def _collect_current_settings(self) -> dict:
        # 从面板收集设置，并合并预览中的自定义位置（若存在）
        settings = self.wm_panel.get_settings()
        prev = getattr(self.preview, "_wm_settings", None)
        if isinstance(prev, dict) and prev.get("position") == "custom":
            settings["position"] = "custom"
            if "pos_x" in prev and "pos_y" in prev:
                settings["pos_x"] = prev.get("pos_x")
                settings["pos_y"] = prev.get("pos_y")
            if "pos_x_pct" in prev and "pos_y_pct" in prev:
                settings["pos_x_pct"] = prev.get("pos_x_pct")
                settings["pos_y_pct"] = prev.get("pos_y_pct")
        return settings



    def closeEvent(self, event) -> None:
        # 关闭时保存当前会话
        from app.services.templates import save_last_session
        data = self._collect_current_settings()
        save_last_session(data)
        super().closeEvent(event)

    def _on_save_template(self) -> None:
        from app.services.templates import save_template
        
        name, ok = QInputDialog.getText(self, "模板名称", "请输入模板名称：", text="默认模板")
        if not ok or not name.strip():
            return
            
        data = self._collect_current_settings()
        
        try:
            path = save_template(name.strip(), data)
            QMessageBox.information(self, "已保存", f"模板已保存：\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"保存模板时出错：\n{str(e)}")

    def _on_load_template(self) -> None:
        from app.services.templates import list_templates, load_template
        
        # 获取模板列表
        templates = list_templates()
        if not templates:
            QMessageBox.information(self, "无模板", "没有找到可用的模板。请先保存一个模板。")
            return
            
        # 显示模板选择对话框
        name, ok = QInputDialog.getItem(
            self, 
            "选择模板", 
            "请选择要加载的模板：", 
            templates, 
            0, 
            False
        )
        
        if not ok or not name:
            return
            
        # 加载模板
        data = load_template(name)
        if not data:
            QMessageBox.warning(self, "加载失败", f"无法加载模板：{name}")
            return
            
        # 应用到面板与预览
        self.wm_panel.apply_settings(data)
        self.preview.set_watermark_settings(data)
        
        # 使模板对所有图片生效：根据模板位置处理每张图片的自定义坐标
        if isinstance(data, dict):
            pos = data.get("position")
            if pos == "custom":
                saved: dict = {}
                if "pos_x_pct" in data and "pos_y_pct" in data:
                    try:
                        saved["pos_x_pct"] = float(data.get("pos_x_pct", 0.0))
                        saved["pos_y_pct"] = float(data.get("pos_y_pct", 0.0))
                    except Exception:
                        pass
                if "pos_x" in data and "pos_y" in data:
                    try:
                        saved["pos_x"] = int(data.get("pos_x", 0))
                        saved["pos_y"] = int(data.get("pos_y", 0))
                    except Exception:
                        pass
                # 将模板中的自定义坐标同步到所有图片
                if saved:
                    for i in range(self.list_widget.count()):
                        item = self.list_widget.item(i)
                        path = item.data(Qt.ItemDataRole.UserRole)
                        if path:
                            self._per_image_custom_pos[path] = dict(saved)
            else:
                # 非 custom 位置：清空所有图片的自定义坐标，确保九宫格等模板位置生效
                self._per_image_custom_pos.clear()
        
        QMessageBox.information(self, "已加载", f"模板已加载：\n{name}")

    def _on_rename_template(self) -> None:
         from app.services.templates import list_templates, rename_template
         names = list_templates()
         if not names:
             QMessageBox.information(self, "无模板", "尚未保存任何模板。")
             return
         old, ok = QInputDialog.getItem(self, "重命名模板", "选择模板：", names, 0, False)
         if not ok:
             return
         new, ok = QInputDialog.getText(self, "新的名称", "请输入新名称：", text=old)
         if not ok or not new.strip():
             return
         if rename_template(old, new.strip()):
             QMessageBox.information(self, "已重命名", f"模板已重命名为：{new.strip()}")
         else:
             QMessageBox.warning(self, "失败", "重命名失败（可能目标已存在）。")

    def _on_delete_template(self) -> None:
         from app.services.templates import list_templates, delete_template
         names = list_templates()
         if not names:
             QMessageBox.information(self, "无模板", "尚未保存任何模板。")
             return
         name, ok = QInputDialog.getItem(self, "删除模板", "选择模板：", names, 0, False)
         if not ok:
             return
         confirm = QMessageBox.question(self, "确认删除", f"确定删除模板\"{name}\"吗？")
         if confirm != QMessageBox.StandardButton.Yes:
             return
         if delete_template(name):
             QMessageBox.information(self, "已删除", "模板已删除。")
         else:
             QMessageBox.warning(self, "失败", "删除失败。")

    # 支持将文件从资源管理器直接拖入列表
    def dragEnterEvent(self, event):
        md = event.mimeData()
        if md.hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def _on_export_all(self) -> None:
        count = self.list_widget.count()
        if count == 0:
            QMessageBox.information(self, "无图片", "列表为空，请先导入图片。")
            return
        out_dir = QFileDialog.getExistingDirectory(self, "选择导出文件夹", str(Path.home()))
        if not out_dir:
            return

        # 获取导出设置
        export_settings = self.export_panel.get_settings()
        fmt = export_settings["format"]
        ext = ".png" if fmt == "PNG" else ".jpg"

        # 选择命名规则（保留原名/添加前缀/添加后缀）
        mode_label, ok = QInputDialog.getItem(
            self,
            "文件命名规则",
            "命名：",
            ["保留原文件名", "添加前缀", "添加后缀"],
            0,
            False,
        )
        if not ok:
            return
        mode = "keep"
        value = ""
        if mode_label == "添加前缀":
            mode = "prefix"
            value, ok = QInputDialog.getText(self, "输入前缀", "前缀：", text="wm_")
            if not ok:
                return
        elif mode_label == "添加后缀":
            mode = "suffix"
            value, ok = QInputDialog.getText(self, "输入后缀", "后缀：", text="_watermarked")
            if not ok:
                return

        # 使用合并了预览自定义位置的设置，确保批量导出与预览一致
        # 注意：需要为每张图片单独合并自定义坐标，避免所有图片共享同一坐标
        ok_count = 0
        fail_items: list[str] = []
        for i in range(count):
            item = self.list_widget.item(i)
            src_path = Path(item.data(Qt.ItemDataRole.UserRole))
            # 从面板获取基础水印参数
            per_settings = dict(self.wm_panel.get_settings())
            src_path_str = str(src_path)
            # 如果是当前预览图片且存在自定义坐标，优先使用当前预览中的坐标
            prev = getattr(self.preview, "_wm_settings", None)
            if (
                isinstance(prev, dict) and prev.get("position") == "custom" and
                self._current_image_path and src_path_str == self._current_image_path
            ):
                per_settings["position"] = "custom"
                if "pos_x" in prev and "pos_y" in prev:
                    per_settings["pos_x"] = prev.get("pos_x")
                    per_settings["pos_y"] = prev.get("pos_y")
                if "pos_x_pct" in prev and "pos_y_pct" in prev:
                    per_settings["pos_x_pct"] = prev.get("pos_x_pct")
                    per_settings["pos_y_pct"] = prev.get("pos_y_pct")
            else:
                # 否则，如果曾为该图片保存过自定义坐标，则合并之
                saved_pos = self._per_image_custom_pos.get(src_path_str)
                if isinstance(saved_pos, dict):
                    per_settings["position"] = "custom"
                    if "pos_x" in saved_pos and "pos_y" in saved_pos:
                        per_settings["pos_x"] = saved_pos.get("pos_x")
                        per_settings["pos_y"] = saved_pos.get("pos_y")
                    if "pos_x_pct" in saved_pos and "pos_y_pct" in saved_pos:
                        per_settings["pos_x_pct"] = saved_pos.get("pos_x_pct")
                        per_settings["pos_y_pct"] = saved_pos.get("pos_y_pct")
            img = self.preview.compose_qimage_for_path(src_path_str, per_settings)
            if img is None:
                fail_items.append(src_path.name)
                continue
                
            # 应用尺寸调整
            if export_settings["resize_mode"] != "none":
                resize_mode = export_settings["resize_mode"]
                resize_value = export_settings["resize_value"]
                
                # 获取原始尺寸
                original_width = img.width()
                original_height = img.height()
                
                if resize_mode == "width":
                    new_width = resize_value
                    new_height = int(original_height * (new_width / original_width))
                    img = img.scaled(new_width, new_height, Qt.AspectRatioMode.KeepAspectRatio)
                elif resize_mode == "height":
                    new_height = resize_value
                    new_width = int(original_width * (new_height / original_height))
                    img = img.scaled(new_width, new_height, Qt.AspectRatioMode.KeepAspectRatio)
                elif resize_mode == "percent":
                    scale_factor = resize_value / 100.0
                    new_width = int(original_width * scale_factor)
                    new_height = int(original_height * scale_factor)
                    img = img.scaled(new_width, new_height, Qt.AspectRatioMode.KeepAspectRatio)
                
            # 根据命名规则生成输出文件名
            stem = src_path.stem
            if mode == "prefix":
                new_name = f"{value}{stem}{ext}"
            elif mode == "suffix":
                new_name = f"{stem}{value}{ext}"
            else:
                new_name = f"{stem}{ext}"
            out_path = Path(out_dir) / new_name
            
            # 保存图片，应用JPEG质量设置
            if fmt == "JPEG":
                quality = export_settings["jpeg_quality"]
                if img.save(str(out_path), fmt, quality):
                    ok_count += 1
                else:
                    fail_items.append(src_path.name)
            else:
                if img.save(str(out_path), fmt):
                    ok_count += 1
                else:
                    fail_items.append(src_path.name)

        if fail_items:
            QMessageBox.warning(
                self,
                "部分导出失败",
                f"成功 {ok_count} 项，失败 {len(fail_items)} 项：\n" + "\n".join(fail_items)
            )
        else:
            QMessageBox.information(self, "导出完成", f"成功导出 {ok_count} 项到：\n{out_dir}")

    def dropEvent(self, event):
        md = event.mimeData()
        if md.hasUrls():
            files = []
            for url in md.urls():
                if url.isLocalFile():
                    files.append(url.toLocalFile())
            if files:
                self._add_files_to_list(files)
            event.acceptProposedAction()
        else:
            event.ignore()

    def _on_export_current(self) -> None:
        items = self.list_widget.selectedItems()
        if not items:
            QMessageBox.information(self, "无选中图片", "请先在左侧列表选择一张图片。")
            return
        item = items[0]
        src_path = Path(item.data(Qt.ItemDataRole.UserRole))

        composed = self.preview.compose_qimage()
        if composed is None:
            QMessageBox.warning(self, "无法导出", "当前没有可导出的预览内容或图片未加载。")
            return

        # 选择命名规则用于默认文件名
        mode_label, ok = QInputDialog.getItem(
            self,
            "文件命名规则",
            "命名：",
            ["保留原文件名", "添加前缀", "添加后缀"],
            0,
            False,
        )
        if not ok:
            return
        mode = "keep"
        value = ""
        if mode_label == "添加前缀":
            mode = "prefix"
            value, ok = QInputDialog.getText(self, "输入前缀", "前缀：", text="wm_")
            if not ok:
                return
        elif mode_label == "添加后缀":
            mode = "suffix"
            value, ok = QInputDialog.getText(self, "输入后缀", "后缀：", text="_watermarked")
            if not ok:
                return

        # 获取导出设置
        export_settings = self.export_panel.get_settings()
        fmt = export_settings["format"]
        ext = ".png" if fmt == "PNG" else ".jpg"

        # 默认使用设置中的扩展名
        if mode == "prefix":
            default_name = f"{value}{src_path.stem}{ext}"
        elif mode == "suffix":
            default_name = f"{src_path.stem}{value}{ext}"
        else:
            default_name = f"{src_path.stem}{ext}"
            
        save_path_str, sel_filter = QFileDialog.getSaveFileName(
            self,
            "导出图片",
            str(src_path.with_name(default_name)),
            "PNG 图像 (*.png);;JPEG 图像 (*.jpg *.jpeg)"
        )
        if not save_path_str:
            return

        save_path = Path(save_path_str)
        fmt = "PNG"
        if save_path.suffix.lower() in {".jpg", ".jpeg"}:
            fmt = "JPEG"
            
        # 应用尺寸调整
        if export_settings["resize_mode"] != "none":
            resize_mode = export_settings["resize_mode"]
            resize_value = export_settings["resize_value"]
            
            # 获取原始尺寸
            original_width = composed.width()
            original_height = composed.height()
            
            if resize_mode == "width":
                new_width = resize_value
                new_height = int(original_height * (new_width / original_width))
                composed = composed.scaled(new_width, new_height, Qt.AspectRatioMode.KeepAspectRatio)
            elif resize_mode == "height":
                new_height = resize_value
                new_width = int(original_width * (new_height / original_height))
                composed = composed.scaled(new_width, new_height, Qt.AspectRatioMode.KeepAspectRatio)
            elif resize_mode == "percent":
                scale_factor = resize_value / 100.0
                new_width = int(original_width * scale_factor)
                new_height = int(original_height * scale_factor)
                composed = composed.scaled(new_width, new_height, Qt.AspectRatioMode.KeepAspectRatio)

        # 保存图片，应用JPEG质量设置
        if fmt == "JPEG":
            quality = export_settings["jpeg_quality"]
            ok = composed.save(str(save_path), fmt, quality)
        else:
            ok = composed.save(str(save_path), fmt)
            
        if ok:
            QMessageBox.information(self, "导出成功", f"已保存到：\n{save_path}")
        else:
            QMessageBox.warning(self, "导出失败", "保存文件失败，请检查路径或权限。")

    # 新增：预览拖拽位置改变后，同步所有图片坐标（百分比优先）
    def _on_preview_position_changed(self, payload: dict) -> None:
        if not isinstance(payload, dict):
            return
        saved: dict = {}
        if "pos_x_pct" in payload and "pos_y_pct" in payload:
            try:
                saved["pos_x_pct"] = float(payload.get("pos_x_pct", 0.0))
                saved["pos_y_pct"] = float(payload.get("pos_y_pct", 0.0))
            except Exception:
                pass
        # 同步像素坐标（作为兼容项）
        if "pos_x" in payload and "pos_y" in payload:
            try:
                saved["pos_x"] = int(payload.get("pos_x", 0))
                saved["pos_y"] = int(payload.get("pos_y", 0))
            except Exception:
                pass
        if not saved:
            return
        # 更新当前图片的坐标
        if self._current_image_path:
            self._per_image_custom_pos[self._current_image_path] = dict(saved)
        # 将坐标同步到列表中所有图片，确保切换图片时保持一致
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            path = item.data(Qt.ItemDataRole.UserRole)
            if path:
                self._per_image_custom_pos[path] = dict(saved)
        # 直接应用到预览（保持position=custom）
        apply_settings = dict(saved)
        apply_settings["position"] = "custom"
        self.preview.set_watermark_settings(apply_settings)