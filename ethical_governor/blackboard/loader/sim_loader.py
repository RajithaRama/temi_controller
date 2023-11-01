import ethical_governor.blackboard.loader.loader as loader


class SimLoader(loader.Loader):

    def __init__(self):
        super().__init__()

    def load(self, env):
        return env
