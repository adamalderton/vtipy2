# This is user interface to perform variable temperature impedance measurements
# using a heating stage and an impedance analyser. This was created as part of 
# the FUSE studentship (Faraday Institute) during the summer of 2020. It is 
# written by Adam Alderton (aa816@exeter.ac.uk, adam.alderton@yahoo.co.uk) 
# with supervision and assistance from Josh Tuffnell (jmt83@cam.ac.uk).
# Please consult the README before using this software.

import sys, os, time, datetime, json, shutil

import numpy as np
import threading
import visa
import tkinter as tk
from tkinter import font as tkfont

import matplotlib
import matplotlib.pyplot as plt
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as animation
from matplotlib import style
from matplotlib.figure import Figure
style.use("ggplot")

from hardware import virtual
from hardware import linkam

# Add current directory to search path windows will take to find .dll files
os.add_dll_directory("{}".format(os.getcwd()))

class Ramp():
    # This class is to store data relevant to a temperature ramp that may be required of the stage.
    # Sequential ramps should be stored in a list of Ramp() instances.
    
    def __init__(self, num, start_temp, end_temp, rate, interval, min_holdtime, voltage, fmin, fmax, ppd, num_sweeps, sweep_delay, scan_at_first_T):
        self.num = num                          # Integer: Stores the index of the ramp for future reference.
        self.interval = interval                # Float: The temperature by which to change in an interval
        self.start_temp = start_temp            # Float: Starting temperature, (°C)
        self.end_temp = end_temp                # Float: Temperature to reach in num_intervals intervals, (°C)
        self.rate = rate                        # Float: The rate at which to change temperature, (°C/min)
        self.min_holdtime = min_holdtime        # Float: The minimum hold time to hold at each interval BEFORE measuring impedance (seconds). Temperature is held automatically while impedances are measured.
        self.voltage = voltage                  # Float: The A.C voltage amplitude (mV)
        self.fmin = fmin                        # Float: Minimum frequency for frequency sweep (Hz)
        self.fmax = fmax                        # Float: Maximum frequency for frequency sweep (Hz)
        self.ppd = ppd                          # Integer: Points per decade at which to measure impedance
        self.num_sweeps_at_T = num_sweeps       # Integer: Number of impedance measurements to take at each temperature interval
        self.sweep_delay = sweep_delay          # Integer: Time (seconds) between each impedance sweep
        self.scan_at_first_T = scan_at_first_T  # String: y/n, whether to scan at first temperature in ramp. Useful to not double scan if ramp starts at same temperature as previous. Becomes bool below.

        # Calculate "up", describes direction of ramp
        if self.start_temp <= self.end_temp:
            self.up = True
        else:
            self.up = False
        
        # If ramp is downwards, set cooling rate maximum of 15 C/min
        if self.up == False and self.rate > 15:
            self.rate = 15
        
        # Calculate num_intervals, Number of intervals in which to change temperature. At each interval, hold by holdtime.
        self.num_intervals = abs(int((self.end_temp - self.start_temp) / self.interval))
        if self.up == False:
            self.interval = abs(self.interval) * -1
        
        # Calculate temperatures (°C)
        self.temps = []
        for i in range(self.num_intervals + 1):
            self.temps.append(round(self.start_temp + (i * self.interval), 2))
        
        # If the first temperature in a ramp should be scanned at
        if self.scan_at_first_T == "y":
            self.scan_at_first_T = True
        elif self.scan_at_first_T == "n":
            self.scan_at_first_T = False
            self.temps.pop(0) # remove first temperature, such that it's not scanned at
        else:
            # If invalid value was input, the sanity check will pick this up
            self.scan_at_first_T = None

        # Calculate numpoints and frequency range
        self.numpoints = int(self.ppd * (np.log10(self.fmax) - np.log10(self.fmin)))
        frange_full = np.logspace(*np.log10( (self.fmin, self.fmax) ), num = self.numpoints)
        self.frange = list(frange_full[::-1])


class vtipy2(tk.Tk):
    # Root tk instance frame which other pages (frames) come from
    def __init__(self):
        # First loads hardware configuration, then switches to StartPage
        tk.Tk.__init__(self)
        self.check_hardware_config()
        self._frame = None
        self.switch_frame(StartPage)

    def switch_frame(self, frame_class):
        new_frame = frame_class(self)
        if self._frame is not None:
            self._frame.destroy()
        self._frame = new_frame
        self._frame.pack()

    def check_hardware_config(self):
        # Checks hardware_setup.json exists and that setup was successful.
        # Then uses information in hardware_setup.json to intialise stage and analyser.
        
        if not os.path.isfile("hardware_setup.json"):
            # Delete hardware config such that it is not unsafely reused
            os.remove("hardware_setup.json")
            raise Exception("hardware_setup.json not found, please run vtipy2_setup.py.")
        
        with open("hardware_setup.json") as jf:
            hardware_setup = json.load(jf)
            
            if hardware_setup["successful"] != True:
                raise Exception("Hardware setup (from vtipy2_setup.py) was unsuccessful.")
            
            global stage, analyser
            
            # add if statements here if new hardware is implemented (also add relevant imports)
            if hardware_setup["stage"]["name"] == "virtual":
                stage = virtual.stage()
            elif hardware_setup["stage"]["name"] == "HFS350":
                stage = linkam.HFS350()
            elif hardware_setup["stage"]["name"] == "TS1000":
                stage = linkam.TS1000()
            else:
                raise Exception("Disagreement on names between vtipy2 and vtipy2_setup.")
            
            if hardware_setup["analyser"]["name"] == "virtual":
                analyser = virtual.analyser()
            elif hardware_setup["analyser"]["name"] == "1260":
                from hardware.solartron import solartron1260
                analyser = solartron1260()
            elif hardware_setup["analyser"]["name"] == "SP_200":
                from hardware.biologic import SP_200
                analyser = SP_200()
            else:
                raise Exception("Disagreement on names between vtipy2 and vtipy2_setup.")
        
        # Delete hardware config such that it is not unsafely reused
        os.remove("hardware_setup.json")


