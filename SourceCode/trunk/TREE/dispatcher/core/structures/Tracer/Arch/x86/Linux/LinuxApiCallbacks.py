# TREE - Taint-enabled Reverse Engineering Environment 
# Copyright (c) 2013 Battelle BIT Team - Nathan Li, Xing Li, Loc Nguyen
#
# All rights reserved.
#
# For detailed copyright information see the file license.txt in the IDA PRO plugins folder
#---------------------------------------------------------------------
# LinuxApiCallbacks.py - Linux API Tracking
#---------------------------------------------------------------------

import dispatcher.core.Util as Util
from dispatcher.core.DebugPrint import dbgPrint, Print

import idc
import logging
import os.path
import idaapi

class IO(object):
    def __init__(self):
        self.logger = None
        self.lpBuffer = None
        self.filter = None
        self.tempStack = []
        
    def SetLoggerInstance(self,logger):
        self.logger = logger
        
    def SetDebuggerInstance(self,dbgHook):
        self.debuggerInstance = dbgHook

    def SetFilters(self,_filter):
        self.filter = _filter
        
class FileIO(IO):
    
    def __init__(self):
        super(FileIO, self).__init__()
        self.handleSet = set()
        
    def My_freadEnd(self):

        numBytesRead = idc.GetRegValue("EAX")
        self.logger.info( "_fread read %d bytes." % (numBytesRead) )
        
        pBuffer = self.tempStack.pop(0)
        pSize = self.tempStack.pop(0)
        stream = self.tempStack.pop(0)
        callerAddr = self.tempStack.pop(0)
        callerFuncName = self.tempStack.pop(0)
        threadID = self.tempStack.pop(0)
        
        _buffer = idaapi.dbg_read_memory(pBuffer,pSize)
        self.logger.debug( _buffer)
        
        inputLoggingList = []
        
        inputLoggingList.append(pBuffer)
        inputLoggingList.append(pSize)
        inputLoggingList.append(_buffer)
        inputLoggingList.append(stream)
        inputLoggingList.append(callerAddr)
        inputLoggingList.append(callerFuncName)
        inputLoggingList.append(threadID)
        
        if numBytesRead > 0:
            self.logger.info( "_fread succeeded.")
            self.debuggerInstance.callbackProcessing(inputLoggingList)
        else:
            Print ("_fread failed." )
            self.logger.info( "_fread failed.")
        
        return 0
        
    def My_fread(self):
  
        """  
        old - size_t fread ( void * ptr, size_t size, size_t count, FILE * stream );
        
        size_t _IO_fread (void * ptr, size_t size, size_t count, FILE * stream )
        
        """
        
        ptr = Util.GetData(0x4)
        self.logger.info( "fp is 0x%x" % (ptr))

        _size = Util.GetData(0x8)
        self.logger.info( "size is %d" % (_size))
        
        _count = Util.GetData(0xc)
        self.logger.info( "count is %d" % (_count))
        
        stream = Util.GetData(0x10)
        self.logger.info( "stream is 0x%x" % (stream))
        
        self.pSize = _size * _count
        self.pBuffer = ptr

        retAddr = Util.GetData(0x0)
        
        callerAddr = retAddr-idc.ItemSize(retAddr)
        
        self.tempStack = []
        self.tempStack.append(self.pBuffer)
        self.tempStack.append(self.pSize)
        self.tempStack.append(stream)
        self.tempStack.append(callerAddr)

        self.tempStack.append("fread")
        self.tempStack.append(idc.GetCurrentThreadId())
         
        if stream in self.handleSet:
            self.logger.info( "Found stream 0x%x" % stream)
            
            idc.AddBpt(retAddr)
            idc.SetBptAttr(retAddr, idc.BPT_BRK, 0)
            idc.SetBptCnd(retAddr,"linuxFileIO.My_freadEnd()")
        else:
            self.logger.info( "Cannot find handle 0x%x" % stream)
            Print( "Removing un-needed fread breakpoint." )
            idc.DelBpt(retAddr)

        return 0
    
    def My_fopenEnd(self):
        """
        Not need to call this function here since fopen already contains the handle
        """
        stream = idc.GetRegValue("EAX")
        
        self.logger.info( "HANDLE is 0x%x" % stream)
        self.handleSet.add(stream)
    
        return 0
    
    def My_fopen(self):
        """
        old - FILE * fopen ( const char * filename, const char * mode );
        
        FILE * _IO_file_fopen (fp, filename, mode, is32not64)
        
        """

        fp = Util.GetData(0x4)
        self.logger.info( "fp is 0x%x" % fp)
        
        filename = Util.GetData(0x8)
         
        filePath = "".join(Util.Read(filename,1))
        
        self.logger.info( "filePath is %s" % filePath)
        
        mode = Util.GetData(0xC)
        self.logger.info( "mode is 0x%x" % (mode))
        
        is32not64 = Util.GetData(0x10)
        self.logger.info("is32not64 is %d" % (is32not64))
        
        fileName = os.path.basename(filePath)
        
        self.logger.info( "The filename is %s" % fileName)
        
        if fileName in self.filter['file']:
            self.handleSet.add(fp)
            self.logger.info( "Filter matched. Add handle to the handle's dictionary to start logging.")
        else:
            self.logger.info( "Filter did not match.")
            
        return 0
    
    def My_fclose(self):
        """
        int fclose ( FILE * stream );          
        """
        stream = Util.GetData(0x4)
        self.logger.info( "stream is 0x%x" % (stream) )
        
        retVal = idc.GetRegValue("EAX")
        
        return 0
