### import#####################################################################


import numpy as np

from PyQt4 import QtGui, QtCore
import pyqtgraph as pg
from pyqtgraph import exporters

import project_globals as g

colors = g.colors_dict.read()


### basic elements ############################################################


class vertical_spacer(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        self.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Maximum)
        self.setLayout(QtGui.QVBoxLayout())
        self.setMinimumHeight(0)
        self.layout().setStretchFactor(self, 1)
    def sizeHint(self):
        return QtCore.QSize(1, 16777215)
    def add_to_layout(self, layout):
        layout.addWidget(self)
        layout.setStretchFactor(self, 16777215)

        
class line(QtGui.QFrame):
    '''
    direction: 'V' or 'H'
    '''
    def __init__(self, direction):
        QtGui.QFrame.__init__(self)
        if direction == 'V':
            self.setFrameShape(QtGui.QFrame.VLine)
        else:
            self.setFrameShape(QtGui.QFrame.HLine)
        StyleSheet = 'QFrame{border: 2px solid custom_color; border-radius: 0px; padding: 0px;}'.replace('custom_color', colors['widget_background'])
        self.setStyleSheet(StyleSheet)


class scroll_area(QtGui.QScrollArea):
    def __init__(self):
        QtGui.QScrollArea.__init__(self)
        self.setFrameShape(QtGui.QFrame.NoFrame)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        StyleSheet = 'QScrollArea, QWidget{background: custom_color;}'.replace('custom_color', colors['background'])
        StyleSheet += 'QScrollBar{background: custom_color;}'.replace('custom_color', colors['widget_background'])
        self.setStyleSheet(StyleSheet)

### general ###################################################################


class spinbox_as_display(QtGui.QDoubleSpinBox):
    def __init__(self, font_size = 14, decimals = 6, justify = 'right'):
        QtGui.QDoubleSpinBox.__init__(self)
        self.setValue(0.0)
        self.setDisabled(True)
        self.decimals_input = decimals
        self.setDecimals(decimals)
        self.setMinimum(-100000)
        self.setMaximum(100000)
        if justify == 'right': self.setAlignment(QtCore.Qt.AlignRight)
        else: self.setAlignment(QtCore.Qt.AlignLeft)
        self.setButtonSymbols(QtGui.QAbstractSpinBox.NoButtons)
        StyleSheet = 'QDoubleSpinBox{color: custom_color_1; font: bold font_sizepx; border: 0px solid #000000;}'.replace('custom_color_1', g.colors_dict.read()['text_light']).replace('font_size', str(int(font_size)))
        StyleSheet += 'QScrollArea, QWidget{background: custom_color;  border-color: black;}'.replace('custom_color', g.colors_dict.read()['background'])                
        self.setStyleSheet(StyleSheet)
    '''
    def textFromValue(self, value):
        return "{:.xf}".replace('x', int(self.decimals_input)).format(value)
    '''


class Shutdown_button(QtGui.QPushButton):
    shutdown_go = QtCore.pyqtSignal()
    def __init__(self):
        QtGui.QPushButton.__init__(self)
        self.clicked.connect(self.initiate_shutdown)
        self.setText('SHUT DOWN')
        StyleSheet = 'QPushButton{background:custom_color; border-width:0px;  border-radius: 0px; font: bold 14px}'.replace('custom_color', colors['stop'])
        self.setStyleSheet(StyleSheet)
    def initiate_shutdown(self):
        self.setText('SHUTTING DOWN')
        g.app.read().processEvents()
        self.shutdown_go.emit()
        

