import attune
import WrightTools as wt

import somatic.modules.abstract_tuning as abstract_tuning

module_name = "TUNE SETPOINT"


class Worker(abstract_tuning.Worker):
    reference_image = "setpoint.png"

    def _process(self, data, curve, channel, gtol, ltol, level, scan_folder, config):

        opa = config["OPA"]["opa"]
        spec = config["Spectral Axis"]["axis"]
        dep = config["Motor"]["motor"]
        data.transform()
        data.transform(opa, f"{opa}_{dep}_points", spec)
        if level:
            data.level(channel, -1, 5)
        curve.convert(data[spec].units)
        data.moment(
            spec,
            moment=1,
            channel=channel,
            resultant=wt.kit.joint_shape(data[opa], data[f"{opa}_{dep}"]),
        )
        channel = -1
        data.channels[-1].clip(data[opa].min() - 1000, data[opa].max() + 1000)
        data.channels[-1].null = data.channels[-1].min()
        data.transform(opa, f"{opa}_{dep}_points")
        return attune.workup.setpoint(
            data,
            channel,
            dep,
            curve,
            # level=level,
            # gtol=gtol,
            # ltol=ltol,
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
        self.items["Processing"]["gtol"].set_disabled(True)
        self.items["Processing"]["ltol"].set_disabled(True)


def load():
    return True


def mkGUI():
    global gui
    gui = GUI(module_name)
