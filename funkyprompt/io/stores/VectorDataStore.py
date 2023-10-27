"""
wraps lancedb for LLM stuff.

https://gpt-index.readthedocs.io/en/latest/examples/vector_stores/LanceDBIndexDemo.html

"""


from funkyprompt.ops.entities import AbstractEntity
from typing import List
from funkyprompt import logger
import warnings
from . import AbstractStore
from funkyprompt import VECTOR_STORE_ROOT_URI
from tqdm import tqdm
from funkyprompt.io.clients.lance import LanceDataTable
from functools import partial


def get_embedding_function_for_provider(text: str, embedding_provider: str = "open-ai"):
    """
    Get some embeddings we can extend this with different types are anyone can pass their own in future

    view embeddings with

    embeddings_2d = UMAP().fit_transform(list_embedding_vectors)
    2d scatter plot or otherwise
    see: https://umap-learn.readthedocs.io/en/latest/plotting.html
    https://umap-learn.readthedocs.io/en/latest/document_embedding.html

    """
    import openai

    response = openai.Embedding.create(model="text-embedding-ada-002", input=text)
    embedding = response["data"][0]["embedding"]

    return embedding


class VectorDataStore(AbstractStore):
    """
    ***
    Vector store for infesting and query data
    can be used as an agent tool to ask questions
    ***
    Example:
        from res.learn.agents.data.VectorDataStore import VectorDataStore
        store = VectorDataStore(<Entity>)
        #tool = store.as_tool()
        store("what is your question....")
        #data = store.load()
        #store.add(data)

    """

    def __init__(
        self,
        entity: AbstractEntity,
        alias: str = None,
        extra_context: str = None,
    ):
        super().__init__(entity=entity, alias=alias, extra_context=extra_context)

        self._embeddings_provider = self._entity.embeddings_provider
        # you need to ensure the entity has a vector column - in pyarrow it becomes a fixed length thing
        self._data = LanceDataTable(
            namespace=self._entity_namespace, name=self._entity_name, schema=entity
        )
        self._table_name = f"/{self._entity_namespace}/{self._entity_name}"

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            # just two types under consideration
            logger.debug(f"Using the embedding {self._embeddings_provider}")

            # we support various embeddings and we need to match what the pydantic types for lengths and what we store
            # this defaults to open ai only because we need no extra deps and not because its the best
            self._embeddings = partial(
                get_embedding_function_for_provider,
                embedding_provider=self._embeddings_provider,
            )

    def run_search(self, query, limit=5, probes=20, refine_factor=10):
        """
        perform the vector search for the query directly on the store (lance is the build in one)
        """
        V = self._embeddings(query)

        return (
            self._data.table.search(V)
            .limit(limit)
            .nprobes(probes)
            .refine_factor(refine_factor)
            .to_df()
        )[["id", "text", "_distance"]].to_dict("records")

    def add(
        self,
        records: List[AbstractEntity],
        plan=False,
    ):
        """
        loads data into the vector store if there is any big text in there
        plan false means you dont insert it and just look at it. its a testing tool.
        par_do means we will parallelize the work of computing, which we generally want to do
        """

        def add_embedding_vector(d):
            d["vector"] = self._embeddings(d["text"])
            return d

        if len(records):
            # TODO: coerce some types - anything that becomes a list of types is fine
            logger.info(f"Adding {len(records)} to {self._table_name}...")
            records_with_embeddings = list(
                tqdm(
                    (add_embedding_vector(r.large_text_dict()) for r in records),
                    total=len(records),
                )
            )

            if plan:
                return records_with_embeddings
            self._data.upsert_records(records_with_embeddings)
            logger.info(f"Records added to {self._data}")
        return records_with_embeddings

    def load(self):
        """
        Loads the lance data backed by s3 parquet files
        """
        return self._data.load()

    def __call__(self, question):
        """
        convenient wrapper to ask questions of the tool
        """
        return self.run_search(question)

    def as_function(self, question: str):
        """
        The full vector text search tool provides rich narrative context. Use this tool when asked general questions of a descriptive nature
        General descriptive questions are those that are less quantitative or statistical in nature.
        This particular function should be used to answer questions about {self._entity_name}
        You should pass in full questions as sentences with everything you want to know

        :param question: the question being asked

        """

        logger.debug(question)

        results = self.run_search(question)
        # audit
        # todo do we want these to be polar?
        logger.debug(results)
        return results
