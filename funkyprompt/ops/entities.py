"""
notes we have use by_alias false in pydantic schema resolution which may not be as expected
"""

from typing import List, Optional
from pydantic import Field, BaseModel, create_model, model_validator
import math
import json
import numpy as np
import typing
import funkyprompt
import pyarrow as pa
import datetime
import re
import datetime

# When we are mature we would store configuration like this somewhere more central
INSTRUCT_EMBEDDING_VECTOR_LENGTH = 768
OPEN_AI_EMBEDDING_VECTOR_LENGTH = 1536


def load_type(namespace, entity_name):
    """
    load an entity from a module under the entities folder which ink funkyprompt is fixed to the examples mod
    provide the qualified namespace under entities and the entity name
    """

    module = namespace
    MODULE_ROOT = "funkyprompt.ops.examples"
    module = module.replace(MODULE_ROOT, "")
    module = f"{MODULE_ROOT}{module}"

    return getattr(__import__(module, fromlist=[entity_name]), entity_name)


def map_pyarrow_type_info(field_type, name=None):
    """
    Load not only the type but extra type metadata from pyarrow that we use in Pydantic type
    """
    t = map_pyarrow_type(field_type, name=name)
    d = {"type": t}
    if pa.types.is_fixed_size_list(field_type):
        d["fixed_size_length"] = field_type.list_size
    return d


def map_pyarrow_type(field_type, name=None):
    """
    basic mapping between pyarrow types and typing info for some basic types we use in stores
    """

    if pa.types.is_fixed_size_list(field_type):
        return typing.List[map_pyarrow_type(field_type.value_type)]
    if pa.types.is_map(field_type):
        return dict
    if pa.types.is_list(field_type):
        return list
    else:
        if field_type in [pa.string(), pa.utf8(), pa.large_string()]:
            return str
        if field_type == pa.string():
            return str
        if field_type in [pa.int16(), pa.int32(), pa.int8(), pa.int64()]:
            return int
        if field_type in [pa.float16(), pa.float32(), pa.float64()]:
            return float
        if field_type in [pa.date32(), pa.date64()]:
            return datetime.datetime
        if field_type in [pa.bool_()]:
            return bool
        if field_type in [pa.binary()]:
            return bytes
        if pa.types.is_timestamp(field_type):
            return datetime.datetime
        raise NotImplementedError(f"We dont handle {field_type} ({name})")


def map_field_types_from_pa_schema(schema):
    """
    given a pyarrow schema return type info so we can create the Pydantic Model from the pyarrow table
    """

    return {f.name: map_pyarrow_type_info(f.type, f.name) for f in schema}


class NpEncoder(json.JSONEncoder):
    """
    A Json encoder that is a little bit more understanding of  numpy types
    """

    def default(self, obj):
        dtypes = (np.datetime64, np.complexfloating)
        if isinstance(obj, dtypes):
            return str(obj)
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            if any([np.issubdtype(obj.dtype, i) for i in dtypes]):
                return obj.astype(str).tolist()
            return obj.tolist()
        return super(NpEncoder, self).default(obj)


