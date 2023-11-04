"""
This is a simple vector store implementation
We use Pydantic types to load and save

- We can query over multiple stores using duckdb to join
- we can do hybrid search. Currently we have a simple AND predicate kwargs but we could do more interesting things depending on use cases. 
  its tacitly assumes that a vector store use case is predominantly vector based and the predicates are add to restrict the set
- we currently do not have a way to reload dynamic types from schema which will be a nice feature - its the reverse schema from pyarrow 
- we need to test how we are using ids to avoid duplicates (especially in same set) - its related to the document model
- built on lance we can do cool stuff with indexes, versions+schema_evo and more

"""


from funkyprompt.ops.entities import AbstractEntity
from typing import List
from funkyprompt import logger
import warnings
from . import AbstractStore, get_embedding_provider
from tqdm import tqdm
from funkyprompt.io.clients.lance import LanceDataTable

import pandas as pd

DEFAULT_EMBEDDING_PROVIDER = "open-ai"


def get_embedding_function_for_provider(
    embedding_provider: str = DEFAULT_EMBEDDING_PROVIDER,
):
    """
    Get some embeddings we can extend this with different types are anyone can pass their own in future

    view embeddings with

    embeddings_2d = UMAP().fit_transform(list_embedding_vectors)
    2d scatter plot or otherwise
    see: https://umap-learn.readthedocs.io/en/latest/plotting.html
    https://umap-learn.readthedocs.io/en/latest/document_embedding.html

    """

    if embedding_provider == "instruct":
        # you need to have added the dep for Instruct:> pip install InstructorEmbedding
        # we load it from lib level so its a singleton (load times)
        model = get_embedding_provider(embedding_provider)

        def embed(text):
            return model.encode(text)

    else:
        import openai

        def embed(text):
            response = openai.Embedding.create(
                model="text-embedding-ada-002", input=text
            )
            return response["data"][0]["embedding"]

    return embed


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

        self._embeddings_provider = (
            self._entity.embeddings_provider or DEFAULT_EMBEDDING_PROVIDER
        )
        # you need to ensure the entity has a vector column - in pyarrow it becomes a fixed length thing
        self._data = LanceDataTable(
            namespace=self._entity_namespace, name=self._entity_name, schema=entity
        )
        self._table_name = f"/{self._entity_namespace}/{self._entity_name}"

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            # just two types under consideration
            logger.debug(
                f"Using the embedding {self._embeddings_provider} when initializing the vector store {self._table_name}"
            )

            self._embeddings = get_embedding_function_for_provider(
                embedding_provider=self._embeddings_provider
            )

    @staticmethod
    def _load_vector_store(
        name: str, namespace: str = "default", embedding_provider: str = None
    ):
        """
        This is a convenience method but to make this correct we need to determine how to
        reload an entity from a schema with proper embedding meta data etc
        """
        from funkyprompt.ops.entities import (
            AbstractVectorStoreEntry,
            InstructAbstractVectorStoreEntry,
        )

        Factory = (
            InstructAbstractVectorStoreEntry
            if embedding_provider == "instruct"
            else AbstractVectorStoreEntry
        )
        dummy_entity = Factory.create_model(name, namespace=namespace)

        # we should think about this. this makes sense because we assume certain things about config
        # mostly its just the name and namespace but for example the embedding also needs to be set properly
        # we dont currently care about the schema at this stage but we could improve this
        return VectorDataStore(dummy_entity)

    @property
    def dataset(
        cls,
    ):
        """
        assumed to exist for now
        """
        return cls._data.dataset

    def query(self, query):
        return self._data.query_dataset(query)

    def run_search(
        self,
        queries: List[str],
        limit: int = 3,
        probes: int = 20,
        refine_factor: int = 10,
        metric: str = "l2",
        # we generally want to really on text only but may add sys fields  and a few labels
        columns: List[str] = ["id", "text", "doc_id"],
        **predicates,
    ):
        """
        Perform the (hybrid) vector search for the queries directly on the store.
        Supplying a list of questions is advised for separate topics that appear i the same question
        - Please ask as many question as you think are useful

        **Args**
            queries: one or more queries which are each a full question with specific details. Splitting questions up can be useful if the question is divergent covering many different topics.
            limit: a vector search / or search retrieval limit
            probes: vector search property - higher number more accurate by slower
            refine_factor: in memory reranking, higher number more accurate
            metric: l2(default)|cosine|dot
            columns: columns to restrict
        """

        # TODO: abstract run search into base and maybe implement the parallization ??
        #  see: https://lancedb.github.io/lancedb/search/#flat-search
        # https://lancedb.github.io/lancedb/sql/

        # predicates are more specific - might be good having a fallback to zero predicates option
        # can add vector column name which defaults to vector to search other things. ok its opening up now
        # we want to work with this and out TextModel + Data Model which can be graph aware

        if not isinstance(queries, list):
            queries = [queries]

        results = []
        # in future we will par-do this
        for query in queries:
            logger.debug(query)
            V = self._embeddings(query)
            query_root = self._data.table.search(V).metric(metric)

            if predicates:
                # simple version to do some simple restrictions. We will need something more powerful
                preds = "AND ".join(
                    [
                        f"{k} IN ({', '.join(map(str, v))})"
                        if isinstance(v, list)
                        else f"{k} = {repr(v)}"
                        for k, v in predicates.items()
                    ]
                )
                logger.debug(f"Adding predicates {preds}")
                query_root.where(preds)

            query_root = (
                query_root.limit(limit).nprobes(probes).refine_factor(refine_factor)
            )
            if columns:
                query_root = query_root.select(columns)

            # repass the columns but basically we dont want the vector(s)
            df = query_root.to_df()

            if len(df) > 0:
                df = df[columns + ["_distance"]]

            results.append(df[df["text"].notnull()])

        # we re rank to get answers over all questions based on abs distance[:limit]
        df = pd.concat(results)
        if len(df) == 0:
            # the concept of reroutng
            logger.debug("advising different strategy")
            return pd.DataFrame(
                [
                    {
                        "text": "As there were no results here, You should search for a different and more specific function to answer this part of the question"
                    }
                ]
            ).to_dict("records")
        return df.sort_values("_distance").to_dict("records")

    def check_length(self, records, max_text_length=int(1 * 1e4)):
        """
        simple length checker for the embedding or some small chunk size
        this for testing only but in practice we need smarted chunking
        todo: length would be a property of the embedding or the type
        """
        for r in records:
            if len(r.text) > max_text_length:
                logger.warning(
                    f"Splitting text of length {len(r.text) } > {max_text_length}. You should a sensible document index instead."
                )
                for chunk in r.split_text(max_text_length):
                    yield chunk
            else:
                yield r

    def add(self, records: List[AbstractEntity], plan=False):
        """
        loads data into the vector store if there is any big text in there
        plan false means you dont insert it and just look at it. its a testing tool.
        par_do means we will parallelize the work of computing, which we generally want to do
        """

        if records and not isinstance(records, list):
            records = [records]

        def add_embedding_vector(d):
            d["vector"] = self._embeddings(d["text"])
            return d

        if len(records):
            # TODO: coerce some types - anything that becomes a list of types is fine
            logger.info(f"Adding {len(records)} to {self._table_name}...")
            records_with_embeddings = list(
                tqdm(
                    (
                        add_embedding_vector(r.large_text_dict())
                        for r in self.check_length(records)
                    ),
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

    def __call__(self, question, **kwargs):
        """
        convenient wrapper to ask questions of the tool
        """
        return self.run_search(question, **kwargs)

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

    def plot(cls, plot_type=False, labels="doc_id", questions=None, **kwargs):
        """
        Use UMAP to plot the vector stores embeddings. Be carefully to limit size in future

        Example:
            store = VectorDataStore(InstructAbstractVectorStoreEntry.create_model("BookChapters-open-ai"))
            store.plot()

        require umap to be installed -
        ``pip install umap-learn[plot]```
        see docs for plotting: https://umap-learn.readthedocs.io/en/latest/plotting.html

        **Args**
            plot_type: points(default)|connectivity}diagnostic
            labels: use in plotting functions to add legend
            questions: add questions into the space as separate docs
            kwargs: any parameter of the selected plotting - see UMAP docs

        """
        import numpy as np
        import umap
        import umap.plot
        import polars as pl

        logger.debug(f"Loading data...")
        # TODO control the columns we are loading
        df = cls.load()[["name", "text", "doc_id", "vector", "id"]]
        if questions:
            # add question with their own doc id
            logger.debug(f"Adding questions")

            df.extend(
                # todo inspect the columns we need first
                pl.DataFrame(
                    {
                        "name": f"q{id}",
                        "text": q,
                        "doc_id": f"q{id}",
                        "vector": pl.Series(cls._embeddings(q)).cast(pl.Float32()),
                        "id": f"q{id}",
                    }
                    for id, q in enumerate(questions)
                )
            )
        v = np.stack(df["vector"].to_list())
        logger.debug(f"Fitting data...")
        F = umap.UMAP().fit(v)
        if plot_type == "connectivity":
            # edge_bundling='hammer'
            umap.plot.connectivity(F, labels=df[labels], **kwargs)
        elif plot_type == "diagnostic":
            diagnostic_type = kwargs.get("diagnostic_type", "pca")
            umap.plot.diagnostic(
                F,
                diagnostic_type=diagnostic_type,
                **{k: v for k, v in kwargs.items() if k not in ["diagnostic_type"]},
            )
        elif plot_type == "interactive":
            umap.plot.output_notebook()
            hover_data = pd.DataFrame(
                {"label": df[labels].to_list(), "text": df["text"].to_list()}
            )
            hover_data["item"] = hover_data["text"].map(lambda x: {"text": x})
            p = umap.plot.interactive(
                F,
                tools=["pan", "wheel_zoom", "box_zoom", "save", "reset", "help"],
                labels=df[labels],
                point_size=5,
                hover_data=hover_data,
                **kwargs,
            )  #

            umap.plot.show(p)
        else:
            umap.plot.points(F, labels=df[labels], **kwargs)

        return df.hstack(
            pl.DataFrame(F.embedding_, schema={"x": pl.Float32, "y": pl.Float32})
        )
        return F
