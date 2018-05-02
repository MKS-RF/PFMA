'''
Created on Sep 24, 2014

@author: Daniel Yun
@summary: Python implementation of SOEM master

Revisions Pushed 8/11/2015
@author: George Neal
@change: commented out #if self.IOMapSize== None:# to always call self.ec_config_map 
         - Fixed bug where ec_config_map was not properly reconfigured after first PREOP->SAFEOP->OP->PREOP 
'''

import sys
from ctypes import *
from struct import pack
from struct import unpack
from struct import calcsize
import os.path
import time

__version__ = '1.0.5'

EC_MAXNAME = 40 # "#define"'d constant in SOEM - not sure if possible to export, so defined here again
EC_MAXLEN_ADAPTERNAME = 128 # "#define"'d constant in SOEM - not sure if possible to export, so defined here again

class ec_adaptert(Structure):
    pass #declare _fields_ outside of class to allow self-reference
ec_adaptert._fields_ = [("name", c_char*EC_MAXLEN_ADAPTERNAME),
                        ("desc", c_char*EC_MAXLEN_ADAPTERNAME),
                        ("next", POINTER(ec_adaptert))]

SOEM_ERR_CODE_TYPES = {0x00:"SDO", 0x01:"EMERGENCY", 0x03:"PACKET", 0x04:"SDO_INFO", 0x05:"FOE", 0x06:"FOE_BUF2SMALL",
                    0x07:"FOE_PACKETNUMBER", 0x08:"SOE", 0x09:"MBX", 0x0A:"WINDOWS", 0x0B:"CUSTOM"}

class SOEM_Exception(Exception):
    '''
    Exception for errors that do not fall under any other specific exception.
    '''
    pass

class SOEM_Windows_Exception(SOEM_Exception):
    '''
    Exception for errors that occur during calls to Windows functions during SOEM initialization
    '''
    def __init__(self, message, err_type, err_code):
        message = str(message) + " Windows error code = " + str(err_code) #call to Windows GetLastError()
        SOEM_Exception.__init__(self, message)
        
        self.message = message
        self.err_type = err_type
        self.err_code = err_code

class SOEM_SDO_Exception(SOEM_Exception):
    '''
    Exception for SDO communication errors
    '''
    def __init__(self, message, err_type, err_code, AL_code, value):
        message = str(message) + " Error type = " + str(err_type) + "; Error code = " + str(err_code) + \
        "; AL Status = " + str(AL_code) + "; Value = " + str(value)
        SOEM_Exception.__init__(self, message)
        
        self.message = message
        self.err_type = err_type
        self.err_code = err_code
        self.AL_code = AL_code
        self.value = value

class SOEM_PDO_Exception(SOEM_Exception):
    '''
    Exception for PDO communication errors
    '''
    def __init__(self, message, err_type, err_code, AL_code, value):
        message = str(message) + " Error type = " + str(err_type) + "; Error code = " + str(err_code) + \
        "; AL Status = " + str(AL_code) + "; Value = " + str(value)
        SOEM_Exception.__init__(self, message)
        
        self.message = message
        self.err_type = err_type
        self.err_code = err_code
        self.AL_code = AL_code
        self.value = value
        
class SOEM_Data_Exception(SOEM_Exception):
    '''
    Exception for errors related to invalid/uninitialized data in SOEM's internal slave structure
    '''
    def __init__(self, message, AL_code):
        message = str(message) + " AL Status = " + str(AL_code)
        SOEM_Exception.__init__(self, message)
        
        self.message = message
        self.AL_code = AL_code

