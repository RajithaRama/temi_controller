from abc import ABC, abstractmethod


class Loader(ABC):

    @abstractmethod
    def load(self):
        raise NotImplementedError("Please implement this method.")
