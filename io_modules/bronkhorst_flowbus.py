import serial
import time
from datetime import datetime
import sys
import csv
import os.path
from os import listdir
from os.path import isfile, join

"""
This code was primarily adapted from code written by Ethan Young at UW-Madison. Nearly all the credit goes to them.

"""

class Instrument(self):
	#This method initializes the Instrument object which encapsulates the Controllers and methods that interact with them
	def __init__(self,config_file):

		self.flow_wait_time = 1/60 #in hours
        self.flow_dev_lim = 2
        self.emergency_flows = {}

		try:
			#------------- Configuring Instrument-------------#
			with open(config_file, 'r') as f:

				config = json.load(f)
				if len(config["controller_settings"]) != config["num_controllers"]: #checking to make sure correct # controllers configured
					raise ValueError("Expected {} controllers, but {} sets of controller configurations provided".format(config["num_controllers"],len(config["controller_settings"])))
				
				#generating the serial connection that each controller will use
				ser = serial.Serial(baudrate=config["connection_settings"]["baudrate"], timeout=config["connection_settings"]["timeout"])
                ser.port = config["connection_settings"]["Port"]
                ser.close()
                ser.open()

                #initializing each controller with its specific max flow, name, etc.
				for i in range(config["num_controllers"]): 
			        bh = Bronkhorst(config["connection_settings"]["Port"],
			        	ser,
			        	config["controller_settings"][i]["Max Flow"],
			        	config["controller_settings"][i]["Node"],
			        	config["controller_settings"][i]["Name"],
			        	config["controller_settings"][i]["Gas"],
			        	config["controller_settings"][i]["Correction Factor"],
			        	config["controller_settings"][i]["Emergency Flow"]
			        	)

			        bh.set_control_mode() #Sets control mode to accept RS-232 setpoints
			        self.emergency_flows[bh.name] = bh.emergency_flow
		            time.sleep(1)
                	self.Controllers.append(bh)		
			
		except KeyError as e:
			raise Error("At least one setting in JSON file not configured properly.")
		except FileNotFoundError as e:
			raise FileNotFoundError("{} not a locatable file".format(config_file))
		except:
			print("Unexpected error: ",sys.exc_info()[0])
			raise

	def read_flows(self):
		curr_flows = {}
		for bh in self.Controllers:
			curr_flows[bh.name] = bh.read_flow()
			if curr_flows[bh.name] == -99: #read_flow() method returns -99 if there is failure to read flow 10x
				raise Error("Flow reading failed at the level of the Bronkhorst class. Comms issue.") 
		return curr_flows

	def set_flows(self,flow_dict,emergency=False):
		for bh in self.Controllers:
			if flow_dict.get(bh.name) is not None: #if controller flow change is dictated in flow_dict
				bh.set_flow(flow_dict[bh.name])

		if not emergency:
			time.sleep(20)
	        for bh in self.Controllers:
	        	if flow_dict.get(bh.name) is not None:
		            act_flow = bh.read_flow()
		            exp_flow_low = flow_dict[bh.name] - self.flow_dev_lim
		            exp_flow_high = flow_dict[bh.name] + self.flow_dev_lim
		            #Not within acceptable region
		            if ((act_flow < exp_flow_low) or (act_flow > exp_flow_high)):
		            	print("Setpoints failed to set. Setting emergency flows.")
		                self.set_flows(self.emergency_flows,emergency=True)
		                raise Error("Emergency flows set due to failure in setting flows")


class Bronkhorst():
    """ Driver for Bronkhorst flow controllers """
    def __init__(self, port, serial, max_flow, node_channel, ID, gas, correction_factor,emergency_flow):
        self.max_setting = max_flow
        self.node = node_channel
        self.ser = serial
        self.name = ID
        self.gas = gas
        self.correction_factor = correction_factor
        self.emergency_flow = emergency_flow

        time.sleep(0.1)
        pass

    def comm(self, command):
        """ Send commands to device and recieve reply """
        self.ser.write(command.encode('ascii'))
        time.sleep(0.1)

        return_string = self.ser.read(self.ser.inWaiting())
        return_string = return_string.decode()
        return return_string



    def read_setpoint(self):
        """ Read the current setpoint """
        read_setpoint = ':06' + self.node + '0401210121\r\n' # Read setpoint
        response = self.comm(read_setpoint)
        response = int(response[11:], 16) #Grabs last 4 hex numbers and converts to decimal
        response = (float(response) / 32000.0) * float(self.max_setting) #response / 32000 gives percentage, then multiply by max setting
        return response



    def read_flow(self):
        """ Read the actual flow """ #If 10 errors then returns -99
        #print("Port: " + str(self.ser.port))
        error = 0
        while error < 10:
            read_pressure = ':06' + self.node + '0401210120\r\n' # Read pressure
            val = self.comm(read_pressure)

            try:
                val = val[11:] #Gets last 4 hex digits
                num = int(val, 16) #Converts to decimal
                pressure = (float(num)/ 32000) * float(self.max_setting) #Determines actual flow
                break

            except ValueError:
                pressure = -99
                error = error + 1
        
        return pressure


    def set_flow(self, setpoint):
        
        """ Set the desired setpoint, which could be a pressure """
        if setpoint > 0:
            setpoint = (float(setpoint) / float(self.max_setting)) * 32000
            setpoint = hex(int(setpoint))
            setpoint = setpoint.upper()
            setpoint = setpoint[2:].rstrip('L')

            if len(setpoint) == 3:
                setpoint = '0' + setpoint

        else:
            setpoint = '0000'
        
        set_setpoint = ':06' + self.node + '010121' + setpoint + '\r\n' # Set setpoint
        response = self.comm(set_setpoint)
        response_check = response[5:].strip()
        
        if response_check == '000005':
            response = 'ok'
        else:
            response = 'error'
        
        return response



    def read_counter_value(self):
        """ Read valve counter. Not fully implemented """
        read_counter = ':06030401210141\r\n'
        response = self.comm(read_counter)
        return str(response)

    def set_control_mode(self):
        """ Set the control mode to accept rs232 setpoint """
        set_control = ':05' + self.node + '01010412\r\n' #Sets control mode to value 18 (rs232)
        response = self.comm(set_control)
        return str(response)


    def read_serial(self):
        """ Read the serial number of device """        
        read_serial = ':1A' + self.node + '04F1EC7163006D71660001AE0120CF014DF0017F077101710A\r\n'
        error = 0
        while error < 10:
            response = self.comm(read_serial)
            response = response[13:-84]
            if sys.version_info[0] < 3: # Python2
                try:
                    response = response.decode('hex')
                except TypeError:
                    response = ''
            else: # Python 3
                try:
                    response = bytes.fromhex(response).decode('utf-8')
                except ValueError:
                    response = ''

            if response == '':
                error = error + 1
            else:
                error = 10

        return str(response)


    def read_unit(self):
        """ Read the flow unit """
        read_capacity = ':1A' + self.node + '04F1EC7163006D71660001AE0120CF014DF0017F077101710A\r\n'
        response = self.comm(read_capacity)
        response = response[77:-26]
        
        try:
            response = bytes.fromhex(response).decode('utf-8')
        except AttributeError: # Python2
            response = response.decode('hex')

        return str(response)


    def read_capacity(self):
        """ Read ?? from device (Not implemented)"""
        read_capacity = ':1A' + self.node + '04F1EC7163006D71660001AE0120CF014DF0017F077101710A\r\n'
        response = self.comm(read_capacity)
        response = response[65:-44]
        #response = response.decode('hex')
        return str(response)