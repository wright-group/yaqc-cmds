### import ####################################################################

import WrightTools as wt

import yaqc_cmds.project.classes as pc
import yaqc_cmds.project.widgets as pw
import somatic.acquisition as acquisition
import yaqc_cmds.hardware.opas as opas


### define ####################################################################


module_name = "HOME"


### custom classes ############################################################


class MotorGUI:
    def __init__(self, name, home):
        self.name = name
        self.input_table = pw.InputTable()
        self.input_table.add(name, None)
        self.home = pc.Bool(initial_value=home)
        self.input_table.add("Home", self.home)


class OPA_GUI:
    def __init__(self, hardware, layout):
        self.hardware = hardware
        motor_names = self.hardware.motor_names
        self.motors = []
        for name in motor_names:
            motor = MotorGUI(name, False)
            if layout is not None:
                layout.addWidget(motor.input_table)
            self.motors.append(motor)
        self.hide()  # initialize hidden

    def hide(self):
        for motor in self.motors:
            motor.input_table.hide()

    def show(self):
        for motor in self.motors:
            motor.input_table.show()


### Worker ####################################################################


class Worker(acquisition.Worker):
    def process(self, scan_folder):
        pass

    def run(self):
        # get OPA properties
        opa_name = self.aqn.read("home", "opa name")
        opa_names = [h.name for h in opas.hardwares]
        opa_index = opa_names.index(opa_name)
        opa_hardware = opas.hardwares[opa_index]
        opa_friendly_name = opa_hardware.name
        curve = opa_hardware.curve
        motor_names = self.aqn.read("home", "motor names")
        # motor
        for motor_index, motor_name in enumerate(motor_names):
            if self.aqn.read(motor_name, "home"):
                opa_hardware.home_motor([motor_name])
        opa_hardware.wait_until_still()
        if not self.stopped.read():
            self.finished.write(True)  # only if acquisition successfull


### GUI #######################################################################


class GUI(acquisition.GUI):
    def create_frame(self):
        # shared settings
        input_table = pw.InputTable()
        allowed = [hardware.name for hardware in opas.hardwares]
        self.opa_combo = pc.Combo(allowed)
        input_table.add("OPA", self.opa_combo)
        self.opa_combo.updated.connect(self.on_opa_combo_updated)
        self.layout.addWidget(input_table)
        # motor settings
        self.opa_guis = [OPA_GUI(hardware, self.layout) for hardware in opas.hardwares]
        self.opa_guis[0].show()

    def load(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        # shared settings
        self.opa_combo.write(aqn.read("home", "opa name"))
        # motor settings
        opa = self.opa_guis[self.opa_combo.read_index()]
        for motor, motor_name in zip(opa.motors, aqn.read("home", "motor names")):
            motor.home.write(aqn.read(motor_name, "home"))
        # allow devices to read from aqn
        self.device_widget.load(aqn_path)

    def on_opa_combo_updated(self):
        self.show_opa_gui(self.opa_combo.read_index())

    def save(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        opa = self.opa_guis[self.opa_combo.read_index()]
        homed_motor_names = []
        for motor in opa.motors:
            if motor.home.read() == True:
                homed_motor_names.append(motor.name)
        homed_motor_names = str(homed_motor_names).replace("'", "")
        aqn.write(
            "info",
            "description",
            "HOME: {} {}".format(self.opa_combo.read(), homed_motor_names),
        )
        # shared settings
        aqn.add_section("home")
        aqn.write("home", "opa name", self.opa_combo.read())
        aqn.write(
            "home",
            "motor names",
            [motor.name for motor in self.opa_guis[self.opa_combo.read_index()].motors],
        )
        # motor settings
        for motor in opa.motors:
            aqn.add_section(motor.name)
            aqn.write(motor.name, "home", motor.home.read())
        # allow devices to save to aqn
        self.device_widget.save(aqn_path)

    def show_opa_gui(self, index):
        for gui in self.opa_guis:
            gui.hide()
        self.opa_guis[index].show()

    def update_mono_settings(self):
        pass


def mkGUI():
    global gui
    gui = GUI(module_name)


def load():
    return True
