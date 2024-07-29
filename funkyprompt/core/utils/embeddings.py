import typing

DEFAULT_EMBEDDING_MODEL = "text-embedding-ada-002"


def embed_collection(c: typing.List[str], provider="open_ai"):
    """get an embedding using the default embedding model"""
    from openai import OpenAI

    r = OpenAI().embeddings.create(input=c, model=DEFAULT_EMBEDDING_MODEL)
    return [e.embedding for e in r.data]


def embed_frame(
    data: typing.List[dict], field_mapping: dict = None, id_column: str = None
) -> typing.List[dict]:
    """given a data frame with texts that require embeddings do the thing and return a collection of records
    default conventions
    key->id
    field mappings for any column pair X and X_embedding
    """
    embeddings = {}

    def frame_col(name):
        """spoofs pandas or polars until we decide to add as lib dep"""
        return [i[name] for i in data]

    """apply conventions just for ease of testing - recommend passing via the model type"""
    if not id_column:
        id_column = "id"
    if not field_mapping:
        field_mapping = {
            k.replace("_embedding", ""): k for k in data.columns if "_embedding" in k
        }

    ids = list(frame_col(id_column))
    for field, mapping in field_mapping.items():
        text = frame_col(field)
        """use the embedding function"""
        embeddings[mapping] = embed_collection(text)

    """reshape to records"""
    keys = embeddings.keys()

    def _extract(keys, i):
        """add the embedded vectors"""
        """add the id column for updating and indexing"""
        d = {id_column: ids[i]}
        d.update({k: embeddings[k][i] for k in keys})
        return d

    return [_extract(keys, i) for i in range(len(data))]
