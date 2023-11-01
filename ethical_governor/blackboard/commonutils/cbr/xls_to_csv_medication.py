import pandas as pd
import os

# CASE_BASE = 'casebase.json'
# df = pd.read_json(CASE_BASE, orient='records', precise_float=True)
#
# df.to_excel('data.xlsx')

CASE_BASE = 'data_medication.xlsx'
df = pd.read_excel(CASE_BASE, header=0, index_col=None, dtype={})


# remove duplicates
# feature_names = df.columns.tolist()
# feature_names.remove("case_id")
# df.drop_duplicates(subset=feature_names, keep='first', inplace=True)

# df.astype({"not_follow_locations": list,  "instructions_given": list})

print(df)
print(df.dtypes)

df.to_json('case_base_gen_medication.json', orient='records', indent=4)