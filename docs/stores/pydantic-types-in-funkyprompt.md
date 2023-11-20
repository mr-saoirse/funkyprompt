---
description: The funkyprompt type system based on Pydantic
---

# Pydantic types in funkyprompt

[Pydantic](https://docs.pydantic.dev/latest/) is used extensively in `funkyprompt` - the base model type for all data objects is the `AbstractModel` and the one used for vector stores which defines embeddings subclasses this - `AbstractContentModel`&#x20;

```python
class AbstractContentModel(LanceModel, AbstractModel):
    """
    MyModel = AbstractContentModel(name='test', content='test', vector=nd.zeros(EmbeddingFunctions.openai.ndims()))
    """

    vector: Vector(
        EmbeddingFunctions.openai.ndims()
    ) = EmbeddingFunctions.openai.VectorField()
    content: str = EmbeddingFunctions.openai.SourceField()
    #default system attributes
    updated_by: typing.Optional[str] = None
    updated_at: typing.Optional[str]
    aperture: int = 0
    refs: typing.List[str] = []
    document: str = ""
    cluster_id: str = ""
```

Note it now extends \`LanceModel\` which defines how lance datasets work with embedding vectors and content. For example, Lance will automatically embed content on the way in (ingestion) and the way out (embedding the query)



Models can be created dynamically with `AbstractContentModel.create_model`

