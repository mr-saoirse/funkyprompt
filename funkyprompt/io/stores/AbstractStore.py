from funkyprompt.ops.entities import AbstractEntity
from funkyprompt.io.tools.fs import typed_record_reader


class AbstractStore:
    def __init__(
        cls, entity: AbstractEntity, alias: str = None, extra_context: str = None
    ):
        # TODO: bit weird - want to figure out of we want to use instances or not
        cls._entity = entity
        cls._alias = alias
        cls._entity_name = cls._entity.entity_name
        cls._entity_namespace = cls._entity.namespace
        cls._key_field = cls._entity.key_field
        cls._fields = cls._entity.fields
        cls._about_entity = cls._entity.about_text
        ###############
        cls._extra_context = extra_context

    @property
    def name(cls):
        return cls._alias or cls._entity_name

    @classmethod
    def ingest_records(cls, uri, entity_type: AbstractEntity, **kwargs):
        """
        Ingest a dataframe format of records that are in the correct schema
        this works if a base class is constructed from the entity
        """
        records = list(typed_record_reader(uri, entity_type=entity_type))
        store: AbstractStore = cls(entity_type)
        store.add(records, **kwargs)
        return store
