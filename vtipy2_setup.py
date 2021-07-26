# This is a complementary setup script for vtipy2 to aid in setting up hardware
# If hardware setup in this script is successful, then the same hardware should be successful in vtipy2
# Program will break and raise errors if any stage of the setup is unsuccessful
# Please consult vtipy2 and the README before using this program

import json, os
from hardware import virtual
import hardware.linkam as linkam

# Add current directory to search path windows will take to find .dll files
os.add_dll_directory("{}".format(os.getcwd()))

# add options to lists below if new hardware is implemented. names should match if statements in vtipy2
stage_options = ["HFS350", "TS1000", "virtual"]
analyser_options = ["1260", "SP_200", "virtual"]

def setup():
    # Creates a hardware_setup.json file, readable by human and vtipy2.
    with open("hardware_setup.json", "w") as jf:
        jsondict = {"successful" : False,
                    "stage" : {
                        "name" : "",
                        "successful" : False},
                    "analyser" : {
                        "name" : "",
                        "successful" : False}
                    }
        jf.write(json.dumps({"successful" : False}, indent = 4))

    # Setup stage and analyser
    stage_setup()
    analyser_setup()

    # Indicate that setup was successful
    with open("hardware_setup.json", "r") as jf:
        jsondict = json.load(jf)
        jsondict["successful"] = True

    # Write all details to hardware_setup.json
    with open("hardware_setup.json", "w") as jf:
        jf.write(json.dumps(jsondict, indent = 4))

    print("\tSetup successful!")

def stage_setup():
    # Takes stage choice, and initialises it to aid in debugging.
    # Writes stage configuration to file.
    
    # Currently, this script does not check that the stage entered is the same as the stage connected.
    # Due to time constraints, I was not able to get this functionality to work in time. 
    # The two commented out lines below could serve as inspiration for anyone tackling this problem.
    # There (should be) a flag in the _StageGroup enum, which indicated whether a stage has vacuum functionality,
    # called "Vacuum". The idea was to use this to differentiate between the two stages.
    #
    # variant = stage.get_value(linkam._StageValueType.Heater1Temp, result = linkam._Variant())
    # print(variant.__getattribute__("vStageGroup"))
    
    while True:
        stage_choice = str(input("\tChoose a stage to use: {}\n".format(stage_options)))
        if stage_choice in stage_options:
            break
        print("\tNot valid, try again.")
    
    if stage_choice == "HFS350":
        stage = linkam.HFS350()
    elif stage_choice == "TS1000":
        stage = linkam.TS1000()
    else:
        stage = virtual.stage()

    print("\tStage intialisation successful: {}\n".format(stage))

    with open("hardware_setup.json", "r") as jf:
        jsondict = json.load(jf)
        jsondict["stage"] = {"name" : stage_choice, "successful" : True}
    # write stage configuration to file
    with open("hardware_setup.json", "w") as jf:
        jf.write(json.dumps(jsondict, indent = 4))

def analyser_setup():
    # Takes stage choice, and initialises it to aid in debugging.
    # Writes stage configuration to file.
    
    while True:
        analyser_choice = str(input("\tChoose an analyser to use: {}\n".format(analyser_options)))
        if analyser_choice in analyser_options:
            break
        print("\tNot valid, try again.")
    
    if analyser_choice == "1260":
        from hardware.solartron import solartron1260
        analyser = solartron1260()
    elif analyser_choice == "SP_200":
        from hardware.biologic import SP_200
        analyser = SP_200()
    else:
        analyser = virtual.analyser()
    
    print("\tAnalyser initialisation successful: {}\n".format(analyser))

    with open("hardware_setup.json", "r") as jf:
        jsondict = json.load(jf)
        jsondict["analyser"] = {"name" : analyser_choice, "successful" : True}
    # write analyser configuration to file
    with open("hardware_setup.json", "w") as jf:
        jf.write(json.dumps(jsondict, indent = 4))

if __name__ == "__main__":
    setup()