class InputTable(QtGui.QWidget):

    def __init__(self, width = 130):
        '''
        accepts a list of inputs with format [[names], 
        type, global object, [additional]] \n
        each global object must have an updated signal \n
        heading: [None] \n
        number: [minimum, maximum, decimals, single step] \n
        '''
        QtGui.QWidget.__init__(self)
        self.width_input = width
        self.setLayout(QtGui.QGridLayout())
        self.layout().setColumnMinimumWidth(0, width)
        self.layout().setColumnMinimumWidth(1, width)
        self.layout().setMargin(0)
        self.row_number = 0
        self.controls = []

    def add(self, name, global_object):
        if global_object is None:
            global_type = 'heading'
        else:
            global_type = global_object.type
        getattr(self, global_type)(name, global_object)

    def busy(self, name, global_object):
        # heading
        heading = QtGui.QLabel(name)
        StyleSheet = 'QLabel{color: custom_color; font: bold 14px;}'.replace('custom_color', colors['heading_0'])
        heading.setStyleSheet(StyleSheet)
        self.layout().addWidget(heading, self.row_number, 0)
        # control
        control = QtGui.QCheckBox()
        local_busy_display = BusyDisplay(global_object, global_object.update_signal)
        # finish
        self.layout().addWidget(local_busy_display, self.row_number, 1)
        self.controls.append(control)
        self.row_number += 1

    def heading(self, name, global_object):
        # heading
        heading = QtGui.QLabel(name)
        StyleSheet = 'QLabel{color: custom_color; font: bold 14px;}'.replace('custom_color', colors['heading_0'])
        heading.setStyleSheet(StyleSheet)
        self.layout().addWidget(heading, self.row_number, 0)
        self.controls.append(None)
        self.row_number += 1

    def number(self, name, global_object):
        # heading
        label = QtGui.QLabel(name)
        StyleSheet = 'QLabel{color: custom_color; font: 14px;}'.replace('custom_color', colors['text_light'])
        label.setStyleSheet(StyleSheet)
        self.layout().addWidget(label, self.row_number, 0)
        #layout
        container_widget = QtGui.QWidget()
        container_widget.setLayout(QtGui.QHBoxLayout())
        layout = container_widget.layout()
        layout.setMargin(0)
        layout.setContentsMargins(0, 0, 0, 0)
        #control
        control = QtGui.QDoubleSpinBox()
        if global_object.display:
            control.setDisabled(True)
            StyleSheet = 'QDoubleSpinBox{color: custom_color_1; font: bold font_sizepx; border: 0px solid #000000;}'.replace('custom_color_1', g.colors_dict.read()['text_light']).replace('font_size', str(int(14)))
            StyleSheet += 'QScrollArea, QWidget{background: custom_color;  border-color: black;}'.replace('custom_color', g.colors_dict.read()['background'])                
        else:
            StyleSheet = 'QDoubleSpinBox{color: custom_color; font: 14px;}'.replace('custom_color', colors['text_light'])
            StyleSheet += 'QScrollArea, QWidget{color: custom_color_1; border: 1px solid custom_color_2; border-radius: 1px;}'.replace('custom_color_1', colors['text_light']).replace('custom_color_2', colors['widget_background'])
            StyleSheet += 'QWidget:disabled{color: custom_color_1; font: 14px; border: 1px solid custom_color_2; border-radius: 1px;}'.replace('custom_color_1', colors['text_disabled']).replace('custom_color_2', colors['widget_background'])                
        control.setStyleSheet(StyleSheet) 
        control.setButtonSymbols(QtGui.QAbstractSpinBox.NoButtons)
        global_object.give_control(control)
        layout.addWidget(control)
        #units combobox
        if not global_object.units_kind == None:
            control.setMinimumWidth(self.width_input - 55)
            units = QtGui.QComboBox()
            units.setMinimumWidth(50)
            units.setMaximumWidth(50)
            StyleSheet = 'QComboBox{color: custom_color_1; font: 14px; border: 1px solid custom_color_2; border-radius: 1px;}'.replace('custom_color_1', colors['text_light']).replace('custom_color_2', colors['widget_background'])
            StyleSheet += 'QComboBox:disabled{color: custom_color_1; font: 14px; border: 1px solid custom_color_2; border-radius: 1px;}'.replace('custom_color_1', colors['text_disabled']).replace('custom_color_2', colors['widget_background'])
            StyleSheet += 'QAbstractItemView{color: custom_color_1; font: 50px solid white;}'.replace('custom_color_1', colors['text_light']).replace('custom_color_2', colors['widget_background'])       
            units.setStyleSheet(StyleSheet)
            layout.addWidget(units)
            global_object.give_units_combo(units)
        #finish
        self.layout().addWidget(container_widget, self.row_number, 1)
        self.controls.append(container_widget)
        self.row_number += 1

    def string(self, name, global_object):
        #heading
        heading = QtGui.QLabel(name)
        StyleSheet = 'QLabel{color: custom_color; font: 14px;}'.replace('custom_color', colors['text_light'])
        heading.setStyleSheet(StyleSheet)
        self.layout().addWidget(heading, self.row_number, 0)
        #control
        control = QtGui.QLineEdit()
        if global_object.display:
            control.setDisabled(True)
            StyleSheet = 'QWidget{color: custom_color_1; font: bold 14px; border: 0px solid custom_color_2; border-radius: 1px;}'.replace('custom_color_1', colors['text_light']).replace('custom_color_2', colors['widget_background'])
        else:
            StyleSheet = 'QWidget{color: custom_color_1; font: 14px; border: 1px solid custom_color_2; border-radius: 1px;}'.replace('custom_color_1', colors['text_light']).replace('custom_color_2', colors['widget_background'])
            StyleSheet += 'QWidget:disabled{color: custom_color_1; font: 14px; border: 1px solid custom_color_2; border-radius: 1px;}'.replace('custom_color_1', colors['text_disabled']).replace('custom_color_2', colors['widget_background'])
        control.setStyleSheet(StyleSheet)
        global_object.give_control(control)
        #finish
        self.layout().addWidget(control, self.row_number, 1)
        self.controls.append(control)
        self.row_number += 1

    def combo(self, name, global_object):
        #heading
        heading = QtGui.QLabel(name)
        StyleSheet = 'QLabel{color: custom_color; font: 14px;}'.replace('custom_color', colors['text_light'])
        heading.setStyleSheet(StyleSheet)
        self.layout().addWidget(heading, self.row_number, 0)
        #control
        control = QtGui.QComboBox()
        StyleSheet = 'QComboBox{color: custom_color_1; font: 14px; border: 1px solid custom_color_2; border-radius: 1px;}'.replace('custom_color_1', colors['text_light']).replace('custom_color_2', colors['widget_background'])
        StyleSheet += 'QComboBox:disabled{color: custom_color_1; font: 14px; border: 1px solid custom_color_2; border-radius: 1px;}'.replace('custom_color_1', colors['text_disabled']).replace('custom_color_2', colors['widget_background'])
        StyleSheet += 'QAbstractItemView{color: custom_color_1; font: 50px solid white;}'.replace('custom_color_1', colors['text_light']).replace('custom_color_2', colors['widget_background'])       
        control.setStyleSheet(StyleSheet)
        global_object.give_control(control)      
        #finish
        self.layout().addWidget(control, self.row_number, 1)
        self.controls.append(control)
        self.row_number += 1

    def checkbox(self, name, global_object):
        #heading
        heading = QtGui.QLabel(name)
        StyleSheet = 'QLabel{color: custom_color; font: 14px;}'.replace('custom_color', colors['text_light'])
        heading.setStyleSheet(StyleSheet)
        self.layout().addWidget(heading, self.row_number, 0)
        #control
        control = QtGui.QCheckBox()
        #StyleSheet = 'QWidget{color: custom_color_1; font: 14px; border: 1px solid custom_color_2; border-radius: 1px;}'.replace('custom_color_1', colors['text_light']).replace('custom_color_2', colors['widget_background'])
        #control.setStyleSheet(StyleSheet)
        global_object.give_control(control)
        #finish
        self.layout().addWidget(control, self.row_number, 1)
        self.controls.append(control)
        self.row_number += 1

    def filepath(self, name, global_object):
        #heading
        heading = QtGui.QLabel(name)
        StyleSheet = 'QLabel{color: custom_color; font: 14px;}'.replace('custom_color', colors['text_light'])
        heading.setStyleSheet(StyleSheet)
        self.layout().addWidget(heading, self.row_number, 0)
        #layout
        container_widget = QtGui.QWidget()
        container_widget.setLayout(QtGui.QHBoxLayout())
        layout = container_widget.layout()
        layout.setMargin(0)
        layout.setContentsMargins(0, 0, 0, 0)
        #push button
        load_button = QtGui.QPushButton('Load')
        StyleSheet = 'QPushButton{background:custom_color; border-width:0px;  border-radius: 0px; font: bold 14px}'.replace('custom_color', colors['go'])
        load_button.setStyleSheet(StyleSheet)
        layout.addWidget(load_button)
        global_object.give_button(load_button)
        #display
        display = QtGui.QLineEdit()
        display.setDisabled(True)
        StyleSheet = 'QWidget{color: custom_color_1; font: 14px; border: 1px solid custom_color_2; border-radius: 1px;}'.replace('custom_color_1', colors['text_light']).replace('custom_color_2', colors['widget_background'])
        StyleSheet += 'QWidget:disabled{color: custom_color_1; font: 14px; border: 1px solid custom_color_2; border-radius: 1px;}'.replace('custom_color_1', colors['text_disabled']).replace('custom_color_2', colors['widget_background'])
        display.setStyleSheet(StyleSheet)
        layout.addWidget(display)
        global_object.give_control(display)
        #finish
        self.layout().addWidget(container_widget, self.row_number, 1)
        self.controls.append(container_widget)
        self.row_number += 1


