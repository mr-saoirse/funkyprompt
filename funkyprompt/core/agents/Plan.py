from funkyprompt.core import AbstractModel, AbstractEntity
import typing
from pydantic import Field, model_validator
import json


def create_lookup(
    data: typing.Dict[str, typing.Any]
) -> typing.Dict[str, typing.Dict[str, typing.Any]]:
    """in a DAG where we are being efficient with named refs, we can get a lookup of all nodes with this and then expand for pydantic"""
    lookup = {}

    def _traverse(node: typing.Dict[str, typing.Any]):
        if "plan_description" in node:
            if node["name"] not in lookup:
                lookup[node["name"]] = {}
            lookup[node["name"]].update(node)
        if "depends" in node:
            for dep in node["depends"]:
                _traverse(dep)

    _traverse(data)
    return lookup


def expand_refs(
    node: typing.Dict[str, typing.Any],
    lookup: typing.Dict[str, typing.Dict[str, typing.Any]],
) -> typing.Dict[str, typing.Any]:
    """in a DAG where we are being efficient with named refs, we can get a lookup of all nodes with this and then expand for pydantic using this function"""
    if "depends" in node:
        expanded_depends = []
        for dep in node["depends"]:
            dep_name = dep["name"]
            if dep_name in lookup:
                expanded_dep = expand_refs(lookup[dep_name], lookup)
                expanded_depends.append(expanded_dep)
            else:
                expanded_depends.append(dep)
        node["depends"] = expanded_depends
    return node


PLANNING_PROMPT = f"""Below is a schema for building a plan.
        I would like you to consider the functions provided and build a plan to solve the task.
        You should break the problem down into steps and consider;
        (a) what functions can be used in each step matching the correct entity to the most suitable function 
        (b) what strategy to use in each step
        (c) how results from one step can be embedded as questions to the next.
        
        Functions that can be called without other dependencies can have empty dependency list and only functions that need the result of another function should depend on the other function.
        When calling functions in later states, you should always pass the shared context or known entities as parameters to the stage.
            - For example if entities are needed in other stages, they should be passed in as parameters in later stages.
        When passing data from one step to the next we can embed data in the question. 
            - For example if we got a collection of data from one or more steps, we could ask a question such as given the data [insert data] [ask the question]
            
        The user will supply further instructions for the task."""


class PlanFunctions(AbstractModel):
    name: str = Field(
        description="fully qualified function name e.g. <namespace>.<name>"
    )
    description: str = Field(
        description="a description of the function preferably with the current context taken into account e.g. provide good example parameters"
    )
    rating: float = Field(
        description="a rating from 0 to 100 for how useful this function should be in context"
    )


class Plan(AbstractEntity):
    """
    this is a base class for a plan
    a plan is something that has a question and a schema
    the plan can be chained into a dependency model
    plans in a graph should have unique names
    """

    class Config:
        name: str = "plan"
        namespace: str = "core"
        description = PLANNING_PROMPT

    name: typing.Optional[str] = Field(
        description="The unique name of the plan node", default=None
    )

    plan_description: str = Field(
        description="The plan to prompt the agent - should provide fully strategy and explain what dependencies exist with other stages"
    )
    questions: typing.Optional[typing.List[str]] = Field(
        description="The question in this plan instance as the user would ask it. A plan can be constructed without a clear question",
        default=None,
    )
    extra_arguments: typing.Optional[dict] = Field(
        description="Placeholder/hint for extra parameters that should be passed from previous stages such as data or identifiers that were discovered in the data and expected by the function either as a parameter or important context",
        default=None,
    )
    functions: typing.Optional[typing.List[PlanFunctions]] = Field(
        description="A collection of functions designed for use with this context",
        default=None,
    )
    depends: typing.Optional[typing.List["Plan"]] = Field(
        description="A dependency graph - plans can be chained into waves of functions that can be called in parallel or one after the other. Data dependencies are injected to downstream plans",
        default=None,
    )

    @model_validator(mode="before")
    @classmethod
    def _expand(cls, values):
        """expand entity refs for pydantic model"""
        l = create_lookup(values)
        values = expand_refs(values, l)
        return values

    @classmethod
    def _get_prompting_data(cls):
        """
        This is provided for promptables i.e. model schema to prompt dump.
        These data will be injected into a large prompt

        """

        from funkyprompt.core import load_entities

        return f"""
        ## Available entity functions
        
        ```json
        {
            json.dumps(load_entities(),default=str)
        }
        ```
    """

    def search_functions(cls, questions: str | typing.List[str]) -> typing.List[dict]:
        """A planner can search for new functions to answer user questions if available functions do not suffice.
           If the questions seem orthogonal they should be split into multiple questions for multiple searches.

        Args:
            questions (str | typing.List[str]): one or more questions - more is better

        Returns:
            typing.List[dict]: a list of functions and their descriptions
        """
        from funkyprompt.services import entity_store
        from funkyprompt.core.functions import Function

        return entity_store(Function).ask(questions)
