"""
Basic tools for interacting with Google Drive using pydrive wrapper of 
Google Drive's API.
"""

# Darien Morrow - darienmorrow@gmail.com - dmorrow3@wisc.edu
# First created: February 17, 2016


### import ####################################################################


import os
import time

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from pydrive.files import GoogleDriveFile

from PyQt4 import QtGui, QtCore

import project.classes as pc
import project.logging_handler as logging_handler
import project.project_globals as g
from project.ini_handler import Ini
main_dir = g.main_dir.read()
ini = Ini(os.path.join(main_dir, 'project', 'google_drive', 'google_drive.ini'))


### address ###################################################################


class Address(QtCore.QObject):
    
    def __init__(self, busy, enqueued):
        QtCore.QObject.__init__(self)
        self.busy = busy
        self.enqueued = enqueued
        # get ID of PyCMDS data folder
        self.PyCMDS_data_ID = ini.read('main', 'PyCMDS data ID')


    def _authenticate(self):
        # authenticate self.drive...
        creds_path = os.path.join(os.path.dirname(__file__), 'mycreds.txt')
        gauth = GoogleAuth()
        gauth.LoadCredentialsFile(creds_path)  # try to load saved client credentials.
        if gauth.credentials is None:
            gauth.LocalWebserverAuth()  # authenticate if credentials are not found.
        elif gauth.access_token_expired:
            gauth.Refresh()  # refresh credentials if they are expired.
        else:
            gauth.Authorize()  # initialize the saved credentials.
        gauth.SaveCredentialsFile(creds_path) # save the current credentials to a file
        self.drive = GoogleDrive(gauth)  # create instance of GoogleDrive and call it drive 
        
    def close(self):
        # TODO: ?
        pass
    
    def create_folder(self, foldername, parentID):
        """
        Create a new folder in Google Drive.
    
        Attributes
        ----------
        foldername : string
            Name of new folder to be created.
        parentID : string
            Google Drive ID of folder that is to be the parent of new folder.
            
        Returns
        -------
        file['id'] : string
            The unique Google Drive ID of the newly created folder. 
        """    
        
        file1 = self.drive.CreateFile({'title': foldername, 
        "parents":  [{"id": parentID}], 
        "mimeType": "application/vnd.google-apps.folder"})
        file1.Upload()
        return file1['id']

    @QtCore.pyqtSlot(str, list)
    def dequeue(self, method, inputs):
        # re-authenticate every time the class does anything
        self._authenticate()
        # execute method
        getattr(self, str(method))(inputs)  # method passed as qstring
        # remove method from enqueued
        self.enqueued.pop()
        if not self.enqueued.read():
            self.ctrl.rtmbot.autoping()
            self.queue_emptied.emit()
            self.busy.write(False)
    
    def get_metadata(self, ID):
        """
        Return Google Drive file/folder metadata.
        
        Attributes
        ----------
        ID : string
            Google Drive ID of file/folder to be explored.
        
        Returns
        -------
        file1 : dictionary [of sorts]
            A small Google Drive dictionary of the file's metadata.
        """    
        
        file1 = self.drive.CreateFile({"id":ID})
        file1.FetchMetadata()  
        return file1    
    
    def get_folder_contents(self, ID):
        """
        Return contents of a Google Drive folder.
        
        Attributes
        ----------
        ID : string
            Google Drive ID of folder to explore the contents of.
            
        Returns
        -------
        file_list : list
            List of files that the Google Drive folder is parent of.
        """    
        
        args = "in parents and mimeType = 'application/vnd.google-apps.folder' and trashed=false"   
        arguments = '\'{0}\' {1}'.format(ID, args)
        
        file_list = self.drive.ListFile({'q':arguments}).GetList()
        return file_list
    
    def upload(self, inputs):
        """
        Upload files to Google Drive. Creates new GD folders if needed.
        Created to be implemented to satisfy the needs of PyCMDS.
        
        Attributes
        ----------
        system_name : string
            System that instance of PyCMDS is controlling.
            This string specifies the subfolder (parent: PyCMDS data) that
            the new data is saved to
        day : string
            Day that PyCMDS started current run of data collection.
            This string specifies the sub,subfolder (parent: system_name) that
            the new data is saved to
        folder_path : string
            Local folder path that contains files to be uploaded. 
        """
        system_name, day, folder_path = inputs
        # TODO: Implement progress bar.
        # system name folder
        found = False
        for f in self.get_folder_contents(self.PyCMDS_data_ID):
            if f['title'] == system_name:
                parent = f['id']
                found = True
        if not found:         
            parent = self.create_folder(system_name, self.PyCMDS_data_ID)
        # day folder
        found = False
        for file1 in self.get_folder_contents(parent):
            if file1['title'] == day:
                parent = file1['id']
                found = True
        if not found:
            parent = self.create_folder(day, parent)
        # contents
        remaining_dirs = [[folder_path, parent]]
        while len(remaining_dirs) > 0:
            current_root, parent_of_root = remaining_dirs.pop(0)
            # create current root folder inside of parent_of_root
            # this is now the parent
            folder_name = current_root.split(os.path.sep)[-1]
            parent = self.create_folder(folder_name, parent_of_root)
            # walk through current root
            for n in os.listdir(current_root):
                full_path = os.path.join(current_root, n)
                if os.path.isfile(full_path):
                    # upload files
                    self.upload_file(full_path, parent)
                    print n, 'uploaded to google drive'
                elif os.path.isdir(full_path):
                    # append directories to be filled later
                    remaining_dirs.append([os.path.join(current_root, n), parent])

    def upload_file(self, filepath, parentID):
        """
        Upload a local file to Google Drive.
        
        Attributes
        ----------
        filepath : string    
            Full local file path (including name) of the file to be uploaded       
        parentID : string
            Google Drive ID of folder to be uploaded to.
        
        Returns
        -------
        file1['id'] : string
            The unique Google Drive ID of the newly uploaded file.    
        """
        
        file1 = self.drive.CreateFile({'title': filepath.split(os.path.sep)[-1], 
        "parents": [{"id": parentID}]})
        
        file1.SetContentFile(filepath)
        file1.Upload()
        return file1['id']
      

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

    def close(self):
        self.q.push('close')
        
    def upload(self, folder_path):
        system_name = g.system_name.read()
        day = time.strftime('%Y.%m.%d', time.localtime(os.stat(folder_path).st_ctime))
        inputs = [system_name, day, folder_path]
        self.q.push('upload', inputs)

control = Control()
g.google_drive_control.write(control)


### testing ###################################################################


if __name__ == '__main__':
    pass
    
