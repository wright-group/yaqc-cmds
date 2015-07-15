# -*- coding: mbcs -*-
# Created by makepy.py version 0.5.01
# By python version 2.7.9 (default, Dec 10 2014, 12:24:55) [MSC v.1500 32 bit (Intel)]
# From type library 'JYConfigBrowserComponent.dll'
# On Fri Jul 10 11:01:33 2015
'JYConfigBrowserComponent 1.0 Type Library'
makepy_version = '0.5.01'
python_version = 0x20709f0

import win32com.client.CLSIDToClass, pythoncom, pywintypes
import win32com.client.util
from pywintypes import IID
from win32com.client import Dispatch

# The following 3 lines may need tweaking for the particular server
# Candidates are pythoncom.Missing, .Empty and .ArgNotFound
defaultNamedOptArg=pythoncom.Empty
defaultNamedNotOptArg=pythoncom.Empty
defaultUnnamedArg=pythoncom.Empty

CLSID = IID('{6996861C-23A5-43B3-B89A-F65CA06E4D13}')
MajorVersion = 1
MinorVersion = 0
LibraryFlags = 8
LCID = 0x0

from win32com.client import DispatchBaseClass
class IJYConfigBrowerInterface(DispatchBaseClass):
	'IJYConfigBrowerInterface Interface'
	CLSID = IID('{FCAC56F8-B378-42AB-8C6C-A41596864D4D}')
	coclass_clsid = IID('{3A457ACC-F1FB-4D7D-9AB4-EE427CE33385}')

	def DeleteDeviceById(self, devID=defaultNamedNotOptArg):
		'method DeleteDeviceById'
		return self._oleobj_.InvokeTypes(51, LCID, 1, (24, 0), ((8, 1),),devID
			)

	def DisplayCurrentConfiguration(self):
		'method DisplayCurrentConfiguration'
		return self._oleobj_.InvokeTypes(50, LCID, 1, (24, 0), (),)

	def GatherCCDInfo(self):
		'method GatherCCDInfo'
		return self._oleobj_.InvokeTypes(41, LCID, 1, (24, 0), (),)

	def GatherDatabaseInfo(self):
		'method GatherDatabaseInfo'
		return self._oleobj_.InvokeTypes(42, LCID, 1, (24, 0), (),)

	def GatherLogInfo(self):
		'method GatherLogInfo'
		return self._oleobj_.InvokeTypes(45, LCID, 1, (24, 0), (),)

	def GatherOriginInfo(self):
		'method GatherOriginInfo'
		return self._oleobj_.InvokeTypes(40, LCID, 1, (24, 0), (),)

	def GatherRegistryInfo(self):
		'method GatherRegistryInfo'
		return self._oleobj_.InvokeTypes(44, LCID, 1, (24, 0), (),)

	def GatherVersionInfo(self):
		'method GatherVersionInfo'
		return self._oleobj_.InvokeTypes(43, LCID, 1, (24, 0), (),)

	def GetDataExperimentPathsByConfig(self, configID=defaultNamedNotOptArg, pathData=pythoncom.Missing, pathExp=pythoncom.Missing):
		'method GetDataExperimentPathsByConfig'
		return self._ApplyTypes_(76, 1, (24, 0), ((8, 1), (16392, 2), (16392, 2)), u'GetDataExperimentPathsByConfig', None,configID
			, pathData, pathExp)

	def GetDefaultApplicationType(self, appType=pythoncom.Missing):
		'method GetDefaultApplicationType'
		return self._ApplyTypes_(77, 1, (24, 0), ((16387, 2),), u'GetDefaultApplicationType', None,appType
			)

	def GetDefaultConfig(self, name=pythoncom.Missing):
		'method GetDefaultConfig'
		return self._ApplyTypes_(75, 1, (24, 0), ((16392, 2),), u'GetDefaultConfig', None,name
			)

	def GetDevIdByConfig(self, configID=defaultNamedNotOptArg, cdc=defaultNamedNotOptArg, devClass=defaultNamedNotOptArg):
		'method GetDevIdByConfig'
		# Result is a Unicode object
		return self._oleobj_.InvokeTypes(52, LCID, 1, (8, 0), ((8, 1), (3, 1), (3, 1)),configID
			, cdc, devClass)

	def GetDevIdFromDevName(self, devName=defaultNamedNotOptArg, devID=pythoncom.Missing):
		'method GetDevIdFromDevName'
		return self._ApplyTypes_(49, 1, (24, 0), ((8, 1), (16392, 2)), u'GetDevIdFromDevName', None,devName
			, devID)

	def GetFirstAccessory(self, accType=defaultNamedNotOptArg, name=pythoncom.Missing):
		'method GetFirstAccessory'
		return self._ApplyTypes_(14, 1, (8, 0), ((3, 1), (16392, 2)), u'GetFirstAccessory', None,accType
			, name)

	def GetFirstAccessoryByConfig(self, configID=defaultNamedNotOptArg, devName=pythoncom.Missing):
		'method GetFirstAccessoryByConfig'
		return self._ApplyTypes_(71, 1, (8, 0), ((8, 1), (16392, 2)), u'GetFirstAccessoryByConfig', None,configID
			, devName)

	def GetFirstCCD(self, name=pythoncom.Missing):
		'method GetFirstCCD'
		return self._ApplyTypes_(10, 1, (8, 0), ((16392, 2),), u'GetFirstCCD', None,name
			)

	def GetFirstCCDByConfig(self, configID=defaultNamedNotOptArg, devName=pythoncom.Missing):
		'method GetFirstCCDByConfig'
		return self._ApplyTypes_(69, 1, (8, 0), ((8, 1), (16392, 2)), u'GetFirstCCDByConfig', None,configID
			, devName)

	def GetFirstComponent(self, name=pythoncom.Missing, creationDate=pythoncom.Missing):
		'method GetFirstComponent'
		return self._ApplyTypes_(36, 1, (8, 0), ((16392, 2), (16392, 2)), u'GetFirstComponent', None,name
			, creationDate)

	def GetFirstConfig(self, name=pythoncom.Missing):
		'method GetFirstConfig'
		return self._ApplyTypes_(2, 1, (8, 0), ((16392, 2),), u'GetFirstConfig', None,name
			)

	def GetFirstDetector(self, name=pythoncom.Missing):
		'method GetFirstDetector'
		return self._ApplyTypes_(8, 1, (8, 0), ((16392, 2),), u'GetFirstDetector', None,name
			)

	def GetFirstDevNode(self, devID=defaultNamedNotOptArg, nodeName=pythoncom.Missing):
		'method GetFirstDevNode'
		return self._ApplyTypes_(22, 1, (24, 0), ((8, 1), (16392, 2)), u'GetFirstDevNode', None,devID
			, nodeName)

	def GetFirstDevNodeChild(self, nodeName=defaultNamedNotOptArg, childNodeName=pythoncom.Missing):
		'method GetFirstDevNodeChild'
		return self._ApplyTypes_(26, 1, (24, 0), ((8, 1), (16392, 2)), u'GetFirstDevNodeChild', None,nodeName
			, childNodeName)

	def GetFirstDevValue(self, devID=defaultNamedNotOptArg, valueName=pythoncom.Missing):
		'method GetFirstDevValue'
		return self._ApplyTypes_(20, 1, (12, 0), ((8, 1), (16392, 2)), u'GetFirstDevValue', None,devID
			, valueName)

	def GetFirstDevice(self, name=pythoncom.Missing):
		'method GetFirstDevice'
		return self._ApplyTypes_(6, 1, (8, 0), ((16392, 2),), u'GetFirstDevice', None,name
			)

	def GetFirstDeviceByConfig(self, configID=defaultNamedNotOptArg, devName=pythoncom.Missing):
		'method GetFirstDeviceByConfig'
		return self._ApplyTypes_(4, 1, (8, 0), ((8, 1), (16392, 2)), u'GetFirstDeviceByConfig', None,configID
			, devName)

	def GetFirstFilterWheel(self, name=pythoncom.Missing):
		'method GetFirstFilterWheel'
		return self._ApplyTypes_(16, 1, (8, 0), ((16392, 2),), u'GetFirstFilterWheel', None,name
			)

	def GetFirstFocusMount(self, name=pythoncom.Missing):
		'method GetFirstFocusMount'
		return self._ApplyTypes_(61, 1, (8, 0), ((16392, 2),), u'GetFirstFocusMount', None,name
			)

	def GetFirstHVController(self, name=pythoncom.Missing):
		'method GetFirstHVController'
		return self._ApplyTypes_(63, 1, (8, 0), ((16392, 2),), u'GetFirstHVController', None,name
			)

	def GetFirstLaser(self, name=pythoncom.Missing):
		'method GetFirstLaser'
		return self._ApplyTypes_(82, 1, (8, 0), ((16392, 2),), u'GetFirstLaser', None,name
			)

	def GetFirstLightSource(self, name=pythoncom.Missing):
		'method GetFirstLightSource'
		return self._ApplyTypes_(47, 1, (8, 0), ((16392, 2),), u'GetFirstLightSource', None,name
			)

	def GetFirstMono(self, name=pythoncom.Missing):
		'method GetFirstMono'
		return self._ApplyTypes_(31, 1, (8, 0), ((16392, 2),), u'GetFirstMono', None,name
			)

	def GetFirstMonoByConfig(self, configID=defaultNamedNotOptArg, devName=pythoncom.Missing):
		'method GetFirstMonoByConfig'
		return self._ApplyTypes_(65, 1, (8, 0), ((8, 1), (16392, 2)), u'GetFirstMonoByConfig', None,configID
			, devName)

	def GetFirstNodeValue(self, nodeName=defaultNamedNotOptArg, valueName=pythoncom.Missing):
		'method GetFirstNodeValue'
		return self._ApplyTypes_(24, 1, (12, 0), ((8, 1), (16392, 2)), u'GetFirstNodeValue', None,nodeName
			, valueName)

	def GetFirstPolarizer(self, name=pythoncom.Missing):
		'method GetFirstPolarizer'
		return self._ApplyTypes_(18, 1, (8, 0), ((16392, 2),), u'GetFirstPolarizer', None,name
			)

	def GetFirstRelatedComponent(self, name=pythoncom.Missing, creationDate=pythoncom.Missing):
		'method GetFirstRelatedComponent'
		return self._ApplyTypes_(38, 1, (8, 0), ((16392, 2), (16392, 2)), u'GetFirstRelatedComponent', None,name
			, creationDate)

	def GetFirstSCD(self, name=pythoncom.Missing):
		'method GetFirstSCD'
		return self._ApplyTypes_(12, 1, (8, 0), ((16392, 2),), u'GetFirstSCD', None,name
			)

	def GetFirstSCDByConfig(self, configID=defaultNamedNotOptArg, devName=pythoncom.Missing):
		'method GetFirstSCDByConfig'
		return self._ApplyTypes_(67, 1, (8, 0), ((8, 1), (16392, 2)), u'GetFirstSCDByConfig', None,configID
			, devName)

	def GetFirstSampleChanger(self, name=pythoncom.Missing):
		'method GetFirstSampleChanger'
		return self._ApplyTypes_(59, 1, (8, 0), ((16392, 2),), u'GetFirstSampleChanger', None,name
			)

	def GetFirstSampleChangerByConfig(self, configID=defaultNamedNotOptArg, devName=pythoncom.Missing):
		'method GetFirstSampleChangerByConfig'
		return self._ApplyTypes_(73, 1, (8, 0), ((8, 1), (16392, 2)), u'GetFirstSampleChangerByConfig', None,configID
			, devName)

	def GetFirstStirrer(self, name=pythoncom.Missing):
		'method GetFirstStirrer'
		return self._ApplyTypes_(57, 1, (8, 0), ((16392, 2),), u'GetFirstStirrer', None,name
			)

	def GetFirstTCSPC(self, name=pythoncom.Missing):
		'method GetFirstTCSPC'
		return self._ApplyTypes_(55, 1, (8, 0), ((16392, 2),), u'GetFirstTCSPC', None,name
			)

	def GetFirstTCSPCdata(self, name=pythoncom.Missing):
		'method GetFirstTCSPCdata'
		return self._ApplyTypes_(53, 1, (8, 0), ((16392, 2),), u'GetFirstTCSPCdata', None,name
			)

	def GetFirstTemperatureControl(self, name=pythoncom.Missing):
		'method GetFirstTemperatureControl'
		return self._ApplyTypes_(34, 1, (8, 0), ((16392, 2),), u'GetFirstTemperatureControl', None,name
			)

	def GetFirstTemperatureControllerByConfig(self, configID=defaultNamedNotOptArg, devName=pythoncom.Missing):
		'method GetFirstTemperatureControllerByConfig'
		return self._ApplyTypes_(78, 1, (8, 0), ((8, 1), (16392, 2)), u'GetFirstTemperatureControllerByConfig', None,configID
			, devName)

	def GetFirstXYStageByConfig(self, configID=defaultNamedNotOptArg, devName=pythoncom.Missing):
		'method GetFirstXYStageByConfig'
		return self._ApplyTypes_(80, 1, (8, 0), ((8, 1), (16392, 2)), u'GetFirstXYStageByConfig', None,configID
			, devName)

	def GetNextAccessory(self, accType=defaultNamedNotOptArg, name=pythoncom.Missing):
		'method GetNextAccessory'
		return self._ApplyTypes_(15, 1, (8, 0), ((3, 1), (16392, 2)), u'GetNextAccessory', None,accType
			, name)

	def GetNextAccessoryByConfig(self, configID=defaultNamedNotOptArg, devName=pythoncom.Missing):
		'method GetNextAccessoryByConfig'
		return self._ApplyTypes_(72, 1, (8, 0), ((8, 1), (16392, 2)), u'GetNextAccessoryByConfig', None,configID
			, devName)

	def GetNextAvailableID(self, jyDevClass=defaultNamedNotOptArg, jyDevType=defaultNamedNotOptArg):
		'method GetNextAvailableID'
		# Result is a Unicode object
		return self._oleobj_.InvokeTypes(30, LCID, 1, (8, 0), ((3, 1), (3, 1)),jyDevClass
			, jyDevType)

	def GetNextCCD(self, name=pythoncom.Missing):
		'method GetNextCCD'
		return self._ApplyTypes_(11, 1, (8, 0), ((16392, 2),), u'GetNextCCD', None,name
			)

	def GetNextCCDByConfig(self, configID=defaultNamedNotOptArg, devName=pythoncom.Missing):
		'method GetNextCCDByConfig'
		return self._ApplyTypes_(70, 1, (8, 0), ((8, 1), (16392, 2)), u'GetNextCCDByConfig', None,configID
			, devName)

	def GetNextComponent(self, name=pythoncom.Missing, creationDate=pythoncom.Missing):
		'method GetNextComponent'
		return self._ApplyTypes_(37, 1, (8, 0), ((16392, 2), (16392, 2)), u'GetNextComponent', None,name
			, creationDate)

	def GetNextConfig(self, name=pythoncom.Missing):
		'method GetNextConfig'
		return self._ApplyTypes_(3, 1, (8, 0), ((16392, 2),), u'GetNextConfig', None,name
			)

	def GetNextDetector(self, name=pythoncom.Missing):
		'method GetNextDetector'
		return self._ApplyTypes_(9, 1, (8, 0), ((16392, 2),), u'GetNextDetector', None,name
			)

	def GetNextDevNode(self, devID=defaultNamedNotOptArg, nodeName=pythoncom.Missing):
		'method GetNextDevNode'
		return self._ApplyTypes_(23, 1, (24, 0), ((8, 1), (16392, 2)), u'GetNextDevNode', None,devID
			, nodeName)

	def GetNextDevNodeChild(self, nodeName=defaultNamedNotOptArg, childNodeName=pythoncom.Missing):
		'method GetNextDevNodeChild'
		return self._ApplyTypes_(27, 1, (24, 0), ((8, 1), (16392, 2)), u'GetNextDevNodeChild', None,nodeName
			, childNodeName)

	def GetNextDevValue(self, devID=defaultNamedNotOptArg, valueName=pythoncom.Missing):
		'method GetNextDevValue'
		return self._ApplyTypes_(21, 1, (12, 0), ((8, 1), (16392, 2)), u'GetNextDevValue', None,devID
			, valueName)

	def GetNextDevice(self, name=pythoncom.Missing):
		'method GetNextDevice'
		return self._ApplyTypes_(7, 1, (8, 0), ((16392, 2),), u'GetNextDevice', None,name
			)

	def GetNextDeviceByConfig(self, configID=defaultNamedNotOptArg, devName=pythoncom.Missing):
		'method GetNextDeviceByConfig'
		return self._ApplyTypes_(5, 1, (8, 0), ((8, 1), (16392, 2)), u'GetNextDeviceByConfig', None,configID
			, devName)

	def GetNextFilterWheel(self, name=pythoncom.Missing):
		'method GetNextFilterWheel'
		return self._ApplyTypes_(17, 1, (8, 0), ((16392, 2),), u'GetNextFilterWheel', None,name
			)

	def GetNextFocusMount(self, name=pythoncom.Missing):
		'method GetNextFocusMount'
		return self._ApplyTypes_(62, 1, (8, 0), ((16392, 2),), u'GetNextFocusMount', None,name
			)

	def GetNextHVController(self, name=pythoncom.Missing):
		'method GetNextHVController'
		return self._ApplyTypes_(64, 1, (8, 0), ((16392, 2),), u'GetNextHVController', None,name
			)

	def GetNextLaser(self, name=pythoncom.Missing):
		'method GetNextLaser'
		return self._ApplyTypes_(83, 1, (8, 0), ((16392, 2),), u'GetNextLaser', None,name
			)

	def GetNextLightSource(self, name=pythoncom.Missing):
		'method GetNextLightSource'
		return self._ApplyTypes_(48, 1, (8, 0), ((16392, 2),), u'GetNextLightSource', None,name
			)

	def GetNextMono(self, name=pythoncom.Missing):
		'method GetNextMono'
		return self._ApplyTypes_(32, 1, (8, 0), ((16392, 2),), u'GetNextMono', None,name
			)

	def GetNextMonoByConfig(self, configID=defaultNamedNotOptArg, devName=pythoncom.Missing):
		'method GetNextMonoByConfig'
		return self._ApplyTypes_(66, 1, (8, 0), ((8, 1), (16392, 2)), u'GetNextMonoByConfig', None,configID
			, devName)

	def GetNextNodeValue(self, nodeName=defaultNamedNotOptArg, valueName=pythoncom.Missing):
		'method GetNextNodeValue'
		return self._ApplyTypes_(25, 1, (12, 0), ((8, 1), (16392, 2)), u'GetNextNodeValue', None,nodeName
			, valueName)

	def GetNextPolarizer(self, name=pythoncom.Missing):
		'method GetNextPolarizer'
		return self._ApplyTypes_(19, 1, (8, 0), ((16392, 2),), u'GetNextPolarizer', None,name
			)

	def GetNextRelatedComponent(self, name=pythoncom.Missing, creationDate=pythoncom.Missing):
		'method GetNextRelatedComponent'
		return self._ApplyTypes_(39, 1, (8, 0), ((16392, 2), (16392, 2)), u'GetNextRelatedComponent', None,name
			, creationDate)

	def GetNextSCD(self, name=pythoncom.Missing):
		'method GetNextSCD'
		return self._ApplyTypes_(13, 1, (8, 0), ((16392, 2),), u'GetNextSCD', None,name
			)

	def GetNextSCDByConfig(self, configID=defaultNamedNotOptArg, devName=pythoncom.Missing):
		'method GetNextSCDByConfig'
		return self._ApplyTypes_(68, 1, (8, 0), ((8, 1), (16392, 2)), u'GetNextSCDByConfig', None,configID
			, devName)

	def GetNextSampleChanger(self, name=pythoncom.Missing):
		'method GetNextSampleChanger'
		return self._ApplyTypes_(60, 1, (8, 0), ((16392, 2),), u'GetNextSampleChanger', None,name
			)

	def GetNextSampleChangerByConfig(self, configID=defaultNamedNotOptArg, devName=pythoncom.Missing):
		'method GetNextSampleChangerByConfig'
		return self._ApplyTypes_(74, 1, (8, 0), ((8, 1), (16392, 2)), u'GetNextSampleChangerByConfig', None,configID
			, devName)

	def GetNextStirrer(self, name=pythoncom.Missing):
		'method GetNextStirrer'
		return self._ApplyTypes_(58, 1, (8, 0), ((16392, 2),), u'GetNextStirrer', None,name
			)

	def GetNextTCSPC(self, name=pythoncom.Missing):
		'method GetNextTCSPC'
		return self._ApplyTypes_(56, 1, (8, 0), ((16392, 2),), u'GetNextTCSPC', None,name
			)

	def GetNextTCSPCdata(self, name=pythoncom.Missing):
		'method GetNextTCSPCdata'
		return self._ApplyTypes_(54, 1, (8, 0), ((16392, 2),), u'GetNextTCSPCdata', None,name
			)

	def GetNextTemperatureControl(self, name=pythoncom.Missing):
		'method GetNextTemperatureControl'
		return self._ApplyTypes_(35, 1, (8, 0), ((16392, 2),), u'GetNextTemperatureControl', None,name
			)

	def GetNextTemperatureControllerByConfig(self, configID=defaultNamedNotOptArg, devName=pythoncom.Missing):
		'method GetNextTemperatureControllerByConfig'
		return self._ApplyTypes_(79, 1, (8, 0), ((8, 1), (16392, 2)), u'GetNextTemperatureControllerByConfig', None,configID
			, devName)

	def GetNextXYStageByConfig(self, configID=defaultNamedNotOptArg, devName=pythoncom.Missing):
		'method GetNextXYStageByConfig'
		return self._ApplyTypes_(81, 1, (8, 0), ((8, 1), (16392, 2)), u'GetNextXYStageByConfig', None,configID
			, devName)

	def Load(self):
		'method Load'
		return self._oleobj_.InvokeTypes(1, LCID, 1, (24, 0), (),)

	def LoadFromFile(self, fullFileName=defaultNamedNotOptArg):
		'method LoadFromFile'
		return self._oleobj_.InvokeTypes(29, LCID, 1, (24, 0), ((8, 1),),fullFileName
			)

	def PackageSupportInfo(self, fullFileName=defaultNamedNotOptArg):
		'method PackageSupportInfo'
		return self._oleobj_.InvokeTypes(46, LCID, 1, (24, 0), ((8, 1),),fullFileName
			)

	def Unload(self):
		'method Unload'
		return self._oleobj_.InvokeTypes(33, LCID, 1, (24, 0), (),)

	def WriteToFile(self, fullFileName=defaultNamedNotOptArg):
		'method WriteToFile'
		return self._oleobj_.InvokeTypes(28, LCID, 1, (24, 0), ((8, 1),),fullFileName
			)

	_prop_map_get_ = {
	}
	_prop_map_put_ = {
	}
	def __iter__(self):
		"Return a Python iterator for this object"
		try:
			ob = self._oleobj_.InvokeTypes(-4,LCID,3,(13, 10),())
		except pythoncom.error:
			raise TypeError("This object does not support enumeration")
		return win32com.client.util.Iterator(ob, None)

