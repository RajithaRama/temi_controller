import collections

import numpy as np
import pandas as pd
import ethical_governor.blackboard.commonutils.cbr.cbr as cbr
import ethical_governor.blackboard.commonutils.cbr.vdm as vdm
from sklearn.preprocessing import OrdinalEncoder, PowerTransformer, MinMaxScaler


class CBRMedication(cbr.CBR):
    def __init__(self, k=3):
        super().__init__()
        self.data_encoded = None
        self.col_names = None
        self.data_original = pd.DataFrame()
        self.dist_feature_map = {}
        self.value_diff_mat = vdm.VDM()
        self.categorical_data_cols = ['med_name', 'med_type', 'state', 'user_response', 'time_of_day', 'action']
        self.numerical_data_cols = ['med_impact', 'no_of_missed_doses', 'time_since_last_reminder', 'no_of_followups', 'no_of_snoozes', 'follower_autonomy', 'follower_wellbeing', 'wellbeing_probability']
        self.list_data_cols = []
        self.categorical_encoder = OrdinalEncoder()

        # Features to be encoded using power transform
        self.p_transform_features = ['time_since_last_reminder', 'no_of_missed_doses', 'no_of_followups', 'no_of_snoozes']
        self.power_transformers = {}

        # Features to be encoded using min-max scaler
        self.min_max_features = ['med_impact']
        self.min_max_scaler = MinMaxScaler()

    def add_data(self, data):
        self.data_original = data
        self.data_original.index = self.data_original.case_id
        self.data_encoded = self.encode_dataset(data)
        self.data_encoded.index = self.data_encoded.case_id
        self.col_names = self.data_encoded.columns
        return self.col_names

    # def get_neighbours(self, query, k=3):
    #     q_col_names = query.columns
    #     distances = {}
    #
    #     query[query.columns.intersection(self.categorical_data_cols)] = self.encoder.transform(
    #         query[query.columns.intersection(self.categorical_data_cols)])
    #
    #     # get the subset of cases that have the features
    #     required_col_names = q_col_names.insert(0, 'case_id')
    #     required_col_names = required_col_names.insert(len(required_col_names), 'acceptability')
    #     subset_df = self.data_encoded[required_col_names].dropna()
    #
    #     # Tune value difference Metric for query
    #     self.value_diff_mat = vdm.VDM().fit(X=subset_df[q_col_names.intersection(self.categorical_data_cols)],
    #                                         y=subset_df['acceptability'])
    #
    #     data_inv = subset_df.T
    #     for col in data_inv.columns:
    #         vec_s = data_inv[col]
    #         distances.setdefault(self.pairwise_distance(vec_s[q_col_names], query.T[0]), []).append(vec_s['case_id'])
    #         # distances[self.distance(vec_s, query)] = vec_s['case_id']
    #
    #     neighbours = []
    #     while len(neighbours) < k:
    #         if len(distances[min(distances.keys())]) + len(neighbours) <= k:
    #             for case in distances[min(distances.keys())]:
    #                 neighbours.append(case)
    #             distances.pop(min(distances.keys()))
    #         else:
    #             i = len(neighbours)
    #             for case in distances[min(distances.keys())]:
    #                 if i > k:
    #                     break
    #                 neighbours.append(case)
    #                 i += 1
    #             distances.pop(min(distances.keys()))
    #     return neighbours

    def get_neighbours_with_distances(self, query, k=3, logger=None):
        q_col_names = query.columns
        distances = {}

        # preprocessing the query
        for cat_col in self.categorical_data_cols:
            try:
                categories = self.categorical_encoder.categories_[self.categorical_encoder.feature_names_in_.tolist().index(cat_col)]
                query[cat_col] = [categories.tolist().index(query[cat_col].values[0])]
            except ValueError:
                # For new labels in query time
                query[cat_col] = -1
            except KeyError:
                continue
        
        # power transform query features

        for feature in self.p_transform_features:
            try:
                feature_data = query[feature].to_numpy().reshape(-1, 1)
                power_transformer = self.power_transformers[feature]
                query[feature] = power_transformer.transform(feature_data).astype('float64')
            except KeyError:
                logger.warn('feature "{}" not found in query.'.format(feature))
        
        # Scale minmax features
        for feature in self.min_max_features:
            try:
                feature_data = query[feature].to_numpy().reshape(-1, 1)
                query[feature] = self.min_max_scaler.transform(feature_data)
            except KeyError:
                logger.warn('feature "{}" not found in query.'.format(feature))


        # get the subset of cases that have the features
        required_col_names = q_col_names.insert(0, 'case_id')
        required_col_names = required_col_names.insert(len(required_col_names), 'acceptability')
        subset_df = self.data_encoded[required_col_names].dropna()

        # Selecting the cases that evaluate the action in query
        subset_df = subset_df.loc[subset_df['action'] == query['action'][0]]

        # Tune value difference Metric for query
        self.value_diff_mat = vdm.VDM().fit(X=subset_df[q_col_names.intersection(self.categorical_data_cols)],
                                            y=subset_df['acceptability'])

        data_inv = subset_df.T
        for col in data_inv.columns:
            vec_s = data_inv[col]
            query_vec = query.T[0].infer_objects()
            distances.setdefault(self.pairwise_distance(vec_s[q_col_names], query_vec), []).append(vec_s['case_id'])
            # distances[self.distance(vec_s, query)] = vec_s['case_id']

        neighbours = []
        while len(neighbours) < k:
            min_dist = min(distances.keys())
            if len(distances[min_dist]) + len(neighbours) <= k:
                for case in distances[min_dist]:
                    neighbours.append((case, min_dist))
                distances.pop(min_dist)
            else:
                i = len(neighbours)
                for case in distances[min_dist]:
                    if i >= k:
                        break
                    neighbours.append((case, min_dist))
                    i += 1
                distances.pop(min_dist)
        return neighbours

    def pairwise_distance(self, a, b):
        col_names = a.index
        distances = []
        # print(a)
        # print(b)
        for col in col_names:
            if col in ['case_id', 'acceptability', 'action']:
                continue
            elif col in self.categorical_data_cols:
                distances.append(self.vdm_distance(col, a[col], b[col]))
            elif col in self.numerical_data_cols:
                distances.append(self.minkowski_distance(a[col], b[col], p=1))
            elif col in self.list_data_cols:
                distances.append(self.jaccard_distance(a[col], b[col]))
            elif type(a[col]) == bool:
                distances.append(1 if a[col] ^ b[col] else 0)
            else:
                continue
        return sum(distances)

    def encode_dataset(self, data):
        # Encoding categorical variables
        col_data = data[data.columns.intersection(self.categorical_data_cols)]
        data[data.columns.intersection(self.categorical_data_cols)] = self.categorical_encoder.fit_transform(X=col_data)

        
        # Encoding power transformed numerical variables
        for feature in self.p_transform_features:
            feature_data = data[feature].to_numpy().reshape(-1, 1)
            power_transformer = PowerTransformer().fit(feature_data)
            data[feature] = power_transformer.transform(feature_data).astype('float64')
            self.power_transformers[feature] = power_transformer

        # Encoding med_impact
        
        other_numeric_data = data[self.min_max_features].to_numpy().reshape(-1, 1)

        self.min_max_scaler = MinMaxScaler()
        data[self.min_max_features] = self.min_max_scaler.fit_transform(other_numeric_data)
    
        return data

    def vdm_distance(self, feature, a, b):
        distance = self.value_diff_mat.item_distance(feature=feature, a=a, b=b)
        return distance

    def minkowski_distance(self, a, b, p):
        if type(a) != type(b):
            # print(type(a), type(b))
            raise ValueError("a and b have different types.")

        distance = 0
        # print(a, b)
        if (type(a) == list) or (type(a) == tuple):
            if len(a) != len(b):
                raise ValueError("a and b are different in sizes.")
            for i in range(len(a)):
                distance += abs(a[i] - b[i]) ** p
            return distance ** (1 / p)
        else:
            return abs(a - b)

    def jaccard_distance(self, a, b):
        """
        :param a: list
        :param b: list
        :return: distance
        """

        def setify(lst):
            s = set()
            for item in lst:
                if isinstance(item, collections.abc.Hashable):
                    s.add(item)
                else:
                    s.add(setify(item))
            return frozenset(s)

        A = setify(a)
        B = setify(b)

        sym_dif = A.symmetric_difference(B)
        union = A.union(B)

        if len(union) > 0:
            distance = len(sym_dif) / len(union)
        else:
            distance = 0
        return distance

    def get_case(self, case_id):
        return self.data_original.T[case_id]

    def distance_weighted_vote(self, neighbours_with_dist, threshold, logger):
        """ Calculate the distance_weighted vote of k neighbours"""
        vote = {0: 0, 1: 0}
        intentions = {}
        for neighbour, distance in neighbours_with_dist:
            # Correction for smaller values
            if distance < 1 / 5:
                vote[self.get_case(neighbour)['acceptability']] += 5
                # intentions[self.get_case(neighbour)['acceptability']] = intentions.setdefault(self.get_case(neighbour)['acceptability'], []).append(self.get_case(neighbour)['intention'])
            else:
                vote[self.get_case(neighbour)['acceptability']] += 1 / distance
                # intentions[self.get_case(neighbour)['acceptability']] = intentions.setdefault(self.get_case(neighbour)['acceptability'], []).append(self.get_case(neighbour)['intention'])

            intentions.setdefault(self.get_case(neighbour)['acceptability'], []).append(
                self.get_case(neighbour)['intention'])
        max_vote = max(vote.values())

        # out 1 if there is a tie.
        class_won = 1 if vote[1] == max_vote else 0
        intention = set(intentions[class_won])

        return class_won, list(intention)

        # if vote > threshold:
        #     # maximum voted intention should be the biggest reason for acceptability == 1
        #     vote_max = max(intentions.values())
        #     intention_max = [i for i in intentions.keys() if intentions[i]==vote_max]
        #     return 1, intention_max
        # else:
        #     # minimum voted intention should be the biggest reason for acceptability == 0
        #     vote_min = min(intentions.values())
        #     intention_min = [i for i in intentions.keys() if intentions[i] == vote_min]
        #     return 0, intention_min
