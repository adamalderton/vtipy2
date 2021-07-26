# This is an adapted and tailorised version of python usage of the biologic EC-LAB development package, by biologic.
# The SP_200 class allows for the programatic control of a potentio electrochemical impedance spectroscopy technique, carried out on a biologic SP-200 unit
# The class should be readily adaptable to carry out other techiques on the same unit, however different parameters would have to be passed.
# Please see the documentation for the EC-LAB development package foe details on how to use the package.

import ctypes
import sys
import time
import threading
import os
import datetime

class eclib(object):
    # Holds functionality and datatypes to leverage the EC-LAB development package 

    # Constants
    UNITS_NB = 16

    # EC-Lab DLL (private)
    __dll = ctypes.CDLL("EClib.dll") # EClib64.dll is the 64 bit version, EClib.dll is the 32 bit version. The 64 bit version is untested with python.

    # Device Info Structure
    class DeviceInfoType(ctypes.Structure):
        _fields_ = [("DeviceCode", ctypes.c_int32),
                    ("RAMSize", ctypes.c_int32),
                    ("CPU", ctypes.c_int32),
                    ("NumberOfChannels", ctypes.c_int32),
                    ("NumberOfSlots", ctypes.c_int32),
                    ("FirmwareVersion", ctypes.c_int32),
                    ("FirmwareDate_yyyy", ctypes.c_int32),
                    ("FirmwareDate_mm", ctypes.c_int32),
                    ("FirmwareDate_dd", ctypes.c_int32),
                    ("HTdisplayOn", ctypes.c_int32),
                    ("NbOfConnectedPC", ctypes.c_int32)]

    # Current Values Type
    class CurrentValuesType(ctypes.Structure):
        _fields_ = [("State", ctypes.c_int32),
                    ("MemFilled", ctypes.c_int32),
                    ("TimeBase", ctypes.c_float),
                    ("Ewe", ctypes.c_float),
                    ("EweRangeMin", ctypes.c_float),
                    ("EweRangeMax", ctypes.c_float),
                    ("Ece", ctypes.c_float),
                    ("EceRangeMin", ctypes.c_float),
                    ("EceRangeMax", ctypes.c_float),
                    ("Eoverflow", ctypes.c_int32),
                    ("I", ctypes.c_float),
                    ("IRange", ctypes.c_int32),
                    ("Ioverflow", ctypes.c_int32),
                    ("ElapsedTime", ctypes.c_float),
                    ("Freq", ctypes.c_float),
                    ("Rcomp", ctypes.c_float),
                    ("Saturation", ctypes.c_int32),
                    ("OptErr", ctypes.c_int32),
                    ("OptPos", ctypes.c_int32)]

    # Data Information Type
    class DataInfosType(ctypes.Structure):
        _fields_ = [("IRQskipped", ctypes.c_int32),
                    ("NbRows", ctypes.c_int32),
                    ("NbCols", ctypes.c_int32),
                    ("TechniqueIndex", ctypes.c_int32),
                    ("TechniqueID", ctypes.c_int32),
                    ("ProcessIndex", ctypes.c_int32),
                    ("loop", ctypes.c_int32),
                    ("StartTime", ctypes.c_double),
                    ("MuxPad", ctypes.c_int32)]

    # Data buffer Type
    DataBufferType = ctypes.c_uint32 * 1000

    # ECC parameter structure
    class EccParamType(ctypes.Structure):
        _fields_ = [("ParamStr", 64 * ctypes.c_byte),
                    ("ParamType", ctypes.c_int32),
                    ("ParamVal", ctypes.c_uint32),
                    ("ParamIndex", ctypes.c_int32)]

    # ECC parameters structure
    class EccParamsType(ctypes.Structure):
        _fields_ = [("len", ctypes.c_int32),
                    ("pParams", ctypes.c_void_p)]

    # Array of units
    UnitsType = ctypes.c_byte * UNITS_NB

    # Array of results
    ResultsType = ctypes.c_int32 * UNITS_NB

    # Error Enumeration
    class ErrorCodeEnum(object):
        ERR_NOERROR = 0

    # Technique Parameter Type Enumeration
    class ParamTypeEnum(object):
        PARAM_INT = 0
        PARAM_BOOLEAN = 1
        PARAM_SINGLE = 2

    BL_GetUSBdeviceinfos = __dll["BL_GetUSBdeviceinfos"]
    BL_GetUSBdeviceinfos.restype= ctypes.c_bool

    # ErrorCode BL_ConvertNumericIntoSingle(int num, ref float psgl)
    BL_ConvertNumericIntoSingle = __dll["BL_ConvertNumericIntoSingle"]
    BL_ConvertNumericIntoSingle.restype = ctypes.c_int

    # ErrorCode BL_Connect(string server, byte timeout, ref int connection_id, ref DeviceInfo pInfos)
    BL_Connect = __dll["BL_Connect"]
    BL_Connect.restype = ctypes.c_int
    
    # ErrorCode BL_Disconnect(int ID)
    BL_Disconnect = __dll["BL_Disconnect"]
    BL_Disconnect.restype = ctypes.c_int
    
    # ErrorCode BL_TestConnection(int ID)
    BL_TestConnection = __dll["BL_TestConnection"]
    BL_TestConnection.restype = ctypes.c_int

    # ErrorCode BL_LoadFirmware(int ID, byte[] pChannels, int[] pResults, byte Length, bool ShowGauge, bool ForceReload, string BinFile, string XlxFile)
    BL_LoadFirmware = __dll["BL_LoadFirmware"]
    BL_LoadFirmware.restype = ctypes.c_int

    # bool BL_IsChannelPlugged(int ID, byte ch)
    BL_IsChannelPlugged = __dll["BL_IsChannelPlugged"]
    BL_IsChannelPlugged.restype = ctypes.c_bool

    # ErrorCode BL_GetChannelsPlugged(int ID, byte[] pChPlugged, byte Size)
    BL_GetChannelsPlugged = __dll["BL_GetChannelsPlugged"]
    BL_GetChannelsPlugged.restype = ctypes.c_int

    # ErrorCode BL_GetMessage(int ID, byte ch, [MarshalAs(UnmanagedType.LPArray)] byte[] msg, ref int size)
    BL_GetMessage = __dll["BL_GetMessage"]
    BL_GetMessage.restype = ctypes.c_int

    # ErrorCode BL_LoadTechnique(int ID, byte channel, string pFName, EccParams pparams, bool FirstTechnique, bool LastTechnique, bool DisplayParams)
    BL_LoadTechnique = __dll["BL_LoadTechnique"]
    BL_LoadTechnique.restype = ctypes.c_int

    # ErrorCode BL_DefineSglParameter(string lbl, float value, int index, IntPtr pParam)
    BL_DefineSglParameter = __dll["BL_DefineSglParameter"]
    BL_DefineSglParameter.restype = ctypes.c_int

    # ErrorCode BL_DefineSglParameter(string lbl, int value, int index, IntPtr pParam)
    BL_DefineIntParameter = __dll["BL_DefineIntParameter"]
    BL_DefineIntParameter.restype = ctypes.c_int

    # ErrorCode BL_DefineSglParameter(string lbl, bool value, int index, IntPtr pParam)
    BL_DefineBoolParameter = __dll["BL_DefineBoolParameter"]
    BL_DefineBoolParameter.restype = ctypes.c_int

    # ErrorCode BL_TestCommSpeed(int ID, byte channel, ref int spd_rcvt, ref int spd_kernel)
    BL_TestCommSpeed = __dll["BL_TestCommSpeed"]
    BL_TestCommSpeed.restype = ctypes.c_int

    # ErrorCode BL_StartChannel(int ID, byte channel)
    BL_StartChannel = __dll["BL_StartChannel"]
    BL_StartChannel.restype = ctypes.c_int
    
    # ErrorCode BL_StopChannel(int ID, byte channel)
    BL_StopChannel = __dll["BL_StopChannel"]
    BL_StopChannel.restype = ctypes.c_int

    # ErrorCode BL_GetData(int ID, byte channel, [MarshalAs(UnmanagedType.LPArray, SizeConst=1000)] int[] buf, ref DataInfos pInfos, ref CurrentValues pValues)
    BL_GetData = __dll["BL_GetData"]
    BL_GetData.restype = ctypes.c_int

