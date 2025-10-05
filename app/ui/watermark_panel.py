from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QSpinBox,
    QSlider,
    QPushButton,
    QColorDialog,
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

        self.font_size = QSpinBox()
        self.font_size.setRange(8, 200)
        self.font_size.setValue(32)

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
        layout.addRow("字号", self.font_size)
        layout.addRow("透明度", self.opacity)
        layout.addRow("颜色", self.color_btn)
        layout.addRow("边距", self.margin)

        self.text.textChanged.connect(self._emit)
        self.position.currentIndexChanged.connect(self._emit)
        self.font_size.valueChanged.connect(self._emit)
        self.opacity.valueChanged.connect(self._emit)
        self.margin.valueChanged.connect(self._emit)
        self.color_btn.clicked.connect(self._choose_color)

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
            "font_size": int(self.font_size.value()),
            "opacity": float(self.opacity.value()) / 100.0,
            "margin": int(self.margin.value()),
            "color": self._color,
        }

    def apply_settings(self, settings: dict) -> None:
        # 将给定设置应用到控件；不处理自定义坐标，仅更新面板可控字段
        text = settings.get("text")
        if isinstance(text, str):
            self.text.setText(text)
        fs = settings.get("font_size")
        if isinstance(fs, int):
            self.font_size.setValue(fs)
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