class StartPage(tk.Frame):
    # First page of vtipy2. 
    # Displays initialised stage and analyser, and gives entries for a name for the experiment and some short notes.
    
    def __init__(self, master):
        tk.Frame.__init__(self, master)
        tk.Label(self, text = "Adam Alderton - 2020", anchor = tk.W, justify = tk.LEFT, width = 55).pack()
        
        tk.Label(self, text = "\nWelcome to vtipy2!\n", font = "Helvetica 24 bold").pack()
        
        tk.Label(self, text = "Please consult the README before using this sofware.\n"
                 "The hardware configuration was successfully loaded!\n", font = tkfont.Font(size = 12)).pack()
        tk.Label(self, text = "STAGE: {}\n"
                 "ANALYSER: {}\n".format(stage.name, analyser.name), font = tkfont.Font(size = 12), justify = tk.LEFT).pack()
        tk.Label(self, text = "Ensure correct stage is connected!\n\n"
                 "To begin, please enter a name for the experiment below.\n"
                 "Optional: Create short notes in the larger box below.\n",
                 font = tkfont.Font(size = 12)).pack()
        
        ent_exp_name = tk.Entry(self, width = 30, font = tkfont.Font(size = 12), relief = tk.GROOVE, borderwidth = 3, justify = tk.CENTER)
        ent_exp_name.insert(0, "Name")
        ent_exp_name.pack()
        
        ent_exp_notes = tk.Text(self, height = 3, width = 40, font = tkfont.Font(size = 12), relief = tk.GROOVE, borderwidth = 3)
        ent_exp_notes.pack(pady = 5)
        
        tk.Button(self, text = "Start", font = tkfont.Font(size = 12), pady = 5, padx = 15, command = lambda: self.start_button_func(master, ent_exp_name, ent_exp_notes)).pack(pady = 15)
    
    def start_button_func(self, master, name_entry, notes_entry):
        # Stores experiment name and notes.
        # Sets up experiment directory and creates details.json file, describing some experiment detail.
        
        
        # Get and store experiment name
        global experiment_name
        experiment_name = name_entry.get()

        # Get notes from text box
        notes = notes_entry.get("1.0", tk.END)
        
        # Create directory to store experiment files and data
        if not os.path.isdir("experiments"):
            os.mkdir("experiments")
        duplicate_num = 1 # This is to handle duplicate names of experiment
        while True:
            if not os.path.isdir("experiments\\" + experiment_name):
                os.mkdir("experiments\\" + experiment_name)
                break
            else:
                if experiment_name.split("_")[-1] == str(duplicate_num - 1):
                    experiment_name = experiment_name.split("_")[0] + "_{}".format(duplicate_num)
                else:
                    experiment_name += "_{}".format(duplicate_num)
                duplicate_num += 1
                
        
        # Store initial experiment details in a json file for easy reading
        json_handler = lambda obj: (obj.isoformat() if isinstance(obj, (datetime.datetime)) else None)
        with open("experiments\\" + experiment_name + "\\details.json", "w") as jf:
            jsondict = {"experiment_name" : experiment_name,
                        "notes" : notes,
                        "datetime" : datetime.datetime.now(),
                        "complete" : False,
                        "stage" : stage.name,
                        "analyser" : analyser.name
                        }
            jf.write(json.dumps(jsondict, indent = 4, default = json_handler))
        
        # Switch frame to RampInputPage
        master.switch_frame(RampInputPage)


