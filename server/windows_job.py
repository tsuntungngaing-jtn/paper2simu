"""Owned Windows process trees; handles, never PID-name based termination."""
from contextlib import contextmanager
import subprocess
import ctypes as ct
from ctypes import wintypes as wt

import win32api
import win32con
import win32event
import win32file
import win32job
import win32process
import pywintypes

ATOMIC_JOB_ASSIGNMENT = True


@contextmanager
def lock_input(path):
    """Keep the reviewed snapshot readable while denying write and replacement."""
    handle = win32file.CreateFile(
        str(path), win32con.GENERIC_READ, win32con.FILE_SHARE_READ, None,
        win32con.OPEN_EXISTING, win32con.FILE_ATTRIBUTE_NORMAL, None,
    )
    try:
        yield
    finally:
        handle.Close()


def create_in_job(command, cwd, job):
    """Assign at CreateProcess time; no unowned suspended-process interval."""
    class SI(ct.Structure):
        _fields_ = [('cb',wt.DWORD),('reserved',wt.LPWSTR),('desktop',wt.LPWSTR),
                    ('title',wt.LPWSTR)] + [(n,wt.DWORD) for n in
                    ('x','y','xsize','ysize','xchars','ychars','fill','flags')] + [
                    ('show',wt.WORD),('reserved2size',wt.WORD),('reserved2',ct.c_void_p),
                    ('stdin',wt.HANDLE),('stdout',wt.HANDLE),('stderr',wt.HANDLE)]
    class SX(ct.Structure):
        _fields_=[('si',SI),('attrs',ct.c_void_p)]
    class PI(ct.Structure):
        _fields_=[('process',wt.HANDLE),('thread',wt.HANDLE),('pid',wt.DWORD),('tid',wt.DWORD)]
    kernel=ct.WinDLL('kernel32',use_last_error=True)
    init=kernel.InitializeProcThreadAttributeList
    init.argtypes=[ct.c_void_p,wt.DWORD,wt.DWORD,ct.POINTER(ct.c_size_t)]
    update=kernel.UpdateProcThreadAttribute
    update.argtypes=[ct.c_void_p,wt.DWORD,ct.c_size_t,ct.c_void_p,ct.c_size_t,ct.c_void_p,ct.c_void_p]
    delete=kernel.DeleteProcThreadAttributeList
    delete.argtypes=[ct.c_void_p]
    create=kernel.CreateProcessW
    create.argtypes=[wt.LPCWSTR,wt.LPWSTR,ct.c_void_p,ct.c_void_p,wt.BOOL,
                     wt.DWORD,ct.c_void_p,wt.LPCWSTR,ct.POINTER(SX),ct.POINTER(PI)]
    size=ct.c_size_t()
    init(None,1,0,ct.byref(size))
    attrs=ct.create_string_buffer(size.value)
    if not init(attrs,1,0,ct.byref(size)):raise ct.WinError(ct.get_last_error())
    try:
        handles=(wt.HANDLE*1)(int(job))
        if not update(attrs,0,0x0002000D,handles,ct.sizeof(handles),None,None):
            raise ct.WinError(ct.get_last_error())
        si=SX();si.si.cb=ct.sizeof(SX);si.attrs=ct.cast(attrs,ct.c_void_p)
        pi=PI()
        cmd=ct.create_unicode_buffer(subprocess.list2cmdline(command))
        if not create(command[0],cmd,None,None,False,
                      win32con.CREATE_SUSPENDED|subprocess.CREATE_NO_WINDOW|0x00080000,
                      None,str(cwd),ct.byref(si),ct.byref(pi)):
            raise ct.WinError(ct.get_last_error())
        return pi.process,pi.thread,pi.pid,pi.tid
    finally:
        delete(attrs)


def process_identity(pid):
    """Return the live process birth time, with absence distinct from probe error."""
    try:
        handle = win32api.OpenProcess(
            win32con.PROCESS_QUERY_INFORMATION | win32con.SYNCHRONIZE, False, pid,
        )
    except pywintypes.error as exc:
        if exc.winerror == 87:  # ERROR_INVALID_PARAMETER for a missing process
            return None
        raise OSError("Unable to open supervisor process") from exc
    try:
        if win32event.WaitForSingleObject(handle, 0) == win32event.WAIT_OBJECT_0:
            return None
        return win32process.GetProcessTimes(handle)["CreationTime"].timestamp()
    except pywintypes.error as exc:
        raise OSError("Unable to query supervisor process") from exc
    finally:
        handle.Close()


class OwnedJob:
    def __init__(self, command, cwd, *, before_create):
        self.job = win32job.CreateJobObject(None, None)
        self.process = self.thread = None
        try:
            info = win32job.QueryInformationJobObject(self.job, win32job.JobObjectExtendedLimitInformation)
            info['BasicLimitInformation']['LimitFlags'] = win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            win32job.SetInformationJobObject(self.job, win32job.JobObjectExtendedLimitInformation, info)
            before_create()
            self.process, self.thread, self.pid, _ = create_in_job(command, cwd, self.job)
            self.created_at = win32process.GetProcessTimes(self.process)['CreationTime'].timestamp()
        except BaseException:
            self.close()
            raise

    def resume(self):
        if win32process.ResumeThread(self.thread) != 1:
            raise RuntimeError("Unexpected native process suspend count")
        win32api.CloseHandle(self.thread)
        self.thread = None

    def active(self):
        return win32job.QueryInformationJobObject(self.job, win32job.JobObjectBasicAccountingInformation)['ActiveProcesses']

    def terminate(self):
        win32job.TerminateJobObject(self.job, 124)

    def exit_code(self):
        return win32process.GetExitCodeProcess(self.process)

    def close(self):
        # Job handle is non-inheritable; a supervisor crash closes its sole handle.
        first_error = None
        for name in ('job', 'thread', 'process'):
            handle = getattr(self, name, None)
            if handle is not None:
                try:
                    win32api.CloseHandle(handle)
                except Exception as exc:
                    if first_error is None:
                        first_error = exc
                else:
                    setattr(self, name, None)
        if first_error is not None:
            raise first_error
