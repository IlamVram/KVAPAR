import matplotlib
import matplotlib.pyplot as plt
import numpy
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

matplotlib.use('Qt5Agg')


class MatplotLibPlotWidget(QWidget):
    def __init__(self, parent):
        QWidget.__init__(self)
        self.overlay = None
        self.setLayout(QVBoxLayout())
        plt.tight_layout()

        self.parent = parent
        self.setParent(parent)

        # creates the display area for displaying
        # parametric and PDW image overlay
        # w=self.overlay_image.frameGeometry().width()
        # print(w)
        self.fig_overlay = plt.figure(figsize=(7.3, 7))

        self.overlay_image_canvas = FigureCanvas(self.fig_overlay)
        self.overlay_image_canvas.setParent(parent)

        self.axs_overlay_image = self.fig_overlay.add_subplot(111)
        self.fig_overlay.subplots_adjust(left=0, right=1, bottom=0, top=1,
                                         hspace=0, wspace=0)

        # creates the navigation toolbar and binds it
        # to the previously created display area
        self.toolbar = NavigationToolbar(self.overlay_image_canvas, self)

        # Get all possible actions on the plot
        actions = self.findChildren(QtWidgets.QAction)
        # define which actions to remove
        actions_to_remove = ["Save", "Subplots", "Customize"]

        # remove specified undesired actions
        for a in actions:
            if a.text() in actions_to_remove:
                self.toolbar.removeAction(a)

        self.toolbar.setParent(parent)

        # adds previously created display and toolbar
        # widgets to the object on the GUI
        self.layout().addWidget(self.overlay_image_canvas)
        self.layout().addWidget(self.toolbar)

    def show_img(self, img):
        """ Shows the given image in the third figure, reserved
            for showing overlay images. The colormap range
            for the parametric image is determined by the given
            vmin & vmax parameters.

        Arguments:
          img (numpy.ndarray): image to be shown
          img_type (str): the type of the image: 'p' -- parametric
                                                 'o' -- overlay (PDW)
          alpha (float): the transparency level for the specified image
          vmin (float): the lower bound for the range of the colormap
          vmax (float): the upper bound for the range of ther colormap
        """

        self.overlay = self.axs_overlay_image.imshow(img, cmap='gray', interpolation='none')

        self.axs_overlay_image.axis('tight')
        self.fig_overlay.subplots_adjust(left=0, right=1, bottom=0, top=1, hspace=0, wspace=0)

    def draw(self):
        """ Updates the canvas of the
            fig_overlay figure.
        """
        self.fig_overlay.canvas.draw()
