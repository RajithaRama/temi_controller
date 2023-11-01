import pandas as pd

import yaml

pd.set_option("display.max_rows", None, "display.max_columns", None)


def load_yaml(input_yaml):
    with open(input_yaml, 'r') as fp:
        yaml_data = yaml.load(fp, Loader=yaml.FullLoader)
    return yaml_data


class Data:

    def __init__(self, data_input, conf):
        self._environment = data_input['environment']
        self._actions = [Action(i) for i in data_input['suggested_actions']]
        self._stakeholders = data_input['stakeholders']

        self._other_inputs = data_input['other_inputs']

        self._table_df = self.create_table(data_input=data_input, conf=conf)
        # print(self._table_df)

    def get_environment_data(self):
        return self._environment

    def get_actions(self):
        return self._actions

    def get_stakeholders_data(self):
        return self._stakeholders

    def get_stakeholder_data(self, stakeholder_id):
        return self._stakeholders[stakeholder_id]

    def get_table_data(self, action, column):
        return self._table_df.loc[action, column]

    def get_other_inputs(self):
        return self._other_inputs

    def put_table_data(self, action, column, value):
        self._table_df.at[action, column] = value

    def get_max_index(self, column):
        column_value = self._table_df[column]
        return column_value[column_value == column_value.max()].index.to_list()

    def log_table(self, logger):
        logger.info('\n' + str(self._table_df))

    def create_table(self, data_input, conf):
        columns = []
        # for key in conf["tests"].keys():
        #     if conf["tests"][key]["per_user_cols"]:
        #         for stakeholder in self.get_stakeholders_data().keys():
        #             for colname in conf["tests"][key]["output_names"]:
        #                 columns.append(stakeholder + '_' + colname)
        #     else:
        #         columns.extend(conf["tests"][key]["output_names"])

        columns.append('desirability_score')

        return pd.DataFrame(columns=columns, index=self._actions)

    def add_table_column(self, col_name, values=None):
        self._table_df[col_name] = values

    def get_table_col_names(self):
        return self._table_df.columns

    def get_data(self, path_to_data):
        data = None
        for step in path_to_data:
            if step == 'environment':
                data = self.get_environment_data()
            elif step == 'stakeholders':
                data = self.get_stakeholders_data()
            elif type(step) == list:
                # If a step is a list, retrive data from that location and use as that data as the key.
                temp_data = self.get_data(step)
                try:
                    data = data[temp_data]
                except (KeyError, TypeError):
                    data = None
            else:
                # print(step, path_to_data)
                try:
                    data = data[step]
                except (KeyError, TypeError):
                    data = None
        return data

class Action:
    def __init__(self, action):
        self.value = action

    def __str__(self):
        return "{}".format(self.value)
