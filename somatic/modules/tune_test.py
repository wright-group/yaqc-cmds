### import ####################################################################

import os

import numpy as np

import matplotlib
matplotlib.pyplot.ioff()

import WrightTools as wt
import attune

import project.project_globals as g
import project.classes as pc
import project.widgets as pw
import somatic.acquisition as acquisition
import somatic.modules.abstract_tuning as abstract_tuning
import project.ini_handler as ini_handler
main_dir = g.main_dir.read()
ini = ini_handler.Ini(os.path.join(main_dir, 'somatic', 'modules', 'tune_test.ini'))
app = g.app.read()

import hardware.opas.opas as opas
import devices.devices as devices

 
### define ####################################################################


module_name = 'TUNE TEST'
 
 
### Worker ####################################################################


class Worker(abstract_tuning.Worker):
    
    def process(self, scan_folder):
        data_path = wt.kit.glob_handler('.data', folder=str(scan_folder))[0]
        data = wt.data.from_PyCMDS(data_path)
        # make tuning curve
        opa_name = self.aqn.read('opa', 'opa')
        opa_names = [opa.name for opa in opas.hardwares]
        opa_index = opa_names.index(opa_name)
        opa = opas.hardwares[opa_index]
        curve = opa.curve.copy()
        if curve.kind == 'poynting':
            curve = curve.subcurve
        channel_name = self.aqn.read('processing', 'channel')
        try:
            order = int(self.aqn.read('spectrometer', 'order'))
        except KeyError:
            order = 1
        transform = list(data.axis_names)
        if order > 0:
            transform[-1] = f"{transform[-1]}_points/{order}"
        else:
            transform[-1] = f"{transform[-1]}_points*{abs(order)}"
        data.transform(*transform)
        attune.workup.tune_test(data, channel_name, curve, save_directory=scan_folder)
        # upload
        self.upload(scan_folder, reference_image=os.path.join(scan_folder, 'tune_test.png'))
    
    def run(self):
        axes = []
        # OPA
        opa_name = self.aqn.read('opa', 'opa')
        opa_names = [opa.name for opa in opas.hardwares]
        opa_index = opa_names.index(opa_name)
        opa_hardware = opas.hardwares[opa_index]
        opa_friendly_name = opa_hardware.name
        curve = opa_hardware.curve.copy()
        curve.convert('wn')
        axis = acquisition.Axis(curve.setpoints[:], 'wn', opa_friendly_name, opa_friendly_name)
        axes.append(axis)
        # mono
        name = 'wm'
        identity = 'Dwm'
        try:
            order = self.aqn.read('spectrometer', 'order')
        except KeyError:
            order = 1
        if order == 0:
            raise ValueError("Spectrometer order cannot be 0")
        elif order > 0:
            kwargs = {'centers': curve.setpoints[:] * self.aqn.read('spectrometer', 'order')}
        else:
            kwargs = {'centers': curve.setpoints[:] / abs(self.aqn.read('spectrometer', 'order'))}
        width = self.aqn.read('spectrometer', 'width')/2.
        npts = self.aqn.read('spectrometer', 'number')
        points = np.linspace(-width, width, npts)
        axis = acquisition.Axis(points, 'wn', name, identity, **kwargs)
        axes.append(axis)
        # do scan
        self.scan(axes)
        # finish
        if not self.stopped.read():
            self.finished.write(True)  # only if acquisition successfull

 
### GUI #######################################################################


class GUI(abstract_tuning.GUI):
    def __init__(self, module_name):
        self.items = {}
        self.items["Spectral Axis"] = abstract_tuning.SpectralAxisSectionWidget("Spectral Axis", self)
        super().__init__(module_name)

def load():
    return True
def mkGUI():        
    global gui
    gui = GUI(module_name)
