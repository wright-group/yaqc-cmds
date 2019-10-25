from .. import acquisition
import project.widgets as pw
import project.classes as pc

import hardware.opas.opas as opas
import hardware.spectrometers.spectrometers as spectrometers
import devices.devices as devices

class Worker(acquisition.Worker):
    def process(self, scan_folder):
        pass

    def run(self):
        pass

class GUI(acquisition.GUI):
    def __init__(self, module_name):
        super().__init__(module_name)
        self.items = {
            "OPA": OpaSectionWidget("OPA"),
            "Processing": ProcessingSectionWidget("Processing"),
            "Device Settings": self.device_widget,
        }

    def create_frame(self):
        for name, item in self.items.Items():
            if name in ("Processing", "Device Settings"):
                continue
            self.layout.add(item.input_table)
        self.layout.add(self["Processing"].input_table)
        self.layout.add(self["Device Settings"].input_table)

    def load(self, aqn_path):
        for item in self.items.Values():
            item.load(aqn_path)

    
    def save(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        aqn.write('info', 'description', f"{self['OPA']['OPA']} {self.module_name}")
        for item in self.items.Values():
            item.save(aqn_path)


    def on_device_settings_updated(self):
        for item in self.items.Values():
            item.on_device_settings_updated()

    def __getitem__(self, name):
        return self.items[name]

def AqnSectionWidget:
    def __init__(self, section_name):
        self.section_name = section_name
        self.items = {}

    @property
    def input_table(self):
        input_table = pw.InputTable()
        input_table.add(self.section_name, None)
        for name, item in self.items.Items():
            input_table.add(name, item)
        return input_table

    def load(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        for name, item in self.items.Items():
            item.write(aqn.read(self.section_name, name))

    def save(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        aqn.add_section(self.section_name)
        for name, item in self.items.Items():
            aqn.write(self.section_name, name, item.read())

    def on_device_settings_updated(self):
        pass

    def __getitem__(self, name):
        return self.items[name]

    
def OpaSectionWidget(AqnSectionWidget):
    def __init__(self, section_name):
        super().__init__(section_name)
        allowed = [hardware.name for hardware in opas.hardwares]
        self.items["OPA"] = pc.Combo(allowed)

def SpectrometerSectionWidget(AqnSectionWidget):
    def __init__(self, section_name):
        super().__init__(section_name)
        allowed = [hardware.name for hardware in spectrometers.hardwares]
        self.items["Action"] = pc.Combo(["Scanned", "None", "Tracking", "Zero Order"], initial_value = "Scanned")
        self.items["Spectrometer"] = pc.Combo(Allowed)

def ProcessingSectionWidget(AqnSectionWidget):
    def __init__(self, section_name):
        super().__init__(section_name)
        self.items["Channel"] = pc.Combo(devices.control.channel_names)
        self.items["level"] = pc.Bool(initial_value=False)
        self.items["gtol"] = pc.Number(initial_value=1e-3, decimals=5)
        self.items["ltol"] = pc.Number(initial_value=1e-2, decimals=5)
        self.items["Apply"] = pc.Bool(initial_value=False)

    def on_device_settings_updated(self):
        self.items["Channel"].set_allowed_values(devices.control.channel_names)

def SpectralAxisSectionWidget(AqnSectionWidget):
    def __init__(self, section_name):
        super().__init__(section_name)
        allowed = []
        for dev in devices.control.devices:
            if dev.has_map:
                allowed.extend(dev.map_axes.keys())
        if not allowed:
            allowed = [""]
        self.items["Axis"] = pc.Combo(allowed)
        self.items["Width"] = pc.Number(initial_value=-250)
        self.items["Num"] = pc.Number(initial_value=51, decimals=0)

def MotorAxisSectionWidget(AqnSectionWidget):
    def __init__(self, section_name):
        super().__init__(section_name)
        #TODO populate motor combo, update with OPA
        self.items["Motor"] = pc.Combo()
        self.items["Width"] = pc.Number(initial_value=1, decimals=3)
        self.items["Num"] = pc.Number(initial_value=31, decimals=0)




def load():
    return False
