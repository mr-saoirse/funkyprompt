from funkyprompt.ops.entities import AbstractEntity, AbstractVectorStoreEntry
from .AbstractStore import AbstractStore
from .ColumnarDataStore import ColumnarDataStore
from .VectorDataStore import VectorDataStore


def insert(entity: AbstractEntity):
    if isinstance(entity, AbstractVectorStoreEntry):
        store = VectorDataStore(entity)
        store.add(entity)
    if isinstance(entity, AbstractEntity):
        store = ColumnarDataStore(entity)
        store.add(entity)
    else:
        raise TypeError(
            f"The entity {entity} must be a subclass of AbstractEntity or implement some interface TBD"
        )