class soem:
    '''
    Modified SOEM EtherCAT master wrapper
    '''
    libname = "libsoem"
    STATES = {"INIT":0x01, "PREOP":0x02, "BOOT":0x03, "SAFEOP":0x04,
                     "OP":0x08, "ACK":0x10, "ERROR":0x10,
                     0x01:"INIT", 0x02:"PREOP", 0x03:"BOOT",
                     0x04:"SAFEOP", 0x08:"OP", 0x10:"ERROR"}

    def __init__(self):
        try:
            #raise SOEM_Exception(os.path)
            #if(os.path.isfile(self.libname+".dll") != True):
             #   raise SOEM_Exception("Cannot locate library. Check that libsoem.dll is in soem.py module directory.")
            self.dll = CDLL(self.libname)
        except WindowsError as e:
            raise SOEM_Exception("Cannot load library:" + str(e))
        
        try:
            self.ec_init = self.dll["ec_init"]
            self.ec_init.argtype = c_char_p
            self.ec_init.restype = c_int
            
            self.py_err2string = self.dll["hlp_err2string"]
            self.py_err2string.argtype = [c_uint, c_uint]
            self.py_err2string.restype = c_char_p
            
            self.ec_close = self.dll["ec_close"]
            #no arguments taken
            #no return value
            
            self.ec_config = self.dll["ec_config"]
            self.ec_config.argtype = [c_ubyte, c_void_p]
            self.ec_config.restype = c_int
            
            self.ec_config_map = self.dll["ec_config_map"]
            self.ec_config_map.argypte = c_void_p
            self.ec_config.restype = c_int
            
            self.ec_config_init = self.dll["ec_config_init"]
            self.ec_config_init.argtype = c_ubyte
            self.ec_config_init.restype = c_int
            
            self.py_get_slave_state = self.dll["hlp_get_slave_state"]
            self.py_get_slave_state.argtype = [c_int, POINTER(c_int)]
            self.py_get_slave_state.restype = c_ushort
            
            self.py_set_slave_state = self.dll["hlp_set_slave_state"]
            self.py_set_slave_state.argtype = [c_int, c_ushort]
            self.py_set_slave_state.restype = c_int
            
            self.py_get_slave_name = self.dll["hlp_get_slave_name"]
            self.py_get_slave_name.argtype = [c_int, c_char*(EC_MAXNAME + 1)]
            self.py_get_slave_name.restype = c_int
            
            self.py_get_eep_man = self.dll["hlp_get_eep_man"]
            self.py_get_eep_man.argtype = [c_int, POINTER(c_int)]
            self.py_get_eep_man.restype = c_int
            
            self.py_get_eep_id = self.dll["hlp_get_eep_id"]
            self.py_get_eep_id.argtype = [c_int, POINTER(c_int)]
            self.py_get_eep_id.restype = c_int
            
            self.py_get_eep_rev = self.dll["hlp_get_eep_rev"]
            self.py_get_eep_rev.argtype = [c_int, POINTER(c_int)]
            self.py_get_eep_rev.restype = c_int
            
            self.py_poperror = self.dll["hlp_poperror"]
            self.py_poperror.argtype = [POINTER(c_int), POINTER(c_int)]
            self.py_poperror.restype = c_int
            
            self.ec_readstate = self.dll["ec_readstate"]
            #no arguments taken
            self.ec_readstate.restype = c_int
            
            self.ec_writestate = self.dll["ec_writestate"]
            self.ec_writestate.argtype = c_ushort
            self.ec_writestate.restype = c_int
            
            self.ec_statecheck = self.dll["ec_statecheck"]
            self.ec_statecheck.argtype = [c_ushort, c_ushort, c_int]
            self.ec_statecheck.restype = c_ushort
            
            self.py_get_slave_ALstatuscode = self.dll["hlp_get_slave_ALstatuscode"]
            self.py_get_slave_ALstatuscode.argtype = c_int
            self.py_get_slave_ALstatuscode.restype = c_ushort
            
            self.ec_ALstatuscode2string = self.dll["ec_ALstatuscode2string"]
            self.ec_ALstatuscode2string.argtype = c_ushort
            self.ec_ALstatuscode2string.restype = c_char_p
            
            self.ec_elist2string = self.dll["ec_elist2string"]
            #no arguments taken
            self.ec_elist2string.restype = c_char_p
            
            self.py_get_slavecount = self.dll["hlp_get_slavecount"]
            #no arguments taken
            self.py_get_slavecount.restype = c_int
            
            self.ec_find_adapters = self.dll["ec_find_adapters"]
            #no arguments taken
            self.ec_find_adapters.restype = POINTER(ec_adaptert)
            
            self.ec_SDOread = self.dll["ec_SDOread"]
            self.ec_SDOread.argtype = [c_ushort, c_ushort, c_ubyte, c_ubyte, POINTER(c_int), c_void_p, c_int]
            self.ec_SDOread.restype = c_int
            
            self.ec_SDOwrite = self.dll["ec_SDOwrite"]
            self.ec_SDOwrite.argtype = [c_ushort, c_ushort, c_ubyte, c_ubyte, c_int, c_void_p, c_int]
            self.ec_SDOwrite.restype = c_int
            
            self.py_start_pdo_timer = self.dll["hlp_start_pdo_timer"]
            #no arguments taken
            self.py_start_pdo_timer.restype = c_uint
            
            self.py_stop_pdo_timer = self.dll["hlp_stop_pdo_timer"]
            self.py_stop_pdo_timer.argtype = c_uint
            self.py_stop_pdo_timer.restype = c_uint
            
            self.ec_send_processdata = self.dll["ec_send_processdata"]
            #no arguments taken
            self.ec_send_processdata.restype = c_int
            
            self.ec_receive_processdata = self.dll["ec_receive_processdata"]
            self.ec_receive_processdata.argtype = c_int
            self.ec_receive_processdata.restype = c_int
            
            self.py_pdo_input_size = self.dll["hlp_pdo_input_size"]
            self.py_pdo_input_size.argtype = [c_int, POINTER(c_int)]
            self.py_pdo_input_size.restype = c_uint
            
            self.py_pdo_output_size = self.dll["hlp_pdo_output_size"]
            self.py_pdo_output_size.argtype = [c_int, POINTER(c_int)]
            self.py_pdo_output_size.restype = c_uint
            
            self.py_pdo_input = self.dll["hlp_pdo_input"]
            self.py_pdo_input.argtype = [c_int, POINTER(c_ubyte)]
            self.py_pdo_input.restype = c_int
            
            self.py_pdo_output = self.dll["hlp_pdo_output"]
            self.py_pdo_output.argtype = [c_int, POINTER(c_ubyte)]
            self.py_pdo_output.restype = c_int
            
            self.py_pdo_input_ind = self.dll["hlp_pdo_input_ind"]
            self.py_pdo_input_ind.argtype = [c_int, POINTER(c_ubyte), c_int, c_int]
            self.py_pdo_input_ind.restype = c_int
            
            self.py_pdo_output_ind = self.dll["hlp_pdo_output_ind"]
            self.py_pdo_output_ind.argtype = [c_int, POINTER(c_ubyte), c_int, c_int]
            self.py_pdo_output_ind.restype = c_int
            
        except AttributeError as e:
            raise SOEM_Exception("Importing function failed: " + str(e))
        
        self.IOMap = (c_ubyte * 4096)()
        self.IOMapSize = None
        
    def err2string(self, err_type, err_code):
        if err_type == 0x00 or 0x04 or 0x08 or 0x09:
            return self.py_err2string(err_type, err_code)
        elif err_type == 0x0A:
            return FormatError(err_code)
        elif err_type == 0x0B:
            return "Custom error code (TODO)"
     
    def print_adapters(self):
        '''
        Print all available adapters
        '''
        xfdt
        adapter = self.ec_find_adapters()
        adap_count = 0
        try:
            while adapter.contents != None:
                print "#:" + str(adap_count) + " == " + str(adapter.contents.desc)
                adap_count += 1
                adapter = adapter.contents.next
        except ValueError: #reached end of linked list
            pass
    
    def config_slaves(self):
        '''
        Print all available adapters
        '''
        self.ec_config_init(0)

    
    def select_adapter(self, ind=0):
        '''
        Gets a pointer to an ec_adaptert linked list structure.
        Raises SOEM_Exception if no adapters found or requested index is outside linked list range (< 0 or > # adapters found).
        @param int ind                              index of adapter (default = 0 = first adapter in the list)
        @return POINTER(ec_adaptert)                pointer to adapter
        '''        
        #count number of adapters
        adapter = self.ec_find_adapters()
        adap_count = 0
        try:
            while adapter.contents != None:
                adap_count += 1
                adapter = adapter.contents.next
        except ValueError: #reached end of linked list
            pass
        
        if adap_count == 0:
            raise SOEM_Exception("No pcap adapters found.")
        if ind < 0 or ind >= adap_count:
            raise SOEM_Exception("Adapter index out of range. Must be within 0 and " + str(adap_count - 1) + ".")
        
        adapter = self.ec_find_adapters()
        while ind > 0:
            adapter = adapter.contents.next
            ind -= 1
        
        return adapter 
        
    def open(self, adapter):
        '''
        Initializes pcap and opens a connection to all available slaves.
        @param POINTER(ec_adaptert) adapter         pointer to linked-list structure generated by select_adapter()
                                                    that identifies the pcap adapter to connect to
        @return int                                 number of slaves found
        '''
        if self.ec_init(c_char_p(adapter.contents.name)) <= 0:
            raise SOEM_Exception("Adapter out of range or ec_init() failed.")
        
        if self.ec_config_init(False) <= 0:
            raise SOEM_Exception("config_init() failed.")
        
        return self.py_get_slavecount()
    
    def close(self):
        '''
        Sets all slaves back to INIT; terminates connection and closes SOEM.
        @return int                                 >0 if succesful
        '''
        if self.py_set_slave_state(0, self.STATES["INIT"]) <= 0:
            raise SOEM_Exception("Slave index out of range.")
        
        self.ec_writestate(0) #returns 0 always
        self.ec_close() #no return
        
        return 1
    
    def slave_count(self):
        '''
        Returns the number of configured slaves.
        @return int                                 number of configured slaves
        '''
        return self.py_get_slavecount()
    
    def get_lasterror(self):
        '''
        Pops the last error from the error stack, then converts it to its corresponding error description string
        @return string                              error string from SOEM stack, or empty string ("") if no error
        '''
        return self.ec_elist2string()
    
    def get_slave_ALstatuscode(self, slave):
        '''
        Returns the AL status code for target slave
        @param int slave                            slave number
        @return int                                 error code from SOEM stack
        '''
        return self.py_get_slave_ALstatuscode(slave)
    
    def ALstatuscode2string(self, code):
        '''
        Returns the AL status description string based on given code
        @param int code                             AL status code
        @return string                              error string from SOEM stack
        '''
        return self.ec_ALstatuscode2string(code)
    
    def get_ALstatusmessage(self, slave):
        '''
        Returns the AL status description string for target slave
        @param int slave                            slave number
        @return string                              error string from SOEM stack
        '''
        return self.ec_ALstatuscode2string(self.py_get_slave_ALstatuscode(slave))
    
    def get_slave_name(self, slave):
        '''
        Returns the display name of the target slave
        @param int slave                            slave number
        @return string                              display name of target slave
        '''
        name = (c_char*(EC_MAXNAME+1))()
        if self.py_get_slave_name(slave, name) <= 0:
            raise SOEM_Exception("Slave index out of range.")
        
        return name.value
    
    def get_eep_man(self, slave):
        '''
        Returns the manufacturer number of the target slave (from EEPROM)
        @param int slave                            slave number
        @return int                                 manufacturer number
        '''
        val = c_int()
        if self.py_get_eep_man(slave, byref(val)) <= 0:
            raise SOEM_Exception("Slave index out of range.")
        
        return val.value
    
    def get_eep_id(self, slave):
        '''
        Returns the Product ID of the target slave (from EEPROM)
        @param int slave                            slave number
        @return int                                 product ID
        '''
        val = c_int()
        if self.py_get_eep_id(slave, byref(val)) <= 0:
            raise SOEM_Exception("Slave index out of range.")
        
        return val.value
    
    def get_eep_rev(self, slave):
        '''
        Returns the revision number of the target slave (from EEPROM)
        @param int slave                            slave number
        @return int                                 revision number
        '''
        val = c_int()
        if self.py_get_eep_rev(slave, byref(val)) <= 0:
            raise SOEM_Exception("Slave index out of range.")
        
        return val.value
        
    def get_state(self, slave):
        '''
        Returns the current state for target slave, or lowest state among all slaves if slave number = 0
        @param int slave                            slave number
        @return int                                 current state
        '''
        self.ec_readstate()
        state = c_int()
        response = self.py_get_slave_state(slave, byref(state))
        if  response <= 0:
            raise SOEM_Exception("Unable to read current state.")
        
        return state.value
    
    def set_state(self, slave, target_state, timeout=1000000):
        '''
        Sets target slave to desired state, or sets all slaves if slave number == 0
        Raises SOEM_Exception if attempting to perform illegal state change
        Raises SOEM_Windows_Exception if error occurs while starting/stopping PDO timer
        @param int slave                            slave number
        @param int state                            desired state
        @param int timeout                          (Optional) timeout for post-state change statecheck
        @return int or None                         state of slave after writing
        @postcondition                              errors in transitioning to/from OP will set a Windows error code,
                                                    which can be translated to a string by FormatError()
                                                    
        '''
        current_state = c_int()
        if self.py_get_slave_state(slave, byref(current_state)) <= 0:
            raise SOEM_Exception("Slave index out of range.")
        
        current_state = current_state.value        
        
        # Check if target_state is valid from current_state
        # Also configure slave to prepare for target_state in some cases
        if current_state == self.STATES["INIT"]:
            if target_state != self.STATES["INIT"] and target_state != self.STATES["PREOP"] and target_state != self.STATES["BOOT"]:
                raise SOEM_Exception("Invalid state change requested: " + str(self.STATES[current_state]) + " to " +
                                     str(self.STATES[target_state]) + " not allowed.")
        elif current_state == self.STATES["BOOT"]:
            if target_state != self.STATES["BOOT"] and target_state != self.STATES["INIT"]:
                raise SOEM_Exception("Invalid state change requested: " + str(self.STATES[current_state]) + " to " +
                                     str(self.STATES[target_state]) + " not allowed.")
        elif current_state == self.STATES["PREOP"]:
            if target_state != self.STATES["PREOP"] and target_state != self.STATES["INIT"] and target_state != self.STATES["SAFEOP"]:
                raise SOEM_Exception("Invalid state change requested: " + str(self.STATES[current_state]) + " to " +
                                     str(self.STATES[target_state]) + " not allowed.")
            elif target_state == self.STATES["SAFEOP"]:
                #if self.IOMapSize == None: # Removed to fix bug  where running two consecutive PDO.csv's causes second to be unable to change state 
                self.IOMapSize = self.ec_config_map(byref(self.IOMap))
        elif current_state == self.STATES["SAFEOP"]:
            if target_state != self.STATES["SAFEOP"] and target_state != self.STATES["INIT"] and target_state != self.STATES["PREOP"] and \
               target_state != self.STATES["OP"]:
                raise SOEM_Exception("Invalid state change requested: " + str(self.STATES[current_state]) + " to " +
                                     str(self.STATES[target_state]) + " not allowed.")
            elif target_state == self.STATES["OP"]:
                if self.py_start_pdo_timer() <= 0:
                    raise SOEM_Windows_Exception("Windows Error occurred while standing PDO timer; failed to " + \
                        "successfully change from "  + str(self.STATES[current_state]) + " to " + str(self.STATES[target_state]) + \
                        ".", SOEM_ERR_CODE_TYPES["WINDOWS"], GetLastError())
                #read/write PDO once to make slave happy				
                self.ec_send_processdata()
                self.ec_receive_processdata(2000)
        elif current_state == self.STATES["OP"]:
            if target_state != self.STATES["OP"] and target_state != self.STATES["INIT"] and target_state != self.STATES["SAFEOP"] and \
               target_state != self.STATES["PREOP"]:
                raise SOEM_Exception("Invalid state change requested: " + str(self.STATES[current_state]) + " to " +
                                     str(self.STATES[target_state]) + " not allowed.")
            elif target_state != self.STATES["OP"]:
                if self.py_stop_pdo_timer() <= 0:
                    raise SOEM_Windows_Exception("Windows Error occurred while stopping PDO timer; failed to " + \
                        "successfully change from "  + str(self.STATES[current_state]) + " to " + str(self.STATES[target_state]) + \
                        ".", SOEM_ERR_CODE_TYPES["WINDOWS"], GetLastError())
        else:
            #raise SOEM_Exception("Current state invalid.")
            pass
        
        # Set target state        
        if self.py_set_slave_state(slave, target_state) <= 0:
            raise SOEM_Exception("Invalid slave number.")
        self.ec_writestate(slave)
        end_state = self.ec_statecheck(slave, target_state, timeout)
        
        return end_state
    
    def SDO_read_buf(self, slave, index, subindex, psize_ptr, p_ptr, CA=False, timeout=1000000):
        '''
        Reads SDO data into buffer p_ptr of minimum length *psize_ptr
        Writes number of bytes read into *psize_ptr
        @param int slave                        slave number
        @param int index                        SDO index
        @param int subindex                     SDO subindex (ignored if CA set to True)
        @param POINTER(c_int) psize_ptr         pointer to size of *p_ptr; after read, *psize_ptr = number of bytes read
        @param POINTER(c_ubyte array) p_ptr     pointer to buffer of size >= *psize_ptr; after read, *p_ptr holds SDO data read
        @param Boolean CA                       True if using Complete Access (default = False = single subindex access)
        @param int timeout                      timeout in us
        @return int                             >0 if successful
        '''
        status = self.ec_SDOread(slave, index, subindex, CA, psize_ptr, p_ptr, timeout)
        if status <= 0:
            errtype = c_uint()
            errcode = c_uint()
            err = self.py_poperror(byref(errtype), byref(errcode))
            if err:
                raise SOEM_SDO_Exception("SDO buffered read failed.", errtype.value, errcode.value, self.py_get_slave_ALstatuscode(slave), p_ptr.contents[0:psize_ptr.contents.value])
            else:
                raise SOEM_Exception("SDO buffered read failed. Error stack empty.")
        
        return status
    
    #TODO: Handle addr type "a" orig timeout=1000000   
    def SDO_read(self, slave, index, subindex, fmt, CA=False, timeout=1000000):
        '''
        Reads SDO data based on format string and returns the formatted value
        Valid format strings are "c", "b", "B", h" "H", "i", "I", "l", "L", "q", "Q", "f", "d", "s", "p"
        See https://docs.python.org/2/library/struct.html#format-characters
        @param int slave                        slave number
        @param int index                        SDO index
        @param int subindex                     SDO subindex
        @param string fmt                       format string for number/floating point value
        @param Boolean CA                       True if using Complete Access (default = False = single subindex access)
        @param int timeout                      timeout in us
        @return value                           read value formatted based on format string
        '''
        if fmt == "a": 
            fmt = "s"
        if fmt == "s" or fmt == "p" or fmt[0].isdigit():
            buf = (c_ubyte * 4096)()
            size = c_int(4096)
        else:
            try:
                buf = (c_ubyte * calcsize(fmt))()
                size = c_int(calcsize(fmt))
            except:
                raise SOEM_Exception("Invalid format string: " + str(fmt)) 
        
        status = self.ec_SDOread(slave, index, subindex, CA, byref(size), byref(buf), timeout)
        if ( (fmt != "s" and fmt != "p") and calcsize(fmt) != size.value): #read failed or wrong number of bytes
            errtype = c_uint()
            errcode = c_uint()
            err = self.py_poperror(byref(errtype), byref(errcode))
            print self.get_lasterror()
            if err:
                raise SOEM_SDO_Exception("SDO read sizes do not match. Expected = " + str(calcsize(fmt))
                    + " bytes; Actual = " + str(size.value) + " bytes.",
                    errtype.value, errcode.value, self.py_get_slave_ALstatuscode(slave), 0)
            else:
                raise SOEM_Exception("SDO read sizes do not match. Error stack empty. Expected = " + str(calcsize(fmt))
                    + " bytes; Actual = " + str(size.value) + " bytes.")
            
        if (fmt=="s" or fmt=="p"): #strings (need to unpack all characters)
            try:
                val = unpack("@"+str(size.value)+fmt, bytearray(buf[0:size.value]))[0]
            except:
                raise SOEM_Exception("Invalid format string: " + str(fmt))
            if status <= 0:
                errtype = c_uint()
                errcode = c_uint()
                err = self.py_poperror(byref(errtype), byref(errcode))
                if err:
                    raise SOEM_SDO_Exception("SDO read failed.", errtype.value, errcode.value, self.py_get_slave_ALstatuscode(slave), val)
                else:
                    raise SOEM_Exception("SDO read failed. Error stack empty.blah2")
            
        else: # single number or array of numbers
            try:
                # print (buf)  just prints out address of buf
                #for index in range(len(buf)):
                    # print 'index' + index + " value " + buf[index]
                    #print index
                    #print buf[index]
                print("single number or array case - fmt is " + fmt)
                val = unpack("@"+fmt, bytearray(buf[0:size.value]))
               # val = unpack("@"+fmt, str(bytearray(buf[0:size.value])))
            except:
                print("Getting exception after unpack()")
                raise SOEM_Exception("Invalid format string: " + str(fmt))
            if len(val) == 1:
                val = val[0] #single number, don't want a tuple
            else:
                val = list(val)
            if status <= 0:
                errtype = c_uint()
                errcode = c_uint()
                err = self.py_poperror(byref(errtype), byref(errcode))
                if err:
                    raise SOEM_SDO_Exception("SDO read failed.", errtype.value, errcode.value, self.py_get_slave_ALstatuscode(slave), val)
                else:
                    raise SOEM_Exception("SDO read failed. Error stack empty.blah")
                
        return val
    
    def SDO_write_buf(self, slave, index, subindex, psize, p_ptr, CA=False, timeout=1000000):
        '''
        Writes SDO data from buffer p_ptr of minimum length psize
        @param int slave                        slave number
        @param int index                        SDO index
        @param int subindex                     SDO subindex (ignored if CA set to True)
        @param c_int psize                      number of bytes to read from *p_ptr
        @param POINTER(c_ubyte array) p_ptr     pointer to buffer of size >= psize containing data to write
        @param Boolean CA                       True if using Complete Access (default = False = single subindex access)
        @param int timeout                      timeout in us
        @return int                             >0 if successful
        '''
        status = self.ec_SDOwrite(slave, index, subindex, CA, psize, p_ptr, timeout)
        if status <= 0:
            errtype = c_uint()
            errcode = c_uint()
            err = self.py_poperror(byref(errtype), byref(errcode))
            if err:
                raise SOEM_SDO_Exception("SDO buffered write failed.", errtype.value, errcode.value, self.py_get_slave_ALstatuscode(slave), p_ptr.contents[0:psize.value])
            else:
                raise SOEM_Exception("SDO buffered write failed. Error stack empty.")
        
        return status
    
    #TODO: Handle addr type "a"
    def SDO_write(self, slave, index, subindex, fmt, val, CA=False, timeout=1000000):
        '''
        Writes SDO data based on format string
        Valid format strings are "c", "b", "B", h" "H", "i", "I", "l", "L", "q", "Q", "f", "d", "s", "p"
        See https://docs.python.org/2/library/struct.html#format-characters
        @param int slave                        slave number
        @param int index                        SDO index
        @param int subindex                     SDO subindex
        @param string fmt                       format string for number/floating point value
        @param val                              value to write
        @param Boolean CA                       True if using Complete Access (default = False = single subindex access)
        @param int timeout                      timeout in us
        @return int                             >0 if successful
        '''
        try:
            if fmt=="s" or fmt=="p":
                buf = list(pack("@"+str(len(val))+fmt, val)) #pack all characters
            elif fmt[0].isdigit():
                buf = list(pack("@"+fmt, *val)) # list of multiple values
            else:
                if (val < 0):
                    fmt = fmt.lower()
                buf = list(pack("@"+fmt, val))
            
            for i in range(0, len(buf)):
                buf[i] = ord(buf[i])
            if fmt == "s" or fmt == "p":
                buf = (c_ubyte * (len(val) * calcsize(fmt)))(*buf)
                psize = c_int(len(val) * calcsize(fmt))       
            else:
                buf = (c_ubyte * calcsize(fmt))(*buf)
                psize = c_int(calcsize(fmt)) 
        except:
            raise SOEM_Exception("Invalid format string: " + str(fmt))
        
        status = self.ec_SDOwrite(slave, index, subindex, CA, psize, byref(buf), timeout)
        if status <= 0:
            errtype = c_uint()
            errcode = c_uint()
            err = self.py_poperror(byref(errtype), byref(errcode))
            if err:
                raise SOEM_SDO_Exception("SDO write failed.", errtype.value, errcode.value, self.py_get_slave_ALstatuscode(slave), val)
            else:
                raise SOEM_Exception("SDO write failed. Error stack empty.")
            
        return status
    
    def PDOIn_size(self, slave):
        '''
        Gets size of PDO input for target slave
        @param int slave                        slave number
        @return: input size                     size of PDO input
        '''
        size = c_int()
        if self.py_pdo_input_size(slave, byref(size)) <= 0:
            raise SOEM_Exception("Getting PDO Input size failed.")
        
        return size.value
    
    def PDOOut_size(self, slave):
        '''
        Gets size of PDO output for target slave
        @param int slave                        slave number
        @return: output size                    size of PDO output
        '''
        size = c_int()
        if self.py_pdo_output_size(slave, byref(size)) <= 0:
            raise SOEM_Exception("Getting PDO Output size failed.")
        
        return size.value
    
    def PDOIn_read_buf(self, slave, in_ptr):
        '''
        Copies PDO input data into in_ptr     
        @param int slave                        slave number
        @param POINTER(c_ubyte array) in_ptr    pointer to array that will hold PDO input data
        @return int                             PDO update counter
        '''
        status = self.py_pdo_input(slave, in_ptr) 
        if status <= 0:
            errtype = c_uint()
            errcode = c_uint()
            err = self.py_poperror(byref(errtype), byref(errcode))
            if err:
                raise SOEM_PDO_Exception("PDO read failed.", errtype.value, errcode.value, self.py_get_slave_ALstatuscode(slave), in_ptr.value)
            else:
                raise SOEM_Exception("Invalid slave number or empty input pointer.")
        else:
            return status
    
    def PDOOut_write_buf(self, slave, out_ptr):
        '''
        Copies PDO output data from out_ptr
        @param int slave                        slave number
        @param POINTER(c_ubyte array) out_ptr   pointer to array that holds PDO output data
        @return int                             PDO update counter
        '''
        status = self.py_pdo_output(slave, out_ptr)
        if status <= 0:
            errtype = c_uint()
            errcode = c_uint()
            err = self.py_poperror(byref(errtype), byref(errcode))
            if err:
                raise SOEM_PDO_Exception("PDO write failed.", errtype.value, errcode.value, self.py_get_slave_ALstatuscode(slave), out_ptr.value)
            else:
                raise SOEM_Exception("Invalid slave number or empty input pointer.")
        else:
            return status
        
    def PDOIn_read_ind(self, slave, in_ptr, index, size):
        '''
        Copies PDO input data at index into in_ptr   
        @param int slave                        slave number
        @param POINTER(c_ubyte array) in_ptr    pointer to array that will hold PDO input data
        @param int index                        index of PDO input data to start reading from
        @param int size                         number of bytes of PDO input data to read
        @return int                             PDO update counter
        '''
        status = self.py_pdo_input_ind(slave, in_ptr, index, size) 
        if status <= 0:
            errtype = c_uint()
            errcode = c_uint()
            err = self.py_poperror(byref(errtype), byref(errcode))
            if err:
                raise SOEM_PDO_Exception("PDO indexed read failed.", errtype.value, errcode.value, self.py_get_slave_ALstatuscode(slave), in_ptr.value)
            else:
                raise SOEM_Exception("Invalid slave number or empty input pointer.")
        else:
            return status
    
    def PDOOut_write_ind(self, slave, out_ptr, index, size):
        '''
        Copies PDO output data to index from out_ptr
        @param int slave                        slave number
        @param POINTER(c_ubyte array) out_ptr   pointer to array that holds PDO output data
        @param int index                        index of PDO output data to start writing to
        @param int size                         number of bytes of PDO output data to write
        @return int                             PDO update counter
        '''
        status = self.py_pdo_output_ind(slave, out_ptr, index, size)
        if status <= 0:
            errtype = c_uint()
            errcode = c_uint()
            err = self.py_poperror(byref(errtype), byref(errcode))
            if err:
                raise SOEM_PDO_Exception("PDO indexed write failed.", errtype.value, errcode.value, self.py_get_slave_ALstatuscode(slave), out_ptr.value)
            else:
                raise SOEM_Exception("Invalid slave number or empty input pointer.")
        else:
            return status
        
    def PDOIn_read(self, slave, index, fmt):
        '''
        Reads PDO data based on format string and returns the formatted value
        Valid format strings are "c", "b", "B", h" "H", "i", "I", "l", "L", "q", "Q", "f", "d", "s", "p"
        See https://docs.python.org/2/library/struct.html#format-characters
        @param int slave                        slave number
        @param int index                        PDO index
        @param string fmt                       format string for number/floating point value
        @return value    `                      read value formatted based on format string
        '''
        size = c_int(calcsize(fmt))
        pdo_buf = (c_ubyte * size.value)()
        ind = c_int(index)
        
        status = self.py_pdo_input_ind(slave, byref(pdo_buf), ind, size)
        
        if (fmt=="s" or fmt=="p"): #strings (need to unpack all characters)
            try:
                val = unpack("@"+str(size.value)+fmt, bytearray(pdo_buf[0:size.value]))[0]
            except:
                raise SOEM_Exception("Invalid format string: " + str(fmt))
            if status <= 0:
                errtype = c_uint()
                errcode = c_uint()
                err = self.py_poperror(byref(errtype), byref(errcode))
                if err:
                    raise SOEM_PDO_Exception("PDO read failed.", errtype.value, errcode.value, self.py_get_slave_ALstatuscode(slave), val)
                else:
                    raise SOEM_Exception("PDO read failed. Error stack empty.")
            
        else: # single number or array of numbers
            try:
                val = unpack("@"+fmt, bytearray(pdo_buf[0:size.value]))
            except:
                raise SOEM_Exception("Invalid format string: " + str(fmt))
            if len(val) == 1:
                val = val[0] #single number, don't want a tuple
            else:
                val = list(val)
            if status <= 0:
                errtype = c_uint()
                errcode = c_uint()
                err = self.py_poperror(byref(errtype), byref(errcode))
                if err:
                    raise SOEM_SDO_Exception("PDO read failed.", errtype.value, errcode.value, self.py_get_slave_ALstatuscode(slave), val)
                else:
                    raise SOEM_Exception("PDO read failed. Error stack empty.")
                
        return val

    def PDOOut_write(self, slave, index, fmt, val):
        try:
            if fmt=="s" or fmt=="p":
                buf = list(pack("@"+str(len(val))+fmt, val)) #pack all characters
            elif fmt[0].isdigit():
                buf = list(pack("@"+fmt, *val)) # list of multiple values
            else:
                buf = list(pack("@"+fmt, val))
            
            for i in range(0, len(buf)):
                buf[i] = ord(buf[i])
            if fmt == "s" or fmt == "p":
                buf = (c_ubyte * (len(val) * calcsize(fmt)))(*buf)
                size = c_int(len(val) * calcsize(fmt))       
            else:
                buf = (c_ubyte * calcsize(fmt))(*buf)
                size = c_int(calcsize(fmt)) 
        except:
            raise SOEM_Exception("Invalid format string: " + str(fmt))
        
        status = self.py_pdo_output_ind(slave, byref(buf), index, size)
        if status <= 0:
            errtype = c_uint()
            errcode = c_uint()
            err = self.py_poperror(byref(errtype), byref(errcode))
            if err:
                raise SOEM_SDO_Exception("PDO write failed.", errtype.value, errcode.value, self.py_get_slave_ALstatuscode(slave), val)
            else:
                raise SOEM_Exception("PDO write failed. Error stack empty.")
            
        return status
        
        
