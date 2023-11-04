from funkyprompt.ops.entities import AbstractEntity, typing
from funkyprompt.io.clients.duck import DuckDBClient
from . import AbstractStore
from funkyprompt import logger, COLUMNAR_STORE_ROOT_URI
from funkyprompt.io.tools import fs
import funkyprompt


class ColumnarDataStore(AbstractStore):
    """
    Load a datastore or use it as a function

    """

    def __init__(self, entity: AbstractEntity, extra_context=None):
        super().__init__(entity=entity)
        self._entity = entity
        self._db = DuckDBClient()
        self._table_path = f"{COLUMNAR_STORE_ROOT_URI}/{self._entity_namespace}/{self._entity_name}/parts/0/data.parquet"
        # base class

        self._extra_context = extra_context

    def load(self):
        return fs.read(self._table_path)

    def __call__(self, question):
        return self.run_search(question)

    def __repr__(self) -> str:
        return f"ColumnarDataStore({self._table_path})"

    @property
    def query_context(self):
        return fs.get_query_context(self._table_path, name=self._entity_name)

    def query(self, query):
        ctx = self.query_context
        return ctx.execute(query).collect()

    def fetch_entities(self, limit=10) -> typing.List[AbstractEntity]:
        data = self.query(f"SELECT * FROM {self._entity_name} LIMIT {limit}").to_dicts()
        return [self._entity(**d) for d in data]

    def add(self, records: typing.List[AbstractEntity], mode="merge", key_field=None):
        """
        Add the fields configured on the Pydantic type that are columnar - defaults all
        These are merged into parquet files on some path in the case of this tool
        """
        if records and not isinstance(records, list):
            records = [records]

        merge_key = key_field or self._key_field

        if len(records):
            logger.info(f"Writing {self._table_path}. {len(records)} records.")
            if mode == "merge":
                logger.info(f" Merge will be on key[{merge_key}]")
            return (
                fs.merge(self._table_path, records, key=merge_key)
                if mode != "overwrite"
                else fs.write(self._table_path, records)
            )
        return records

    def run_search(
        self,
        question: str,
        limit: int = 200,
    ):
        """
        Perform the columnar data search for the queries directly on the store. This store is used for answering questions of a statistical nature about the entity.

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

        enums = {} if not build_enums else self._db.inspect_enums(self._table_path)

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
            return []

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