class _IJYConfigBrowerInterfaceEvents:
	'_IJYConfigBrowerInterfaceEvents Interface'
	CLSID = CLSID_Sink = IID('{06C073A5-AD0F-4A9C-A048-E2789C3594C9}')
	coclass_clsid = IID('{3A457ACC-F1FB-4D7D-9AB4-EE427CE33385}')
	_public_methods_ = [] # For COM Server support
	_dispid_to_func_ = {
		}

	def __init__(self, oobj = None):
		if oobj is None:
			self._olecp = None
		else:
			import win32com.server.util
			from win32com.server.policy import EventHandlerPolicy
			cpc=oobj._oleobj_.QueryInterface(pythoncom.IID_IConnectionPointContainer)
			cp=cpc.FindConnectionPoint(self.CLSID_Sink)
			cookie=cp.Advise(win32com.server.util.wrap(self, usePolicy=EventHandlerPolicy))
			self._olecp,self._olecp_cookie = cp,cookie
	def __del__(self):
		try:
			self.close()
		except pythoncom.com_error:
			pass
	def close(self):
		if self._olecp is not None:
			cp,cookie,self._olecp,self._olecp_cookie = self._olecp,self._olecp_cookie,None,None
			cp.Unadvise(cookie)
	def _query_interface_(self, iid):
		import win32com.server.util
		if iid==self.CLSID_Sink: return win32com.server.util.wrap(self)

	# Event Handlers
	# If you create handlers, they should have the following prototypes:


