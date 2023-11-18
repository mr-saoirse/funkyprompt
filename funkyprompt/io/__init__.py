from funkyprompt import str_hash
from funkyprompt.io.stores import VectorDataStore, ColumnarDataStore

# def add_context(text, **kwargs):
#     """
#     this method can be used just to add arbitrary context that we want the agent to use
#     """
#     from funkyprompt.ops.entities import FPActorDetails
#     from funkyprompt.io.stores import VectorDataStore

#     data = kwargs
#     data["name"] = f"Entry {str_hash()}"
#     data["text"] = text
#     record = FPActorDetails(**data)
#     store = VectorDataStore(FPActorDetails)
#     store.add(record)
#     return store
