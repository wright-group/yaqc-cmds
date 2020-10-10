import attune

import somatic.modules.abstract_tuning as abstract_tuning
import yaqc_cmds.project.classes as pc
import yaqc_cmds.hardware.opas as opas


### define ####################################################################


module_name = "TUNE HOLISTIC"


### Worker ####################################################################


class Worker(abstract_tuning.Worker):
    reference_image = "holistic.png"

    def _process(self, data, curve, channel, gtol, ltol, level, scan_folder, config):
        spec = config["Spectral Axis"]["axis"]
        opa = config["OPA"]["opa"]
        motor0 = config["Motor0"]["motor"]
        motor1 = config["Motor1"]["motor"]
        data.transform()
        data.transform(f"{opa}_{motor0}", f"{opa}_{motor1}", spec)
        return attune.workup.holistic(
            data,
            channel,
            [motor0, motor1],
            curve,
            level=level,
            gtol=gtol,
            # ltol=ltol,
            save_directory=scan_folder,
        )


### GUI #######################################################################


class GUI(abstract_tuning.GUI):
    def __init__(self, module_name):
        self.items = {}
        self.items["Spectral Axis"] = abstract_tuning.SpectralAxisSectionWidget(
            "Spectral Axis", self
        )
        self.items["Motor0"] = ProxyMotorAxisSectionWidget("Motor0", self)
        self.items["Motor1"] = abstract_tuning.MotorAxisSectionWidget("Motor1", self)
        super().__init__(module_name)
        self.items["Processing"]["ltol"].set_disabled(True)


class ProxyMotorAxisSectionWidget(abstract_tuning.AqnSectionWidget):
    def __init__(self, section_name, parent):
        super().__init__(section_name, parent)
        self.items["Motor"] = pc.Combo()

    def on_update(self):
        hardware = next(h for h in opas.hardwares if h.name == self.parent["OPA"]["OPA"].read())
        self.items["Motor"].set_allowed_values(hardware.curve.dependent_names)


def load():
    return True


def mkGUI():
    global gui
    gui = GUI(module_name)
