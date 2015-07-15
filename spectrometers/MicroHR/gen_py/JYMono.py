# -*- coding: mbcs -*-
# Created by makepy.py version 0.5.01
# By python version 2.7.9 (default, Dec 10 2014, 12:24:55) [MSC v.1500 32 bit (Intel)]
# From type library 'JYMono.dll'
# On Thu Jul 09 22:15:33 2015
'JYMono 1.0 Type Library'
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

CLSID = IID('{D7E942DC-3716-4BC1-8DA2-08D273BDC501}')
MajorVersion = 1
MinorVersion = 0
LibraryFlags = 8
LCID = 0x0

from win32com.client import DispatchBaseClass
class IJYMonoReqd(DispatchBaseClass):
	'IJYMonoReqd Interface'
	CLSID = IID('{7963F672-D074-4F67-B15C-AF022065927E}')
	coclass_clsid = IID('{BFF968D4-7B20-4D16-BD3A-BDEFEB0863A4}')

	def Calibrate(self, actualWavelength=defaultNamedNotOptArg):
		'method Calibrate'
		return self._oleobj_.InvokeTypes(605, LCID, 1, (24, 0), ((5, 1),),actualWavelength
			)

	def CalibrateSlitWidth(self, slitNumber=defaultNamedNotOptArg):
		'method CalibrateSlitWidth'
		return self._oleobj_.InvokeTypes(608, LCID, 1, (24, 0), ((3, 1),),slitNumber
			)

	def CanDeviceChangeAddress(self):
		'method CanDeviceChangeAddress'
		return self._oleobj_.InvokeTypes(153, LCID, 1, (11, 0), (),)

	def CheckLightPath(self, inPort=defaultNamedNotOptArg, outPort=defaultNamedNotOptArg):
		'method CheckLightPath'
		return self._oleobj_.InvokeTypes(21, LCID, 1, (11, 0), ((3, 1), (3, 1)),inPort
			, outPort)

	def CloseCommunications(self):
		'method CloseCommunications'
		return self._oleobj_.InvokeTypes(11, LCID, 1, (24, 0), (),)

	def CloseShutter(self):
		'method CloseShutter'
		return self._oleobj_.InvokeTypes(615, LCID, 1, (24, 0), (),)

	def Configure(self):
		'method Configure'
		return self._oleobj_.InvokeTypes(100, LCID, 1, (24, 0), (),)

	def DisableAllInputTriggers(self):
		'method DisableAllInputTriggers'
		return self._oleobj_.InvokeTypes(132, LCID, 1, (24, 0), (),)

	def DisableAllOutputTriggers(self):
		'method DisableAllOutputTriggers'
		return self._oleobj_.InvokeTypes(141, LCID, 1, (24, 0), (),)

	def DisableInputTrigger(self, trigAddress=defaultNamedNotOptArg, event=defaultNamedNotOptArg, sigType=defaultNamedNotOptArg):
		'method DisableInputTrigger'
		return self._oleobj_.InvokeTypes(131, LCID, 1, (24, 0), ((3, 1), (3, 1), (3, 1)),trigAddress
			, event, sigType)

	def DisableOutputTrigger(self, trigAddress=defaultNamedNotOptArg, event=defaultNamedNotOptArg, sigType=defaultNamedNotOptArg):
		'method DisableOutputTrigger'
		return self._oleobj_.InvokeTypes(140, LCID, 1, (24, 0), ((3, 1), (3, 1), (3, 1)),trigAddress
			, event, sigType)

	def EnableInputTrigger(self, trigAddress=defaultNamedNotOptArg, event=defaultNamedNotOptArg, sigType=defaultNamedNotOptArg):
		'method EnableInputTrigger'
		return self._oleobj_.InvokeTypes(130, LCID, 1, (24, 0), ((3, 1), (3, 1), (3, 1)),trigAddress
			, event, sigType)

	def EnableOutputTrigger(self, trigAddress=defaultNamedNotOptArg, event=defaultNamedNotOptArg, sigType=defaultNamedNotOptArg):
		'method EnableOutputTrigger'
		return self._oleobj_.InvokeTypes(139, LCID, 1, (24, 0), ((3, 1), (3, 1), (3, 1)),trigAddress
			, event, sigType)

	def GetComponentVersion(self, major=pythoncom.Missing, minor=pythoncom.Missing, mini=pythoncom.Missing, buildNum=pythoncom.Missing):
		'method GetComponentVersion'
		return self._ApplyTypes_(27, 1, (8, 0), ((16387, 2), (16387, 2), (16387, 2), (16387, 2)), u'GetComponentVersion', None,major
			, minor, mini, buildNum)

	def GetControllerOperationValue(self, token=defaultNamedNotOptArg, lastSet=pythoncom.Missing):
		'method GetControllerOperationValue'
		return self._ApplyTypes_(117, 1, (5, 0), ((3, 1), (16389, 2)), u'GetControllerOperationValue', None,token
			, lastSet)

	def GetConverterReference(self, pVal=pythoncom.Missing):
		'method GetConverterReference'
		return self._ApplyTypes_(112, 1, (24, 0), ((16393, 2),), u'GetConverterReference', None,pVal
			)

	def GetCurrentGrating(self, pGratingDensity=pythoncom.Missing, pGratings=pythoncom.Missing):
		'method GetCurrentGrating'
		return self._ApplyTypes_(602, 1, (24, 0), ((16389, 2), (16396, 2)), u'GetCurrentGrating', None,pGratingDensity
			, pGratings)

	def GetCurrentGratingWithDetails(self, pGratingDensity=pythoncom.Missing, pGratings=pythoncom.Missing, pBlaze=pythoncom.Missing, pDescription=pythoncom.Missing):
		'method GetCurrentGratingWithDetails'
		return self._ApplyTypes_(625, 1, (24, 0), ((16389, 2), (16396, 2), (16396, 2), (16396, 2)), u'GetCurrentGratingWithDetails', None,pGratingDensity
			, pGratings, pBlaze, pDescription)

	def GetCurrentMirrorPosition(self, MirrorNumber=defaultNamedNotOptArg):
		'method GetMirrorPosition'
		return self._oleobj_.InvokeTypes(613, LCID, 1, (3, 0), ((3, 1),),MirrorNumber
			)

	def GetCurrentShutterPosition(self):
		'method GetCurrentShutterPosition'
		return self._oleobj_.InvokeTypes(616, LCID, 1, (3, 0), (),)

	def GetCurrentSlitWidth(self, sl=defaultNamedNotOptArg):
		'method GetCurrentSlitWidth'
		return self._oleobj_.InvokeTypes(607, LCID, 1, (5, 0), ((3, 1),),sl
			)

	def GetCurrentTurret(self):
		'method GetCurrentTurret'
		return self._oleobj_.InvokeTypes(627, LCID, 1, (3, 0), (),)

	def GetCurrentWavelength(self):
		'method GetCurrentWavelength'
		return self._oleobj_.InvokeTypes(604, LCID, 1, (5, 0), (),)

	def GetDefaultUnits(self, type=defaultNamedNotOptArg, pVal=pythoncom.Missing, pStrVal=pythoncom.Missing):
		'method GetDefaultUnits'
		return self._ApplyTypes_(110, 1, (24, 0), ((3, 1), (16387, 2), (16396, 18)), u'GetDefaultUnits', None,type
			, pVal, pStrVal)

	def GetDeviceAddress(self, devAddress=pythoncom.Missing):
		'method GetDeviceAddress'
		return self._ApplyTypes_(151, 1, (24, 0), ((16396, 2),), u'GetDeviceAddress', None,devAddress
			)

	def GetDeviceConfigProperty(self, property=defaultNamedNotOptArg):
		'method GetDeviceConfigProperty'
		return self._ApplyTypes_(148, 1, (12, 0), ((3, 1),), u'GetDeviceConfigProperty', None,property
			)

	def GetFirstControllerOperation(self, token=pythoncom.Missing, Description=pythoncom.Missing, currentValue=pythoncom.Missing):
		'method GetFirstControllerOperation'
		return self._ApplyTypes_(114, 1, (24, 0), ((16387, 2), (16392, 2), (16389, 2)), u'GetFirstControllerOperation', None,token
			, Description, currentValue)

	def GetFirstOperatingMode(self, modeName=pythoncom.Missing):
		'method GetFirstOperatingMode'
		return self._ApplyTypes_(119, 1, (3, 0), ((16392, 2),), u'GetFirstOperatingMode', None,modeName
			)

	def GetFirstSupportedInputTriggerAddress(self, trigAddress=pythoncom.Missing, trigAddressString=pythoncom.Missing):
		'method GetFirstSupportedInputTriggerAddress'
		return self._ApplyTypes_(124, 1, (24, 0), ((16387, 2), (16392, 2)), u'GetFirstSupportedInputTriggerAddress', None,trigAddress
			, trigAddressString)

	def GetFirstSupportedInputTriggerEvent(self, trigAddress=defaultNamedNotOptArg, eventPtr=pythoncom.Missing, trigEventString=pythoncom.Missing):
		'method GetFirstSupportedInputTriggerEvent'
		return self._ApplyTypes_(126, 1, (24, 0), ((3, 1), (16387, 2), (16392, 2)), u'GetFirstSupportedInputTriggerEvent', None,trigAddress
			, eventPtr, trigEventString)

	def GetFirstSupportedInputTriggerSignalType(self, trigAddress=defaultNamedNotOptArg, event=defaultNamedNotOptArg, trigSigType=pythoncom.Missing, trigSigTypeString=pythoncom.Missing):
		'method GetFirstSupportedInputTriggerSignalType'
		return self._ApplyTypes_(128, 1, (24, 0), ((3, 1), (3, 1), (16387, 2), (16392, 2)), u'GetFirstSupportedInputTriggerSignalType', None,trigAddress
			, event, trigSigType, trigSigTypeString)

	def GetFirstSupportedOutputTriggerAddress(self, trigAddress=pythoncom.Missing, trigAddressString=pythoncom.Missing):
		'method GetFirstSupportedOutputTriggerAddress'
		return self._ApplyTypes_(133, 1, (24, 0), ((16387, 2), (16392, 2)), u'GetFirstSupportedOutputTriggerAddress', None,trigAddress
			, trigAddressString)

	def GetFirstSupportedOutputTriggerEvent(self, trigAddress=defaultNamedNotOptArg, eventPtr=pythoncom.Missing, trigEventString=pythoncom.Missing):
		'method GetFirstSupportedOutputTriggerEvent'
		return self._ApplyTypes_(135, 1, (24, 0), ((3, 1), (16387, 2), (16392, 2)), u'GetFirstSupportedOutputTriggerEvent', None,trigAddress
			, eventPtr, trigEventString)

	def GetFirstSupportedOutputTriggerSignalType(self, trigAddress=defaultNamedNotOptArg, event=defaultNamedNotOptArg, trigSigType=pythoncom.Missing, trigSigTypeString=pythoncom.Missing):
		'method GetFirstSupportedOutputTriggerSignalType'
		return self._ApplyTypes_(137, 1, (24, 0), ((3, 1), (3, 1), (16387, 2), (16392, 2)), u'GetFirstSupportedOutputTriggerSignalType', None,trigAddress
			, event, trigSigType, trigSigTypeString)

	def GetFirstSupportedUnits(self, unitsType=defaultNamedNotOptArg, pVal=pythoncom.Missing, pStrVal=pythoncom.Missing):
		'method GetFirstSupportedUnits'
		return self._ApplyTypes_(108, 1, (24, 0), ((3, 1), (16387, 2), (16396, 18)), u'GetFirstSupportedUnits', None,unitsType
			, pVal, pStrVal)

	def GetFixedPosition(self):
		'method GetFixedPosition'
		return self._oleobj_.InvokeTypes(632, LCID, 1, (5, 0), (),)

	def GetGratingMotorSpeeds(self, pFrequencyMin=pythoncom.Missing, pFrequencyMax=pythoncom.Missing, pRampTime=pythoncom.Missing):
		'method GetGratingMotorSpeeds'
		return self._ApplyTypes_(620, 1, (24, 0), ((16389, 2), (16389, 2), (16389, 2)), u'GetGratingMotorSpeeds', None,pFrequencyMin
			, pFrequencyMax, pRampTime)

	def GetNextControllerOperation(self, token=pythoncom.Missing, Description=pythoncom.Missing, currentValue=pythoncom.Missing):
		'method GetNextControllerOperation'
		return self._ApplyTypes_(115, 1, (24, 0), ((16387, 2), (16392, 2), (16389, 2)), u'GetNextControllerOperation', None,token
			, Description, currentValue)

	def GetNextOperatingMode(self, modeName=pythoncom.Missing):
		'method GetNextOperatingMode'
		return self._ApplyTypes_(120, 1, (3, 0), ((16392, 2),), u'GetNextOperatingMode', None,modeName
			)

	def GetNextSupportedInputTriggerAddress(self, trigAddress=pythoncom.Missing, trigAddressString=pythoncom.Missing):
		'method GetNextSupportedInputTriggerAddress'
		return self._ApplyTypes_(125, 1, (24, 0), ((16387, 2), (16392, 2)), u'GetNextSupportedInputTriggerAddress', None,trigAddress
			, trigAddressString)

	def GetNextSupportedInputTriggerEvent(self, trigAddress=defaultNamedNotOptArg, eventPtr=pythoncom.Missing, trigEventString=pythoncom.Missing):
		'method GetNextSupportedInputTriggerEvent'
		return self._ApplyTypes_(127, 1, (24, 0), ((3, 1), (16387, 2), (16392, 2)), u'GetNextSupportedInputTriggerEvent', None,trigAddress
			, eventPtr, trigEventString)

	def GetNextSupportedInputTriggerSignalType(self, trigAddress=defaultNamedNotOptArg, event=defaultNamedNotOptArg, trigSigType=pythoncom.Missing, trigSigTypeString=pythoncom.Missing):
		'method GetNextSupportedInputTriggerSignalType'
		return self._ApplyTypes_(129, 1, (24, 0), ((3, 1), (3, 1), (16387, 2), (16392, 2)), u'GetNextSupportedInputTriggerSignalType', None,trigAddress
			, event, trigSigType, trigSigTypeString)

	def GetNextSupportedOutputTriggerAddress(self, trigAddress=pythoncom.Missing, trigAddressString=pythoncom.Missing):
		'method GetNextSupportedOutputTriggerAddress'
		return self._ApplyTypes_(134, 1, (24, 0), ((16387, 2), (16392, 2)), u'GetNextSupportedOutputTriggerAddress', None,trigAddress
			, trigAddressString)

	def GetNextSupportedOutputTriggerEvent(self, trigAddress=defaultNamedNotOptArg, eventPtr=pythoncom.Missing, trigEventString=pythoncom.Missing):
		'method GetNextSupportedOutputTriggerEvent'
		return self._ApplyTypes_(136, 1, (24, 0), ((3, 1), (16387, 2), (16392, 2)), u'GetNextSupportedOutputTriggerEvent', None,trigAddress
			, eventPtr, trigEventString)

	def GetNextSupportedOutputTriggerSignalType(self, trigAddress=defaultNamedNotOptArg, event=defaultNamedNotOptArg, trigSigType=pythoncom.Missing, trigSigTypeString=pythoncom.Missing):
		'method GetNextSupportedOutputTriggerSignalType'
		return self._ApplyTypes_(138, 1, (24, 0), ((3, 1), (3, 1), (16387, 2), (16392, 2)), u'GetNextSupportedOutputTriggerSignalType', None,trigAddress
			, event, trigSigType, trigSigTypeString)

	def GetNextSupportedUnits(self, unitsType=defaultNamedNotOptArg, pVal=pythoncom.Missing, pStrVal=pythoncom.Missing):
		'method GetNextSupportedUnits'
		return self._ApplyTypes_(109, 1, (24, 0), ((3, 1), (16387, 2), (16396, 18)), u'GetNextSupportedUnits', None,unitsType
			, pVal, pStrVal)

	def GetOperatingModeValue(self, whichOpMode=defaultNamedNotOptArg):
		'method GetOperatingMode'
		return self._ApplyTypes_(121, 1, (12, 0), ((3, 1),), u'GetOperatingModeValue', None,whichOpMode
			)

	def Initialize(self, forceInit=defaultNamedOptArg, emulate=defaultNamedOptArg, nonThreaded=defaultNamedOptArg):
		'method Initialize'
		return self._oleobj_.InvokeTypes(12, LCID, 1, (24, 0), ((12, 17), (12, 17), (12, 17)),forceInit
			, emulate, nonThreaded)

	def IsBusy(self):
		'method IsBusy'
		return self._oleobj_.InvokeTypes(611, LCID, 1, (11, 0), (),)

	def IsControllerOperationSupported(self, whichOperation=defaultNamedNotOptArg):
		'method IsControllerOperationSupported'
		return self._oleobj_.InvokeTypes(118, LCID, 1, (11, 0), ((3, 1),),whichOperation
			)

	def IsFixedPosition(self):
		'method IsFixedPosition'
		return self._oleobj_.InvokeTypes(631, LCID, 1, (11, 0), (),)

	def IsInputTriggerEnabled(self, trigAddress=defaultNamedNotOptArg, event=defaultNamedNotOptArg, sigType=defaultNamedNotOptArg):
		'method IsInputTriggerEnabled'
		return self._oleobj_.InvokeTypes(144, LCID, 1, (11, 0), ((3, 1), (3, 1), (3, 1)),trigAddress
			, event, sigType)

	def IsInputTriggerSupported(self, trigAddress=defaultNamedNotOptArg, event=defaultNamedNotOptArg, sigType=defaultNamedNotOptArg):
		'method IsInputTriggerSupported'
		return self._oleobj_.InvokeTypes(142, LCID, 1, (11, 0), ((3, 1), (3, 1), (3, 1)),trigAddress
			, event, sigType)

	def IsOperatingModeSupported(self, opModeToCheck=defaultNamedNotOptArg):
		'method IsOperatingModeSupported'
		return self._oleobj_.InvokeTypes(123, LCID, 1, (11, 0), ((3, 1),),opModeToCheck
			)

	def IsOutputTriggerEnabled(self, trigAddress=defaultNamedNotOptArg, event=defaultNamedNotOptArg, sigType=defaultNamedNotOptArg):
		'method IsOutputTriggerEnabled'
		return self._oleobj_.InvokeTypes(145, LCID, 1, (11, 0), ((3, 1), (3, 1), (3, 1)),trigAddress
			, event, sigType)

	def IsOutputTriggerSupported(self, trigAddress=defaultNamedNotOptArg, event=defaultNamedNotOptArg, sigType=defaultNamedNotOptArg):
		'method IsOutputTriggerSupported'
		return self._oleobj_.InvokeTypes(143, LCID, 1, (11, 0), ((3, 1), (3, 1), (3, 1)),trigAddress
			, event, sigType)

	def IsReady(self):
		'method IsReady'
		return self._oleobj_.InvokeTypes(622, LCID, 1, (11, 0), (),)

	def IsSubItemInstalled(self, type=defaultNamedNotOptArg):
		'method IsSubItemInstalled'
		return self._oleobj_.InvokeTypes(624, LCID, 1, (11, 0), ((3, 1),),type
			)

	def IsTargetWithinLimits(self, what=defaultNamedNotOptArg, where=defaultNamedNotOptArg, withinLimits=pythoncom.Missing, minForCurrentGrating=pythoncom.Missing
			, maxForCurrentGrating=pythoncom.Missing, whichSlit=defaultNamedOptArg):
		'method IsTargetWithinLimits'
		return self._ApplyTypes_(628, 1, (24, 0), ((3, 1), (5, 1), (16396, 2), (16389, 2), (16389, 2), (12, 17)), u'IsTargetWithinLimits', None,what
			, where, withinLimits, minForCurrentGrating, maxForCurrentGrating, whichSlit
			)

	def Load(self):
		'Method Load'
		return self._oleobj_.InvokeTypes(1, LCID, 1, (24, 0), (),)

	def MovetoGrating(self, GratingDensity=defaultNamedNotOptArg):
		'method MovetoGrating'
		return self._oleobj_.InvokeTypes(601, LCID, 1, (24, 0), ((5, 1),),GratingDensity
			)

	def MovetoMirrorPosition(self, MirrorNumber=defaultNamedNotOptArg, NewMirrorPosition=defaultNamedNotOptArg):
		'method MovetoMirrorPosition'
		return self._oleobj_.InvokeTypes(612, LCID, 1, (24, 0), ((3, 1), (3, 1)),MirrorNumber
			, NewMirrorPosition)

	def MovetoSlitWidth(self, sl=defaultNamedNotOptArg, newWidth=defaultNamedNotOptArg):
		'method MovetoSlitWidth'
		return self._oleobj_.InvokeTypes(606, LCID, 1, (24, 0), ((3, 1), (5, 1)),sl
			, newWidth)

	def MovetoTurret(self, turretNumberZeroBased=defaultNamedNotOptArg):
		'method MovetoTurret'
		return self._oleobj_.InvokeTypes(626, LCID, 1, (24, 0), ((3, 1),),turretNumberZeroBased
			)

	def MovetoWavelength(self, newWavelength=defaultNamedNotOptArg):
		'method MovetoWavelength'
		return self._oleobj_.InvokeTypes(603, LCID, 1, (24, 0), ((5, 1),),newWavelength
			)

	def OpenCommunications(self):
		'Method OpenCommunications'
		return self._oleobj_.InvokeTypes(4, LCID, 1, (24, 0), (),)

	def OpenCommunicationsEx(self, _MIDL_0016_=defaultNamedNotOptArg, portNum=defaultNamedNotOptArg, devName=defaultNamedOptArg, bRate=defaultNamedOptArg
			, databits=defaultNamedOptArg, parityBits=defaultNamedOptArg, jy_pid_comm_stopbits=defaultNamedOptArg):
		'Method OpenCommunicationsEx'
		return self._oleobj_.InvokeTypes(3, LCID, 1, (24, 0), ((3, 1), (3, 1), (12, 17), (12, 17), (12, 17), (12, 17), (12, 17)),_MIDL_0016_
			, portNum, devName, bRate, databits, parityBits
			, jy_pid_comm_stopbits)

	def OpenShutter(self):
		'method OpenShutter'
		return self._oleobj_.InvokeTypes(614, LCID, 1, (24, 0), (),)

	def ReadCommSetting(self, _MIDL_0017_=defaultNamedNotOptArg):
		'method ReadCommSetting'
		return self._ApplyTypes_(19, 1, (12, 0), ((3, 1),), u'ReadCommSetting', None,_MIDL_0017_
			)

	def ReadI2C(self, i2cAddr=defaultNamedNotOptArg, length=defaultNamedNotOptArg, rxData=pythoncom.Missing):
		'method ReadI2C'
		return self._ApplyTypes_(23, 1, (24, 0), ((3, 1), (3, 1), (16396, 2)), u'ReadI2C', None,i2cAddr
			, length, rxData)

	def ReadString(self, charCount=defaultNamedNotOptArg):
		'method ReadString'
		return self._ApplyTypes_(6, 1, (8, 0), ((16387, 3),), u'ReadString', None,charCount
			)

	def RebootDevice(self):
		'method RebootDevice'
		return self._oleobj_.InvokeTypes(152, LCID, 1, (24, 0), (),)

	def Save(self):
		'Method Save'
		return self._oleobj_.InvokeTypes(2, LCID, 1, (24, 0), (),)

	def SendString(self, stringToSend=defaultNamedNotOptArg, countToSend=defaultNamedOptArg):
		'method SendString'
		return self._oleobj_.InvokeTypes(5, LCID, 1, (24, 0), ((8, 1), (12, 17)),stringToSend
			, countToSend)

	def SetControllerOperationValue(self, token=defaultNamedNotOptArg, newValue=defaultNamedNotOptArg):
		'method SetControllerOperationValue'
		return self._oleobj_.InvokeTypes(116, LCID, 1, (24, 0), ((3, 1), (5, 1)),token
			, newValue)

	def SetDefaultUnits(self, type=defaultNamedNotOptArg, newVal=defaultNamedNotOptArg):
		'method SetDefaultUnits'
		return self._oleobj_.InvokeTypes(111, LCID, 1, (24, 0), ((3, 1), (3, 1)),type
			, newVal)

	def SetDeviceAddress(self, newAddress=defaultNamedNotOptArg):
		'method SetDeviceAddress'
		return self._oleobj_.InvokeTypes(150, LCID, 1, (24, 0), ((12, 1),),newAddress
			)

	def SetDeviceConfigProperty(self, property=defaultNamedNotOptArg, newVal=defaultNamedNotOptArg, newVal2=defaultNamedOptArg, newVal3=defaultNamedOptArg
			, newVal4=defaultNamedOptArg):
		'method SetDeviceConfigProperty'
		return self._oleobj_.InvokeTypes(149, LCID, 1, (24, 0), ((3, 1), (12, 1), (12, 17), (12, 17), (12, 17)),property
			, newVal, newVal2, newVal3, newVal4)

	def SetGratingMotorSpeeds(self, FrequencyMin=defaultNamedNotOptArg, FrequencyMax=defaultNamedNotOptArg, RampTime=defaultNamedNotOptArg):
		'method SetGratingMotorSpeeds'
		return self._oleobj_.InvokeTypes(621, LCID, 1, (24, 0), ((5, 1), (5, 1), (5, 1)),FrequencyMin
			, FrequencyMax, RampTime)

	def SetJYLoggerProperties(self, newLevel=defaultNamedNotOptArg, newFileName=defaultNamedNotOptArg, newFilePath=defaultNamedNotOptArg, newMaxBackupFiles=defaultNamedNotOptArg
			, newMaxFileSize=defaultNamedNotOptArg):
		'method SetJYLoggerProperties'
		return self._oleobj_.InvokeTypes(623, LCID, 1, (24, 0), ((3, 1), (8, 17), (8, 17), (3, 17), (3, 17)),newLevel
			, newFileName, newFilePath, newMaxBackupFiles, newMaxFileSize)

	def SetMonoToManual(self, fEnabled=defaultNamedNotOptArg):
		'method SetMonoToManual'
		return self._oleobj_.InvokeTypes(630, LCID, 1, (24, 0), ((11, 1),),fEnabled
			)

	def SetOperatingModeValue(self, whichOpMode=defaultNamedNotOptArg, newOpModeVal=defaultNamedNotOptArg):
		'method SetOperatingMode'
		return self._oleobj_.InvokeTypes(122, LCID, 1, (24, 0), ((3, 1), (12, 1)),whichOpMode
			, newOpModeVal)

	def SetShutterToAuto(self):
		'method SetShutterToAuto'
		return self._oleobj_.InvokeTypes(629, LCID, 1, (24, 0), (),)

	# The method SetSlitMotorSpeed is actually a property, but must be used as a method to correctly pass the arguments
	def SetSlitMotorSpeed(self, sl=defaultNamedNotOptArg, arg1=defaultUnnamedArg):
		'property'
		return self._oleobj_.InvokeTypes(619, LCID, 4, (24, 0), ((3, 1), (5, 1)),sl
			, arg1)

	def Setup(self):
		'method Setup'
		return self._oleobj_.InvokeTypes(101, LCID, 1, (24, 0), (),)

	def Shutdown(self, msToWait=defaultNamedNotOptArg):
		'method Shutdown'
		return self._oleobj_.InvokeTypes(146, LCID, 1, (24, 0), ((3, 17),),msToWait
			)

	# The method SlitMotorSpeed is actually a property, but must be used as a method to correctly pass the arguments
	def SlitMotorSpeed(self, sl=defaultNamedNotOptArg):
		'property'
		return self._oleobj_.InvokeTypes(619, LCID, 2, (5, 0), ((3, 1),),sl
			)

	def SoftwareAssertHardwareTrigger(self):
		'method SoftwareAssertHardwareTrigger'
		return self._oleobj_.InvokeTypes(155, LCID, 1, (24, 0), (),)

	def Stop(self):
		'method Stop'
		return self._oleobj_.InvokeTypes(617, LCID, 1, (24, 0), (),)

	def TalkUSB(self, request=defaultNamedNotOptArg, index=defaultNamedNotOptArg, value=defaultNamedNotOptArg, length=defaultNamedNotOptArg
			, direction=defaultNamedNotOptArg, data=defaultNamedNotOptArg):
		'method TalkUSB'
		return self._ApplyTypes_(154, 1, (24, 0), ((3, 1), (3, 1), (3, 1), (3, 1), (3, 1), (16396, 3)), u'TalkUSB', None,request
			, index, value, length, direction, data
			)

	def Uninitialize(self):
		'method Uninitialize'
		return self._oleobj_.InvokeTypes(14, LCID, 1, (24, 0), (),)

	def UpdateCommSetting(self, _MIDL_0018_=defaultNamedNotOptArg, newVal=defaultNamedNotOptArg):
		'method UpdateCommSetting'
		return self._oleobj_.InvokeTypes(20, LCID, 1, (24, 0), ((3, 1), (12, 1)),_MIDL_0018_
			, newVal)

	def ValidateHW(self):
		'method ValidateHW'
		return self._oleobj_.InvokeTypes(25, LCID, 1, (24, 0), (),)

	def WriteI2C(self, i2cAddr=defaultNamedNotOptArg, length=defaultNamedNotOptArg, txData=defaultNamedNotOptArg):
		'method WriteI2C'
		return self._oleobj_.InvokeTypes(22, LCID, 1, (24, 0), ((3, 1), (3, 1), (12, 1)),i2cAddr
			, length, txData)

	_prop_map_get_ = {
		"AxialDetectorId": (635, 2, (8, 0), (), "AxialDetectorId", None),
		"BacklashEnabled": (633, 2, (11, 0), (), "BacklashEnabled", None),
		"ControllerChannelIndex": (113, 2, (12, 0), (), "ControllerChannelIndex", None),
		"Description": (147, 2, (8, 0), (), "Description", None),
		"DeviceClass": (104, 2, (3, 0), (), "DeviceClass", None),
		"DeviceType": (105, 2, (3, 0), (), "DeviceType", None),
		"Emulating": (9, 2, (11, 0), (), "Emulating", None),
		"ErrDisplayMode": (15, 2, (3, 0), (), "ErrDisplayMode", None),
		"FirmwareVersion": (8, 2, (8, 0), (), "FirmwareVersion", None),
		"InitializeComplete": (24, 2, (11, 0), (), "InitializeComplete", None),
		"LastError": (13, 2, (3, 0), (), "LastError", None),
		"LateralDetectorId": (634, 2, (8, 0), (), "LateralDetectorId", None),
		"Name": (10, 2, (8, 0), (), "Name", None),
		"PassThruSendTerminationCharacter": (7, 2, (8, 0), (), "PassThruSendTerminationCharacter", None),
		"SerialNumber": (26, 2, (8, 0), (), "SerialNumber", None),
		"SupportFilesPath": (18, 2, (8, 0), (), "SupportFilesPath", None),
		"Uniqueid": (103, 2, (8, 0), (), "Uniqueid", None),
	}
	_prop_map_put_ = {
		"AxialDetectorId": ((635, LCID, 4, 0),()),
		"BacklashEnabled": ((633, LCID, 4, 0),()),
		"ControllerChannelIndex": ((113, LCID, 4, 0),()),
		"Description": ((147, LCID, 4, 0),()),
		"ErrDisplayMode": ((15, LCID, 4, 0),()),
		"LateralDetectorId": ((634, LCID, 4, 0),()),
		"Name": ((10, LCID, 4, 0),()),
		"PassThruSendTerminationCharacter": ((7, LCID, 4, 0),()),
		"SupportFilesPath": ((18, LCID, 4, 0),()),
		"Uniqueid": ((103, LCID, 4, 0),()),
	}
	def __iter__(self):
		"Return a Python iterator for this object"
		try:
			ob = self._oleobj_.InvokeTypes(-4,LCID,3,(13, 10),())
		except pythoncom.error:
			raise TypeError("This object does not support enumeration")
		return win32com.client.util.Iterator(ob, None)

