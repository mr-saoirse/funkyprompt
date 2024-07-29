from funkyprompt.core import AbstractModel
import typing
from funkyprompt.services.data import DataServiceBase


class DuckDBService(DataServiceBase):
    """the duckdb sql model uses lancedb as an assistant vector index"""

    def create_model(self, model: AbstractModel):
        pass

    def update_records(self, records: typing.List[AbstractModel]):
        pass

    def select_one(self, id: str):
        pass

    def ask(self, question: str):
        pass
