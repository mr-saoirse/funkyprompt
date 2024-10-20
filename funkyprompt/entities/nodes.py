from funkyprompt.core import AbstractEntity, AbstractContentModel, typing, Field, OpenAIEmbeddingField,RelationshipField
import datetime
from . import GenericEntityTypes
from pydantic import model_validator
from ast import literal_eval
from funkyprompt.core.utils.ids import funky_id
from funkyprompt.entities.relations import ProjectTask, TaskResource
from funkyprompt.core import utils

class Project(AbstractEntity):
    class Config:
        name: str = "project"
        namespace: str = "public"
        description: str = (
            """Projects allow people to manage what they care about, their goals etc. 
            It is possible to add and search projects and build relationships between projects and other entities"""
        )
 
    #TODO we need some context of user qualifier for key lookups and other queries. It could be an internal thing to the system
    #the agent does not need to know the user context but when saving AbstractUserEntity we could qualify the name as user/name 
    # and when resolving in he entity resolver we could "try" both keys i.e. the qualified one. For now for testing its ok to be single tenant
    name: str = Field(description="The unique name of the project")
    description: str = OpenAIEmbeddingField(
        description="The detailed description of the project"
    )
    target_completion: typing.Optional[datetime.datetime] = Field(
        default=None, description="An optional target completion date for the project"
    )
    labels: typing.Optional[typing.List[str] | str] = RelationshipField(
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
    def set_task_target_completion_date(
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

        """could set these to upserts for cases where actually its not there"""
       
        """we should make these operations idempotent and work in contexts where the thing does not exist - check what the unique id should be resolved to e.g. name.user->id""" 
        # q = f"""
        # INSERT INTO {cls.sql().table_name} (name, target_completion)
        # VALUES (%s, %s)
        # ON CONFLICT (name) 
        # DO UPDATE SET target_completion = EXCLUDED.target_completion
        # """

        q = f"""UPDATE {cls.sql().table_name} set target_completion=%s WHERE name = ANY(%s)"""

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
    labels: typing.Optional[typing.List[str]] = RelationshipField(description='general labels to attach to the entity beyond category',default=None)
    
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
    
    
"""form filling reference implementation
commonly we will want to collect data over time and its not obvious how to reliably do this without losing information over time. 
We rely on the reasoning ability of the agent and implement the pattern on faith for now
"""
class PersonPreferences(AbstractEntity):
    class Config:
        name: str = "person_preferences"
        namespace: str = "public"
        description: str = (
            """This is an example of a form filling pattern. The users preferences are updated over time. 
            Generally you should augment and extend the description of the person to create a nice overall summary that does not drop important information.
            Any concise facts that do not belong in the description could be added as attributes in the `misc_attributes` section if there is value to having a key property. Do not guess attributes and only added guessed attributes under the misc attributes section
            If you are given information about a user/person, you can update their details and preferences with this object.
            Entities are updated as type 4 slowly changing dimensions where we store and audit the user-agent conversation separately and we maintain current state in this object
            but its important not to overwrite any useful information but instead use an intelligent merge strategy.
            There are various fields that should be upserted for the user during conversation and there may be functions that can be called to save or lookup other details.
            It is important to consider the context of the user's preference when performing some tasks.
            You should be careful to unique identify a person. It is good to normalize names to title Case and observe ownership case e.g toms or tom's probably refers to the person Tom.
            
            When adding related entities you should add them as references of the form S/C where S is a specific entity and C is a category. Please save these as `graph_paths`
            If asked to list or count the preferences in the system you can run a search for this too. Generally you should try to run a search unless asked meta questions about the agent abilities.
            """
        )

    name: typing.Optional[str] = Field(description="users name - good practice to always title case and remove any possession or plurals. For example toms or tom's should be mapped to Tom", default=None)
    email: typing.Optional[str] = Field(description='users email',default=None)
    description: typing.Optional[str] = OpenAIEmbeddingField(description='A detailed description of the person, their social network, interests etc. it is very important to retain all information that you gather and dont overwrite important details. Use an intelligence merge strategy', default=None)
    occupation: typing.Optional[str] = Field(description='persons occupation or role', default=None)
    favorite_topics: typing.Optional[typing.List[str]] = Field(default=None,description="A list of broad categories of interests the user has")
    date_of_birth: typing.Optional[datetime.date] = Field(default=None)
    life_goals:  typing.Optional[typing.List[str]] = Field(default=None,description="A list of medium to long term ambitions the user has")
    misc_attributes: typing.Optional[dict] = Field(default=None, description="Any concise factual attributes that do not fit neatly into an existing field e.g. the name of a pet. Dont put long form details here but instead add to description. Please supply a dict or something that can be parsed to a dict")
    related_entities: typing.Optional[dict] = RelationshipField(default=None, 
                                                                description="Any entities (by name) that are referenced can be replicated here with a short description of how they relate")
    
    @model_validator(mode="before")
    @classmethod
    def _types(cls, values):
        if values.get('life_goals'):
            values['life_goals'] = utils.coerce_list(values['life_goals'] )
        if values.get('favorite_topics'):
            values['favorite_topics'] = utils.coerce_list(values['favorite_topics'] )
        if values.get('misc_attributes'):
            values['misc_attributes'] = utils.coerce_json(values['misc_attributes'] )
        if values.get('related_entities'):
            values['related_entities'] = utils.coerce_json(values['related_entities'] )
        return values
    
    
    
class Diary(AbstractContentModel):
    class Config:
        namespace: str = 'public'
        name: str = 'diary'
        description:str = """ Your job is to summarize the text based on the users interests using Markdown but do not fence the markdown. You can do this by reproducing the main contain including web links. You can use a special markdown format or MTags to categorize the text.

These MTags are of the link format [A/B (Weight)](A/B) where B is one of the user’s broad preferences and A is a sub category of your choice and Weight is a score between 0 and 1 about the relevance. This creates a path between a user and the sub category and sub broad category in two hops.
You can use MTags both to group the summary into sections and to add highlights to part of the text. For example within paragraphs you can add MTags beside the text to show its importance.

The user’s interests are Business, Technology, Personal Development (includes time management and productivity) and you should only use these for instances of A. The user is also specifically interested in the idea of the value of information in a world where we are overloaded and overwhelmed by too much information and how we can build tools to control information value based on user intent.
Please maintain a detailed format of the content including related resources. Any web links are very important to maintain.

When asked about the diary you can use the run_search method to find entries and you can also observe the special graph_path tags to find similar results especially if a deeper analysis is required.

 """

    @classmethod
    def visit_site_and_summarize(cls, uri: str, context:str=None):
        """
        Visit the site and use an internal agent to summarize the text in some context.
        The context is important to manage the utility of the information at the source.
        
        Args:   
            uri: the web ury to scrape and summarize
            context: the optional context to add for summarization
        """
        
        from funkyprompt.core.utils.parsing.web import scrape_text
        from funkyprompt import summarize
        text = scrape_text(uri)
        
        text = f"""# Summary of {uri}
{text}
        """
        
        return summarize(text, context)
    
    #may move this to entity later
    @classmethod
    def explore_similar_by_graph_path_tags(cls, graph_paths: str):
        """Given some interesting tags which we call graph_paths, you can lookup similar entries by those tags
           An example tag would be an area of interest like Robotics/AI where this provides a path between a specific category like robotics in the field of AI 
           
           Args:
            graph_paths: the tag in the format A/B given   
        
        """
        from funkyprompt.core.utils.parsing import json_loads
        from funkyprompt.core import logger
        
        """TODO - this shows we are not parsing models properly from the database if the tags are not lists"""
        graph_paths = json_loads(graph_paths)
        
        logger.debug(f"Exploring tags {graph_paths=}")
        from funkyprompt.services import entity_store

        return entity_store(cls).graph.query_by_path(graph_paths)
        
        
class Summary(AbstractContentModel):
    class Config:
        namespace: str = 'public'
        name: str = 'summary'
        description:str = """Maintain summaries as a separate node"""
          

"""temporary - we would override this with the database entry"""
class Notes(AbstractContentModel):
    class Config:
        name: str = "Notes"
        namespace: str = "public"
        description: str = (
            """This is a proxy for the Notes markdown agent which can be used to read, save and search for notes
            """
        )