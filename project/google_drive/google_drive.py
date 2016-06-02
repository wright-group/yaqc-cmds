"""
Basic tools for interacting with Google Drive using pydrive wrapper of 
Google Drive's API.
"""


### import ####################################################################


import os
import time
import shutil

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from pydrive.files import GoogleDriveFile

from PyQt4 import QtGui, QtCore

import WrightTools as wt

import project.classes as pc
import project.logging_handler as logging_handler
import project.project_globals as g
from project.ini_handler import Ini
main_dir = g.main_dir.read()
ini = Ini(os.path.join(main_dir, 'project', 'google_drive', 'google_drive.ini'))


### define ####################################################################


directory = os.path.dirname(__file__)

PyCMDS_data_ID = ini.read('main', 'PyCMDS data ID')


### ensure temp folder exists #################################################


directory = os.path.dirname(__file__)
temp_directory = os.path.join(directory, 'temp')
if not os.path.isdir(temp_directory):
    os.mkdir(temp_directory)


### address ###################################################################


class Address(QtCore.QObject):
    
    def __init__(self, busy, enqueued):
        QtCore.QObject.__init__(self)
        self.busy = busy
        self.enqueued = enqueued
        self.drive = wt.google_drive.Drive()

    @QtCore.pyqtSlot(str, list)
    def dequeue(self, method, inputs):
        # execute method
        getattr(self, str(method))(inputs)  # method passed as qstring
        # remove method from enqueued
        self.enqueued.pop()
        if not self.enqueued.read():
            self.ctrl.rtmbot.autoping()
            self.queue_emptied.emit()
            self.busy.write(False)
    
    def upload(self, inputs):
        for n in os.listdir(temp_directory):
            p = os.path.join(temp_directory, n)
            self.drive.upload(p, PyCMDS_data_ID, delete_local=True)
      

### control ###################################################################


class Control:
    
    def __init__(self):
        # create control containers
        self.busy = pc.Busy()
        self.enqueued = pc.Enqueued()
        # create address object
        self.thread = QtCore.QThread()
        self.address = Address(self.busy, self.enqueued)
        self.address.moveToThread(self.thread)
        self.thread.start()
        # create q
        self.q = pc.Q(self.enqueued, self.busy, self.address)
        # connect
        g.shutdown.add_method(self.close)
        # own google drive method for quick operations
        self.drive = wt.google_drive.Drive()

    def close(self):
        self.q.push('close')
        
    def upload(self, folder_path, image_path=None):
        # define path
        system_name = g.system_name.read()
        day = time.strftime('%Y.%m.%d', time.localtime(os.stat(folder_path).st_ctime))
        folder_name = os.path.basename(folder_path)
        # create container folder on google drive
        folderid = self.drive.create_folder([system_name, day, folder_name], PyCMDS_data_ID)
        folder_url = wt.google_drive.id_to_url(folderid)
        # upload representative image
        if image_path is not None:
            imageid = self.drive.upload(image_path, folderid)
            image_url = 'https://docs.google.com/uc?id=' + imageid
        else:
            image_url = None
        # create container folder in temp
        system_path = os.path.join(temp_directory, system_name)
        if not os.path.isdir(system_path):
            os.mkdir(system_path)
        day_path = os.path.join(system_path, day)
        if not os.path.isdir(day_path):
            os.mkdir(day_path)
        # copy
        src = folder_path
        dst = os.path.join(day_path, src.split(os.sep)[-1])
        shutil.copytree(src, dst)
        # enqueue syncing    
        self.q.push('upload')
        # finish
        return folder_url, image_url

control = Control()
g.google_drive_control.write(control)


### testing ###################################################################


if __name__ == '__main__':
    pass
    
