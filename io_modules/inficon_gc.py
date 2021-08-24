import json
import sys
import pandas as pd
import zipfile
import os
from datetime import datetime

class Instrument():



    def __init__(self,config_file,online=True):
                #-----------PHYSICAL CONSTANTS-----------#
        self.P_IN_ATM = 1 
        self.R_L_ATM_MOL_K = 0.0820575
        self.T_IN_C = 24
        self.T_IN_K = self.T_IN_C + 273
        self.mL_per_min_to_mol_per_s = (self.P_IN_ATM/(self.R_L_ATM_MOL_K*self.T_IN_K)) / (60*1000) #multiply by this conversion factor to go mL/min --> mol/s assuming IG


                #-----------Config Parameters-------------#
        self.flows_exist = False 
        self.online = online
        self.old_run_location = None

                #-----------Load Config-------------------#
        try:       
            with open(config_file, 'r') as f:
                config = json.load(f)
                # self.GC_peak_search_window = config["GC Peak Search Window"] #seconds

                                #------------------- Analysis Set-Up---------------------#
                self.reactants = config["Reactants"] #identifies reactants of the reaction
                self.major_reactant = config["Major Reactant"] #identifies the 'major' reactant, ex. propane in ODH
                self.diluent = config["Diluent"] #identifies the diluent, ex. N2 or He
                self.products = config["Products"] #identifies the set of products
                self.carbon_number = config["Carbon Number"] #identifies the C number of each compound, ex. propane has C number of 3
                self.selectivity = config["Selectivity"] #identifies which compounds or sets of compounds you want a C selectivity for
                self.conversion = config["Conversion"] #identifies which compounds you want conversion for. Does either reactant or C product conversion
                self.instantaneous_rate = config["Instantaneous Rate"] #identifies which compounds or sets of compounds you want a catalyst and volumetric productivity for
                self.catalyst_mass = config["Catalyst Mass"] # in grams
                self.bed_volume = config["Bed Volume"] #in mL
                self.molecular_weight = config["Molecular Weight"] #molecular weights of compounds, used to generate rates and such
                if online: #if planning to communicate with the GC
                    self.host = config["IP Address"]
                    self.old_run_location = self.get_last_run_location()



            #------------------- Calibration Set-Up---------------#
            print("Using calibration file: {}".format(config["Cal File Loc"]))
            self.cal = pd.read_csv(config["Cal File Loc"])


        except KeyError as e:
            raise ValueError("Inficon config file has some error. Check to make sure all spellings are correct. Error at: {}".format(e))
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
    def get_last_run_ID(self):
        response = requests.get(self.old_run_location)
        last_run = response.json()
        return last_run["$id"]

    def get_last_run_timestamp(self):
        response = requests.get(self.old_run_location)
        last_run = response.json()
        return last_run["runTimeStamp"]

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

    def prep_data(self,dataset,path_to_store_data):
        """Dataset comes in as a .zip file. This fx extracts this .zip, renames the files with .JSON ending, and returns a list of filenames to iterate through."""
        with zipfile.ZipFile(dataset,"r") as dataset:
            dataset.extractall(path=path_to_store_data)
            flist = []
            for fname in dataset.namelist(): #replace endings with .json and create our return list
                old_fname = path_to_store_data+fname
                new_fname = old_fname[:-12]+".json"
                os.rename(old_fname,new_fname)
                flist.append(new_fname)
            return flist


    # def add_peak_window(self,run_json):
    

    # def is_air(self,peak):
    #     if peak["area"] > 1000000 and 20 < peak["top"] and peak["top"] < 30 and peak["detector"] != "moduleA:tcd":
    #         return True 
    #     else:
    #         return False

    """ This method is the workhorse of the module. Analyzes a run by pulling in all the peaks from the run, 
        making sure they're labelled correctly, correcting any unlabelled peaks, and then calculating the 
        concentration of each species based on its calibration."""
    # This method returns two ordered dictionaries, one with the analysis metrics and another with the raw peak data
    
    def collect_cal_peaks(self):
        return {i:{"area" : 0,"detector":None} for i in self.cal.to_dict()["Compound"].values()} #initialize set of compounds from calibration

    def generate_bypass_areas(self,bypass,extract=True):
        
        if extract:
            peaks = self.collect_cal_peaks()
          
            for detector_name,detector in bypass["detectors"].items(): #Pull all labelled peaks from calibration
                for peak in detector["analysis"]["peaks"]:
                    label = peak.get("label")
                    if label in peaks.keys(): #make sure label is in calibration
                        if label in self.reactants:
                            peaks[label]["bypass_area"] = peak["area"]
                    elif label is not None: #if there is a labelled peak not in the calibration, raise an error!
                        raise ValueError("Peak found in gc with label {}. This label does not exist in cal".format(label))
                    else:
                        continue
            return peaks

        else:
            return bypass




    def analyze_run_offline(self,run_json,bypass,avgd_bp=False):

        results = {} # this will be the reported results of the run. No need for ordered dict since Py3.7+ guarantees insertion order.


        #--------------------------Pull in areas from bypass--------------------------#
        if avgd_bp:
            peaks = self.generate_bypass_areas(bypass,extract=False)
        else:
            peaks = self.generate_bypass_areas(bypass,extract=True)


        #------------------------Pull in data from run_json------------------#
        for detector_name,detector in run_json["detectors"].items(): #Pull all labelled peaks from calibration
            for peak in detector["analysis"]["peaks"]:
                label = peak.get("label")
                if label in peaks.keys(): #make sure label is in calibration
                    peaks[label]["detector"] = detector_name
                    for key,val in peak.items():
                        peaks[label][key] = val
                elif label is not None: #if there is a labelled peak not in the calibration, raise an error!
                    raise ValueError("Peak found in gc with label {}. This label does not exist in cal".format(label))
                else:
                    continue

        #add ID Info

        results["ID Info"] = {}
        results["ID Info"]["runID"] = run_json["runID"]
        results["ID Info"]["runTimeStamp"] = run_json["runTimeStamp"]
        if "T" in run_json.keys():
            results["ID Info"]["Temperature"] = run_json["T"] 
        elif "Temperature" in run_json.keys():
            results["ID Info"]["Temperature"] = run_json["Temperature"] 
        elif "Temp" in run_json.keys():
            results["ID Info"]["Temperature"] = run_json["Temp"]
        else:
            pass
        #--------------------------Acquire Flows if Desired----------------------------#
        if "Total Flow" not in run_json:
            val = -1
            while val != "0" and val != "1":
                val = input("\nNo flowrates detected in JSON input file. Select 0 to continue without flows or 1 to manually input reactant volumetric flowrates: ")
                if val == "1":
                    finished = False
                    while not finished:
                        try:
                            total_flow = float(input("Input TRUE total flow: "))
                            if total_flow <= 0:
                                raise ValueError("Total flow must be greater than 0")
                            correct = input("You entered a flow of {}. Enter 1 to confirm or anything else to re-enter flow rate: ".format(total_flow))
                            print("Received: {}".format(correct))
                            if correct == "1":
                                results["ID Info"]["Total Flow"] = total_flow
                                finished = True
                                self.flows_exist = True
                            else:
                                continue

                        except:
                            print("Error on flow input. Make sure the value is a positive number")
                            continue
                elif val == "0": #No input flows desired
                    self.flows_exist = False

        else: #flows are in run_json already (run_json provided by another program)

            results["ID Info"]["Total Flow"] = run_json["Total Flow"]
            self.flows_exist = True



        #--------------------Construct Results Dictionary-------------------#
        
        all_compounds = [] #build out a list of all compounds
        for compound in self.reactants:
            if compound not in all_compounds:
                all_compounds.append(compound)
        all_compounds.append(compound)
        for compound in self.products:
            if compound not in all_compounds:
                all_compounds.append(compound)

        validation_parameters = {} #Store a group of validation parameters to add to the end of the results (how much can we trust this run?)
        results["Areas In"] = { compound : peaks[compound]["bypass_area"] for compound in self.reactants}
        results["Mol % In"] = {compound : 100*results["Areas In"][compound] / float(self.cal.loc[self.cal["Compound"] == compound,"Slope"].values[0]) for compound in self.reactants}
        validation_parameters["Sum of Reactant Mol %"] = sum(val for key,val in results["Mol % In"].items())

        #flows in
        if self.flows_exist:
            results["Flow In (mol/s/g)"] = {key : (val/100) * results["Flows"]["Total"] * self.mL_per_min_to_mol_per_s / self.catalyst_mass for key, val in results["Mol % In"].items()}
            results["Flow In (mol/s/mL)"] = {key : (val/100) * results["Flows"]["Total"] * self.mL_per_min_to_mol_per_s / self.bed_volume for key, val in results["Mol % In"].items()}
        
        results["Areas Out"] = {compound : peak["area"] for compound,peak in peaks.items()}

        validation_parameters["Diluent Factor"] = peaks[self.diluent]["bypass_area"] / peaks[self.diluent]["area"] #N2 Factor
        results["Mol % Out"] = {compound : 100*peaks[compound]["area"] / float(self.cal.loc[self.cal["Compound"] == compound,"Slope"].values[0])  for compound in all_compounds}

        #flows out
        if self.flows_exist:
            results["Flow Out (mol/s/g)"] = {key : (val/100) * results["Flows"]["Total"] * self.mL_per_min_to_mol_per_s * validation_parameters["Diluent Factor"] / self.catalyst_mass for key, val in results["Mol % Out"].items()}
            results["Flow Out (mol/s/mL)"] = {key : (val/100) * results["Flows"]["Total"] * self.mL_per_min_to_mol_per_s * validation_parameters["Diluent Factor"] / self.bed_volume for key, val in results["Mol % Out"].items()}
      
        C_product_pct = sum([results["Mol % Out"][compound] * self.carbon_number[compound] * validation_parameters["Diluent Factor"] for compound in self.products]) # All C products

        #conversion
        results["Product Conversion %"] = {self.major_reactant : 100*C_product_pct / (results["Mol % In"][self.major_reactant]*self.carbon_number[self.major_reactant])}
        results["Reactant Conversion %"] = {compound : 100*(results["Mol % In"][compound]-results["Mol % Out"][compound] * validation_parameters["Diluent Factor"]) / results["Mol % In"][compound] for compound in self.conversion}

        #selectivity
        results["Selectivity"] = {group : {} for group in self.selectivity}
        for group in self.selectivity: #selectivity and rate can have groupings of multiple compounds together
            selectivity = 0 
            for compound in self.selectivity[group]:
                selectivity += results["Mol % Out"][compound] * self.carbon_number[compound] * validation_parameters["Diluent Factor"] / C_product_pct #Carbon selectivity
            results["Selectivity"][group] = 100*selectivity

        if self.flows_exist:
            results["Instantaneous Rate (kg/kg-cat/hr)"] =  {group : {} for group in self.instantaneous_rate}
            results["Instantaneous Rate (kg/L/hr)"] = {group : {} for group in self.instantaneous_rate}
            for group in self.instantaneous_rate:
                rate_mass = 0
                rate_vol = 0
                for compound in self.instantaneous_rate[group]:
                    rate_mass += results["Flow Out (mol/s/g)"][compound] * self.molecular_weight[compound] * 3600 #mult. by 3600 to go s to hr
                    rate_vol += results["Flow Out (mol/s/mL)"][compound] / self.molecular_weight[compound] * 3600 * 1000 #mult. by 1000 to go mL to L
                    
                results["Instantaneous Rate (kg/kg-cat/hr)"][group] =  rate_mass
                results["Instantaneous Rate (kg/L/hr)"][group] = rate_vol

            results["Contact Time"] = {"WHSV (h^-1)" : None, "GHSV (h^-1)" : None}
            results["Contact Time"]["WHSV (h^-1)"] = results["Flow In (mol/s/g)"][self.major_reactant] * self.molecular_weight[self.major_reactant] * 3600 #3600 is s --> hr
            results["Contact Time"]["GHSV (h^-1)"] = results["Flow In (mol/s/mL)"][self.major_reactant] / self.mL_per_min_to_mol_per_s * 60 #60 is min --> hr
        
        #carbon balance
        C_in = sum([results["Mol % In"][reactant]/100 * self.carbon_number[reactant] for reactant in self.reactants if reactant in self.carbon_number.keys()]) #add all C-containing reactants
        C_out = sum([results["Mol % Out"][product]/100 * self.carbon_number[product] * validation_parameters["Diluent Factor"] for product in results["Mol % Out"].keys() if product in self.carbon_number.keys()]) #add all C-containing products
        validation_parameters["Carbon Balance %"] = (C_in - C_out) * 100 / C_in

        return (results, peaks,validation_parameters)










        




        #first iterate through all the GC peaks and add any labelled ones to our peaks dictionary for the run
        # unlabelled_peaks = []
        # for detector_name,detector in run_json["detectors"].items():
        #     if detector_name != "moduleD:tcd": #ignore all peaks from Module D for the time being
        #         for peak in detector["analysis"]["peaks"]:
        #             label = peak.get("label")
        #             peak["detector"] = detector_name
        #             if label is None:
        #                 unlabelled_peaks.append(peak) #deal with unlabelled peaks after going through all the peaks
        #             elif label in peaks.keys(): #make sure label is in calibration
        #                 peaks[label] = peak
        #             else:
        #                 raise ValueError("Peak found in gc with label {}. This label does not exist in cal".format(label))

        #strip air peaks and peaks with minimal area, i.e. < 100
        # unlabelled_peaks = [peak for peak in unlabelled_peaks if (not is_air(peak)) and  peak["area"] > 100]
        # unlabelled_peaks = sorted(unlabelled_peaks,key= lambda x: x["top"]) #sort unlabelled peaks by low-to-high RT

        # remaining_cal_peaks = [label for label in peaks.keys() if peaks[label] == {}]

        # for label in remaining_cal_peaks:
        #     #first method of assigning peaks: Look at shift of nearest peak in cal that is labelled
        #     row_ID = df.loc[df["Compound"]==label].index
        #     module = df.loc[df["Compound"]==label]["Module"]
        #     if <
        #     df.iloc[df.loc[df["Compound"]=="CO"].index-1,:]












