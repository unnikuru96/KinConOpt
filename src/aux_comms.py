import sys
import csv
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
		self.setpt_file_exists = False
		sys.path.append('../io_modules/') 

		with open("../config_files/main_config.json", 'r') as f:
			self.main_config = json.load(f)

		self.log_poll_time = float(self.main_config["Log Poll Time"]) #in seconds
		self.logfile = self.main_config["Condition Log File"]


		print("Initializing Auxiliary communications (flow, temp, etc.):")
		self.aux_devices = {}
		for dev_type in ["Flow Module","Temp Module"]:
			if self.main_config[dev_type] != "":
				print("Using {}: {}. Establishing communications...".format(dev_type,self.main_config[dev_type]))
				module = importlib.import_module(self.main_config[dev_type])
				self.aux_devices[dev_type] =module.Instrument(self.main_config[dev_type[:-7] + " Config File"])
				print("Successfully established communications with {}".format(self.main_config[dev_type]))
			else:
				print("Not using {}.".format(dev_type))
				self.aux_devices[dev_type] = None

	def initialize_logging(self):

		print("Beginning logging to: {} with poll time of {} seconds.".format(self.main_config["Condition Log File"],self.log_poll_time))

		#-----------------------Generating Header--------------------------#
		self.header = ["Time"]
		for dev_type,dev in self.aux_devices.items():
			if dev is not None:
				dev_sp = dev.read_sp()
				dev_pv = dev.read_pv()
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
		with open(self.logfile, 'a', newline='') as csvfile:
			writer = csv.DictWriter(csvfile,fieldnames=self.header)
			logrow = {"Time" : datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
			for dev in self.aux_devices.values():
				if dev is not None:
					for sub_dev_name, sub_dev_val in dev.read_sp():
						logrow[sub_dev_name] = sub_dev_val
					for sub_dev_name, sub_dev_val in dev.read_pv():
						logrow[sub_dev_name] = sub_dev_val
			writer.writerow(logrow)
			if print_row:
				print("Log: {}".format(logrow))
#If run as standalone file

if __name__ == '__main__':

	proceed = False
	print("\n")
	if len(sys.argv) > 1:
		print("Beginning setpoint control from: {}. (Not Implemented Yet)".format(sys.argv[1]))

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

	aux_comms.initialize_logging()



	prev_time = time.time()
	while True:
		if (time.time() - prev_time) > aux_comms.log_poll_time:
			aux_comms.log(print_row=True)
		time.sleep(1)




