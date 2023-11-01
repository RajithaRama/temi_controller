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
            other_util = 0
            i = 0
            for stakeholder in data.get_stakeholders_data().keys():
                if stakeholder == 'robot':
                    continue
                autonomy = data.get_table_data(action=action, column=stakeholder + '_autonomy')
                wellbeing = data.get_table_data(action=action, column=stakeholder + '_wellbeing')
                availability = data.get_table_data(action=action, column='robot_availability')
                if stakeholder == 'follower':
                    # balanced utilitarian agent
                    # 1/1.5 for normalising
                    follower_util = (autonomy + wellbeing + availability)/3

                else:
                    i += 1
                    other_util += (autonomy + wellbeing)/1.2
            if other_util:
                other_util = other_util/i

            # if other_util + follower_util > 0.5:
            #     desirability = 1
            # elif other_util + follower_util < 0:
            #     desirability = 0
            # else:
                # desirability = round((other_util + follower_util), 6)
            desirability = round((other_util + follower_util), 6)

            logger.info('Other util:' + str(other_util) + ' follower util:' + str(follower_util))
            logger.info('Desirability of action ' + str(action.value) + ' : ' + str(desirability))
            self.score[action] = desirability

