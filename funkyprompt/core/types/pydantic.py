import typing
import pydantic
import pyarrow as pa
from datetime import date, datetime
import sys
import inspect
import types

def get_pydantic_properties_string(cls):
    """
    this is useful as a prompting device
    """
    annotations = typing.get_type_hints(cls)
    class_str = f"class {cls.__name__}(BaseModel)\n"
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
    return class_str


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