### hardware ##################################################################

class BusyDisplay(QtGui.QPushButton):
    '''
    access value object to get state
    
    True: scan running
    
    pause methods are built in to this object
    '''
    def __init__(self, busy_object, update_signal):
        QtGui.QPushButton.__init__(self)
        self.busy_object = busy_object
        update_signal.connect(self.update)        
        self.setText('READY')
        self.setMinimumHeight(15)
        self.setMaximumHeight(15)
        StyleSheet = 'QPushButton{background:background_color; border-width:0px;  border-radius: 0px; font: bold 14px; color: text_color}'.replace('background_color', colors['background']).replace('text_color', colors['background'])
        self.setStyleSheet(StyleSheet)
        self.update()
    def update(self):
        if self.busy_object.read():
            self.setText('BUSY')
            StyleSheet = 'QPushButton{background:background_color; border-width:0px;  border-radius: 0px; font: bold 14px; color: text_color; text-align: left}'.replace('background_color', colors['background']).replace('text_color', colors['stop'])
            self.setStyleSheet(StyleSheet)
        else: 
            self.setText('READY')
            StyleSheet = 'QPushButton{background:background_color; border-width:0px;  border-radius: 0px; font: bold 14px; color: text_color}'.replace('background_color', colors['background']).replace('text_color', colors['background'])
            self.setStyleSheet(StyleSheet)        

