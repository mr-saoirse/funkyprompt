import duckdb
import os


def escape(s):
    return s if not isinstance(s, str) else f"'{s}'"


class _query:
    """
    ***
    very simple fluent query helper
    ***

    """

    def __init__(self, engine, root):
        self._table = root
        self._predicates = []
        self._engine = engine

    def where(self, **kwargs):
        """
        only support and predicates right now
        chained filters that can then be sub filtered in pandas
        """
        for k, v in kwargs.items():
            self._predicates.append(f"{k}={escape(v)}")
        return self

    def isin(self, **kwargs):
        """
        only support and predicates right now
        chained filters that can then be sub filtered in pandas
        """
        for k, values in kwargs.items():
            if not isinstance(values, list):
                values = [values]
            values = f",".join([escape(s) for s in values])
            self._predicates.append(f"{k} in ({values})")
        return self

    def select(self, fields=None, plan=False):
        fields = "*" if fields is None else ",".join(fields)
        query = f"""SELECT {fields} from read_parquet('{self._table}') """

        if self._predicates:
            query += "WHERE "
            query += " AND ".join(self._predicates)

        if plan:
            return query

        return self._engine.execute(query)

    def __repr__(self) -> str:
        return self.select(plan=True)


class DuckDBClient:
    def __init__(self, **options):
        self._cursor = duckdb.connect()
        AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
        AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]
        AWS_DEFAULT_REGION = os.environ["AWS_DEFAULT_REGION"]
        if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
            creds = f"""
                SET s3_region='{AWS_DEFAULT_REGION}';
                SET s3_access_key_id='{AWS_ACCESS_KEY_ID}';
                SET s3_secret_access_key='{AWS_SECRET_ACCESS_KEY}';"""

        self._cursor.execute(
            f"""
            INSTALL httpfs;
            LOAD httpfs;
            {creds}
        """
        )

    def inspect_enums(
        self, uri, enum_threshold=200, max_str_length=100, omit_fields=None
    ):
        """
        inspect enums is used to send context to LLM
        dont use this if you have sensitive data in fields or add protection

        for example this can be used if we ask vague questions
        or questions that reference misspelled or alternately spelt data - the LLM can make sense of it

        this is probably necessary for SQL types to be useful but avoides sending too much data in context
        """
        df = self.execute(f"SELECT * FROM '{uri}'")

        def try_unique(c):
            try:
                # dont allow big strings (polars notation)
                l = df[c].str.lengths().mean()
                # filter by sending back max threshold in these cases
                if l > max_str_length or c in (omit_fields or []):
                    return enum_threshold
                # if we are happy, return the list of enumerated values for LLM context
                return len(df[c].unique())

            except:
                return enum_threshold

        columns = df.columns
        enum_types = [c for c in columns if try_unique(c) < enum_threshold]
        return {c: list(df[c].unique()) for c in df.columns if c in enum_types}

    def probe_field_names(self, uri):
        return list(self.execute(f"SELECT * FROM '{uri}' LIMIT 1").columns)

    def execute(self, query):
        """ """
        return self._cursor.execute(query).pl()

    def query_from_root(self, root):
        root = root.rstrip("/")
        if root[-1 * len(".parquet") :] != ".parquet":
            root += "/*.parquet"
        return _query(self, root)
