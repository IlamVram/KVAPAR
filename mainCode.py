import ctypes
import os
import sys
import traceback
import datetime
import PIL.ImageDraw as ImageDraw
import PyQt5
import SimpleITK as sitk
import numpy as np
import pydicom
import scipy.ndimage as ndi
from PIL import Image
from PyQt5 import QtCore, QtGui, QtWidgets

from WheelWidget import MainWidget
from untitled import Ui_MainWindow

awareness = ctypes.c_int()
errorCode = ctypes.windll.shcore.SetProcessDpiAwareness(2)
ctypes.windll.user32.SetProcessDPIAware()

os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "2"
if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
    PyQt5.QtWidgets.QApplication.setAttribute(
        QtCore.Qt.AA_EnableHighDpiScaling, True)

if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
    PyQt5.QtWidgets.QApplication.setAttribute(
        QtCore.Qt.AA_UseHighDpiPixmaps, True)


class Data(object):

    def __init__(self):
        self.num_of_segments = 0
        self.points_list = []
        self.suv = None


class DicomController(object):

    def __init__(self):
        self.pixels = None
        self.main_window_ui = None
        self.points = None
        self.current_file_name = None
        self.new_name = None
        self.extension = None
        self.filename = None
        self.base = None
        self.filepath = None
        self.seg_man = None
        self.curr_segmented = None
        self.num_of_segments = None
        self.segmented_pdws = None
        self.pdw = None
        self.cdireleas = None
        self.cidmotion = None
        self.cdipress = None
        self.select_dicom = None
        self.widgets = None
        self.is_last = False
        self.is_first = False
        self.drawings = {}
        self.currentIndex = 0
        self.points_list = []

    def after_processing(self, main_window):
        """ Sets up the UI by adding components
            to the main window.

        Arguments:
            main_window (QMainWindow): The main window on                                        which we add all
                                       the components.
        """

        self.widgets = [main_window]
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("etf_logo.ico"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        main_window.setWindowIcon(icon)

        # assign main window as the central widget

        self.main_window_ui = Ui_MainWindow()
        self.main_window_ui.setupUi(main_window)

        self.widgets.append(self.main_window_ui.next_subject_button)

        self.widgets.append(self.main_window_ui.load_button)

        self.widgets.append(self.main_window_ui.save_button)

        """ self.widgets.append(self.main_window_ui.as_button)"""

        self.widgets.append(self.main_window_ui.manual_radio)

        self.widgets.append(self.main_window_ui.clear_button)

        self.widgets.append(self.main_window_ui.loaded_path)

        # add overlay image placeholder

        self.connect_methods()
        self.main_window_ui.next_subject_button.setDisabled(True)
        self.main_window_ui.save_button.setDisabled(True)
        """ self.main_window_ui.as_button.setDisabled(True)"""
        self.main_window_ui.clear_button.setDisabled(True)
        self.main_window_ui.manual_radio.setDisabled(True)

        self.select_dicom = False
        QtCore.QMetaObject.connectSlotsByName(main_window)

    def clear_figures(self):
        """ Clears all three figures """
        self.main_window_ui.overlay_image.axs_overlay_image.clear()
        self.main_window_ui.overlay_image.draw()

    def connect_methods(self):
        """ Connects the clicked event of the buttons
            to the according class method which we wish
            to execute when those buttons are clicked.
        """
        self.main_window_ui.load_button.clicked.connect(self.load_first_image)
        self.main_window_ui.next_subject_button.clicked.connect(self.restart_workspace)
        self.main_window_ui.save_button.clicked.connect(self.save_regions)
        """ self.main_window_ui.as_button.clicked.connect(self.another_slice)"""
        self.main_window_ui.manual_radio.toggled.connect(self.toggle_manual)
        self.main_window_ui.clear_button.clicked.connect(self.clear_roi)
        self.main_window_ui.info_button.clicked.connect(self.show_info)

        self.main_window_ui.genderW.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.main_window_ui.genderW.setFocusPolicy(QtCore.Qt.NoFocus)

        self.main_window_ui.genderM.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.main_window_ui.genderM.setFocusPolicy(QtCore.Qt.NoFocus)

        self.cdipress = self.main_window_ui.overlay_image.overlay_image_canvas.mpl_connect('button_press_event',
                                                                                           self.on_mouse_press)
        self.cidmotion = self.main_window_ui.overlay_image.overlay_image_canvas.mpl_connect(
            'motion_notify_event', self.on_mouse_moved)
        self.cdireleas = self.main_window_ui.overlay_image.overlay_image_canvas.mpl_connect('button_release_event',
                                                                                            self.on_mouse_release)

    def restart_workspace(self):
        self.main_window_ui.manual_radio.setChecked(False)
        _translate = QtCore.QCoreApplication.translate
        self.pdw = []
        self.main_window_ui.manual_radio.setChecked(False)
        self.segmented_pdws = []
        self.clear_figures()
        self.main_window_ui.load_button.setDisabled(False)
        self.num_of_segments = 0
        self.main_window_ui.loaded_path.clear()

        self.main_window_ui.manual_radio.setDisabled(True)
        self.main_window_ui.clear_button.setDisabled(True)
        self.main_window_ui.save_button.setDisabled(True)
        """ self.main_window_ui.as_button.setDisabled(True)"""
        self.main_window_ui.next_subject_button.setDisabled(True)
        self.main_window_ui.overlay_image.axs_overlay_image.clear()
        self.seg_man = []
        self.curr_segmented = []
        self.main_window_ui.loaded_path.setText(_translate("main_window", "Choose file"))
        self.is_last = False
        self.is_first = False
        self.drawings = {}
        self.currentIndex = 0
        self.points_list = []
        self.set_empty_calculations()
        self.patientName = ""
        self.patientAge = -1
        self.patientSex = ""
        self.studyDate = ""
        self.modality = ""
        self.dose = -1

    def load_first_image(self):
        load_success = False
        _translate = QtCore.QCoreApplication.translate
        try:

            # load the initial DICOM file
            filepath, _ = QtWidgets.QFileDialog.getOpenFileName()

            # check if the user hasn't selected any file
            if not filepath:
                return
            self.filepath = filepath
            self.points_list = []
            self.pdw = []
            data = pydicom.dcmread(filepath)
            print(data.Units)
            self.load_scan_info(data)
            print(data.dir())
            print(data.file_meta)
            data = data.pixel_array

            places = np.where(data != 0)
            print(data[places])

            zoom = int(1008 / data.shape[1])

            # apply spline interpolation to
            # the slice
            # new_data = np.zeros((1, 1008, 1008))
            new_data = ndi.zoom(data, zoom=zoom, order=1)
            new_data[new_data < 0] = 0
            new_data.astype(np.int16)
            self.pdw = new_data
            self.pixels = self.pdw
            load_success = True

        except Exception:
            # show a warning message box which indicates
            # that an error occurred while loading selected
            # subject's data
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Critical)
            msg.setText("Invalid selection!")
            msg.setInformativeText('')
            msg.setWindowTitle("Error")
            msg.exec_()

        if load_success:
            self.currentIndex = 0
            self.points_list = []
            self.drawings = {}
            # msg = QtWidgets.QMessageBox()
            # msg.setIcon(QtWidgets.QMessageBox.Information)
            # msg.setText("File is loading!")
            # msg.setInformativeText('')
            # msg.setWindowTitle("Wait")
            # msg.exec_()
            base, filename = os.path.split(filepath)
            self.base = base
            self.filename = filename
            extension = os.path.splitext(filename)[-1].lower()
            self.extension = extension
            if self.extension:
                self.new_name = filename[:-len(self.extension)]
                self.main_window_ui.loaded_path.setText(_translate("main_window", self.new_name))
            else:
                self.main_window_ui.loaded_path.setText(_translate("main_window", filename))

            self.main_window_ui.next_subject_button.setDisabled(False)
            """ self.main_window_ui.as_button.setDisabled(False)"""
            self.main_window_ui.manual_radio.setDisabled(False)
            self.main_window_ui.overlay_image.show_img(self.pdw)
            self.main_window_ui.overlay_image.draw()
            self.main_window_ui.load_button.setDisabled(True)
            self.num_of_segments = 0
            self.current_file_name = filename
            print(filename)

    def load_scan_info(self, data):
        self.patientName = data.PatientName
        self.patientAge = data.PatientAge
        self.patientSex = data.PatientSex
        self.studyDate = datetime.datetime.strptime(data.StudyDate, "%Y%m%d").strftime("%d-%m-%Y")
        self.modality = data.Modality
        self.dose = data[0x0054, 0x0016][0][0x0018, 0x1074].value / 1000000

        if self.patientSex == "M":
            self.main_window_ui.genderM.setChecked(True)
        else:
            self.main_window_ui.genderW.setChecked(True)
        self.main_window_ui.doseInput.setText(str(self.dose))
        print(data.PatientName)
        print(data.PatientAge)
        print(data.PatientSex)
        print(data.StudyDate)
        print(data.Modality)
        print(data[0x0054, 0x0016][0][0x0018, 0x1074].value)

    def update_figures(self):

        self.main_window_ui.overlay_image.axs_overlay_image.clear()
        # checks the mode and if there are any segments (in case of manual segmentation)
        if self.main_window_ui.manual_radio.isChecked() and self.num_of_segments > 0:

            # show image created by segmenting

            self.curr_segmented = np.copy(self.segmented_pdws)  # sets current segmented if the rois are loaded
            self.main_window_ui.overlay_image.show_img(self.curr_segmented)
        else:
            self.main_window_ui.overlay_image.show_img(self.pdw)

        self.main_window_ui.overlay_image.draw()

    def save_regions(self):
        if self.main_window_ui.manual_radio.isChecked() and self.num_of_segments > 0:
            # self.save_button.setDisabled(False)
            self.calculate_and_show_info(self.seg_man)
        else:
            self.set_empty_calculations()
        if self.num_of_segments == 0:
            self.set_empty_calculations()

    def set_empty_calculations(self):
        self.main_window_ui.suv.setText("")
        self.main_window_ui.sul.setText("")
        self.main_window_ui.mtv.setText("")
        self.main_window_ui.tlg.setText("")

    def calculate_and_show_info(self, seg):
        suv = self.calculate_suv(seg)
        sul = self.calculate_sul(suv)
        mtv = self.calculate_mtv()
        tlg = self.calculate_tlg(suv, mtv)

        self.main_window_ui.suv.setText(f'{suv:.2f}')
        self.main_window_ui.sul.setText(f'{sul:.2f}')
        self.main_window_ui.mtv.setText(f'{mtv:.2f}')
        self.main_window_ui.tlg.setText(f'{tlg:.2f}')

    def calculate_suv(self, seg):
        obj = ndi.label(seg)[0]
        seg = np.where(obj > 0, obj, np.nan).astype(np.uint8)
        places = np.where(seg != 0)
        x_coord = places[0]
        y_coord = places[1]
        weight = float(self.main_window_ui.weightInput.text())
        dose = float(self.main_window_ui.doseInput.text().replace(',', '.'))
        pixels_value_sum = 0
        for x, y in zip(x_coord, y_coord):
            print(self.pixels[x, y])
            pixels_value_sum += self.pixels[x, y]
        activity = pixels_value_sum * 1 / ((dose / 59707.0907208) * 37)
        suv = (activity / (dose / weight))/1000000
        return suv

    def calculate_mtv(self):
        suv_threshold = int(self.main_window_ui.suvThreshold.text())
        sum = 0
        dict_values = [self.drawings[key] for key in sorted(self.drawings.keys(), reverse=True)]
        for i in range(self.currentIndex):
            saved_data = dict_values[i]
            saved_suv = saved_data.suv
            if saved_suv > suv_threshold:
                sum += saved_suv

        current_suv = self.calculate_suv(self.seg_man)
        if current_suv > suv_threshold:
            sum += current_suv
        return sum

    def calculate_tlg(self, suv, mtv):
        return suv * mtv

    def calculate_sul(self, suv):
        value_one = 6.68
        value_two = 216
        if self.main_window_ui.genderW.isChecked():
            value_one = 8.78
            value_two = 244

        weight = int(self.main_window_ui.weightInput.text())
        height = int(self.main_window_ui.heightInput.text())
        bmi = (weight / ((height / 100) ** 2))
        lbm = (9.27 * 1000 * 1000 * weight) / (value_one * 1000 + value_two * bmi)
        sul = suv * (lbm / (weight * 1000))
        return sul

    def another_slice(self):
        load_success = False
        _translate = QtCore.QCoreApplication.translate
        try:
            savedData = Data()
            savedData.num_of_segments = self.num_of_segments
            savedData.points_list = self.points_list
            suv = 0
            if self.num_of_segments > 0:
                suv = self.calculate_suv(self.seg_man)
            savedData.suv = suv
            old_file_name = self.current_file_name
            file_name = str(int(self.current_file_name) + 11)
            self.current_file_name = file_name
            file_path = self.base + "/" + self.current_file_name
            data = pydicom.read_file(file_path)
            self.load_scan_info(data)
            data = data.pixel_array
            self.clear_all()
            self.drawings[old_file_name] = savedData
            zoom = int(1008 / data.shape[1])

            # apply spline interpolation to
            # the slice
            # new_data = np.zeros((1, 1008, 1008))
            new_data = ndi.zoom(data, zoom=zoom, order=1)
            new_data[new_data < 0] = 0
            new_data.astype(np.int16)
            self.pdw = new_data
            self.pixels = self.pdw

            load_success = True


        except Exception as ex:
            # show a warning message box which indicates
            # that an error occurred while loading selected
            # subject's data
            file_name = str(int(self.current_file_name) - 11)
            self.current_file_name = file_name
            """traceback.print_exc()
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Critical)
            msg.setText("There is no more!")
            msg.setInformativeText('')
            msg.setWindowTitle("Error")
            msg.exec_()"""

        if load_success:
            self.currentIndex += 1
            # msg = QtWidgets.QMessageBox()
            # msg.setIcon(QtWidgets.QMessageBox.Information)
            # msg.setText("File is loading!")
            # msg.setInformativeText('')
            # msg.setWindowTitle("Wait")
            # msg.exec_()
            base, filename = os.path.split(file_path)
            self.base = base
            self.filename = filename
            extension = os.path.splitext(filename)[-1].lower()
            self.extension = extension
            if self.extension:
                self.new_name = filename[:-len(self.extension)]
                self.main_window_ui.loaded_path.setText(_translate("main_window", self.new_name))
            else:
                self.main_window_ui.loaded_path.setText(_translate("main_window", filename))

            self.main_window_ui.next_subject_button.setDisabled(False)
            self.main_window_ui.manual_radio.setDisabled(False)
            self.main_window_ui.overlay_image.show_img(self.pdw)
            self.main_window_ui.overlay_image.draw()
            self.main_window_ui.load_button.setDisabled(True)
            if self.current_file_name in self.drawings:
                oldData = self.drawings[self.current_file_name]
                self.num_of_segments = oldData.num_of_segments
                self.points_list = oldData.points_list
                for one_points in self.points_list:
                    self.points = one_points
                    self.man_algorithm()
            else:
                self.points_list = []
                self.num_of_segments = 0

    def previous_slice(self):
        load_success = False
        _translate = QtCore.QCoreApplication.translate
        try:
            savedData = Data()
            savedData.num_of_segments = self.num_of_segments
            savedData.points_list = self.points_list
            suv = 0
            if self.num_of_segments > 0:
                suv = self.calculate_suv(self.seg_man)
            savedData.suv = suv
            old_file_name = self.current_file_name
            file_name = str(int(self.current_file_name) - 11)
            self.current_file_name = file_name
            file_path = self.base + "/" + self.current_file_name
            data = pydicom.read_file(file_path)
            self.load_scan_info(data)
            data = data.pixel_array
            self.drawings[old_file_name] = savedData
            self.clear_all()

            zoom = int(1008 / data.shape[1])

            # apply spline interpolation to
            # the slice
            # new_data = np.zeros((1, 1008, 1008))
            new_data = ndi.zoom(data, zoom=zoom, order=1)
            new_data[new_data < 0] = 0
            new_data.astype(np.int16)
            self.pdw = new_data
            self.pixels = self.pdw

            load_success = True


        except Exception:
            # show a warning message box which indicates
            # that an error occurred while loading selected
            # subject's data
            file_name = str(int(self.current_file_name) + 11)
            self.current_file_name = file_name
            """msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Critical)
            msg.setText("This is first!")
            msg.setInformativeText('')
            msg.setWindowTitle("Error")
            msg.exec_()"""

        if load_success:
            self.currentIndex -= 1
            # msg = QtWidgets.QMessageBox()
            # msg.setIcon(QtWidgets.QMessageBox.Information)
            # msg.setText("File is loading!")
            # msg.setInformativeText('')
            # msg.setWindowTitle("Wait")
            # msg.exec_()
            base, filename = os.path.split(file_path)
            self.base = base
            self.filename = filename
            extension = os.path.splitext(filename)[-1].lower()
            self.extension = extension
            if self.extension:
                self.new_name = filename[:-len(self.extension)]
                self.main_window_ui.loaded_path.setText(_translate("main_window", self.new_name))
            else:
                self.main_window_ui.loaded_path.setText(_translate("main_window", filename))

            self.main_window_ui.next_subject_button.setDisabled(False)
            self.main_window_ui.manual_radio.setDisabled(False)
            self.main_window_ui.overlay_image.show_img(self.pdw)
            self.main_window_ui.overlay_image.draw()
            self.main_window_ui.load_button.setDisabled(True)
            if self.current_file_name in self.drawings:
                oldData = self.drawings[self.current_file_name]
                self.num_of_segments = oldData.num_of_segments
                self.points_list = oldData.points_list
                for one_points in self.points_list:
                    self.points = one_points
                    self.man_algorithm()
            else:
                self.points_list = []
                self.num_of_segments = 0

    def clear_roi(self):
        if self.main_window_ui.manual_radio.isChecked() and self.num_of_segments > 0:
            img = self.seg_man

            img[img == self.num_of_segments] = 0  # because the last segment has value equal to the number of segments
            self.seg_man = img
            self.num_of_segments -= 1  # decrease the number of segments on the current slice

            # creates the new segments pdw
            seg = self.seg_man

            obj = ndi.label(seg)[0]
            seg = np.where(obj > 0, obj, np.nan).astype(np.uint8)

            seg = sitk.GetImageFromArray(seg)
            pdw = self.pdw
            pdw_copy = (((np.copy(pdw)) / np.max(pdw)) * 255).astype(np.uint8)
            pdw_original = np.copy(pdw_copy).astype(np.uint8)
            pdw_original = sitk.GetImageFromArray(pdw_original)
            ovr = sitk.LabelOverlay(pdw_original, seg)
            ovr = sitk.GetArrayFromImage(ovr)
            self.segmented_pdws = np.copy(ovr)
            self.points_list.pop()
            # updates the figures
            self.update_figures()

    def clear_all(self):
        if self.num_of_segments == 0:
            return
        img = self.seg_man
        for i in range(1, self.num_of_segments + 1):
            img[img == i] = 0  # because the last segment has value equal to the number of segments
        self.seg_man = img
        self.num_of_segments = 0  # decrease the number of segments on the current slice

        # creates the new segments pdw
        seg = self.seg_man

        obj = ndi.label(seg)[0]
        seg = np.where(obj > 0, obj, np.nan).astype(np.uint8)

        seg = sitk.GetImageFromArray(seg)
        pdw = self.pdw
        pdw_copy = (((np.copy(pdw)) / np.max(pdw)) * 255).astype(np.uint8)
        pdw_original = np.copy(pdw_copy).astype(np.uint8)
        pdw_original = sitk.GetImageFromArray(pdw_original)
        ovr = sitk.LabelOverlay(pdw_original, seg)
        ovr = sitk.GetArrayFromImage(ovr)
        self.segmented_pdws = np.copy(ovr)

        # updates the figures
        self.update_figures()

    def toggle_manual(self):
        """ Toggles the manual and
            auto mode.
        """

        if self.main_window_ui.manual_radio.isChecked():

            self.main_window_ui.clear_button.setDisabled(False)
            self.main_window_ui.save_button.setDisabled(False)
            """ self.main_window_ui.as_button.setDisabled(False)"""

            self.update_figures()
            self.main_window_ui.next_subject_button.setDisabled(False)
            self.points = [[], []]
            self.update_figures()

            pdw_copy = (((np.copy(self.pdw)) / np.max(self.pdw)) * 255).astype(np.uint8)
            pdw_original = np.copy(pdw_copy).astype(np.uint8)
            self.segmented_pdws = pdw_original
            image = Image.new("P", (1008, 1008))

            self.seg_man = (np.array(image))

        else:
            # transition from manual to auto

            self.num_of_segments = 0
            self.main_window_ui.save_button.setDisabled(True)
            """ self.main_window_ui.as_button.setDisabled(True)"""
            self.main_window_ui.clear_button.setDisabled(True)
            self.segmented_pdws = []
            self.update_figures()

    def on_mouse_press(self, event):
        """ Detects the press of the mouse. This event is used as the beginning of the manual segmentation.
            From the moment the mouse button is pressed unit it is released, the coordinates are taken and used to generate the segment.
        """

        # ensures that the mode is manual, the segmentation hasn't already started and zoom or pan aren't being used
        if self.main_window_ui.manual_radio.isChecked() and self.select_dicom == False and self.main_window_ui.overlay_image.toolbar.mode == '':
            # selectRoi - variable used as an indication if the segmentation has started
            self.select_dicom = True
            # list of points from the mouse
            self.points = [[], []]

            self.num_of_segments += 1  # increases the number of segments for the current slice
            # takes the event coordinates
            self.points[0].append(event.xdata)
            self.points[1].append(event.ydata)
            # plots the starting point
            self.main_window_ui.overlay_image.axs_overlay_image.scatter(event.xdata, event.ydata, c='r')
            self.main_window_ui.overlay_image.axs_overlay_image.plot(event.xdata, event.ydata, ',',
                                                                     c='r')
            # updates the canvas
            self.main_window_ui.overlay_image.draw()

    def on_mouse_moved(self, event):
        """ Used for segmentation. Everytime the mouse is moved after it has been clicked, records the event coordinates
            and creates a line between the current point and the previous in order to make a closed shape.
        """
        # checks to see if the mode is manual and the segmentation has started
        if self.main_window_ui.manual_radio.isChecked() and self.select_dicom:
            # gets the event coordinated
            self.points[0].append(event.xdata)
            self.points[1].append(event.ydata)

            # draws the line for current point
            self.main_window_ui.overlay_image.axs_overlay_image.plot(self.points[0][-2:],
                                                                     self.points[1][-2:], c='r')
            # updates the canvas
            self.main_window_ui.overlay_image.draw()

    def on_mouse_release(self, event):
        """ Marks the end of segmentation. When the mouse is released the drawing of the current segment is finished.
            Ensures the shape is closed by connecting the first and the last point.
        """
        # checks if mode is manual and no tool is in use (pan/zoom)
        if self.main_window_ui.manual_radio.isChecked() and self.main_window_ui.overlay_image.toolbar.mode == '':
            self.select_dicom = False

            # draws the line between the first and the last point
            self.main_window_ui.overlay_image.axs_overlay_image.plot(
                [self.points[0][0], self.points[0][-1]],
                [self.points[1][0], self.points[1][-1]], c='r')
            # updates canvas
            self.main_window_ui.overlay_image.draw()

            # manual segmentation
            self.points_list.append(self.points)
            self.man_algorithm()

    def man_algorithm(self):
        """ Creates the segmented pdw image based on the shape drawn. """
        # creates the tuple of coordinates required for the ImageDraw.Draw to draw a polygon
        pts = tuple(zip(self.points[0], self.points[1]))

        pom = Image.fromarray(self.seg_man)
        draw = ImageDraw.Draw(pom)
        # chooses the color to be the current number of segments on the slice for easier display
        f = int(self.num_of_segments)
        # draws the polygon
        draw.polygon(pts, fill=f)
        self.seg_man = np.array(pom)

        seg = self.seg_man
        # creates segmented pdw
        obj = ndi.label(seg)[0]
        seg = np.where(obj > 0, obj, np.nan).astype(np.uint8)

        seg = sitk.GetImageFromArray(seg)

        pdw = self.pdw
        pdw_copy = (((np.copy(pdw)) / np.max(pdw)) * 255).astype(np.uint8)
        pdw_original = np.copy(pdw_copy).astype(np.uint8)
        pdw_original = sitk.GetImageFromArray(pdw_original)
        ovr = sitk.LabelOverlay(pdw_original, seg)
        ovr = sitk.GetArrayFromImage(ovr)
        self.segmented_pdws = np.copy(ovr)

        # update figures
        self.update_figures()

    def show_info(self):
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setText("Info")
        msg.setInformativeText(
            '''
Patient Name: {0}
Age: {1}
Modality: {2}
Study Date: {3}
Dose: {4}
'''.format(self.patientName, self.patientAge, self.modality, self.studyDate, self.dose))
        msg.setWindowTitle("Info")
        msg.exec_()

    def start_up(self):
        # get the display resolution
        # width
        try:

            # initialize the application
            app = QtWidgets.QApplication(sys.argv)
            main_window = MainWidget()
            main_window.dim = self

            icon = QtGui.QIcon()
            icon.addPixmap(QtGui.QPixmap("./resources/icon.png"), QtGui.QIcon.Normal, QtGui.QIcon.On)
            main_window.setWindowIcon(icon)
            self.after_processing(main_window)

            # show the main window
            main_window.show()
            # plt.close(4)
        except:
            traceback.print_exc()
        sys.exit(app.exec_())
