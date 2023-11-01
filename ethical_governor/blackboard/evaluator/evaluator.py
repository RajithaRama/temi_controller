from abc import ABC, abstractmethod


class Evaluator(ABC):

    def __init__(self):
        self.score = {}

    @abstractmethod
    def evaluate(self, data, logger):
        """ Should evaluate the actions using the data in the blackboard and write the results to the self.score
            dictionary as follows
                - action 1: score
                - action 2: score
                ...
        """
        raise NotImplementedError("Please implement this method")

    def get_results(self):
        return self.score
