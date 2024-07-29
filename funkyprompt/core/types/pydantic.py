import typing
import pydantic


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
