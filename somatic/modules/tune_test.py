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
    
    def _process(self, data, curve, channel, gtol, ltol, level, scan_folder, config):
        opa = config["OPA"]["opa"]
        spec = config["Spectral Axis"]["axis"]
        data.transform(opa, f"{opa}-{spec}")
        return attune.workup.tune_test(data, channel, curve, save_directory=scan_folder)
    
 
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