class RampInputPage(tk.Frame):
    # Page to allow the input of parameters, defining a "ramp"
    # One confusing parameter may be "Scan @ first T", please see the README
    
    def __init__(self, master):
        tk.Frame.__init__(self, master)
        self.frm_form = tk.Frame()
        self.frm_form.pack()
        
        # Store ramps in list of Ramp instances
        global ramps
        ramps = []
        
        self.ramp_count = 0
        
        self.ramp_attributes = [
            "Starting Temperature (°C):",
            "End Temperature (°C):",
            "Rate (°C/min):",
            "Temperature Interval (°C):",
            "Minimum Holdtime (s):",
            "Voltage Amplitude (mV):",
            "Minimum Frequency (Hz):",
            "Maximum Frequency (Hz):",
            "Points per Decade:",
            "Sweeps at T:",
            "Sweep Delay (s):",
            "Scan @ first T:"
        ]
        
        default_entries = [
            "30.0",     # start_temp
            "60.0",     # end_temp
            "5.0",      # rate
            "10",       # interval
            "300",      # min_holdtime
            "50",       # voltage amplitude
            "1e-1",     # fmin
            "1e7",      # fmax
            "10",       # ppd
            "1",        # num_sweeps_at_T
            "300",      # sweep_delay
            "y"         # scan_at_first_t
        ]
        
        # Display labels and entries
        self.entries = []
        for i, attr in enumerate(self.ramp_attributes):
            label = tk.Label(master = self.frm_form, text = attr, font = tkfont.Font(size = 12), anchor = tk.W, justify = tk.LEFT)
            entry = tk.Entry(master = self.frm_form, width = 10, font = tkfont.Font(size = 12), justify = tk.RIGHT)
            self.entries.append(entry)
            entry.insert(0, default_entries[i])
            label.grid(row = i, column = 0, sticky = tk.W, pady = 3)
            entry.grid(row = i, column = 2, sticky = tk.E, pady = 3)
        
        # Display allowed values for each of the parameters
        tk.Label(master = self.frm_form, text = "{:.1f} \u2192 {:.1f}".format(stage.min_temp, stage.max_temp), font = tkfont.Font(size = 12), width = 12).grid(row = 0, column = 1, pady = 3) # starting temperature range
        tk.Label(master = self.frm_form, text = "{:.1f} \u2192 {:.1f}".format(stage.min_temp, stage.max_temp), font = tkfont.Font(size = 12), width = 12).grid(row = 1, column = 1, pady = 3) # end temperature range
        tk.Label(master = self.frm_form, text = "{:.1f} \u2192 {:.1f}".format(stage.min_rate, stage.max_rate), font = tkfont.Font(size = 12), width = 12).grid(row = 2, column = 1, pady = 3) # heater rate (C/min)
        tk.Label(master = self.frm_form, text = "\u2265 1", font = tkfont.Font(size = 12), width = 12).grid(row = 3, column = 1, pady = 3) # temperature interval
        tk.Label(master = self.frm_form, text = "1 \u2192 3e7", font = tkfont.Font(size = 12), width = 12).grid(row = 4, column = 1, pady = 3) # minimum holdtime
        tk.Label(master = self.frm_form, text = "{} \u2192 {}".format(analyser.min_V, analyser.max_V), font = tkfont.Font(size = 12), width = 12).grid(row = 5, column = 1, pady = 3) # minimum holdtime
        tk.Label(master = self.frm_form, text = "\u2265 {:.2e}".format(analyser.min_frequency), font = tkfont.Font(size = 12), width = 12).grid(row = 6, column = 1, pady = 3) # minimum frequency
        tk.Label(master = self.frm_form, text = "\u2264 {:.2e}".format(analyser.max_frequency), font = tkfont.Font(size = 12), width = 12).grid(row = 7, column = 1, pady = 3) # maximum frequency
        tk.Label(master = self.frm_form, text = "\u2265 1", font = tkfont.Font(size = 12), width = 12).grid(row = 8, column = 1, pady = 3) # ppd
        tk.Label(master = self.frm_form, text = "\u2265 0", font = tkfont.Font(size = 12), width = 12).grid(row = 9, column = 1, pady = 3) # num sweeps at T
        tk.Label(master = self.frm_form, text = "\u2265 5", font = tkfont.Font(size = 12), width = 12).grid(row = 10, column = 1, pady = 3) # sweep delay
        tk.Label(master = self.frm_form, text = "y/n", font = tkfont.Font(size = 12), width = 12).grid(row = 11, column = 1, pady = 3) # sweep delay

        self.frm_buttons = tk.Frame()
        self.frm_buttons.pack(fill = tk.X, padx = 5, pady = 5)

        # Finish button
        btn_finish = tk.Button(master = self.frm_buttons, text = "Finish", font = tkfont.Font(size = 12), command = lambda: self.save_ramps(master))
        btn_finish.pack(side = tk.RIGHT, padx = 10)
        
        # Add ramp button
        btn_ramp = tk.Button(master = self.frm_buttons, text = "Create Ramp", font = tkfont.Font(size = 12), command = self.input_ramp)
        btn_ramp.pack(side=tk.RIGHT, padx = 10)
        
        # Clear all button
        btn_clear = tk.Button(master = self.frm_buttons, text = "Clear All", font = tkfont.Font(size = 12), command = self.clear_all)
        btn_clear.pack(side = tk.LEFT, padx = 10)
        
        # Clear previous button
        btn_clear_prev = tk.Button(master = self.frm_buttons, text = "Clear Prev", font = tkfont.Font(size = 12), command = self.clear_prev)
        btn_clear_prev.pack(side = tk.LEFT, padx = 10)
        
        # Ramp counter
        self.lbl_counter = tk.Label(master = self.frm_buttons, text = "Total Ramps = 0", font = tkfont.Font(size = 12))
        self.lbl_counter.pack(side = tk.RIGHT, padx = 10)

    def increase_ramp_counter(self):
        # Whenever a ramp is input, the ramp counter at the bottom of the page is incremented
        self.ramp_count += 1
        self.lbl_counter["text"] = "Total Ramps = " + str(self.ramp_count)

    def clear_all(self):
        # All ramps can be cleared from memory, using the "clear all" button
        
        for entry in self.entries:
            entry.delete(0, tk.END)
        
        ramps.clear()
        
        self.ramp_count = 0
        self.lbl_counter["text"] = "Total Ramps = " + str(self.ramp_count)

    def clear_prev(self):
        # If it exists, the previous ramp can be cleared to be re-entered
        
        if self.ramp_count > 0:
            ramps.pop()
            self.ramp_count -= 1
            self.lbl_counter["text"] = "Total Ramps = " + str(self.ramp_count)

    def sanity_check(self, ramp):
        # Once a ramp is input, it's values are checked to be within the allowed bounds
        
        global stage, analyser
        
        if not stage.min_temp <= ramp.start_temp <= stage.max_temp:
            return False, "Start Temp"
        if not stage.min_temp <= ramp.end_temp <= stage.max_temp:
            return False, "End Temp"
        if not stage.min_rate <= ramp.rate <= stage.max_rate:
            return False, "Rate"
        if abs((ramp.end_temp - ramp.start_temp) / ramp.interval) % 1 != 0: # If interval does not divide in \Delta{T}
            return False, "(T2 - T1) / dT =/= 0"
        if abs(ramp.interval) < 1:
            return False, "Interval"
        if not 1 <= ramp.min_holdtime <= 3e7:
            return False, "Minimum Holdtime"
        if not analyser.min_V <= ramp.voltage <= analyser.max_V:
            return False, "Voltage"
        if ramp.fmin >= ramp.fmax:
            return False, "fmin >= fmax"
        if ramp.fmin < analyser.min_frequency:
            return False, "Minimum Frequency"
        if ramp.fmax > analyser.max_frequency:
            return False, "Maximum Frequency"
        if ramp.ppd < 1:
            return False, "PPD"
        if not isinstance(ramp.ppd, int):
            return False, "PPD not int"
        if ramp.num_sweeps_at_T < 0:
            return False, "#Sweeps"
        if not isinstance(ramp.num_sweeps_at_T, int):
            return False, "#Sweeps"
        if ramp.sweep_delay < 5:
            return False, "Sweep Delay"
        if ramp.scan_at_first_T not in [True, False]:
            return False, "Scan @ first T y/n"
        
        # if no errors are found, return True as the result and None as the error code
        return True, None

    def input_ramp(self):
        # On press of the "input ramp" button, the following is executed.
        # Values from the entries are taken, and checked to be both valid and sane.
        # If the ramp is a valid ramp, the ramp is stored in the global "ramps" list
        
        entries_types_valid = False
        try:
            ramp = Ramp(
                num = self.ramp_count + 1, # Such that first ramp is ramp 1 etc
                start_temp =    float(self.entries[0].get()),
                end_temp =      float(self.entries[1].get()),
                rate =          float(self.entries[2].get()),
                interval =      int(self.entries[3].get()),
                min_holdtime =  int(self.entries[4].get()),
                voltage =       float(self.entries[5].get()),
                fmin =          float(self.entries[6].get()),
                fmax =          float(self.entries[7].get()),
                ppd =           int(self.entries[8].get()),
                num_sweeps =    int(self.entries[9].get()),
                sweep_delay =   int(self.entries[10].get()),
                scan_at_first_T=str(self.entries[11].get()).lower() # take lowercase
            )
            entries_types_valid = True
        except:
            tk.messagebox.showwarning(title = "Input Error", message = "Input(s) invalid.\nPlease check inputs!")
        if entries_types_valid:
            entries_types_valid, fault = self.sanity_check(ramp)
            
            if entries_types_valid: # if input values are valid, proceed

                # Swap start_temp and end_temp entries such that user easily inputs reverse of ramp just entered
                if len(ramps) == 0:
                    n_ramp = ramp
                    new_start_temp = n_ramp.end_temp
                    new_end_temp = n_ramp.start_temp
                # If not the first ramp, details from the 2nd previous ramp are loaded into the entry boxes as standard
                # This is useful assuming the ramp temperature directions alternate, up down up down etc
                else:
                    n_ramp = ramps[-1]
                    new_start_temp = n_ramp.start_temp
                    new_end_temp = n_ramp.end_temp

                for entry in self.entries:
                    entry.delete(0, tk.END)
                
                self.entries[0].insert(0, str(new_start_temp))
                self.entries[1].insert(0, str(new_end_temp))
                self.entries[2].insert(0, str(n_ramp.rate))
                self.entries[3].insert(0, str(abs(n_ramp.interval)))
                self.entries[4].insert(0, str(n_ramp.min_holdtime))
                self.entries[5].insert(0, str(n_ramp.voltage))
                self.entries[6].insert(0, "{:.2e}".format(n_ramp.fmin))
                self.entries[7].insert(0, "{:.2e}".format(n_ramp.fmax))
                self.entries[8].insert(0, str(n_ramp.ppd))
                self.entries[9].insert(0, str(n_ramp.num_sweeps_at_T))
                self.entries[10].insert(0, str(n_ramp.sweep_delay))
                self.entries[11].insert(0, "y" if n_ramp.scan_at_first_T else "n")

                # Store ramp
                ramps.append(ramp)
                self.increase_ramp_counter()
                
            else: # if inputs are not valid
                tk.messagebox.showwarning(title = "Input Error", message = "Input(s) invalid.\nFAULT: {}\n".format(fault))

    def save_ramps(self, master):
        # Open existing details, and allocate space to store ramp data
        with open("experiments\\{}\\details.json".format(experiment_name), "r") as jf:
            jsondict = json.load(jf)
        jsondict["ramps"] = [] 

        # All the ramps are then stored in the details.json file
        # if applicable, warnings related to the cooling water and the cooling pump are displayed
        if len(ramps) > 0:
            water_warning_shown = False
            pump_warning_shown = False
            with open("experiments\\{}\\details.json".format(experiment_name), "w") as jf:
                for ramp in ramps:
                    if not water_warning_shown:
                        if ramp.end_temp >= 200 or ramp.start_temp >= 200:
                            water_warning_shown = True
                            tk.messagebox.showwarning(title = "Cooling Water Warning", message = "Temperature will go above 200°C.\nCheck cooling water before proceeding!")
                    if not pump_warning_shown:
                        if ramp.end_temp <= 22 or ramp.start_temp <= 22:
                            pump_warning_shown = True
                            tk.messagebox.showwarning(title = "Room Temperature Warning", message = "Temperature will go below 25°C.\nIf cooling pump is not connected, this will not be possible!")
                    ramp_dict = ramp.__dict__.copy()
                    del(ramp_dict["frange"]) # don't store frequency range, as fmin, fmax and ppd are already stored
                    jsondict["ramps"].append(ramp_dict)
                jf.write(json.dumps(jsondict, indent = 4))
                
                self.frm_buttons.destroy()
                self.frm_form.destroy()
                master.switch_frame(ReviewRampsPage)
        else:
            tk.messagebox.showwarning(title = "No Ramps", message = "No ramps have been input.")


