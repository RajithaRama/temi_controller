import numpy as np


class VDM:

    def __init__(self, k=1):
        """
        Implementation of Value Difference Metric.
        :param k: Exponent used to compute the distance between feature value.
        """
        self.target_classes = None
        self.k = k
        self.proba_per_class = {}

    def fit(self, X, y):
        """
        Computing prior probabilities of each class
        :param X: input feature data
        :param y: target class
        :return:
        """

        if len(X) != len(y):
            raise TypeError("X and y has different lengths.")

        self.target_classes = y.unique()

        for col in X.columns:
            class_proba = {}
            feature_data = X[col]
            for cls in feature_data.unique():
                if cls == np.NaN:
                    continue
                probs = []
                grouped_target = y[feature_data == cls]
                total = len(grouped_target)
                target_counts = grouped_target.value_counts()
                for target_class in self.target_classes:
                    try:
                        count = target_counts[target_class]
                    except KeyError:
                        count = 0
                    p = count / total
                    probs.append(p)

                class_proba[cls] = probs
            self.proba_per_class[col] = class_proba
        return self

    def item_distance(self, feature, a, b):
        """
        Given feature name and two different values, return the distance between them.
        :param feature: name of the feature
        :param a: value 1
        :param b: value 2
        :return: distance
        """
        distance = 0
        for i in range(len(self.target_classes)):
            try:
                distance += abs(self.proba_per_class[feature][a][i] - self.proba_per_class[feature][b][i]) ** self.k
            except KeyError:
                continue

        return distance
