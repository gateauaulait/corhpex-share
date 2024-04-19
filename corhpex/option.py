from abc import ABC, abstractmethod

class Option(ABC):
    @staticmethod
    def of(var=None):
        return Nothing() if var is None else Some(var)

    @staticmethod
    def empty():
        return Nothing()

class AbstractOption:
    @abstractmethod
    def is_empty(self):
        pass

    @abstractmethod
    def is_some(self):
        pass

    @abstractmethod
    def unwrap(self):
        pass

    @abstractmethod
    def unwrap_or(self, val):
        pass

class Nothing(AbstractOption):
    def is_empty(self):
        return True

    def is_some(self):
        return False

    def unwrap(self):
        raise Exception("Try to use Nothing as something")

    def unwrap_or(self, val):
        return val

class Some(AbstractOption):
    def __init__(self, var):
        self.__value = var

    def is_empty(self):
        return False

    def is_some(self):
        return True

    def unwrap(self):
        return self.__value

    def unwrap_or(self, val):
        return self.__value