class ReviewRampsPage(tk.Frame):
    # This page is to review the ramps input
    # A predicted time is generated as well as a predicted schematic of what the temperature profile will look like over time.
    
    def __init__(self, master):
        tk.Frame.__init__(self, master)
        
        self.process_ramps(master)
        
        tk.Label(self, text = "\nPlease see a schematic of the experiment above.\n\n",
                 font = tkfont.Font(size = 12)).pack()

        tk.Label(self, text = "Estimated Time = {} (H:M:S)".format(estimated_time),
                 font = tkfont.Font(size = 18)).pack()

        tk.Label(self, text = "(Assuming cooling pump is in use)\n",
                 font = tkfont.Font(size = 12)).pack()
        
        frm_buttons = tk.Frame(self)
        frm_buttons.pack()
        
        tk.Button(frm_buttons, text = "Begin Experiment", font = tkfont.Font(size = 12), pady = 5, padx = 15, command = lambda: self.begin_experiment_button_func(master)).pack(side = tk.RIGHT, padx = 5, pady = 15)
    
        tk.Button(frm_buttons, text = "Start Over", font = tkfont.Font(size = 12), pady = 5, padx = 15, command = lambda: self.start_over(master)).pack(side = tk.RIGHT, padx = 5, pady = 15)
    
        self.two_hr_warning_shown = False
    
    def start_over(self, master):
        # The matplotlib embedded plot is destroyed and the frame is switched back to the ramp input page,
        # on a "start over" button press.
        # The "ramps" list is not cleared here as it is re-initialised on the change of the frame
        
        self.plot_widget.destroy()
        master.switch_frame(RampInputPage)

    def begin_experiment_button_func(self, master):
        # On the press of the "begin experiment" button, the frame is changed to the "RunningPage" frame.
        # If the total running time is greater than two hours, a warning is shown, as the Linkam stages should not be at a high temp for more than two hours.
        
        global estimated_time
        if self.two_hr_warning_shown == True or estimated_time.total_seconds() <= 120 * 60: # two hours in seconds
            self.plot_widget.destroy()
            estimated_time = str(estimated_time)
            master.switch_frame(RunningPage)
        else:
            self.two_hr_warning_shown = True
            tk.messagebox.showwarning(title = "2 Hour Warning", message = "Estimated time is above 2 hours.\nEnsure stage is not held at a high temperature for more than 2 hours at a time over the temperature profile!")

    def process_ramps(self, master):
        # Plots an estimated schematic of the temperature profile over time, as well as calculates the estimated time for the whole experiment.
        # The time taken to take an impedance scan is roughly t(f) = 1/f + 2 for the solartron, as was measured manually and fit to by a curve.
        # For the biologic, the time was fit to a polynomial.
        # These times are then summed over for the entire frequency sweep, for every frequency sweep of every ramp.
        # The time needed to heat / cool are also calculated (assuming a cooling pump)
            
        def dt_sweep(ramp):
            t = 0
            frange = ramp.frange
            if analyser.name == "Virtual Analyser" or analyser.name == "Solartron 1260":
                t += round(1.8047 * ramp.numpoints)
                for f in frange:
                    t += round(1.0025 / f)
            elif analyser.name == "Biologic SP-200":
                t += round(1.76e1 * ramp.numpoints)
                for f in frange:
                    t += (-3.12e-8 * f**3) + (5.37e-5 * f**2) + (-3e-2 * f) + (2.36e1 * f**-1) + (-3.11e1 * f**-2) + (1.84e1 * f**-3)
            else:
                raise Exception("Analyser type unrecognised when calculating estimated time.")
            return abs((ramp.min_holdtime + (ramp.num_sweeps_at_T - 1) * ramp.sweep_delay + ramp.num_sweeps_at_T * t) / 60) # Convert to minutes
        
        global estimated_time
        estimated_time = 0 
        
        fig = plt.figure()
        ax = plt.axes()
        
        for i, ramp in enumerate(ramps):
            temps = ramp.temps
            rate = ramp.rate
            
            # Time taken at each interval to hold and sweep
            ramp_dt_sweep = dt_sweep(ramp)
            
            # Heating to initial temperature, from room temperature or previous ramp
            if ramp.num == 1:
                prev_temp = 22
            else:
                prev_temp = ramps[i - 1].temps[-1]
            dT = abs(ramp.temps[0] - prev_temp)
            dt = abs(dT / ramp.rate)
            ax.plot([estimated_time, estimated_time + dt], [prev_temp, ramp.temps[0]], color = "red" if ramp.temps[0] >= prev_temp else "blue", linewidth = 2)
            estimated_time += dt
            ax.plot([estimated_time, estimated_time + ramp_dt_sweep], [ramp.temps[0], ramp.temps[0]], ":", color = "black", linewidth = 2)
            estimated_time += ramp_dt_sweep
            
            # Now take into account heating and holding to and at intervals
            for j in range(len(temps) - 1):
                dT = abs(temps[j + 1] - temps[j])
                dt = abs(dT / rate) # in minutes
                
                # Plot temperature change line
                ax.plot([estimated_time, estimated_time + dt], [temps[j], temps[j + 1]], color = "red" if temps[j + 1] >= temps[j] else "blue", linewidth = 2)
                estimated_time += dt
                # Plot hold and sweep line
                ax.plot([estimated_time, estimated_time + ramp_dt_sweep], [temps[j + 1], temps[j + 1]], ":", color = "black", linewidth = 2)
                
                estimated_time += ramp_dt_sweep 
        
        ax.set_xlabel("Time [mins]")
        ax.set_ylabel("Temperature [°C]")
        
        canvas = FigureCanvasTkAgg(fig, master = master)
        self.plot_widget = canvas.get_tk_widget()
        self.plot_widget.pack()
        fig.canvas.draw()
        
        # Convert estimated time to hours:minutes:seconds, rounding up to the nearest minute
        estimated_time = datetime.timedelta(minutes = estimated_time)
        estimated_time += datetime.timedelta(seconds = np.floor(60 - (estimated_time.seconds % 60)))
        estimated_time -= datetime.timedelta(microseconds = estimated_time.microseconds)