class Hardware_control_table(QtGui.QWidget):

    def __init__(self, hardware_names, combobox=False, combobox_label=''):
        QtGui.QWidget.__init__(self)
        self.setLayout(QtGui.QGridLayout())
        self.layout().setMargin(0)
        self.comboboxes = []
        self.current_position_displays = []
        self.new_position_controls = []
        self.set_buttons = []
        for i in range(len(hardware_names)):
            #names
            collumn = 0
            label = QtGui.QLabel(hardware_names[i])
            StyleSheet = 'QLabel{color: custom_color; font: bold 14px;}'.replace('custom_color', colors['heading_0'])
            label.setStyleSheet(StyleSheet)
            self.layout().addWidget(label, i, collumn)
            #comboboxes
            if combobox:
                collumn += 1
                combobox_obj = QtGui.QComboBox()
                self.layout().addWidget(combobox_obj, i, collumn)
                self.comboboxes.append(combobox_obj)
            #current
            collumn += 1
            current_position = QtGui.QDoubleSpinBox()
            current_position.setButtonSymbols(QtGui.QAbstractSpinBox.NoButtons)
            current_position.setDisabled(True)
            self.layout().addWidget(current_position, i, collumn)
            self.current_position_displays.append(current_position)
            #new
            collumn += 1
            new_position = QtGui.QDoubleSpinBox()
            new_position.setButtonSymbols(QtGui.QAbstractSpinBox.NoButtons)
            self.layout().addWidget(new_position, i, collumn)
            self.new_position_controls.append(new_position)
            self.set_allowed_values(i, 0, 10000, 2, 10)

    def set_allowed_values(self, index, min_val, max_val, decimals=2, single_step=1.00):
        controls = [self.current_position_displays[index], self.new_position_controls[index]]
        for control in controls:
            control.setMinimum(min_val)
            control.setMaximum(max_val)
            control.setDecimals(decimals)
            control.setSingleStep(single_step)


