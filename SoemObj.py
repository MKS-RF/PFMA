'''
Created on Nov 6, 2014

@author: Daniel Yun

Modified on April 10, 2015
@author: Michael Park
@change: added Edestination class
@change: added parse destination function
@change: added execute function
@change: added comments for each module
@change: modified pdo and sdo to handle unhappy path test cases

July 13, 2015
@author: George Neal
@change: added "get_current_state" function for ECAT state
@change: added ECAT state checks based on SDO/PDO R/W
@change: raise SOEM_Exception when current state could not be read-back

August 11, 2015
@author: George Neal
@change: Changed result strings to be more uniform: to simplify parsing in check_deviation
'''

'''
September 13, 2017
@author: Anthony Nguyen
added comments to failures for robot framework
moved go sleep function to soemobj
moved all imports as well from runner
added type dictionary
added deviation parameter
split 'parse_sdo' to 'read_sdo' and 'write_sdo'
split 'parse_pdo' to 'read_pdo' and 'write_pdo'
added label argument to define any assertion errors
added assertion errors to change_state commands so test cases will fail with non-state arguments
removed ecat destination class, execute method, parse destination method
removed unused imports from runner.py
removed return calls and replaced them with assertion errors

'''

import time
from time import sleep

import soem
from soem import SOEM_Exception

__version__ = '1.0.8'
ecatdest = None


'''
@summary: Encapsulates ECAT initialization, open, close, and parsing modules
'''


