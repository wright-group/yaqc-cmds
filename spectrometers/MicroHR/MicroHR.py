# http://stackoverflow.com/questions/12039174/python-activex-automation
# need to creat py_gen...

### import #####################################################################

import os
if __name__ == '__main__': os.chdir(r'C:\Users\John\Desktop\PyCMDS')

import time

import project.project_globals as g
main_dir = g.main_dir.read()

import spectrometers.MicroHR.gen_py.JYConfigBrowserComponent as JYConfigBrowserComponent
import spectrometers.MicroHR.gen_py.JYMono as JYMono

### mono object ################################################################

class MicroHR:
    def __init__(self):
        #open control
        self.ctrl = JYMono.Monochromator()
        self.ctrl.Uniqueid = 'Mono1'
        self.ctrl.Load()
        self.ctrl.OpenCommunications()
        self.ctrl.Initialize()
        #import some information from control
        self.description = self.ctrl.Description
        self.serial_number = self.ctrl.SerialNumber
    def close(self):
        self.ctrl.CloseCommunications()
    def get_wavelength(self):
        self.current_wavelength = self.ctrl.GetCurrentWavelength()
        return self.current_wavelength
    def go_to_wavelength(self, destination):
        self.ctrl.MovetoWavelength(destination)

### testing ####################################################################

if __name__ == '__main__':

    mono = MicroHR()
    
    print mono.get_wavelength()
    mono.go_to_wavelength(1000)
    time.sleep(10)
    mono.go_to_wavelength(1300)
    
    mono.close()