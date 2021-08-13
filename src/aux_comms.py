import sys
import csv
import pandas
import time
import json
import importlib
import datetime

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
			logrow = {"Time" : datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
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
				self.prev_online_setpt_chg = df #Record the df so that we don't continually try to open one that we just opened.

				if df.shape[0] != 1:
					raise IndexError("Online Setpt Change File has {} rows of data and should only have 1".format(df.shape[0]))
				for dev_name in self.aux_devices.keys(): #for each device we're communicating with

					new_sp_dict = {}
					sub_devices = self.aux_devices[dev_name].get_sub_dev_names().keys() #get its subdevices
					for dev_with_new_sp in df.columns: #for each device listed in setpt change file:

						if dev_with_new_sp not in self.sub_dev_map.keys():

							raise KeyError(dev_with_new_sp)
						if dev_with_new_sp in sub_devices: #if it is part of the overall device we've iterated to:
							if df.iloc[0][dev_with_new_sp] > (1.01*self.prev_log_row[dev_with_new_sp+" SP"]) or df.iloc[0][dev_with_new_sp] < (0.99*self.prev_log_row[dev_with_new_sp+ " SP"]): #if we differ from curr sp by more than 1%:
								new_val = float(df.iloc[0][dev_with_new_sp])
								new_sp_dict[dev_with_new_sp] = new_val

					if new_sp_dict != {}:#if we made any changes to setpts:
						for sub_dev, new_val in new_sp_dict.items():
							print("Changing setpt for: {} to {}...".format(sub_dev,new_val))

						if self.aux_devices[dev_name].write_SP(new_sp_dict): #if write_SP returns True
							print("Setpoints took successfully")

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

		
#If run as standalone file

if __name__ == '__main__':

	proceed = False
	print("\n")
	aux_comms = AuxComms()

	#--------------------------Verify log file location and online setpt change file location is correct------------------------------#
	while not proceed:
		answer = input("\nProgram will overwrite any log file stored at {}. Acknowledge log file location is correct (y/n): ".format(aux_comms.logfile))
		if answer == 'y':
			proceed=True 
		elif answer == 'n':
			raise ValueError("Log file location acknowledged as incorrect. Please fix and restart!")
		else:
			continue

	proceed = False
	while not proceed:
		answer = input("\nProgram will overwrite any file stored at {}. Acknowledge online setpt change file location is correct (y/n): ".format(aux_comms.main_config["Online Setpt Change File"]))
		if answer == 'y':
			proceed=True 
		elif answer == 'n':
			raise ValueError("Online setpt change file location acknowledged as incorrect. Please fix and restart!")
		else:
			continue

	if len(sys.argv) > 1:
		raise NotImplementedError("Setpoint Control from File not implemented yet")
		aux_comms.setpt_file_exists = True

	else:
		with open(aux_comms.main_config["Online Setpt Change File"],'w') as f: #clear file
			pass

		print("To manually change the setpoint, modify the file at {} with the exact setpoints you want for each device.".format(aux_comms.main_config["Online Setpt Change File"]))




	aux_comms.initialize_logging()

	prev_time = time.time()
	while True:
		if (time.time() - prev_time) > aux_comms.log_poll_time:
			prev_time = time.time()
			aux_comms.log(print_row=True)
		
		if not aux_comms.setpt_file_exists: #if we allow online setpt changes
			if aux_comms.online_setpt_change():
				time.sleep(5)
			else:
				time.sleep(1)
		
		else:
			time.sleep(1)




