import pandas as pd
import os
import ast

# CASE_BASE = 'casebase.json'
# df = pd.read_json(CASE_BASE, orient='records', precise_float=True)
#
# df.to_excel('data.xlsx')
def str_to_list(cell):

    if cell is not None:
        print(type(cell))
        var = ast.literal_eval(cell)
    else:
        var = None
    return var

CASE_BASE = 'data_telepresence.xlsx'
df = pd.read_excel(CASE_BASE, header=0, index_col=None, na_filter=False,dtype={"other_patient_locations": list})
df = df.replace({'': None})

# remove duplicates

# feature_names = df.columns.tolist()
# feature_names.remove("case_id")
# df.drop_duplicates(subset=feature_names, keep='first', inplace=True)

df[["on_call", "receiver_seen", "receiver_preference", "worker_seen", "worker_preference", "other_patient_seen"]] = df[["on_call", "receiver_seen", "receiver_preference", "worker_seen", "worker_preference", "other_patient_seen"]].astype(bool)
df["other_patient_locations"] = df["other_patient_locations"].apply(str_to_list)
df[["caller_autonomy", "receiver_wellbeing", "receiver_privacy", "worker_privacy", "other_resident_privacy"]] = df[["caller_autonomy", "receiver_wellbeing", "receiver_privacy", "worker_privacy", "other_resident_privacy"]].astype(float)



# df = pd.read_excel(CASE_BASE, header=0, index_col=None, keep_default_na=False, dtype={"other_patient_locations": list, 
#     "on_call": bool, 
#     "receiver_seen": bool,	
#     "receiver_preference": bool, 
#     "worker_seen": bool,
#     "worker_preference": bool,
#     "other_patient_seen": bool})
# df.astype({
#     "other_patient_locations": list, 
#     "on_call": bool, 
#     "receiver_seen": bool,	
#     "receiver_preference": bool, 
#     "worker_seen": bool,
#     "worker_preference": bool,
#     "other_patient_seen": bool
# })

# df = df.replace({'': None})
# df["other_patient_locations"] = df["other_patient_locations"].astype(list)

print(df)
print(df.dtypes)

df.to_json('case_base_gen_telepresence.json', orient='records', indent=4)