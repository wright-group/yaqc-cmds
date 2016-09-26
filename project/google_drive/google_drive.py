"""
Basic tools for interacting with Google Drive using pydrive wrapper of 
Google Drive's API.
"""


### import ####################################################################


import os
import time
import shutil
from distutils.dir_util import copy_tree

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
    
    def __init__(self, busy, enqueued, system_name):
        QtCore.QObject.__init__(self)
        self.busy = busy
        self.enqueued = enqueued
        self.drive = wt.google_drive.Drive()
        self.system_name = system_name

    @QtCore.pyqtSlot(str, list)
    def dequeue(self, method, inputs):
        # execute method
        getattr(self, str(method))(inputs)  # method passed as qstring
        # remove method from enqueued
        self.enqueued.pop()
        if not self.enqueued.read():
            self.busy.write(False)
    
    def upload(self, inputs):
        # copy into temp directory
        if inputs[0] == 'folder':
            _, folder_path, reference_path = inputs
            queue_folder_name, acquisition_folder_name, scan_folder_name = folder_path.split(os.sep)[-3:]
            folder_names = [self.system_name, queue_folder_name, acquisition_folder_name, scan_folder_name]
            # copy files into temp directory
            folder = temp_directory
            for folder_name in folder_names:
                folder = os.path.join(folder, folder_name)
                if not os.path.isdir(folder):
                    os.mkdir(folder)
            copy_tree(folder_path, folder)
        elif inputs[0] == 'file':
            _, file_path, reference_path = inputs
            relative_path = os.path.relpath(file_path, reference_path)
            folder_names = [self.system_name] + relative_path.split(os.sep)[:-1]
            # copy into temp directory
            folder = temp_directory
            for folder_name in folder_names:
                folder = os.path.join(folder, folder_name)
                if not os.path.isdir(folder):
                    os.mkdir(folder)
            shutil.copy(file_path, folder)
        # sync temp directory to google drive
        for n in os.listdir(temp_directory):
            p = os.path.join(temp_directory, n)
            self.drive.upload(p, PyCMDS_data_ID, overwrite=True, delete_local=True)
          

### control ###################################################################


class Control:
    
    def __init__(self):
        self.system_name = g.system_name.read()
        # create control containers
        self.busy = pc.Busy()
        self.enqueued = pc.Enqueued()
        # create address object
        self.thread = QtCore.QThread()
        self.address = Address(self.busy, self.enqueued, self.system_name)
        self.address.moveToThread(self.thread)
        self.thread.start()
        # create q
        self.q = pc.Q(self.enqueued, self.busy, self.address)
        # connect
        g.shutdown.add_method(self.close)
        # own google drive method for quick operations
        self.drive = wt.google_drive.Drive()
        # session path variables
        self.data_folder = os.path.abspath(os.path.join(g.main_dir.read(), 'data'))

    def close(self):
        self.q.push('close')
        
    def create_folder(self, path):
        '''
        create a folder, with path relative to data folder
        
        returns folder url
        '''
        relative_path = os.path.relpath(os.path.abspath(path), self.data_folder)
        folder_names = [self.system_name] + relative_path.split(os.sep)
        folderid = self.drive.create_folder(folder_names, PyCMDS_data_ID)
        folder_url = wt.google_drive.id_to_url(folderid)
        return folder_url
        
    def upload_scan(self, folder_path, representative_image_path=None):
        queue_folder_name, acquisition_folder_name, scan_folder_name = folder_path.split(os.sep)[-3:]
        folder_names = [self.system_name, queue_folder_name, acquisition_folder_name, scan_folder_name]  
        # create folder on google drive
        folderid = self.drive.create_folder(folder_names, PyCMDS_data_ID)
        folder_url = wt.google_drive.id_to_url(folderid)
        # upload representative image
        if representative_image_path is not None:
            imageid = self.drive.upload(representative_image_path, folderid)
            image_url = 'https://docs.google.com/uc?id=' + imageid
        else:
            image_url = None
        # enqueue syncing    
        self.q.push('upload', ['folder', folder_path, self.data_folder])
        # finish
        return folder_url, image_url
    
    def upload_file(self, filepath):
        '''
        upload a file, with path relative to data folder
        '''
        # enqueue syncing    
        self.q.push('upload', ['file', filepath, self.data_folder])
        
        
        
        

control = Control()
g.google_drive_control.write(control)


### testing ###################################################################


if __name__ == '__main__':
    pass
    
