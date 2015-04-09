import os 
os.chdir('C:\Users\John\Desktop\PyCMDS 00.02')

#import-------------------------------------------------------------------------

#from packages import win32com
import packages.win32com.client as w32c
from packages.win32com.client import constants
import packages.pythoncom as pythoncom

#initialize---------------------------------------------------------------------

MicroHR = w32c.Dispatch(r'JYMono.Monochromator')
print MicroHR
MicroHR.Uniqueid = 'Mono1'
MicroHR.Load()
MicroHR.OpenCommunications()
MicroHR.Initialize()
print MicroHR.InitializeComplete