### import ####################################################################


import configparser
import os

import numpy as np

import WrightTools as wt
import attune

import project.project_globals as g
import project.classes as pc
import project.widgets as pw
import somatic.acquisition as acquisition
import project.ini_handler as ini_handler
main_dir = g.main_dir.read()
ini = ini_handler.Ini(os.path.join(main_dir, 'somatic', 'modules', 'tune_test.ini'))
app = g.app.read()

import hardware.opas.opas as opas
import hardware.spectrometers.spectrometers as spectrometers
import devices.devices as devices

 
### define ####################################################################


module_name = 'AUTOTUNE'
 
 
### Worker ####################################################################


class Worker(acquisition.Worker):

    def process(self, scan_folder):
        p = os.path.join(scan_folder, '000.data')
        data = wt.data.from_PyCMDS(p)
        curve = self.curve
        channel = self.aqn.read("process", 'channel')
        transform = list(data.axis_names)
        dep = self.aqn.read("scan", "motor")
        transform[-1] = f"{transform[0]}_{dep}_points"
        data.transform(*transform)
        data[channel].signed = False
        attune.workup.intensity(
            data,
            channel,
            dep,
            curve,
            save_directory=scan_folder,
            level=self.aqn.read("process", "level"),
            gtol=self.aqn.read("process", "gtol"),
            ltol=self.aqn.read("process", "ltol"),
        )

        if not self.stopped.read() and self.aqn.read("process", "apply"):
            p = wt.kit.glob_handler('.curve', folder = scan_folder)[0]
            self.opa_hardware.driver.curve_paths[self.curve_id].write(p)

        # upload
        p = wt.kit.glob_handler('.png', folder = scan_folder)[0]
        self.upload(scan_folder, reference_image = p)

    def run(self):
        axes = []
        # OPA
        opa_name = self.aqn.read('opa', 'opa')
        opa_names = [opa.name for opa in opas.hardwares]
        opa_index = opa_names.index(opa_name)
        opa_hardware = opas.hardwares[opa_index]
        self.opa_hardware = opa_hardware

        # mono
        for spec in spectrometers.hardwares:
            spec.set_position(0)
            
        section = "scan"
        name = self.aqn.read(section, "motor")
        curve = opa_hardware.curve.copy()
        self.curve = curve
        while not name in curve.dependent_names:
            curve = curve.subcurve
        curve.convert("wn")
        width = self.aqn.read(section,'width')
        npts = int(self.aqn.read(section,'number'))
        points = np.linspace(-width/2.,width/2., npts)
        motor_positions = curve[name][:]
        kwargs = {'centers': motor_positions}
        hardware_dict = {opa_name: [opa_hardware, 'set_motor', [name, 'destination']]}
        axis = acquisition.Axis(points, None, opa_name+'_'+name, 'D'+opa_name, hardware_dict, **kwargs)
                

        curve_ids = list(opa_hardware.driver.curve_paths.keys())
        while not name in curve.dependent_names:
            curve = curve.subcurve
            curve_ids = curve_ids[:-1]
        self.curve_id = curve_ids[-1]
        curve.convert('wn')                    
        
        axes = []
        # Note: if the top level curve covers different ranges than the subcurves,
        # This will behave quite poorly...
        # It will need to be changed to accomodate more complex hierarchies, e.g. TOPAS
        # It should handle top level curves, even for topas, though
        # 2019-08-28 KFS
        # Also, if the current interaction string is the one which defines the motor, should be fine
        opa_axis = acquisition.Axis(curve.setpoints[:], 'wn', opa_name, opa_name)
        axes.append(opa_axis)
        axes.append(axis)
        
        scan_folder = self.scan(axes)

                    # finish
        if not self.stopped.read():
            self.finished.write(True)  # only if acquisition successfull

 
### GUI #######################################################################

