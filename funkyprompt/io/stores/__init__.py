# for speed reasons only we store them in the module as singleton - you may need to install deps that are not bundled with funkyprompt

EMBEDDINGS = {}


def get_embedding_provider(provider):
    if provider in EMBEDDINGS:
        return EMBEDDINGS[provider]
    else:
        if provider == "instruct":
            from InstructorEmbedding import INSTRUCTOR

            model = INSTRUCTOR("hkunlp/instructor-large")
            EMBEDDINGS[provider] = model
            return model


from funkyprompt.ops.entities import (
    AbstractEntity,
    AbstractVectorStoreEntry,
    InstructAbstractVectorStoreEntry,
)
from .AbstractStore import AbstractStore
from .ColumnarDataStore import ColumnarDataStore
from .VectorDataStore import VectorDataStore
from funkyprompt import VECTOR_STORE_ROOT_URI, COLUMNAR_STORE_ROOT_URI
from glob import glob


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


def list_stores():
    return [
        dict(
            zip(
                ["type", "namespace", "name"],
                [i.split(".")[0] for i in c.split("/")[-3:]],
            )
        )
        for c in list(glob(f"{VECTOR_STORE_ROOT_URI}/*/*"))
        + list(glob(f"{COLUMNAR_STORE_ROOT_URI}/*/*"))
    ]


def open_store(name: str, type: str, namespace: str = "default"):
    """
    Convenience to load store by name. the interface is still being worked out
    """
    store = VectorDataStore if type == "vector-store" else ColumnarDataStore
    model = AbstractVectorStoreEntry if type == "vector-store" else AbstractEntity
    # hack
    if "-instruct" in name:
        model = InstructAbstractVectorStoreEntry
    Model = model.create_model(name, namespace=namespace)
    store = store(Model)
    return store


def get_probe():
    """
    convenience method to check if there is any response from stores for a given question
    """
    import itertools
    import pandas as pd

    loaded_stores = [open_store(**s) for s in list_stores()]

    def f(text):
        def try_res(s, q):
            try:
                return s(q, limit=1)
            except Exception as ex:
                return {}

        return pd.DataFrame(
            list(itertools.chain(*[try_res(s, text) for s in loaded_stores]))
        ).sort_values("_distance")

    return f