class HardwareLayoutWidget(QtGui.QGroupBox):

    def __init__(self, name, update_signal):
        QtGui.QGroupBox.__init__(self)
        # layout
        self.setLayout(QtGui.QVBoxLayout())
        self.layout().setMargin(5)
        # container
        heading_container = QtGui.QWidget()
        heading_container.setLayout(QtGui.QHBoxLayout())
        heading_container.layout().setMargin(0)
        # add heading
        heading = QtGui.QLabel(name)
        StyleSheet = 'QLabel{color: custom_color; font: bold 14px;}'.replace('custom_color', colors['heading_1'])
        heading.setStyleSheet(StyleSheet)
        heading_container.layout().addWidget(heading)
        self.layout().addWidget(heading_container)
        
    def add_buttons(self, set_method, advanced_method, hardwares=[]):
        # layout
        button_container = QtGui.QWidget()
        button_container.setLayout(QtGui.QHBoxLayout())
        button_container.layout().setMargin(0)
        # advanced
        advanced_button = QtGui.QPushButton()
        advanced_button.setText('ADVANCED')
        advanced_button.setMinimumHeight(25)
        StyleSheet = 'QPushButton{background:custom_color; border-width:0px;  border-radius: 0px; font: bold 14px}'.replace('custom_color', colors['advanced'])
        advanced_button.setStyleSheet(StyleSheet)
        button_container.layout().addWidget(advanced_button)
        advanced_button.clicked.connect(advanced_method)
        # set
        set_button = QtGui.QPushButton()
        set_button.setText('SET')
        set_button.setMinimumHeight(25)
        StyleSheet = 'QPushButton{background:custom_color; border-width:0px;  border-radius: 0px; font: bold 14px}'.replace('custom_color', colors['set'])
        set_button.setStyleSheet(StyleSheet)
        # add
        self.layout().addWidget(button_container)
        # connect to signals
        g.module_control.disable_when_true(set_button)
        button_container.layout().addWidget(set_button)
        set_button.clicked.connect(set_method)
        for hardware in hardwares:
            set_button.setDisabled(hardware.busy.read())  # first time
            hardware.update_ui.connect(lambda: set_button.setDisabled(hardware.busy.read()))
            

### module ####################################################################
        

class module_combobox(QtGui.QComboBox):
    shutdown_go = QtCore.pyqtSignal()
    def __init__(self):
        QtGui.QComboBox.__init__(self)
        StyleSheet = 'QComboBox{font: bold 14px}'#.replace('custom_color', colors['background'])
        self.setStyleSheet(StyleSheet)

      
class module_go_button(QtGui.QPushButton):
    launch_scan = QtCore.pyqtSignal()
    stop_scan = QtCore.pyqtSignal()
    '''
    access value object to get state
    
    True: scan running
    
    pause methods are built in to this object
    '''
    def __init__(self):
        QtGui.QPushButton.__init__(self)
        self.clicked.connect(self.update)
        self.setMinimumHeight(25)
        self.custom_style_maker('GO', 'go')
        self.value = False
    def update(self):
        if self.value:
            #pause or stop scan
            self.pause_or_stop()
        else:
            #begin scan
            self.custom_style_maker('STOP', 'stop')
            self.value = True
            self.launch_scan_method()
    def give_launch_scan_method(self, method):
        self.launch_scan_method = method
    def give_stop_scan_method(self, method):
        self.stop_scan_method = method
    def give_scan_complete_signal(self, signal):
        signal.connect(self.scan_complete)
    def give_pause_objects(self, pause, paused):
        self.pause_object = pause
        self.paused_object = paused
    def give_going_objects(self, go, going):
        self.go_object = go
        self.going_object = going
    def custom_style_maker(self, text, color):
        self.setText(text)
        StyleSheet = 'QPushButton{background:custom_color; border-width:0px;  border-radius: 0px; font: bold 14px}'.replace('custom_color', colors[color])
        self.setStyleSheet(StyleSheet)
    def pause_or_stop(self):
        self.pause_object.write(True)
        self.wait_for_scan_to_pause()
        my_window = choice_window()
        answer = my_window.say('PAUSED', 'Do you wish to continue or stop?', ['CONTINUE', 'STOP'], icon = 'Question')  
        self.pause_object.write(False)        
        if answer == 1: self.stop_scan_method()
        else: self.custom_style_maker('STOP', 'stop')
    def wait_for_scan_to_pause(self):
        self.clicked.disconnect(self.update)
        self.setText('WAIT')
        g.app.read().processEvents()
        print 'here', self.paused_object.read()
        while not self.paused_object.read(): self.paused_object.wait_for_update()
        self.clicked.connect(self.update)
    def scan_complete(self):
        self.value = False
        self.custom_style_maker('GO', 'go')


