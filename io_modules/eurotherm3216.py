import json #for config file
import sys
import time
import minimalmodbus



class Instrument():
	def __init__(self,config_file):
		try:
			


			#------------- Configuring Instrument-------------#
			with open(config_file, 'r') as f:
				config = json.load(f)
				self.eurotherm = minimalmodbus.Instrument(config["port"],config["address"])
				self.name = config["Name"]
				if "baudrate" in config.keys():
					self.eurotherm.serial.baudrate = config["baudrate"]
				if "timeout" in config.keys():
					self.eurotherm.serial.timeout = config["timeout"]

			#------------- Checking Communications------------#
			test_value = self.eurotherm.read_register(config["Test Register"],0) 
			if test_value != config["Test Value"]:
				raise ValueError("Test register value did not match expected value from JSON file. Got: {}. Expected: {}.".format(test_value,config["Test Value"]))

			#------------- Setting up PV and SP registers ----#
			self.PV_register = config["PV Register"]
			self.SP_register = config["SP Register"]
			
		except KeyError as e:
			raise KeyError("port, address, test_register, test_response, PV register, or SP register is not in JSON file. Error Msg: {}".format(e))
		except FileNotFoundError as e:
			raise FileNotFoundError("{} not a locatable file".format(config_file))
		except:
			print("Unexpected error: ",sys.exc_info()[0])
			raise

	def get_sub_dev_names(self):
		return {self.name : self.name}

	def read_PV(self):
		try:
			return {self.name + " PV": self.eurotherm.read_float(self.PV_register)}
		except:
			raise

	def write_SP(self,sp_dict): #{"subdevice name: new_sp_value"}
		try:
			self.eurotherm.write_float(self.SP_register,sp_dict[self.name])
			time.sleep(1)
			if self.read_SP()[self.name + " SP"] != sp_dict[self.name]: #checking to see if SP was written successfully
				time.sleep(1)
				raise IOError("Setpoint write failed. Desired SP: {} Current SP: {}".format(sp_dict[self.name],self.read_SP()[self.name+ " SP"]))
			else:
				return True
		except:
			raise
	def read_SP(self):
		try:
			return {self.name + " SP": self.eurotherm.read_float(self.SP_register)}
		except:
			raise




			

