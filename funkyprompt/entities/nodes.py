from funkyprompt.core import AbstractEntity, typing, Field, OpenAIEmbeddingField
import datetime
from . import GenericEntityTypes
from pydantic import model_validator
from ast import literal_eval
from funkyprompt.core.utils.ids import funky_id


class Project(AbstractEntity):
    class Config:
        name: str = "project"
        namespace: str = "public"
        description: str = (
            """Projects allow people to manage what they care about, their goals etc. 
            It is possible to add and search projects and build relationships between projects and other entities"""
        )

    name: str = Field(description="The unique name of the project")
    description: str = OpenAIEmbeddingField(
        description="The detailed description of the project"
    )
    target_completion: typing.Optional[datetime.datetime] = Field(
        default=None, description="An optional target completion date for the project"
    )
    labels: typing.Optional[typing.List[str] | str] = Field(
        default_factory=list,
        description="Optional category labels - should link to topic entities",
        entity_name=GenericEntityTypes.TOPIC,
    )

    @model_validator(mode="before")
    @classmethod
    def _types(cls, values):
        """we should be stricter in array/list types but here
        example of allowing lists as TEXT in stores
        """

        if isinstance(values.get("labels"), str):
            try:
                values["labels"] = literal_eval(values["labels"])
            except:
                pass

        return values


class Task(Project):
    class Config:
        name: str = "task"
        namespace: str = "public"
        description: str = (
            """Tasks allow people to manage small objectives as part of large projects. 
            It is possible to add and search tasks and build relationships between tasks and other entities"""
        )

    project: typing.Optional[str] = Field(
        default_factory=list,
        description="The associated project",
        entity_name=GenericEntityTypes.PROJECT,
    )

    status: typing.Optional[str] = Field(
        default="TODO",
        description="The status of the project e.g. TODO, DONE",
    )

    @model_validator(mode="before")
    @classmethod
    def _ids(cls, values):
        """tasks take ids based on their project and name
        it is up to the caller to ensure uniqueness
        """
        proj = values.get("project")
        name = f"{proj}/{values['name']}"
        values["id"] = funky_id(name)
        return values

    # TODO: im testing adding the inline task - but actually the agent should know this usually if we design things right (either the agent is Task or the planner provides the metadata)
    # TODO also testing moving crud to base class so that we can assume it on a type but using its schema and not the generic one in doc strings

    @classmethod
    def add(cls, task: "Task", **kwargs):
        """Save or update a task based on its task name as key

        #task model

        ```python
        class Task(BaseModel):
            name: str
            description: str
            project: Optional[str] = None
            labels: Optional[list[str]] = []
            target_completion: Optional[datetime]
        ```

        Args:
            task: The task object to add
        """
        from funkyprompt.services import entity_store

        if isinstance(task, dict):
            task = cls(**task)

        return entity_store(cls).update_records(task)

    @classmethod
    def set_task_status(cls, task_names: typing.List[str], status: str):
        """Move all tasks by name to the given status

        Args:
            task_names (typing.List[str]): list of one or more tasks for which to change status
            status (str): status as TODO or DONE
        """
        from funkyprompt.services import entity_store

        if task_names and not isinstance(task_names, list):
            task_names = [task_names]

        q = f"""UPDATE {cls.sql().table_name} set status=%s WHERE name = ANY(%s)"""

        return entity_store(cls).execute(q, (status, task_names))

    @classmethod
    def set_task_target_completion(
        cls, task_names: typing.List[str], date: str | datetime.datetime
    ):
        """Move all tasks by name to the given status

        Args:
            task_names (typing.List[str]): list of one or more tasks for which to change status
            date (str): the new date to complete the task
        """
        from funkyprompt.services import entity_store

        if task_names and not isinstance(task_names, list):
            task_names = [task_names]

        q = f"""UPDATE {cls.sql().table_name} set target_completion=% WHERE name = ANY(%)"""

        return entity_store(cls).execute(q, (date, task_names))

    @classmethod
    def run_search(
        cls,
        questions: typing.List[str] | str,
        after_date: typing.Optional[dict] | str = None,
    ):
        """Query the tasks by natural language questions
        Args:
            questions (typing.List[str]|str): one or more questions to search for tasks
            date (str): the new date to complete the task
        """
        from funkyprompt.services import entity_store

        return entity_store(cls).ask(questions, after_date=after_date)
