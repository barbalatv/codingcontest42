import ctypes
from ctypes import wintypes
HANDLES=[]
def limit_current_process(mb=1024):
    class Basic(ctypes.Structure):
        _fields_=[('ProcessTime',ctypes.c_longlong),('JobTime',ctypes.c_longlong),('Flags',wintypes.DWORD),('MinWorking',ctypes.c_size_t),('MaxWorking',ctypes.c_size_t),('Active',wintypes.DWORD),('Affinity',ctypes.c_size_t),('Priority',wintypes.DWORD),('Scheduling',wintypes.DWORD)]
    class IO(ctypes.Structure):_fields_=[(str(i),ctypes.c_ulonglong) for i in range(6)]
    class Extended(ctypes.Structure):_fields_=[('Basic',Basic),('IO',IO),('ProcessMemory',ctypes.c_size_t),('JobMemory',ctypes.c_size_t),('PeakProcess',ctypes.c_size_t),('PeakJob',ctypes.c_size_t)]
    k=ctypes.WinDLL('kernel32',use_last_error=True);k.CreateJobObjectW.restype=wintypes.HANDLE;k.CreateJobObjectW.argtypes=[ctypes.c_void_p,wintypes.LPCWSTR];k.SetInformationJobObject.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD];k.AssignProcessToJobObject.argtypes=[wintypes.HANDLE,wintypes.HANDLE];k.GetCurrentProcess.restype=wintypes.HANDLE
    job=k.CreateJobObjectW(None,None);info=Extended();info.Basic.Flags=0x100;info.ProcessMemory=mb*1024*1024
    applied=bool(job and k.SetInformationJobObject(job,9,ctypes.byref(info),ctypes.sizeof(info)) and k.AssignProcessToJobObject(job,k.GetCurrentProcess()))
    HANDLES.append(job)
    return dict(applied=applied,process_memory_mb=mb,error=0 if applied else ctypes.get_last_error(),child_inheritance=True)
