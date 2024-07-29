import pytest
import typing
from uuid import UUID
from enum import Enum
from pydantic import BaseModel

from funkyprompt.core import Function


class AType(BaseModel):
    name: str


class EnumExample(Enum):
    choice_a = "a"
    choice_b = "b"


def test_function(
    a: str,
    b: int,
    c: typing.Optional[int | float],
    context: AType,
    l: typing.List[str] = None,
    l2: typing.List[str | dict] = None,
    choices: EnumExample = None,
    e: UUID | str = None,
    id: str = None,
    metadata: dict = None,
):
    """some details

    Args:
        a (str): _description_
        b (int): _description_
        c (typing.Optional[int | float]): _description_
        context (AType): _description_
        l (typing.List[str], optional): _description_. Defaults to None.
    """
    return True


def test_function_from_callable():
    """"""

    F = Function.from_callable(test_function)
    assert F("", 1, 1, None), "Unable to call the function when loaded"


def test_function_dumps_dict():
    """"""

    F = Function.from_callable(test_function)
    dict = F.get_function_description_dict()

    assert dict, "Unable to generate a dict for json schema from function"
    fc = dict.get("function")
    assert (
        fc is not None
    ), "the function property is missing from the dict when dumping json schema from function"
    assert fc["description"] == "some details\n", "wrong description"
    assert fc["name"] == "test_function", "wrong name"

    params = fc.get("parameters")
    assert params is not None, "missing `parameters` in function json schema dict"

    params = params.get("properties")
    assert (
        params is not None
    ), "missing `properties` in parameters of function json schema dict"

    assert len(params) == 10, "wrong number of parameters"


def test_dump_and_reload():
    F = Function.from_callable(test_function)

    """dumpy twice to test idempotence"""
    X = F.model_dump()
    X = F.model_dump()

    """reload"""

    F = Function(**X)
    assert (
        F.name == "test_function" and len(F.parameters) == 10
    ), f"""**Did not recover the serialized function correctly**
         - expected name of function to be 'test_function' and 10 params
         - got `{F.name}` / {len(F.parameters)}"""


"""TODO tests
- complex types are objects
- more types
- long doc strings
- missing type info - handle gracefully
- 
"""
