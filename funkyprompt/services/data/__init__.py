from funkyprompt.core import AbstractModel
from abc import ABC, abstractmethod
import typing


class DataServiceBase(ABC):
    """
    the abstract interface for all data services used in funkyprompt
    """

    @abstractmethod
    def create_model(self, model: AbstractModel):
        """
        stores can create a model which depending on the implementation is like creating a table.
        the abstract model provides all metadata for creating types in the underlying store
        """
        pass

    @abstractmethod
    def update_records(self, records: typing.List[AbstractModel], **kwargs):
        """
        data can be ingested into stores using the typed schema
        data can be queried by agents
        """
        pass

    @abstractmethod
    def select_one(self, id: str) -> AbstractModel:
        """
        a convenience to retrieve a specific entity by key
        """
        pass

    @abstractmethod
    def ask(self, question: str, **kwargs) -> typing.List[dict]:
        """
        an english question is converted into a query for the store
        each store will implement this in its own way
        an internal LLM can be used to reason about the question and convert it into the correct format eg. key-value or SQL
        """
        pass

    @abstractmethod
    def ask(self, query: str, **kwargs):
        """
        the query in the format required for the store.
        this could be a text search in a vector store, and sql query, list of keys etc.
        """
