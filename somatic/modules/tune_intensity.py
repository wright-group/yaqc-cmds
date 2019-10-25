### import ####################################################################


import os

import numpy as np

import WrightTools as wt
import attune

import project.classes as pc
import project.widgets as pw
import somatic.acquisition as acquisition
import somatic.modules.abstract_tuning as abstract_tuning


import hardware.opas.opas as opas
import hardware.spectrometers.spectrometers as spectrometers
import devices.devices as devices

 
### define ####################################################################


module_name = 'TUNE INTENSITY'
 
 
### Worker ####################################################################


class Worker(abstract_tuning.Worker):

    def process(self, scan_folder):
        p = os.path.join(scan_folder, '000.data')
        data = wt.data.from_PyCMDS(p)
        curve = self.curve
        channel = self.aqn.read("process", 'channel')
        data[channel].signed = False
        level = self.aqn.read("process", 'level')
        transform = list(data.axis_expressions)
        dep = self.aqn.read("scan", "motor")
        transform = transform[:2]
        for axis in data.axis_expressions:
            if axis not in transform:
                if level:
                    data.level(axis, 0, 5)
                data.moment(axis, channel)
                channel = -1
        transform[1] = f"{transform[0]}_{dep}_points"
        data.transform(*transform)
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
            p = wt.kit.glob_handler('.curve', folder = str(scan_folder))[0]
            self.opa_hardware.driver.curve_paths[self.curve_id].write(p)

        # upload
        p = wt.kit.glob_handler('.png', folder = str(scan_folder))[0]
        self.upload(scan_folder, reference_image = p)

    def run(self):
        axes = []
        # OPA
        opa_name = self.aqn.read('opa', 'opa')
        opa_names = [opa.name for opa in opas.hardwares]
        opa_index = opa_names.index(opa_name)
        opa_hardware = opas.hardwares[opa_index]
        self.opa_hardware = opa_hardware

        spec_name = self.aqn.read("spectrometer", "hardware")
        spec_names = [spec.name for spec in spectrometers.hardwares]
        spec_index = spec_names.index(spec_name)
        spec_hardware = spectrometers.hardwares[spec_index]
        self.spec_hardware = spec_hardware
        spec_action = self.aqn.read("spectrometer", "action")

        if spec_action == "Zero Order":
            spec_hardware.set_position(0)
            
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
        if spec_action == "Tracking":
            opa_name += f"={spec_name}"
        opa_axis = acquisition.Axis(curve.setpoints[:], 'wn', opa_name, opa_name)
        axes.append(opa_axis)
        axes.append(axis)
        
        self.scan(axes)

                    # finish
        if not self.stopped.read():
            self.finished.write(True)  # only if acquisition successfull

 
### GUI #######################################################################

class GUI(abstract_tuning.GUI):
    def __init__(self, module_name):
        self.items = {}
        self.items["Motor"] = abstract_tuning.MotorAxisSectionWidget("Motor", self)
        super().__init__(module_name)

def load():
    return True

def mkGUI():        
    global gui
    gui = GUI(module_name)
