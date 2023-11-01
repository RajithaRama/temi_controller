import numpy as np

import ethical_governor.blackboard.evaluator.evaluator as evaluator


class UtilitarianEvaluator(evaluator.Evaluator):

    def __init__(self):
        super().__init__()
        weight_dist = {'follower': 1, 'rest': 0.5}

    def evaluate(self, data, logger):
        logger.info(__name__ + ' started evaluation using the data in the blackboard.')
        self.score = {}
        for action in data.get_actions():
            desirability = 0
            follower_util = 0
            
            # for stakeholder in data.get_stakeholders_data().keys():
                # if stakeholder == 'robot':
                #     continue
            autonomy = data.get_table_data(action=action, column='patient_0_autonomy')
            wellbeing = data.get_table_data(action=action, column='patient_0_wellbeing')

            # if stakeholder == 'patient_0':
            # Autonomy focused utilitarian agent
            follower_util = (0.5*autonomy + 0.5*wellbeing)

            
            desirability = round(follower_util, 6)

            logger.info('Desirability of action ' + str(action.value) + ' : ' + str(desirability))
            self.score[action] = desirability

