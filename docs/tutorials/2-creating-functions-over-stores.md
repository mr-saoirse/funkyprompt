---
description: How we discover stores and functions to query them
---

# 2 Creating functions over stores

The agent has an `available_functions_search` that it can use to lookup functions. It can also be supplied with a list of functions up front. We always want to use the supplied functions and only fall back to the search if needed. This means the functions also need to describe what they can do (and cannot do) so the interpreter will use them first if it is sensible to do so.\


In `funkyprompt` we can have different types of functions; `api` , `default` `stores` are thee types. `api` uses a proxy to make REST requests. `stores` are actually different types of stores like `vector-store` and `columnar-store` while the `default` will just load functions in python from a registry. In all cases we save the functions to a registry.

When creating a store like a vector store, when it is crated for the first time it will register the store in a registry. This registry is in fact just another vector-store that can be searched.&#x20;

```
from funkyprompt import FunkyRegistry
reg = FunkyRegistry()
reg.load() #this will list a Polars dataframe of functions
```

<figure><img src="../.gitbook/assets/image.png" alt=""><figcaption><p>sample functions</p></figcaption></figure>

The content of the function description is embedded for search. The \`metadata\` describes how to reconstruct the function. For example for these stores, a factory can be use to load the correct stores and expose its search function.

While stores are registered on creation, we can see how this is done by explicitly registering the function again

```
Model = InstructEmbeddingContentModel.create_model('BookChapters')
store = VectorDataStore(Model, description="A store of different book chapters")
store.register_store()
```

This allows us to search for stores/functions in different way. We could do a lookup on function names or we could do a vector search on possibly long-form textual descriptinos of what functions can do. This is design for a case when we have a very large number of functions/stores.

