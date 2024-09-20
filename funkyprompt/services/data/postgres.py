"""
The postgres service is a wrapper around psycopg2 with some awareness of a pg_vector extension and age extension
In funkyprompt the game is to play nice with AbstractModels so that the postgres stuff is under the hood


# Reading
[pg_vector](https://github.com/pgvector/pgvector)
[Text Search Control](https://www.postgresql.org/docs/current/textsearch-controls.html)
"""

import json
import typing
import psycopg2
from funkyprompt.core import AbstractModel, AbstractEntity, AbstractEdge
from funkyprompt.services.data import DataServiceBase
from funkyprompt.core.utils.env import POSTGRES_CONNECTION_STRING, AGE_GRAPH
from funkyprompt.core.utils import logger
from funkyprompt.core.types.sql import VectorSearchOperator
from funkyprompt.entities import resolve as resolve_entity
from pydantic._internal._model_construction import ModelMetaclass

def cypher_with_age_wrapper(q: str, returns=None):
    """wrapper a cypher query - specify the return variables expected"""
    returns = returns or ['n']
    returns = f",".join([f'{n} agtype' for n in returns])
    return (
        f""" LOAD 'age';
        SET search_path = ag_catalog, "$user", public;
        SELECT * 
        FROM cypher('{AGE_GRAPH}', $$
            {q}
        $$) as ({returns});"""
        if q
        else None
    )


def _parse_vertex_result(x):
    x = json.loads(x["n"].split("::")[0])
    parts = x["label"].split("_", 1)
    if len(parts) == 2:
        model_namespace, model_name = parts
    else:
        model_namespace, model_name = 'core', parts[0]
    name = x["properties"].get("name")
    d = {
        "entity_model_name": model_name,
        "entity_model_namespace": model_namespace,
        "name": name,
    }

    d["model"] = resolve_entity(**d)

    return d

class GraphManager:
    def __init__(self, service: "PostgresService"):
        self._service = service
        
    def query_by_path(cls, path, edge_name='TAG', filter_node_types: typing.Optional[str] = None):
        """
        given a path A/B/C we query nodes connected along edges (tags)
        """
        
        #TEMP - we can do multiple easily enough
        if isinstance(path,str):
            path = [path]
                    
        if len(path):
            """for any number of matches"""
            predicates = f" OR ".join([f"( b.name = '{p.split('/')[0]}' and c.name = '{p.split('/')[1]}' )" for p in path])
            Q = f"""MATCH (a)-[:{edge_name}]->(b)-[:{edge_name}]->(c)
            WHERE {predicates}
            RETURN a
            """

            logger.trace(f"Query names {Q=}")
            data = cls._service._execute_cypher(Q)
            names = [json.loads(d['n'].split('::')[0]).get('properties',{}).get('name') for d in data]
            
            logger.debug(f"Query names {names=}")
            return cls._service.select_by_names(names)
        else:
            raise Exception("You must pass a set of paths of the form A/B")
