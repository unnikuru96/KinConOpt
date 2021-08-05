#!/usr/bin/env python3""" Driver for Bronkhorst flow controllers, including simple test case """import serialimport timefrom datetime import datetimeimport sysimport csvimport os.pathfrom os import listdirfrom os.path import isfile, join#For email servicesimport smtplibfrom email.mime.multipart import MIMEMultipartfrom email.mime.text import MIMEText"""Created on Sat Feb  3 11:20:42 2018@author: ethanyoung"""class Reaction():    def __init__(self):        self.Controllers = []        self.Flows = {}        self.emerg_flows = {}        self.Times = []        self.input_files = []        self.open_ports = []        self.elapsed_time = 0        #Filenames        self.init_file = "./Settings/Filenames.txt"        self.reaction_file = ""        self.bronkhorst_file = ""        self.user_comm_file = ""        self.log_output_file = ""                 #Error settings        self.flow_wait_time = 1/60 #in hours        self.flow_dev_lim = 2        #Messages        self.rxn_end_msg = "Reaction successfully completed. Previous flows are being used until reset by user or next reaction."        self.chg_flow_err = "Error in microcontrollers achieving specified flow. No within specified error region within specified wait time."        self.chg_flows = "Flows successfully changed.."        self.subject_error = "REACTION ERROR: Error in bronkhorst program, shutting down program."        self.subject_update = "Reaction Update for Bronkhorst Program."                #Email Settings        self.emails = []        self.email = ""        '''#Email Settings        self.Email_Start_Run = True        self.Email_Flow_Switch  = True        self.Email_Error = True        self.Email_Finished_Run = True        #Log settings        self.Log_On_Screen = True        self.Log_Start_Run = True        self.Log_Flow_Switch = True        self.Log_Error = True        self.Log_Finish_Run = True        self.Log_Number_Saved = 7'''                #Constants        self.RXN_END = -1                    '''Initalize Bronkhorst controllers to 0: tests that they work'''    def initReactions(self):        for bh in self.Controllers:                        bh.set_control_mode()            #bh.set_flow(0)            time.sleep(1)            #print("Try")            #Confirms controllers successfully turn flow rate to 0            #if (bh.read_flow() != 0):            #    message = "Error with initializing controllers. Should be 0. Actual: " + str(bh.read_flow())            #    rxn.error(message)    '''Returns -1 if flows not within specified amount in specified time'''    def changeFlows(self, t):        t = float(t)        #Error in changing flows        if (t == -1):            for bh in self.Controllers:                flow = self.emerg_flows[bh.name]                bh.set_flow(flow)            return 0        else:                for bh in self.Controllers:                flow = self.Flows[bh.name][t]                #print("Set flow " + str(bh.name) + ": " + str(flow))                bh.set_flow(flow)                            #Confirms flow change was successful            #TODO: time.sleep(self.flow_wait_time * 60 * 60)            time.sleep(30)            for bh in self.Controllers:                act_flow = bh.read_flow()                exp_flow_low = self.Flows[bh.name][t] - self.flow_dev_lim                exp_flow_high = self.Flows[bh.name][t] + self.flow_dev_lim                #print(str(bh.name) + ": " + str(act_flow))                #Not within acceptable region                if ((act_flow < exp_flow_low) or (act_flow > exp_flow_high)):                    return -1                            return 0    '''    * This method initializes all filenames for the other setting files. These    * filenames can be edited in ./Settings/Filenames.txt    *     * Param: rfile: is the reaction_file    * Param: bfile: is the bronkhorst_file    * Param: ucfile: is the user_comm_file    *    * Return: 1 on success, <0 on failure (-1: could not find file, -2: error reading file)    '''    def setFilenames(self, rfile, bfile, ucfile, logfile):        #self.reaction_file = rfile[:-1]        self.bronkhorst_file = bfile[:-1]        self.user_comm_file = ucfile[:-1]        self.log_output_file = logfile                # Create log file for appending later        f = open(logfile,'w+')        f.close()            '''FILE_IO'''    '''    * This method initializes filenames of other setting files.    *    * Return: 1 on success, <0 on failure (-1: could not find file, -2: error reading file)    '''    def initFilenames(self):        #Opens init_file to get filenames        filenames_file = open(self.init_file, "r")        files = []        i = 1        #Extracts file names        for line in filenames_file:            i = i + 1            if (i % 2 == 0): #Weird \n in files                continue                        files.append(line)                version = 0        now = datetime.now()                #Create the ouput log file        while(True):            file_path = "./Logs/Reaction_" + str(now.month) + "_" + str(now.day) + "_" + str(now.year) + "-" + str(version) + ".txt"            if (os.path.exists(file_path)):                version += 1            else:                break                self.setFilenames(files[0], files[1], files[2], file_path)        '''    * This method initializes filenames of other setting files.    *    * Return: 1 on success, <0 on failure (-1: could not find file, -2: error reading file)    '''    def initSettings(self):        self.readBronkhorstSettings()        self.readCommSettings()        self.readReactionInputs()            '''    * This method reads the text file containing the current reaction details. The    * name of the text file is in config.py.    *     * Ex) Flow rates for each microcontroller and when to switch, etc..     *    * Return: 1 on success, <0 on failure (-1: could not find file, -2: error reading file)    '''    def readReactionInputs(self):        end_found = False                with open(self.reaction_file, newline='') as csvfile:             file = csv.reader(csvfile, delimiter=',', quotechar='|')               row = 0            col = 0                        for line in file:                row = row + 1                col = 0                curr_bh = ""                for val in line:                    if (len(val) < 1):                        continue                                        col = col + 1                    if "Controller" in val:                        continue                    if "Emergency" in val:                        continue                    #Times row                    if (row == 1):                        #Make sure there is an end point                        if "END" in val:                            end_found = True                            self.Times.append(-1) #Indicates end of reaction                            continue                        if val == '':                            continue                        #print("->" + str(val) + "<-")                        val = float(val)                        #Check correct format                        #if ((val%1) > .6 and val != -1):                        #    self.error("ReactionInputs: Cannot have elapsed times with minutes over 60.")                                                 #Makes sure flows don't change while waiting to check success                        #if ((val > 0) and ((val - self.Flows[curr_bh][0])/60 < self.flow_wait_time)):                        # TODO   self.error("Time between flow rate changes was too small. Must be greater than flow_wait_time")                        #print(val)                        self.Times.append(float(val))                                                continue                                        #Name of controller                    if (col == 1):                        found = False                        #print(val + " !")                        #Check that controller name is in Controllers                        for bh in self.Controllers:                            #print(str(bh.name))                            if (bh.name == val):                                found = True                                curr_bh = bh.name                                self.Flows[curr_bh] = {}                                break                        if (found == False):                            self.error("ReactionInputs: Controller name not same as in Bronkhorst Config File.")                        continue                                        #Emergency flows                    if (col == 2):                        self.emerg_flows[curr_bh] = float(val)                        continue                                            #Saves flow value at given time (-1 for the end time)                    self.Flows[curr_bh][self.Times[col-3]] = float(val)                                                                       if (end_found != True):            self.error("Input file must have an END in the time row in the cell after the last time.")            sys.exit()                '''    * This method reads the text file containing the settings for the user communication. The    * name of the text file is in config.py and is a constant user can't change.    *     * Ex) Settings for writing to log, email comunication settings, etc..    *    * Return: 1 on success, <0 on failure (-1: could not find file, -2: error reading file)    '''    def readCommSettings(self):        file = open(self.user_comm_file, "r")        for line in file:            if (len(line) < 2):                continue                        self.emails.append(line)            '''condition = line[:-1].split(':')[0].strip()            val = line[:-1].split(':')[1].strip()            if (val == "No"):                if (condition == "Email Started Run"):                   self.Email_Start_Run = False                elif (condition == "Email Flow Switch"):                    self.Email_Flow_Switch = False                elif (condition == "Email Error"):                    self.Email_Error = False                elif (condition == "Email Finished Run"):                    self.Email_Finished_Run = False                elif (condition == "Log Started Run"):                    self.Log_Start_Run = False                elif (condition == "Log Flow Switch"):                    self.Log_Flow_Switch = False                elif (condition == "Log Error"):                    self.Log_Error = False                elif (condition == "Log Finished Run"):                    self.Log_Finish_Run = False                elif (condition == "Display On-Screen Log"):                    self.Log_On_Screen = False            elif (condition == "Number Experiments Save Log"):                self.Log_Number_Saved = int(val)'''      '''    * This method reads the text file containing the settings for the bronkhorst controllers. The    * name of the text file is in config.py and is a constant user can't change.    *     * Ex) Names of controllers, port for each, number of control rates, etc..    *    * Return: 1 on success, <0 on failure (-1: could not find file, -2: error reading file)    '''    def readBronkhorstSettings(self):        file = open(self.bronkhorst_file, "r")                j = 0                name = ""        Port = ""        Max_Flow = ""        bh = ""        Node = ""        ser = 0        found = False        #Parses controller file         for line in file:            found = False            if (len(line) < 2):                continue            val = line.split(':')[1].strip()            #print("Value: " + val)            #Extracts components            if (j == 0):                name = val            if (j == 1):                Port = val                #print(Port)                                                                #Make sure port is open (TODO: Check that this works)                for p in self.open_ports:                    #print("Checking: " + str(p.port))                    if (p.port == Port):                        found = True                        ser = p                        #print("Found")                                if (found == False):                    #print("Here " + str(Port))                    #found = False                    ser = serial.Serial(baudrate = 38400, timeout=1)                    ser.port = Port                    #print(Port)                    ser.close()                    ser.open()                    self.open_ports.append(ser)                                                    if (j == 2):                Node = '{:02x}'.format(int(val))            if (j == 3):                Max_Flow = val                                #print("Controller: " + str(name) + " Port: " + str(Port) + " Flow: " + str(Max_Flow))                bh = Bronkhorst(Port, ser, Max_Flow, Node, name)                self.Controllers.append(bh)                j = -1                    j = j + 1    '''    * This method writes various information to a log file. Information written can    * be manipulated in the settings file.    *     * Ex) When reaction flows change, if set_flow and acutal_flow differ by certain amount, etc..    * Ex) Flow Change    *       > Curr Flow: 100 New Flow: 75    * Return: 1 on success, <0 on failure (-1: could not write to file)    '''    def writeToLog(self, email, message):        if (email):            if ("Error" in message):                subject = rxn.subject_error            else:                subject = rxn.subject_update                            rxn.emailAlert(subject, message)                    #Append the message to the log file        f = open(rxn.log_output_file,'a')        f.write("*** (Actual Time: " + str(datetime.now()) + ")\n" + message + "\n")        f.close()    '''    * This method prints out information before the reaction. Output is    * to the console, but could be redirected to a file. Output can be adjusted in     * the settings file.    *     * Ex) Set_flow = 10 Actual_flow = 10.1, etc..    *    * Return: 1 on success, <0 on failure    '''    def displayReaction(self):        message = ""                #TODO: Implement write initially to log        for t in self.Times:            if (t == -1):                    continue            message += "Time: " + str(t) + "..\n"            for bh in self.Controllers:                if (t == -1):                    continue                message += str(bh.name) + ": " + str(rxn.Flows[bh.name][t]) + " "                            message += "\n"                    self.writeToLog(False, message)                return message    def displayStatus(self, time):        print("After " + str("{0:.3f}".format(time)) + " hours.. (Actual Time: " + str(datetime.now()) + ")")                #Check that controller name is in Controllers        for bh in self.Controllers:            message = "Curr Flow: " + str("{0:.3f}".format(bh.read_flow())) + " for controller: " + str(bh.name)            print(message)                print("")    '''    * This method calls methods from SendEmail.py based on user preferences. Different    * emails can be sent on the current situation.    *     * Ex)Send an email when reaction complete, when flows switch, when error occurs, etc..    *    * Return: 1 on success, <0 on failure    '''    def emailAlert(self, subject, message):        #TODO: Implement them adding people to this        fromaddr = "hermansflowcontroller@gmail.com"        toaddr = self.email                 msg = MIMEMultipart()                 msg['From'] = fromaddr        msg['To'] = toaddr        msg['Subject'] = subject                 msg.attach(MIMEText(message, 'plain'))                         server = smtplib.SMTP('smtp.gmail.com', 587)        server.starttls()        server.login(fromaddr, "FlowController2018")        text = msg.as_string()        server.sendmail(fromaddr, toaddr, text)        server.quit()        pass        def print_emails(self):        j = 0        for i in self.emails:            if (i == None):                continue            if '\n' in i:                print(str(j) + ") " + i[:-1])            else:                print(str(j) + ") " + i)            j = j + 1        def error(self, message):        err_message = "Error: " + str(message)        #TODO: self.writeToLog(True, err_message)        self.writeToLog(True, err_message)        print(message)        print("Final Flows..")        rxn.displayStatus(-1)        sys.exit()    def display_reaction_files(self):        self.input_files = [f for f in listdir("./Reactions") if isfile(join("./Reactions", f))]                i = 0        for f in self.input_files:            print(str(i) + ": " + str(f))            i = i + 1    class Bronkhorst():    """ Driver for Bronkhorst flow controllers """    def __init__(self, port, serial, max_flow, node_channel, ID):        self.max_setting = max_flow        self.node = node_channel        self.ser = serial        self.name = ID        time.sleep(0.1)        pass    def comm(self, command):        """ Send commands to device and recieve reply """        self.ser.write(command.encode('ascii'))        time.sleep(0.1)        return_string = self.ser.read(self.ser.inWaiting())        return_string = return_string.decode()        return return_string    def read_setpoint(self):        """ Read the current setpoint """        read_setpoint = ':06' + self.node + '0401210121\r\n' # Read setpoint        response = self.comm(read_setpoint)        response = int(response[11:], 16) #Grabs last 4 hex numbers and converts to decimal        response = (float(response) / 32000.0) * float(self.max_setting) #response / 32000 gives percentage, then multiply by max setting        return response    def read_flow(self):        """ Read the actual flow """ #If 10 errors then returns 99        #print("Port: " + str(self.ser.port))        error = 0        while error < 10:            read_pressure = ':06' + self.node + '0401210120\r\n' # Read pressure            val = self.comm(read_pressure)            try:                val = val[11:] #Gets last 4 hex digits                num = int(val, 16) #Converts to decimal                pressure = (float(num)/ 32000) * float(self.max_setting) #Determines actual flow                break            except ValueError:                pressure = -99                error = error + 1                return pressure    def set_flow(self, setpoint):                """ Set the desired setpoint, which could be a pressure """        if setpoint > 0:            setpoint = (float(setpoint) / float(self.max_setting)) * 32000            setpoint = hex(int(setpoint))            setpoint = setpoint.upper()            setpoint = setpoint[2:].rstrip('L')            if len(setpoint) == 3:                setpoint = '0' + setpoint        else:            setpoint = '0000'                set_setpoint = ':06' + self.node + '010121' + setpoint + '\r\n' # Set setpoint        response = self.comm(set_setpoint)        response_check = response[5:].strip()                if response_check == '000005':            response = 'ok'        else:            response = 'error'                return response    def read_counter_value(self):        """ Read valve counter. Not fully implemented """        read_counter = ':06030401210141\r\n'        response = self.comm(read_counter)        return str(response)    def set_control_mode(self):        """ Set the control mode to accept rs232 setpoint """        set_control = ':05' + self.node + '01010412\r\n' #Sets control mode to value 18 (rs232)        response = self.comm(set_control)        return str(response)    def read_serial(self):        """ Read the serial number of device """                read_serial = ':1A' + self.node + '04F1EC7163006D71660001AE0120CF014DF0017F077101710A\r\n'        error = 0        while error < 10:            response = self.comm(read_serial)            response = response[13:-84]            if sys.version_info[0] < 3: # Python2                try:                    response = response.decode('hex')                except TypeError:                    response = ''            else: # Python 3                try:                    response = bytes.fromhex(response).decode('utf-8')                except ValueError:                    response = ''            if response == '':                error = error + 1            else:                error = 10        return str(response)    def read_unit(self):        """ Read the flow unit """        read_capacity = ':1A' + self.node + '04F1EC7163006D71660001AE0120CF014DF0017F077101710A\r\n'        response = self.comm(read_capacity)        response = response[77:-26]                try:            response = bytes.fromhex(response).decode('utf-8')        except AttributeError: # Python2            response = response.decode('hex')        return str(response)    def read_capacity(self):        """ Read ?? from device (Not implemented)"""        read_capacity = ':1A' + self.node + '04F1EC7163006D71660001AE0120CF014DF0017F077101710A\r\n'        response = self.comm(read_capacity)        response = response[65:-44]        #response = response.decode('hex')        return str(response)        '''Makes sure serial numbers are consistent with settings'''def serial_test(self, rxn):    for bh in rxn.Controllers:        bh.set_control_mode()        print("Name: " + str(bh.name) + " Serial Number: " + str(bh.read_serial()) + ' Flow rate: '              + str(bh.read_flow()))                print(bh.set_flow(0))        time.sleep(3)        print("New Flow: " + str(bh.read_flow()))if __name__ == '__main__':        rxn = Reaction()    '''Prompt user for proper reaction file'''    rxn.display_reaction_files()    answer = input("\n\nWhich reaction file would you like to use? (Indicate by typing the number)")    rxn.reaction_file = "./Reactions/" + str(rxn.input_files[int(answer)])        """Initialize the reaction and settings in files specified in filenames.txt"""    rxn.initFilenames()    rxn.initSettings()    '''Test correct setup and run simple test suite'''    rxn.initReactions()    '''Prompt user to make sure running correct reaction'''    print(rxn.print_emails())    answer = input("\n\nWhich email would you like to be the primary email for this reaction? (Specify the number)")    rxn.email = rxn.emails[int(answer)]        print(rxn.displayReaction())    answer = input("\n\nIs the correct reaction specifications? (y or n)")    if (answer == "n"):        sys.exit()    elif (answer != "y"):        rxn.error("Incorrect input for correct reaction response.")         print("Reaction Beginning...\n")    rxn.writeToLog(False, "\nStarting reaction for file: " + rxn.reaction_file + "\n")    #rxn.writeToLog(False, rxn.displayReaction())            next_switch = 0    next_index = 0    status_counter = 0        rxn.elapsed_time = 0    init = time.time() #In hours    rxn.displayStatus(rxn.elapsed_time)    #Main program loop    while(True):        status_counter += 1                #Time since the reaction began        rxn.elapsed_time = (time.time() - init)/(60*60) #In hours        #rxn.elapsed_time = time.time() - init        #print("Time: " + str(rxn.elapsed_time))                #Check if flow switch needed        if (rxn.elapsed_time > next_switch):                        #Update and record flow change, check for correct execution            if (rxn.changeFlows(next_switch) == -1):                #Set to emergency flows                rxn.changeFlows(-1)                rxn.error(rxn.chg_flow_err)                        #Writes new flow rates to log            message = rxn.chg_flows + "\n >>> After " + str(next_switch) + " hours, new flow rates are:"            for bh in rxn.Controllers:                message += " " + bh.name + ": " + str(rxn.Flows[bh.name][next_switch])            message += "\n"                            rxn.writeToLog(False, message)            #rxn.displayStatus(rxn.elapsed_time)            #Sets up next flow change            next_switch = rxn.Times[next_index]            next_index = next_index + 1                        #Detect end of reaction            if (next_switch == rxn.RXN_END):                rxn.displayStatus(rxn.elapsed_time)                                #Per request, controllers kept at previous conditions                rxn.writeToLog(True, rxn.rxn_end_msg)                sys.exit()                    #Prints current flows        if (status_counter == 5):            rxn.displayStatus(rxn.elapsed_time)            status_counter = 0        time.sleep(1) #TODO: Is this too long of a switch?       