from funkyprompt.io.tools.fs import typed_record_reader
from funkyprompt.model.entity import AbstractModel, FunctionRegistryRecord, typing
from funkyprompt.model.func import (
    FunctionFactory,
    FunctionDescription,
    describe_function,
)
import json
import funkyprompt


class AbstractStore:
    # sub classes should set this
    STORE_DIR = "abstract-store"

    def __init__(cls, model: AbstractModel, alias: str = None, description: str = None):
        # TODO: bit weird - want to figure out of we want to use instances or not
        cls._model = model
        cls._alias = alias
        cls._about_entity = cls._model.__about__
        cls._description = description
        cls._key_field = cls._model.__key_field__

    @property
    def name(cls):
        return cls._alias or cls._model.__entity_name__

    def register_store(cls):
        """
        upsert the description and components that we use to discover this store
        """
        from funkyprompt.io.stores import FunkyRegistry

        full_name = f"{cls.STORE_DIR}/{cls._model.__fullname__}"
        funkyprompt.logger.debug(f"Registering {full_name=}, {cls._description}")
        return FunkyRegistry().add(
            FunctionRegistryRecord(
                name=full_name,
                description=cls._description,
                type=cls.STORE_DIR,
                entity_name=cls._model.__entity_name__,
                namespace=cls._model.__entity_namespace__,
                # serialized the function description
                metadata=cls.as_function_description(
                    context=cls._description
                ).model_dump_json(),
            )
        )

    @classmethod
    def run_search_many(
        cls,
        questions: typing.List[str],
        stores: typing.List[typing.Any],  # SElf in 3.11 leave it for now
        num_cores=1,
    ):
        """ """
        from itertools import chain

        # TODO - parallel implementation - we may use Ray depending on where we go with this
        # ray will be an optional dep
        return list(
            chain.from_iterable([store.run_search(questions) for store in stores])
        )

    @classmethod
    def ingest_records(cls, uri, entity_type: AbstractModel, **kwargs):
        """
        Ingest a dataframe format of records that are in the correct schema
        this works if a base class is constructed from the entity
        """
        records = list(typed_record_reader(uri, entity_type=entity_type))
        store: AbstractStore = cls(entity_type)
        store.add(records, **kwargs)
        return store

    @property
    def pyarrow_schema(cls):
        """
        the pyarrow schema from inspection
        experimenting with different formats for loading so this interface is a bit screwy
        """
        # this is a polars dataframe probably but still working on standardizing
        df = cls.load(limit=1, lazy=True).limit(1)
        if hasattr(df, "collect"):
            df = df.collect()
        return df.to_arrow().schema

    def get_data_model(cls):
        """
        If we create a store from a pydantic model in memory then we know the proper model
        But if we reload the store from disk we only have the pyarrow schema of the data to use to infer the mode
        """
        return AbstractModel.create_model_from_pyarrow(
            # names
            name=cls._model.__entity_name__,
            namespace=cls._model.__entity_namespace__,
            # sample the schema
            py_arrow_schema=cls.pyarrow_schema,
        )

    def as_function_description(
        cls,
        name: str = None,
        context: str = None,
        weight: float = 5,
        max_context_length=150,
    ):
        """
        Pass in the name and context
        """
        note = f"Provides context about the type [{cls._model.__entity_name__}] - ask your full question as per the function signature"
        # the description should be short (arbitrary for now)
        if context:
            note = f"{context[:max_context_length]}. {note}"

        model = cls._model.__bases__[-1]
        model_module = model.__module__
        model_name = model.__name__

        return describe_function(
            cls.run_search,
            alias=name,
            weight=weight,
            augment_description=note,
            # this is a bit lame but doing it for now. we need a proper factory mechanism
            factory=FunctionFactory(
                # for abstract stores this is the name but not in general
                name="run_search",
                partial_args={
                    "store_dir": cls.STORE_DIR,
                    "store_type": cls.__class__.__name__,
                    "model": f"{cls._model.__entity_namespace__}.{cls._model.__entity_name__}",
                    "entity_type": f"{model_module}.{model_name}"
                    # on vector stores we need to know the embedding for now - if the store we loaded with meta data e.g. from type resolution we would not
                    # "embedding": getattr(cls, "_embedding_provider", None),
                },
            ),
        )

    def as_agent(cls, allow_function_search=False):
        """
        convenience retrieve agent with self as function description to test stores
        """
        from funkyprompt import AgentBase

        return AgentBase(
            initial_functions=[cls.as_function_description()],
            allow_function_search=allow_function_search,
        )

    @classmethod
    def restore_from_data(cls, data, as_function_description=False, weight=5):
        """
        experimental work on using a round trip to serialized descriptions and restore them so we can vector search functions/stores

        **Args**
           data: a data row as per the FunctionRegistryRecord which contains an embedded function description with factory args to construct the model for search
                 it might be easier to restore the lance models or duck models but hey
           as_function_description: return the store or the function_description for search (default)
        """
        from funkyprompt.io.stores import VectorDataStore, ColumnarDataStore

        # the metadata is the function
        metadata = data["metadata"]
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        try:
            description = data["description"]
            factory = metadata["factory"]
            factory_pargs = factory["partial_args"]
            model_name = factory_pargs["model"]
            store_class = eval(factory_pargs["store_type"])
            model_class: AbstractModel = eval(factory_pargs["entity_type"])
            model_kwargs = dict(zip(["namespace", "name"], model_name.split(".")))
            Model = model_class.create_model(**model_kwargs)
            store = store_class(Model, description=description)
            if as_function_description:
                return store.as_function_description(
                    name=f"{factory_pargs['store_type']}_search_{model_name.replace('.','_')}".lower(),
                    weight=weight,
                    # one reason not to do this is excessively long function descriptions
                    # the question remains if there is a need to to vector search on longer texts then we provide to the LLM
                    context=description,
                )
            return store
        except:
            funkyprompt.logger.warning(f"Failed to parse {data}")
            raise