class AbstractEntity(BaseModel):
    """
    The funkyprompt base type with some store helper attributes
    """

    @classmethod
    @property
    def namespace(cls):
        """
        Takes the namespace from config or module - returns default if nothing else e.g. dynamic modules
        """
        if hasattr(cls, "Config"):
            if hasattr(cls.Config, "namespace"):
                return cls.Config.namespace

        # TODO: simple convention for now - we can introduce other stuff including config
        namespace = cls.__module__.split(".")[-1]
        # for now we use the default namespace for anything in entities
        return namespace if namespace != "entities" else "default"

    @classmethod
    @property
    def entity_name(cls):
        # TODO: we will want to fully qualify these names
        s = cls.model_json_schema(by_alias=False)
        return s["title"]

    @classmethod
    @property
    def full_entity_name(cls, sep="_"):
        return f"{cls.namespace}{sep}{cls.entity_name}"

    @classmethod
    @property
    def key_field(cls):
        s = cls.model_json_schema(by_alias=False)
        key_props = [k for k, v in s["properties"].items() if v.get("is_key")]
        # TODO: assume one key for now
        if len(key_props):
            return key_props[0]

    @classmethod
    @property
    def fields(cls):
        s = cls.model_json_schema()
        key_props = [k for k, v in s["properties"].items()]
        return key_props

    @classmethod
    @property
    def about_text(cls):
        if hasattr(cls, "config"):
            c = cls.config
            return getattr(c, "about", "")

    @classmethod
    @property
    def embeddings_provider(cls):
        if hasattr(cls, "Config"):
            if hasattr(cls.Config, "embeddings_provider"):
                return cls.Config.embeddings_provider

    def large_text_dict(cls):
        return cls.model_dump()

    def __str__(cls):
        """
        For the purposes of testing some logging with types
        the idea of using markdown and fenced objects is explored
        """

        d = cls.model_dump()
        d["__type__"] = cls.entity_name
        d["__key__"] = cls.key_field
        d["__namespace__"] = cls.namespace
        d = json.dumps(d, cls=NpEncoder, default=str)
        return f"""```json{d}```"""

    @classmethod
    def create_model_from_data(cls, name, data, namespace=None, **kwargs):
        pass

    @classmethod
    def create_model_from_pyarrow(
        cls, name, py_arrow_schema, namespace=None, key_field=None, **kwargs
    ):
        def _Field(name, fi):
            d = dict(fi)
            t = d.pop("type")
            # field = Field (t, None, is_key=True) if name == key_field else Field
            return (t, None)

        namespace = namespace or cls.namespace
        fields = map_field_types_from_pa_schema(py_arrow_schema)
        fields = {k: _Field(k, v) for k, v in fields.items()}
        return create_model(name, **fields, __module__=namespace, __base__=cls)

    @classmethod
    def create_model(cls, name, namespace=None, **fields):
        """
        For dynamic creation of models for the type systems
        create something that inherits from the class and add any extra fields

        when we create models we should audit them somewhere in the system because we can later come back and make them
        """
        namespace = namespace or cls.namespace
        return create_model(name, **fields, __module__=namespace, __base__=cls)

    @staticmethod
    def get_type(namespace, entity_name):
        """
        accessor for type loading by convention
        """
        return load_type(namespace=namespace, entity_name=entity_name)

    @staticmethod
    def get_type_from_the_ossified(json_type):
        """
        accessor for type loading by convention
        """
        namespace = json_type["__namespace__"]
        entity_name = json_type["__type__"]

        return load_type(namespace=namespace, entity_name=entity_name)

    @staticmethod
    def hydrate_type(json_type):
        """
        determine type and reload the json string by conventional embed of type info
        """
        ptype = AbstractEntity.get_type_from_the_ossified(json_type)
        return ptype(**json_type)

    @classmethod
    def pyarrow_schema(cls):
        """
        Convert a Pydantic model into a PyArrow schema in a very simplistic sort of way

        Args:
            model_class: A Pydantic model class.

        Returns:
            pyarrow.Schema: The corresponding PyArrow schema.
        """
        import pyarrow as pa

        def iter_field_annotations(obj):
            for key, info in obj.__fields__.items():
                yield key, info.annotation

        """
        We want to basically map to any types we care about
        there is a special consideration for vectors
        we take the pydantic field attributes in this case fixed_size_length to determine this
        Each pydantic type is designed for a particular embedding so for example we want an 
        OPEN_AI or Instruct embedding fixed vector length
        """

        def mapping(k, fixed_size_length=None):
            mapping = {
                int: pa.int64(),
                float: pa.float64(),
                str: pa.string(),
                bool: pa.bool_(),
                bytes: pa.binary(),
                list: pa.list_(pa.null()),
                dict: pa.map_(pa.string(), pa.null()),
                # TODO: this is temporary: there is a difference between these embedding vectors and other stuff
                typing.List[int]: pa.list_(
                    pa.int64(), list_size=fixed_size_length or -1
                ),
                typing.List[float]: pa.list_(
                    pa.float32(), list_size=fixed_size_length or -1
                ),
                None: pa.null(),
            }

            return mapping[k]

        fields = []

        props = cls.model_json_schema(by_alias=False)["properties"]
        for field_name, field_info in iter_field_annotations(cls):
            print(field_name, field_info)
            if hasattr(field_info, "__annotations__"):
                # TODO need to test this more
                field_type = AbstractEntity.pyarrow_schema(field_info)
            else:
                if getattr(field_info, "__origin__", None) is not None:
                    field_info = field_info.__args__[0]
                """
                take the fixed size from the pydantic type attribute if it exists turning the 
                list into a vector
                """
                field_type = mapping(
                    field_info, props[field_name].get("fixed_size_length")
                )

            field = pa.field(field_name, field_type)
            fields.append(field)

        return pa.schema(fields)


class AbstractVectorStoreEntry(AbstractEntity):
    """
    The Base of Vector Store types that manages vector embedding lengths

    We can store vectors and other attributes
    At a minimum the and text are needed as we can generate other ids from those
    Name must be unique if the id is omitted of course - but its the primary key so it makes sense
    """

    name: str = Field(is_key=True)
    text: str = Field(long_text=True)
    doc_id: Optional[str]
    vector: Optional[List[float]] = Field(
        fixed_size_length=OPEN_AI_EMBEDDING_VECTOR_LENGTH,
        default_factory=list,
    )  # lambda: [0.0 for i in range(OPEN_AI_EMBEDDING_VECTOR_LENGTH)]
    id: Optional[str]
    depth: Optional[int] = 0
    # node types eg. summaries at depth -1
    text_node_type: Optional[str] = "FULL"

    @model_validator(mode="before")
    def default_ids(cls, values):
        if not values.get("id"):
            values["id"] = values["name"]
        if not values.get("doc_id"):
            values["doc_id"] = values["name"]
        return values

    def split_text(cls, max_length=int(1 * 1e4), **options):
        """
        simple text splitter - working on document model
        """

        def part(s, i):
            return s[i * max_length : (i * max_length) + max_length]

        # we keep the model N times with partial items
        # we assume for now that we have univariate vector schema which in general will not be the case
        return [
            cls.model_copy(update={"text": part})
            for part in [
                part(cls.text, i) for i in range(math.ceil(len(cls.text) / max_length))
            ]
        ]

    @classmethod
    def as_store(cls):
        """
        because stores are determined by types alone, we can construct stores this way
        """
        from funkyprompt.io.stores import VectorDataStore

        return VectorDataStore(cls)


