"""
A wrapper around to get to know the interface and do some opinionated stuff

https://github.com/lancedb/lance
https://blog.lancedb.com/
https://lancedb.github.io/lance/read_and_write.html
https://lancedb.github.io/lancedb/basic/#creating-an-empty-table
https://lancedb.github.io/lance/notebooks/quickstart.html

"""


import lance
import lancedb
import pyarrow as pa
import typing
from funkyprompt.io.clients.duck import DuckDBClient
from funkyprompt.io.tools.fs import exists
from funkyprompt import logger
from funkyprompt import VECTOR_STORE_ROOT_URI


class LanceDataTable:
    def __init__(self, namespace, name, space=None, schema=None):
        self._name = name
        self._db_root = f"{VECTOR_STORE_ROOT_URI}/{namespace}"
        self._uri = f"{self._db_root}/{name}.lance"  #
        self._db = lancedb.connect(self._db_root)
        self._duck_client = DuckDBClient()
        try:
            self._table = self._db.open_table(self._name)
        except:
            logger.warning(
                f"Table does not exist - creating {self._db_root}/{self._name} from schema {schema}"
            )
            self._table = self.table_from_schema(self._name, schema=schema)

    @property
    def name(self):
        return self._name

    @property
    def table(self):
        return self._table

    @property
    def uri(self):
        return self._uri

    @property
    def database_uri(self):
        return self._db_root

    def __repr__(self):
        return f"LanceDataSet({self._name}): {self._uri}"

    def table_from_schema(self, name, schema, space=None):
        """
        not sure how i want to do this yet but we can create tables from schema
        might be easier to just assume we have some data at some point and then add or upsert to the table
        """

        if not isinstance(schema, pa.Schema):
            # this is because we are assuming it has this e.g. an abstract entity
            schema = schema.pyarrow_schema()
            logger.debug(f"{schema=}")
        return self._db.create_table(name=name, schema=schema)

    def upsert_records(self, records: typing.List[dict], key="id", mode="append"):
        """
        add to the table and remove anything that had the same id
        """
        if len(records):
            in_list = ",".join([f'"{r[key]}"' for r in records])
            self._table.delete(f"{key} IN ({in_list})")

            return self._table.add(data=records, mode=mode)
        return self._dataset

    def query_dataset(self, query):
        dataset = lance.dataset(self._uri)
        return self._duck_client.execute(query)

    def load(self, limit=None):
        """
        returns the polars data for the records
        """
        dataset = lance.dataset(self._uri)
        logger.debug(f"Fetching from {self._uri}")
        limit = f"LIMIT {limit}" if limit else ""
        return self._duck_client.execute(f"SELECT * FROM dataset {limit}")
