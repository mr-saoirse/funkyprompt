import typing
import pydantic
import pyarrow as pa
from datetime import date, datetime
import sys
import inspect
import types

def get_innermost_args(type_hint):
    """
    Recursively extracts the innermost type arguments from nested Optionals, Lists, and Unions.
    """

    if typing.get_origin(type_hint) is typing.Union:
        for arg in typing.get_args(type_hint):
            if arg is not type(None):  
                return get_innermost_args(arg)

    if typing.get_origin(type_hint) is list or type_hint == typing.List:
        list_args = typing.get_args(type_hint)
        if list_args:
            return get_innermost_args(list_args[0])

    return type_hint

def match_type(inner_type, base_type) -> bool:
    """
    Recursively check if any of the inner types match the base type.

    """
    arg = get_innermost_args(inner_type)
    if issubclass(arg, base_type):
        return arg

def get_model_reference_types(obj, model_root, visits=None):
    """given a model root (presume AbstractModel) find all types that references other types"""
    annotations = typing.get_type_hints(obj) 
    
    """bootstrapped from the root we know about"""
    if visits is None:
        visits = []
    else:
        visits.append(obj)
    for _, field_type in annotations.items():
        
        otype = match_type(field_type, model_root)
        if otype and otype not in visits:
            get_model_reference_types(otype, model_root, visits)
    return visits

def make_type_table(obj):
    """generates the markdown table for the the type info from obj type annotations"""
    def make_header(name, max_lengths):
        return f"""### {name}
        
| {'Field Name'.ljust(max_lengths[0],' ')} | {'Type'.ljust(max_lengths[1],' ')}| {'Description'.ljust(max_lengths[2],' ')} |
| {'-'.ljust(max_lengths[0], '-')}|{'-'.ljust(max_lengths[1],'-')}|{'-'.ljust(max_lengths[2],'-')}|
"""
        
    annotations = typing.get_type_hints(obj)
    elements = []
    max_lengths = [0,0,0]
    for field_name, field_type in annotations.items():
        field_default = getattr(obj, field_name, ...)
        field_info = obj.__fields__.get(field_name)
        description =  field_info.description  if getattr(field_info, "description", None) else ""
   
        type_str = repr(field_type)
        """not sure if defaults are useful in hints yet"""
        default = None
        if field_default is ...:
            pass
        else:
            if isinstance(field_default, pydantic.Field):
                default = repr(field_default.default) 
            else:
                default = repr(field_default)
        if max_lengths[0] < len(field_name):
            max_lengths[0] = len(field_name)
        if max_lengths[1] < len(type_str):
            max_lengths[1] = len(type_str)
        if max_lengths[2] < len(description):
            max_lengths[2] = len(description)
            
        elements.append([field_name, type_str.replace('typing.',''), description])        
        
    table = make_header(obj.get_model_name(), max_lengths)
    for el in elements:
        table += f"""| {el[0].ljust(max_lengths[0],' ')}| {el[1].ljust(max_lengths[1], ' ')}| {(el[2] or '').ljust(max_lengths[2], ' ')}|""" + '\n'
    
    return table + '\n'


def get_markdown_description(cls: "AbstractModel", functions: typing.List[dict]=None):
    """
    this is useful as a prompting device - from an abstract model, generate the agent prompt info
    the prompt (names and description) is combined with nested respond types and the available api functions are registered with the type
    """
    from funkyprompt.core import AbstractModel
    
    """add any external functions i.e. api calls that the function manager can load"""
    
    formatted_functions = [f""" - [{d.get('name')}]({d.get('url')}) {d.get('description')}""" for d in functions or []]
    child_types =  []
    get_model_reference_types(cls,AbstractModel,visits=child_types)
      
    return f"""# {cls.get_model_name()}
{cls.get_model_description()}

## Structured Response Types

{"".join(make_type_table(c) for c in child_types[::-1] if c is not cls)}

{make_type_table(cls)}

## Available Functions

{formatted_functions}
"""
    
    
def get_pydantic_properties_string(cls, child_types=None):
    """
    this is useful as a prompting device
    """
    annotations = typing.get_type_hints(cls)
    
    """if known child types are provided, we render them first"""
    child_strings = f"\n\n".join(get_pydantic_properties_string(t) for t in child_types or [])
    
    class_str = f"\n\nclass {cls.__name__}(BaseModel)\n"
    for field_name, field_type in annotations.items():
        field_default = getattr(cls, field_name, ...)
        field_info = cls.__fields__.get(field_name)
        description = (
            f" # {field_info.description}"
            if getattr(field_info, "description", None)
            else ""
        )
        type_str = repr(field_type)

        if field_default is ...:
            class_str += f"  -  {field_name}: {type_str}{description}\n"
        else:
            if isinstance(field_default, pydantic.Field):

                class_str += f" - {field_name}: {type_str} = Field(default={repr(field_default.default)}) {description}\n"
            else:
                class_str += f" - {field_name}: {type_str} = {repr(field_default)} {description}\n"
    return child_strings + class_str