class SoemObj(object):
    '''
    SOEM EtherCAT object used for Interface Test
    '''

    def __init__(self, adap_num):
        '''
        Constructor
        '''
        self.master = soem.soem()
        self.adapter = self.master.select_adapter(adap_num)

        '''
        Type Dictionary
        '''

        self.type_dictionary = {'': None,
                                'BOOL': 'b',
                                'ADDR': 'a',
                                'BYTE': 'B',
                                'WORD': 'H',
                                'REAL': 'f',
                                'DWORD': 'I',
                                'INT': 'h',
                                'UINT': 'H',
                                'UDINT': 'I',
                                'STRING': 's',
                                }

    '''
    Connects to SOEM
    '''

    def open(self):
        '''
        Open EtherCAT connection; finds number of slaves in network; tries to set all slaves to safe-op
        '''
        try:
            self.slave_count = self.master.open(self.adapter)
        except soem.SOEM_Exception:
            try:
                log(
                    "SOEM_Exception occured initializing fieldbus.\nIs the Ecat adapter set correctly?, soem.open(adapter)")
            except:
                print (
                    "SOEM_Exception occured initializing fieldbus.\nIs the Ecat adapter set correctly?, soem.open(adapter)")
            return False

        try:
            for slv in range(1, self.slave_count + 1):
                cur_state = self.master.set_state(slv, self.master.STATES["INIT"])
                tries = 0
                while tries < 10 and cur_state != self.master.STATES["PREOP"]:
                    cur_state = self.master.set_state(slv, self.master.STATES["PREOP"])
                    tries = tries + 1
        except soem.SOEM_Windows_Exception:
            try:
                log("SOEM_Exception occured initializing fieldbus, setting state to PREOP")
            except:
                print ("SOEM_Exception occured initializing fieldbus, soem.open(adapter)")

            return False

        if cur_state != self.master.STATES["PREOP"]:
            try:
                log("SOEM_Exception occured initializing fieldbus, unable to set state to PREOP")
            except:
                print ("SOEM_Exception occured initializing fieldbus, soem.open(adapter)")

            return False
        else:
            return True

    '''
    Disconnects from SOEM
    '''

    def close(self):
        try:
            self.master.set_state(0, self.master.STATES["INIT"])
            self.master.close()
            return True
        except:
            return False

    '''
    @param time
    @return: 1: success, -1: sleep failed
    '''

    def go_sleep(self, time):
        try:
            time = float(time)
            sleep(time)
            return 1
        except:
            raise AssertionError
            return -1

    '''
    Get current state as string
    '''

    def get_current_state(self, slave):
        return self.master.STATES[self.master.get_state(slave)]

    '''
    changes the ECAT state into target_state
    '''

    def change_state(self, slave, target_state):

        if slave > self.slave_count:
            raise AssertionError, "Slave index out of bounds!"
            return -1

        current_state = self.get_current_state(slave)

        if current_state == "INIT":
            if target_state == "INIT" or target_state == "PREOP" or target_state == "BOOT":
                self.master.set_state(slave, self.master.STATES[target_state])
            elif target_state == "SAFEOP":
                self.change_state(slave, "PREOP")
                self.master.set_state(slave, self.master.STATES[target_state])
            elif target_state == "OP":
                self.change_state(slave, "SAFEOP")
                self.master.set_state(slave, self.master.STATES[target_state])
            else:
                raise AssertionError, "Invalid target state!"
                return -1
        elif current_state == "PREOP":
            if target_state == "BOOT":
                self.change_state(slave, "INIT")
                self.master.set_state(slave, self.master.STATES[target_state])
            if target_state == "PREOP" or target_state == "INIT" or target_state == "SAFEOP":
                self.master.set_state(slave, self.master.STATES[target_state])
            elif target_state == "OP":
                self.change_state(slave, "SAFEOP")
                self.master.set_state(slave, self.master.STATES[target_state])
            else:
                raise AssertionError, "Invalid target state!"
                return -1
        elif current_state == "SAFEOP" or current_state == "OP":
            if target_state == "BOOT":
                self.change_state(slave, "INIT")
                self.master.set_state(slave, self.master.STATES[target_state])
            elif target_state == "SAFEOP" or target_state == "INIT" or target_state == "PREOP" or target_state == "OP":
                self.master.set_state(slave, self.master.STATES[target_state])
            else:
                raise AssertionError, "Invalid target state!"
                return -1
        elif current_state == "BOOT":
            if target_state == "INIT":
                self.master.set_state(slave, self.master.STATES[target_state])
            elif target_state == "PREOP":
                self.master.change_state(slave, "INIT")
                self.master.set_state(slave, target_state)
            elif target_state == "SAFEOP":
                self.change_state(slave, "PREOP")
                self.master.set_state(slave, self.master.STATES[target_state])
            elif target_state == "OP":
                self.change_state(slave, "SAFEOP")
                self.master.set_state(slave, self.master.STATES[target_state])
            else:
                raise AssertionError, "Invalid target state!"
                return -1
        else:
            raise AssertionError, "Invalid current state!"
            return -1
        val = self.get_current_state(slave)
        return val

    '''
    Requests SDO Read or Write function in SOEM Wrapper class 
    Returns a result as a list: List[0] = success or fail indicator, List[1] = return message  
    '''

    def read_sdo(self, slave_num, index, sub_index, val_type, value, response, label, deviation):
        if slave_num > self.slave_count:
            raise AssertionError, "Failed! Slave number ({}) is greater than # of found slaves. {} Address: {}.{}.{}; Label: {}".format(
                slave_num, self.slave_count, slave_num, index, sub_index, label)

        val_type = self.type_dictionary[val_type]

        try:
            if sub_index == -1:
                rval = self.master.SDO_read(slave_num, index, 0, str(len(value)) + val_type, CA=True)
            else:
                rval = self.master.SDO_read(slave_num, index, sub_index, val_type)                

          #  if deviation == None:  # checks for deviation parameter                
          #      return ["slave_num({}), index({}), subindex({}). val_type({})".format(
          #      slave_num, index, sub_index, val_type)] 
                
            if deviation == None:    
                 pass    
            else:
                lowerDev = value - deviation
                upperDev = value + deviation
                if lowerDev < rval < upperDev:
                    value = rval
                else:
                    raise AssertionError, "Failed! Expected: {} is not within {} of Actual: {}".format(rval, deviation,
                                                                                                       value)

            if response == None:  # expected valid response + no error expected
                try:
                    if (val_type == 's'):
                        rval = rval.rstrip('\000')
                    value = type(rval)(value)
                    
                except:
                    raise AssertionError, "Failed! Could not typecast expected value to received value type; Value received: {}; Label: {}".format(
                        str(rval), label)

                if isinstance(rval, (str, unicode)):
                    rval = rval.rstrip('\000')
                    try:
                        sval = rval.encode("utf-8")
                    except UnicodeDecodeError:
                        sval = "\\x" + rval.encode("hex")

                    if rval == value:
                        return (sval)
                    else:
                        raise AssertionError, "Failed! Value received does not match expected value; Value Received: {}; Label: {}".format(
                            sval, label)
                else:
                    if rval == value:
                        return  str(rval)
                    else:
                        raise AssertionError, "Failed! Value received does not match expected value; Value received: {}; Label: {}".format(
                            str(rval), label)
            else:  # expected error
                raise AssertionError, "Failed! Exception error expected but (valid) Value received; Value received: {}; Label: {}".format(
                    str(rval), label)

        except soem.SOEM_SDO_Exception as e:
            if response == None:  # expected valid response + no error
                raise AssertionError, "Failed! Error not expected but error occurred; error received: {}; error code: {}; Label: {}".format(
                    str(self.master.err2string(e.err_type, e.err_code)), hex(e.err_code), label)
            else:  # expected error
                if e.err_code == response:
                    return ["True", "Success! Error received matches expected error; error received: "
                            + str(self.master.err2string(e.err_type, e.err_code)) + "; error code: " + hex(
                        e.err_code)]
                else:
                    raise AssertionError, "Failed! Error received does not match expected error; error recieved: {}; error code: {}; Label: {}".format(
                        str(self.master.err2string(e.err_type, e.err_code)), hex(e.err_code), label)

        except soem.SOEM_Exception as e:
            raise AssertionError, "Failed! Non-SDO error occurred; {}; Label: {}".format(str(e.message), label)
            try:
                if sub_index == -1:
                    rval = self.master.SDO_read(slave_num, index, 0, str(len(value)) + val_type, CA=True)
                else:
                    rval = self.master.SDO_read(slave_num, index, sub_index, val_type)

                if response == None:  # expected valid response + no error expected
                    try:
                        if (val_type == 's'):
                            rval = rval.rstrip('\000')
                        value = type(rval)(value)
                       # return [u"True", u"Success! Value received matches expected value; Value received: "
                       #         + (value)]
                        
                    except:
                        raise AssertionError, "Failed! Could not typecast expected value to received value type; Value received: {}; Label: {}".format(
                            str(rval), label)

                    if isinstance(rval, (str, unicode)):
                        rval = rval.rstrip('\000')
                        try:
                            sval = rval.encode("utf-8")
                        except UnicodeDecodeError:
                            sval = "\\x" + rval.encode("hex")

                        if rval == value:
                            return [u"True", u"Success! Value received matches expected value; Value received: "
                                    + (sval)]
                        else:
                            raise AssertionError, "Failed! Value received does not match expected value; Value Received: {}; Label: {}".format(
                                sval, label)
                    else:
                        if rval == value:
                            return [u"True", u"Success! Value received matches expected value; Value received: "
                                    + str(rval)]
                        else:
                            raise AssertionError, "Failed! Value received does not match expected value; Value received: {}; Label: {}".format(
                                str(rval), label)
                else:  # expected error
                    raise AssertionError, "Failed! Exception error expected but (valid) Value received; Value received: {}; Label: {}".format(
                        str(rval), label)

            except soem.SOEM_SDO_Exception as e:
                if response == None:  # expected valid response + no error
                    raise AssertionError, "Failed! Error not expected but error occurred; error received: {}; error code: {}; Label: {}".format(
                        str(self.master.err2string(e.err_type, e.err_code)), hex(e.err_code), label)
                else:  # expected error
                    if e.err_code == response:
                        return ["True", "Success! Error received matches expected error; error received: "
                                + str(self.master.err2string(e.err_type, e.err_code)) + "; error code: " + hex(
                            e.err_code)]
                    else:
                        raise AssertionError, "Failed! Error received does not match expected error; error recieved: {}; error code: {}; Label: {}".format(
                            str(self.master.err2string(e.err_type, e.err_code)), hex(e.err_code), label)

            except soem.SOEM_Exception as e:
                raise AssertionError, "Failed! Non-SDO error occurred; {}; Label: {}".format(str(e.message), label)

    def write_sdo(self, slave_num, index, sub_index, val_type, value, response, label):

        if slave_num > self.slave_count:
            raise AssertionError, "Failed! Slave number ({}) is greater than # of found slaves. {} Address: {}.{}.{}; Label: {}".format(
                slave_num, self.slave_count, slave_num, index, sub_index, label)

        val_type = self.type_dictionary[val_type]

        try:
            if sub_index == -1:
                str(self.master.SDO_write(slave_num, index, 0, str(len(value)) + val_type, value, CA=True))
            else:
                str(self.master.SDO_write(slave_num, index, sub_index, val_type, value))

            if response == None:  # expected valid response + no error expected
                return ["True", "Success! Write completed without any errors."]
            else:
                raise AssertionError, "Failed! Error expected but no error occurred. Label: {}".format(label)

        except soem.SOEM_SDO_Exception as e:
            if response == None:  # expected no error
                raise AssertionError, "Failed! Error not expected but error occurred; error received: {}; error code: {}; Label: {}".format(
                    str(self.master.err2string(e.err_type, e.err_code)), hex(e.err_code), label)
            else:  # expected error
                if e.err_code == response:
                    return ["True", "Success! Error received matches expected error; error received: "
                            + str(self.master.err2string(e.err_type, e.err_code)) + "; error code: " + hex(
                        e.err_code)]
                else:
                    raise AssertionError, "Failed! Error received does not match expected error; error received: {}; error code: {}; Label: {}".format(
                        str(self.master.err2string(e.err_type, e.err_code)), hex(e.err_code), label)

        except soem.SOEM_Exception as e:
            raise AssertionError, "Failed! Non-SDO error occurred; {}; Label: {}".format(str(e.message), label)

    '''
    Requests PDO Read or Write function in SOEM Wrapper class 
    Returns a result as a list: List[0] = success or fail indicator, List[1] = return message  
    '''

    def read_PDO(self, slave_num, mapped_index, val_type, value, response, label, deviation):
		
        if slave_num > self.slave_count:
            raise AssertionError, "Failed! Slave number is greater than # of found slaves."

        val_type = self.type_dictionary[val_type]
        try:
            rval = self.master.PDOIn_read(slave_num, mapped_index, val_type)

            if deviation == None:    
                 pass    
            else:
                lowerDev = value - deviation
                upperDev = value + deviation
                if lowerDev < rval < upperDev:
                    value = rval
                else:
                    raise AssertionError, "Failed! Expected: {} is not within {} of Actual: {}".format(rval, deviation,
                                                                                                       value)

            if response == None:  # expected valid response + no error expected
                try:
                    value = type(rval)(value)
                except:
                    raise AssertionError, "Failed! Could not typecast expected value to received value type; Value received: {}; Label: {}".format(str(rval), label)
                if rval == value:
                     return str(rval)
                else:
                    raise AssertionError, "Failed! Value received does not match expected value; Value received: {}; Label: {}".format(str(rval), label)
            else:  # expected error
                raise AssertionError, "Failed! Exception error expected but (valid) Value received; Value received: {}; Label: {}".format(str(rval), label)

        except soem.SOEM_PDO_Exception as e:
            if response == None:  # expected valid response + no error
                raise AssertionError, "Failed! Error not expected but error occurred; error received: {}; error code: {}; Label: {}".format(str(self.master.err2string(e.err_type, e.err_code)), hex(e.err_code), label)
            else:  # expected error
                if e.err_code == response:
                    return ["True", "Success! Error received matches expected error; error received: "
                            + str(self.master.err2string(e.err_type, e.err_code)) + "; error code: " + hex(
                        e.err_code)]
                else:
                    raise AssertionError, "Failed! Error received does not match expected error; error received : {}; error code: {}; Label: {}".format(str(self.master.err2string(e.err_type, e.err_code)), hex(e.err_code), label)

        except soem.SOEM_Exception as e:
            raise AssertionError, "Failed! Non-PDO error occurred {}; Label: {}".format(str(e.message), label)

    def write_PDO(self, slave_num, mapped_index, val_type, value, response, label):
        if slave_num > self.slave_count:
            raise AssertionError, "False", "Failed! Slave number is greater than # of found slaves."

        val_type = self.type_dictionary[val_type]
        try:
            self.master.PDOOut_write(slave_num, mapped_index, val_type, value)

            if response == None:  # expected valid response + no error expected
                return ["True", "Success! Write completed without any errors."]
            else:
                raise AssertionError, "Failed! Error expected but no error occurred."

        except soem.SOEM_PDO_Exception as e:
            if response == None:  # expected no error
                raise AssertionError, "Failed! Error not expected but error occurred; error received: {}; error code: {}; Label: {}".format(str(self.master.err2string(e.err_type, e.err_code)), hex(e.err_code), label)
            else:  # expected error
                if e.err_code == response:
                    return ["True", "Success! Error received matches expected error; error received: "
                            + str(self.master.err2string(e.err_type, e.err_code)) + "; error code: " + hex(
                        e.err_code)]
                else:
                    raise AssertionError, "Failed! Error received does not match expected error; error received: {}; error code: {}; Label: {}".format(str(self.master.err2string(e.err_type, e.err_code)), hex(e.err_code), label)

        except soem.SOEM_Exception as e:
            raise AssertionError, "Failed! Non-PDO error occurred; {}; Label: {}".format(str(e.message), label)
