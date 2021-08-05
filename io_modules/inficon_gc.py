import json
import pandas as pd


class Instrument():
    def __init__(self,online=True):
        self.online = online
        self.old_run_location = None

        try:       
            with open(config_file, 'r') as f:
                config = json.load(f)
                self.GC_peak_search_window = config["GC Peak Search Window"] #seconds
                if online: #if planning to communicate with the GC
                    self.host = config["IP Address"]
                    self.old_run_location = self.get_last_run_location()

            #------------------- Calibration Set-Up---------------#
            self.cal = pd.read_csv(config_file["Cal File Loc"])


        except KeyError as e:
            raise Error("port, address, test_register, test_response, PV register, or SP register is not in JSON file.")
        except FileNotFoundError as e:
            raise FileNotFoundError("{} not a locatable file".format(config_file))
        except:
            print("Unexpected error: ",sys.exc_info()[0])
            raise

    #This method sends a GET request to the GC for the latest run and returns that run's ID
    def get_last_run_location(self):
    #    return 'b923ec2b-5ccc-4f83-b56b-acf841aa08d3'
        last_run_location = 'http://' + self.host + '/v1/lastRun'
        try:
            response = requests.get(last_run_location)
            last_run = response.json()
            return last_run['dataLocation']
        except KeyboardInterrupt:
            print("Exiting on interrupt.")
            sys.exit()
        except: # catchall
            e = sys.exc_info()[0]
            print("Error retreiving last_run_location from " + last_run_location)
            print(e)
            return ""

    #returns True if ID of latest run is different from last ID stored in program
    def check_for_new_run(self):
        new_run_location = self.get_last_run_location()
        if self.old_run_location == new_run_location:
            return True 
        else:
            return False


    def analyze_run_online(self):
            response = requests.get(self.old_run_location)
            last_run = response.json()
            return self.analyze_run_offline(last_run)

    """ This method is the workhorse of the module. Analyzes a run by pulling in all the peaks from the run, 
        making sure they're labelled correctly, correcting any unlabelled peaks, and then calculating the 
        concentration of each species based on its calibration."""

    def add_peak_window(self,run_json):
    

    def is_air(self,peak):
        if peak["area"] > 1000000 and 20 < peak["top"] and peak["top"] < 30 and peak["detector"] != "moduleA:tcd":
            return True 
        else:
            return False
    def analyze_run_offline(self,run_json):
        peaks = {i:{} for i in df.to_dict()["Compound"].values()} #initialize set of compounds from calibration

        #first iterate through all the GC peaks and add any labelled ones to our peaks dictionary for the run
        unlabelled_peaks = []
        for detector_name,detector in run_json["detectors"].items():
            if detector_name != "moduleD:tcd": #ignore all peaks from Module D for the time being
                for peak in detector["analysis"]["peaks"]:
                    label = peak.get("label")
                    peak["detector"] = detector_name
                    if label is None:
                        unlabelled_peaks.append(peak) #deal with unlabelled peaks after going through all the peaks
                    elif label in peaks.keys(): #make sure label is in calibration
                        peaks[label] = peak
                    else:
                        raise ValueError("Peak found in gc with label {}. This label does not exist in cal".format(label))

        #strip air peaks and peaks with minimal area, i.e. < 100
        unlabelled_peaks = [peak for peak in unlabelled_peaks if (not is_air(peak)) and  peak["area"] > 100]
        unlabelled_peaks = sorted(unlabelled_peaks,key= lambda x: x["top"]) #sort unlabelled peaks by low-to-high RT

        remaining_cal_peaks = [label for label in peaks.keys() if peaks[label] == {}]

        for label in remaining_cal_peaks:
            #first method of assigning peaks: Look at shift of nearest peak in cal that is labelled
            row_ID = df.loc[df["Compound"]==label].index
            module = df.loc[df["Compound"]==label]["Module"]
            if <
            df.iloc[df.loc[df["Compound"]=="CO"].index-1,:]