class PostgresService(DataServiceBase):
    """the postgres service wrapper for sinking and querying entities/models

    Examples:

    ```python
    from funkyprompt.entities import Project
    #having create a model Project._register() which uses the service under the hood
    from funkyprompt.services import entity_store

    #create a typed instance
    store =entity_store(Project)

    #add entries
    p=Project(name='test', description='this is a test project for testing search about sirsh interests', labels=['test'])
    store.update_records(p)

    # look up nodes without type
    x= store.get_nodes_by_name('test')
    # specifically lookup a node of type
    store.select_one('test')

    # run any query (store.execute) or do vector search
    store.ask(question="are there any projects about sirsh's interests")

    ```
    """

    def __init__(self, model: AbstractModel):
        self.conn = psycopg2.connect(POSTGRES_CONNECTION_STRING)
        """we do this because its easy for user to assume the instance is what we want instead of the type"""
        model = AbstractModel.ensure_model_not_instance(model)
        self.model = model

    def _alter_model(cls):
        """try to alter the table by adding new columns only"""
        raise NotImplementedError("alter table not yet implemented")
    
    def _drop_graph(self):
        """danger zone"""
        Q = """MATCH (n)
            DETACH DELETE n"""
            
        return self._execute_cypher(Q)
    
    
    def _create_schema(self, schema_name:str):
        """create a schema in the database"""
        Q = f"""CREATE SCHEMA {schema_name}"""
        return self.execute(Q)

    def _create_model(cls):
        """internal create model"""

        try:
            script = cls.model.sql().create_script()
            logger.debug(script)
            cls.execute(script)
            """
            for now create the node type separately but we could merge
            """
            script = cypher_with_age_wrapper(cls.model.cypher().create_script())
            cls.execute(script)
            logger.info(f"updated {cls.model.get_model_fullname()}")
        except Exception as pex:
            if pex is psycopg2.errors.DuplicateTable:
                cls._alter_model()
            else:
                raise

    def __drop_table__(cls):
        """drop the table - really just for testing and not something we would likely do often"""
        script = f"drop table {cls.model.get_model_fullname()}"
        logger.debug(script)
        cls.execute(script)
        logger.info(f"dropped {cls.model.get_model_fullname()}")

    def execute(
        cls,
        query: str,
        data: tuple = None,
        as_upsert: bool = False,
        page_size: int = 100,
    ):
        """run any sql query
        this works only for selects and transactional updates without selects
        """
        
        # lets not do this for a moment
        # if not isinstance(data, tuple):
        #     data = (data,)
        
        if not query:
            return
        try:
            c = cls.conn.cursor()
            if as_upsert:
                psycopg2.extras.execute_values(
                    c, query, data, template=None, page_size=page_size
                )
            else:
                c.execute(query, data)

            if c.description:
                result = c.fetchall()
                """if we have and updated and read we can commit and send,
                otherwise we commit outside this block"""
                cls.conn.commit()
                column_names = [desc[0] for desc in c.description or []]
                result = [dict(zip(column_names, r)) for r in result]
                return result
            """case of upsert no-query transactions"""
            cls.conn.commit()
        except Exception as pex:
            logger.warning(f"Failing to execute query {query} for model {cls.model} - Postgres error: {pex}, {data}")
            cls.conn.rollback()
            raise
        finally:
            cls.conn.close

    def _execute_cypher(
        cls,
        query: str,
    ):
        """wrapper to run cypher queries in AGE (needs a basic wrapper)"""
        try:
            return cls.execute(cypher_with_age_wrapper(query))
        except:
            logger.warning(f"Failing to execute cypher query")
            raise
    
    def execute_upsert(cls, query: str, data: tuple = None, page_size: int = 100):
        """run an upsert sql query"""
        return cls.execute(query, data=data, page_size=page_size, as_upsert=True)

    @classmethod
    def create_model(cls, model: AbstractModel):
        """creates the model based on the type.
        system fields are added for created and updated at.
        the raw table is associated with separate embeddings table via a view
        """
        return cls(model)._create_model()
    
    @property
    def graph(self):
        """provide access to extended graph based functionality"""
        return GraphManager(self)


    def queue_update_embeddings(self, result: typing.List[dict]):
        """embeddings in general should be processed async
        when we insert some data, we read back a result with ids and column data for embeddings
        we then use whatever provided to get an embedding tensor and save it to the database
        this insert could be inline or adjacent table
        """
        from funkyprompt.core.utils.embeddings import embed_frame

        helper = self.model.sql()
        
        if not helper.embedding_fields:
            """no embeddings, no op"""
            return

        embeddings = embed_frame(
            result,
            field_mapping=self.model.get_embedding_fields(),
            id_column=helper.id_field,
        )

        query = helper.embedding_fields_partial_update_query(batch_size=len(result))

        return self.execute_upsert(
            query=query, data=(helper.partial_model_tuple(e) for e in embeddings)
        )
        
    def select_by_names(self, names: typing.List[str]):
        """name lookup"""
        if not names:
            return
        if not isinstance(names,list):
            names = [names]
        column: str = "name"
        """selects one by name using the internal model"""
        table_name = self.model.get_model_fullname()
        fields = ",".join(self.model.sql().field_names)
        q = f"""SELECT { fields } FROM {table_name} where {column} = ANY(%s);"""
        data = self.execute(q,names)
        if len(data):
            logger.debug(f"Fetched {len(data)} related entries")
            """TODO: trace loaded keys here and elsewhere as this is like citations"""
            return [self.model(**dict(d)) for d in data ]
        

    def select_one(self, name: str, column: str = "name"):
        """selects one by name using the internal model"""
        table_name = self.model.get_model_fullname()
        fields = ",".join(self.model.sql().field_names)
        q = f"""SELECT { fields } FROM {table_name} where {column} = '{name}' limit 1"""
        data = self.execute(q)
        if len(data):
            return self.model(**dict(data[0]))
        
    def select(self, limit:int=None):
        """selects top records ordered by date desc"""
        table_name = self.model.get_model_fullname()
        fields = ",".join(self.model.sql().field_names)
        q = f"""SELECT { fields } FROM {table_name} order by created_at desc limit {limit or 10}"""
        data = self.execute(q)
        return [self.model(**dict(d)) for d in data]
        
    def ask(self, question: str):
        """[DEPRECATE] natural language to SQL is used to query the store"""
        # prompt  = self.model.get_model_as_prompt()
        query = self.model.sql().query_from_natural_language(
            question,
        )
        return self.execute(query)

    def __getitem__(self, name: str):
        """the key value lookup on the graph is used for the labelled model type and name"""
        entity = self.select_one(name)
        """what we will do here is create what is called a wrapped entity"""
        return entity

    @classmethod
    def get_nodes_by_name(cls, name: str, default_model: None) -> typing.List[AbstractEntity]:
        """the node mode is only useful when we are invariant to types,
        because we can resolve nodes even when we dont know their type.
        Suppose an LLM knows that something _is_ an entity but does not know what it is
        we can match ANY nodes in the graph and then when we know the label->entity map
        we can then select one by one.
        We can make this more efficient in a number of ways but for now it provides a nice
        entity resolution route for agent
        Examples of optimization:
        - cached types in the instance
        - async parallel search over nodes
        """

        cypher_query = f"""MATCH (v {{name:'{name}'}}) RETURN v"""
        data = cls(AbstractEntity).query_graph(cypher_query)
        """do the entity wrapper stuff here
           should return an expanded abstract model i.e. one with lots of metadata in a structure e.g. desc, data, available functions
        """

        """we can wrap the entities when we know their type when they match name
           we need to do multiple select_ones for each matched type here (TODO:)
        """
        data = [_parse_vertex_result(x) for x in data]
        if not len(data):
            """we are going to try and use graph nodes to manage any type but we can also just assume one exists on this entity type"""
            data = [ {'name':name, 'model': default_model } ]
            
        """a not so efficient way to load entities but fine for now"""
        valid_entities = []
        for d in data:
            try:
                """sketches: we want a generalized way to load entities and register their metadata"""
                e = cls(d["model"]).select_one(d["name"])
                if e:
                    valid_entities.append(e)
            except Exception as ex:
                logger.warning(f"Failed to load an entity from the graph node - {d}")
              
        return valid_entities

    def query_graph(self, query: str, returns: typing.List[str]=None):
        """query the graph with a valid cypher query
        Args:
            query: a cypher query
            returns: a list of return variables e.g. n,e,r - defaults to n i.e. a single result column
        """
        ###
        """AGE/postgres runs cypher with some boilerplate"""
        query = cypher_with_age_wrapper(query,returns=returns)
        return self.execute(query)

    def ask_graph(self, question: str):
        """map the question into a valid cypher query and execute query on the graph"""
        query = self.model.cypher().query_from_natural_language(question)

        return self.query_graph(query)

    def ask(
        self,
        question: str,
        after_date: typing.Optional[dict] | str = None,
        limit: int = None,
        **kwargs,
    ):
        """
        a high level interface that determines the correct mode of query from natural language question
        different possible avenues from here... experimental
        """

        from funkyprompt.core.agents import QueryClassifier

        # TODO: this method is a pivotal point of funkyprompt - if types are good, this thing should work and be fast

        """this is experimental - there are other ways to do this e.g. push down in postgres"""
        classification: QueryClassifier = (
            QueryClassifier._classify_question_as_query_for_model(
                model=self.model, question=question
            )
        )

        print(classification)

        """we should audit all query decisions - maybe as an async task
        below this is framed as an either or to put pressure on the decision maker
        but we could also do this as a parallel search, try to avoid false fetches and combine
        """

        results = {}
        # we should try to avoid using general entity terms and use this just for specific things
        if classification.recommend_query_type == "ENTITY":
            for e in classification.entities:
                for r in self.get_nodes_by_name(e, default_model=self.model):
                    results[r.id] = r
            # if we have nothing, try the other options
            if len(results):
                return list(results.values())

        # if we have a high confidence query and it works, do this
        if (
            classification.sql_query
            and classification.sql_query_confidence_based_on_model
            > QueryClassifier.Config.MIN_QUERY_CONFIDENCE
        ):
            # TODO: manage thresholds and multiple queries
            # TODO drop embeddings from the result that is returned
            data = self.execute(classification.sql_query)
            if len(data):
                return data

        """fall back to a vector search - a temporal predicate will be needed here"""
        count_vector_result = 0
        for q in classification.decomposed_questions:
            try:
                for r in self.vector_search(q):
                    results[r["id"]] = r
                    count_vector_result+= 1
            except:
                #because we do this aspirationally we only error if the recommended type was vector
                if classification.recommend_query_type == 'VECTOR':
                    raise
        #telemetry
        logger.debug(f"fetched {count_vector_result} using vector search")
        return list(results.values())

    def vector_search(
        self,
        question: str,
        search_operator: VectorSearchOperator = VectorSearchOperator.INNER_PRODUCT,
        limit: int = 7,
    ):
        """
        search the model' embedding content
        in generally we can query multiple embeddings per table but for now testing with just one

        Args:
            question: a natural language question
            search_operator: the pg_vector operator type as an enum - uses the default inner product because we use the open ai embeddings by default
            limit: limit results to return

        Example:

            ```python
            from funkyprompt.core import ConversationModel
            from funkyprompt.services import entity_store
            #load the store for this type/model/table
            store =entity_store(ConversationModel)
            #search...
            store.vector_search('what did i asked about installing postgres on the mac')
            ```
        """

        from funkyprompt.core.utils.embeddings import embed_collection

        helper = self.model.sql()

        if not helper.embedding_fields:
            raise Exception(
                "this type does not support vector search as there are no embedding columns"
            )

        """default to one for now and OR later 
        - we actually need to determine the embedding provided for each column from the metadata 
        :TODO: test the more general case of multiple columns with multiple providers when getting embeddings
        it may be a different operator is better in each case
        """
        vec = embed_collection([question])[0]

        embedding_fields = helper.embedding_fields[0]
        select_fields = ",".join(helper.field_names)

        distance_max: float = (
            -0.79
        )  ##TODO: this only makes sense for the neg inner product
        part_predicates = (
            f"{embedding_fields} {search_operator.value} '{vec}' < {distance_max}"
        )

        """distances are determined in different ways, that includes what 'large' is"""
        distances = f"{embedding_fields} {search_operator.value} '{vec}' "

        """TODO: we could make some attempt to normalize for different systems
        the scale of divergence e.g. for NE_INNER_PRODUCT (-1 - d)"""
        """generate the query for now for only one embedding col"""
        query = f"""SELECT
            {select_fields},
            ({distances}) as distances
            from {helper.table_name} 
              WHERE {part_predicates}
                order by {distances} ASC LIMIT {limit}
             """

        return self.execute(query)
    
    
    def update_records(self, records: typing.List[AbstractModel]):
        """records are updated using typed object relational mapping.
        the embedding update is queued
        """

        # TODO: there is a very confusing behaviour when the update records works on dictionaries and not objects

        if records and not isinstance(records, list):
            records = [records]
        """
        something i am trying to understand is model for sub classed models e.g. missing content but
        """
        helper = self.model.sql()  
        data = [
            tuple(helper.serialize_for_db(r).values()) for i, r in enumerate(records)
        ]

        if records:
            query = helper.upsert_query(batch_size=len(records))
            try:
                result = self.execute_upsert(query=query, data=data)
            except:
                logger.info(f"Failing to run {query}")
                raise

            """for now do inline but this could be an async thing to not block"""
            self.queue_update_embeddings(result)

            """ <<GRAPH>>
                add the node and edges for certain types that have unique names and are entity like
                we could do this as a transaction inside the main upsert or we can also do it on background process
                if we had different providers and not just postgres we might make different choices
            """
            if issubclass(self.model, AbstractEntity):
                """save the primary node ref - this doubles as a key-value lookup"""
                
                query = self.model.cypher().upsert_path_statements(records)
                logger.trace(query)
                _ = self._execute_cypher(query=query)
                
                """al alternative options"""
                # query = self.model.cypher().upsert_nodes_statement(records, has_full_entity=True) 
                # logger.trace(query)
                # _ = self._execute_cypher(query)
                # """export all edges pointing away from each entity using the metadata"""
                # nodes_query, edges_query = self.model.cypher().upsert_relationships_queries(records)
                # logger.trace(nodes_query)
                # logger.trace(edges_query)
                # _ = self._execute_cypher(nodes_query)
                # _ = self._execute_cypher(edges_query)
 
            return result


"""notes
- unit test correct behaviour or no embedding fields - test no attempt to update

"""