class CoClassBaseClass:
	def __init__(self, oobj=None):
         pythoncom.CoInitialize()
         if oobj is None: oobj = pythoncom.new(self.CLSID)
         self.__dict__["_dispobj_"] = self.default_interface(oobj)
	def __repr__(self):
		return "<win32com.gen_py.%s.%s>" % (__doc__, self.__class__.__name__)

	def __getattr__(self, attr):
		d=self.__dict__["_dispobj_"]
		if d is not None: return getattr(d, attr)
		raise AttributeError(attr)
	def __setattr__(self, attr, value):
		if attr in self.__dict__: self.__dict__[attr] = value; return
		try:
			d=self.__dict__["_dispobj_"]
			if d is not None:
				d.__setattr__(attr, value)
				return
		except AttributeError:
			pass
		self.__dict__[attr] = value
  
# This CoClass is known by the name 'JYConfigBrowserComponent.JYConfigBrowerInterface.1'
class JYConfigBrowerInterface(CoClassBaseClass): # A CoClass
	# JYConfigBrowerInterface Class
	CLSID = IID('{3A457ACC-F1FB-4D7D-9AB4-EE427CE33385}')
	coclass_sources = [
		_IJYConfigBrowerInterfaceEvents,
	]
	default_source = _IJYConfigBrowerInterfaceEvents
	coclass_interfaces = [
		IJYConfigBrowerInterface,
	]
	default_interface = IJYConfigBrowerInterface

