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
				if "baudrate" in config.keys():
					eurotherm.serial.baudrate = config["baudrate"]
				if "timeout" in config.keys():
					eurotherm.serial.timeout = config["timeout"]

			#------------- Checking Communications------------#
			if self.eurotherm.read_register(config["test_register"],0) != config["test_value"]:
				raise ValueError("Test register value did not match expected value from JSON file.")

			#------------- Setting up PV and SP registers ----#
			self.PV_register = config["PV_register"]
			self.SP_register = config["SP_register"]
			
		except KeyError as e:
			raise Error("port, address, test_register, test_response, PV register, or SP register is not in JSON file.")
		except FileNotFoundError as e:
			raise FileNotFoundError("{} not a locatable file".format(config_file))
		except:
			print("Unexpected error: ",sys.exc_info()[0])
			raise

	def read_pv():
		try:
			return self.eurotherm.read_float(self.PV_register)
		except:
			raise

	def write_sp(new_sp):
		try:
			self.eurotherm.write_float(self.SP_register,new_sp)
			time.sleep(1)

			if self.read_sp() != new_sp: #checking to see if SP was written successfully
				time.sleep(1)
				raise Error("Setpoint write failed. Desired SP: {} Current SP: {}".format(new_sp,self.read_sp()))
			else:
				return True
		except:
			raise
	def read_sp():
		try:
			return self.eurotherm.read_float(self.SP_register)
		except:
			raise




			

