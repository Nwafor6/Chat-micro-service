# lifecycle_manager.py
from fastapi import FastAPI
from loguru import logger

from app.production_task.task_executor import ProductionTaskExecutor


class LifecycleManager:
    """
    Handles application lifecycle events
    """

    def __init__(self, app: FastAPI):
        """
        Initialize the lifecycle manager with the provided FastAPI app.
        """
        self.app = app
        self.app.add_event_handler("startup", self.startup)
        self.app.add_event_handler("shutdown", self.shutdown)

    async def startup(self):
        """
        Startup proccess
        """
        logger.info("Performing startup tasks...")
        await self.run_production_tasks()
        logger.info("Startup tasks completed.")

    async def shutdown(self):
        """
        Shutdown proccess
        """
        logger.info("Performing shutdown tasks...")

    async def run_production_tasks(self):
        """
        Run production tasks
        """
        logger.info("Running production tasks...")
        executor = ProductionTaskExecutor()
        logger.info("Production tasks completed.")
        await executor.handle()
