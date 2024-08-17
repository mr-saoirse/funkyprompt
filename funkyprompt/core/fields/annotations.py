"""
Functions can be decorated for aiding resolution at runtime for LLMs
This supports stubbing patterns
"""

from pydantic import Field, BaseModel
from functools import partial
import typing

"""
[A] Provide some common shorthands for field annotations used with pydantic objects
"""

class AnnotationHelper:
    def __init__(self, model:BaseModel):
        type_hints = model.model_fields
        self.extras = {k : v.json_schema_extra for k,v in type_hints.items() if hasattr(v, 'json_schema_extra')}
        
    @property
    def typed_edges(self)->dict:
        """provide the field that contains edges and their type"""
        edges = {}
        for k,v in self.extras.items():
            if v and v.get('is_edge'):
               edges[k] = v.get('edge_type') 
        return edges

class SqlTypeFields(BaseModel):
    """things like varchar lengths"""

    varchar_length: typing.Optional[int] = Field(
        default=None,
        description="If a varchar length is used the field will be VARCHAR otherwise we might default to TEXT",
    )
    numeric_type: typing.Optional[tuple] = Field(
        default=None,
        description="Numeric types can be defined",
    )


def KeyField():
    """it is common to specify which field is the key"""
    return partial(Field, is_key=True)


def OpenAIEmbeddingField():
    """it is common to have text content or image content that can be embedded - openai will use system defaults"""
    return partial(Field, embedding_provider="openai")


def CLIPEmbeddingField():
    """it is common to have text content or image content that can be embedded - clip will use system defaults"""
    return partial(Field, embedding_provider="clip")

def RelationshipField(edge_type=None):
    """edge types tell us that we want to export edges relating source node to target nodes"""
    return partial(Field, is_edge=True, edge_type=edge_type)



"""
By partially invoking we recover the doc string for the Fields that can be used as normal
"""
KeyField = KeyField()
OpenAIEmbeddingField = OpenAIEmbeddingField()
CLIPEmbeddingField = CLIPEmbeddingField()
RelationshipField = RelationshipField()

class Example(BaseModel):
    """
    Here is an example annotation to use for reference and tests
    """

    id: str = KeyField(description="test")
    text: str = OpenAIEmbeddingField(description="example embedded property")


"""
[B] Provide some helpers to inspect type annotations. Uses include
- function signatures
- mapping pydantic objects to other formats

In some cases we apply conventions for funkyprompt that would not apply in general
"""
