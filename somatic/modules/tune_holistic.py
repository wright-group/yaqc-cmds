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


module_name = 'TUNE HOLISTIC'
 
 
### Worker ####################################################################


class Worker(abstract_tuning.Worker):

    def process(self, scan_folder):
        pass

    def run(self):
        pass

 
### GUI #######################################################################

class GUI(abstract_tuning.GUI):
    def __init__(self, module_name):
        self.items = {}
        self.items["Spectral Axis"] = abstract_tuning.SpectralAxisSectionWidget("Spectral Axis", self)
        self.items["Motor0"] = abstract_tuning.MotorAxisSectionWidget("Motor0", self)
        self.items["Motor1"] = abstract_tuning.MotorAxisSectionWidget("Motor1", self)
        super().__init__(module_name)

def load():
    return True

def mkGUI():        
    global gui
    gui = GUI(module_name)
