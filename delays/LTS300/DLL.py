import ctypes 
serial_number = 45837036
hw_type = 42

dll_path = r'C:\Users\John\Documents\myscripts\PyAPT\APTDLLPack\DLL\x86\APT.dll'

dll = ctypes.WinDLL(dll_path)