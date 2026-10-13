"""
Abstract base class for all actions providing a common set of methods
and attributes
"""

from abc import ABC, abstractmethod


class Action(ABC):
    @abstractmethod
    def time_left(self, current_tick: int) -> int:
        """
        Returns the number of ticks remaining for the action to complete.
        """
        ...
