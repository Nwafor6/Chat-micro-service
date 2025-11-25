from abc import ABC, abstractmethod


class BaseTask(ABC):
    """
    Abstract base class for production tasks.

    This class provides a template for defining production tasks that can be
    executed in different environments such as production, local, and development.
    Subclasses must implement the `handle` method to define the specific task behavior.

    Attributes:
        envs (list of str): A list of environment names where the task can be executed.
    """

    # The environments where the task can be executed
    envs = ["production", "local", "dev"]

    # The maximum number of times the task can be run
    max_runs = 1

    @abstractmethod
    async def handle(self):
        """
        Executes the production task.
        """
        raise NotImplementedError
