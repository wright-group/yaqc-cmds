### import ####################################################################

import os
import collections

import WrightTools as wt

import project.project_globals as g
import project.classes as pc
import project.widgets as pw
import somatic.acquisition as acquisition
import project.ini_handler as ini_handler
main_dir = g.main_dir.read()
ini = ini_handler.Ini(os.path.join(main_dir, 'somatic', 'modules', 'tune_test.ini'))
app = g.app.read()

import hardware.opas.opas as opas
import devices.devices as devices

 
### define ####################################################################


module_name = 'AUTOTUNE'
 
 
### Worker ####################################################################


class Worker(acquisition.Worker):
    
    def process(self, scan_folder):
        pass
    
    def run(self):
        opa_names = [opa.name for opa in opas.hardwares]
        opa_name = self.aqn.read('OPA', 'name')
        opa_index = opa_names.index(opa_name)
        opa = opas.hardwares[opa_index]
        opa.run_auto_tune(self)

 
### GUI #######################################################################


class GUI(acquisition.GUI):

    def create_frame(self):
        input_table = pw.InputTable()
        self.opa_combobox = pc.Combo()
        self.opa_combobox.updated.connect(self.on_opa_combobox_updated)
        input_table.add('OPA', self.opa_combobox)
        self.layout.addWidget(input_table)
        # opa frames
        self.opa_widgets = collections.OrderedDict()
        self.opa_autotunes = collections.OrderedDict()
        for opa in opas.hardwares:
            if hasattr(opa.driver, 'auto_tune'):
                widget = opa.driver.auto_tune
                self.layout.addWidget(widget)
                self.opa_widgets[opa.name] = widget
                widget.hide()
                self.opa_autotunes[opa.name] = opa.driver.auto_tune
        self.opa_combobox.set_allowed_values(self.opa_widgets.keys())
        self.on_opa_combobox_updated()
        for opa in opas.hardwares:
            opa.initialized_signal.connect(self.on_initialized)
            
    def load(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        self.opa_combobox.write(aqn.read('OPA', 'name'))
        self.opa_autotunes[self.opa_combobox.read()].load(aqn_path)
        self.device_widget.load(aqn_path)
        
    def on_opa_combobox_updated(self):
        for w in self.opa_widgets.values():
            w.hide()
        self.opa_widgets[self.opa_combobox.read()].show()

    def on_device_settings_updated(self):
        channel_names = devices.control.channel_names
        for w in self.opa_widgets.values():
            if w.initialized.read():
                w.update_channel_names(channel_names)
            
    def on_initialized(self):
        self.on_device_settings_updated()
        
    def save(self, aqn_path):
        aqn = wt.kit.INI(aqn_path)
        aqn.add_section('OPA')
        aqn.write('OPA', 'name', self.opa_combobox.read())
        self.opa_autotunes[self.opa_combobox.read()].save(aqn_path)
        aqn.write('info', 'description', "AUTOTUNE {} [{}]".format(
                                            self.opa_combobox.read(), 
                                            ','.join([section for section in aqn.sections 
                                                if aqn.has_option(section, 'do') and aqn.read(section,'do')])))
        self.device_widget.save(aqn_path)
def load():
    return True
def mkGUI():        
    global gui
    gui = GUI(module_name)
