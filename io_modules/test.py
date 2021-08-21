import inficon_gc as ig
import json
import pandas as pd

with open("../tests/test_files/VSi_440C_C3ODH_40mL.json",'r') as run_f:
	run_json = json.load(run_f)

with open("../tests/test_files/VSi_bp_C3ODH_40mL.json",'r') as bp_f:
	bp_json = json.load(bp_f)

gc = ig.Instrument("../config_files/inficon_gc_config_propane_odh.json",online=False)

res,peaks,val_params = gc.analyze_run_offline(run_json,bp_json)
# for major_result_category, sub_result in res.items():
# 	for minor_result_category, minor_result in sub_result.items():
# 		res
res_df = pd.json_normalize(res,sep="_")
val_df = pd.json_normalize(val_params,sep="_")
print(pd.concat([res_df,val_df],axis=1))