class InstructAbstractVectorStoreEntry(AbstractVectorStoreEntry):
    class Config:
        embeddings_provider = "instruct"

    vector: Optional[List[float]] = Field(
        fixed_size_length=INSTRUCT_EMBEDDING_VECTOR_LENGTH,
        default_factory=list,
    )


class SchemaOrgVectorEntity(AbstractVectorStoreEntry):
    """
    A helper for mapping schema.org data usually scrapped in Json+LD
    we want tp put this in various pydantic types to use the Rag Store
    """

    class Config:
        # these are excluded from the output we send to data stores for now
        EXCLUDE_ATTRIBUTES = ["comment", "sameAs"]
        # these are mapped from objects that are complex with @id to just have the string value (s)
        PULL_IDs = ["image", "video", "publisher", "aggregate_rating"]
        FLATTEN_COMPLEX_NAMED_TEXT_TYPES = ["HowToStep"]

    @model_validator(mode="before")
    def pull_ids(cls, values):
        for key in values.keys():
            if key in SchemaOrgVectorEntity.Config.PULL_IDs:
                if not isinstance(values, dict):
                    raise NotImplementedError("multiples todo for mapping @id stuff")
                values[key] = values.get("name", values.get("@id"))
        return values

    @model_validator(mode="before")
    def _coerce_str(cls, values):
        # this is just for testing
        for key in values.keys():
            values[key] = str(values[key])
        return values

    @staticmethod
    def should_exclude(k, override_exclude=None):
        return k in (
            override_exclude or SchemaOrgVectorEntity.Config.EXCLUDE_ATTRIBUTES
        )

    @classmethod
    def create_model_from_schema(
        cls,
        name,
        schema,
        namespace=None,
        exclude_fields_snake_case=None,
        text_fields=None,
    ):
        # from stringcase import snakecase
        def snakecase(s):
            # Replace spaces and underscores with a single underscore
            s = re.sub(r"[-_ ]+", "_", s)
            # Remove non-alphanumeric characters except underscores
            s = re.sub(r"[^a-zA-Z0-9_]", "", s)
            return s.lower()

        """
        
        schema org attributes but snake case and cleaned
        for now we will not type until we have a use case for columnar data      
        schema can be a type or an instance in the json format of python typed objects
        if its a type from schema org it will be better for generating but for simple use cases it does not matter  
        TODO: we will combine text fields into one that we use for the VStore - at the moment its assumed that there is at least a text field which is typical enough for schema.org
        """

        field_norm = lambda s: snakecase(s.lstrip("@"))

        fields = {
            field_norm(field_name): (
                # ToDo manage types properly
                str,
                Field(alias=field_name),
            )
            for field_name, type_info in schema.items()
        }

        # field names that we want to generate
        # if this were written out we could use underscores but this is a hidden dynamic type so we dont generate these excluded fields at all
        fields = {
            k: v
            for k, v in fields.items()
            if not SchemaOrgVectorEntity.should_exclude(k, exclude_fields_snake_case)
        }

        if "text" not in fields:
            fields["text"] = (str, "")

        if text_fields:
            pass  # add the validator
            # we need to add a validator to merge these fields into a text field

        #
        namespace = namespace or cls.namespace
        return create_model(name, **fields, __module__=namespace, __base__=cls)


class FPActorDetails(AbstractVectorStoreEntry):
    """
    stores context about the user or users.
    We can use this as one of our built-ins to understand specific people (us and the people we care about)

    Would be interesting to run "enrich" on this to add more data
    """

    # enum
    role: str = "Human"
    username: Optional[str] = None
    event_date: Optional[str] = None
    category: typing.Optional[str] = "General"

    @model_validator(mode="before")
    def validate_attributes(cls, values):
        if not values.get("username"):
            values["username"] = funkyprompt.getuser()
        if not values.get("event_date"):
            values["event_date"] = funkyprompt.utc_now_str()

        return values


#explore what the LanceDub type does for me
#the idea of a global registry of embeddings that we can load in the type?        
class AbstractContent(AbstractEntity):
    """
    the schema of a type that we ingest
    the schema defines a store but the store will also have a name and namespace
    normally we subclass this and create a named type / possibly dynamically
    
    It might be useful to have a config only on the type - we need to have a vector store descriptor 
    - search-mode 
    - specificity
    - scope
    - contemporaneousness 
    """
    #the key unless override with is-key
    name: str
    #the uri or text to embed
    content: str
    #the default embedded vector
    vector: Optional[List[float]] = Field(
        embedding_provider='open-ai'
        fixed_size_length=OPEN_AI_EMBEDDING_VECTOR_LENGTH,
        default_factory=list,
    )
    category: str = None
    depth int: = 0
    timestamp: str
    #user
    
    
    
    
    
    
    
    