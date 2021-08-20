import sys
import csv
import pandas
import time
import json
import importlib
import datetime
import pandas as pd
from datetime import timezone
from tkinter.filedialog import asksaveasfilename

"""
Usage
------------
'python aux_comms.py' will initialize logging of auxiliary comms devices as configured in the ../config_files/self.main_config.json configuration file. you will also be able to perform onlinee setpoint changes.
'python aux_comms.py setpt_file.csv' will initialize setpoint control of auxiliary comms devices based on setpt_file.csv, as well as logging (configured as above).
aux_comms is also an importable module to be utilized by a higher-level program (for example, if you want to manually change setpoints)
"""

class AuxComms():
	def __init__(self):
		self.prev_log_row = None #Previous row for logger
		self.prev_online_setpt_chg = None #Previous online setpt chg file
		self.setpt_file_exists = False
		sys.path.append('../io_modules/') 

		with open("../config_files/main_config.json", 'r') as f:
			self.main_config = json.load(f)

		self.log_poll_time = float(self.main_config["Log Poll Time"]) #in seconds
		self.logfile = self.main_config["Condition Log File"]


		
		self.sub_dev_map = {}

		#------------------Initializing Comms-------------------#
		print("Initializing Auxiliary communications (flow, temp, etc.):")
		self.aux_devices = {}
		for dev_type in ["Flow Module","Temp Module"]:
			if self.main_config[dev_type] != "":
				print("Using {}: {}. Establishing communications...".format(dev_type,self.main_config[dev_type]))
				module = importlib.import_module(self.main_config[dev_type])
				instr = module.Instrument(self.main_config[dev_type[:-7] + " Config File"])
				self.aux_devices[instr.name] = instr
				print("Successfully established communications with {}".format(instr.name))

				for sub_dev_name, main_dev_name in instr.get_sub_dev_names().items():
					if sub_dev_name in self.sub_dev_map.keys():
						raise KeyError("Key overlap. Two subdevices have same name. Curr sub_dev_map: {}. Key Name: {}".format(self.sub_dev_map,sub_dev_name))
					else:
						self.sub_dev_map[sub_dev_name] = main_dev_name
			else:
				print("Not using {}.".format(dev_type))

	def initialize_gc(self):
		gc = importlib.import_module(self.main_config["GC Module"])
		self.gc = gc.Instrument(self.main_config["GC Config File"])

	def initialize_logging(self):



		print("Beginning logging to: {} with poll time of {} seconds.".format(self.main_config["Condition Log File"],self.log_poll_time))

		#-----------------------Generating Header--------------------------#
		self.header = ["Time"]
		for dev_name,dev in self.aux_devices.items():
			dev_pv = dev.read_PV()
			dev_sp = dev.read_SP()
			for sub_dev_name in dev_sp.keys(): #ex. for each flow controller in the Bronkhorst flow controllers:
				self.header.append(sub_dev_name)
			for sub_dev_name in dev_pv.keys():
				self.header.append(sub_dev_name)


		#------------------------Writing Header to File---------------------#
		with open(self.logfile, 'w', newline='') as csvfile:
			writer = csv.DictWriter(csvfile,fieldnames=self.header)
			writer.writeheader()

		self.log(print_row=True)

	def log(self,print_row = False):

		#--------------------Appending to logfile with time and each SP and PV value--------------------#
		with open(self.logfile, 'a', newline='') as csvfile:
			writer = csv.DictWriter(csvfile,fieldnames=self.header)
			logrow = {"Time" : datetime.datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}
			for dev in self.aux_devices.values():
				for sub_dev_name, sub_dev_val in dev.read_SP().items():
					logrow[sub_dev_name] = sub_dev_val
				for sub_dev_name, sub_dev_val in dev.read_PV().items():
					logrow[sub_dev_name] = sub_dev_val

			#-------------------Passing values to output, logfile, storage--------------#			
			self.prev_log_row = logrow
			writer.writerow(logrow)
			if print_row:
				print("Log: {}".format(logrow))

	def online_setpt_change(self):
		try:
			df = pandas.read_csv(self.main_config["Online Setpt Change File"])

			if df.equals(self.prev_online_setpt_chg):
				return
			else:		
				self.prev_online_setpt_chg = df #Record the df so that we don't continually try to use one that still has an error.

				if df.shape[0] != 1:
					raise IndexError("Online Setpt Change File has {} rows of data and should only have 1".format(df.shape[0]))
				self.make_setpt_change(df.iloc[0,:])
				self.log(print_row=True)
		except IndexError as e:
			print(e)
			pass

		except KeyError as e:
			print("Unable to change setpts based on setpt file. Allowable device names include:\n{}\nOffending Name: {}\nError Message: {}".format(self.sub_dev_map.keys(),dev_with_new_sp,e))
			pass 

		except pandas.errors.EmptyDataError:
			pass #all is well, no new setpts

		except PermissionError:
			print("Collision btwn file save and pandas read. Will change SP on next iteration.")
	def make_setpt_change(self,next_setpts): #takes in a Pandas Series

				for dev_name in self.aux_devices.keys(): #for each device we're communicating with

					new_sp_dict = {}
					sub_devices = self.aux_devices[dev_name].get_sub_dev_names().keys() #get its subdevices
					for dev_with_new_sp in next_setpts.index: #for each device listed in setpt change file:

						if dev_with_new_sp not in self.sub_dev_map.keys():

							raise KeyError(dev_with_new_sp)
						if dev_with_new_sp in sub_devices: #if it is part of the overall device we've iterated to:
							if next_setpts[dev_with_new_sp] > (1.01*self.prev_log_row[dev_with_new_sp+" SP"]) or next_setpts[dev_with_new_sp] < (0.99*self.prev_log_row[dev_with_new_sp+ " SP"]): #if we differ from curr sp by more than 1%:
								new_val = float(next_setpts[dev_with_new_sp])
								new_sp_dict[dev_with_new_sp] = new_val

					if new_sp_dict != {}:#if we made any changes to setpts:
						for sub_dev, new_val in new_sp_dict.items():
							print("Changing setpt for: {} to {}...".format(sub_dev,new_val))

						if self.aux_devices[dev_name].write_SP(new_sp_dict): #if write_SP returns True
							print("Setpoints took successfully")




		