class RunningPage(tk.Frame):
    # This page can be considered the main page of the application.
    # This page controlls the main loop of the experiment, as well as displays an informative dashboard and a temperature live plot.
    # This is achieved using a series of threads.
    # If altering the below, remember that matplotlib is not threadsafe, so ensure matplotlib widgets are only run in the main thread, as below.
    
    def __init__(self, master):
        tk.Frame.__init__(self, master)
        
        # Info frame
        self.frm_info_master = tk.Frame(self)
        self.frm_info_master.grid(row = 0, column = 0)
        self.setup_info(self.frm_info_master)
        self.setup_status_box(self.frm_info_master)
        
        # Live plot frame
        self.frm_plot_master = tk.Frame(self)
        self.frm_plot_master.grid(row = 0, column = 1, rowspan = 2)
        self.setup_plot(self.frm_plot_master)
        
        # Stop / Finish Button
        self.frm_stop = tk.Frame(self, pady = 20)
        self.frm_stop.grid(row = 1, column = 0)
        self.btn_stop = tk.Button(self.frm_stop, text = "STOP", font = "Helvetica 22 bold", fg = "red", width = 12, height = 1, command = self.stop_button_func)
        self.btn_stop.pack()
        
        # Begin main experiment thread
        self.experiment_thread = threading.Thread(target = self.experiment_mainloop, args = (master,))
        self.experiment_thread.daemon = True
        self.experiment_thread.start()
        
        # Save the current time to measure the time elapsed
        self.start_time = time.perf_counter()
        with open("experiments\\" + experiment_name + "\\details.json", "r") as jf:
            self.start_time_datetime = datetime.datetime.strptime(json.load(jf)["datetime"], "%Y-%m-%dT%H:%M:%S.%f")
        
    def stop_button_func(self):
        # On press of the "STOP" button, the below is executed.
        # Any stage heating process is stopped, the details file is updated, and any logs are updated.
        # The temperature plot is also saved and the "get temperature" thread is stopped.
        # The application is then exited
        
        stage.stop_heating()
        
        with open("experiments\\" + experiment_name + "\\details.json", "r") as jf:
            json_dict = json.load(jf)
            json_dict["time_elapsed"] = str(self.info_data["Time Elapsed"].cget("text"))
        
        with open("experiments\\" + experiment_name + "\\details.json", "w") as jf:
            jf.write(json.dumps(json_dict, indent = 4))
        
        try:
            stage.move_log(experiment_name)
        except:
            pass
        
        self.update_status("Stop button used / user interrupt.", True)
        
        self.stop_thread = True
        time.sleep(0.5)
            
        self.save_plot()
        
        plt.close("all")
        app.destroy()
        sys.exit()
    
    def finish_button_func(self):
        # On press of the "finish" button, the below is executed.
        # The "get temperature" thread is stopped, and the program is exited.
        
        self.update_status("Program Ended", True)
        self.stop_thread = True
        time.sleep(0.5)
        
        plt.close("all")
        app.destroy()
        sys.exit()

    def setup_status_box(self, master):
        # Tkinter related code to initialise the status box
        
        lbl_running = tk.Label(master)
        lbl_running.pack()
        
        frm_status_box = tk.Frame(master)
        frm_status_box.pack()
        
        lbl_status_title = tk.Label(master = frm_status_box, text = "CURRENT STATUS", font = "Helvetica 13 bold")
        lbl_status_title.pack()
        
        self.lbl_status = tk.Label(master = frm_status_box, font = tkfont.Font(size = 12), text = "Experiment is Starting.", width = 45, relief = tk.GROOVE, borderwidth = 2, pady = 20)
        self.lbl_status.pack()

    def setup_info(self, master):
        # Tkinter related code to setup a large portion of the dashboard.
        # There are various frames in which related information is grouped.
        
        frm_info = tk.Frame(master)
        frm_info.pack()

        # Store data for easy updating
        self.info_labels = {}
        self.info_data = {}

        def setup_row(frame, label, row):
            self.info_labels[label] = tk.Label(master = frame, text = label + " =", font = tkfont.Font(size = 12), anchor = tk.W, justify = tk.LEFT, width = 25)
            self.info_data[label] = tk.Label(master = frame, text = "-", font = tkfont.Font(size = 12), anchor = tk.E, justify = tk.RIGHT, width = 20)
            
            self.info_labels[label].grid(row = row, column = 0, sticky = tk.W, pady = 5)
            self.info_data[label].grid(row = row, column = 1, sticky = tk.E, pady = 5)

        # Frame 1: Experiment Name, Estimated Total Time and Time Elapsed
        frm_1 = tk.Frame(master = frm_info, pady = 1, relief = tk.GROOVE, borderwidth = 2)
        frm_1.pack()
        setup_row(frm_1, "Experiment Name", 0)
        setup_row(frm_1, "Estimated Total Time", 1)
        setup_row(frm_1, "Time Elapsed", 2)
        
        tk.Label(master = frm_info, pady = 1).pack()

        # Frame 2: Temperature
        frm_2 = tk.Frame(master = frm_info, pady = 1, relief = tk.GROOVE, borderwidth = 2)
        frm_2.pack()
        setup_row(frm_2, "Temperature (°C)", 0)
        
        tk.Label(master = frm_info, pady = 1).pack()
        
        # Frame 3: Ramp, Temperature Interval, Impedance Sweep Number
        frm_3 = tk.Frame(master = frm_info, pady = 1, relief = tk.GROOVE, borderwidth = 2)
        frm_3.pack()
        setup_row(frm_3, "Ramp", 0)
        
        # Set up custom row displaying ramp details
        self.info_labels["Ramp Details"] = tk.Label(master = frm_3, font = tkfont.Font(size = 12), width = 35, relief = tk.GROOVE, borderwidth = 2)
        self.info_labels["Ramp Details"].grid(row = 1, column = 0, columnspan = 2, pady = 5, padx = 5)
        
        # Continue Frame 3
        setup_row(frm_3, "Temperature Point", 2)
        setup_row(frm_3, "Impedance Sweep", 3)
        setup_row(frm_3, "Impedance Scan", 4)
        
        # Insert experiment name and estimated time
        self.info_data["Experiment Name"]["text"] = experiment_name
        self.info_data["Estimated Total Time"]["text"] = estimated_time

    def setup_plot(self, master):
        # Tkinter and matplotlib calling to setup the live temperature plot.
        # A matplotlib animation is used to display the live temperature.
        
        fig_ani = Figure(figsize = (10, 6))
        ax_ani = fig_ani.add_subplot(111)
        
        with open("experiments\\" + experiment_name + "\\details.json") as jf:
            ramps = json.load(jf)["ramps"]
        
        terminating_temps = []
        for ramp in ramps:
            terminating_temps.append(ramp["start_temp"])
            terminating_temps.append(ramp["end_temp"])
        
        # These are found to define the axes range.
        min_temp = min(terminating_temps) - 1
        max_temp = max(terminating_temps) + 1
        
        def animate(i):
            # Animation function called on repeat by the matplotlib animation widget.
            
            if os.path.exists("experiments\\" + experiment_name + "\\temperature_data.txt"):
                lines = open("experiments\\" + experiment_name + "\\temperature_data.txt").readlines()[1:]
                data = np.asarray([line.strip().split(",") for line in lines[0:]]).astype(np.float)

                temp_data = data[:,1]
                time_data = data[:,0]
                time_data = [seconds / 60 for seconds in time_data] # change to minutes
                
                # If more than 30 minutes have past, only plot last 30 minutes
                time_data = time_data[-1800:]
                temp_data = temp_data[-1800:]

                # Clear canvas and plot updated data
                ax_ani.clear()
                ax_ani.plot(time_data, temp_data)
                
                ax_ani.set_xlabel("Time [mins]")
                ax_ani.set_ylabel("Temperature [$^o$C]")
                
                ax_ani.set_xlim(right = max(5, time_data[-1] + 1)) # axis range will never be below 5 minutes
                
                # If temperature has exceeded the bounds described above, adjust the bounds
                y_low = min_temp
                y_high = max_temp
                
                highest_temp = max(temp_data)
                lowest_temp = min(temp_data)
                
                if highest_temp > y_high:
                    y_high = highest_temp
                if lowest_temp < y_low:
                    y_low = lowest_temp
                
                ax_ani.set_ylim(y_low - 5, y_high + 5)
                
            else:
                time.sleep(5)
        
        # Initialise temperature_data.txt file, and write header.
        # This file is read repeatedly by the animation function.
        with open("experiments\\" + experiment_name + "\\temperature_data.txt", "a") as f:
            f.write("seconds, temperature\n")
 
        canvas = FigureCanvasTkAgg(fig_ani, master = master)
        canvas.draw()
        canvas.get_tk_widget().pack()
        canvas._tkcanvas.pack()
        
        app.ani = animation.FuncAnimation(fig_ani, animate, frames = None, repeat = False)

    def save_plot(self):
        # On "STOP", "FINISH" button presses, or on exit, the temperature plot is saved as below.
        
        fig, ax = plt.subplots(1,1,figsize=(10,6))

        lines = open("experiments\\" + experiment_name + "\\temperature_data.txt").readlines()[1:]
        data = np.asarray([line.strip().split(",") for line in lines[0:]]).astype(np.float)

        temp_data = data[:,1]
        time_data = data[:,0]
        time_data = [second / 60 for second in time_data]

        ax.plot(time_data, temp_data)
        ax.set_xlabel("Time [mins]")
        ax.set_ylabel("Temperature [$^o$C]")

        ax.set_title("Experiment: {}".format(experiment_name))

        plt.savefig("experiments\\" + experiment_name + "\\temp_profile.png", dpi = 200)

    def update_measurement_info(self, temp, ramp, stage, temp_interval_num, sweep_num):
        # On certain events, such as a measurement completion, the dashboard of information is updated.
        
        self.info_data["Ramp"]["text"] = "{} / {}".format(ramp.num, len(ramps))
        self.info_labels["Ramp Details"]["text"] = "[ {:.2f} \u2192 {:.2f} ] °C, \u0394T = {:.2f} K".format(ramp.start_temp, ramp.end_temp, ramp.interval)
        self.info_data["Temperature Point"]["text"] = "{} °C    {} / {}".format(round(temp, 2), temp_interval_num, ramp.num_intervals + 1)
        self.info_data["Impedance Sweep"]["text"] = "{} / {}".format(sweep_num, ramp.num_sweeps_at_T)
        self.info_data["Impedance Scan"]["text"] = "{} Hz    {} / {}".format("-", "-", len(ramp.frange))

    def _update_temperature_and_time(self, stage):
        # Called as part of the "get temperature" thread, the temperature and time elapsed is updated every second.
        # The temperature and time are written to temperature_data.txt
        
        while not self.stop_thread:
            temperature = round(stage.get_temperature(), 2)
            seconds = np.floor(time.perf_counter() - self.start_time)
            self.info_data["Temperature (°C)"]["text"] = str(temperature)
            
            if not self.complete:
                self.info_data["Time Elapsed"]["text"] = str(datetime.timedelta(seconds = seconds))

            with open("experiments\\" + experiment_name + "\\temperature_data.txt", "a") as f:
                f.write("{:.2f},{:.2f}\n".format(seconds, temperature))
                
            time.sleep(1)

    def update_status(self, status, log):
        # On certain events, such as the start of a new impedance sweep, the status box is updated.
        # If this event is to be logged, it is, along with relevant information regarding the current state of the experiment.
        
        self.lbl_status["text"] = status
        
        if log:
            time = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            ramp = self.info_data["Ramp"].cget("text")
            temp_point = self.info_data["Temperature Point"].cget("text")
            temp_point = temp_point[:8] + temp_point[10:] # Remove centre spaces
            temp = self.info_data["Temperature (°C)"].cget("text").ljust(5, "0")
            with open("experiments\\{}\\experiment_log.txt".format(experiment_name), "a") as f:
                f.write("{} | Ramp : {} | Temp Point : {} | T : {} °C | {}\n".format(time, ramp, temp_point, temp, status))

    def experiment_mainloop(self, master):
        # The mainloop of the experiment.
        # For each of the ramps input, the "ramp_and_measure" method is called.
        
        self.complete = False
        
        # Spawn subprocesses to update temperature and time every second
        self.stop_thread = False
        self.temp_update_process = threading.Thread(target = self._update_temperature_and_time, args = (stage,))
        self.temp_update_process.daemon = True
        self.temp_update_process.start()
        
        # Create experiment log file
        with open("experiments\\{}\\experiment_log.txt".format(experiment_name), "w") as f:
            f.write("Experiment Log File for: {}\n".format(experiment_name))
        
        self.update_status("Experiment is Starting.", True)

        for ramp in ramps:
            # Create directory to store ramp data
            os.mkdir("experiments//" + experiment_name + "//{}_{}".format(ramp.num, "up" if ramp.up else "down"))
            
            # Measure impedances and varying temperatures along the ramp
            self.ramp_and_measure(ramp, stage, analyser)
        
        self.update_status("Experiment Complete", True)
        
        # Change experiment to being complete in details.json
        with open("experiments\\{}\\details.json".format(experiment_name), "r") as jf:
            jsondict = json.load(jf)
            jsondict["complete"] = True
            jsondict["time_elapsed"] = self.info_data["Time Elapsed"].cget("text")

        with open("experiments\\{}\\details.json".format(experiment_name), "w") as jf:
            jf.write(json.dumps(jsondict, indent = 4))
        
        # Stop hardware and threads, and change STOP button to FINISH
        stage.stop_heating()
        try:
            stage.move_log(experiment_name)
        except:
            pass
        
        # The temperature plot is saved, and the experiment is complete.
        self.save_plot()
        self.complete = True
        
        # The "STOP" button is changed to a "FINISH" button, and it not calls finish_button_func instead of stop_button_func
        self.btn_stop.configure(text = "FINISH", font = "Helvetica 22 bold", fg = "black", width = 12, height = 1, command = self.finish_button_func)

    def ramp_and_measure(self, ramp, stage, analyser):
        # Given a ramp, a temperature controlled stage, and an impedance analyser, measurements are carried out.
        # For each of the temperatures at which to measure during the temperature, impedance sweeps are carried out.
        
        for temp_interval_num, temp in enumerate(ramp.temps):
            # Dashboard is updated
            self.update_measurement_info(temp, ramp, stage, temp_interval_num + 1, 0)

            # While loop to attempt heating until temperature is within 1 degree of where it should be
            first_iter = True
            while True:
                stage._start_heating(temp, ramp.rate, ramp.min_holdtime)
                time.sleep(3) # if important as if within a few degrees, stage may be returning that it's holding but we actually need to keep heating

                self.update_status("Heating/Cooling to {} °C".format(temp), first_iter)
                first_iter = False
                
                # Holdtime is 0.0 while stage is heating/cooling
                while stage.get_holdtime_remaining() == 0.0:
                    time.sleep(1)
                
                # If temperature has not been reached to within a degree, try again.
                if temp - 1 <= stage.get_temperature() <= temp + 1:
                    break
                
            # "Hold", to allow stage to settle at desired temperature within a given tolerance
            stage.toggle_hold() # toggle hold on
            if not isinstance(stage, virtual.stage):
                stage.update_tolerance(temp)
                first_iter = True # for logging purposes
                while not (temp - stage.tolerance <= stage.get_temperature() <= temp + stage.tolerance):
                    self.update_status("Temperature not T = {:.2f} °C, holding...".format(temp), first_iter)
                    first_iter = False
                    time.sleep(1)

            # Then actually hold for the given hold time, such that sample can thermalise
            holdtime_remaining = ramp.min_holdtime
            first_iter = True # for logging purposes
            while holdtime_remaining > 0.0:
                self.update_status("Holding at T = {:.2f} °C, Holdtime Remaining = {:.2f} (s)".format(temp, round(holdtime_remaining)), first_iter)
                first_iter = False
                time.sleep(1)
                holdtime_remaining -= 1
            
            # If measurements are to be made on this ramp, make them
            if ramp.num_sweeps_at_T != 0:
                # Make desired measurements
                for sweep_num in range(ramp.num_sweeps_at_T):
                    # Update dashboard.
                    self.update_measurement_info(temp, ramp, stage, temp_interval_num + 1, sweep_num + 1)
                    
                    # If not the first sweep, wait sweep_delay seconds
                    if sweep_num != 0:
                        first_iter = True
                        for seconds_elapsed in range(ramp.sweep_delay):
                            self.update_status("Waiting to perform next impedance sweep, t = {}s".format(ramp.sweep_delay - seconds_elapsed), first_iter)
                            first_iter = False
                            time.sleep(1)
                    
                    # Get temperature as measured by the stage to include in the metadata of the sweep
                    Tcell = stage.get_temperature()
                    
                    # Begin impedance measurement thread
                    self.update_status("Beginning sweep {} / {}.".format(sweep_num + 1, ramp.num_sweeps_at_T), True)
                    Z_measurement_thread = analyser.measure_impedance(self.info_data["Impedance Scan"], ramp, sweep_num, Tcell, experiment_name, temp_interval_num)
                    time.sleep(1) # Wait for thread to start
                    
                    # Obtain temperature every second until impedance sweeps are complete
                    self.update_status("Performing sweep {} / {}.".format(sweep_num + 1, ramp.num_sweeps_at_T), True)
                    while Z_measurement_thread.is_alive():
                        time.sleep(1)
            else:
                self.update_status("No sweeps to be carried during this ramp.", True)
        
            # Now that required impedance measurements are complete, stop holding at temperature and proceed
            stage.toggle_hold() # toggle hold off
            
            # Update dashboard
            self.update_measurement_info(temp, ramp, stage, temp_interval_num + 1, 0)


def on_closing():
    # The function called by closing any frame.
    # All matplotlib widgets and plots are closed.
    # If not the running page, the app is simply destroyed.
    # If it is the running page, the stop_button_func method is called.
    
    if tk.messagebox.askokcancel("Quit", "Do you want to quit?"):
        plt.close("all")
        if isinstance(app._frame, RunningPage):
            app._frame.stop_button_func()
        else:
            app.destroy()


if __name__ == "__main__":
    global app
    app = vtipy2()
    app.title("vtipy2")
    app.protocol("WM_DELETE_WINDOW", on_closing) # Specifies that the "on_closing" function should be called on pressing the exiting "X" button
    app.mainloop()
    sys.exit()