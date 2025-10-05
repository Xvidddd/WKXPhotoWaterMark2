from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget,
    QFormLayout,
    QComboBox,
    QSlider,
    QLabel,
    QSpinBox,
    QHBoxLayout,
)


class ExportPanel(QWidget):
    settingsChanged = Signal(dict)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        # 导出格式选择
        self.format = QComboBox()
        self.format.addItems(["PNG", "JPEG"])
        self.format.setCurrentIndex(0)  # 默认PNG

        # JPEG质量滑块（0-100）
        self.quality_label = QLabel("质量：80")
        self.quality = QSlider(Qt.Orientation.Horizontal)
        self.quality.setRange(0, 100)
        self.quality.setValue(80)  # 默认质量80
        self.quality.setEnabled(False)  # 初始禁用（仅JPEG时启用）

        # 图片尺寸调整
        self.resize_mode = QComboBox()
        self.resize_mode.addItems(["不调整", "按宽度", "按高度", "按百分比"])
        self.resize_mode.setCurrentIndex(0)  # 默认不调整

        self.resize_value = QSpinBox()
        self.resize_value.setRange(1, 10000)
        self.resize_value.setValue(100)
        self.resize_value.setEnabled(False)  # 初始禁用（仅选择调整模式时启用）
        
        # 百分比模式下的单位标签
        self.resize_unit_label = QLabel("%")
        self.resize_unit_label.setVisible(False)

        # 尺寸调整水平布局
        resize_layout = QHBoxLayout()
        resize_layout.addWidget(self.resize_value)
        resize_layout.addWidget(self.resize_unit_label)
        resize_layout.addStretch()

        # 主布局
        layout = QFormLayout(self)
        layout.addRow("格式", self.format)
        layout.addRow("JPEG质量", self.quality)
        layout.addRow("", self.quality_label)
        layout.addRow("尺寸调整", self.resize_mode)
        layout.addRow("", resize_layout)

        # 连接信号
        self.format.currentIndexChanged.connect(self._on_format_changed)
        self.quality.valueChanged.connect(self._on_quality_changed)
        self.resize_mode.currentIndexChanged.connect(self._on_resize_mode_changed)
        self.resize_value.valueChanged.connect(self._emit)

    def _on_format_changed(self, index):
        # 仅当选择JPEG格式时启用质量滑块
        is_jpeg = index == 1
        self.quality.setEnabled(is_jpeg)
        self.quality_label.setEnabled(is_jpeg)
        self._emit()

    def _on_quality_changed(self, value):
        self.quality_label.setText(f"质量：{value}")
        self._emit()

    def _on_resize_mode_changed(self, index):
        # 仅当选择调整模式时启用尺寸输入
        enabled = index > 0
        self.resize_value.setEnabled(enabled)
        
        # 根据模式设置单位标签
        if index == 3:  # 百分比模式
            self.resize_unit_label.setText("%")
            self.resize_unit_label.setVisible(True)
            self.resize_value.setValue(100)  # 默认100%
            self.resize_value.setRange(1, 500)  # 百分比范围1-500%
        elif index > 0:  # 宽度或高度模式
            self.resize_unit_label.setText("px")
            self.resize_unit_label.setVisible(True)
            self.resize_value.setValue(1000)  # 默认1000px
            self.resize_value.setRange(1, 10000)  # 像素范围1-10000px
        else:
            self.resize_unit_label.setVisible(False)
        
        self._emit()

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
        
        quality = settings.get("jpeg_quality", 80)
        if isinstance(quality, int):
            self.quality.setValue(quality)
        
        resize_mode = settings.get("resize_mode", "none")
        mode_index = {"none": 0, "width": 1, "height": 2, "percent": 3}.get(resize_mode, 0)
        self.resize_mode.setCurrentIndex(mode_index)
        
        resize_value = settings.get("resize_value", 100)
        if isinstance(resize_value, int):
            self.resize_value.setValue(resize_value)