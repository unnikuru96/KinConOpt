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
		

	def analyze(self,run_json,bp_json,logfile):
		"""This method takes in a singular GC run JSON and figures out what flowrate and temperature the run occurred at, based on the logfile timestamps.
		It then passes the run_json, with Temp and Flowrate, into the analyzer to produce conversion, selectivity, etc."""
		
		#-----------------Finding Flow and Temperature conditions from logfile------------------#
		# GC_time = pd.to_datetime(pd.Series(dateutil.parser.parse(str(run_json['runTimeStamp'])))) #UTC time from GC run
		# logdf = pd.read_csv(logfile)
		# logdf["Time"] = pd.to_datetime(logdf["Time"], format="%Y-%m-%d %H:%M:%S")
		# prev_time = None
		# for i,logtime in enumerate(logdf["Time"]):
		# 	if logtime > GC_time: #if the logfile now supercedes the GC run time
		# 		if prev_time is None:
		# 			raise ValueError("All log times greater than GC time- cannot determine run conditions.\nGC time: {} Logtime: {}".format(GC_time,logtime))
		# 		else:
		# 			break #prev_time now represents the flow conditions for our GC run
		# 	else:
		# 		prev_time = logtime #we're still iterating through logtimes before the GC_time. increment our timestep in the logfile

		# if self.flow_config is not None:
		# 	run_json["Total Flow"] = logdf.loc[logdf["Time"]==prev_time]["Total Flow SP"]
		# if self.temp_config is not None:
		# 	run_json["Temperature"] = logdf.loc[logdf["Time"]==prev_time][self.temp_name + " SP"]

		return gc.analyze_run_offline(run_json,bp_json)

	def generate_bypass(self,bp_dataset,run_log_fname):
		"""This function averages multiple bypass runs to generate an average bp run"""

		bp_files = self.gc.prep_dataset(bp_dataset,self.path_to_store_data) #returns a list of string filenames from dataset
		bypass = self.gc.generate_bypass_areas(bp_files[0])

		for data_fname in bp_files):
			with open(data_fname,'r') as f:
				bp_json = json.load(f)
				peaks = 
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