#If run as standalone file

if __name__ == '__main__':

	proceed = False
	print("\n")
	aux_comms = AuxComms()

	#--------------------------Verify log file location is correct------------------------------#
	while not proceed:
		answer = input("\nProgram will overwrite any log file stored at {}. Acknowledge log file location is correct (y/n): ".format(aux_comms.logfile))
		if answer == 'y':
			proceed=True 
		elif answer == 'n':
			raise ValueError("Log file location acknowledged as incorrect. Please fix and restart!")
		else:
			continue
		
	#-------------------------If using online setpts--------------------------------#
	if len(sys.argv) == 1:
		proceed = False
		while not proceed:
			answer = input("\nProgram will overwrite any file stored at {}. Acknowledge online setpt change file location is correct (y/n): ".format(aux_comms.main_config["Online Setpt Change File"]))
			if answer == 'y':
				proceed=True 
			elif answer == 'n':
				raise ValueError("Online setpt change file location acknowledged as incorrect. Please fix and restart!")
			else:
				continue
		with open(aux_comms.main_config["Online Setpt Change File"],'w') as f: #clear file
			pass
		print("To manually change the setpoint, modify the file at {} with the exact setpoints you want for each device.".format(aux_comms.main_config["Online Setpt Change File"]))

	#-------------------------If using offline setpts--------------------------------#
	else:

		
		#make sure each named subdevice is something we currently control and all columns of file have correct names for subdevices
		setpts = pd.read_csv(sys.argv[1])
		for i,sub_dev in enumerate(setpts.columns): 
			if sub_dev not in aux_comms.sub_dev_map.keys():
				if sub_dev != "Num_Datapts" and sub_dev != "Total Flow":
					raise ValueError("Subdevice {} found in file {} but not in subdevice map {}".format(sub_dev,sys.argv[1],aux_comms.sub_dev_map))
		aux_comms.setpt_file_exists = True
		
		#initialize run log file
		run_log_fname = asksaveasfilename(filetypes=[("CSV file","*.csv")])
		headers = list(setpts.columns)
		headers.append("runTimeStamp")
		headers.append("runID")
		pd.DataFrame(columns=headers).to_csv(run_log_fname,header=True) #save header to file as a check that it exists!


		#initialize GC and GC params
		aux_comms.initialize_gc()
		aux_comms.gc.check_for_new_run() #burn one check so that we now have the current runID stored for future checks
		num_datapts_remaining = 0 #num GC datapts at our current setpts
		next_setpt_row = 0



	aux_comms.initialize_logging()

	prev_time = time.time()
	while True:
		if (time.time() - prev_time) > aux_comms.log_poll_time: #logging
			prev_time = time.time()
			aux_comms.log(print_row=True)
			time.sleep(1)


		if aux_comms.setpt_file_exists: #if offline setpt changes:
			if T_timer_active:
				t_delta = time.time() - T_time_init
				if t_delta > 20:
					T_timer_active = False
				else:
					print("Waiting for Temp stabilization. Time since Temp change: {} seconds. ".format(t_delta))
			else:
				if aux_comms.gc.check_for_new_run(): #whenever there's a new run, write to run log
					num_datapts_remaining -= 1
					timestamp = aux_comms.gc.get_last_run_timestamp()
					time.sleep(1)
					runID = aux_comms.gc.get_last_run_ID()
					run_data = pd.Series({"runTimeStamp" : timestamp, "runID" : runID})
					log_row = next_setpts.append(run_data)
					pd.DataFrame(log_row).transpose().to_csv(run_log_file, mode='a', header=False)


				if num_datapts_remaining <= 0: #if we have no more required GC datapts at this set of conditions
					if next_setpt_row >= setpts.shape[0] #if we've reached the end of our setpts:
						pass #done with setpt changes, just log
					else:
						curr_T_setpt = next_setpts["T"]
						next_setpts = df.iloc[next_setpt_row,:]
						num_datapts_remaining = next_setpts["Num_Datapts"]
						total_flow = next_setpts["Total Flow"]
						sub_dev_setpts = next_setpts.drop(["Num_Datapts", "Total Flow"]) 
						aux_comms.make_setpt_change(sub_dev_setpts)
						if next_setpts["T"] != curr_T_setpt: #Temperature stabilization time
							T_timer_active = True
							T_time_init = time.time()
						next_setpt_row += 1

		else: #if online setpt changes
			if aux_comms.online_setpt_change(): #checks for and makes online_setpt_changes
				time.sleep(5)
			else:
				time.sleep(1)
		





