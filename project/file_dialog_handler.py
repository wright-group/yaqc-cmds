'''
QFileDialog objects can only be run in the main thread.
'''


### imports ###################################################################


import os
import time

from PyQt4 import QtCore
from PyQt4 import QtGui

import project_globals as g
import classes as pc


### FileDialog object #########################################################


directory_filepath = pc.Mutex()
open_filepath = pc.Mutex()
save_filepath = pc.Mutex()


class FileDialog(QtCore.QObject):
    update_ui = QtCore.pyqtSignal()
    queue_emptied = QtCore.pyqtSignal()
    
    def __init__(self, enqueued_object, busy_object):
        QtCore.QObject.__init__(self)
        self.name = 'file_dialog'
        self.enqueued = enqueued_object
        self.busy = busy_object
    
    @QtCore.pyqtSlot(str, list)
    def dequeue(self, method, inputs):
        '''
        accepts queued signals from 'queue' (address using q method) \n
        string method, list inputs
        '''
        self.update_ui.emit()
        # print self.name, 'dequeue:', method, inputs
        # execute method
        getattr(self, str(method))(inputs)  # method passed as qstring
        # remove method from enqueued
        self.enqueued.pop()
        if not self.enqueued.read():
            self.queue_emptied.emit()
            self.check_busy([])
            self.update_ui.emit()
            
    def check_busy(self, inputs):
        '''
        decides if the hardware is done and handles writing of 'busy' to False
        '''
        # must always write busy whether answer is True or False
        if self.enqueued.read():
            time.sleep(0.1)  # don't loop like crazy
            self.busy.write(True)
        else:
            self.busy.write(False)
            self.update_ui.emit()
            
    def clean(self, out):
        '''
        takes the output and returns a string that has the properties I want
        '''
        out = str(out)
        out = out.replace('/', os.sep)
        return out
        
    def getExistingDirectory(self, inputs=[]):
        caption, directory, options = inputs
        options = QtGui.QFileDialog.ShowDirsOnly
        out = self.clean(QtGui.QFileDialog.getExistingDirectory(g.main_window.read(), caption, directory, options))
        directory_filepath.write(out)        
    
    def getOpenFileName(self, inputs=[]):
        caption, directory, options = inputs
        out = self.clean(QtGui.QFileDialog.getOpenFileName(g.main_window.read(), caption, directory, options))
        open_filepath.write(out)
        
    def getSaveFileName(self, inputs=[]):
        caption, directory, savefilter, selectedfilter, options = inputs
        out = self.clean(QtGui.QFileDialog.getSaveFileName(g.main_window.read(), caption, directory, savefilter, selectedfilter, options))
        save_filepath.write(out)


busy = pc.Busy()
enqueued = pc.Enqueued()
file_dialog = FileDialog(enqueued, busy)
q = pc.Q(enqueued, busy, file_dialog)


### thread-safe file dialog methods ###########################################

# the q method only works between different threads
# call directly if the calling object is in the main thread

def dir_dialog(caption, directory, options):
    inputs = [caption, directory, options]
    if  QtCore.QThread.currentThread() == g.main_thread.read():
        file_dialog.getExistingDirectory(inputs)
    else:
        q.push('getExistingDirectory', inputs)
        while busy.read():
            time.sleep(0.1)
    return directory_filepath.read()


def open_dialog(caption, directory, options):
    inputs = [caption, directory, options]
    if  QtCore.QThread.currentThread() == g.main_thread.read():
        file_dialog.getOpenFileName(inputs)
    else:
        q.push('getOpenFileName', inputs)
        while busy.read():
            time.sleep(0.1)
    return open_filepath.read()


def save_dialog(caption, directory, savefilter, selectedfilter, options):
    inputs = [caption, directory, savefilter, selectedfilter, options]
    if  QtCore.QThread.currentThread() == g.main_thread.read():
        file_dialog.getSaveFileName(inputs)
    else:
        q.push('getSaveFileName', inputs)
        while busy.read():
            time.sleep(0.1)
    return save_filepath.read()
