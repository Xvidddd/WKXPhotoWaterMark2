from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView


class PreviewView(QGraphicsView):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHints(self.renderHints())
        self.setDragMode(QGraphicsView.ScrollHandDrag)

    def load_image(self, file_path: str) -> bool:
        pix = QPixmap(file_path)
        if pix.isNull():
            return False
        self._scene.clear()
        self._scene.addPixmap(pix)
        self._scene.setSceneRect(pix.rect())
        self.fitInView(self._scene.sceneRect(), mode=self.AspectRatioMode.KeepAspectRatio)
        return True