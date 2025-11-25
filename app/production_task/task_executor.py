"""task executor"""

from datetime import datetime, timezone
from importlib import import_module

from loguru import logger

from app.core.config import settings
from app.models.production_task import ProductionTask
from app.production_task.base_task import BaseTask


class ProductionTaskExecutor:
    """
    Executor for handling and executing production tasks.

    This class is responsible for managing the execution of various production
    tasks by dynamically importing task classes and running their `handle` method.
    It checks whether a task has already been executed and if it should be run
    based on the current environment and execution status.

    Attributes:
        providers (list of str): List of fully qualified class paths for the tasks to be executed.
        task_model (ProductionTask): The model used to track the execution status of tasks.
    """

    providers = []

    def __init__(self):
        """
        Initializes the ProductionTaskExecutor instance.
        """

        self.task_model = ProductionTask
        self.app_env = settings.env

    def import_string(self, path: str):
        """
        Import a class from a string path.

        Args:
            path (str): Dotted path to the class

        Returns:
            class: The imported class
        """
        try:
            module_path, class_name = path.rsplit(".", 1)
            module = import_module(module_path)
            return getattr(module, class_name)
        except (ImportError, AttributeError) as exc:
            raise ImportError(f"Could not import '{path}'. {str(exc)}") from exc

    async def handle(self):
        """
        Executes all the tasks defined in the `providers` list.

        This method iterates over the list of task providers, imports each task
        class, checks if it has been executed previously, and if not, runs its
        `handle` method. It also logs the status of each task execution and
        updates the task's execution status in the database.
        """
        for provider_path in self.providers:
            try:
                provider_class = self.import_string(provider_path)
                executor = provider_class()

                if await self.check_provider_executed(provider_path, executor):
                    logger.info(f"{provider_path} already executed")
                    continue

                # Check environment restrictions
                if hasattr(executor, "envs") and executor.envs:
                    if self.app_env not in executor.envs:
                        logger.info(
                            f"{provider_path} not executed in {self.app_env} environment"
                        )
                        continue

                logger.info(f"Executing {provider_path}...")
                await executor.handle()
                await self.mark_provider_executed(provider_path, executor)
                logger.info(f"Executed {provider_path} Successfully")

            except Exception as e:
                logger.error(f"Error executing {provider_path}: {str(e)}")
                raise

    async def check_provider_executed(self, provider: str, executor: BaseTask) -> bool:
        """
        Checks if a task provider has been executed and if it has reached its maximum run count.

        Args:
            provider (str): The fully qualified class path of the task provider.

        Returns:
            bool: True if the task has been executed the maximum number of times, False otherwise.
        """
        try:
            # Scan for the task with the given provider name
            task = await self.task_model.first(
                task_name=provider,
            )

            logger.info(f"Task for {provider}")

            if task:
                return task.run_count >= executor.max_runs

            return False

        except Exception as e:
            logger.error("Error checking provider execution: %s", str(e))
            return False

    async def mark_provider_executed(self, provider: str, executor: BaseTask):
        """
        Marks a task provider as executed and updates its run count.

        Args:
            provider (str): The fully qualified class path of the task provider.
        """
        try:
            # Scan for existing task
            task = await self.task_model.first(
                task_name=provider,
            )

            if not task:
                # Create new task if it doesn't exist
                task = self.task_model(
                    task_name=provider, run_count=0, max_runs=executor.max_runs
                )

            # Update task execution status
            task.run_count += 1
            task.updated_at = datetime.now(timezone.utc)  # Set the current UTC time
            await task.save()

        except Exception as e:
            logger.error(f"Error marking provider as executed: {str(e)}")
            raise
