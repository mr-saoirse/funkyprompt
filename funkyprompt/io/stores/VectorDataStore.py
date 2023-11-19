import lancedb
import lance
from funkyprompt.model.entity import AbstractContentModel, typing, BaseModel
from funkyprompt.io.clients.duck import DuckDBClient
import funkyprompt
from funkyprompt import STORE_ROOT
import polars as pl
import pyarrow as pa
from funkyprompt.io.stores import AbstractStore


class StoreSearchVector:
    pass


class QueryOptions(BaseModel):
    limit: int = 5
    probes: int = 20
    metric: str = "l2"
    refine_factor: int = 10
    columns: typing.List[str] = ["name", "content"]
    # no point returning anything after something like this
    distance_threshold: float = 0.65


class VectorDataStore(AbstractStore):
    """
    In funkyprompt we have a generic store that implements search semantics over stores
    """

    # for store registries this is a type that can be changed
    STORE_DIR = "vector-store"

    def __init__(
        cls,
        model: AbstractContentModel,
        description: str,
        store_vector: StoreSearchVector = None,
        register_store=True,
    ):
        """
        **Args**
            model: A pydantic model that inherits from a suitable schema aware base
            description: a description of the store that can be registered for search
            store_vector: a vectorized description of how and when to use the store

        """
        super().__init__(model=model, description=description)
        cls._model = model
        cls._description = description
        cls._store_vector = store_vector

        cls._db_uri = f"{STORE_ROOT}/{cls.STORE_DIR}/{cls._model.__entity_namespace__}"
        cls._table_uri = f"{cls._db_uri}/{cls._model.__entity_name__}.lance"
        cls._table = cls._open_table(register=register_store)
        cls._duck_client = DuckDBClient()

    def _get_lance_connection(self):
        # from env + do some s3 stuff
        # os.environ["AWS_ACCESS_KEY_ID"] = AWS_ACCESS_KEY_ID
        # os.environ["AWS_SECRET_ACCESS_KEY"] = AWS_SECRET_ACCESS_KEY
        # return lancedb.connect(root, region=os.environ.get("AWS_DEFAULT_REGION"))

        db = lancedb.connect(self._db_uri)
        return db

    def _open_table(self, register=True):
        db = self._get_lance_connection()
        name = self._model.__entity_name__
        if name in db:
            return db[name]
        if register:
            self.register_store()
        funkyprompt.logger.debug(f"Creating table {name=} {self._model=}")
        # dont always have to call to pyarrow schema but making it explicit
        schema = self._model.to_arrow_schema()

        return db.create_table(
            name,
            schema=schema,
            embedding_functions=self._model.parse_embedding_functions(),
        )

    def query_dataset(self, query):
        dataset = lance.dataset(self._table_uri)
        return self._duck_client.execute(query)

    def load(self, limit=None, lazy=False):
        """
        returns the polars data for the records
        """
        dataset = lance.dataset(self._table_uri)
        # logger.debug(f"Fetching from {self._table_uri}")
        limit = f"LIMIT {limit}" if limit else ""
        return self._duck_client.execute(f"SELECT * FROM dataset {limit}")

    def add(cls, records: typing.List[AbstractContentModel], key_field=None):
        """
        Add record(s) to the store using the correct schema

        **Args**
           records: A list of abstract entities (or dicts that conform to that schema)
           key_field: The pyantic type either by default or config should define the key field for upsert or it can be passed in here
        """
        if not isinstance(records, list):
            records = [records]
        return cls.upsert_records(records=records, key=key_field)

    def __call__(cls, *args, **kwargs):
        return cls.run_search(*args, **kwargs)

    def run_search(
        cls,
        questions: typing.List[str],
        since_date: str = None,
        # lance db settings + our own system predicates including probe, limit
        query_options: QueryOptions = QueryOptions(),
        # add schema predicates for IN and = to matches for simple filtering
        **predicates,
    ):
        """
        run a vector search for the given entity

        **Args**
           questions: one or more questions to ask the store. Recommend full sentences.
           since_date: for restricting vector searches post some date
           query_options: underlying query options - usually the defaults are sufficient
        """
        # want to remove this as dep
        import pandas as pd

        query_options = query_options or QueryOptions()

        # we dont have a case of passing empty predicates
        predicates = {k: v for k, v in predicates.items() if v}

        funkyprompt.logger.debug(
            f"Searching with {cls._model.__entity_name__}, {predicates=} {query_options=}"
        )

        def _predicates_from_kwargs():
            preds = None
            if predicates:
                funkyprompt.logger.debug(preds)
                preds = "AND ".join(
                    [
                        f"{k} IN ({', '.join(map(str, v))})"
                        if isinstance(v, list)
                        else f"{k} = {repr(v)}"
                        for k, v in predicates.items()
                        if v is not None
                    ]
                )
            # note updated_at is a conventional timestamp column that we can add to schema somewhere
            if since_date:
                pred = f"updated_at > date '{since_date}'"
                preds = f"{preds} AND {pred}" if preds else pred
            return preds

        def search_one(question):
            padded_question = f"{question}"
            funkyprompt.logger.info(f"Asking {question=}")
            query_root = (
                cls._table.search(padded_question).limit(query_options.limit)
                # .nprobes(query_options.probes)
                # .refine_factor(query_options.refine_factor)
            )

            preds = _predicates_from_kwargs()
            if preds:
                query_root = query_root.where(preds)

            # im not sure why the vector is returned
            return (
                query_root.select(query_options.columns)
                .to_pandas()
                .drop("vector", axis=1)
            )

        if not isinstance(questions, list):
            questions = [questions]

        # combine to a polars table
        ensure_columns = ["_distance"] + query_options.columns
        result = pd.concat([search_one(q) for q in questions])

        if not len(result):
            return []

        funkyprompt.logger.debug(f"Fetched {len(result)}")

        # result = pl.from_arrow(pa.concat_tables(result))
        # result = result.filter(pl.col("_distance") < query_options.distance_threshold)

        result = (
            result[ensure_columns]
            .sort_values("_distance", ascending=False)
            .head(query_options.limit)
        )

        # default to dicts - may create an interface for searches later e.g. response.data response.status response.message etc
        return result.to_dict("records")

    def upsert_records(
        cls, records: typing.List[AbstractContentModel], key="name", mode="append"
    ):
        """
        add to the table and remove anything that had the same id
        """

        key = key or "name"
        if len(records):
            keys = set(
                getattr(r, key) if hasattr(r, "dict") else r[key] for r in records
            )
            in_list = ",".join([f'"{k}"' for k in keys])
            try:
                cls._table.delete(f"{key} IN ({in_list})")
            except:
                import traceback

                funkyprompt.logger.warning(
                    f"Failed in a delete transaction using key {key}  - this can lead to duplicates {traceback.format_exc()}"
                )

            # todo - support schema migration and fix this support for dicts or models without vectors that need embedding
            def f(d):
                d = d.dict() if hasattr(d, "dict") else d
                return {k: v for k, v in d.items() if k not in ["vector"]}

            records = [f(d) for d in records]
            return cls._table.add(data=records, mode=mode)
        return cls.load()

    def plot(cls, plot_type=False, labels="document", questions=None, **kwargs):
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

        # not sure if we need this for hover data
        import pandas as pd

        funkyprompt.logger.debug(f"Loading data...")
        # TODO control the columns we are loading
        df = cls.load()[["name", "content", "vector", "document"]]
        if questions:
            # add question with their own doc id
            funkyprompt.logger.debug(f"Adding questions")

            df.extend(
                # todo inspect the columns we need first
                pl.DataFrame(
                    {
                        "name": f"q{id}",
                        "content": q,
                        "vector": pl.Series(cls._embeddings(q)).cast(pl.Float32()),
                    }
                    for id, q in enumerate(questions)
                )
            )
        v = np.stack(df["vector"].to_list())
        funkyprompt.logger.debug(f"Fitting data...")
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
                {"label": df[labels].to_list(), "text": df["content"].to_list()}
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

    def _rename(cls, columns):
        """
        this is not save - it drops and adds a new table with the Model without transactions
        it is a helper for aggressively changing data during testing only - we will add more useful functions later
        """

        # load and rename columns
        df = cls.load()
        df = df.rename(columns)
        # replace the dataset

        lance.write_dataset(
            df, cls._table_uri, schema=cls._model.to_arrow_schema(), mode="overwrite"
        )