def get_extras(field_info, key: str):
    """
    Get the extra metadata from a Pydantic FieldInfo.
    """
    return (field_info.json_schema_extra or {}).get(key)


def _py_type_to_arrow_type(py_type, field, coerce_str=True):
    """Convert a field with native Python type to Arrow data type.

    Raises
    ------
    TypeError
        If the type is not supported.
    """
    if py_type == int:
        return pa.int64()
    elif py_type == float:
        return pa.float64()
    elif py_type == str:
        return pa.utf8()
    elif py_type == bool:
        return pa.bool_()
    elif py_type == bytes:
        return pa.binary()
    elif py_type == date:
        return pa.date32()
    elif py_type == datetime:
        tz = get_extras(field, "tz")
        return pa.timestamp("us", tz=tz)
    elif getattr(py_type, "__origin__", None) in (list, tuple):
        child = py_type.__args__[0]
        return pa.list_(_py_type_to_arrow_type(child, field))

    if coerce_str:
        return pa.utf8()

    raise TypeError(
        f"Converting Pydantic type to Arrow Type: unsupported type {py_type}."
    )


def is_nullable(field) -> bool:
    """Check if a Pydantic FieldInfo is nullable."""
    if isinstance(field.annotation, typing._GenericAlias):
        origin = field.annotation.__origin__
        args = field.annotation.__args__
        if origin == typing.Union:
            if len(args) == 2 and args[1] == type(None):
                return True
    elif sys.version_info >= (3, 10) and isinstance(field.annotation, types.UnionType):
        args = field.annotation.__args__
        for typ in args:
            if typ == type(None):
                return True
    return False


def _pydantic_model_to_fields(model: pydantic.BaseModel) -> typing.List[pa.Field]:
    return [_pydantic_to_field(name, field) for name, field in model.__fields__.items()]


def _pydantic_to_arrow_type(field) -> pa.DataType:
    """Convert a Pydantic FieldInfo to Arrow DataType"""

    if isinstance(field.annotation, typing._GenericAlias) or (
        sys.version_info > (3, 9) and isinstance(field.annotation, types.GenericAlias)
    ):
        origin = field.annotation.__origin__
        args = field.annotation.__args__
        if origin == list:
            child = args[0]
            return pa.list_(_py_type_to_arrow_type(child, field))
        elif origin == typing.Union:
            if len(args) == 2 and args[1] == type(None):
                return _py_type_to_arrow_type(args[0], field)
    elif sys.version_info >= (3, 10) and isinstance(field.annotation, types.UnionType):
        args = field.annotation.__args__
        if len(args) == 2:
            for typ in args:
                if typ == type(None):
                    continue
                return _py_type_to_arrow_type(typ, field)
    elif inspect.isclass(field.annotation):
        if issubclass(field.annotation, pydantic.BaseModel):
            # Struct
            fields = _pydantic_model_to_fields(field.annotation)
            return pa.struct(fields)
    #         elif issubclass(field.annotation, FixedSizeListMixin):
    #             return pa.list_(field.annotation.value_arrow_type(), field.annotation.dim())
    return _py_type_to_arrow_type(field.annotation, field)


def _pydantic_to_field(name: str, field) -> pa.Field:
    """Convert a Pydantic field to a PyArrow Field."""
    dt = _pydantic_to_arrow_type(field)
    return pa.field(name, dt, is_nullable(field))


def pydantic_to_arrow_schema(
    model: pydantic.BaseModel, metadata: dict = None
) -> typing.List[pa.Field]:
    """
    convert a pydantic schema to arrow schema in some sort of opinionated way e.g. dealing with complex types
    """
    fields = [
        _pydantic_to_field(name, field) for name, field in model.model_fields.items()
    ]

    schema = pa.schema(fields)

    if metadata:
        schema = schema.with_metadata(metadata)

    return schema
