import attune
import WrightTools as wt

import somatic.modules.abstract_tuning as abstract_tuning


module_name = "TUNE INTENSITY"


class Worker(abstract_tuning.Worker):
    reference_image = "intensity.png"

    def _process(self, data, curve, channel, gtol, ltol, level, scan_folder, config):
        opa = config["OPA"]["opa"]
        dep = config["Motor"]["motor"]
        data[channel].signed = False
        transform = list(data.axis_expressions)
        transform = transform[:2]
        if level:
            data.level(channel, -1, 5)
        for axis in data.axis_expressions[2:]:
            data.moment(
                axis,
                channel,
                moment=0,
                resultant=wt.kit.joint_shape(data[opa], data[f"{opa}_{dep}_points"]),
            )
            channel = -1
        data.transform(opa, f"{opa}_{dep}_points")
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
        self.items["Spectrometer"]["Action"].set_allowed_values(
            self.items["Spectrometer"]["Action"].allowed_values[1:]
        )


def load():
    return True


def mkGUI():
    global gui
    gui = GUI(module_name)
