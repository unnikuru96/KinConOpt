import importlib
import json
import sys
import pprint

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
			results, peaks = gc.analyze_run_offline(run_json,bp_json)
			print("\nAnalysis of GC Data")
			for major_key,val in results.items():
				print('---------------')				
				print(major_key)
				for key, minor_value in val.items():
					if (1*10**(-20) < minor_value < .01) or minor_value > 1000:
						print("     {}: {:.2e}".format(key, minor_value))
					else:
						print("     {}: {:.2f}".format(key, minor_value))
