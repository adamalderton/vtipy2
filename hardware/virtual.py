# The stage and analyser classes below reflect functionality for "virtual" stages and analysers
# They do not interact with any hardware in any way at all, and can be sued for testing or demonstration purposes
# Theys simply return random numbers or predictable behaviour when necessary
# The analyser class inherits from the solartron1260 class, and therefore behaves similarly


import random, os, time, datetime, shutil
import numpy as np
import threading

from hardware import linkam
from hardware.solartron import solartron1260

# Testing is made safe by method overwriting
class stage():
    def __init__(self):
        self.name = "Virtual Stage"
        self.min_temp, self.max_temp = self.get_value_limits(linkam._StageValueType.Heater1Temp)
        self.min_rate, self.max_rate = self.get_value_limits(linkam._StageValueType.HeaterRate)
        

    def _start_heating(self, temp, rate, holdtime):
        pass
    
    def stop_heating(self):
        pass
        
    def get_temperature(self):
        return 45 + 15 * np.sin(0.1 * time.perf_counter())
    
    def get_holdtime_remaining(self):
        return random.choice([0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
    
    def toggle_hold(self):
        pass
    
    def get_value_limits(self, svt):
        if isinstance(svt, str):
            svt = getattr(linkam._StageValueType, svt)
        else:
            svt = linkam._StageValueType(svt)
  
        if svt == linkam._StageValueType.Heater1Temp:
            vmin = 0
            vmax = 500
        elif svt == linkam._StageValueType.HeaterRate:
            vmin = 1
            vmax = 30
        else:
            print("get value limits err")
        
        return tuple( float(v) for v in (vmin, vmax) )
    
    def move_log(self, experiment_name):
        shutil.move("linkam_log.txt", "experiments\\" + experiment_name + "\\linkam_log.txt")

class analyser(solartron1260):
    # Inherits analyser code from solartron1260, apart from measure_frequency which is overwritten below
    def __init__(self):
        self.name = "Virtual Analyser"
        self.min_frequency = 1e-5 # from manual
        self.max_frequency = 3.2e7
        self.min_V = 1
        self.max_V = 100
        
    def send(self, message):
        pass
    
    def measure_frequency(self, frequency):
        time.sleep((1/frequency) + 2)
        return "{},{},{}".format(random.uniform(-1e6, 1e6), random.uniform(0, 1e6), random.uniform(0, 2* np.pi))
    