### plotting ##################################################################


class plot_1D(pg.GraphicsView):
    
    def __init__(self, title = None):
        pg.GraphicsView.__init__(self)
        #create layout
        self.graphics_layout = pg.GraphicsLayout(border = 'w')
        self.setCentralItem(self.graphics_layout)
        self.graphics_layout.layout.setSpacing(0.)                                                             
        self.graphics_layout.setContentsMargins(0., 0., 1., 1.)
        #create plot object
        self.plot_object = self.graphics_layout.addPlot(0, 0)
        self.plot_object.showGrid(x = True, y = True, alpha = 0.5)
        self.plot_object.setMouseEnabled(False, True)
        #title
        if title: 
            self.plot_object.setTitle(title)
            
    def add_scatter(self, color = 'c', size = 3, symbol = 'o'):
        curve = pg.ScatterPlotItem(symbol=symbol, pen=(color), brush=(color), size=size)
        self.plot_object.addItem(curve)
        return curve 
        
    def add_curve(self, color = 'c', size = 3):
        curve = pg.PlotCurveItem(pen=(color), brush=(color), size=size)
        self.plot_object.addItem(curve)
        return curve 
        
    def add_line(self, color = 'y', angle = 90, movable = False):
        '''
        returns a hidden InfiniteLine object \n
        useful methods of returned object: setValue(), show(), hide()
        '''
        line = pg.InfiniteLine(pen=(color))
        line.setAngle(angle)
        line.setMovable(movable)
        line.hide()
        self.plot_object.addItem(line)
        return line  
        
    def set_labels(self, xlabel = None, ylabel = None):
        if xlabel:
            self.plot_object.setLabel('bottom', text=xlabel)
            self.plot_object.showLabel('bottom')
        if ylabel:
            self.plot_object.setLabel('left', text=ylabel)
            self.plot_object.showLabel('left')
            
    def clear(self):
        self.plot_object.clear()

        
### pop-ups ###################################################################


class choice_window(QtGui.QMessageBox):

    def __init__(self):
        QtGui.QMessageBox.__init__(self)

    def say(self, window_title, text, buttons, icon = 'NoIcon', informative_text=''):
        '''
        icon choices: NoIcon, Question, Information, Warning, Critical \n
        returns index of button chosen as integer
        '''
        #self.size()
        self.setWindowTitle(window_title)
        self.setText(text)
        self.setInformativeText(informative_text)
        self.setIcon(getattr(self, icon))
        for label in buttons:
            my_button = QtGui.QPushButton(label)
            self.addButton(my_button, QtGui.QMessageBox.YesRole)
        self.isActiveWindow()
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        return self.exec_()


class wait_window(QtGui.QMessageBox):

    def __init__(self, wait_for, text='', wait_to_be='True'):
        '''
        waits for a boolean to be true or false
        '''
        QtGui.QMessageBox.__init__(self)
        self.setWindowTitle('wait')
        self.setText('wait wait wait')
        self.isActiveWindow()
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        print 'here', wait_for.read()
        if wait_to_be == 'True':
            while not wait_for.read():
                self.show()
                wait_for.wait_for_update()
            self.close()
        else:
            while wait_for.read():
                self.show()
                wait_for.wait_for_update()
            self.close()
