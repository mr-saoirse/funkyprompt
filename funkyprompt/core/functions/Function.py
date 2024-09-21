"""
The function classes are used to provide runtime context of any callable thing
Functions can also be saved in a registry and searched by their description
In this file there are some function related helper types

1. FunctionCall: trivially wraps the name and args to a function call
2. FunctionParameter: describes a parameter name, type, and details
3. FunctionMetadata: describes a function and wraps parameters
4. Function: The main class represents a Function entity 
"""

from pydantic import Field, BaseModel, PrivateAttr, model_validator, model_serializer
from funkyprompt.core import AbstractEntity
from funkyprompt.core import types as core_types, AbstractEntity
from funkyprompt.core.types.inspection import resolve_signature_types, TypeInfo
from funkyprompt.core.fields.annotations import OpenAIEmbeddingField
from funkyprompt import LanguageModelProvider
import docstring_parser
import typing
import re
from funkyprompt.core.utils.openapi import ApiEndpoint

"""for example open ai does not allow some stuff like dots"""
REGEX_ALLOW_FUNCTION_NAMES: str = (
    r"[^a-zA-Z0-9_]"  # n = re.sub(regex_allow_names, "", n) if regex_allow_names else n
)
MAX_FUNCTION_NAME_LENGTH = 64
MAX_FUNCTION_DESCRIPTION_LENGTH = 1024


DESCRIPTION = f"""Functions provide an interface over resources/tools that a language model can use.
Functions can be API alls, runtime python functions, database client etc and it really does not matter which is which.
The important thing is functions provide metadata (doc strings) about how they should be used along with parameter descriptions
With this information a language model can plan over functions and invoke functions to answer user questions and solve problems.
"""


class FunctionCall(BaseModel):
    name: str
    arguments: str | dict


class FunctionParameter(BaseModel):
    """simple model for function parameters"""

    name: str
    is_required: bool = True
    description: str = Field(description="The parameter description")
    type: str = Field(description="The json schema type of the parameter")
    enum_options: typing.Optional[typing.List[str]] = Field(
        description="enums can provide option hints", default_factory=list
    )
    # format or mode if its some thing we need

    @model_serializer()
    def dump(self):
        """make more compact"""
        d = dict(vars(self))
        if not d.get("enum_options"):
            d.pop("enum_options")
        return d

    @classmethod
    def from_type_info(cls, type_info: TypeInfo, description: str):
        """the parameter descriptions are merged with annotations to produce the parameter info"""
        data = dict(vars(type_info))
        data["type"] = core_types.PYTHON_TO_JSON_MAP.get(data["type"], "object")
        if type_info.is_list:
            data["type"] = "list"

        data["description"] = f"{description}"
        return FunctionParameter(**data)

    def to_json_spec(cls, **kwargs):
        """
        dump in a json schema format ala openai
        https://cookbook.openai.com/examples/how_to_call_functions_with_chat_models
        """
        d = {"type": cls.type, "description": cls.description}
        if cls.enum_options:
            d["enums"] = cls.enum_options
        return {cls.name: d}


class FunctionMetadataParser(BaseModel):
    """simple model for function metadata - its a `Function` subset just to factor out parsing"""

    name: str = Field(description="function name")
    description: str = Field(
        description="the function description as per the docstring"
    )
    parameters: typing.List[FunctionParameter] = Field(
        default_factory=list, description="structured list of parameters"
    )

    @classmethod
    def parse_metadata(
        cls, fn: typing.Callable, alias: str = None, augment_description: str = None
    ) -> "FunctionMetadataParser":
        """
        parses some expected doc string formats and produces a description and parameter list
        the best practice of type annotations and good doc strings is assumed here

        the external lib supports some stand doc styles
        https://github.com/rr-/docstring_parser
        "Currently support ReST, Google, Numpydoc-style and Epydoc docstrings."

        Args:
            fn: the callable function
            alias: an optional alias to rename the function
            augmented_description: an optional extra context to add to the function
        """

        """for now use the external library or add custom parsers"""

        # TODO: support complex types as parameters in the most efficient way either adding them to the doc string prompt or kwargs them out in the signature

        def s_combine(*l):
            return "\n".join(i for i in l if i)

        p = docstring_parser.parse(fn.__doc__)
        description = s_combine(
            p.short_description, p.long_description, augment_description
        )
        parameter_descriptions = {p.arg_name: p.description for p in p.params}

        """function name or alias"""
        name = alias or fn.__name__
        """using type annotations get the names and types of parameters with some other info"""
        parameters = resolve_signature_types(fn)
        """map from our type-info schema which is basically the same 
           - the descriptions are merged in from doc strings"""
        parameters = [
            FunctionParameter.from_type_info(p, parameter_descriptions.get(p.name))
            for p in parameters
        ]
        return FunctionMetadataParser(
            name=name, description=description, parameters=parameters
        )


