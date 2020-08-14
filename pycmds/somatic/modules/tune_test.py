import attune

import somatic.modules.abstract_tuning as abstract_tuning

module_name = "TUNE TEST"


class Worker(abstract_tuning.Worker):
    reference_image = "tune_test.png"

    def _process(self, data, curve, channel, gtol, ltol, level, scan_folder, config):
        opa = config["OPA"]["opa"]
        spec = config["Spectral Axis"]["axis"]
        data.transform(opa, f"{spec}-{opa}")
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
        super().__init__(module_name)


def load():
    return True


def mkGUI():
    global gui
    gui = GUI(module_name)
