"""
inspection is one of the main objectives of FunkyPrompt so we need to refine this guy in particular
for now its just a sketch - may move into model 
"""

import inspect
import typing
import re
from pydantic import Field, BaseModel
import json
import importlib
import pkgutil
import sys
from funkyprompt import logger
from enum import Enum
import funkyprompt
from functools import partial

# unless told otherwise
DEFAULT_MODULE_ROOT = "funkyprompt.ops.examples"


def call_api(endpoint, verb="get", **kwargs):
    """

    simple version tested for gets -> we will create a partial factory on the endpoint


    """
    import os
    import requests

    # KEY =
    # headers = {"Authorization": f"Bearer {KEY}", "Content-type": "application/json"}

    f = getattr(requests, verb)

    response = f(
        f"https://data.resmagic.io/{endpoint.lstrip('/')}",
        headers={},
        params=kwargs,
    )

    return response.json()


class CallableModule(BaseModel):
    name: str
    namespace: typing.Optional[str]
    fullname: typing.Optional[str]
    interval_hours: typing.Union[typing.Any, None] = None
    interval_minutes: typing.Union[typing.Any, None] = None
    interval_days: typing.Union[typing.Any, None] = None
    options: typing.Optional[dict] = None


class FunctionFactory(BaseModel):
    """
    this is used to reload functions and partially eval them for different contexts
    With the function description and factory we can satisfy the LLM interface and also generate functions over stores
    """

    name: str
    module: typing.Optional[str] = None
    partial_args: typing.Optional[dict] = Field(default_factory=dict)


class FunctionFactory(BaseModel):
    """
    this is used to reload functions and partially eval them for different contexts
    With the function description and factory we can satisfy the LLM interface and also generate functions over stores
    """

    name: str
    module: typing.Optional[str] = None
    # often contains store_name
    partial_args: typing.Optional[dict] = Field(default_factory=dict)


class FunctionDescription(BaseModel):
    """
    Typed function details for passing functions to LLMs/
    """

    name: str
    description: str
    parameters: dict
    raises: typing.Optional[str] = None
    returns: typing.Optional[str] = None
    function: typing.Any = Field(exclude=True)
    # serialize function ref. we need to load something with partial args
    factory: typing.Optional[FunctionFactory] = None
    weight: float = 0
    # function namespace and category or "subjects"

    @classmethod
    def restore(cls, data, weight=0, alias=None):
        """
        this is a temporary sketch - it would probably make more sense for the ops utils e.g. inspector to allow for restoring function descriptions
        will refactor as the ideas converge
        """

        if isinstance(data, str):
            data = json.loads(data)

        factory = data["factory"]
        args = factory.get("partial_args") or {}

        # temp - for now all functions will be restored as store functions
        if factory["name"] == "api_call":
            # proxy the function
            fn = partial(call_api, endpoint=args["endpoint"], verb=args["verb"])
            # set the function
            data["function"] = fn
            # call with all the stuff
            return FunctionDescription(**data)

        # this will change - currently we have store information but we should probably create a factory type instead
        elif args.get("store_type"):
            """
            Here we assume a certain pattern for the factory
            """
            from funkyprompt.io.stores import AbstractStore

            # need to be careful - we set him function descriptions to restore from the metadata level
            # think about how stores are restored - from functions or from registry
            row = {"metadata": data, "description": "a restored function for searching"}
            return AbstractStore.restore_from_data(row, as_function_description=True)
        # implement other store
        else:
            # assume its an op
            return describe_function(
                load_op(factory["name"], module=factory["module"]), weight=weight
            )

    def from_openapi_json(url_or_json: typing.Union[str, dict], endpoint, verb="get"):
        """
        Get the openapi spec, endpoint and make a function

        **Args**
            url_or_json: the spec, can be the url to the json, the json text or python dict
            endpoint: filter the endpoint e.g '/meta-one/meta-one
            verb: filter the verb
        """
        import requests

        if "http://" or "https://" in url_or_json:
            url_or_json = requests.get(url_or_json).json()
        elif isinstance(url_or_json, str):
            url_or_json = json.loads(url_or_json)

        def get_component(comp):
            # assume just a schema type
            s = comp.split("/")[-1]
            return s

        # assert leading and trailing / to save user stress
        schema = url_or_json["paths"][endpoint][verb]
        schema["name"] = schema["summary"].lower().replace(" ", "_").replace("__", "_")

        # treat params, and renaming
        def _treat(d):
            d.update(d["schema"])
            d["description"] = d.get("description", d.get("title", ""))
            # TODO we can pop the required from here and put them into a required list up one level
            return {k: v for k, v in d.items() if k in ["description", "type"]}

        schema["parameters"] = {p["name"]: _treat(p) for p in schema["parameters"]}

        factory = FunctionFactory(
            name="api_call", partial_args={"verb": "get", "endpoint": endpoint}
        )

        # the callable is like this
        args = factory.partial_args
        fn = partial(call_api, endpoint=args["endpoint"], verb=args["verb"])

        return FunctionDescription(**schema, function=fn, factory=factory)

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
                # i tried just leaving this but it seems more reliable to prompt in the function desc.
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


