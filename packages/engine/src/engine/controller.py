"""
A single-agent controller that is just a wrapper for a P controller
"""

import numpy as np


class SingleAgentController:
    """
    A super simple proportional (P) controller for a single agent.
    """
 
    def __init__(self, kp: float, magnitude_limit: float):
        self.kp = kp
        self.magnitude_limit = magnitude_limit

    def apply(
        self,
        current_position: np.typing.NDArray[np.float64],
        goal_position: np.typing.NDArray[np.float64]
    ) -> np.typing.NDArray[np.float64]:
        """
        Apply the controller returning the input velocity command.

        Args:
            current_position: The current position of the agent. (2,)
            goal_position: The desired goal position of the agent. (2,)

        Returns:
            The computed velocity command for the agent. (2,)
        """
        desired_velocity = self.kp * (goal_position - current_position)
        if np.linalg.norm(desired_velocity) > self.magnitude_limit:
            desired_velocity = desired_velocity / np.linalg.norm(desired_velocity) * self.magnitude_limit
        return desired_velocity
