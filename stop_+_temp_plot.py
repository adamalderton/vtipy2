# This is a script to stop the heating functionality of a connected Linkam stage, and then continue to plot the current temperature.
# This should be used in the event of a failure in vtipy2 perhaps, or any other emergency that would require the stage to begin cooling.
# This can also be used to simply check and monitor the temperature of a connected stage. Ensure not to run this if you do not want the stage to stop heating.
# Remember: vtipy2 also displays the current temperature, and has a stop button to stop the heating of a connected stage.

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import style
style.use("ggplot")

import hardware.linkam as linkam

# Connect to stage using _HeatingStage base class, such that this functionality is not stage type reliant
# This could fail if another process is in communication with the stage. For example vtipy2 or the LINK softare.
stage = linkam._HeatingStage()

# Stop heating
stage.stop_heating()

# Global variables to hold temperatures and times
global temps, times
temps = []
times = []

# matplotlib figure
fig = plt.figure()
ax = plt.axes()

# Animation function for matplotlib to produce live plot animation
def animate(i):
    global temps, times
    new_temp = round(stage.get_temperature(), 2)
    temps.append(new_temp)
    times.append(i) # interval is 1 second, so i represents seconds
    
    ax.clear()
    ax.plot(times, temps)

    # If more than 10 minutes have past, only plot last 10 minutes
    times = times[-600:]
    temps = temps[-600:]

    # set minimum time axis to be 2 minutes
    ax.set_xlim(right = max(120, times[-1] + 1))
    
    y_low = 5 # default lower y value for plot
    y_high = 45 # default upper y value for plot

    # set y axis limit dependent on whether temperature is out of default bounds above
    highest_temp = max(temps)
    lowest_temp = min(temps)
    if highest_temp > y_high:
        y_high = highest_temp
    if lowest_temp < y_low:
        y_low = lowest_temp
    ax.set_ylim(y_low - 5, y_high + 5)

    ax.set_title("Stage Temperature")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Temperature [°C]")

ani = animation.FuncAnimation(fig, animate, interval = 1000) # create animation with interval of 1s
plt.show()
