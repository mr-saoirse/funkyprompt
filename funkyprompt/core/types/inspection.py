from inspect import getmembers, isfunction, isclass, ismethod, ismodule
import types
import typing
from pydantic import BaseModel, Field
from enum import Enum
import importlib, pkgutil


class TypeInfo(BaseModel):
    name: str = Field(description="parameter name")
    type: typing.Type = Field(
        description="the python type resolve from precedence of required"
    )
    args: tuple | typing.Type = Field(description="All type options in union types")
    input: typing.Any = Field(
        description="The full annotation input that we are mapping"
    )
    is_required: bool = Field(description="required or not")
    is_list: bool = Field(description="is a collection/list type or not")
    enum_options: typing.Optional[typing.List[str]] = Field(
        description="enums can provide option hints", default_factory=list
    )

    def to_json_schema(cls) -> dict:
        return {}


def get_defining_class(member,cls):
    defining_class = getattr(member, '__objclass__', None)
    if defining_class:
        return defining_class

    for base_class in cls.mro():
        if member.__name__ in base_class.__dict__:
            return base_class
    return None
    
def is_strict_subclass(subclass, superclass):
    try:
        if not subclass:
            return False
        return issubclass(subclass, superclass) and subclass is not superclass
    except:
        raise ValueError(f"failed to check {subclass}, {superclass} as a strict subclass relationship")

def get_class_and_instance_methods(cls, inheriting_from: type=None):
    """inspect the methods on the type for methods
    
    by default only the classes methods are used or we can take anything inheriting from a base such as AbstractModel (not in)
    
    Args:
        inheriting_from: create the excluded base from which to inherit. 
        In our case we want to treat the AbstractModel as a base that does not share properties
    """
    methods = []
    class_methods = []

    def __inherits(member):
        """
        find out of a member inherits from something we care about, not including the thing itself
        """
        if not inheriting_from:
            return True
        
        """we can traverse up to a point"""
        return  is_strict_subclass(get_defining_class(member,cls), inheriting_from)
    
    for name, member in getmembers(cls):
        if isfunction(member) or ismethod(member):
            # Check if the method belongs to the class and not inherited
            if member.__qualname__.startswith(cls.__name__) or __inherits(member):
                if isinstance(member, types.FunctionType):
                    methods.append(getattr(cls, name))
                elif isinstance(member, types.MethodType):
                    class_methods.append(getattr(cls, name))

    return methods + class_methods


def resolve_signature_types(fn: typing.Callable, **kwargs):
    """given a function, resolve all signature annotations in out opinionated way"""
    return [resolve_named_type(k, v) for k, v in typing.get_type_hints(fn).items()]


def resolve_named_type(name: str, t: type, **kwargs):
    """a simple opinionated type mapping - we may pass some precedence for different modes
    the tuple that comes from `typing.get_type_hints` is passed in
    """

    def apply_precedence(t):
        """a primitive reduction - just reduce the inner most left type for now
        Example
            #this is a non required list of type string
            typing.Optional[typing.List[str | dict]]

        ultimately json stuff is sent over the wire so for now we want our functions
        to be well behaved and parse the inputs via coercian
        """
        if isinstance(t, tuple):
            t = t[0]
        args = typing.get_args(t)
        if len(args) > 0:
            t = args[0]
            return apply_precedence(t)
        return t

    args = typing.get_args(t)
    required = types.NoneType not in typing.get_args(t)
    contains_list = False
    for item in args:
        if typing.get_origin(item) in {list, typing.List}:
            contains_list = True

    """generate the summary object"""
    args = args or t
    T = apply_precedence(args)

    """handle enum types and options"""
    enum_options = []
    if isclass(T) and issubclass(T, Enum):
        enum_options = [member.value for member in T]
        if len(enum_options):
            T = type(enum_options[0])

    return TypeInfo(
        name=name,
        type=T,
        args=args,
        is_required=required,
        is_list=contains_list,
        input=t,
        enum_options=enum_options,
    )


def get_classes(
    base_filter: type = None,
    package="funkyprompt.core",
    exclusions: typing.List[str] = None,
) -> list[type]:
    """recurse and get classes implementing a base class
    we do some env stuff to make inspection work well and we should test for this e.g. dont load models and do not init singletons
    """

    exclusions = exclusions or []
    classes_in_package = []
    # Go through the modules in the package
    for _importer, module_name, is_package in pkgutil.iter_modules(
        importlib.import_module(package).__path__
    ):
        full_module_name = f"{package}.{module_name}"
        if full_module_name in exclusions:
            continue
        # Recurse through any sub-packages
        if is_package:
            classes_in_subpackage = get_classes(
                package=full_module_name, base_filter=base_filter
            )
            classes_in_package.extend(classes_in_subpackage)

        # Load the module for inspection
        module = importlib.import_module(full_module_name)

        # Iterate through all the objects in the module and
        # using the lambda, filter for class objects and only objects that exist within the module
        for _name, obj in getmembers(
            module,
            lambda member, module_name=full_module_name: isclass(member)
            and member.__module__ == module_name,
        ):
            classes_in_package.append(obj)
    return (
        classes_in_package
        if not base_filter
        else [c for c in classes_in_package if issubclass(c, base_filter)]
    )
