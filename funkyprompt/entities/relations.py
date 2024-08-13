from pydantic import BaseModel, Field
import typing
import datetime
from funkyprompt.core import AbstractEdge

class ProjectTask(AbstractEdge):
    class Config:
        name: str = 'project_task'
        namespace: str = 'public'
        description: str = "When a user associates a task with a project or goal"
        
    """edges normally are weighted"""
    utility: typing.Optional[float] = Field(default=None, description="If the utility of the task can be estimated for the user's project or goals")
    effort: typing.Optional[float] = Field(default=None, description="An estimate of the difficulty of the task given what has been done so far")
   
class TaskResource(AbstractEdge):
    class Config:
        name: str = 'task_resource'
        namespace: str = 'public'
        description: str = "When a user associates a resource with a task"
        
    """edges normally are weighted"""
    utility: typing.Optional[float] = Field(default=None, description="If the utility of the resource can be estimated for the user's task")
   

class ResourcePerson(AbstractEdge):
    class Config:
        name: str = 'resource_person'
        namespace: str = 'public'
        description: str = "Associate a person with a resource for example a thought leader or owner"
    
    #we could sub class to create categories but the association is fine for now
    """edges normally are weighted"""
    reputation: typing.Optional[float] = Field(default=None, description="Teh reputation or rank of the person with respect to the resource")
    category: typing.Optional[str] = Field(default=None,description="How the person is associated with the idea - THINKER|WORKER|OWNER")
     
     
