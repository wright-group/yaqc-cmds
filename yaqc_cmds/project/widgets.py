### import#####################################################################


import collections
import pathlib

from PySide2 import QtWidgets, QtCore

import pyqtgraph as pg

from yaqc_cmds.project import project_globals as g

colors = g.colors_dict.read()
__here__ = pathlib.Path(__file__).parent


### basic elements ############################################################


class ExpandingWidget(QtWidgets.QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)
        self.setLayout(QtWidgets.QVBoxLayout())
        self.setMinimumHeight(0)
        self.setMinimumWidth(0)
        self.layout().setStretchFactor(self, 1)

    def sizeHint(self):
        return QtCore.QSize(16777215, 16777215)

    def add_to_layout(self, layout):
        layout.addWidget(self)
        layout.setStretchFactor(self, 16777215)


class Line(QtWidgets.QFrame):
    """
    direction: 'V' or 'H'
    """

    def __init__(self, direction):
        QtWidgets.QFrame.__init__(self)
        if direction == "V":
            self.setFrameShape(QtWidgets.QFrame.VLine)
        else:
            self.setFrameShape(QtWidgets.QFrame.HLine)
        StyleSheet = (
            "QFrame{border: 2px solid custom_color; border-radius: 0px; padding: 0px;}".replace(
                "custom_color", colors["widget_background"]
            )
        )
        self.setStyleSheet(StyleSheet)


line = Line  # legacy


class scroll_area(QtWidgets.QScrollArea):
    def __init__(self, show_bar=True):
        QtWidgets.QScrollArea.__init__(self)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.setWidgetResizable(True)
        if show_bar:
            self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        StyleSheet = "QScrollArea, QWidget{background: custom_color;}".replace(
            "custom_color", colors["background"]
        )
        StyleSheet += "QScrollBar{background: custom_color;}".replace(
            "custom_color", colors["widget_background"]
        )
        self.setStyleSheet(StyleSheet)


class Led(QtWidgets.QCheckBox):
    def __init__(self):
        QtWidgets.QCheckBox.__init__(self)
        self.setDisabled(True)
        path = str(__here__).replace("\\", "/")
        StyleSheet = f"QCheckBox::indicator:checked {{image: url({path}/widget files/checkbox_checked.png);}}"
        StyleSheet += f"QCheckBox::indicator:unchecked {{image: url({path}/widget files/checkbox_unchecked.png);}}"
        print(StyleSheet)
        self.setStyleSheet(StyleSheet)


### general ###################################################################


class SpinboxAsDisplay(QtWidgets.QDoubleSpinBox):
    def __init__(self, font_size=14, decimals=6, justify="right"):
        QtWidgets.QDoubleSpinBox.__init__(self)
        self.setValue(0.0)
        self.setDisabled(True)
        self.decimals_input = decimals
        self.setDecimals(decimals)
        self.setMinimum(-100000)
        self.setMaximum(100000)
        if justify == "right":
            self.setAlignment(QtCore.Qt.AlignRight)
        else:
            self.setAlignment(QtCore.Qt.AlignLeft)
        self.setMinimumWidth(0)
        self.setMaximumWidth(600)
        self.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        StyleSheet = "QDoubleSpinBox{color: custom_color_1; font: bold font_sizepx; border: 0px solid #000000;}".replace(
            "custom_color_1", g.colors_dict.read()["text_light"]
        ).replace(
            "font_size", str(int(font_size))
        )
        StyleSheet += (
            "QScrollArea, QWidget{background: custom_color;  border-color: black;}".replace(
                "custom_color", g.colors_dict.read()["background"]
            )
        )
        self.setStyleSheet(StyleSheet)


