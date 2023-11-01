import collections

import numpy as np
import pandas as pd
import ethical_governor.blackboard.commonutils.cbr.cbr as cbr
import ethical_governor.blackboard.commonutils.cbr.vdm as vdm
from sklearn.preprocessing import OrdinalEncoder, PowerTransformer


class CBRFollowing(cbr.CBR):
    def __init__(self, k=3):
        super().__init__()
        self.data_encoded = None
        self.col_names = None
        self.data_original = pd.DataFrame()
        self.dist_feature_map = {}
        self.value_diff_mat = vdm.VDM()
        self.categorical_data_cols = ['follower_seen_location', 'last_seen_location', 'robot_location', 'time',
                                      'action']
        self.numerical_data_cols = ['follower_time_since_last_seen', 'follower_health', 'follower_history', 'battery_level',
                                    'follower_autonomy', 'follower_wellbeing',
                                    'follower_availability']
        self.list_data_cols = ['not_follow_locations', 'instructions_given']
        self.encoder = OrdinalEncoder()

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
                categories = self.encoder.categories_[self.encoder.feature_names_in_.tolist().index(cat_col)]
                query[cat_col] = [categories.tolist().index(query[cat_col].values[0])]
            except ValueError:
                # For new labels in query time
                query[cat_col] = -1
            except KeyError:
                continue
        # query[query.columns.intersection(self.categorical_data_cols)] = self.encoder.transform(
        #     query[query.columns.intersection(self.categorical_data_cols)])
        query['battery_level'] = query['battery_level'] / 100

        try:
            query['follower_time_since_last_seen'] = self.power_transformer_last_seen.transform(
                query['follower_time_since_last_seen'].to_numpy().reshape(-1, 1))
        except KeyError:
            logger.warn('feature "follower_time_since_last_seen" not found in query.')

        try:
            query['follower_history'] = self.power_transformer_history.transform(
                query['follower_history'].to_numpy().reshape(-1, 1))
        except KeyError:
            logger.warn('feature "follower_history" not found in query.')

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
            distances.setdefault(self.pairwise_distance(vec_s[q_col_names], query.T[0]), []).append(vec_s['case_id'])
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
                    if i > k:
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
        data[data.columns.intersection(self.categorical_data_cols)] = self.encoder.fit_transform(X=col_data)

        # Scaling battery level
        data['battery_level'] = data['battery_level'] / 100

        # Transforming time since last seen
        last_seen_data = data['follower_time_since_last_seen'].to_numpy().reshape(-1, 1)
        self.power_transformer_last_seen = PowerTransformer().fit(last_seen_data)
        data['follower_time_since_last_seen'] = self.power_transformer_last_seen.transform(last_seen_data)

        # Transform history
        history_data = data['follower_history'].to_numpy().reshape(-1, 1)
        self.power_transformer_history = PowerTransformer().fit(history_data)
        data['follower_history'] = self.power_transformer_history.transform(history_data)

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