class SP_200(eclib):
    def __init__(self):
        self.name = "Biologic SP-200"
        
        # Hardware specifications
        self.minimum_frequency = 1e-5 # Hz
        self.maximum_frequency = 7e6 # Hz
        self.min_V = 1e-6 #micro volt, although data will likely be terrible at this amplitude
        self.max_V = 1e4 # 10V (10,000 mV), absolute maximum but not entirely recomended
        
        # Configuration
        self.cfg_conn_ip = b"USB0" # Can be changed to an IP if controlling remotely, or changed to a different USB num if multiple units are connected
        self.cfg_conn_timeout = 10 # Timeout for the connection channel
        self.cfg_channel = 0
        self.glob_conn_id = ctypes.c_int(-1)

        # Connect to instrument (call BL_CONNECT)
        device_info = self.DeviceInfoType()
        error = self.BL_Connect(ctypes.c_char_p(self.cfg_conn_ip), ctypes.c_byte(self.cfg_conn_timeout), ctypes.byref(self.glob_conn_id), ctypes.byref(device_info))
        if error != self.ErrorCodeEnum.ERR_NOERROR:
            raise Exception("Error connecting to instrument. Errcode = {}".format(error))
        
        # Get connected channels
        units = self.UnitsType()
        error = eclib.BL_GetChannelsPlugged(self.glob_conn_id, ctypes.byref(units), ctypes.c_ubyte(self.UNITS_NB))
        if error != self.ErrorCodeEnum.ERR_NOERROR:
            raise Exception("Error retrieving connected channel(s). Errcode = {}".format(error))
        
        # Load firmware
        results = self.ResultsType()
        error = self.BL_LoadFirmware(self.glob_conn_id, units, ctypes.byref(results), ctypes.c_ubyte(self.UNITS_NB), False, True, None, None)
        if error != self.ErrorCodeEnum.ERR_NOERROR:
            raise Exception ("Error loading firmware. Errcode = {}".format(error))
    
    def disconnect(self):
        error = self.BL_StopChannel(ctypes.c_int32(0), 0)
        if error != self.ErrorCodeEnum.ERR_NOERROR:
            raise Exception ("Error closing channel. Errcode = {}".format(error))
        error = self.BL_Disconnect(ctypes.c_int32(0))
        if error != self.ErrorCodeEnum.ERR_NOERROR:
            raise Exception ("Error disconnecting. Errcode = {}".format(error))

    def define_parameter(self, p_type, p_index, label, value, index):
        # Used to define parameters for a technique.
        # p_type defines the type of the parater
        # p_index is the index of the parameter by which it is passed, unique to each parameter
        # label is the "name" of the parameter, as defined in the development package, passed as bytes.
        # value is the value the parameter should take
        # index is the parameter index when related to multi-step parameters. Is usually 0 unless in the mentioned case.
        
        # Defined parameters are then stored in self.EccParamArray
        # Returns False if an error is encountered, otherwise True.
        
        if p_type == "float":
            if not isinstance(value, float):
                return False
            error = self.BL_DefineSglParameter(ctypes.c_char_p(label), ctypes.c_float(value), ctypes.c_int32(index), ctypes.byref(self.EccParamArray[p_index]))
            if error != self.ErrorCodeEnum.ERR_NOERROR:
                return False
            return True
        elif p_type == "int":
            if not isinstance(value, int):
                return False
            error = self.BL_DefineIntParameter(ctypes.c_char_p(label), ctypes.c_int32(value), ctypes.c_int32(index), ctypes.byref(self.EccParamArray[p_index]))
            if error != self.ErrorCodeEnum.ERR_NOERROR:
                return False
            return True
        elif p_type == "bool":
            if not isinstance(value, bool):
                return False
            error = self.BL_DefineBoolParameter(ctypes.c_char_p(label), ctypes.c_bool(value), ctypes.c_int32(index), ctypes.byref(self.EccParamArray[p_index]))
            if error != self.ErrorCodeEnum.ERR_NOERROR:
                return False
            return True
        else:
            return False

    def measure_impedance_process(self, label, ramp, sweep_num, Tcell, experiment_name, temp_interval_num):
        # If directory for this temperature interval does not exist, create it
        dir_name = "experiments//{}//{}//{}".format(experiment_name, "{}_{}".format(ramp.num, "up" if ramp.up else "down"), "{}C".format(ramp.temps[temp_interval_num]))
        if not os.path.isdir(dir_name):
            os.mkdir(dir_name)
        
        # Create data file for sweep and write sweep file header
        file_path = "{}//{}".format(dir_name, "{}C_sweep_{}.txt".format(ramp.temps[temp_interval_num], sweep_num + 1))
        now = datetime.datetime.now()
        with open(file_path, "w") as f:
            f.write("sweep_num, date, time, Tcell, setT, ramp_direction\n")
            f.write( "{}, {}, {}, {}, {}, {}\n".format(sweep_num, now.strftime("%Y/%m/%d"), now.strftime("%H:%M:%S"), Tcell, ramp.end_temp, "up" if ramp.up else "down"))
        
        # Set up parameters
        params = [
            ["float", 0, b"Final_frequency", ramp.fmin, 0],
            ["float", 1, b"Initial_frequency", ramp.fmax, 0],
            ["bool", 2, b"sweep", False, 0], #logarithmic sweep
            ["float", 3, b"Amplitude_Voltage", ramp.voltage, 0], 
            ["int", 4, b"Frequency_number", ramp.numpoints, 0],
            ["int", 5, b"Average_N_times", 1, 0],
            ["bool", 6, b"Correction", False, 0],
            ["float", 7, b"Wait_for_steady", 0.1, 0]
        ]
        
        params_nb = len(params)
        EccParamArrayType = self.EccParamType * params_nb
        self.EccParamArray = EccParamArrayType()
        self.EccParams = self.EccParamsType()
        self.EccParams.len = ctypes.c_int32(params_nb)
        self.EccParams.pParams = ctypes.cast(self.EccParamArray, ctypes.c_void_p)

        # Pass parameters
        for param in params:               # p_type   # p_index # label  # value   # index
            success = self.define_parameter(param[0], param[1], param[2], param[3], param[4])
            if success == False:
                raise Exception("Error defining parameter: {}".format(param[2]))
            time.sleep(0.2)

        # Load technique (peis4.ecc is the file for potentio electrochemical impedance spectroscopy)
        error = self.BL_LoadTechnique(self.glob_conn_id, ctypes.c_ubyte(self.cfg_channel), b"peis4.ecc", self.EccParams, True, True, True)
        if error != self.ErrorCodeEnum.ERR_NOERROR:
            raise Exception("BL_LoadTechnique error. Errcode = {}".format(error))
        
        # Start channel
        error = self.BL_StartChannel(self.glob_conn_id, ctypes.c_ubyte(self.cfg_channel))
        if error != self.ErrorCodeEnum.ERR_NOERROR:
            raise Exception("BL_StartChannel error. Errcode = {}".format(error))

        # Main loop
        for i in range(ramp.numpoints):
            label["text"] = "{:.2e} Hz    {} / {}".format(ramp.frange[i], i, ramp.numpoints)
            result, PI = self.get_result()
            with open(file_path, "a") as f:
                if PI == 1: # if data recieved is from process index 1 (process of interest), store the data
                    f.write(",".join(str(x) for x in result) + "\n")

    def get_result(self):
        # Gets data presented by the biologic unit, then processes it to return a format which should make analysis easier
        # Returns a list being [frequency, impedance magnitude, impedance argument], and the index of the process which returned the original data
        
        data = []
        while not data: # Continually ping data store for process 1 until it is not empty
            # Retrieve data
            buffer = self.DataBufferType()
            infos = self.DataInfosType()
            values = self.CurrentValuesType()
            error = self.BL_GetData(self.glob_conn_id, ctypes.c_ubyte(self.cfg_channel), ctypes.byref(buffer), ctypes.byref(infos), ctypes.byref(values))
            if error != self.ErrorCodeEnum.ERR_NOERROR:
                raise Exception("BL_GetData error. Errcode = {}".format(error))
            
            if infos.ProcessIndex == 1:
                for i in range(infos.NbRows * infos.NbCols):
                    receive_data = ctypes.c_float(0.0)
                    error = self.BL_ConvertNumericIntoSingle(buffer[i], ctypes.byref(receive_data))
                    if error != self.ErrorCodeEnum.ERR_NOERROR:
                        raise Exception("BL_ConvertNumericIntoSingle error. Errcode = {}".format(error))
                    data.append(receive_data.value)
        
        result = [round(data[0], 2), round(abs(data[1]) / abs(data[2]), 2), round(data[3], 2)] # [freq, |z| = |V| / |I|, arg(z)]
        return result, int(infos.ProcessIndex)
        
    def measure_impedance(self, label, ramp, sweep_num, Tcell, experiment_name, temp_interval_num):
        # Begin python thread to measure impedances
        process = threading.Thread(
            target = self.measure_impedance_process,
            args = (label, ramp, sweep_num, Tcell, experiment_name, temp_interval_num),
            daemon = True
        )
        process.start()
        return process