class InputTable(QtWidgets.QWidget):
    def __getitem__(self, key):
        return self._dict[key]

    def __init__(self, width=130):
        """
        width of 160 good for modules
        """
        QtWidgets.QWidget.__init__(self)
        self.width_input = width
        self.setLayout(QtWidgets.QGridLayout())
        self.layout().setColumnMinimumWidth(0, width)
        self.layout().setColumnMinimumWidth(1, width)
        # self.layout().setMargin(0)
        self.row_number = 0
        self.controls = []
        self._dict = collections.OrderedDict()

    def add(self, name, global_object, key=None):
        if key is None:
            key = name
        if global_object is None:
            global_type = "heading"
        else:
            global_type = global_object.type
            self._dict[key] = global_object
        getattr(self, global_type)(name, global_object)

    def heading(self, name, global_object):
        # heading
        heading = QtWidgets.QLabel(name)
        StyleSheet = "QLabel{color: custom_color; font: bold 14px;}".replace(
            "custom_color", colors["heading_0"]
        )
        heading.setStyleSheet(StyleSheet)
        heading.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        self.layout().addWidget(heading, self.row_number, 0)
        self.controls.append(None)
        self.row_number += 1

    def number(self, name, global_object):
        # heading
        heading = QtWidgets.QLabel(name)
        StyleSheet = "QLabel{color: custom_color; font: 14px;}".replace(
            "custom_color", colors["text_light"]
        )
        heading.setStyleSheet(StyleSheet)
        heading.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        self.layout().addWidget(heading, self.row_number, 0)
        # layout
        container_widget = QtWidgets.QWidget()
        container_widget.setLayout(QtWidgets.QHBoxLayout())
        layout = container_widget.layout()
        layout.setMargin(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        # control
        control = QtWidgets.QDoubleSpinBox()
        if global_object.display:
            control.setDisabled(True)
            StyleSheet = "QDoubleSpinBox{color: custom_color_1; font: bold font_sizepx; border: 0px solid #000000;}".replace(
                "custom_color_1", g.colors_dict.read()["text_light"]
            ).replace(
                "font_size", str(int(14))
            )
            StyleSheet += (
                "QScrollArea, QWidget{background: custom_color;  border-color: black;}".replace(
                    "custom_color", g.colors_dict.read()["background"]
                )
            )
        else:
            StyleSheet = "QDoubleSpinBox{color: custom_color; font: 14px;}".replace(
                "custom_color", colors["text_light"]
            )
            StyleSheet += "QScrollArea, QWidget{color: custom_color_1; border: 1px solid custom_color_2; border-radius: 1px;}".replace(
                "custom_color_1", colors["text_light"]
            ).replace(
                "custom_color_2", colors["widget_background"]
            )
            StyleSheet += "QWidget:disabled{color: custom_color_1; font: 14px; border: 1px solid custom_color_2; border-radius: 1px;}".replace(
                "custom_color_1", colors["text_disabled"]
            ).replace(
                "custom_color_2", colors["widget_background"]
            )
        control.setStyleSheet(StyleSheet)
        control.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        global_object.give_control(control)
        layout.addWidget(control)
        # units combobox
        if global_object.units is not None:
            control.setMinimumWidth(self.width_input - 55)
            control.setMaximumWidth(self.width_input - 55)
            units = QtWidgets.QComboBox()
            units.setMinimumWidth(50)
            units.setMaximumWidth(50)
            StyleSheet = "QComboBox{color: custom_color_1; font: 14px; border: 1px solid custom_color_2; border-radius: 1px;}".replace(
                "custom_color_1", colors["text_light"]
            ).replace(
                "custom_color_2", colors["widget_background"]
            )
            StyleSheet += "QComboBox:disabled{color: custom_color_1; font: 14px; border: 1px solid custom_color_2; border-radius: 1px;}".replace(
                "custom_color_1", colors["text_disabled"]
            ).replace(
                "custom_color_2", colors["widget_background"]
            )
            StyleSheet += (
                "QAbstractItemView{color: custom_color_1; font: 50px solid white;}".replace(
                    "custom_color_1", colors["text_light"]
                ).replace("custom_color_2", colors["widget_background"])
            )
            units.setStyleSheet(StyleSheet)
            layout.addWidget(units)
            global_object.give_units_combo(units)
        # finish
        self.layout().addWidget(container_widget, self.row_number, 1)
        self.controls.append(container_widget)
        self.row_number += 1

    def string(self, name, global_object):
        # heading
        heading = QtWidgets.QLabel(name)
        heading.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        StyleSheet = "QLabel{color: custom_color; font: 14px;}".replace(
            "custom_color", colors["text_light"]
        )
        heading.setStyleSheet(StyleSheet)
        self.layout().addWidget(heading, self.row_number, 0)
        # control
        control = QtWidgets.QLineEdit()
        control.setMinimumWidth(self.width_input)
        control.setMaximumWidth(self.width_input)
        if global_object.display:
            control.setDisabled(True)
            StyleSheet = "QWidget{color: custom_color_1; font: bold 14px; border: 0px solid custom_color_2; border-radius: 1px;}".replace(
                "custom_color_1", colors["text_light"]
            ).replace(
                "custom_color_2", colors["widget_background"]
            )
        else:
            StyleSheet = "QWidget{color: custom_color_1; font: 14px; border: 1px solid custom_color_2; border-radius: 1px;}".replace(
                "custom_color_1", colors["text_light"]
            ).replace(
                "custom_color_2", colors["widget_background"]
            )
            StyleSheet += "QWidget:disabled{color: custom_color_1; font: 14px; border: 1px solid custom_color_2; border-radius: 1px;}".replace(
                "custom_color_1", colors["text_disabled"]
            ).replace(
                "custom_color_2", colors["widget_background"]
            )
        control.setStyleSheet(StyleSheet)
        global_object.give_control(control)
        # finish
        self.layout().addWidget(control, self.row_number, 1)
        self.controls.append(control)
        self.row_number += 1

    def combo(self, name, global_object):
        # heading
        heading = QtWidgets.QLabel(name)
        heading.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        StyleSheet = "QLabel{color: custom_color; font: 14px;}".replace(
            "custom_color", colors["text_light"]
        )
        heading.setStyleSheet(StyleSheet)
        self.layout().addWidget(heading, self.row_number, 0)
        # control
        control = QtWidgets.QComboBox()
        control.setMinimumWidth(self.width_input)
        control.setMaximumWidth(self.width_input)
        if global_object.display:
            control.setDisabled(True)
            StyleSheet = "QComboBox{color: custom_color_1; font: bold 14px; border: 0px solid custom_color_2; border-radius: 1px;}".replace(
                "custom_color_1", colors["text_light"]
            ).replace(
                "custom_color_2", colors["widget_background"]
            )
            # StyleSheet += 'QComboBox:disabled{color: custom_color_1; font: 14px; border: 0px solid custom_color_2; border-radius: 1px;}'.replace('custom_color_1', colors['text_disabled']).replace('custom_color_2', colors['widget_background'])
            StyleSheet += "QAbstractItemView{color: custom_color_1; font: 50px solid white; border: 0px white}".replace(
                "custom_color_1", colors["widget_background"]
            ).replace(
                "custom_color_2", colors["widget_background"]
            )
            StyleSheet += "QComboBox::drop-down{border: 0;}"
        else:
            StyleSheet = "QComboBox{color: custom_color_1; font: 14px; border: 1px solid custom_color_2; border-radius: 1px;}".replace(
                "custom_color_1", colors["text_light"]
            ).replace(
                "custom_color_2", colors["widget_background"]
            )
            StyleSheet += "QComboBox:disabled{color: custom_color_1; font: 14px; border: 1px solid custom_color_2; border-radius: 1px;}".replace(
                "custom_color_1", colors["text_disabled"]
            ).replace(
                "custom_color_2", colors["widget_background"]
            )
            StyleSheet += (
                "QAbstractItemView{color: custom_color_1; font: 50px solid white;}".replace(
                    "custom_color_1", colors["text_light"]
                ).replace("custom_color_2", colors["widget_background"])
            )
        control.setStyleSheet(StyleSheet)
        global_object.give_control(control)
        # finish
        self.layout().addWidget(control, self.row_number, 1)
        self.controls.append(control)
        self.row_number += 1

    def checkbox(self, name, global_object):
        # heading
        heading = QtWidgets.QLabel(name)
        heading.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        StyleSheet = "QLabel{color: custom_color; font: 14px;}".replace(
            "custom_color", colors["text_light"]
        )
        heading.setStyleSheet(StyleSheet)
        self.layout().addWidget(heading, self.row_number, 0)
        # control
        if global_object.display:
            control = Led()
        else:
            control = QtWidgets.QCheckBox()
        global_object.give_control(control)
        # finish
        self.layout().addWidget(control, self.row_number, 1)
        self.controls.append(control)
        self.row_number += 1

    def filepath(self, name, global_object):
        # heading
        heading = QtWidgets.QLabel(name)
        heading.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        StyleSheet = "QLabel{color: custom_color; font: 14px;}".replace(
            "custom_color", colors["text_light"]
        )
        heading.setStyleSheet(StyleSheet)
        self.layout().addWidget(heading, self.row_number, 0)
        # layout
        container_widget = QtWidgets.QWidget()
        container_widget.setLayout(QtWidgets.QHBoxLayout())
        layout = container_widget.layout()
        layout.setMargin(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        # push button
        load_button = QtWidgets.QPushButton("Load")
        StyleSheet = "QPushButton{background:custom_color; border-width:0px;  border-radius: 0px; font: bold 14px}".replace(
            "custom_color", colors["go"]
        )
        load_button.setStyleSheet(StyleSheet)
        load_button.setMinimumHeight(20)
        load_button.setMaximumHeight(20)
        load_button.setMinimumWidth(40)
        load_button.setMaximumWidth(40)
        layout.addWidget(load_button)
        global_object.give_button(load_button)
        # display
        display = QtWidgets.QLineEdit()
        # display.setDisabled(True)
        display.setReadOnly(True)
        display.setMinimumWidth(self.width_input - 45)
        display.setMaximumWidth(self.width_input - 45)
        StyleSheet = "QWidget{color: custom_color_1; font: 14px; border: 1px solid custom_color_2; border-radius: 1px;}".replace(
            "custom_color_1", colors["text_light"]
        ).replace(
            "custom_color_2", colors["widget_background"]
        )
        StyleSheet += "QWidget:disabled{color: custom_color_1; font: 14px; border: 1px solid custom_color_2; border-radius: 1px;}".replace(
            "custom_color_1", colors["text_disabled"]
        ).replace(
            "custom_color_2", colors["widget_background"]
        )
        display.setStyleSheet(StyleSheet)
        layout.addWidget(display)
        global_object.give_control(display)
        # finish
        self.layout().addWidget(container_widget, self.row_number, 1)
        self.controls.append(container_widget)
        self.row_number += 1


class Label(QtWidgets.QLabel):
    def __init__(self, text, color="text_light", bold=False, font_size=14):
        QtWidgets.QLabel.__init__(self, text)
        if bold:
            bold_status = "bold"
        else:
            bold_status = ""
        StyleSheet = f"QLabel{{color: {colors[color]}; font: {bold_status} {font_size}px;}}"
        StyleSheet += f"QLabel:disabled{{color: {colors['text_disabled']}; font: {font_size}px;}}"
        self.setStyleSheet(StyleSheet)


class SetButton(QtWidgets.QPushButton):
    def __init__(self, text, color="go"):
        QtWidgets.QPushButton.__init__(self)
        self.setText(text)
        self.setMinimumHeight(25)
        StyleSheet = "QPushButton{background:custom_color; border-width:0px;  border-radius: 0px; font: bold 14px}".replace(
            "custom_color", colors[color]
        )
        self.setStyleSheet(StyleSheet)


class TableWidget(QtWidgets.QTableWidget):
    def __init__(self):
        QtWidgets.QTableWidget.__init__(self)
        StyleSheet = "QTableWidget::item{padding: 0px}"
        StyleSheet += "QHeaderView::section{background: background_color; color:white; font: bold 14px}".replace(
            "background_color", colors["background"]
        )
        StyleSheet += "QTableWidget{background-color: custom_color;}".replace(
            "custom_color", colors["background"]
        )
        self.setStyleSheet(StyleSheet)


class TabWidget(QtWidgets.QTabWidget):
    def __init__(self):
        QtWidgets.QTabWidget.__init__(self)
        StyleSheet = "QTabBar::tab{width: 130px;}"
        self.setStyleSheet(StyleSheet)


### queue #####################################################################


class ChoiceWindow(QtWidgets.QMessageBox):
    def __init__(self, title, button_labels):
        QtWidgets.QMessageBox.__init__(self)
        self.setWindowTitle(title)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        for label in button_labels:
            self.addButton(label, QtWidgets.QMessageBox.YesRole)
        self.setIcon(self.NoIcon)

    def set_informative_text(self, text):
        self.setInformativeText(text)

    def set_text(self, text):
        self.setText(text)

    def show(self):
        """
        Returns the index of the chosen button
        """
        self.isActiveWindow()
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        return self.exec_()


### plotting ##################################################################


class Plot1D(pg.GraphicsView):
    def __init__(self, title=None, xAutoRange=True, yAutoRange=True):
        pg.GraphicsView.__init__(self)
        # create layout
        self.graphics_layout = pg.GraphicsLayout(border="w")
        self.setCentralItem(self.graphics_layout)
        self.graphics_layout.layout.setSpacing(0)
        self.graphics_layout.setContentsMargins(0.0, 0.0, 1.0, 1.0)
        # create plot object
        self.plot_object = self.graphics_layout.addPlot(0, 0)
        self.labelStyle = {"color": "#FFF", "font-size": "14px"}
        self.x_axis = self.plot_object.getAxis("bottom")
        self.x_axis.setLabel(**self.labelStyle)
        self.y_axis = self.plot_object.getAxis("left")
        self.y_axis.setLabel(**self.labelStyle)
        self.plot_object.showGrid(x=True, y=True, alpha=0.5)
        self.plot_object.setMouseEnabled(False, True)
        self.plot_object.enableAutoRange(x=xAutoRange, y=yAutoRange)
        # title
        if title:
            self.plot_object.setTitle(title)

    def add_scatter(self, color="c", size=3, symbol="o"):
        curve = pg.ScatterPlotItem(symbol=symbol, pen=(color), brush=(color), size=size)
        self.plot_object.addItem(curve)
        return curve

    def add_line(self, color="c", size=3, symbol="o"):
        curve = pg.PlotCurveItem(symbol=symbol, pen=(color), brush=(color), size=size)
        self.plot_object.addItem(curve)
        return curve

    def add_infinite_line(self, color="y", style="solid", angle=90.0, movable=False, hide=True):
        """
        Add an InfiniteLine object.

        Parameters
        ----------
        color : (optional)
            The color of the line. Accepts any argument valid for `pyqtgraph.mkColor <http://www.pyqtgraph.org/documentation/functions.html#pyqtgraph.mkColor>`_. Default is 'y', yellow.
        style : {'solid', 'dashed', dotted'} (optional)
            Linestyle. Default is solid.
        angle : float (optional)
            The angle of the line. 90 is vertical and 0 is horizontal. 90 is default.
        movable : bool (optional)
            Toggles if user can move the line. Default is False.
        hide : bool (optional)
            Toggles if the line is hidden upon initialization. Default is True.

        Returns
        -------
        InfiniteLine object
            Useful methods: setValue, show, hide
        """
        if style == "solid":
            linestyle = QtCore.Qt.SolidLine
        elif style == "dashed":
            linestyle = QtCore.Qt.DashLine
        elif style == "dotted":
            linestyle = QtCore.Qt.DotLine
        else:
            print("style not recognized in add_infinite_line")
            linestyle = QtCore.Qt.SolidLine
        pen = pg.mkPen(color, style=linestyle)
        line = pg.InfiniteLine(pen=pen)
        line.setAngle(angle)
        line.setMovable(movable)
        if hide:
            line.hide()
        self.plot_object.addItem(line)
        return line

    def set_labels(self, xlabel=None, ylabel=None):
        if xlabel:
            self.plot_object.setLabel("bottom", text=xlabel)
            self.plot_object.showLabel("bottom")
        if ylabel:
            self.plot_object.setLabel("left", text=ylabel)
            self.plot_object.showLabel("left")

    def set_xlim(self, xmin, xmax):
        self.plot_object.setXRange(xmin, xmax)

    def set_ylim(self, ymin, ymax):
        self.plot_object.setYRange(ymin, ymax)

    def clear(self):
        self.plot_object.clear()
