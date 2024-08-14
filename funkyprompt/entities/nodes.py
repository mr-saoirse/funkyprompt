from funkyprompt.core import AbstractEntity, typing, Field, OpenAIEmbeddingField
import datetime
from . import GenericEntityTypes
from pydantic import model_validator
from ast import literal_eval
from funkyprompt.core.utils.ids import funky_id
from funkyprompt.entities.relations import ProjectTask, TaskResource

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
        description="Optional category labels - should link to topic entities. When you are using labels you should always upsert or add labels to whatever is there already and never replace unless asked",
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

    project_name: typing.Optional[str] = Field(
        default_factory=list,
        description="The associated project",
        entity_name=GenericEntityTypes.PROJECT,
    )

    status: typing.Optional[str] = Field(
        default="TODO",
        description="The status of the project e.g. TODO, DONE",
    )
    
    resource_names: typing.Optional[typing.List[str]] = Field(
        default_factory=list,
        description="A list of resources (unique name) that might be used in the task",
        entity_name=GenericEntityTypes.RESOURCE,
    )
    actionable: typing.Optional[str] = Field(default=None, description="A Low|Medium|High estimate of actionability")
    utility: typing.Optional[float] = Field(default=None, description="If the utility of the task can be estimated for the user's project or goals")
    effort: typing.Optional[float] = Field(default=None, description="An estimate of the difficulty of the task given what has been done so far")
   
    def get_relationships(cls):
        """
        instance method provides a list of edges defined on the object such as ProjectTasks
        instance methods are not accessible to agents
        """
        return None

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

class Resource(AbstractEntity):
    class Config:
        name: str = "resource"
        namespace: str = "public"
        description: str = (
            """Resources are websites, data or people that can be involved in a project or task
               The may have unique domain names and they can be described
            """
        )
        
    uri: typing.Optional[str] = Field(description='a unique resource identifier if know')
    image_uri: typing.Optional[str] = Field(description='a representative image for the resource if known')
    category: str = Field(default=None,description="Resources can include IDEA|PERSON|WEBSITE|DATA|SOFTWARE and other categories")
    labels: typing.Optional[typing.List[str]] = Field(description='general labels to attach to the entity beyond category',default=None)
    
    

    
class TaskIdeaSummary(AbstractEntity):
    """this is a higher level example for testing the ideas
       the formatting of the type requires special care and then we will harden it in the pydantic type
       we should do a few different examples before we do because the model is very sensitive to the precise formatting of this
       however it should be something we can standardize for our scope
       we need something concise that expands child types
       also the dynamic data would be loaded based on some model or an entity lookup
    """
    class Config:
        name: str = 'task_idea_summary'
        namespace: str = 'public'
        description = """You are provided with a list of users prioritized goals and some data that could be useful.
Please summarize the main idea content and list resources in the form of entities and domains/websites.
Then produce a list of tasks as they relate to the users goals and projects.
"""
    
    """list resources | specific type -> people, companies, domain names, links, ideas"""
    content: str =  Field(default=None, description="Please summarize all the main useful ideas in the text")
        
    """lots of categorized resources - resource should also contain the category name so we can flat map db
       but we could override with an attribute if we really wanted to on our side - its just not clear what we want
       it might be an idea in this version to always be constrained to one child type entity and one child type relationships 
    """
    domain_names: typing.List[Resource] = Field(default_factory=list, description="a list of domain names, a category of resources")
    real_world_entities: typing.List[Resource] = Field(default_factory=list, description="a list of real world entities like people, websites, software, companies etc - these are a category of resources")
        
    """tasks which are a relationship type"""
    tasks: typing.List[Task] = Field(default_factory=dict, description="List tasks and the goal they map to. The goals of the user are listed and you suggest what actions they can take with respect to goals")
    
    @classmethod
    def _get_child_models(cls):
        """"""
        return [Resource]
    @classmethod
    def _get_prompting_data(cls):
        """
        this provides data injected into prompts for this type - can be dynamically loaded
        """
        return f"""
### User's prioritized goals
```text
1. create a business for personal knowledge management AI with rich support for databases of different types such as key-value, sql, vector and graph
2  write as much as possible and find good tools to manage my writing
3. understand the challenges people face today in terms of managing knowledge and personal growth
4. learn new AI methods and data modeling methods
5. build integrations from popular services and app
```
"""
    
    @classmethod
    def get_model_as_prompt(cls):
        """
        ---
        """
        #
        P = f"""
        
{cls._get_prompting_data()}

-----------------------------

_You will respond in Json using the following schema_

# Response schema

```python
class TaskIdeaSummary(BaseModel)
    id: typing.Union[str, uuid.UUID, NoneType] # A unique hash/uuid for the entity. The name can be hashed if its marked as the key
    name: <class 'str'> # The name is unique for the entity
    content: <class 'str'> # Please outline all the main useful ideas in the text in a lot of detail
    domain_names: typing.List[Resource] # a list of domain names, a category of resources
    real_world_entities: typing.List[Resource] # a list of real world entities like people, websites, software, companies etc - these are a category of resources
    tasks: typing.List[Task] # List tasks and the goal they map to. The goals of the user are listed and you suggest what actions they can take with respect to goals
```

#### This model uses child types below...

```python
class Resource(BaseModel)
    id: typing.Union[str, uuid.UUID, NoneType] # A unique hash/uuid for the entity. The name can be hashed if its marked as the key
    name: <class 'str'> # The name is unique for the entity
    url: typing.Optional[str] # the full url if given
    image_uri: typing.Optional[str] # a representative image for the resource if known
    category: <class 'str'> # Resources can include IDEA|PERSON|WEBSITE|DATA|SOFTWARE and other categories
    labels: typing.Optional[typing.List[str]] # general labels to attach to the entity beyond category
```


```python
class Task(BaseModel)
    name: <class 'str'> # The name is unique for the entity
    content: str # a description of the entity
    project: dict #the listed project or goal that this task would relate to - use the map of the `index` and `description` e.g. {{1:'my goal'}}
    utility_score: float # the possibly utility score with respect the users goals/project on a scale of 0 to 10
    actionability: str # the actionability of this task on a scale Low|Medium|High
    effort_days: int # the effort in days for this task
```

        """
        
        return P