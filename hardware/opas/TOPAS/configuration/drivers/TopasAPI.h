// TopasAPI.h
// Header file for TopasAPI.dll- library 
// Contains declarations of macros and functions 


#ifdef __cplusplus
	extern "C" {
#endif

#define MAX_DEVICES_COUNT								5
#define MAX_NUMBER_OF_MOTORS							18

#define	WL_OUTPUT										0
#define	WL_OPA											1
#define WL_MIXER1										2
#define	WL_MIXER2										3
#define WL_MIXER3										4

#define	UNIT_OPA										0
#define	UNIT_MIXER1										1
#define	UNIT_MIXER2										2
#define	UNIT_MIXER3										3

#define	INTERACTION_NON									0
#define	INTERACTION_SGN									1
#define	INTERACTION_IDL									2
#define	INTERACTION_SH									3
#define	INTERACTION_SF									4
#define	INTERACTION_DFG									5
#define	INTERACTION_DFG1								6
#define	INTERACTION_DFG2								7
#define	INTERACTION_DFP									8
#define	INTERACTION_DFP1								9
#define	INTERACTION_DFP2								10
#define	INTERACTION_DFP3								11
#define	INTERACTION_DFP4								12
#define	INTERACTION_TH									13
#define	INTERACTION_DFM									14
#define INTERACTION_WS									15

#define	REFERENCE_SWITCH_OPENED							0
#define REFERENCE_SWITCH_CLOSED							1

#define	TOPASAPI_ERROR_OK										0
#define TOPASAPI_ERROR_UNKNOWN									1
#define	TOPASAPI_ERROR_NO_DEVICES_FOUND							2
#define	TOPASAPI_ERROR_INVALID_DEVICE_INSTANCE					3
#define	TOPASAPI_ERROR_INVALID_DEVICE_INDEX						4
#define	TOPASAPI_ERROR_BUFFER_TO_SMALL							5
#define TOPASAPI_ERROR_GET_SERIAL								6
#define	TOPASAPI_ERROR_DEVICE_ALREADY_OPENED					7
#define	TOPASAPI_ERROR_DEVICE_OPEN_FAILED						8
#define TOPASAPI_ERROR_USB_OPEN_FAILED							9
#define	TOPASAPI_ERROR_USB_READ_ERROR							10
#define TOPASAPI_ERROR_MOTOR_CONFIGURATION_FAILED_TO_LOAD		11
#define TOPASAPI_ERROR_CONFIGURATION_AND_FLASH_MISMATCH			12
#define TOPASAPI_ERROR_TRANSMIT_OF_PARAMETERS_FAILED			13
#define TOPASAPI_ERROR_SERIAL_NUMBER_NOT_FOUND					14
#define TOPASAPI_ERROR_INVALID_CARD_TYPE						15
#define TOPASAPI_ERROR_DEVICE_NOT_OPENED						16
#define TOPASAPI_ERROR_USB_COMMAND_FAILED						17
#define TOPASAPI_ERROR_WL_CAN_NOT_BE_SET						18
#define TOPASAPI_ERROR_INVALID_MOTOR_NUMBER						19
#define TOPASAPI_ERROR_LPT_CARD_NOT_SUPPORTED					20
#define TOPASAPI_ERROR_INVALID_WL_CODE							21
#define TOPASAPI_ERROR_INVALID_UNIT_CODE						22
#define TOPASAPI_ERROR_CURVE_CONFIGURATION_FAILED_TO_LOAD		23
#define TOPASAPI_ERROR_CURVE_READ_ERROR							24
#define TOPASAPI_ERROR_WRONG_CURVE_FILE_VERSION					25
#define TOPASAPI_ERROR_WRONG_CURVE_TYPE							26
#define TOPASAPI_ERROR_INVALID_MOTOR_COUNT						27
#define TOPASAPI_ERROR_INVALID_INTERACTIONS_COUNT				28
#define TOPASAPI_ERROR_OPA_TYPE_MISMATCH						29
#define TOPASAPI_ERROR_INVALID_WAVELENGTHS						30
#define TOPASAPI_ERROR_OPA_INVALID_GRATING_MOTOR				31
#define TOPASAPI_ERROR_CURVE_TYPE_MISMATCH						32
#define	TOPASAPI_ERROR_CONF_FILE_NOT_FOUND						33
#define TOPASAPI_ERROR_WL_CAN_NOT_BE_SET_WITH_COMBINATION		34

unsigned long	__stdcall	Topas_GetCountOfDevices(void);
unsigned long	__stdcall	Topas_GetDeviceSerialNumber(unsigned int instance, char* buffer, unsigned int size);
unsigned long	__stdcall	Topas_OpenDevice(unsigned char index, char* conf_path);
unsigned long	__stdcall	Topas_OpenShutter(unsigned char index, bool flag);
unsigned long	__stdcall	Topas_GetCountOfMotors(unsigned char index, unsigned char* count);
unsigned long	__stdcall	Topas_GetMotorPosition(unsigned char index, unsigned char motor, unsigned long* position);
unsigned long	__stdcall	Topas_IsMotorStill(unsigned char index, unsigned char motor, bool* result);
unsigned long	__stdcall	Topas_AreAllMotorsStill(unsigned char index, bool* result);
unsigned long	__stdcall	Topas_MoveMotor(unsigned char index, unsigned char motor, unsigned long new_position);
unsigned long	__stdcall	Topas_MoveMotorToPositionInUnits(unsigned char index, unsigned char motor, double new_position);
unsigned long	__stdcall	Topas_StartMotorMotion(unsigned char index, unsigned char motor, unsigned long new_position);
unsigned long	__stdcall	Topas_UpdateMotorsPositions(unsigned char index);
unsigned long	__stdcall	Topas_StopMotor(unsigned char index, unsigned char motor);
unsigned long	__stdcall	Topas_GetReferenceSwitchStatus(unsigned char index, unsigned char motor, unsigned char* left, unsigned char* right);
unsigned long	__stdcall	Topas_SetWavelength(unsigned char index, double wl);
unsigned long	__stdcall	Topas_SetWavelengthEx(unsigned char index, double wl, unsigned char interaction_opa, unsigned char interaction_mixer1, unsigned char interaction_mixer2, unsigned char interaction_mixer3);
unsigned long	__stdcall	Topas_StartSettingWavelength(unsigned char index, double wl);
unsigned long	__stdcall	Topas_StartSettingWavelengthEx(unsigned char index, double wl, unsigned char interaction_opa, unsigned char interaction_mixer1, unsigned char interaction_mixer2, unsigned char interaction_mixer3);
unsigned long	__stdcall	Topas_IsWavelengthSettingFinished(unsigned char index, bool* result);
unsigned long	__stdcall	Topas_GetWl(unsigned char index, unsigned char wl_code, double* wl);
unsigned long	__stdcall	Topas_GetInteraction(unsigned char index, unsigned char unit_code, unsigned char* interaction);
unsigned long	__stdcall	Topas_ConvertPositionToSteps(unsigned char index, unsigned char motor, double pos_in_units, unsigned long* pos_in_steps);
unsigned long	__stdcall	Topas_ConvertPositionToUnits(unsigned char index, unsigned char motor, unsigned int pos_in_steps, double* pos_in_units);

unsigned long	__stdcall	Topas_SetMotorOffset(unsigned char index, unsigned char unit_code, unsigned char interaction_index, unsigned char motor_index, double offset);
unsigned long	__stdcall	Topas_SetMotorAffix(unsigned char index, unsigned char motor, double affix);
unsigned long	__stdcall	Topas_GetMotorOffset(unsigned char index, unsigned char unit_code, unsigned char interaction_index, unsigned char motor_index, double* offset);
unsigned long	__stdcall	Topas_GetMotorAffix(unsigned char index, unsigned char motor, double* affix);

unsigned long	__stdcall	Topas_CloseDevice(unsigned char index);

unsigned long __stdcall TopasUSB_SetSpeedParams(unsigned char index, unsigned char motor, unsigned short v_min, unsigned short v_max, unsigned short a_max);
unsigned long __stdcall TopasUSB_GetSpeedParams(unsigned char index, unsigned char motor, unsigned short *v_min, unsigned short *v_max, unsigned short *a_max);
unsigned long __stdcall Topas_SetMotorPosition(unsigned char index, unsigned char motor, unsigned long position);
unsigned long __stdcall Topas_GetMotorPositionsRange(unsigned char index, unsigned char motor, unsigned long* min_position, unsigned long* max_position);
unsigned long __stdcall Topas_SetMotorPositionsRange(unsigned char index, unsigned char motor, unsigned long min_position, unsigned long max_position);

unsigned long __stdcall	 Topas_GetInfo(unsigned char index, unsigned char unit_code, char* str);

#ifdef __cplusplus
	}
#endif