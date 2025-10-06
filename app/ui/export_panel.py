from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget,
    QFormLayout,
    QComboBox,
    QSpinBox,
    QSlider,
    QLabel,
    QHBoxLayout,
)


class _NoWheelMixin:
    def wheelEvent(self, event):
        event.ignore()

class NoWheelSpinBox(_NoWheelMixin, QSpinBox):
    pass

class NoWheelSlider(_NoWheelMixin, QSlider):
    pass

class NoWheelComboBox(_NoWheelMixin, QComboBox):
    pass

class ExportPanel(QWidget):
    settingsChanged = Signal(dict)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        # 导出格式（保持与 MainWindow 期望的字段名一致）
        self.format = NoWheelComboBox()
        self.format.addItems(["PNG", "JPEG"])  # index: 0->PNG, 1->JPEG
        # JPEG 质量
        self.quality = NoWheelSlider(Qt.Orientation.Horizontal)
        self.quality.setRange(0, 100)
        self.quality.setValue(90)

        # 尺寸调整模式：与 MainWindow 的索引映射保持一致
        # 0:none, 1:width, 2:height, 3:percent
        self.resize_mode = NoWheelComboBox()
        self.resize_mode.addItems(["不调整", "按宽度(像素)", "按高度(像素)", "按比例(%)"])
        self.resize_value = NoWheelSpinBox()
        self.resize_value.setRange(1, 10000)
        self.resize_value.setValue(100)

        layout = QFormLayout(self)
        layout.addRow("导出格式", self.format)
        layout.addRow("JPEG质量", self.quality)
        layout.addRow("尺寸调整", self.resize_mode)
        layout.addRow("调整值", self.resize_value)

        self.format.currentIndexChanged.connect(self._emit)
        self.quality.valueChanged.connect(self._emit)
        self.resize_mode.currentIndexChanged.connect(self._emit)
        self.resize_value.valueChanged.connect(self._emit)

    def _emit(self, *args) -> None:
        self.settingsChanged.emit(self.get_settings())

    def get_settings(self) -> dict:
        return {
            "format": "PNG" if self.format.currentIndex() == 0 else "JPEG",
            "jpeg_quality": self.quality.value(),
            "resize_mode": ["none", "width", "height", "percent"][self.resize_mode.currentIndex()],
            "resize_value": self.resize_value.value(),
        }

    def apply_settings(self, settings: dict) -> None:
        # 应用导出设置
        fmt = settings.get("format", "PNG")
        self.format.setCurrentIndex(1 if fmt == "JPEG" else 0)
        
        quality = settings.get("jpeg_quality", 90)
        if isinstance(quality, int):
            self.quality.setValue(quality)
        
        resize_mode = settings.get("resize_mode", "none")
        mode_index = {"none": 0, "width": 1, "height": 2, "percent": 3}.get(resize_mode, 0)
        self.resize_mode.setCurrentIndex(mode_index)
        
        resize_value = settings.get("resize_value", 100)
        if isinstance(resize_value, int):
            self.resize_value.setValue(resize_value)