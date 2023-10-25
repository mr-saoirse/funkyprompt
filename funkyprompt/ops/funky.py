import typing
import re
from pydantic import Field, BaseModel
import json


def is_pydantic_type(t):
    """
    determine if the type is a pydantic type we care about
    """

    try:
        from pydantic._internal._model_construction import ModelMetaclass
    except:
        from pydantic.main import ModelMetaclass

    return isinstance(t, ModelMetaclass)


class FunctionDescription(BaseModel):
    """ """

    name: str
    description: str
    parameters: dict
    raises: str
    returns: str
    function: typing.Any = Field(exclude=True)

    def pop_object_types(cls, d):
        """
        this is prompt engineering to describe function calls
        """
        objects = {}
        desc = ""
        for param, param_description in d.items():
            # this is the schema type check
            param_type = param_description["type"]
            if isinstance(param_type, dict):
                objects[param] = param_type
                # replace the description with something that points to the schema
                # i tried just leaving this but it seems more reliable to prompt in the function desc
                # at least at the time of writing
                d[param] = {
                    "type": "object",
                    "description": "This is a complex Pydantic type who's schema is described in the function description",
                }
        for param_name, v in objects.items():
            desc += f"The parameter [{param_name}] is a Pydantic object type described below: \n"
            desc += f"json```{json.dumps(v)}```\n"
        return desc

    def function_dict(cls, function_alias=None):
        """
        describe the function for the LLM
        this is the openAI flavour

        a function alias is useful in case of name collisions
        """
        d = cls.dict()
        object_descriptions = cls.pop_object_types(d["parameters"])
        return {
            "name": function_alias or d["name"],
            "description": f"{d['description']}\n{ object_descriptions}",
            "parameters": {"type": "object", "properties": d["parameters"]},
        }


def describe_function(
    function: typing.Callable,
) -> FunctionDescription:
    """
    Used to get the description of the method for use with the LLM


    """
    type_hints = typing.get_type_hints(function)

    def python_type_to_json_type(python_type):
        """
        map typing info
        """
        if python_type == int:
            return "integer"
        elif python_type == float:
            return "number"
        elif python_type == str:
            return "string"
        elif python_type == bool:
            return "boolean"
        # for pydantic objects return the schema
        elif is_pydantic_type(python_type):
            return python_type.schema()
        else:
            return "object"

    def parse_args_into_dict(args_text):
        """
        parse out args with type mapping for the agent
        """
        args_dict = {}

        for line in args_text.splitlines():
            parts = line.strip().split(":")
            if len(parts) == 2:
                param_name = parts[0].strip()
                param_description = parts[1].strip()
                args_dict[param_name] = {
                    # assuming the name of the type matches between args and doc string
                    "type": python_type_to_json_type(type_hints[param_name]),
                    "description": param_description,
                }

        return args_dict

    docstring = function.__doc__
    parsed_sections = {}

    sections = re.split(r"\n(?=\s*\*\*)", docstring)

    for section in sections[1:]:
        match = re.match(r"\s*\*\*\s*(.*?)\s*\*\*", section)
        if match:
            section_name = match.group(1)
            section_content = re.sub(
                r"\s*\*\*\s*" + section_name + r"\s*\*\*", "", section
            ).strip()
            if section_name.lower() in ["args", "params", "arguments", "parameters"]:
                parsed_sections["parameters"] = parse_args_into_dict(section_content)

            else:
                parsed_sections[section_name.lower()] = section_content

    parsed_sections["description"] = sections[0].strip()
    parsed_sections["name"] = function.__name__

    return FunctionDescription(**parsed_sections, function=function)


def save_type(code_str, namespace="default", add_crud_ops=True):
    """
    Save a type which is a pydantic class under the modules_home/namespace/
    the Crud is a RAG op set for getting columnar and vector data
    we can use conventions to generate ops that load the given stores to retrieve typed objects for use in agent systems
    those methods can be extended e.g. to load data from other subscriptions
    """

    # exceptions for parsing errors
    my_type = eval(code_str)

    path = my_type.get_path()

    with open(path, "w") as f:
        f.write(code_str)


def load_type(entity_name, namespace="default"):
    """
    the entity name can be fully qualified in which case we ignore the namespace, otherwise we qualify with passed namespace
    module_home/namespace/entity
    """
    pass