class _IJYDeviceReqdEvents:
	'_IJYDeviceReqdEvents Interface'
	CLSID = CLSID_Sink = IID('{A2C81A78-CA13-4A39-8FCB-CD51BD4E9376}')
	coclass_clsid = IID('{BFF968D4-7B20-4D16-BD3A-BDEFEB0863A4}')
	_public_methods_ = [] # For COM Server support
	_dispid_to_func_ = {
		        1 : "OnInitialize",
		        4 : "OnCriticalError",
		        3 : "OnUpdate",
		        2 : "OnOperationStatus",
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
#	def OnInitialize(self, status=defaultNamedNotOptArg, eventInfo=defaultNamedNotOptArg):
#		'method Initialize'
#	def OnCriticalError(self, status=defaultNamedNotOptArg, eventInfo=defaultNamedNotOptArg):
#		'method CriticalError'
#	def OnUpdate(self, updateType=defaultNamedNotOptArg, eventInfo=defaultNamedNotOptArg):
#		'method Update'
#	def OnOperationStatus(self, status=defaultNamedNotOptArg, eventInfo=defaultNamedNotOptArg):
#		'method OperationStatus'


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
  
# This CoClass is known by the name 'JYMono.Monochromator.1'
class Monochromator(CoClassBaseClass): # A CoClass
	# Monochromator Class
	CLSID = IID('{BFF968D4-7B20-4D16-BD3A-BDEFEB0863A4}')
	coclass_sources = [
		_IJYDeviceReqdEvents,
	]
	default_source = _IJYDeviceReqdEvents
	coclass_interfaces = [
		IJYMonoReqd,
	]
	default_interface = IJYMonoReqd

IJYMonoReqd_vtables_dispatch_ = 1
IJYMonoReqd_vtables_ = [
	(( u'MovetoGrating' , u'GratingDensity' , ), 601, (601, (), [ (5, 1, None, None) , ], 1 , 1 , 4 , 0 , 368 , (3, 0, None, None) , 0 , )),
	(( u'GetCurrentGrating' , u'pGratingDensity' , u'pGratings' , ), 602, (602, (), [ (16389, 2, None, None) , 
			(16396, 2, None, None) , ], 1 , 1 , 4 , 0 , 372 , (3, 0, None, None) , 0 , )),
	(( u'MovetoWavelength' , u'newWavelength' , ), 603, (603, (), [ (5, 1, None, None) , ], 1 , 1 , 4 , 0 , 376 , (3, 0, None, None) , 0 , )),
	(( u'GetCurrentWavelength' , u'pWavelength' , ), 604, (604, (), [ (16389, 10, None, None) , ], 1 , 1 , 4 , 0 , 380 , (3, 0, None, None) , 0 , )),
	(( u'Calibrate' , u'actualWavelength' , ), 605, (605, (), [ (5, 1, None, None) , ], 1 , 1 , 4 , 0 , 384 , (3, 0, None, None) , 0 , )),
	(( u'MovetoSlitWidth' , u'sl' , u'newWidth' , ), 606, (606, (), [ (3, 1, None, None) , 
			(5, 1, None, None) , ], 1 , 1 , 4 , 0 , 388 , (3, 0, None, None) , 0 , )),
	(( u'GetCurrentSlitWidth' , u'sl' , u'pVal' , ), 607, (607, (), [ (3, 1, None, None) , 
			(16389, 10, None, None) , ], 1 , 1 , 4 , 0 , 392 , (3, 0, None, None) , 0 , )),
	(( u'CalibrateSlitWidth' , u'slitNumber' , ), 608, (608, (), [ (3, 1, None, None) , ], 1 , 1 , 4 , 0 , 396 , (3, 0, None, None) , 0 , )),
	(( u'IsBusy' , u'BusyStatus' , ), 611, (611, (), [ (16395, 10, None, None) , ], 1 , 1 , 4 , 0 , 400 , (3, 0, None, None) , 0 , )),
	(( u'MovetoMirrorPosition' , u'MirrorNumber' , u'NewMirrorPosition' , ), 612, (612, (), [ (3, 1, None, None) , 
			(3, 1, None, None) , ], 1 , 1 , 4 , 0 , 404 , (3, 0, None, None) , 0 , )),
	(( u'GetCurrentMirrorPosition' , u'MirrorNumber' , u'pMirrorPostion' , ), 613, (613, (), [ (3, 1, None, None) , 
			(16387, 10, None, None) , ], 1 , 1 , 4 , 0 , 408 , (3, 0, None, None) , 0 , )),
	(( u'OpenShutter' , ), 614, (614, (), [ ], 1 , 1 , 4 , 0 , 412 , (3, 0, None, None) , 0 , )),
	(( u'CloseShutter' , ), 615, (615, (), [ ], 1 , 1 , 4 , 0 , 416 , (3, 0, None, None) , 0 , )),
	(( u'GetCurrentShutterPosition' , u'pShutterPosition' , ), 616, (616, (), [ (16387, 10, None, None) , ], 1 , 1 , 4 , 0 , 420 , (3, 0, None, None) , 0 , )),
	(( u'Stop' , ), 617, (617, (), [ ], 1 , 1 , 4 , 0 , 424 , (3, 0, None, None) , 0 , )),
	(( u'SlitMotorSpeed' , u'sl' , u'pFrequency' , ), 619, (619, (), [ (3, 1, None, None) , 
			(16389, 10, None, None) , ], 1 , 2 , 4 , 0 , 428 , (3, 0, None, None) , 0 , )),
	(( u'SlitMotorSpeed' , u'sl' , u'pFrequency' , ), 619, (619, (), [ (3, 1, None, None) , 
			(5, 1, None, None) , ], 1 , 4 , 4 , 0 , 432 , (3, 0, None, None) , 0 , )),
	(( u'GetGratingMotorSpeeds' , u'pFrequencyMin' , u'pFrequencyMax' , u'pRampTime' , ), 620, (620, (), [ 
			(16389, 2, None, None) , (16389, 2, None, None) , (16389, 2, None, None) , ], 1 , 1 , 4 , 0 , 436 , (3, 0, None, None) , 0 , )),
	(( u'SetGratingMotorSpeeds' , u'FrequencyMin' , u'FrequencyMax' , u'RampTime' , ), 621, (621, (), [ 
			(5, 1, None, None) , (5, 1, None, None) , (5, 1, None, None) , ], 1 , 1 , 4 , 0 , 440 , (3, 0, None, None) , 0 , )),
	(( u'IsReady' , u'BusyStatus' , ), 622, (622, (), [ (16395, 10, None, None) , ], 1 , 1 , 4 , 0 , 444 , (3, 0, None, None) , 0 , )),
	(( u'SetJYLoggerProperties' , u'newLevel' , u'newFileName' , u'newFilePath' , u'newMaxBackupFiles' , 
			u'newMaxFileSize' , ), 623, (623, (), [ (3, 1, None, None) , (8, 17, None, None) , (8, 17, None, None) , 
			(3, 17, None, None) , (3, 17, None, None) , ], 1 , 1 , 4 , 0 , 448 , (3, 0, None, None) , 0 , )),
	(( u'IsSubItemInstalled' , u'type' , u'installed' , ), 624, (624, (), [ (3, 1, None, None) , 
			(16395, 10, None, None) , ], 1 , 1 , 4 , 0 , 452 , (3, 0, None, None) , 0 , )),
	(( u'GetCurrentGratingWithDetails' , u'pGratingDensity' , u'pGratings' , u'pBlaze' , u'pDescription' , 
			), 625, (625, (), [ (16389, 2, None, None) , (16396, 2, None, None) , (16396, 2, None, None) , (16396, 2, None, None) , ], 1 , 1 , 4 , 0 , 456 , (3, 0, None, None) , 0 , )),
	(( u'MovetoTurret' , u'turretNumberZeroBased' , ), 626, (626, (), [ (3, 1, None, None) , ], 1 , 1 , 4 , 0 , 460 , (3, 0, None, None) , 0 , )),
	(( u'GetCurrentTurret' , u'turretNumberZeroBased' , ), 627, (627, (), [ (16387, 10, None, None) , ], 1 , 1 , 4 , 0 , 464 , (3, 0, None, None) , 0 , )),
	(( u'IsTargetWithinLimits' , u'what' , u'where' , u'withinLimits' , u'minForCurrentGrating' , 
			u'maxForCurrentGrating' , u'whichSlit' , ), 628, (628, (), [ (3, 1, None, None) , (5, 1, None, None) , 
			(16396, 2, None, None) , (16389, 2, None, None) , (16389, 2, None, None) , (12, 17, None, None) , ], 1 , 1 , 4 , 1 , 468 , (3, 0, None, None) , 0 , )),
	(( u'SetShutterToAuto' , ), 629, (629, (), [ ], 1 , 1 , 4 , 0 , 472 , (3, 0, None, None) , 0 , )),
	(( u'SetMonoToManual' , u'fEnabled' , ), 630, (630, (), [ (11, 1, None, None) , ], 1 , 1 , 4 , 0 , 476 , (3, 0, None, None) , 0 , )),
	(( u'IsFixedPosition' , u'isMonoFixed' , ), 631, (631, (), [ (16395, 10, None, None) , ], 1 , 1 , 4 , 0 , 480 , (3, 0, None, None) , 0 , )),
	(( u'GetFixedPosition' , u'fixedWavelength' , ), 632, (632, (), [ (16389, 10, None, None) , ], 1 , 1 , 4 , 0 , 484 , (3, 0, None, None) , 0 , )),
	(( u'BacklashEnabled' , u'enabled' , ), 633, (633, (), [ (11, 1, None, None) , ], 1 , 4 , 4 , 0 , 488 , (3, 0, None, None) , 0 , )),
	(( u'BacklashEnabled' , u'enabled' , ), 633, (633, (), [ (16395, 10, None, None) , ], 1 , 2 , 4 , 0 , 492 , (3, 0, None, None) , 0 , )),
	(( u'LateralDetectorId' , u'detectorID' , ), 634, (634, (), [ (8, 1, None, None) , ], 1 , 4 , 4 , 0 , 496 , (3, 0, None, None) , 0 , )),
	(( u'LateralDetectorId' , u'detectorID' , ), 634, (634, (), [ (16392, 10, None, None) , ], 1 , 2 , 4 , 0 , 500 , (3, 0, None, None) , 0 , )),
	(( u'AxialDetectorId' , u'detectorID' , ), 635, (635, (), [ (8, 1, None, None) , ], 1 , 4 , 4 , 0 , 504 , (3, 0, None, None) , 0 , )),
	(( u'AxialDetectorId' , u'detectorID' , ), 635, (635, (), [ (16392, 10, None, None) , ], 1 , 2 , 4 , 0 , 508 , (3, 0, None, None) , 0 , )),
]

RecordMap = {
}

CLSIDToClassMap = {
	'{A2C81A78-CA13-4A39-8FCB-CD51BD4E9376}' : _IJYDeviceReqdEvents,
	'{BFF968D4-7B20-4D16-BD3A-BDEFEB0863A4}' : Monochromator,
	'{7963F672-D074-4F67-B15C-AF022065927E}' : IJYMonoReqd,
}
CLSIDToPackageMap = {}
win32com.client.CLSIDToClass.RegisterCLSIDsFromDict( CLSIDToClassMap )
VTablesToPackageMap = {}
VTablesToClassMap = {
	'{7963F672-D074-4F67-B15C-AF022065927E}' : 'IJYMonoReqd',
}


NamesToIIDMap = {
	'IJYMonoReqd' : '{7963F672-D074-4F67-B15C-AF022065927E}',
	'_IJYDeviceReqdEvents' : '{A2C81A78-CA13-4A39-8FCB-CD51BD4E9376}',
}