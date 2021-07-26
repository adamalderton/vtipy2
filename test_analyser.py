# This is a script to test the connection of a physically connected analyser, and check that it is outputting reasonable numbers.
# Analyser choice is taken from hardware_setup.json, as made in vtipy2_setup.py.
# An impedance sweep is then carried out, and a basic Nyquist is shown, such that a user can validate the results.
# Adaptation of this script is encouraged.

import os, sys, json, datetime, ctypes, time

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import style
style.use("ggplot")

from hardware import virtual

def main():
    # Gets analyser choice, carries out one impedance sweep, and plots results.
    
    # Get and initialise analyser from setup
    if not os.path.isfile("hardware_setup.json"):
        raise Exception("hardware_setup.json not found, please run vtipy2_setup.py.")

    with open("hardware_setup.json") as jf:
        hardware_setup = json.load(jf)
        
        if hardware_setup["analyser"]["name"] == "virtual":
            analyser = virtual.analyser()
        elif hardware_setup["analyser"]["name"] == "1260":
            from hardware.solartron import solartron1260
            analyser = solartron1260()
        elif hardware_setup["analyser"]["name"] == "SP_200":
            from hardware.biologic import SP_200
            analyser = SP_200()
        else:
            raise Exception("Disagreement on names between vtipy2 and test_analyser.")
    print("\tDetected analyser: {}\n".format(analyser.name))

    # Take inputs for test impedance sweep
    try:
        voltage = float(input("\tEnter a voltage for a test impedance sweep: (mV):\n"))
        fmin = float(input("\tEnter the minimum frequency (Hz):\n"))
        fmax = float(input("\tEnter the maximum frequency: (Hz):\n"))
        ppd = int(input("\tEnter the points-per-decade:\n"))
    except:
        raise Exception("Invalid inputs.")
    
    def sanity_check():
        if not analyser.min_V <= voltage <= analyser.max_V:
            return False, "Voltage not valid"
        if fmin >= fmax:
            return False, "fmin >= fmax"
        if fmin < analyser.min_frequency:
            return False, "Minimum Frequency not valid"
        if fmax > analyser.max_frequency:
            return False, "Maximum Frequency not valid"
        if ppd < 1:
            return False, "PPD not valid"
        if not isinstance(ppd, int):
            return False, "PPD not int"
        
        return True, None
    
    sane, message = sanity_check()
    
    if not sane:
        raise Exception(message)
    
    # Carry out impedance sweep, if virtual analyser or Solartron 1260
    if isinstance(analyser, virtual.analyser) or isinstance(analyser, solartron1260):
        print("\tInitialising...")
        # Send command specifying voltage amplitude for this ramp
        analyser.send("VA " + str(float(voltage)))
        
        # Create data file for sweep and write sweep file header
        file_path = "test_analyser_data.txt"

        with open(file_path, "w") as f:
            f.write("sweep_num, date, time, Tcell, setT, ramp_direction\n")
            f.write("test, test, test, test, test, test\n")
        
        numpoints = int(ppd * (np.log10(fmax) - np.log10(fmin)))
        frange_full = np.logspace(*np.log10( (fmin, fmax) ), num = numpoints)
        frange = list(frange_full[::-1])
        
        print("\tPerfoming sweep...")
        for f in frange:
            print("{:.2e} Hz    {} / {}".format(f, i, numpoints))
            try:
                result = analyser.measure_frequency(f)
            except:
                result = analyser.measure_frequency(1.)
                result = analyser.measure_frequency(f)
            
            # Write result of measurement to file, discarding trailing zeroes
            result = ",".join(result.split(",")[:4])
            with open(file_path, "a") as f:
                f.write(result + "\n")

    # Perform impedance sweep if analyser is biologic SP_200
    elif isinstance(analyser, SP_200):
        print("\tInitialising...")
        # Create data file for sweep and write sweep file header
        file_path = "test_analyser_data.txt"
        with open(file_path, "w") as f:
            f.write("sweep_num, date, time, Tcell, setT, ramp_direction\n")
            f.write("test, test, test, test, test, test\n")

        numpoints = int(ppd * (np.log10(fmax) - np.log10(fmin)))
        frange_full = np.logspace(*np.log10( (fmin, fmax) ), num = numpoints)
        frange = list(frange_full[::-1])
        
        # Set up parameters
        params = [
            ["float", 0, b"Final_frequency", fmin, 0],
            ["float", 1, b"Initial_frequency", fmax, 0],
            ["bool", 2, b"sweep", False, 0], #logarithmic sweep
            ["float", 3, b"Amplitude_Voltage", voltage, 0], 
            ["int", 4, b"Frequency_number", numpoints, 0],
            ["int", 5, b"Average_N_times", 1, 0],
            ["bool", 6, b"Correction", False, 0],
            ["float", 7, b"Wait_for_steady", 0.1, 0]
        ]
        
        params_nb = len(params)
        EccParamArrayType = analyser.EccParamType * params_nb
        analyser.EccParamArray = EccParamArrayType()
        analyser.EccParams = analyser.EccParamsType()
        analyser.EccParams.len = ctypes.c_int32(params_nb)
        analyser.EccParams.pParams = ctypes.cast(analyser.EccParamArray, ctypes.c_void_p)

        # Pass parameters
        for param in params:
            success = analyser.define_parameter(param[0], param[1], param[2], param[3], param[4])
            if success == False:
                raise Exception("Error defining parameter: {}".format(param[2]))
            time.sleep(0.2)

        # Load technique
        error = analyser.BL_LoadTechnique(analyser.glob_conn_id, ctypes.c_ubyte(analyser.cfg_channel), b"peis4.ecc", analyser.EccParams, True, True, True)
        if error != analyser.ErrorCodeEnum.ERR_NOERROR:
            raise Exception("BL_LoadTechnique error. Errcode = {}".format(error))
        
        # Start channel
        error = analyser.BL_StartChannel(analyser.glob_conn_id, ctypes.c_ubyte(analyser.cfg_channel))
        if error != analyser.ErrorCodeEnum.ERR_NOERROR:
            raise Exception("BL_StartChannel error. Errcode = {}".format(error))

        # Main loop
        print("\tPerforming sweep...")
        for i in range(numpoints):
            print("{:.2e} Hz    {} / {}".format(frange[i], i, numpoints))
            result, PI = analyser.get_result()
            with open(file_path, "a") as f:
                if PI == 1: # if data is from process index 1 (process of interest), store the data
                    f.write(",".join(str(x) for x in result) + "\n")

    else:
        raise Exception("Analyser could not be recognised for an impedance sweep.")
    
    # Make Nyquist plot
    print("\tSweep complete, creating plot...")
    
    # Get data from file (file can be safely deleted by user when no longer needed, will be overwritten if this script is run again)
    data = np.genfromtxt("test_analyser_data.txt", skip_header = 2, delimiter = ",")
    re = data[:,1]*np.cos(data[:,2]*np.pi*2./360.)
    im = data[:,1]*np.sin(data[:,2]*np.pi*2./360.)
    
    # Change to kiloohms
    re = re / 1000
    im = im / 1000
    
    plt.plot(re, -im, "o")
    
    plt.title("Nyquist Plot")
    plt.xlabel("Re[Z] / k\u03A9")
    plt.ylabel("-Im[Z] / k\u03A9")
    
    plt.show()
    
    print("\tTest complete.")
    
if __name__ == "__main__":
    main()