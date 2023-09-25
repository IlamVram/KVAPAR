from PyQt5.QtWidgets import QWidget, QMainWindow
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout



i = 0


class MainWidget(QMainWindow):

    def __init__(self):
        QWidget.__init__(self)
        self.overlay = None

    def mousePressEvent(self, QMouseEvent):  # real signature unknown; restored from __doc__
        print("PRESS")

    def wheelEvent(self, event):
        # Check if the wheel event occurred while holding a modifier key (e.g., Ctrl)
        global i
        i += 1
        if not (event.modifiers() & Qt.ControlModifier):
            if event.angleDelta().y() > 0:
                self.dim.another_slice()
                print("Scroll Up" + str(i))
            else:
                self.dim.previous_slice()
                print("Scroll Down" + str(i))
