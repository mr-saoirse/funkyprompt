from typing import List
from lancedb.embeddings import (
    EmbeddingFunctionRegistry,
    TextEmbeddingFunction,
)
import numpy as np
import typing
import json
import pyarrow as pa
import datetime

"""

TODO: below a little assortment of things we will move around later
"""

"""
Schema tools / pyarrow to mpydantic etc. crude    
"""


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

        if "timestamp" in str(field_type):
            return typing.Optional[str]
        return typing.Optional[str]

        raise NotImplementedError(f"We dont handle {field_type} ({name})")


def map_field_types_from_pa_schema(schema):
    """
    given a pyarrow schema return type info so we can create the Pydantic Model from the pyarrow table
    """

    return {f.name: map_pyarrow_type_info(f.type, f.name) for f in schema}


"""
Encoder
"""


class NpEncoder(json.JSONEncoder):
    """
    A Json encoder that is a little bit more understanding of  numpy types
    """

    def default(self, obj):
        from pandas.api.types import is_datetime64_any_dtype as is_datetime
        from pandas._libs.tslibs.timestamps import Timestamp
        from pandas import isna

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
        elif not isinstance(obj, list) and isna(obj):
            return None
        # this is a choice for serialization
        elif isinstance(obj, Timestamp) or is_datetime(obj):
            return str(obj)
        return super(NpEncoder, self).default(obj)


"""
Embeddings
"""

EMBEDDING_REGISTRY = EmbeddingFunctionRegistry.get_instance()
INSTRUCT_EMBEDDING_VECTOR_LENGTH = 768
OPEN_AI_EMBEDDING_VECTOR_LENGTH = 1536


@EMBEDDING_REGISTRY.register("openai")
class OpenAIEmbeddings(TextEmbeddingFunction):
    name: str = "text-embedding-ada-002"

    def ndims(self):
        return OPEN_AI_EMBEDDING_VECTOR_LENGTH

    def generate_embeddings(
        self, texts: typing.Union[typing.List[str], np.ndarray]
    ) -> typing.List[np.array]:
        openai = self.safe_import("openai")
        rs = openai.embeddings.create(input=texts, model=self.name).data
        emb = [v.embedding for v in rs]
        return emb

    def __call__(
        self, texts: typing.Union[typing.List[str], np.ndarray]
    ) -> typing.List[np.array]:
        return self.generate_embeddings(texts)

    def compute_source_embeddings_with_retry(
        self, texts: typing.Union[typing.List[str], np.ndarray], *args, **kwargs
    ) -> List:
        return super().compute_source_embeddings(texts, *args, **kwargs)


@EMBEDDING_REGISTRY.register("instruct")
class InstructEmbeddings(TextEmbeddingFunction):
    name: str = "hkunlp/instructor-base"
    batch_size: int = 32
    device: str = "cpu"
    show_progress_bar: bool = True
    normalize_embeddings: bool = True
    quantize: bool = False

    source_instruction: str = "represent the document for retrieval"
    query_instruction: str = (
        "represent the document for retrieving the most similar documents"
    )

    def ndims(self):
        return INSTRUCT_EMBEDDING_VECTOR_LENGTH

    def compute_query_embeddings(self, query: str, *args, **kwargs) -> List[np.array]:
        return self.generate_embeddings([[self.query_instruction, query]])

    def compute_source_embeddings(
        self, texts: typing.Union[typing.List[str], np.ndarray], *args, **kwargs
    ) -> List[np.array]:
        texts = self.sanitize_input(texts)
        texts_formatted = []
        for text in texts:
            texts_formatted.append([self.source_instruction, text])
        return self.generate_embeddings(texts_formatted)

    def generate_embeddings(self, texts: List) -> List:
        model = self.get_model()
        res = model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=self.show_progress_bar,
            normalize_embeddings=self.normalize_embeddings,
        ).tolist()
        return res

    def __call__(
        self, texts: typing.Union[typing.List[str], np.ndarray]
    ) -> typing.List[np.array]:
        return self.generate_embeddings(texts)

    def compute_source_embeddings_with_retry(
        self, texts: typing.Union[typing.List[str], np.ndarray], *args, **kwargs
    ) -> List:
        return super().compute_source_embeddings(texts, *args, **kwargs)

    # @weak_lru(maxsize=1)
    def get_model(self):
        instructor_embedding = self.safe_import(
            "InstructorEmbedding", "InstructorEmbedding"
        )
        torch = self.safe_import("torch", "torch")

        model = instructor_embedding.INSTRUCTOR(self.name)
        if self.quantize:
            if (
                "qnnpack" in torch.backends.quantized.supported_engines
            ):  # fix for https://github.com/pytorch/pytorch/issues/29327
                torch.backends.quantized.engine = "qnnpack"
            model = torch.quantization.quantize_dynamic(
                model, {torch.nn.Linear}, dtype=torch.qint8
            )
        return model


class Embeddings:
    """
    an opinionated wrapper around the embedding function loaders - may deprecate
    """

    def __init__(self):
        self._registry = {}

    def __getitem__(self, key):
        if key in self._registry:
            return self._registry[key]
        else:
            if key == "openai":
                open_ai_embedding = EMBEDDING_REGISTRY.get("openai").create()
                self._registry[key] = open_ai_embedding
                return open_ai_embedding

            if key == "instruct":
                instruct_embedding = EMBEDDING_REGISTRY.get("instruct").create()
                self._registry[key] = instruct_embedding
                return instruct_embedding

    @property
    def openai(self):
        return self["openai"]

    @property
    def instruct(self):
        return self["instruct"]


EmbeddingFunctions = Embeddings()

from .entity import (
    AbstractContentModel,
    AbstractModel,
    InstructEmbeddingContentModel,
)

from .func import FunctionDescription
