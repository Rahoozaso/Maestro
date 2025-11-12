from abc import ABC, abstractmethod


class BaseAgent(ABC):

    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def run(self, *args, **kwargs):
        pass
