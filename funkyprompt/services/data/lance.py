from funkyprompt.core import AbstractModel
import typing
from funkyprompt.services.data import DataServiceBase
from funkyprompt.core.utils import logger
from funkyprompt.core.types.sql import VectorSearchOperator

class LanceDBService(DataServiceBase):
    """the duckdb sql model uses lancedb as an assistant vector index"""

    def create_model(self, model: AbstractModel):
        pass

    def update_records(self, records: typing.List[AbstractModel]):
        pass

    def select_one(self, id: str):
        pass

    def ask(self, question: str):
        pass
    
    def vector_search(
        self,
        question: str,
        search_operator: VectorSearchOperator = VectorSearchOperator.INNER_PRODUCT,
        limit: int = 7,
    ):
        pass