def is_pydantic_type(t):
    """
    determine if the type is a pydantic type we care about
    """

    try:
        from pydantic._internal._model_construction import ModelMetaclass
    except:
        from pydantic.main import ModelMetaclass

    return isinstance(t, ModelMetaclass)


def describe_function(
    function: typing.Callable,
    add_sys_fields: bool = False,
    augment_description: str = None,
    factory: FunctionFactory = None,
    alias: str = None,
    weight: int = 5,
) -> FunctionDescription:
    """
    Used to get the description of the method for use with the LLM
    This is only setup for a few test cases and not for general types
    assumes some Pydantic types or optional/primitives or returns object

    """
    type_hints = typing.get_type_hints(function)

    def python_type_to_json_type(python_type):
        """
        map typing info
        todo: implement enums
        diagram_request
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
        if is_pydantic_type(python_type):
            return python_type.schema()

        if issubclass(python_type, Enum):
            # assume uniform types
            delegate_type = type(list(python_type)[0].value)
            return python_type_to_json_type(delegate_type)
        else:
            return "object"

    def parse_args_into_dict(args_text):
        """
        parse out args with type mapping for the agent
        TODO: support more complex typing e.g. options and unions etc...
        """
        args_dict = {}

        for line in args_text.splitlines():
            parts = line.strip().split(":")
            if len(parts) == 2:
                param_name = parts[0].strip()
                param_description = parts[1].strip()
                assert (
                    param_name in type_hints
                ), f"The type hints are missing for parameter `{param_name}` - you should add it to your functions arg definition for this parameter or check the names of the args"
                T = type_hints[param_name]
                if hasattr(T, "__args__"):
                    # this is just for the optional case - not general case
                    T = T.__args__[0]
                # TODO: handle optional types e.g Optional[str]
                args_dict[param_name] = {
                    # assuming the name of the type matches between args and doc string
                    "type": python_type_to_json_type(T),
                    "description": param_description,
                }
                # for enums adds the choices
                if issubclass(T, Enum):
                    args_dict[param_name]["enum"] = [member.value for member in T]

        """
        we can optionally add system fields 
        """
        if add_sys_fields:
            args_dict["__confidence__"] = {
                "type": "string",
                "description": "Your confidence between 0 and 100 that calling this function is the right thing to do in this context",
            }
            args_dict["__context__"] = {
                "type": "string",
                "description": "Explain why you are calling this function",
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
    if augment_description:
        parsed_sections["description"] += f"\n{augment_description}"
    parsed_sections["name"] = alias or function.__name__

    if factory is None:
        factory = {
            "partial_args": {"type": "default"},
            "module": function.__module__,
            "name": function.__name__,
        }
    return FunctionDescription(
        **parsed_sections, function=function, factory=factory, weight=weight
    )


def list_function_signatures(module, str_rep=True):
    """
    the describe the signatures of the methods in the module
    """
    if module == None:
        module = funkyprompt.ops.examples
    stringify = lambda s: re.findall(r"\((.*?)\)", str(s))[0]
    members = inspect.getmembers(module)
    functions = [member for member in members if inspect.isfunction(member[1])]
    function_signatures = {name: inspect.signature(func) for name, func in functions}
    if str_rep:
        return [f"{k}({stringify(v)})" for k, v in function_signatures.items()]
    return function_signatures


def list_functions(module=None, description=True):
    """
    the describe the signatures of the methods in the module
    """
    if module == None:
        module = funkyprompt.ops.examples
    members = inspect.getmembers(module)
    functions = [member for member in members if inspect.isfunction(member[1])]

    if description:
        # because its a tuple we fetch the function to describe
        return [describe_function(f[-1]) for f in functions]

    return functions


def _get_module_callables(name, module_root="funkyprompt.ops.examples"):
    """
    an iterator for callable modules
    """
    MODULE_ROOT = f"{module_root}."
    fname = name.replace(MODULE_ROOT, "")
    namespace = f".".join(fname.split(".")[:2])
    for name, op in inspect.getmembers(
        importlib.import_module(fname), inspect.isfunction
    ):
        if name in ["generator", "handler"]:
            d = {
                "name": f"{namespace}.{name}",
                "fullname": f"{fname}.{name}",
                "namespace": namespace,
                "options": {} if not hasattr(op, "meta") else op.meta,
            }
            if hasattr(op, "meta"):
                # take non none values to override
                d.update({k: v for k, v in op.meta.items() if v is not None})
            yield CallableModule(**d)


def inspect_modules(
    module=None,
    filter=None,
) -> typing.Iterator[CallableModule]:
    """
    We go through looking for callable methods in our modules obeying some norms
    """
    path_list = []
    spec_list = []

    if module is None:
        from funkyprompt.ops import examples

        module = examples

    for importer, modname, ispkg in pkgutil.walk_packages(module.__path__):
        import_path = f"{module.__name__}.{modname}"
        if ispkg:
            spec = pkgutil._get_spec(importer, modname)
            importlib._bootstrap._load(spec)
            spec_list.append(spec)
        else:
            path_list.append(import_path)
            for mod in _get_module_callables(import_path):
                yield mod

    for spec in spec_list:
        del sys.modules[spec.name]


def inspect_modules_for_class_types(module=None, type_filter=None):
    """

    iterate over module for the type requested

    Example:
        import diagrams:
        from diagrams import Node
        list(inspect_modules_for_class_types(diagrams, Node))

    """
    path_list = []
    spec_list = []

    for importer, modname, ispkg in pkgutil.walk_packages(module.__path__):
        import_path = f"{module.__name__}.{modname}"
        if ispkg:
            spec = pkgutil._get_spec(importer, modname)
            importlib._bootstrap._load(spec)
            spec_list.append(spec)
        else:
            path_list.append(import_path)

            for name, obj in inspect.getmembers(importlib.import_module(import_path)):
                if inspect.isclass(obj) and issubclass(obj, type_filter):
                    yield import_path, name, obj

    for spec in spec_list:
        del sys.modules[spec.name]


def load_op(op, module=None):
    """
    much of this library depends on simple conventions so can be improved
    in this case we MUST be able to find the modules
     'monolith.modules.<NAMESPACE>.<op>'
    these ops currently live in the controller so a test is that they are exposed to the module surface
    or we do more interesting inspection of modules
    """

    if module is None:
        from funkyprompt.ops import examples

        module = examples

    if isinstance(module, str):
        module = importlib.import_module(module)

    return getattr(module, op)
