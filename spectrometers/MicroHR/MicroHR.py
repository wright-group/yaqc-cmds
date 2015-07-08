### import #####################################################################

#from packages import win32com
import win32com.client as w32c
from win32com.client import constants
import pythoncom as pythoncom

### address ####################################################################

MicroHR = w32c.Dispatch(r'JYMono.Monochromator')
print MicroHR
MicroHR.Uniqueid = 'Mono1'
MicroHR.Load()
MicroHR.OpenCommunications()
MicroHR.Initialize()
print MicroHR.InitializeComplete