# for speed reasons only we store them in the module as singleton - you may need to install deps that are not bundled with funkyprompt

# EMBEDDINGS = {}


# def get_embedding_provider(provider):
#     if provider in EMBEDDINGS:
#         return EMBEDDINGS[provider]
#     else:
#         if provider == "instruct":
#             from InstructorEmbedding import INSTRUCTOR

#             model = INSTRUCTOR("hkunlp/instructor-large")
#             EMBEDDINGS[provider] = model
#             return model

import funkyprompt
from funkyprompt.model.entity import FunctionRegistryRecord
from .AbstractStore import AbstractStore
from .ColumnarDataStore import ColumnarDataStore
from .VectorDataStore import VectorDataStore
from .EntityDataStore import EntityDataStore
import typing

from funkyprompt.model.func import FunctionDescription


class FunkyRegistry(VectorDataStore):
    """
    Sublcass the base to create a new configuration
    This registry is used to register functions
    - vector stores as fucntions
    - columnar stores as functions
    - library functions
    - API calls

    """

    STORE_DIR = "function-registry"
    DESCRIPTION = "Used to search for different types of stores for vector search, tabular structured date search etc."

    def __init__(cls):
        Model = FunctionRegistryRecord.create_model(cls.STORE_DIR, namespace="default")
        super().__init__(model=Model, description=cls.DESCRIPTION, register_store=False)

    def _remove_stores_by_name(cls, stores):
        """
        convenience - need to be careful here - its not a proper predicate as it does not consider namespaces
        """
        st = f",".join([f"'{s}'" for s in stores])
        cls._table.delete(f"entity_name in ({st})")

    def register_function(
        cls, function: typing.Union[typing.Callable, FunctionDescription]
    ):
        """
        upsert the description and components that we use to discover this function
        """

        # allow passing the function description
        fd = (
            funkyprompt.describe_function(function)
            if not isinstance(function, FunctionDescription)
            else function
        )
        namespace = fd.factory.module
        fq_name = f"functions_{namespace}_{fd.name}".replace(".", "_")

        cls.add(
            FunctionRegistryRecord(
                name=fq_name,
                description=fd.description,
                type="default",
                entity_name="function_subject_todo",
                namespace=namespace,
                # serialized the function description
                metadata=fd.model_dump_json(),
            )
        )
        funkyprompt.logger.info(f"Registered {fd.name}")


from funkyprompt import VECTOR_STORE_ROOT_URI, COLUMNAR_STORE_ROOT_URI
from glob import glob
