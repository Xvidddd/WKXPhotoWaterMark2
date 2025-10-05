from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase
from PySide6.QtWidgets import (
    QWidget,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QSpinBox,
    QSlider,
    QPushButton,
    QColorDialog,
    QCheckBox,
    QHBoxLayout,
    QGroupBox,
    QVBoxLayout,
)


class WatermarkPanel(QWidget):
    settingsChanged = Signal(dict)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.text = QLineEdit()
        self.text.setPlaceholderText("输入水印文字")

        self.position = QComboBox()
        # 九宫格位置：四角、中心、边缘中点（左居中/右居中/上居中/下居中）
        self.position.addItems(["左上", "右上", "左下", "右下", "居中", "上居中", "下居中", "左居中", "右居中"])
        self.position.setCurrentIndex(3)  # 默认右下

        # 字体选择
        self.font_family = QComboBox()
        # 加载系统所有字体
        font_families = QFontDatabase.families()
        self.font_family.addItems(font_families)
        # 设置默认字体为系统默认
        default_font = QFont().family()
        default_index = self.font_family.findText(default_font)
        if default_index >= 0:
            self.font_family.setCurrentIndex(default_index)

        self.font_size = QSpinBox()
        self.font_size.setRange(8, 200)
        self.font_size.setValue(32)

        # 字体样式：粗体、斜体
        self.font_bold = QCheckBox("粗体")
        self.font_italic = QCheckBox("斜体")
        font_style_layout = QHBoxLayout()
        font_style_layout.addWidget(self.font_bold)
        font_style_layout.addWidget(self.font_italic)
        font_style_widget = QWidget()
        font_style_widget.setLayout(font_style_layout)

        # 文本样式：阴影和描边
        # 阴影设置
        self.shadow_enabled = QCheckBox("启用阴影")
        self.shadow_offset = QSpinBox()
        self.shadow_offset.setRange(1, 10)
        self.shadow_offset.setValue(2)
        self.shadow_blur = QSpinBox()
        self.shadow_blur.setRange(0, 10)
        self.shadow_blur.setValue(2)
        
        # 阴影颜色
        self._shadow_color = QColor(0, 0, 0)  # 默认黑色
        self.shadow_color_btn = QPushButton("阴影颜色")
        self._update_shadow_color_btn()
        
        shadow_layout = QFormLayout()
        shadow_layout.addRow("启用:", self.shadow_enabled)
        shadow_layout.addRow("偏移:", self.shadow_offset)
        shadow_layout.addRow("模糊:", self.shadow_blur)
        shadow_layout.addRow("颜色:", self.shadow_color_btn)
        
        shadow_group = QGroupBox("阴影效果")
        shadow_group.setLayout(shadow_layout)
        
        # 描边设置
        self.stroke_enabled = QCheckBox("启用描边")
        self.stroke_width = QSpinBox()
        self.stroke_width.setRange(1, 10)
        self.stroke_width.setValue(2)
        
        # 描边颜色
        self._stroke_color = QColor(255, 255, 255)  # 默认白色
        self.stroke_color_btn = QPushButton("描边颜色")
        self._update_stroke_color_btn()
        
        stroke_layout = QFormLayout()
        stroke_layout.addRow("启用:", self.stroke_enabled)
        stroke_layout.addRow("宽度:", self.stroke_width)
        stroke_layout.addRow("颜色:", self.stroke_color_btn)
        
        stroke_group = QGroupBox("描边效果")
        stroke_group.setLayout(stroke_layout)
        
        # 文本样式布局
        text_style_layout = QVBoxLayout()
        text_style_layout.addWidget(shadow_group)
        text_style_layout.addWidget(stroke_group)
        
        text_style_widget = QWidget()
        text_style_widget.setLayout(text_style_layout)

        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(0, 100)
        self.opacity.setValue(60)

        self.margin = QSpinBox()
        self.margin.setRange(0, 200)
        self.margin.setValue(20)

        # 颜色选择器（默认黑色）
        self._color = QColor(0, 0, 0)
        self.color_btn = QPushButton("选择颜色")
        self._update_color_btn()

        layout = QFormLayout(self)
        layout.addRow("文本", self.text)
        layout.addRow("位置", self.position)
        layout.addRow("字体", self.font_family)
        layout.addRow("字号", self.font_size)
        layout.addRow("样式", font_style_widget)
        layout.addRow("透明度", self.opacity)
        layout.addRow("颜色", self.color_btn)
        layout.addRow("边距", self.margin)
        layout.addRow("文本效果", text_style_widget)

        self.text.textChanged.connect(self._emit)
        self.position.currentIndexChanged.connect(self._emit)
        self.font_family.currentIndexChanged.connect(self._emit)
        self.font_size.valueChanged.connect(self._emit)
        self.font_bold.stateChanged.connect(self._emit)
        self.font_italic.stateChanged.connect(self._emit)
        self.opacity.valueChanged.connect(self._emit)
        self.margin.valueChanged.connect(self._emit)
        self.color_btn.clicked.connect(self._choose_color)
        
        # 阴影和描边信号连接
        self.shadow_enabled.stateChanged.connect(self._emit)
        self.shadow_offset.valueChanged.connect(self._emit)
        self.shadow_blur.valueChanged.connect(self._emit)
        self.shadow_color_btn.clicked.connect(self._choose_shadow_color)
        
        self.stroke_enabled.stateChanged.connect(self._emit)
        self.stroke_width.valueChanged.connect(self._emit)
        self.stroke_color_btn.clicked.connect(self._choose_stroke_color)

    def _emit(self, *args) -> None:
        self.settingsChanged.emit(self.get_settings())

    def get_settings(self) -> dict:
        pos_map = {
            0: "top_left",
            1: "top_right",
            2: "bottom_left",
            3: "bottom_right",
            4: "center",
            5: "top_center",
            6: "bottom_center",
            7: "center_left",
            8: "center_right",
        }
        return {
            "text": self.text.text().strip(),
            "position": pos_map.get(self.position.currentIndex(), "bottom_right"),
            "font_family": self.font_family.currentText(),
            "font_size": int(self.font_size.value()),
            "font_bold": self.font_bold.isChecked(),
            "font_italic": self.font_italic.isChecked(),
            "opacity": float(self.opacity.value()) / 100.0,
            "margin": int(self.margin.value()),
            "color": self._color,
            # 阴影设置
            "shadow_enabled": self.shadow_enabled.isChecked(),
            "shadow_offset": self.shadow_offset.value(),
            "shadow_blur": self.shadow_blur.value(),
            "shadow_color": self._shadow_color,
            # 描边设置
            "stroke_enabled": self.stroke_enabled.isChecked(),
            "stroke_width": self.stroke_width.value(),
            "stroke_color": self._stroke_color,
        }

    def apply_settings(self, settings: dict) -> None:
        # 将给定设置应用到控件；不处理自定义坐标，仅更新面板可控字段
        text = settings.get("text")
        if isinstance(text, str):
            self.text.setText(text)
        
        # 字体设置
        font_family = settings.get("font_family")
        if isinstance(font_family, str):
            index = self.font_family.findText(font_family)
            if index >= 0:
                self.font_family.setCurrentIndex(index)
        
        fs = settings.get("font_size")
        if isinstance(fs, int):
            self.font_size.setValue(fs)
            
        # 字体样式
        font_bold = settings.get("font_bold")
        if isinstance(font_bold, bool):
            self.font_bold.setChecked(font_bold)
            
        font_italic = settings.get("font_italic")
        if isinstance(font_italic, bool):
            self.font_italic.setChecked(font_italic)
            
        op = settings.get("opacity")
        if isinstance(op, (int, float)):
            self.opacity.setValue(int(max(0.0, min(1.0, float(op))) * 100))
        color = settings.get("color")
        if isinstance(color, QColor):
            self._color = color
            self._update_color_btn()
        margin = settings.get("margin")
        if isinstance(margin, int):
            self.margin.setValue(margin)
        pos = settings.get("position")
        if isinstance(pos, str):
            index_map = {
                "top_left": 0,
                "top_right": 1,
                "bottom_left": 2,
                "bottom_right": 3,
                "center": 4,
                "top_center": 5,
                "bottom_center": 6,
                "center_left": 7,
                "center_right": 8,
            }
            if pos in index_map:
                self.position.setCurrentIndex(index_map[pos])
                
        # 阴影设置
        shadow_enabled = settings.get("shadow_enabled")
        if isinstance(shadow_enabled, bool):
            self.shadow_enabled.setChecked(shadow_enabled)
            
        shadow_offset = settings.get("shadow_offset")
        if isinstance(shadow_offset, int):
            self.shadow_offset.setValue(shadow_offset)
            
        shadow_blur = settings.get("shadow_blur")
        if isinstance(shadow_blur, int):
            self.shadow_blur.setValue(shadow_blur)
            
        shadow_color = settings.get("shadow_color")
        if isinstance(shadow_color, QColor):
            self._shadow_color = shadow_color
            self._update_shadow_color_btn()
            
        # 描边设置
        stroke_enabled = settings.get("stroke_enabled")
        if isinstance(stroke_enabled, bool):
            self.stroke_enabled.setChecked(stroke_enabled)
            
        stroke_width = settings.get("stroke_width")
        if isinstance(stroke_width, int):
            self.stroke_width.setValue(stroke_width)
            
        stroke_color = settings.get("stroke_color")
        if isinstance(stroke_color, QColor):
            self._stroke_color = stroke_color
            self._update_stroke_color_btn()
            
        # 应用完毕后发出一次更新
        self._emit()

    def _choose_color(self) -> None:
        color = QColorDialog.getColor(self._color, self, "选择水印颜色")
        if color.isValid():
            self._color = color
            self._update_color_btn()
            self._emit()

    def _update_color_btn(self) -> None:
        # 在按钮上显示当前颜色块
        self.color_btn.setStyleSheet(
            f"background-color: {self._color.name()}; color: white;"
        )
        
    def _update_shadow_color_btn(self) -> None:
        # 在按钮上显示当前颜色块
        self.shadow_color_btn.setStyleSheet(
            f"background-color: {self._shadow_color.name()}; color: white;"
        )
        
    def _update_stroke_color_btn(self) -> None:
        # 在按钮上显示当前颜色块
        self.stroke_color_btn.setStyleSheet(
            f"background-color: {self._stroke_color.name()}; color: black;"
        )
        
    def _choose_shadow_color(self) -> None:
        color = QColorDialog.getColor(self._shadow_color, self, "选择阴影颜色")
        if color.isValid():
            self._shadow_color = color
            self._update_shadow_color_btn()
            self._emit()
            
    def _choose_stroke_color(self) -> None:
        color = QColorDialog.getColor(self._stroke_color, self, "选择描边颜色")
        if color.isValid():
            self._stroke_color = color
            self._update_stroke_color_btn()
            self._emit()