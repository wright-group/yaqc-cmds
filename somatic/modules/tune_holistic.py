import attune

import somatic.modules.abstract_tuning as abstract_tuning


### define ####################################################################


module_name = 'TUNE HOLISTIC'
 
 
### Worker ####################################################################


class Worker(abstract_tuning.Worker):

    def _process(self, data, curve, channel, gtol, ltol, level, scan_folder, config):
        opa = config["OPA"]["opa"]
        spec = config["Spectral Axis"]["axis"]
        data.transform(motor0, motor1, spec)
        return attune.workup.holistic(
            data,
            channel,
            curve,
            level=level,
            gtol=gtol,
            ltol=ltol,
            save_directory=scan_folder,
        )

 
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
