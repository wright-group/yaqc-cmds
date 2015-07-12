### import #####################################################################

import os
if __name__ == '__main__': os.chdir(r'C:\Users\John\Desktop\PyCMDS')
import time

from PyQt4 import QtCore

import project.project_globals as g
main_dir = g.main_dir.read()
app = g.app.read()
import project.custom_widgets as custom_widgets
import project.ini_handler as ini
import project.classes as pc

### address ####################################################################

hardware_dict = {'MicroHR': [os.path.join(main_dir, 'spectrometers', 'MicroHR')]}

#read which hardware will be loaded from ini
for key in hardware_dict.keys():
    print key
    




#1/0
### control ####################################################################

class control():
    
    def __init__(self):
        self.ready = False
        print 'control.__init__'
        g.shutdown.add_method(self.shutdown)
        g.poll_timer.connect_to_timeout(self.poll)
        self.initialize_hardware()
        
    def initialize_hardware(self):
        q('initialize')
        
    def poll(self):
        pass
        #if not g.module_control.read(): q('poll')
        
    def set_hardware(self, destination):
        print 'set hardware'
        q('go_to', [destination])
    
    def wait_until_done(self, timeout = 10):
        '''
        timeout in seconds
        
        will only refer to timeout when busy.wait_for_update fires
        '''
        start_time = time.time()
        while busy.read():
            if time.time()-start_time < timeout:
                if not enqueued_actions.read(): q('check_busy')
                busy.wait_for_update()
            else: 
                g.logger.log('warning', 'Wait until done timed out', 'timeout set to {} seconds'.format(timeout))
                break
                
    def shutdown(self):
        if g.debug.read(): print 'MicroHR shutting down'
        g.logger.log('info', 'MicroHR shutdown')
        q('shutdown')
        self.wait_until_done()
        address_thread.quit()
        gui.stop()
        
control = control()

#gui############################################################################

class gui(QtCore.QObject):

    def __init__(self):
        QtCore.QObject.__init__
        address_obj.update_ui.connect(self.update)
        self.create_frame()
        
    def create_frame(self):
        
        layout_widget = custom_widgets.hardware_layout_widget('Monochromator', busy, address_obj.update_ui)
        layout = layout_widget.layout()

        input_table = custom_widgets.input_table(125)
        input_table.add('MicroHR', None)
        input_table.add('Grating', current_grating)
        input_table.add('Color', current_color)
        input_table.add('Grating Destination', grating_destination)
        input_table.add('Color Destination', color_destination)
        layout.addWidget(input_table)

        layout_widget.add_buttons(self.on_set, self.show_advanced)
        
        g.hardware_widget.add_to(layout_widget)
    
    def update(self):
        print 'update'
        pass
        
    def on_set(self):
        print 'on_set'
        control.set_hardware(destination.read())
    
    def show_advanced(self):
        pass
              
    def stop(self):
        pass
        
gui = gui()