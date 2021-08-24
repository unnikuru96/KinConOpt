import importlib
import pandas as pd
import dateutil
from datetime import datetime
import json
import sys
import os

class Analyzer():
	def __init__(self):

		sys.path.append('../io_modules/') #add io_modules to path!

			#------------------Loading GC Config File----------------------#
		with open("../config_files/main_config.json", 'r') as f:
			self.main_config = json.load(f)
			gc_module = self.main_config["GC Module"] #pick gc module to import
			with open(self.main_config["GC Config File"],'r') as gc_f:
				self.gc_config = json.load(gc_f)

			gc_module = importlib.import_module(gc_module)
			self.gc = gc_module.Instrument(self.main_config["GC Config File"],online=False)
			

			#------------------Loading Flow Config File---------------------#
			if self.main_config["Flow Config File"] != "":
				with open(self.main_config["Flow Config File"],'r') as flow_f:
					self.flow_config = json.load(flow_f)
			else:
				self.flow_config = None

			#-------------------Loading Temp Config File--------------------#
			if self.main_config["Temp Config File"] != "":
				with open(self.main_config["Temp Config File"],'r') as temp_f:
					self.temp_config = json.load(flow_f)
					self.temp_name = self.temp_config["Name"]
				else:
					self.temp_config = None

			print("Using GC: {}".format(gc_module))
			print("Using GC config file: {}".format(self.main_config["GC Config File"]))
			print("Using Flow config file: {}".format(self.main_config["Flow Config File"]))

			#--------------------Preparing Output Directory------------------#
			now = datetime.now()
        	self.path_to_store_data = self.main_config["Data Analysis Path"]+"{}".format(now.strftime("%Y-%m-%d_%H.%M.%S")) #creating a new directory for data analysis
			os.mkdir(self.path_to_store_data)
		

	def analyze_multiple_runs(self,run_dataset,bp_dataset,run_log_fname):
		run_files = self.gc.prep_dataset(run_dataset,self.path_to_store_data+"/run_files")
		if ".zip" in bp_dataset: #generate bypass unless it's already generated
			bp_json = self.generate_bypass(bp_dataset)
		else:
			bp_json = bp_dataset
		df = None
		for file in run_files:
			with open(file,'r') as f:
				run_json = json.load(f)
				run_json = self.add_conditions(run_json,run_log_fname) #adds temperature, flow, etc. to run_json
				res, peaks, val_params = self.gc.analyze_run_offline(run_json,bp_json)
				res_df = pd.json_normalize(res,sep="_") #flatten the results dictionary to form a dataframe
				val_params_df = pd.json_normalize(val_params,sep="_")
				combined_df = pd.concat([res_df,val_params_df],axis=1) #add C balance, etc. to results

				if df is None:
					df = combined_df
				else:
					df.append(combined_df)

		return df

	def generate_bypass(self,bp_dataset):
		"""This function averages multiple bypass runs to generate an average bp run"""

		bp_files = self.gc.prep_dataset(bp_dataset,self.path_to_store_data+"/bp_files") #returns a list of string filenames from dataset
		bypass = self.gc.collect_cal_peaks() #produce a starting dictionary of all peaks we're looking for
		for data_fname in bp_files:
			with open(data_fname,'r') as f:
				bp_json = json.load(f)
				peaks = self.gc.generate_bypass_areas(bp_json,extract=True) #extract the peak areas from the complicated GC file structure
				for compound, area_dict in peaks.items():
					if compound in bypass.keys():
						bypass[compound]["bypass_area"] += area_dict["bypass_area"]
					else:
						bypass[compound]["bypass_area"] = area_dict["bypass_area"]

		#average bypass areas
		for compound, area_dict in peaks.items():
			if "bypass_area" in area_dict.keys():
				bypass[compound]["bypass_area"] /= len(bp_files)

		return bypass

	def analyze(self,run_json,bypass_fname,run_log_fname):
		analyses = []
		run_json = self.add_conditions(run_fname,run_log_fname)
		return self.gc.analyze_run_offline(run_json)

	def add_conditions(self,run_fname,run_log_fname): #adds all conditions from run log entry to a JSON file
		with open(run_fname,'r') as f:
			filedata = json.load(f)
			runID = filedata["runID"]
			df = pd.read_csv(run_log_fname)
			run_log_entry = df.loc[df["runID"] == runID] #returns the row of run log which we want
			for idx in run_log_entry:
				if idx != "runTimeStamp":
					if idx != "runID":
						filedata[idx] = run_log_entry[idx]
		return filedata

	

















if __name__ == '__main__':

	sys.path.append('../io_modules/') #add io_modules to path!

	with open("../config_files/main_config.json", 'r') as f:
		main_config = json.load(f)
		gc_module = main_config["GC Module"] #pick gc module to import


		print("Using GC: {}".format(gc_module))
		print("Using GC config file: {}".format(main_config["GC Config File"]))

		gc_module = importlib.import_module(gc_module)


		print("Run File Location: {}".format(sys.argv[1]))
		print("Bypass File Location: {}".format(sys.argv[2]))

		with open(sys.argv[1],'r') as run_f:
			with open(sys.argv[2], 'r') as bypass_f:
				run_json = json.load(run_f)
				bp_json = json.load(bypass_f)
				gc = gc_module.Instrument(main_config["GC Config File"],online=False)
				results, peaks,val_params = gc.analyze_run_offline(run_json,bp_json)
				print("\nAnalysis of GC Data")
				for major_key,val in results.items():
					print('---------------')				
					print(major_key)
					for key, minor_value in val.items():
						if (1*10**(-20) < minor_value < .01) or minor_value > 1000:
							print("     {}: {:.6e}".format(key, minor_value))
						else:
							print("     {}: {:.6f}".format(key, minor_value))
				print('---------------')	
				print("Validation Parameters")
				for key, val in val_params.items():		
					print("     {}: {:.6e}".format(key, val))
