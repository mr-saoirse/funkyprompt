from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from pydantic import BaseModel
from collections.abc import Iterator
from typing import Callable, Union, Any, Optional, List
from functools import partial
from funkyprompt import logger
import warnings
from funkyprompt.ops.utils.inspector import CallableModule, inspect_modules

EVENT_TYPE = Union[BaseModel, List[BaseModel], dict, List[dict]]

# im ignoring the apscheduler induced time zone warning (and everything else for now)
warnings.filterwarnings("ignore")


class ScheduledTask(BaseModel):
    name: str
    namespace: str
    runner: Callable
    hour: Union[Any, None] = None
    minute: Union[Any, None] = None
    day: Union[Any, None] = None


def invoke_task(
    name: str,
    event: Optional[EVENT_TYPE] = None,
    options: Optional[dict] = None,
):
    logger.info("Invoked")


def get_scheduled_jobs(
    module_iterator: Iterator[CallableModule],
) -> Iterator[ScheduledTask]:
    """
    We can inspect any modules for the callable contract
    by default inspect module in funkyprompt is used but any iterator can be used
    """
    logger.debug(f"Fetching tasks to schedule using supplied iterator")
    module_iterator = module_iterator or inspect_modules()
    for op in module_iterator:
        if op.interval_minutes or op.interval_days or op.interval_hours:
            yield ScheduledTask(
                name=op.name,
                namespace=op.namespace,
                # we just partially eval this just so the scheduler has something it can easily run
                # this will call an api e.g. rest with the right params
                runner=partial(invoke_task, name=op.namespace),
                # we specify how often we want to kick of this task
                minute=op.interval_minutes,
            )


def start_scheduler(module_iterator: Iterator[CallableModule] = None):
    """
    Start the scheduler. Load all the callable functions that have attributes for scheduling

    """
    scheduler = BlockingScheduler({"apscheduler.timezone": "UTC"})

    for task in get_scheduled_jobs(module_iterator=module_iterator):
        logger.info(f"<< Adding to schedule task {task} >>")
        scheduler.add_job(
            task.runner,
            CronTrigger(
                start_date="2023-1-1", hour=task.hour, minute=task.minute, day=task.day
            ),
            id=task.name,
            replace_existing=True,
            args=None,
        )

    logger.info("Starting blocking scheduler")
    scheduler.start()

    return scheduler
