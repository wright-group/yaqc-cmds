# http://stackoverflow.com/questions/12039174/python-activex-automation
# need to create py_gen...

### import #####################################################################

import os
if __name__ == '__main__': os.chdir(r'C:\Users\John\Desktop\PyCMDS')

import time

import project.project_globals as g
main_dir = g.main_dir.read()
import project.ini_handler as ini
ini_path = os.path.join(main_dir, 'spectrometers', 'MicroHR', 'MicroHR.ini')

import spectrometers.MicroHR.gen_py.JYConfigBrowserComponent as JYConfigBrowserComponent
import spectrometers.MicroHR.gen_py.JYMono as JYMono

### mono object ################################################################

# CRITICAL:
# FOR SOME REASON THE PHYSICAL USB KEY IS NEEDED FOR THIS CODE TO WORK

class MicroHR:  
    def __init__(self):
        #open control
        self.ctrl = JYMono.Monochromator()
        self.ctrl.Uniqueid = 'Mono1'
        self.ctrl.Load()
        self.ctrl.OpenCommunications()
        #initialize hardware
        forceInit = True #this toggles mono homing behavior
        emulate = False 
        notThreaded = True
        self.ctrl.Initialize(forceInit, emulate, notThreaded)
        #import some information from control
        self.description = self.ctrl.Description
        self.serial_number = self.ctrl.SerialNumber
        self.current_wavelength = self.ctrl.GetCurrentWavelength()
        #import information from ini
        init_grating_index = ini.read(ini_path, 'main', 'grating index')
        init_wavelength = ini.read(ini_path, 'main', 'position (nm)')
        #go to old position after initialization is done
        while self.is_busy(): time.sleep(1)
        self.set_turret(init_grating_index)
        self.set_position(init_wavelength)
    def close(self):
        #close control
        self.ctrl.CloseCommunications()
        #save current position to ini
        ini.write(ini_path, 'main', 'grating index', self.grating_index)
        ini.write(ini_path, 'main', 'position (nm)', self.current_wavelength)
    def get_position(self):
        self.current_wavelength = self.ctrl.GetCurrentWavelength()
        return self.current_wavelength
    def is_busy(self):
        return self.ctrl.IsBusy()
    def set_position(self, destination):
        self.ctrl.MovetoWavelength(destination)
        self.get_position()
    def set_turret(self, destination_index):
        #turret index on ActiveX call starts from zero
        destination_index_zero_based = destination_index - 1
        self.ctrl.MovetoTurret(destination_index_zero_based)
        self.grating_index = destination_index
    def stop(self):
        self.ctrl.Stop()
MicroHR = MicroHR()
        
### advanced gui ###############################################################

### testing ####################################################################

if __name__ == '__main__':
    
    
    
    #wait for initialization to complete
    while MicroHR.is_busy():
        time.sleep(1)
    
    print MicroHR.get_position()
    
    MicroHR.set_position(1000)
    
    while MicroHR.is_busy():
        time.sleep(1)
    
    if False:
        MicroHR.set_position(1000)
        time.sleep(5)
        print MicroHR.get_position()
        MicroHR.set_position(1300)
    
    MicroHR.close()