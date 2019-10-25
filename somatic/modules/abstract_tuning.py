import configparser

import WrightTools as wt

import somatic.acquisition as acquisition

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
        self.items.update({
            "OPA": OpaSectionWidget("OPA", self),
            "Spectrometer": SpectrometerSectionWidget("Spectrometer", self),
            "Processing": ProcessingSectionWidget("Processing", self),
        })
        super().__init__(module_name)
        for item in self.items.values():
            for i in item.items.values():
                i.updated.connect(self.on_update)
        self.items["Device Settings"] = self.device_widget

    def create_frame(self):
        self.layout.addWidget(self["OPA"].input_table)
        self.layout.addWidget(self["Spectrometer"].input_table)
        for name, item in self.items.items():
            if name in ("OPA", "Spectrometer", "Processing", "Device Settings"):
                continue
            self.layout.addWidget(item.input_table)
        self.layout.addWidget(self["Processing"].input_table)

    def load(self, aqn_path):
        for item in self.items.values():
            item.load(aqn_path)

    
    def save(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        aqn.write('info', 'description', f"{self['OPA']['OPA'].read()} {self.module_name}")
        for item in self.items.values():
            item.save(aqn_path)

    def on_device_settings_updated(self):
        self.on_update()

    def on_update(self):
        for item in self.items.values():
            if isinstance(item, AqnSectionWidget):
                item.on_update()

    def __getitem__(self, name):
        return self.items[name]

class AqnSectionWidget:
    def __init__(self, section_name, parent):
        self.section_name = section_name
        self.parent = parent
        self.items = {}

    @property
    def input_table(self):
        input_table = pw.InputTable()
        input_table.add(self.section_name, None)
        for name, item in self.items.items():
            input_table.add(name, item)
        return input_table

    def load(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        for name, item in self.items.items():
            item.write(aqn.read(self.section_name, name))

    def save(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        try:
            aqn.add_section(self.section_name)
        except configparser.DuplicateSectionError:
            pass
        for name, item in self.items.items():
            aqn.write(self.section_name, name, item.read())

    def on_update(self):
        pass

    def __getitem__(self, name):
        return self.items[name]

    
class OpaSectionWidget(AqnSectionWidget):
    def __init__(self, section_name, parent):
        super().__init__(section_name, parent)
        allowed = [hardware.name for hardware in opas.hardwares]
        self.items["OPA"] = pc.Combo(allowed)

class SpectrometerSectionWidget(AqnSectionWidget):
    def __init__(self, section_name, parent):
        super().__init__(section_name, parent)
        allowed = [hardware.name for hardware in spectrometers.hardwares]
        self.items["Action"] = pc.Combo(["Scanned", "None", "Tracking", "Zero Order"], initial_value = "Scanned")
        self.items["Spectrometer"] = pc.Combo(allowed)

    def on_update(self):
        self.items["Spectrometer"].set_disabled(self.items["Action"].read() == "None")

class ProcessingSectionWidget(AqnSectionWidget):
    def __init__(self, section_name, parent):
        super().__init__(section_name, parent)
        self.items["Channel"] = pc.Combo(devices.control.channel_names)
        self.items["level"] = pc.Bool(initial_value=False)
        self.items["gtol"] = pc.Number(initial_value=1e-3, decimals=5)
        self.items["ltol"] = pc.Number(initial_value=1e-2, decimals=5)
        self.items["Apply"] = pc.Bool(initial_value=False)

    def on_update(self):
        self.items["Channel"].set_allowed_values(devices.control.channel_names)

class SpectralAxisSectionWidget(AqnSectionWidget):
    def __init__(self, section_name, parent):
        super().__init__(section_name, parent)
        self.items["Axis"] = pc.Combo()
        self.items["Width"] = pc.Number(initial_value=-250)
        self.items["Num"] = pc.Number(initial_value=51, decimals=0)
    
    def on_update(self):
        if self.parent["Spectrometer"]["Action"] == "Scanned":
            allowed = [self.parent["Spectrometer"]["Spectrometer"]]
        else:
            allowed = []
            for dev in devices.control.devices:
                if dev.has_map:
                    allowed.extend(dev.map_axes.keys())
            if not allowed:
                allowed = [""]
        self.items["Axis"].set_allowed_values(allowed)
        

class MotorAxisSectionWidget(AqnSectionWidget):
    def __init__(self, section_name, parent):
        super().__init__(section_name, parent)
        self.items["Motor"] = pc.Combo()
        self.items["Width"] = pc.Number(initial_value=1, decimals=3)
        self.items["Num"] = pc.Number(initial_value=31, decimals=0)

    def on_update(self):
        hardware = next(h for h in opas.hardwares if h.name == self.parent["OPA"]["OPA"].read())
        self.items["Motor"].set_allowed_values(hardware.curve.dependent_names)




def load():
    return False
