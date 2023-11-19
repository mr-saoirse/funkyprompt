from . import AbstractStore
from funkyprompt.model.entity import AbstractModel, typing
from funkyprompt.io.clients.duck import DuckDBClient
from funkyprompt import logger, STORE_ROOT
from funkyprompt.io.tools import fs
import funkyprompt


class ColumnarDataStore(AbstractStore):
    """
    Load a datastore or use it as a function

    """

    STORE_DIR = "columnar-store"

    def __init__(cls, model: AbstractModel, description):
        super().__init__(model=model, description=description)
        cls._model = model
        cls._db = DuckDBClient()
        cls._table_path = f"{STORE_ROOT}/{cls.STORE_DIR}/{cls._model.__entity_namespace__}/{cls._model.__entity_name__}/parts/0/data.parquet"
        cls._description = description
        cls._load_table_metadata()

    def _load_table_metadata(cls):
        cls._enums = (
            cls._db.inspect_enums(cls._table_path) if fs.exists(cls._table_path) else {}
        )
        cls._fields = (
            cls._db.probe_field_names(cls._table_path)
            if fs.exists(cls._table_path)
            else []
        )

    def load(self, limit=None, lazy=False):
        """
        currently a cumbersome interface because im migrating the stores to be consistent on polars
        """
        return (
            fs.read(self._table_path, lazy=lazy)
            if not limit
            else fs.read(self._table_path, lazy=lazy).limit(limit)
        )

    def __call__(self, question):
        return self.run_search(question)

    def __repr__(self) -> str:
        return f"ColumnarDataStore({self._table_path})"

    @property
    def query_context(self):
        return fs.get_query_context(self._table_path, name=self._model.__entity_name__)

    def query(self, query):
        ctx = self.query_context
        return ctx.execute(query).collect()

    def fetch_entities(self, limit=10) -> typing.List[AbstractModel]:
        data = self.query(
            f"SELECT * FROM {self._model.__entity_name__} LIMIT {limit}"
        ).to_dicts()
        # infer / sometimes we dont need to do this but for now this is just a convenience
        model = self.get_data_model()
        return [model(**d) for d in data]

    def add(self, records: typing.List[AbstractModel], mode="merge", key_field=None):
        """
        Add the fields configured on the Pydantic type that are columnar - defaults all
        These are merged into parquet files on some path in the case of this tool
        """
        if records and not isinstance(records, list):
            records = [records]

        merge_key = key_field or self._key_field

        if len(records):
            logger.info(f"Writing {self._table_path}. {len(records)} records.")
            if not fs.exists(self._table_path):
                logger.info("registering the store as we add first time records")
                self.register_store()
            if mode == "merge":
                logger.info(f" Merge will be on key[{merge_key}]")
            return (
                fs.merge(self._table_path, records, key=merge_key)
                if mode != "overwrite"
                else fs.write(self._table_path, records)
            )
        # reload for query
        self._load_table_metadata()

        return records

    def run_search(
        self,
        question: str,
        limit: int = 200,
    ):
        """
        Perform the columnar data search for the queries directly on the store. This store is used for answering questions of a statistical nature about the entity.
        Some special links etc like image url may be in the data.

        **Args**
            question: supply a question about data in the store
            limit: limit the number of data rows returned - this is to stay with context window but defaults can be trusted in most cases
        """

        # may make these class property of the store. the search method should be something an LLM can use
        return_type = "dict"
        build_enums = True

        def parse_out_sql_and_try_clean(s):
            if "```" in s:
                s = s.split("```")[1].replace("sql", "").strip("\n")
            return s.replace("CURRENT_DATE ", "CURRENT_DATE()")

        enums = {} if not build_enums else self._enums

        prompt = f"""For a table called TABLE with the {self._fields}, and the following column enum types {enums} ignore any columns asked that are not in this schema and give
            me a DuckDB dialect sql query without any explanation that answers the question below. 
            Question: {question} """

        logger.debug(prompt)
        query = funkyprompt.agent.ask(prompt)
        query = query.replace("TABLE", f"'{self._table_path}'")
        try:
            query = parse_out_sql_and_try_clean(query)
            logger.debug(query)
            data = self._db.execute(query)
            if limit:
                data = data[:limit]
            if return_type == "dict":
                return data.to_dicts()
            return data
        # TODO better LLM and Duck exception handling
        except Exception as ex:
            logger.warning(f"Failed to execute {ex}")
            return [
                {
                    "FAILED_QUERY_REASON": f"Your question failed: {str(ex).replace(self._table_path, 'TABLE')}"
                }
            ]

    def as_function(self, question: str):
        """
        The full columnar data tool provides statistical and quantitative results but also key attributes. Usually can be used to answer questions such as how much, rank, count etc. and random facts about the entity.
        this particular function should be used to answer questions about {self._entity_name}

        :param question: the question being asked
        """

        results = self.run_search(question)
        # audit
        logger.debug(results)
        return results
