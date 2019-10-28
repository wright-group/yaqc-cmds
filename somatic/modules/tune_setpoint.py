import attune

import somatic.modules.abstract_tuning as abstract_tuning

module_name = "TUNE SETPOINT"


class Worker(abstract_tuning.Worker):
    def process(self, data, curve, channel, gtol, ltol, level, scan_folder, config):

        opa = config["OPA"]["opa"]
        spec = config["Spectral Axis"]["axis"]
        #TODO transform then moment then transform
        data.transform(opa, f"{opa}-{spec}")
        return attune.workup.tune_test(
            data,
            channel,
            curve,
            level=level,
            gtol=gtol,
            ltol=ltol,
            save_directory=scan_folder,
        )


class GUI(abstract_tuning.GUI):
    def __init__(self, module_name):
        self.items = {}
        self.items["Spectral Axis"] = abstract_tuning.SpectralAxisSectionWidget(
            "Spectral Axis", self
        )
        self.items["Motor"] = abstract_tuning.MotorAxisSectionWidget("Motor", self)
        super().__init__(module_name)


def load():
    return True


def mkGUI():
    global gui
    gui = GUI(module_name)
