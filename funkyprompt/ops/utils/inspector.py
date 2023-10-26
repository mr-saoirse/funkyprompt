"""
inspection is one of the main objectives of FunkyPrompt so we need to refine this guy in particular
for now its just a sketch
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

# unless told otherwise
DEFAULT_MODULE_ROOT = "funkyprompt.ops.examples"


class CallableModule(BaseModel):
    name: str
    namespace: typing.Optional[str]
    fullname: typing.Optional[str]
    interval_hours: typing.Union[typing.Any, None] = None
    interval_minutes: typing.Union[typing.Any, None] = None
    interval_days: typing.Union[typing.Any, None] = None
    options: typing.Optional[dict] = None


class FunctionDescription(BaseModel):
    """
    Typed function details for passing functions to LLMs
    """

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


def list_function_signatures(module, str_rep=True):
    """
    the describe the signatures of the methods in the module
    """
    stringify = lambda s: re.findall(r"\((.*?)\)", str(s))[0]
    members = inspect.getmembers(module)
    functions = [member for member in members if inspect.isfunction(member[1])]
    function_signatures = {name: inspect.signature(func) for name, func in functions}
    if str_rep:
        return [f"{k}({stringify(v)})" for k, v in function_signatures.items()]
    return function_signatures


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


def load_op(module, op="handler", default=None):
    """
    much of this library depends on simple conventions so can be improved
    in this case we MUST be able to find the modules
     'monolith.modules.<NAMESPACE>.<op>'
    these ops currently live in the controller so a test is that they are exposed to the module surface
    or we do more interesting inspection of modules
    """

    def default_handler(event, **kwargs):
        """
        this is the default when the module does not provide a handler
        """
        logger.info(f"<<<< Proxy handling for {module}.{op} >>>>")
        logger.info(f"processing {event}, {kwargs}")
        return {}

    MODULE_ROOT = f"{DEFAULT_MODULE_ROOT}."
    module = module.replace(MODULE_ROOT, "")
    module = f"{MODULE_ROOT}{module}"
    try:
        logger.debug(f"Loading function {op} from {module}")
        return getattr(__import__(module, fromlist=[op]), op)
    except Exception as ex:
        logger.warning(f"Failed loading function {op} from {module} - {repr(ex)}")
        if default:
            return default
        return default_handler
