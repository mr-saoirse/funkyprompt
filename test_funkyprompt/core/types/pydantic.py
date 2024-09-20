import typing
from funkyprompt.core import AbstractModel
from pydantic import Field
import typing

class GChild(AbstractModel):
    name: str
        
class TestChildType(AbstractModel):
    name: str
    value: int
    g: GChild
        
class TestModel(AbstractModel):
    """desc"""
    class Config:
        name: str = 'test_model'
        namespace: str = 'testing'
        description:str = "this is an entity description but also an agent description"
            
    name: str = Field( description="This is the name desc")
    content: str = Field(description="This is the content desc")
    is_ok: typing.Optional[bool] = Field(default=None, description="An optional bool")
    lists : typing.Optional[typing.List[dict]]     = Field(description="some list type that is optional", default_factory=list)
    metadata: dict = Field(description="Metadata dict - not optional")
    child_list: typing.Optional[typing.List[TestChildType]]


"""
worth generating tests for inspection methods later as this will become critical
"""

def test_generate_markdown():
    """
    We will settle on a markdown agent format and the pydantic should map consistently to the format
    """
    
    from funkyprompt.core.types.pydantic import  get_markdown_description
 

    markdown = get_markdown_description(TestModel) 
    
    """for now just assert does not below up and later we can test content"""
    
    assert markdown is not None
