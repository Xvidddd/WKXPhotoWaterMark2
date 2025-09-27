from pathlib import Path
from PySide6.QtCore import QSize
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow, QFileDialog, QMessageBox

from .preview_view import PreviewView


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("WKX Photo Watermark")
        self.resize(1000, 700)

        self.preview = PreviewView(self)
        self.setCentralWidget(self.preview)

        self._setup_actions()

    def _setup_actions(self) -> None:
        open_action = QAction("导入图片", self)
        open_action.setStatusTip("选择并预览一张图片")
        open_action.triggered.connect(self._on_open_image)

        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)

        menu = self.menuBar().addMenu("文件")
        menu.addAction(open_action)
        menu.addSeparator()
        menu.addAction(exit_action)

    def _on_open_image(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            str(Path.home()),
            "图像文件 (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)"
        )
        if not file_path:
            return
        ok = self.preview.load_image(file_path)
        if not ok:
            QMessageBox.warning(self, "加载失败", "无法加载所选图片，请检查格式或文件是否损坏。")