class Function(AbstractEntity):
    """a Function is a core entity in `funkyprompt`
    - map apis and databases etc as functions
    - search for functions
    - load and invoke
    - pass descriptions to language models
    """

    class Config:
        name: str = "function"
        namespace: str = "core"
        description = DESCRIPTION

    name: str = Field(description="the fully qualified function name")
    description: str = Field(
        description="the function description as in doc strings and as used to prompt"
    )
    searchable_description: typing.Optional[str] = OpenAIEmbeddingField(
        description="extended content used primarily for searching (vector search) if the docstring is not detailed enough",
        default=None,
    )
    parameters: typing.List[FunctionParameter] = Field(
        description="The parameter types and descriptions", default_factory=list
    )
    metadata: typing.Optional[dict] = Field(
        default_factory=dict,
        description="Any metadata associated with the function used in instantiation of a callable object such as security or factory providers",
    )

    @model_validator(mode="before")
    def _vals(cls, values):
        """ensure we have a description for the function for search"""
        values["extended_description"] = (
            values.get("extended_description") or values["description"]
        )
        return values

    def to_json_spec(
        cls, model_provider: LanguageModelProvider = LanguageModelProvider.openai, **kwargs
    ) -> dict:
        """dump in a json schema format ala openai
        https://cookbook.openai.com/examples/how_to_call_functions_with_chat_models
        """

        """parameters - a map of stff"""
        props = {p.name: p.to_json_spec(**kwargs) for p in cls.parameters}
        """body - we parse the name but this must marry up with what we use elsewhere"""
        name = re.sub(REGEX_ALLOW_FUNCTION_NAMES, "", cls.name)
        parameters_name = 'parameters'
        if model_provider == LanguageModelProvider.anthropic:
            #this is one difference of the function spec 
            parameters_name = 'input_schema'
        return {
            # "type": "function",
            # "function": {
            "name": name,
            "description": cls.description[:MAX_FUNCTION_DESCRIPTION_LENGTH],
            parameters_name: {"type": "object", "properties": props},
            # },
        }

    @classmethod
    def from_library_function(
        cls,
        function_name: str,
        instance_type: str = None,
        alias: str = None,
        searchable_description: str = None,
    ) -> "_RunTimeFunction":
        """for any function that can be valuated in your library, a fully qualified name is provided to eval it

        Args:
            function_name (str): the fully qualified name of the function in your library
            instance_type (str): if the function is an instance of a type, provide the constructor
        """

        instance = core_types.eval(function_name, instance_type)
        return cls.from_callable(
            instance, alias=alias, searchable_description=searchable_description
        )

    @classmethod
    def from_callable(
        cls,
        fn: typing.Callable,
        alias: str = None,
        searchable_description: str = None,
        augment_description: str = None,
    ) -> "_RunTimeFunction":
        """given a callable, return a Function wrapper
        Alias is used because the function name e.g. if its on an instance, will not tell the whole story

        Args:
            fn (typing.Callable): any callable python object
            alias (str): an alternative name to use to name the function
        """

        """
        get the parameters and their descriptions - the kernel of the function data
        """
        function_desc = FunctionMetadataParser.parse_metadata(
            fn, alias=alias, augment_description=augment_description
        )

        """get the function description"""
        return _RunTimeFunction(
            **function_desc.model_dump(),
            searchable_description=searchable_description,
            _function=fn,
        )

    @classmethod
    def from_openapi_endpoint(
        cls, api_endpoint: ApiEndpoint
    ) -> "_RunTimeFunction":
        """Given a named endpoint and the spec, provide a callable function description.
           (Maybe need some token provider beyond bearer)

        Args:
            api_endpoint: this is our structure api type
        """
        return _RunTimeFunction(_function=api_endpoint.invoke, 
                                name=api_endpoint.name, 
                                description=api_endpoint.description, 
                                parameters=api_endpoint.parameters)
    
    """convenience callable behaviors - not serialized"""
    _function: typing.Optional[typing.Callable] = PrivateAttr(default=None)

    def __call__(self, *args, **kwargs):
        function = getattr(self, "function", None)
        if function:
            try:
                return function(*args, **kwargs)
            except:
                import traceback
                print('failing to call function directly - there is one case where we might want to use the bound function but generally not')
                
                raise
                print(traceback.format_exc())
                # undecided about bound versus unbound functions
                return function.__func__(*args, **kwargs)
        raise Exception(
            "The function object is not callable because there is no underling function object on the instance"
        )


class _RunTimeFunction(Function):
    """
    this is used in place of the one we serialize so that we can hold the function and call it
    """

    function: typing.Optional[typing.Callable] = None

    @model_validator(mode="before")
    def _init_content(cls, values):
        """
        add the function from the private one
        """
        values["function"] = values.get("_function")
        return values

    @model_serializer()
    def dump(self):
        """functions are removed"""
        d = dict(vars(self))
        if "function" in d:
            d.pop("function")

        return d