IJYConfigBrowerInterface_vtables_dispatch_ = 1
IJYConfigBrowerInterface_vtables_ = [
	(( u'Load' , ), 1, (1, (), [ ], 1 , 1 , 4 , 0 , 28 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstConfig' , u'name' , u'configID' , ), 2, (2, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 32 , (3, 0, None, None) , 0 , )),
	(( u'GetNextConfig' , u'name' , u'configID' , ), 3, (3, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 36 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstDeviceByConfig' , u'configID' , u'devName' , u'devID' , ), 4, (4, (), [ 
			(8, 1, None, None) , (16392, 2, None, None) , (16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 40 , (3, 0, None, None) , 0 , )),
	(( u'GetNextDeviceByConfig' , u'configID' , u'devName' , u'devID' , ), 5, (5, (), [ 
			(8, 1, None, None) , (16392, 2, None, None) , (16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 44 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstDevice' , u'name' , u'devID' , ), 6, (6, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 48 , (3, 0, None, None) , 0 , )),
	(( u'GetNextDevice' , u'name' , u'devID' , ), 7, (7, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 52 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstDetector' , u'name' , u'detectorID' , ), 8, (8, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 56 , (3, 0, None, None) , 0 , )),
	(( u'GetNextDetector' , u'name' , u'detectorID' , ), 9, (9, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 60 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstCCD' , u'name' , u'ccdID' , ), 10, (10, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 64 , (3, 0, None, None) , 0 , )),
	(( u'GetNextCCD' , u'name' , u'ccdID' , ), 11, (11, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 68 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstSCD' , u'name' , u'ccdID' , ), 12, (12, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 72 , (3, 0, None, None) , 0 , )),
	(( u'GetNextSCD' , u'name' , u'ccdID' , ), 13, (13, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 76 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstAccessory' , u'accType' , u'name' , u'accID' , ), 14, (14, (), [ 
			(3, 1, None, None) , (16392, 2, None, None) , (16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 80 , (3, 0, None, None) , 0 , )),
	(( u'GetNextAccessory' , u'accType' , u'name' , u'accID' , ), 15, (15, (), [ 
			(3, 1, None, None) , (16392, 2, None, None) , (16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 84 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstFilterWheel' , u'name' , u'accID' , ), 16, (16, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 88 , (3, 0, None, None) , 0 , )),
	(( u'GetNextFilterWheel' , u'name' , u'accID' , ), 17, (17, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 92 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstPolarizer' , u'name' , u'accID' , ), 18, (18, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 96 , (3, 0, None, None) , 0 , )),
	(( u'GetNextPolarizer' , u'name' , u'accID' , ), 19, (19, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 100 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstDevValue' , u'devID' , u'valueName' , u'value' , ), 20, (20, (), [ 
			(8, 1, None, None) , (16392, 2, None, None) , (16396, 10, None, None) , ], 1 , 1 , 4 , 0 , 104 , (3, 0, None, None) , 0 , )),
	(( u'GetNextDevValue' , u'devID' , u'valueName' , u'value' , ), 21, (21, (), [ 
			(8, 1, None, None) , (16392, 2, None, None) , (16396, 10, None, None) , ], 1 , 1 , 4 , 0 , 108 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstDevNode' , u'devID' , u'nodeName' , ), 22, (22, (), [ (8, 1, None, None) , 
			(16392, 2, None, None) , ], 1 , 1 , 4 , 0 , 112 , (3, 0, None, None) , 0 , )),
	(( u'GetNextDevNode' , u'devID' , u'nodeName' , ), 23, (23, (), [ (8, 1, None, None) , 
			(16392, 2, None, None) , ], 1 , 1 , 4 , 0 , 116 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstNodeValue' , u'nodeName' , u'valueName' , u'value' , ), 24, (24, (), [ 
			(8, 1, None, None) , (16392, 2, None, None) , (16396, 10, None, None) , ], 1 , 1 , 4 , 0 , 120 , (3, 0, None, None) , 0 , )),
	(( u'GetNextNodeValue' , u'nodeName' , u'valueName' , u'value' , ), 25, (25, (), [ 
			(8, 1, None, None) , (16392, 2, None, None) , (16396, 10, None, None) , ], 1 , 1 , 4 , 0 , 124 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstDevNodeChild' , u'nodeName' , u'childNodeName' , ), 26, (26, (), [ (8, 1, None, None) , 
			(16392, 2, None, None) , ], 1 , 1 , 4 , 0 , 128 , (3, 0, None, None) , 0 , )),
	(( u'GetNextDevNodeChild' , u'nodeName' , u'childNodeName' , ), 27, (27, (), [ (8, 1, None, None) , 
			(16392, 2, None, None) , ], 1 , 1 , 4 , 0 , 132 , (3, 0, None, None) , 0 , )),
	(( u'WriteToFile' , u'fullFileName' , ), 28, (28, (), [ (8, 1, None, None) , ], 1 , 1 , 4 , 0 , 136 , (3, 0, None, None) , 0 , )),
	(( u'LoadFromFile' , u'fullFileName' , ), 29, (29, (), [ (8, 1, None, None) , ], 1 , 1 , 4 , 0 , 140 , (3, 0, None, None) , 0 , )),
	(( u'GetNextAvailableID' , u'jyDevClass' , u'jyDevType' , u'newDevID' , ), 30, (30, (), [ 
			(3, 1, None, None) , (3, 1, None, None) , (16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 144 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstMono' , u'name' , u'monoID' , ), 31, (31, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 148 , (3, 0, None, None) , 0 , )),
	(( u'GetNextMono' , u'name' , u'monoID' , ), 32, (32, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 152 , (3, 0, None, None) , 0 , )),
	(( u'Unload' , ), 33, (33, (), [ ], 1 , 1 , 4 , 0 , 156 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstTemperatureControl' , u'name' , u'accID' , ), 34, (34, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 160 , (3, 0, None, None) , 0 , )),
	(( u'GetNextTemperatureControl' , u'name' , u'accID' , ), 35, (35, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 164 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstComponent' , u'name' , u'creationDate' , u'versionNumber' , ), 36, (36, (), [ 
			(16392, 2, None, None) , (16392, 2, None, None) , (16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 168 , (3, 0, None, None) , 0 , )),
	(( u'GetNextComponent' , u'name' , u'creationDate' , u'versionNumber' , ), 37, (37, (), [ 
			(16392, 2, None, None) , (16392, 2, None, None) , (16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 172 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstRelatedComponent' , u'name' , u'creationDate' , u'versionNumber' , ), 38, (38, (), [ 
			(16392, 2, None, None) , (16392, 2, None, None) , (16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 176 , (3, 0, None, None) , 0 , )),
	(( u'GetNextRelatedComponent' , u'name' , u'creationDate' , u'versionNumber' , ), 39, (39, (), [ 
			(16392, 2, None, None) , (16392, 2, None, None) , (16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 180 , (3, 0, None, None) , 0 , )),
	(( u'GatherOriginInfo' , ), 40, (40, (), [ ], 1 , 1 , 4 , 0 , 184 , (3, 0, None, None) , 0 , )),
	(( u'GatherCCDInfo' , ), 41, (41, (), [ ], 1 , 1 , 4 , 0 , 188 , (3, 0, None, None) , 0 , )),
	(( u'GatherDatabaseInfo' , ), 42, (42, (), [ ], 1 , 1 , 4 , 0 , 192 , (3, 0, None, None) , 0 , )),
	(( u'GatherVersionInfo' , ), 43, (43, (), [ ], 1 , 1 , 4 , 0 , 196 , (3, 0, None, None) , 0 , )),
	(( u'GatherRegistryInfo' , ), 44, (44, (), [ ], 1 , 1 , 4 , 0 , 200 , (3, 0, None, None) , 0 , )),
	(( u'GatherLogInfo' , ), 45, (45, (), [ ], 1 , 1 , 4 , 0 , 204 , (3, 0, None, None) , 0 , )),
	(( u'PackageSupportInfo' , u'fullFileName' , ), 46, (46, (), [ (8, 1, None, None) , ], 1 , 1 , 4 , 0 , 208 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstLightSource' , u'name' , u'accID' , ), 47, (47, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 212 , (3, 0, None, None) , 0 , )),
	(( u'GetNextLightSource' , u'name' , u'accID' , ), 48, (48, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 216 , (3, 0, None, None) , 0 , )),
	(( u'GetDevIdFromDevName' , u'devName' , u'devID' , ), 49, (49, (), [ (8, 1, None, None) , 
			(16392, 2, None, None) , ], 1 , 1 , 4 , 0 , 220 , (3, 0, None, None) , 0 , )),
	(( u'DisplayCurrentConfiguration' , ), 50, (50, (), [ ], 1 , 1 , 4 , 0 , 224 , (3, 0, None, None) , 0 , )),
	(( u'DeleteDeviceById' , u'devID' , ), 51, (51, (), [ (8, 1, None, None) , ], 1 , 1 , 4 , 0 , 228 , (3, 0, None, None) , 0 , )),
	(( u'GetDevIdByConfig' , u'configID' , u'cdc' , u'devClass' , u'devID' , 
			), 52, (52, (), [ (8, 1, None, None) , (3, 1, None, None) , (3, 1, None, None) , (16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 232 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstTCSPCdata' , u'name' , u'TcspcDataID' , ), 53, (53, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 236 , (3, 0, None, None) , 0 , )),
	(( u'GetNextTCSPCdata' , u'name' , u'TcspcDataID' , ), 54, (54, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 240 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstTCSPC' , u'name' , u'tcspcID' , ), 55, (55, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 244 , (3, 0, None, None) , 0 , )),
	(( u'GetNextTCSPC' , u'name' , u'tcspcID' , ), 56, (56, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 248 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstStirrer' , u'name' , u'stirrerID' , ), 57, (57, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 252 , (3, 0, None, None) , 0 , )),
	(( u'GetNextStirrer' , u'name' , u'stirrerID' , ), 58, (58, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 256 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstSampleChanger' , u'name' , u'scID' , ), 59, (59, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 260 , (3, 0, None, None) , 0 , )),
	(( u'GetNextSampleChanger' , u'name' , u'scID' , ), 60, (60, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 264 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstFocusMount' , u'name' , u'focusID' , ), 61, (61, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 268 , (3, 0, None, None) , 0 , )),
	(( u'GetNextFocusMount' , u'name' , u'focusID' , ), 62, (62, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 272 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstHVController' , u'name' , u'HVcontrollerID' , ), 63, (63, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 276 , (3, 0, None, None) , 0 , )),
	(( u'GetNextHVController' , u'name' , u'HVcontrollerID' , ), 64, (64, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 280 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstMonoByConfig' , u'configID' , u'devName' , u'devID' , ), 65, (65, (), [ 
			(8, 1, None, None) , (16392, 2, None, None) , (16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 284 , (3, 0, None, None) , 0 , )),
	(( u'GetNextMonoByConfig' , u'configID' , u'devName' , u'devID' , ), 66, (66, (), [ 
			(8, 1, None, None) , (16392, 2, None, None) , (16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 288 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstSCDByConfig' , u'configID' , u'devName' , u'devID' , ), 67, (67, (), [ 
			(8, 1, None, None) , (16392, 2, None, None) , (16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 292 , (3, 0, None, None) , 0 , )),
	(( u'GetNextSCDByConfig' , u'configID' , u'devName' , u'devID' , ), 68, (68, (), [ 
			(8, 1, None, None) , (16392, 2, None, None) , (16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 296 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstCCDByConfig' , u'configID' , u'devName' , u'devID' , ), 69, (69, (), [ 
			(8, 1, None, None) , (16392, 2, None, None) , (16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 300 , (3, 0, None, None) , 0 , )),
	(( u'GetNextCCDByConfig' , u'configID' , u'devName' , u'devID' , ), 70, (70, (), [ 
			(8, 1, None, None) , (16392, 2, None, None) , (16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 304 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstAccessoryByConfig' , u'configID' , u'devName' , u'devID' , ), 71, (71, (), [ 
			(8, 1, None, None) , (16392, 2, None, None) , (16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 308 , (3, 0, None, None) , 0 , )),
	(( u'GetNextAccessoryByConfig' , u'configID' , u'devName' , u'devID' , ), 72, (72, (), [ 
			(8, 1, None, None) , (16392, 2, None, None) , (16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 312 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstSampleChangerByConfig' , u'configID' , u'devName' , u'devID' , ), 73, (73, (), [ 
			(8, 1, None, None) , (16392, 2, None, None) , (16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 316 , (3, 0, None, None) , 0 , )),
	(( u'GetNextSampleChangerByConfig' , u'configID' , u'devName' , u'devID' , ), 74, (74, (), [ 
			(8, 1, None, None) , (16392, 2, None, None) , (16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 320 , (3, 0, None, None) , 0 , )),
	(( u'GetDefaultConfig' , u'name' , ), 75, (75, (), [ (16392, 2, None, None) , ], 1 , 1 , 4 , 0 , 324 , (3, 0, None, None) , 0 , )),
	(( u'GetDataExperimentPathsByConfig' , u'configID' , u'pathData' , u'pathExp' , ), 76, (76, (), [ 
			(8, 1, None, None) , (16392, 2, None, None) , (16392, 2, None, None) , ], 1 , 1 , 4 , 0 , 328 , (3, 0, None, None) , 0 , )),
	(( u'GetDefaultApplicationType' , u'appType' , ), 77, (77, (), [ (16387, 2, None, None) , ], 1 , 1 , 4 , 0 , 332 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstTemperatureControllerByConfig' , u'configID' , u'devName' , u'devID' , ), 78, (78, (), [ 
			(8, 1, None, None) , (16392, 2, None, None) , (16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 336 , (3, 0, None, None) , 0 , )),
	(( u'GetNextTemperatureControllerByConfig' , u'configID' , u'devName' , u'devID' , ), 79, (79, (), [ 
			(8, 1, None, None) , (16392, 2, None, None) , (16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 340 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstXYStageByConfig' , u'configID' , u'devName' , u'devID' , ), 80, (80, (), [ 
			(8, 1, None, None) , (16392, 2, None, None) , (16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 344 , (3, 0, None, None) , 0 , )),
	(( u'GetNextXYStageByConfig' , u'configID' , u'devName' , u'devID' , ), 81, (81, (), [ 
			(8, 1, None, None) , (16392, 2, None, None) , (16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 348 , (3, 0, None, None) , 0 , )),
	(( u'GetFirstLaser' , u'name' , u'laserID' , ), 82, (82, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 352 , (3, 0, None, None) , 0 , )),
	(( u'GetNextLaser' , u'name' , u'laserID' , ), 83, (83, (), [ (16392, 2, None, None) , 
			(16392, 10, None, None) , ], 1 , 1 , 4 , 0 , 356 , (3, 0, None, None) , 0 , )),
]

RecordMap = {
}

CLSIDToClassMap = {
	'{06C073A5-AD0F-4A9C-A048-E2789C3594C9}' : _IJYConfigBrowerInterfaceEvents,
	'{FCAC56F8-B378-42AB-8C6C-A41596864D4D}' : IJYConfigBrowerInterface,
	'{3A457ACC-F1FB-4D7D-9AB4-EE427CE33385}' : JYConfigBrowerInterface,
}
CLSIDToPackageMap = {}
win32com.client.CLSIDToClass.RegisterCLSIDsFromDict( CLSIDToClassMap )
VTablesToPackageMap = {}
VTablesToClassMap = {
	'{FCAC56F8-B378-42AB-8C6C-A41596864D4D}' : 'IJYConfigBrowerInterface',
}


NamesToIIDMap = {
	'IJYConfigBrowerInterface' : '{FCAC56F8-B378-42AB-8C6C-A41596864D4D}',
	'_IJYConfigBrowerInterfaceEvents' : '{06C073A5-AD0F-4A9C-A048-E2789C3594C9}',
}


