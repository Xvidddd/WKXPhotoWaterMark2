from PySide6.QtGui import QPixmap, QFont, QColor, QTransform, QFontDatabase, QImage, QPainter, QFontMetricsF, QPen
from PySide6.QtCore import Qt, QRect
from PySide6.QtWidgets import (
    QGraphicsScene,
    QGraphicsView,
    QGraphicsPixmapItem,
    QGraphicsTextItem,
    QGraphicsItem,
    QGraphicsDropShadowEffect,
)
import shiboken6


class StrokedTextItem(QGraphicsTextItem):
    """带描边效果的文本项"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.stroke_width = 0
        self.stroke_color = QColor(255, 255, 255)
    
    def set_stroke(self, width, color):
        """设置描边宽度和颜色"""
        self.stroke_width = width
        self.stroke_color = color
        self.update()
    
    def paint(self, painter, option, widget=None):
        """重写绘制方法以添加描边效果"""
        if self.stroke_width > 0:
            # 保存原始设置
            original_pen = painter.pen()
            original_brush = painter.brush()
            
            # 获取文本路径
            path = self.textPath()
            
            # 绘制描边 - 使用较粗的笔绘制路径轮廓
            stroke_pen = QPen(self.stroke_color, self.stroke_width * 2)
            stroke_pen.setJoinStyle(Qt.RoundJoin)
            stroke_pen.setCapStyle(Qt.RoundCap)
            painter.setPen(stroke_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)
            
            # 绘制文本填充
            painter.setPen(Qt.NoPen)
            painter.setBrush(self.defaultTextColor())
            painter.drawPath(path)
            
            # 恢复原始设置
            painter.setPen(original_pen)
            painter.setBrush(original_brush)
        else:
            # 没有描边时使用默认绘制
            super().paint(painter, option, widget)
    
    def boundingRect(self):
        """重写边界矩形以包含描边"""
        rect = super().boundingRect()
        if self.stroke_width > 0:
            # 为描边预留额外空间
            extra = self.stroke_width
            rect = rect.adjusted(-extra, -extra, extra, extra)
        return rect
    
    def textPath(self):
        """获取文本路径"""
        from PySide6.QtGui import QPainterPath
        path = QPainterPath()
        font = self.font()
        text = self.toPlainText()
        # 使用QFontMetricsF获取更准确的基线位置
        metrics = QFontMetricsF(font)
        baseline_y = metrics.ascent()
        path.addText(0, baseline_y, font, text)
        return path


class PreviewView(QGraphicsView):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHints(self.renderHints())
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self._image_item: QGraphicsPixmapItem | None = None
        self._wm_item: QGraphicsTextItem | None = None
        self._wm_settings: dict | None = None
        # 缩放相关状态
        self._zoom: float = 1.0
        self._user_zoom_active: bool = False
        self._zoom_step: float = 1.25
        self._min_zoom: float = 0.1
        self._max_zoom: float = 10.0
        self._base_transform: QTransform = QTransform()
        self._dragging_wm: bool = False

    def load_image(self, file_path: str) -> bool:
        pix = QPixmap(file_path)
        if pix.isNull():
            return False
        self._scene.clear()
        # 清空场景后，之前的水印项会被删除，避免悬空引用
        self._wm_item = None
        self._image_item = QGraphicsPixmapItem(pix)
        self._scene.addItem(self._image_item)
        self._scene.setSceneRect(pix.rect())
        # 加载图片后重置缩放为适配视图
        self.reset_zoom()
        # 加载图片后刷新水印显示
        self._apply_watermark()
        return True

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 当窗口或视图大小变化时，保持图像按比例适配
        rect = self._scene.sceneRect()
        if not rect.isNull():
            if not self._user_zoom_active:
                # 非用户缩放：更新适配并记录基准变换
                self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
                self._base_transform = self.transform()
                self._zoom = 1.0
            else:
                # 用户缩放：窗口变化后重新计算基准，再叠加用户缩放
                self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
                self._base_transform = self.transform()
                self._apply_transform()

    def set_watermark_settings(self, settings: dict) -> None:
         # 保存当前的自定义位置信息（如果存在）
         custom_position_data = {}
         if self._wm_settings and self._wm_settings.get("position") == "custom":
             # 保存所有自定义位置相关的数据
             for key in ["pos_x", "pos_y", "pos_x_pct", "pos_y_pct"]:
                 if key in self._wm_settings:
                     custom_position_data[key] = self._wm_settings[key]
         
         # 更新设置
         self._wm_settings = settings
         
         # 仅当新设置明确为 custom，且未提供坐标时，才恢复之前的自定义坐标
         if self._wm_settings.get("position") == "custom" and custom_position_data:
             for key in ["pos_x", "pos_y", "pos_x_pct", "pos_y_pct"]:
                 if key not in self._wm_settings and key in custom_position_data:
                     self._wm_settings[key] = custom_position_data[key]
         
         self._apply_watermark()

    def _apply_watermark(self) -> None:
        # 防御：如果场景清空导致旧对象已被销毁，但成员仍保留引用，重置为 None
        if self._wm_item is not None and not shiboken6.isValid(self._wm_item):
            self._wm_item = None
        if not self._wm_settings or not self._wm_settings.get("text"):
            # 无文本或设置，移除水印项
            if self._wm_item is not None:
                self._scene.removeItem(self._wm_item)
                self._wm_item = None
            return
        if self._image_item is None:
            return

        text = self._wm_settings.get("text", "")
        font_size = int(self._wm_settings.get("font_size", 32))
        opacity = float(self._wm_settings.get("opacity", 0.6))
        margin = int(self._wm_settings.get("margin", 20))
        position = self._wm_settings.get("position", "bottom_right")
        color = self._wm_settings.get("color", QColor(0, 0, 0))
        if not isinstance(color, QColor):
            color = QColor(0, 0, 0)
    
        # 读取阴影与描边配置
        shadow_enabled = bool(self._wm_settings.get("shadow_enabled", False))
        shadow_offset = int(self._wm_settings.get("shadow_offset", 2))
        shadow_blur = int(self._wm_settings.get("shadow_blur", 5))
        shadow_color = self._wm_settings.get("shadow_color", QColor(0, 0, 0))
        if not isinstance(shadow_color, QColor):
            shadow_color = QColor(0, 0, 0)
        stroke_enabled = bool(self._wm_settings.get("stroke_enabled", False))
        stroke_width = int(self._wm_settings.get("stroke_width", 2))
        stroke_color = self._wm_settings.get("stroke_color", QColor(255, 255, 255))
        if not isinstance(stroke_color, QColor):
            stroke_color = QColor(255, 255, 255)

        # 读取字体族与样式（应用用户选择的字体）
        font_family = self._wm_settings.get("font_family", "")
        font_bold = bool(self._wm_settings.get("font_bold", False))
        font_italic = bool(self._wm_settings.get("font_italic", False))

        # 新建项标志：用于区分场景清空后新创建的水印项是否应直接使用旧位置
        just_created = False

        # 创建或更新水印项
        if self._wm_item is None:
            if stroke_enabled:
                self._wm_item = StrokedTextItem()
                self._wm_item.set_stroke(stroke_width, stroke_color)
            else:
                self._wm_item = QGraphicsTextItem()
            self._wm_item.setZValue(1001)
            self._wm_item.setFlags(
                QGraphicsItem.GraphicsItemFlag.ItemIsMovable
                | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            )
            self._wm_item.setAcceptHoverEvents(True)
            self._scene.addItem(self._wm_item)
            # 标记为刚创建，用于后续位置恢复逻辑
            just_created = True

        self._wm_item.setPlainText(text)
        
        # 设置字体
        if font_family:
            font = QFont(font_family)
        else:
            font = QFontDatabase.systemFont(QFontDatabase.GeneralFont)
        font.setPointSize(font_size)
        font.setBold(font_bold)
        font.setItalic(font_italic)
        self._wm_item.setFont(font)
        self._wm_item.setOpacity(opacity)
        if isinstance(color, QColor):
            self._wm_item.setDefaultTextColor(color)

        # 设置阴影效果
        if shadow_enabled:
            shadow_effect = QGraphicsDropShadowEffect()
            shadow_effect.setOffset(shadow_offset, shadow_offset)
            shadow_effect.setBlurRadius(shadow_blur)
            shadow_effect.setColor(shadow_color if isinstance(shadow_color, QColor) else QColor(0, 0, 0))
            self._wm_item.setGraphicsEffect(shadow_effect)
        else:
            self._wm_item.setGraphicsEffect(None)

        # 定义当前位置标志与当前位置
        current_is_custom = (self._wm_settings.get("position") == "custom")
        current_pos = self._wm_item.pos() if self._wm_item is not None else None

        # 如果有保存的位置且是自定义位置，恢复位置
        if current_is_custom:
            # 如果有当前位置且不是刚创建（避免默认(0,0)误判），直接使用
            if current_pos is not None and not just_created:
                self._wm_item.setPos(current_pos)
                # 更新设置中的位置信息
                self._wm_settings["position"] = "custom"
                self._wm_settings["pos_x"] = float(current_pos.x())
                self._wm_settings["pos_y"] = float(current_pos.y())
                # 计算百分比位置
                img_rect = self._scene.sceneRect()
                if img_rect.width() > 0 and img_rect.height() > 0:
                    self._wm_settings["pos_x_pct"] = float((current_pos.x() - img_rect.left()) / img_rect.width())
                    self._wm_settings["pos_y_pct"] = float((current_pos.y() - img_rect.top()) / img_rect.height())
                return
            # 如果没有当前位置但有保存的自定义位置，从设置中恢复
            elif "pos_x_pct" in self._wm_settings and "pos_y_pct" in self._wm_settings:
                img_rect = self._scene.sceneRect()
                pct_x = float(self._wm_settings.get("pos_x_pct", 0.0))
                pct_y = float(self._wm_settings.get("pos_y_pct", 0.0))
                x = img_rect.left() + pct_x * img_rect.width()
                y = img_rect.top() + pct_y * img_rect.height()
                self._wm_item.setPos(x, y)
                return
            elif "pos_x" in self._wm_settings and "pos_y" in self._wm_settings:
                x = float(self._wm_settings.get("pos_x", 0))
                y = float(self._wm_settings.get("pos_y", 0))
                self._wm_item.setPos(x, y)
                return
 
         # 否则按照位置设置计算新位置
         img_rect = self._scene.sceneRect()
         wm_rect = self._wm_item.boundingRect()
        
        # 为阴影和描边预留额外空间
        extra_margin = 0
        if shadow_enabled:
            extra_margin = max(extra_margin, shadow_offset + shadow_blur + 5)  # 额外增加5像素缓冲
        if stroke_enabled:
            extra_margin = max(extra_margin, stroke_width + 3)  # 额外增加3像素缓冲

        x = img_rect.left() + margin + extra_margin
        y = img_rect.top() + margin + extra_margin
        if position == "top_left":
            x = img_rect.left() + margin + extra_margin
            y = img_rect.top() + margin + extra_margin
        elif position == "top_right":
            x = img_rect.right() - wm_rect.width() - margin - extra_margin
            y = img_rect.top() + margin + extra_margin
        elif position == "bottom_left":
            x = img_rect.left() + margin + extra_margin
            y = img_rect.bottom() - wm_rect.height() - margin - extra_margin
        elif position == "bottom_right":
            x = img_rect.right() - wm_rect.width() - margin - extra_margin
            y = img_rect.bottom() - wm_rect.height() - margin - extra_margin
        elif position == "center":
            x = img_rect.center().x() - wm_rect.width() / 2
            y = img_rect.center().y() - wm_rect.height() / 2
        elif position == "top_center":
            x = img_rect.center().x() - wm_rect.width() / 2
            y = img_rect.top() + margin + extra_margin
        elif position == "bottom_center":
            x = img_rect.center().x() - wm_rect.width() / 2
            y = img_rect.bottom() - wm_rect.height() - margin - extra_margin
        elif position == "center_left":
            x = img_rect.left() + margin + extra_margin
            y = img_rect.center().y() - wm_rect.height() / 2
        elif position == "center_right":
            x = img_rect.right() - wm_rect.width() - margin - extra_margin
            y = img_rect.center().y() - wm_rect.height() / 2
        elif position == "custom":
            # 使用用户拖拽记录的位置：优先按百分比映射，不存在时回退像素
            if "pos_x_pct" in self._wm_settings and "pos_y_pct" in self._wm_settings:
                pct_x = float(self._wm_settings.get("pos_x_pct", 0.0))
                pct_y = float(self._wm_settings.get("pos_y_pct", 0.0))
                cx = img_rect.left() + pct_x * img_rect.width()
                cy = img_rect.top() + pct_y * img_rect.height()
            else:
                cx = float(self._wm_settings.get("pos_x", img_rect.left() + margin))
                cy = float(self._wm_settings.get("pos_y", img_rect.top() + margin))
            min_x = img_rect.left() + margin + extra_margin
            min_y = img_rect.top() + margin + extra_margin
            max_x = img_rect.right() - wm_rect.width() - margin - extra_margin
            max_y = img_rect.bottom() - wm_rect.height() - margin - extra_margin
            x = max(min_x, min(max_x, cx))
            y = max(min_y, min(max_y, cy))

        # 设置文本位置
        self._wm_item.setPos(x, y)

    # ===== 缩放相关API =====
    def _apply_transform(self) -> None:
        t = QTransform()
        t.scale(self._zoom, self._zoom)
        self.setTransform(self._base_transform * t)

    def zoom_in(self) -> None:
        if self._image_item is None:
            return
        self._zoom = min(self._zoom * self._zoom_step, self._max_zoom)
        self._user_zoom_active = True
        self._apply_transform()

    def zoom_out(self) -> None:
        if self._image_item is None:
            return
        self._zoom = max(self._zoom / self._zoom_step, self._min_zoom)
        self._user_zoom_active = True
        self._apply_transform()

    def reset_zoom(self) -> None:
        # 回到适配窗口显示，并更新基准变换
        rect = self._scene.sceneRect()
        if not rect.isNull():
            self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
            self._base_transform = self.transform()
        self._zoom = 1.0
        self._user_zoom_active = False
        # 明确应用基准变换，确保视觉上回到“适配窗口”
        self.setTransform(self._base_transform)

    def wheelEvent(self, event):
        # Ctrl + 滚轮进行缩放，其余交由默认行为
        if event.modifiers() & Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    # ===== 鼠标事件：仅点击水印时允许拖拽水印，其他保持图片平移 =====
    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        # 如果点中水印，则临时关闭视图拖拽，交由水印自身拖拽
        if item is not None and self._wm_item is not None and item is self._wm_item:
            self._dragging_wm = True
            self.setDragMode(QGraphicsView.NoDrag)
        else:
            self._dragging_wm = False
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self._dragging_wm and self._wm_item is not None and shiboken6.isValid(self._wm_item):
            pos = self._wm_item.pos()
            # 将当前位置写入设置为自定义，便于导出一致
            if self._wm_settings is None:
                self._wm_settings = {}
            self._wm_settings["position"] = "custom"
            self._wm_settings["pos_x"] = float(pos.x())
            self._wm_settings["pos_y"] = float(pos.y())
            # 同时记录相对百分比，便于跨不同尺寸图片保持相对位置
            rect = self._scene.sceneRect()
            if rect.width() > 0 and rect.height() > 0:
                self._wm_settings["pos_x_pct"] = float((pos.x() - rect.left()) / rect.width())
                self._wm_settings["pos_y_pct"] = float((pos.y() - rect.top()) / rect.height())
        # 释放后恢复视图拖拽模式
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self._dragging_wm = False

    # ===== 导出合成 =====
    def compose_qimage(self):
        if self._image_item is None or not self._wm_settings:
            return None
        pix: QPixmap = self._image_item.pixmap()
        if pix.isNull():
            return None
        img: QImage = pix.toImage().convertToFormat(QImage.Format_ARGB32)

        text = self._wm_settings.get("text", "")
        if not text:
            return img
        font_size = int(self._wm_settings.get("font_size", 32))
        opacity = float(self._wm_settings.get("opacity", 0.6))
        margin = int(self._wm_settings.get("margin", 20))
        position = self._wm_settings.get("position", "bottom_right")
        color = self._wm_settings.get("color", QColor(0, 0, 0))
        if not isinstance(color, QColor):
            color = QColor(0, 0, 0)
    
        # 读取阴影与描边配置
        shadow_enabled = bool(self._wm_settings.get("shadow_enabled", False))
        shadow_offset = int(self._wm_settings.get("shadow_offset", 2))
        shadow_blur = int(self._wm_settings.get("shadow_blur", 5))
        shadow_color = self._wm_settings.get("shadow_color", QColor(0, 0, 0))
        if not isinstance(shadow_color, QColor):
            shadow_color = QColor(0, 0, 0)
        stroke_enabled = bool(self._wm_settings.get("stroke_enabled", False))
        stroke_width = int(self._wm_settings.get("stroke_width", 2))
        stroke_color = self._wm_settings.get("stroke_color", QColor(255, 255, 255))
        if not isinstance(stroke_color, QColor):
            stroke_color = QColor(255, 255, 255)

        # 构造字体（应用用户选择的字体族与样式）
        font_family = self._wm_settings.get("font_family", "")
        font_bold = bool(self._wm_settings.get("font_bold", False))
        font_italic = bool(self._wm_settings.get("font_italic", False))
        if font_family:
            font = QFont(font_family)
        else:
            font = QFontDatabase.systemFont(QFontDatabase.GeneralFont)
        font.setPointSize(font_size)
        font.setBold(font_bold)
        font.setItalic(font_italic)
    
        # 用场景渲染文本（包含阴影与描边），生成透明文本图层
        text_scene = QGraphicsScene()
        if stroke_enabled:
            text_item = StrokedTextItem()
            text_item.set_stroke(stroke_width, stroke_color)
        else:
            text_item = QGraphicsTextItem()
        text_item.setPlainText(text)
        text_item.setDefaultTextColor(color)
        text_item.setFont(font)
        text_item.setOpacity(opacity)
        if shadow_enabled:
            eff = QGraphicsDropShadowEffect()
            eff.setOffset(shadow_offset, shadow_offset)
            eff.setBlurRadius(shadow_blur)
            eff.setColor(shadow_color)
            text_item.setGraphicsEffect(eff)
        text_scene.addItem(text_item)
        # 计算文本场景的包围矩形（包含阴影扩展）
        text_rect = text_scene.itemsBoundingRect()
        text_scene.setSceneRect(text_rect)
        text_img = QImage(int(text_rect.width()), int(text_rect.height()), QImage.Format_ARGB32)
        text_img.fill(QColor(0, 0, 0, 0))
        painter_layer = QPainter(text_img)
        # 将文本项移动使其从(0,0)开始渲染
        text_item.setPos(text_item.pos() - text_rect.topLeft())
        text_scene.render(painter_layer)
        painter_layer.end()

        # 位置计算：支持枚举位置与自定义坐标（使用文本图层尺寸）
        painter = QPainter(img)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        text_w = text_img.width()
        text_h = text_img.height()
        if position == "custom":
            # 优先使用百分比映射位置；回退到像素坐标
            if "pos_x_pct" in self._wm_settings and "pos_y_pct" in self._wm_settings:
                cx = float(self._wm_settings.get("pos_x_pct", 0.0)) * img.width()
                cy = float(self._wm_settings.get("pos_y_pct", 0.0)) * img.height()
            else:
                cx = float(self._wm_settings.get("pos_x", margin))
                cy = float(self._wm_settings.get("pos_y", margin))
            # 夹紧范围到内容区域（避免文字溢出右下边界）
            min_x = margin
            min_y = margin
            max_x = img.width() - margin - text_w
            max_y = img.height() - margin - text_h
            x = max(min_x, min(max_x, cx))
            y = max(min_y, min(max_y, cy))
            painter.drawImage(int(x), int(y), text_img)
        else:
            # 使用内容区域 + 对齐绘制
            content_rect = img.rect().adjusted(margin, margin, -margin, -margin)
            if position == "top_left":
                x = content_rect.left()
                y = content_rect.top()
            elif position == "top_right":
                x = content_rect.right() - text_w
                y = content_rect.top()
            elif position == "bottom_left":
                x = content_rect.left()
                y = content_rect.bottom() - text_h
            elif position == "bottom_right":
                x = content_rect.right() - text_w
                y = content_rect.bottom() - text_h
            elif position == "top_center":
                x = content_rect.center().x() - text_w // 2
                y = content_rect.top()
            elif position == "bottom_center":
                x = content_rect.center().x() - text_w // 2
                y = content_rect.bottom() - text_h
            elif position == "center_left":
                x = content_rect.left()
                y = content_rect.center().y() - text_h // 2
            elif position == "center_right":
                x = content_rect.right() - text_w
                y = content_rect.center().y() - text_h // 2
            else:  # center
                x = content_rect.center().x() - text_w // 2
                y = content_rect.center().y() - text_h // 2
            painter.drawImage(int(x), int(y), text_img)
        painter.end()
        return img

    def compose_qimage_for_path(self, path: str, settings: dict | None = None):
        # 离屏合成：直接从文件读取为 QImage 并绘制水印
        if not path:
            return None
        img = QImage(path)
        if img.isNull():
            return None
        img = img.convertToFormat(QImage.Format_ARGB32)

        wm = settings or self._wm_settings or {}
        text = wm.get("text", "")
        if not text:
            return img
        font_size = int(wm.get("font_size", 32))
        opacity = float(wm.get("opacity", 0.6))
        margin = int(wm.get("margin", 20))
        position = wm.get("position", "bottom_right")
        color = wm.get("color", QColor(0, 0, 0))
        if not isinstance(color, QColor):
            color = QColor(0, 0, 0)

        # 读取阴影与描边配置
        shadow_enabled = bool(wm.get("shadow_enabled", False))
        shadow_offset = int(wm.get("shadow_offset", 2))
        shadow_blur = int(wm.get("shadow_blur", 5))
        shadow_color = wm.get("shadow_color", QColor(0, 0, 0))
        if not isinstance(shadow_color, QColor):
            shadow_color = QColor(0, 0, 0)
        stroke_enabled = bool(wm.get("stroke_enabled", False))
        stroke_width = int(wm.get("stroke_width", 2))
        stroke_color = wm.get("stroke_color", QColor(255, 255, 255))
        if not isinstance(stroke_color, QColor):
            stroke_color = QColor(255, 255, 255)

        # 构造字体（应用用户选择的字体族与样式）
        font_family = wm.get("font_family", "")
        font_bold = bool(wm.get("font_bold", False))
        font_italic = bool(wm.get("font_italic", False))
        if font_family:
            font = QFont(font_family)
        else:
            font = QFontDatabase.systemFont(QFontDatabase.GeneralFont)
        font.setPointSize(font_size)
        font.setBold(font_bold)
        font.setItalic(font_italic)

        # 用场景渲染文本（包含阴影与描边），生成透明文本图层
        text_scene = QGraphicsScene()
        if stroke_enabled:
            text_item = StrokedTextItem()
            text_item.set_stroke(stroke_width, stroke_color)
        else:
            text_item = QGraphicsTextItem()
        text_item.setPlainText(text)
        text_item.setDefaultTextColor(color)
        text_item.setFont(font)
        text_item.setOpacity(opacity)
        if shadow_enabled:
            eff = QGraphicsDropShadowEffect()
            eff.setOffset(shadow_offset, shadow_offset)
            eff.setBlurRadius(shadow_blur)
            eff.setColor(shadow_color)
            text_item.setGraphicsEffect(eff)
        text_scene.addItem(text_item)
        text_rect = text_scene.itemsBoundingRect()
        text_scene.setSceneRect(text_rect)
        text_img = QImage(int(text_rect.width()), int(text_rect.height()), QImage.Format_ARGB32)
        text_img.fill(QColor(0, 0, 0, 0))
        painter_layer = QPainter(text_img)
        text_item.setPos(text_item.pos() - text_rect.topLeft())
        text_scene.render(painter_layer)
        painter_layer.end()

        # 位置计算与绘制
        painter = QPainter(img)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        text_w = text_img.width()
        text_h = text_img.height()
        if position == "custom":
            if "pos_x_pct" in wm and "pos_y_pct" in wm:
                cx = float(wm.get("pos_x_pct", 0.0)) * img.width()
                cy = float(wm.get("pos_y_pct", 0.0)) * img.height()
            else:
                cx = float(wm.get("pos_x", margin))
                cy = float(wm.get("pos_y", margin))
            min_x = margin
            min_y = margin
            max_x = img.width() - margin - text_w
            max_y = img.height() - margin - text_h
            x = max(min_x, min(max_x, cx))
            y = max(min_y, min(max_y, cy))
            painter.drawImage(int(x), int(y), text_img)
        else:
            content_rect = img.rect().adjusted(margin, margin, -margin, -margin)
            if position == "top_left":
                x = content_rect.left()
                y = content_rect.top()
            elif position == "top_right":
                x = content_rect.right() - text_w
                y = content_rect.top()
            elif position == "bottom_left":
                x = content_rect.left()
                y = content_rect.bottom() - text_h
            elif position == "bottom_right":
                x = content_rect.right() - text_w
                y = content_rect.bottom() - text_h
            elif position == "top_center":
                x = content_rect.center().x() - text_w // 2
                y = content_rect.top()
            elif position == "bottom_center":
                x = content_rect.center().x() - text_w // 2
                y = content_rect.bottom() - text_h
            elif position == "center_left":
                x = content_rect.left()
                y = content_rect.center().y() - text_h // 2
            elif position == "center_right":
                x = content_rect.right() - text_w
                y = content_rect.center().y() - text_h // 2
            else:
                x = content_rect.center().x() - text_w // 2
                y = content_rect.center().y() - text_h // 2
            painter.drawImage(int(x), int(y), text_img)
        painter.end()
        return img