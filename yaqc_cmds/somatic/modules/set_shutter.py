### import ####################################################################

import WrightTools as wt

import yaqc_cmds.project.classes as pc
import yaqc_cmds.project.widgets as pw
import yaqc_cmds.somatic.acquisition as acquisition
import yaqc_cmds.hardware.opas as opas


### define ####################################################################


module_name = "SHUTTER"


### Worker ####################################################################


class Worker(acquisition.Worker):
    def process(self, scan_folder):
        pass

    def run(self):
        for opa in opas.hardwares:
            opa = opa.driver
            if opa.shutter_port is None:
                continue
            opa.set_shutter([self.aqn.read("shutter", opa.name)])
        if not self.stopped.read():
            self.finished.write(True)  # only if acquisition successfull


### GUI #######################################################################


class GUI(acquisition.GUI):
    def create_frame(self):
        # shared settings
        input_table = pw.InputTable()
        self.shutter_state = {
            hardware.name: pc.Bool() for hardware in opas.hardwares if hardware.driver.shutter_port
        }
        for k, v in self.shutter_state.items():
            input_table.add(k, v)
        self.layout.addWidget(input_table)

    def load(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        for k, v in self.shutter_state.items():
            v.write(aqn.read("shutter", k))

    def save(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        aqn.write(
            "info",
            "description",
            f"SHUTTER: {', '.join(k for k, v in self.shutter_state.items() if v.read())}",
        )
        # shared settings
        aqn.add_section("shutter")
        for k, v in self.shutter_state.items():
            aqn.write("shutter", k, v.read())


def mkGUI():
    global gui
    gui = GUI(module_name)


def load():
    return True
