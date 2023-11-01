import ethical_governor.blackboard.blackboard as bb


class EthicalGovernor:

    def __init__(self, conf):
        self.blackboard = bb.Blackboard(conf=conf)

    def recommend(self, env):
        self.blackboard.load_data(env)
        self.blackboard.run_tests()
        recommendations = self.blackboard.recommend()
        # print(recommendations)
        return recommendations
