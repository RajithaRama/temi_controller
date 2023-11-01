import ethical_governor.blackboard.evaluator.evaluator as evaluator


class DeontologyEvaluator(evaluator.Evaluator):

    def __init__(self):
        super().__init__()

    def evaluate(self, data, logger):
        logger.info(__name__ + ' started evaluation using the data in the blackboard.')
        self.score = {}
        for action in data.get_actions():
            if data.get_table_data(action, 'is_breaking_rule'):
                self.score[action] = 0
            else:
                self.score[action] = 1
            logger.info('Desirability of action ' + str(action.value) + ' : ' + str(self.score[action]))
