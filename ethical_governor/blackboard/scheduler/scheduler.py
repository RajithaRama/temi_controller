from abc import ABC, abstractmethod


class Scheduler(ABC):

    def __init__(self, conf):
        self.conf = conf

    @abstractmethod
    def next(self):
        raise NotImplementedError("Please implement this method");
