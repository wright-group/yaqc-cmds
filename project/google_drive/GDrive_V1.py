# Darien Morrow - darienmorrow@gmail.com - dmorrow3@wisc.edu
# First created: February 17, 2016
"""
Basic tools for interacting with Google Drive using pydrive wrapper of 
Google Drive's API.
"""


import os
import glob
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from pydrive.files import GoogleDriveFile


def gd_authorization(credentials_directory):
    """
    Create and authenticate an instance of GoogleDrive.
    
    Attributes
    ----------
    credentials_directory : string    
        File path of directory in which credentials file: 'mycreds.txt' lives.         
        
    Returns
    -------
    drive
        An instance of the class GoogleDrive.
    """    
    # TODO: Eventually this needs to be migrated to an .ini file method.
    creds_path = os.path.join(credentials_directory, 'mycreds.txt')
    gauth = GoogleAuth()
    # Try to load saved client credentials.
    gauth.LoadCredentialsFile(creds_path)
    if gauth.credentials is None:
        # Authenticate if credentials are not found.
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        # Refresh credentials if they are expired.
        gauth.Refresh()
    else:
        # Initialize the saved credentials.
        gauth.Authorize()
    # Save the current credentials to a file
    gauth.SaveCredentialsFile(creds_path)
    # Create instance of GoogleDrive and call it drive.    
    drive = GoogleDrive(gauth)
    return drive

def PyCMDS_data_folder():
    """ Return Google Drive ID for PyCMDS folder. """    
    # TODO: Remove this hard code dataID and replace with hidden .ini file.    
    PyCMDS_data_ID = '0B5XBhboKMJCTeFhpc0FRNlZ6Wlk'
    return PyCMDS_data_ID  

def gd_fileupload(filepath,parentID):
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
    
    file1 = drive.CreateFile({'title': filepath.split(os.path.sep)[-1], 
    "parents": [{"id": parentID}]})
    
    file1.SetContentFile(filepath)
    file1.Upload()
    return file1['id']


def gd_foldercreation(foldername,parentID):
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
    
    file1 = drive.CreateFile({'title': foldername, 
    "parents":  [{"id": parentID}], 
    "mimeType": "application/vnd.google-apps.folder"})
    file1.Upload()
    return file1['id']

def gd_metadata(ID):
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
    
    file1=drive.CreateFile({"id":ID})    
    file1.FetchMetadata()  
    return file1    

def gd_foldercontents(ID):
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
    
    file_list = drive.ListFile({'q':arguments}).GetList()
    return file_list

 
def upload(system_name, day, folder_path):
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
        
    Returns
    -------
    fid1 : string
        Google Drive ID for the day folder into which all files were saved.
    
    Notes
    -----
    This upload method only crawls four folders deep in the local system. 
    This upload method calls a local file a folder if that file does not have
    a .fileextension on the end of it. 
    
    This upload method prints out many various statements. 
        It details when it finds the correct Google Drivedirectories to upload to.
        It prints a statement everytime it uploads a file.
            e.g. 'uploaded /Users/darienmorrow/Desktop/test5/test.txt'   
    """

    # TODO: Implement progress bar.
    fid0 = None     
    PyCMDS_data = gd_foldercontents(PyCMDS_data_ID)        
    for file1 in PyCMDS_data:
        if file1['title'] == system_name:
            print 'Found system folder.'
            fid0 = file1['id']
    if fid0 == None:
        # Make new folder and get its ID.           
        fid0 = gd_foldercreation(system_name,PyCMDS_data_ID)
        print 'Could not find system folder. Made new one.'
        
    fid1 = None     
    system_data = gd_foldercontents(fid0)        
    for file1 in system_data:
        if file1['title'] == day:
            fid1 = file1['id']
            print 'Found day folder. Its ID is:', fid1
    if fid1 == None:
        # Make new folder and get its ID.           
        fid1 = gd_foldercreation(day,fid0)
        print 'Could not find day folder. Made new one. Its ID is:', fid1
   
    # TODO: Genearlize folder crawling/creation methadology to extend to N folders.
    file_paths = [os.path.join(folder_path, p) for p in os.listdir(folder_path)]
    
    for file1 in file_paths:
        gd_fileupload(file1,fid1)
        print 'uploaded', file1
    for file1 in os.listdir(folder_path):
        # Check to see if any of the things are folders.         
        if '.' not in file1:
            fid2 = gd_foldercreation(file1,fid1)
            # Upload all the contents of the new-found folder.
            file_paths2 = glob.glob(os.path.join(folder_path, file1,'*.*'))
            for file2 in file_paths2:
                gd_fileupload(file2,fid2)
                print 'uploaded', file2
            
            for file2 in os.listdir(os.path.join(folder_path, file1)):
                # Check to see if any of the things are folders.         
                if '.' not in file2:
                    fid3 = gd_foldercreation(file2,fid2)
                    # Upload all the contents of the new-found folder.
                    file_paths3 = glob.glob(os.path.join(folder_path, file1, file2,'*.*'))
                    for file3 in file_paths3:
                        gd_fileupload(file3,fid3)
                        print 'uploaded', file3
    return fid1
      
  
if __name__ == '__main__':
    import time
    start = time.clock()
    drive = gd_authorization(os.path.dirname(__file__))
    PyCMDS_data_ID = PyCMDS_data_folder()
    middle = time.clock()
    path = r'C:\Users\John\Desktop\Old Data\2016.01.28\MOTORTUNE [w1, w1_Crystal_2, w1_Delay_2, wa] 2016.01.25 16_56_06'
    print path    
    upload('test3', '2016.02.18', path)
    end = time.clock()
    print middle - start
    print end - middle
    print end - start