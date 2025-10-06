from PySide6.QtGui import QPixmap, QFont, QColor, QTransform, QFontDatabase, QImage, QPainter, QFontMetricsF, QPen
from PySide6.QtCore import Qt, QRect, Signal
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
    positionChanged = Signal(dict)
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHints(self.renderHints())
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self._image_item: QGraphicsPixmapItem | None = None
        self._wm_item: QGraphicsTextItem | None = None
        # 图片水印项与当前拖拽项
        self._wm_img_item: QGraphicsPixmapItem | None = None
        self._drag_item: QGraphicsItem | None = None
        self._wm_settings: dict | None = None
        # 缩放相关状态
        self._zoom: float = 1.0
        self._user_zoom_active: bool = False
        self._zoom_step: float = 1.25
        self._min_zoom: float = 0.1
        self._max_zoom: float = 10.0
        self._base_transform: QTransform = QTransform()
        self._dragging_wm: bool = False
        # 当前预览图片路径
        self._current_path: str | None = None

    def zoom_in(self) -> None:
        self._user_zoom_active = True
        self._zoom = min(self._max_zoom, self._zoom * self._zoom_step)
        self._apply_transform()


    def zoom_out(self) -> None:
        self._user_zoom_active = True
        self._zoom = max(self._min_zoom, self._zoom / self._zoom_step)
        self._apply_transform()


    def reset_zoom(self) -> None:
        rect = self._scene.sceneRect()
        if not rect.isNull():
            self._user_zoom_active = False
            self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
            self._base_transform = self.transform()
            self._zoom = 1.0


    def _apply_transform(self) -> None:
        t = QTransform(self._base_transform)
        t.scale(self._zoom, self._zoom)
        self.setTransform(t)


    def load_image(self, file_path: str) -> bool:
        pix = QPixmap(file_path)
        if pix.isNull():
            return False

        self._scene.clear()
        # 清空场景后，之前的水印项会被删除，避免悬空引用
        self._wm_item = None
        self._wm_img_item = None
        self._image_item = QGraphicsPixmapItem(pix)
        self._scene.addItem(self._image_item)
        self._scene.setSceneRect(pix.rect())
        # 记录当前图片路径，供导出当前使用
        self._current_path = file_path
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
         # 读取旧设置
         prev = self._wm_settings or {}

         # 以旧设置为基础进行合并，避免未提供的键被丢弃
         merged = dict(prev)
         for k, v in settings.items():
             merged[k] = v

         # 如果新设置未提供 position，则保留旧的 position
         if "position" not in settings and "position" in prev:
             merged["position"] = prev["position"]
         # 若最终位置为 custom：当新设置未提供坐标时，继承旧坐标（像素与百分比）
         if merged.get("position") == "custom":
             coord_keys = ["pos_x", "pos_y", "pos_x_pct", "pos_y_pct"]
             has_coords_in_new = any(k in settings for k in coord_keys)
             if not has_coords_in_new:
                 for k in coord_keys:
                     if k in prev and k not in merged:
                         merged[k] = prev[k]
         else:
             # 当位置切换到非 custom（如九宫格），清理旧的坐标字段避免干扰预览渲染
             for k in ["pos_x", "pos_y", "pos_x_pct", "pos_y_pct"]:
                 if k in merged:
                     merged.pop(k)

         # 应用合并后的设置
         self._wm_settings = merged
         self._apply_watermark()

    def _apply_watermark(self) -> None:
        # 防御：如果场景清空导致旧对象已被销毁，但成员仍保留引用，重置为 None
        if self._wm_item is not None and not shiboken6.isValid(self._wm_item):
            self._wm_item = None
        if self._wm_img_item is not None and not shiboken6.isValid(self._wm_img_item):
            self._wm_img_item = None
        if not self._wm_settings:
            # 无设置，移除所有水印项
            if self._wm_item is not None:
                self._scene.removeItem(self._wm_item)
                self._wm_item = None
            if self._wm_img_item is not None:
                self._scene.removeItem(self._wm_img_item)
                self._wm_img_item = None
            return
        if self._image_item is None:
            return

        wm_type = self._wm_settings.get("wm_type", "text")
        # 其余逻辑在后续代码中按类型分别处理

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

        # 创建或更新水印项（文本分支保留，图片分支在后续处理）
        if wm_type == "text":
            if not text:
                # 无文本则移除文本水印
                if self._wm_item is not None:
                    self._scene.removeItem(self._wm_item)
                    self._wm_item = None
                # 同时清理图片水印，避免残留
                if self._wm_img_item is not None:
                    self._scene.removeItem(self._wm_img_item)
                    self._wm_img_item = None
                return
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

            # 位置计算（文本水印）：支持枚举与自定义坐标/百分比
            img_rect = self._scene.sceneRect()
            wm_rect = self._wm_item.boundingRect().toRect()
            current_is_custom = (self._wm_settings.get("position") == "custom")
            current_pos = self._wm_item.pos() if self._wm_item is not None else None
            
        
            if current_is_custom:
                # 自定义位置：优先使用显式提供的坐标（百分比或像素），其次才保留现有位置
                img_rect = self._scene.sceneRect()
                wm_rect = self._wm_item.boundingRect().toRect()
                if "pos_x_pct" in self._wm_settings and "pos_y_pct" in self._wm_settings:
                    pct_x = float(self._wm_settings.get("pos_x_pct", 0.0))
                    pct_y = float(self._wm_settings.get("pos_y_pct", 0.0))
                    cx = img_rect.left() + pct_x * img_rect.width()
                    cy = img_rect.top() + pct_y * img_rect.height()
                    # 边界约束
                    min_x = img_rect.left() + margin
                    min_y = img_rect.top() + margin
                    max_x = img_rect.right() - wm_rect.width() - margin
                    max_y = img_rect.bottom() - wm_rect.height() - margin
                    x = max(min_x, min(max_x, cx))
                    y = max(min_y, min(max_y, cy))

                    # 对自定义坐标不使用 margin 约束，避免在切换图片或调整面板后位置被挤压
                    min_x = img_rect.left()
                    min_y = img_rect.top()
                    max_x = img_rect.right() - wm_rect.width()
                    max_y = img_rect.bottom() - wm_rect.height()
                    x = max(min_x, min(max_x, cx))
                    y = max(min_y, min(max_y, cy))

                    self._wm_item.setPos(x, y)
                elif "pos_x" in self._wm_settings and "pos_y" in self._wm_settings:
                    cx = float(self._wm_settings.get("pos_x", img_rect.left() + margin))
                    cy = float(self._wm_settings.get("pos_y", img_rect.top() + margin))
                    min_x = img_rect.left() + margin
                    min_y = img_rect.top() + margin
                    max_x = img_rect.right() - wm_rect.width() - margin
                    max_y = img_rect.bottom() - wm_rect.height() - margin
                    x = max(min_x, min(max_x, cx))
                    y = max(min_y, min(max_y, cy))

                    # 对自定义坐标不使用 margin 约束
                    min_x = img_rect.left()
                    min_y = img_rect.top()
                    max_x = img_rect.right() - wm_rect.width()
                    max_y = img_rect.bottom() - wm_rect.height()
                    x = max(min_x, min(max_x, cx))
                    y = max(min_y, min(max_y, cy))

                    self._wm_item.setPos(x, y)
                elif current_pos is not None and not just_created:

                    self._wm_item.setPos(current_pos)
                else:
                    # 无坐标且新创建，使用默认偏移
                    x = img_rect.left() + margin
                    y = img_rect.top() + margin
                    self._wm_item.setPos(x, y)
                # 预览渲染不写回坐标，避免在切换图片时覆盖用户自定义的百分比坐标
                # 保持 self._wm_settings 中的 pos_x/pos_y/pos_x_pct/pos_y_pct 不变，仅在拖拽结束时写回
            else:
                # 枚举位置
                x = img_rect.left() + margin
                y = img_rect.top() + margin
                if position == "top_left":
                    x = img_rect.left() + margin
                    y = img_rect.top() + margin
                elif position == "top_right":
                    x = img_rect.right() - wm_rect.width() - margin
                    y = img_rect.top() + margin
                elif position == "bottom_left":
                    x = img_rect.left() + margin
                    y = img_rect.bottom() - wm_rect.height() - margin
                elif position == "bottom_right":
                    x = img_rect.right() - wm_rect.width() - margin
                    y = img_rect.bottom() - wm_rect.height() - margin
                elif position == "center":
                    x = img_rect.center().x() - wm_rect.width() / 2
                    y = img_rect.center().y() - wm_rect.height() / 2
                elif position == "top_center":
                    x = img_rect.center().x() - wm_rect.width() / 2
                    y = img_rect.top() + margin
                elif position == "bottom_center":
                    x = img_rect.center().x() - wm_rect.width() / 2
                    y = img_rect.bottom() - wm_rect.height() - margin
                elif position == "center_left":
                    x = img_rect.left() + margin
                    y = img_rect.center().y() - wm_rect.height() / 2
                elif position == "center_right":
                    x = img_rect.right() - wm_rect.width() - margin
                    y = img_rect.center().y() - wm_rect.height() / 2
                else:  # center
                    x = img_rect.center().x() - wm_rect.width() / 2
                    y = img_rect.center().y() - wm_rect.height() / 2
                self._wm_item.setPos(x, y)
            # 图片水印项在文本模式下移除
            if self._wm_img_item is not None:
                self._scene.removeItem(self._wm_img_item)
                self._wm_img_item = None
        # 图片水印分支
        else:
            img_path = self._wm_settings.get("image_path", "")
            if not img_path:
                # 无图片路径，移除图片水印
                if self._wm_img_item is not None:
                    self._scene.removeItem(self._wm_img_item)
                    self._wm_img_item = None
                # 文本项也清理
                if self._wm_item is not None:
                    self._scene.removeItem(self._wm_item)
                    self._wm_item = None
                return
            src_pix = QPixmap(img_path)
            if src_pix.isNull():
                # 无法加载图片，移除
                if self._wm_img_item is not None:
                    self._scene.removeItem(self._wm_img_item)
                    self._wm_img_item = None
                if self._wm_item is not None:
                    self._scene.removeItem(self._wm_item)
                    self._wm_item = None
                return
            # 读取图片透明度与缩放
            img_opacity = float(self._wm_settings.get("img_opacity", 0.6))
            scale_mode = self._wm_settings.get("img_scale_mode", "proportional")
            if scale_mode not in {"proportional", "free"}:
                scale_mode = "proportional"
            if self._wm_img_item is None:
                self._wm_img_item = QGraphicsPixmapItem()
                self._wm_img_item.setZValue(1001)
                self._wm_img_item.setFlags(
                    QGraphicsItem.GraphicsItemFlag.ItemIsMovable
                    | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
                )
                self._wm_img_item.setAcceptHoverEvents(True)
                self._scene.addItem(self._wm_img_item)
                just_created = True
            # 计算缩放后的像素图
            if scale_mode == "proportional":
                pct = int(self._wm_settings.get("img_scale_pct", 100))
                pct = max(1, min(1000, pct))
                new_w = max(1, int(src_pix.width() * pct / 100.0))
                new_h = max(1, int(src_pix.height() * pct / 100.0))
                wm_pix = src_pix.scaled(new_w, new_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.SmoothTransformation)
            else:
                target_w = int(self._wm_settings.get("img_width", src_pix.width()))
                target_h = int(self._wm_settings.get("img_height", src_pix.height()))
                target_w = max(1, target_w)
                target_h = max(1, target_h)
                wm_pix = src_pix.scaled(target_w, target_h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.SmoothTransformation)
            self._wm_img_item.setPixmap(wm_pix)
            self._wm_img_item.setOpacity(img_opacity)
            # 文本项在图片模式下移除
            if self._wm_item is not None:
                self._scene.removeItem(self._wm_item)
                self._wm_item = None
            # 恢复或计算位置
            current_is_custom = (self._wm_settings.get("position") == "custom")
            current_pos = self._wm_img_item.pos() if self._wm_img_item is not None else None
    
            if current_is_custom:
                if current_pos is not None and not just_created:
            
                    self._wm_img_item.setPos(current_pos)
                elif "pos_x_pct" in self._wm_settings and "pos_y_pct" in self._wm_settings:
                    img_rect = self._scene.sceneRect()
                    wm_rect = self._wm_img_item.boundingRect().toRect()
                    pct_x = float(self._wm_settings.get("pos_x_pct", 0.0))
                    pct_y = float(self._wm_settings.get("pos_y_pct", 0.0))
                    cx = img_rect.left() + pct_x * img_rect.width()
                    cy = img_rect.top() + pct_y * img_rect.height()
                    # 边界约束，保持与导出一致
                    min_x = img_rect.left() + margin
                    min_y = img_rect.top() + margin
                    max_x = img_rect.right() - wm_rect.width() - margin
                    max_y = img_rect.bottom() - wm_rect.height() - margin
                    x = max(min_x, min(max_x, cx))
                    y = max(min_y, min(max_y, cy))
            
                    # 自定义坐标不使用 margin 约束
                    min_x = img_rect.left()
                    min_y = img_rect.top()
                    max_x = img_rect.right() - wm_rect.width()
                    max_y = img_rect.bottom() - wm_rect.height()
                    x = max(min_x, min(max_x, cx))
                    y = max(min_y, min(max_y, cy))
            
                    self._wm_img_item.setPos(x, y)
                elif "pos_x" in self._wm_settings and "pos_y" in self._wm_settings:
                    img_rect = self._scene.sceneRect()
                    wm_rect = self._wm_img_item.boundingRect().toRect()
                    cx = float(self._wm_settings.get("pos_x", img_rect.left() + margin))
                    cy = float(self._wm_settings.get("pos_y", img_rect.top() + margin))
                    # 同样进行边界约束
                    min_x = img_rect.left() + margin
                    min_y = img_rect.top() + margin
                    max_x = img_rect.right() - wm_rect.width() - margin
                    max_y = img_rect.bottom() - wm_rect.height() - margin
                    x = max(min_x, min(max_x, cx))
                    y = max(min_y, min(max_y, cy))
            
                    # 自定义坐标不使用 margin 约束
                    min_x = img_rect.left()
                    min_y = img_rect.top()
                    max_x = img_rect.right() - wm_rect.width()
                    max_y = img_rect.bottom() - wm_rect.height()
                    x = max(min_x, min(max_x, cx))
                    y = max(min_y, min(max_y, cy))
            
                    self._wm_img_item.setPos(x, y)
                # 预览渲染不写回坐标，避免在切换图片时覆盖用户自定义的百分比坐标
                # 保持 self._wm_settings 中的 pos_x/pos_y/pos_x_pct/pos_y_pct 不变，仅在拖拽结束时写回
            else:
                img_rect = self._scene.sceneRect()
                wm_rect = self._wm_img_item.boundingRect().toRect()
                x = img_rect.left() + margin
                y = img_rect.top() + margin
                if position == "top_left":
                    x = img_rect.left() + margin
                    y = img_rect.top() + margin
                elif position == "top_right":
                    x = img_rect.right() - wm_rect.width() - margin
                    y = img_rect.top() + margin
                elif position == "bottom_left":
                    x = img_rect.left() + margin
                    y = img_rect.bottom() - wm_rect.height() - margin
                elif position == "bottom_right":
                    x = img_rect.right() - wm_rect.width() - margin
                    y = img_rect.bottom() - wm_rect.height() - margin
                elif position == "center":
                    x = img_rect.center().x() - wm_rect.width() / 2
                    y = img_rect.center().y() - wm_rect.height() / 2
                elif position == "top_center":
                    x = img_rect.center().x() - wm_rect.width() / 2
                    y = img_rect.top() + margin
                elif position == "bottom_center":
                    x = img_rect.center().x() - wm_rect.width() / 2
                    y = img_rect.bottom() - wm_rect.height() - margin
                elif position == "center_left":
                    x = img_rect.left() + margin
                    y = img_rect.center().y() - wm_rect.height() / 2
                elif position == "center_right":
                    x = img_rect.right() - wm_rect.width() - margin
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
                    min_x = img_rect.left() + margin
                    min_y = img_rect.top() + margin
                    max_x = img_rect.right() - wm_rect.width() - margin
                    max_y = img_rect.bottom() - wm_rect.height() - margin
                    x = max(min_x, min(max_x, cx))
                    y = max(min_y, min(max_y, cy))
                self._wm_img_item.setPos(x, y)

    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        # 如果点中任一水印，则临时关闭视图拖拽，交由水印自身拖拽
        if item is not None and (
            (self._wm_item is not None and item is self._wm_item) or
            (self._wm_img_item is not None and item is self._wm_img_item)
        ):
            self._dragging_wm = True
            self._drag_item = item
            self.setDragMode(QGraphicsView.NoDrag)
        else:
            self._dragging_wm = False
            self._drag_item = None
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self._dragging_wm and self._drag_item is not None and shiboken6.isValid(self._drag_item):
            pos = self._drag_item.pos()
            if self._wm_settings is None:
                self._wm_settings = {}
            self._wm_settings["position"] = "custom"
            self._wm_settings["pos_x"] = float(pos.x())
            self._wm_settings["pos_y"] = float(pos.y())
            rect = self._scene.sceneRect()
            if rect.width() > 0 and rect.height() > 0:
                self._wm_settings["pos_x_pct"] = float((pos.x() - rect.left()) / rect.width())
                self._wm_settings["pos_y_pct"] = float((pos.y() - rect.top()) / rect.height())
            # 发射位置变化信号，供主窗口同步到所有图片
            self.positionChanged.emit({
                "position": "custom",
                "pos_x": self._wm_settings.get("pos_x"),
                "pos_y": self._wm_settings.get("pos_y"),
                "pos_x_pct": self._wm_settings.get("pos_x_pct"),
                "pos_y_pct": self._wm_settings.get("pos_y_pct"),
            })
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self._dragging_wm = False
        self._drag_item = None

    def compose_qimage(self):
        """Compose current preview image with watermark based on the currently loaded file path.
        Returns QImage or None if no current image is loaded.
        """
        # 使用当前已加载图片路径进行离屏合成
        if hasattr(self, "_current_path") and self._current_path:
            return self.compose_qimage_for_path(self._current_path, None)
        return None

    def compose_qimage_for_path(self, path: str, settings: dict | None = None):
        # 离屏合成：直接从文件读取为 QImage 并绘制水印
        if not path:
            return None
        img = QImage(path)
        if img.isNull():
            return None
        img = img.convertToFormat(QImage.Format_ARGB32)

        wm = settings or self._wm_settings or {}
        wm_type = wm.get("wm_type", "text")
        if wm_type == "image":
            # 图片水印导出
            img_path = wm.get("image_path", "")
            if not img_path:
                return img
            wm_img = QImage(img_path)
            if wm_img.isNull():
                return img
            opacity = float(wm.get("img_opacity", 0.6))
            margin = int(wm.get("margin", 20))
            scale_mode = wm.get("img_scale_mode", "proportional")
            if scale_mode == "proportional":
                pct = int(wm.get("img_scale_pct", 100))
                target_w = max(1, int(wm_img.width() * pct / 100.0))
                target_h = max(1, int(wm_img.height() * pct / 100.0))
                wm_scaled = wm_img.scaled(target_w, target_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            else:
                target_w = max(1, int(wm.get("img_width", wm_img.width())))
                target_h = max(1, int(wm.get("img_height", wm_img.height())))
                wm_scaled = wm_img.scaled(target_w, target_h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)

            painter = QPainter(img)
            painter.setOpacity(opacity)
            wm_w = wm_scaled.width()
            wm_h = wm_scaled.height()
            position = wm.get("position", "bottom_right")
            if position == "custom":
                if "pos_x_pct" in wm and "pos_y_pct" in wm:
                    cx = float(wm.get("pos_x_pct", 0.0)) * img.width()
                    cy = float(wm.get("pos_y_pct", 0.0)) * img.height()
                else:
                    cx = float(wm.get("pos_x", margin))
                    cy = float(wm.get("pos_y", margin))
                min_x = margin
                min_y = margin
                max_x = img.width() - margin - wm_w
                max_y = img.height() - margin - wm_h
                x = max(min_x, min(max_x, cx))
                y = max(min_y, min(max_y, cy))

                painter.drawImage(int(x), int(y), wm_scaled)
            else:
                content_rect = img.rect().adjusted(margin, margin, -margin, -margin)
                if position == "top_left":
                    x = content_rect.left()
                    y = content_rect.top()
                elif position == "top_right":
                    x = content_rect.right() - wm_w
                    y = content_rect.top()
                elif position == "bottom_left":
                    x = content_rect.left()
                    y = content_rect.bottom() - wm_h
                elif position == "bottom_right":
                    x = content_rect.right() - wm_w
                    y = content_rect.bottom() - wm_h
                elif position == "top_center":
                    x = content_rect.center().x() - wm_w // 2
                    y = content_rect.top()
                elif position == "bottom_center":
                    x = content_rect.center().x() - wm_w // 2
                    y = content_rect.bottom() - wm_h
                elif position == "center_left":
                    x = content_rect.left()
                    y = content_rect.center().y() - wm_h // 2
                elif position == "center_right":
                    x = content_rect.right() - wm_w
                    y = content_rect.center().y() - wm_h // 2
                else:  # center
                    x = content_rect.center().x() - wm_w // 2
                    y = content_rect.center().y() - wm_h // 2
                painter.drawImage(int(x), int(y), wm_scaled)
            painter.end()
            return img

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
            else:  # center
                x = content_rect.center().x() - text_w // 2
                y = content_rect.center().y() - text_h // 2
            painter.drawImage(int(x), int(y), text_img)
        painter.end()
        return img


    def compose_qimage_for_path_duplicate(self, path: str, settings: dict | None = None):
        # 离屏合成：直接从文件读取为 QImage 并绘制水印
        if not path:
            return None
        img = QImage(path)
        if img.isNull():
            return None
        img = img.convertToFormat(QImage.Format_ARGB32)

        wm = settings or self._wm_settings or {}
        wm_type = wm.get("wm_type", "text")
        if wm_type == "image":
            # 图片水印导出
            img_path = wm.get("image_path", "")
            if not img_path:
                return img
            wm_img = QImage(img_path)
            if wm_img.isNull():
                return img
            opacity = float(wm.get("img_opacity", 0.6))
            margin = int(wm.get("margin", 20))
            scale_mode = wm.get("img_scale_mode", "proportional")
            if scale_mode == "proportional":
                pct = int(wm.get("img_scale_pct", 100))
                target_w = max(1, int(wm_img.width() * pct / 100.0))
                target_h = max(1, int(wm_img.height() * pct / 100.0))
                wm_scaled = wm_img.scaled(target_w, target_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            else:
                target_w = max(1, int(wm.get("img_width", wm_img.width())))
                target_h = max(1, int(wm.get("img_height", wm_img.height())))
                wm_scaled = wm_img.scaled(target_w, target_h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)

            painter = QPainter(img)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setOpacity(opacity)
            wm_w = wm_scaled.width()
            wm_h = wm_scaled.height()
            position = wm.get("position", "bottom_right")
            if position == "custom":
                if "pos_x_pct" in wm and "pos_y_pct" in wm:
                    cx = float(wm.get("pos_x_pct", 0.0)) * img.width()
                    cy = float(wm.get("pos_y_pct", 0.0)) * img.height()
                else:
                    cx = float(wm.get("pos_x", margin))
                    cy = float(wm.get("pos_y", margin))
                min_x = margin
                min_y = margin
                max_x = img.width() - margin - wm_w
                max_y = img.height() - margin - wm_h
                x = max(min_x, min(max_x, cx))
                y = max(min_y, min(max_y, cy))
                painter.drawImage(int(x), int(y), wm_scaled)
            else:
                content_rect = img.rect().adjusted(margin, margin, -margin, -margin)
                if position == "top_left":
                    x = content_rect.left()
                    y = content_rect.top()
                elif position == "top_right":
                    x = content_rect.right() - wm_w
                    y = content_rect.top()
                elif position == "bottom_left":
                    x = content_rect.left()
                    y = content_rect.bottom() - wm_h
                elif position == "bottom_right":
                    x = content_rect.right() - wm_w
                    y = content_rect.bottom() - wm_h
                elif position == "top_center":
                    x = content_rect.center().x() - wm_w // 2
                    y = content_rect.top()
                elif position == "bottom_center":
                    x = content_rect.center().x() - wm_w // 2
                    y = content_rect.bottom() - wm_h
                elif position == "center_left":
                    x = content_rect.left()
                    y = content_rect.center().y() - wm_h // 2
                elif position == "center_right":
                    x = content_rect.right() - wm_w
                    y = content_rect.center().y() - wm_h // 2
                else:
                    x = content_rect.center().x() - wm_w // 2
                    y = content_rect.center().y() - wm_h // 2
                painter.drawImage(int(x), int(y), wm_scaled)
            painter.end()
            return img

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