import typing
from pydantic import Field, BaseModel, create_model, model_validator
from enum import Enum


class TextNodeType(Enum):
    summary: str = "SUMMARY"
    motif: str = "MOTIF"
    full: str = "FULL"
    fragment: str = "FRAGMENT"


class TextNode(BaseModel):
    fid: str
    text: str
    type: TextNodeType
    refs: typing.List[str] = []


class TextTreeModel(BaseModel):
    """
    How we represent text and text fragments
    """

    text: str
    nodes: typing.List[TextNode]
