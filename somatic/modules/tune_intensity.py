import attune

import somatic.acquisition as acquisition
import somatic.modules.abstract_tuning as abstract_tuning


 
module_name = 'TUNE INTENSITY'
 
 
class Worker(abstract_tuning.Worker):

    def _process(self, data, curve, channel, gtol, ltol, level, scan_folder, config):
        dep = config["Motor"]["motor"]
        data[channel].signed = False
        transform = list(data.axis_expressions)
        transform = transform[:2]
        for axis in data.axis_expressions:
            if axis not in transform:
                if level:
                    data.level(axis, 0, 5)
                data.moment(axis, channel)
                channel = -1
        transform[1] = f"{transform[0]}_{dep}_points"
        data.transform(*transform)
        return attune.workup.intensity(
            data,
            channel,
            dep,
            curve,
            level=level,
            gtol=gtol,
            ltol=ltol,
            save_directory=scan_folder,
        )

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