class GUI(acquisition.GUI):

    def create_frame(self):
        input_table = pw.InputTable()
        # opa combo
        allowed = [hardware.name for hardware in opas.hardwares]
        if not allowed:
            return
        self.opa_combo = pc.Combo(allowed)
        self.opa_combo.updated.connect(self.on_opa_combo_updated)
        input_table.add('OPA', self.opa_combo)

        self.layout.addWidget(input_table)

        # motor selection
        self.opa_guis = [OPA_GUI(hardware, self.layout) for hardware in opas.hardwares]
        self.opa_guis[0].show()

        input_table = pw.InputTable()

        # finish
        self.layout.addWidget(input_table)
        
    def load(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        self.opa_combo.write(aqn.read('opa', 'opa'))
        opa_gui = self.opa_guis[self.opa_combo.read_index()]
        opa_gui.motor.write(aqn.read("scan", 'motor'))
        opa_gui.width.write(aqn.read("scan", 'width'))
        opa_gui.number.write(aqn.read("scan", 'number'))
        opa_gui.channel_combo.write(aqn.read("process", 'channel'))
        opa_gui.process_level.write(aqn.read("process", "level"))
        opa_gui.process_gtol.write(aqn.read("process", "gtol"))
        opa_gui.process_ltol.write(aqn.read("process", "ltol"))
        opa_gui.process_apply.write(aqn.read("process", "apply"))
        # allow devices to load settings
        self.device_widget.load(aqn_path)
        
    def on_opa_combo_updated(self):
        self.show_opa_gui(self.opa_combo.read_index())

    def show_opa_gui(self, index):
        for gui in self.opa_guis:
            gui.hide()
        self.opa_guis[index].show()

    def on_device_settings_updated(self):
        for gui in self.opa_guis:
            gui.channel_combo.set_allowed_values(devices.control.channel_names)
        
    def save(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        aqn.write('info', 'description', '{} Auto Tune'.format(self.opa_combo.read()))
        aqn.add_section('opa')
        aqn.write('opa', 'opa', self.opa_combo.read())

        opa_gui = self.opa_guis[self.opa_combo.read_index()]
        aqn.add_section("scan")
        aqn.write("scan", 'motor', opa_gui.motor_gui.motor.read())
        aqn.write("scan", 'width', opa_gui.motor_gui.width.read())
        aqn.write("scan", 'number', opa_gui.motor_gui.number.read())
        aqn.add_section("process")
        aqn.write("process", 'channel', opa_gui.channel_combo.read())
        aqn.write("process", 'level', opa_gui.process_level.read())
        aqn.write("process", 'gtol', opa_gui.process_gtol.read())
        aqn.write("process", 'ltol', opa_gui.process_ltol.read())
        aqn.write("process", 'apply', opa_gui.process_apply.read())
        # allow devices to write settings
        self.device_widget.save(aqn_path)

class OPA_GUI():
    def __init__(self,hardware,layout):
        self.hardware = hardware
        curve = self.hardware.curve
        motor_names = curve.dependent_names
        self.motors = []
        self.motor_gui = MotorGUI(motor_names, 1,31)
        layout.addWidget(self.motor_gui.input_table)
        self.process_gui = pw.InputTable()

        self.process_gui.add('Processing', None)
        self.channel_combo = pc.Combo(allowed_values=devices.control.channel_names)
        self.process_gui.add('Channel', self.channel_combo)

        self.process_level = pc.Bool(initial_value=False)
        self.process_gtol = pc.Number(initial_value=1e-3, decimals=5)
        self.process_ltol = pc.Number(initial_value=1e-1, decimals=5)
        self.process_apply = pc.Bool(initial_value=True)
        self.process_gui.add('level', self.process_level)
        self.process_gui.add('gtol', self.process_gtol)
        self.process_gui.add('ltol', self.process_ltol)
        self.process_gui.add('apply curve', self.process_apply)
        layout.addWidget(self.process_gui)


        self.hide()

    def hide(self):
        self.motor_gui.input_table.hide()
        self.process_gui.hide()
    def show(self):
        self.motor_gui.input_table.show()
        self.process_gui.show()

class MotorGUI():
    def __init__(self, motor_names, width, number):
        self.input_table = pw.InputTable()

        self.motor = pc.Combo(allowed_values=motor_names)
        self.input_table.add('Motor', self.motor)

        self.width = pc.Number(initial_value = width, decimals = 3)
        self.input_table.add('Width', self.width)

        self.number = pc.Number(initial_value = number, decimals = 0)
        self.input_table.add('Number', self.number)
        
        
def load():
    return True

def mkGUI():        
    global gui
    gui = GUI(module_name)
