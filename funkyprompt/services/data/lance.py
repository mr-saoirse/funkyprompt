from funkyprompt.core import AbstractModel
import typing
from funkyprompt.services.data import DataServiceBase
from funkyprompt.core.utils import logger, env
from funkyprompt.core.types.sql import VectorSearchOperator
import os
from lancedb.table import LanceDataset, LanceTable
import pyarrow as pa
from lancedb.pydantic import LanceModel, Vector
from lancedb.embeddings import get_registry
from funkyprompt.services import fs
"""TODO env.preferred_test_embedding"""
func = get_registry().get("openai").create(name="text-embedding-ada-002")


class LanceAbstractContentModel(LanceModel, AbstractModel):
    """
    The abstract content model extends the AbstractModel to focus on unstructured data that we might want embeddings for (text,image)

    MyModel = AbstractContentModel(name='test', content='test', vector=nd.zeros(EmbeddingFunctions.openai.ndims()))
    See
    """

    #TODO - have the pyarrow support the union type
    id: typing.Optional[str] = None
    vector: Vector(func.ndims()) = func.VectorField()
    content: str = func.SourceField()
    name: str
    
class LanceDBService(DataServiceBase):
    """the duckdb sql model uses lancedb as an assistant vector index"""

    def _lance_connect(self, use_async=True):
        """
        This is basically for S3 access and we are specific about it
        """
        import lancedb
        #root = _setup(root)
 
        return lancedb.connect(self._db_uri)#region=os.environ.get("AWS_DEFAULT_REGION")
  
    def __init__(self, model: AbstractModel, auto_register:bool=True, schema: pa.Schema = None):
        """the model is going to be mapped to the Lance abstract content model to take advantage of its auto-vector bits
           conveniently this only needs to be in the construction and we can write dicts to the db later
        """
        self.model =  LanceAbstractContentModel.create_model(name=model.get_model_name(), 
                                           namespace=model.get_model_namespace(), 
                                                #fields=model.model_fields
                                                )
        
        self._db_uri = f"{env.STORE_ROOT}/vector-store/{self.model.get_model_namespace()}"
        self._table_uri = f"{self._db_uri}/{self.model.get_model_name()}.lance"
        self._name = self.model.get_model_name()
        self._db = self._lance_connect()
        try: 
            self._table = LanceTable(self._db, self._name)
            if not fs.exists(self._table_uri):
                raise FileNotFoundError
        except FileNotFoundError as fex:
            if auto_register:
                logger.info(f"creating table {self._name}")
                self._table = self.table_from_schema(self._name, schema_or_model=self.model)
            else:
                raise
        
    def __repr__(self):
        return str(self._table)
            
    def table_from_schema(self, name: str, schema_or_model: pa.Schema | AbstractModel ):
        """
        given a pyarrow schema or abstract model, create the lance table
        """

        if not isinstance(schema_or_model, pa.Schema):
            schema_or_model = schema_or_model.to_arrow_schema()
        return self._db.create_table(name=name, schema=schema_or_model)
    
    def create_model(self, model: AbstractModel):
        return self.table_from_schema(model.get_model_name(), schema_or_model=model)

    def update_records(self, records: typing.List[AbstractModel], mode:str='append'):
        """
        adding tables to the lance store
        """
        if not records:
            return
        if not isinstance(records,list):
            records = [records]
            
        self._delete_by_record_key_values(records)
        
        """any fields we should excluded can be determined here"""
        excluded_fields = []
        def f(d):
            d = d.model_dump() if hasattr(d, "model_dump") else d
            return {k: v for k, v in d.items() if k not in excluded_fields}
            
        self._table.add(data=[f(r) for r in records], mode=mode)

    def select_one(self, id: str):
        pass

    def ask(self, question: str):
        return self.vector_search(question=question)
    
    def _delete(self, keys: typing.List[str]):
        """remove based on the model keys - assumed to be string like"""
        key_field = self.model.get_model_key_field() or 'name'
        in_list = ",".join([f'"{k}"' for k in keys])
        return self._table.delete(f"{key_field} IN ({in_list})")
        
        
    def _delete_by_record_key_values(self, records: typing.Optional[AbstractModel]):
        """get the key values in the list and delete match"""
        key_field = self.model.get_model_key_field() or 'name'
        keys = set(
                getattr(r, key_field) if hasattr(r, "dict") else r[key_field] for r in records
            )
        return self._delete(keys)
        
    def vector_search(
        self,
        question: str,
        search_operator: VectorSearchOperator = VectorSearchOperator.L2,
        limit: int = 7,
        probes: int = 20,
        refine_factor: int = 10,
        #distance threshold
    ):
        """
        lancedb search - see docs
        """
        
        """TODO: map all enumerations to the right thing for each provider """
        search_operator = 'l2'
        
        query_root = self._table.search(question).metric(search_operator)
        #todo hybrid
        #query_root.where(preds)
        query_root = (
            query_root.limit(limit).nprobes(probes).refine_factor(refine_factor)
        )
        """determine this from the model in general"""
        _extra_fields = ["name", "content"]
        
        if isinstance(_extra_fields, list) and _extra_fields:
            query_root = query_root.select(_extra_fields)

        """some work to do on the response model"""
        return query_root.to_list()
        