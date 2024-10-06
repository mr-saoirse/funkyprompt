from pydantic import BaseModel, create_model, Field, model_validator
import uuid
import typing
from funkyprompt.core.types import inspection
from funkyprompt.core.types.sql import SqlHelper
from funkyprompt.core.types.cypher import CypherHelper
from funkyprompt.core.utils.ids import funky_id
from funkyprompt.core.utils.dates import utc_now
import datetime
from pydantic._internal._model_construction import ModelMetaclass
import json
"""
names are always unique in funkyprompt for key-value entity lookups
however there are times when the name is not unique and if so the id should be generated by the system
"""
KEY_FIELD_ATTRIBUTE = "is_key"
DEFAULT_KEY_ATTRIBUTE_NAME = "name"
DEFAULT_NAMESPACE = "default"

def can_parse_json(d):
    """dumb validator"""
    try:
        json.loads(d)
        return True
    except:
        return False
    
def create_config(name:str, namespace:str, description:str, functions: typing.Optional[typing.List[dict]]):
    """generate config classes on dynamic instances"""
    def _create_config(class_name, *property_names):
        class_dict = {}
        for prop in property_names:
            class_dict[prop] = property(
                fget=lambda self, prop=prop: getattr(self, f'_{prop}', None),
                fset=lambda self, value, prop=prop: setattr(self, f'_{prop}', value)
            )
        return type(class_name, (object,), class_dict)


    Config = _create_config('Config', 'name', 'namespace', 'description', 'functions', 'is_abstract')
    Config.name = name
    Config.namespace = namespace
    Config.description = description
    Config.functions = functions
    Config.is_abstract = True
    
    return Config

class Node(BaseModel):
    """a simple node"""
    name: str
    node_type: str = Field(default='generic')
    attributes: typing.Optional[str|dict] = None
    
    @property
    def key(self):
        return f"{self.node_type}_{self.name}"
    
    @model_validator(mode="before")
    @classmethod
    def _types(cls, values):
        """formatting for cypher and often we have qualified node names and this makes it easier"""
        values['node_type'] = values.get('node_type', 'generic').replace('.','_')
        att = values.get('attributes')
        if isinstance(att,dict):
            values['attributes'] = Node.format_attributes(att)
        return values

    @staticmethod
    def format_attributes(att):
        def f(s):
            return s if not isinstance(s,str) else f'"{s}"'
        return " ".join([f"k:{f(v)}" for k,v in att.items()]) if att else None
    
class Edge(BaseModel):
    """a simple edge"""
    source_node: Node
    target_node: Node
    attributes: typing.Optional[str|dict] = Field(default=None)
    description: str
    type: typing.Optional[str] = Field(default='edge')
    
    @property
    def edge_name(self):
        """when edges are created they are typed - we can maintain an one edge of type between two unique nodes but we could qualify"""
        return f"{self.source_node.key}{self.target_node.key}"

    @staticmethod
    def format_attributes_for_assignment(att, alias='e'):
        def f(s):
            return s if not isinstance(s,str) else f'"{s}"'
        return " ".join([f"{alias}.{k}={f(v)}" for k,v in att.items()]) if att else None
    
    def make_edge_upsert_query_fragment(self: "Edge", index:int=0):
        """Conventional generation of edges uses a form of cypher to format,
        the node name is assumed to be the key in funkyprompt,
        attributes are upserted on the name of the edge
        """

        """TODO: it may ne we want to understand edge uniqueness but for now we create liberally 
        - we assume the edge name can be generated uniquely but attributes can be updated
        """
        attribute_assignments = Edge.format_attributes_for_assignment(self.attributes, alias=f"e{index}") or f"""e{index}.description="{self.description.replace('"', '/"')}" """
        attribute_assignments += f",e{index}.timestamp='{utc_now().isoformat()}'"
        A = f"""a{index}:{self.source_node.node_type} {{name: '{self.source_node.name}' }}"""
        B = f"""b{index}:{self.target_node.node_type} {{name: '{self.target_node.name}' }}"""
        return f"""MERGE ({A})-[e{index}:{self.type} {{name: '{self.edge_name}' }}]->({B}) SET {attribute_assignments}"""
        
class AbstractModel(BaseModel):
    """"""
    
    """should have a name for the naming logic to work and still have config take precedence"""
    # class Config:
    #     name: str = "abstract_model"
    #     namespace: str = "core"
    #     description: str = "Provide a rich model description"

    id: typing.Optional[str | uuid.UUID] = Field(
        default=None,
        description="A unique hash/uuid for the entity. The name can be hashed if its marked as the key",
    )

    
    @staticmethod
    def ensure_model_not_instance(cls_or_instance: typing.Any):
        from pydantic._internal._model_construction import ModelMetaclass
        if not isinstance(cls_or_instance, ModelMetaclass) and isinstance(cls_or_instance,AbstractModel):
            """because of its its convenient to use an instance to construct stores and we help the user"""
            return cls_or_instance.__class__
        return cls_or_instance
            
    
    @classmethod
    def get_model_name(cls):
        c = getattr(cls, "Config", None)
        if c and getattr(c, "name", None):
            return c.name
        """else infer from lib"""
        s = cls.model_json_schema(by_alias=False)
        return s.get("title", cls.__name__)

    @classmethod
    def get_model_namespace(cls):
        c = getattr(cls, "Config", None)
        if c and getattr(c, "namespace", None):
            return c.namespace
        """else infer from lib"""
        # convention
        namespace = cls.__module__.split(".")[-1]
        return (
            namespace
            if namespace not in ["model", "__main__", "entity"]
            else DEFAULT_NAMESPACE
        )

    @classmethod
    def get_model_description(cls):
        """the description of the entity - import for prompting"""
        c = getattr(cls, "Config", None)
        if c and getattr(c, "description", None):
            return c.description
        return getattr(cls, '__doc__', None)

    @classmethod
    def get_model_fullname(cls):
        """
        the model name is our convention e.g. meta.bodies
        usually we determine this from either a config object or the type itself
        """
        return f"{cls.get_model_namespace()}.{cls.get_model_name()}"

    @classmethod
    def get_type_fullname(cls):
        """
        the object name
        """
        return f"{cls.get_model_namespace()}.{cls.get_model_name()}"

    @classmethod
    def get_model_key_field(cls):
        """
        the field that is used as the primary key if it exists
        - otherwise a unique id should be generated by the system
        all models have ids and some of additional friendly names
        """
        s = cls.model_json_schema(by_alias=False)
        key_props = [
            k for k, v in s["properties"].items() if v.get(KEY_FIELD_ATTRIBUTE)
        ]
        if len(key_props):
            return key_props[0]

    def get_key_value(cls):
        """
        return the instance key value based on the configured key attribute name
        """
        return getattr(cls, cls.get_model_key_field())

    @classmethod
    def create_model(cls, name: str, namespace: str = None, description:str=None, functions:typing.List[str] = None, fields=None):
        """
        For dynamic creation of models for the type systems
        create something that inherits from the class and add any extra fields
        
        Args:
            name: name of the model (only required prop)
            namespace: namespace for the model - types take python models or we can use public as default
            description: a markdown description of the model e.g. prompt with structured type tables
            functions: a list of function descriptions e.g. name, url, verb, security provider
        """
        if not fields:
            fields = {}
            
        namespace = namespace or cls.get_model_namespace()
        model =  create_model(name, **fields, __module__=namespace, __base__=cls)

        model.Config = create_config(name=name, 
                                     namespace=namespace,
                                     description=description,
                                     functions=functions or [])
        
        return model
    
    @classmethod
    def create_model_from_markdown(cls, markdown:str, namespace_override:str='public', preserve_markdown:bool=True):
        """most of the prompt is markdown but we also provide functions as links (assumed to be URLS when brought in from markdown (External)).
        The structured type in some cases could be related separately to the language model e.g. as pydantic but this approach allows for tweaking descriptions and provably works well even for complex structures
        """
        from funkyprompt.core.types.markdown import MarkdownAgent
        from funkyprompt.core.types.pydantic import get_field_annotations_from_json
        spec = MarkdownAgent.parse_markdown_to_agent_spec(markdown )
        
        structured_types = f""
        
        name = spec.name
        #apply conventions
        if '.' in name:
            namespace_override = name.split('.')[0]
            name = name.split('.')[1]
        
        structured_fields = None
        for stype in spec.structured_response_types:
            """temporary because it assumes only one type"""
            structured_fields = stype.to_json_schema().get('fields')
            structured_types+= f"### {stype.name}\n"
            structured_types += f"**field name** | **description** | **type**  \n---|---|---  \n"
            for cells in stype.rows:
                structured_types += "|".join(cells) + '\n'
        
        if preserve_markdown:
            desc = markdown
        else:
            #"""this is an experimental model to mask certain things until asked for them e.g. functions"""
            desc = f"""
    # {spec.name}
    
    { spec.description}

    ## Structured response types
    {structured_types}
            """
        functions = [f.model_dump() for f in spec.function_links]
        structured_fields = get_field_annotations_from_json(structured_fields,parent_model=cls)  if structured_fields else {}
        return cls.create_model(name=name, description=desc, namespace=namespace_override, functions=functions, fields=structured_fields)
    
    @classmethod
    def create_model_from_json(cls, data: dict):
        """
        A yaml format would be preferred for this but we load and parse
        """
        pass
        
        
    def get_dummy_values(cls):
        """dummy values useful in some automation"""
        pass

    def to_arrow(cls):
        """convert the object to its pyarrow representation"""
        pass

    @classmethod
    def sql(cls) -> SqlHelper:
        """reference the sql helper"""

        return SqlHelper(cls)

    @classmethod
    def cypher(cls) -> CypherHelper:
        """reference the cypher helper"""

        return CypherHelper(cls)

    def db_dump(self):
        """serialize complex types as we need for DBs/Postgres
        - we do things like allow for config to turn fields off
        - we map complex types to json
        - embedding are added async on a new table in our model

        """
        from funkyprompt.core.types.sql import SqlHelper
        import json

        data = vars(self)
        """control selectable fields by exclude or other attributes"""
        fields = SqlHelper.select_fields(self)

        def check_complex(v):
            if isinstance(v, dict):# or isinstance(v, list):
                return json.dumps(v)
            return v

        data = {k: check_complex(v) for k, v in data.items() if k in fields}

        return data
    
    @classmethod
    def to_arrow_schema(cls):
        """
        get the arrow schema from the pydantic type
        """
        from funkyprompt.core.types.pydantic import pydantic_to_arrow_schema

        return pydantic_to_arrow_schema(
            cls
        )
        
    @classmethod
    def get_embedding_fields(cls) -> typing.Dict[str, str]:
        """returns the fields that have embeddings based on the attribute - uses our convention"""
        needs_embeddings = {}
        for k, v in cls.model_fields.items():
            extras = getattr(v, "json_schema_extra", {}) or {}
            if extras.get("embedding_provider"):
                needs_embeddings[k] = f"{k}_embedding"
        return needs_embeddings

    @classmethod
    def _get_child_models(cls) -> typing.List["AbstractModel"]:
        """
        if this is implemented, we will show the child types in the model description
        """
        return []
    
    @classmethod
    def get_model_as_prompt(cls) -> str:
        """the model as prompt provides a schema and also the description of the model
        if the base class implements `_get_prompting_data` then data will be loaded into context
        For example this is used in function planning

        this is experimental and may not be a perfect abstraction
        """
        
        if hasattr(cls, "Config") and hasattr(cls.Config, 'is_abstract'):
            if cls.Config.is_abstract:
                """for example when loading dynamically from data or markdown we do not use typing info"""
                return cls.get_model_description()
        
        from funkyprompt.core.types.pydantic import get_markdown_description

        injected_data = ""
        if getattr(cls, "_get_prompting_data", None) is not None:
            injected_data = cls._get_prompting_data()
        #  todo include functions in the markdown - expected these are "external" functions i.e. API calls
        
        return f"""{get_markdown_description(cls)  }

{injected_data}
    """

    #############
    ##   INSPECTION
    #############

    @classmethod
    def get_class_and_instance_methods(cls):
        """returns the methods on the type that we care about"""

        # TODO: by default we do not show all base methods as agent-callable but we can register run_search and add here (crud)

        if not isinstance(cls, ModelMetaclass):
            cls = cls.__class__
            
        """any methods that are not on the abstract model are fair game"""
        methods = inspection.get_class_and_instance_methods(cls, inheriting_from=AbstractModel)

        """return everything but hide privates"""
        return [m for m in methods if not m.__name__[:1] == "_"]

    """
    ----------
    """

    @classmethod
    def _register(cls):
        """a not to be abused but convenient self-register in the core entity store"""
        from funkyprompt.services import entity_store

        return entity_store(cls)._create_model()
    
    @classmethod
    def _ask(cls, question:str, raw_results:bool=False, review_messages:bool=False):
        """convenience method to load up an entity store with the model and 
        ask a question and optionally run the wrong store query
        this is hidden for now so as not to harden this interface
        """
        from funkyprompt.services.models import language_model_client_from_context
        from funkyprompt.services import entity_store
        from funkyprompt.core.agents import   MessageStack, LanguageModel
        result = entity_store(cls).ask(question) 
        if raw_results:
            return result
        
        messages= MessageStack.from_q_and_a(question, result)
        if review_messages:
            return messages
                            
        lm_client: LanguageModel = language_model_client_from_context(None)
        response = lm_client(messages=messages, functions=None, context=None)
        return response 
    
    @classmethod
    def _describe_model(cls, qualify_function_name: bool = False):
        """
        This model takes a particular format for allow an agent to know what it can do with the model
        it could convert to get-prompt but we will see
        """
        #
        """now prepare the metadata starting with functions"""
        functions = []
        for f in cls.get_class_and_instance_methods():
            name = f.__name__
            if qualify_function_name:
                name = f"{cls.get_model_namespace()}_{cls.get_model_name()}_{f.__name__}"
            functions.append({
                'function_name': name ,
                'description' : f.__doc__,
                'entity_name': cls.get_model_fullname()
            })
        
        """add the models into a map, unique on the entity type"""
        return {
            'about': cls.get_model_description(),
            'functions': functions,
            'fields': {k: v.description for k,v in cls.model_fields.items()}
        }
    
    @classmethod
    def describe_models(cls, models : typing.List["AbstractModel"],**kwargs)->dict:
        """
        Given a collection of models, we return the model data collection but also provide the distinct list of entity metadata
        """        
        
        if not models:
            return {
            'type_metadata': {},
            'status': 'no data matched the query',
            'records': []
        }
        
        if not isinstance(models,list):
            models = [models]
        
        metadata = {}
        data = []
        for m in models:
            """dump and qualify the data"""
            d = m.model_dump()
            d['model_type'] = m.get_model_fullname()
            data.append(d)
            """add the models into a map, unique on the entity type"""
            metadata[m.get_model_fullname()] = m._describe_model()
        return {
            'type_metadata': metadata,
            'records': data
        }
        
    @classmethod
    def explain(cls, data:str|dict|typing.List[dict], explain_json_only:bool=False, **kwargs)->str:
        """
        it is often convenient to run the runner directly on data which uses this standard recipe below;
        - the model is used to provided context
        - the data are provided and can be explained
        
        this is a useful pattern to de-structure internal agent communication for the user
        
        Args:
            data: the data is anything that can be dumped as json or a raw string
            explain_json_only: (default - False) to only attempt to explain structured data and "trust" simple text as being explanatory
        """
        from funkyprompt.services.models import language_model_client_from_context
        from funkyprompt.core.agents import LanguageModel
        
        if explain_json_only and not can_parse_json(data):
            return data
        
        P = f"""Please explain the data below according to the `Guidelines` provided at bottom...
        
        ## Data
        
         ```{data if isinstance(data,str) else json.dumps(data)}```
         
        ## Guidelines
        
        {cls.describe_models(data)}
        """

        lm_client: LanguageModel = language_model_client_from_context(None)
        """an example where messages can be any simple textual or json thing"""
        response = lm_client(messages=P, functions=None, context=None)
        return response 

class AbstractEntity(AbstractModel):
    """the abstract entity is a sub class of model that admits a unique name0
    - abstract entities are treated as graph nodes unless the config specifies exclude_from_graph=True

    """

    name: str = Field(description="The name is unique for the entity", is_key=True)
    """for now im excluding the user name but the entities should carry them eventually"""
    username: typing.Optional[str] = Field(description='username universally unique e.g. email', default=None, exclude=True)
    
    graph_paths: typing.Optional[typing.List[str]|str] = Field(description="These (unique) paths are added as graph paths from the document. They are of the format SpecificEntity/Category/SuperCategory and you can do an entity search (lookup_entity) on specific entities or categories", default_factory=list)
     
    @classmethod
    def _lookup_entity(cls, name:str, include_relations: bool=False):
        """convenience to lookup the type by name (cypher query on the node)"""
        from funkyprompt.services import entity_store
        ntype = f"{cls.get_model_namespace()}_{cls.get_model_name()}"
        query = f"""MATCH (v:{ntype} {{name:'{name}'}}) RETURN v"""
        if include_relations:
            query = f"""MATCH (v:{ntype} {{name:'{name}'}})-[r]-(o) RETURN v,r,o"""
            return entity_store(cls).query_graph(query,returns=['n', 'r', 'o'])
        return entity_store(cls).query_graph(query)
    
    @model_validator(mode="before")
    @classmethod
    def _id(cls, values):
        
        """"""
        from funkyprompt.core.utils.parsing import json_loads
        if not values.get("id"):
            """very important to observe current convention of 
            id generated from caseless string"""
            values["id"] = funky_id(values["name"].lower(), values.get('username'))
        
        """the SQL model or other things could do this"""
        gp = values.get('graph_paths')
        try:
            if gp and isinstance(gp,str):
                gp = [gp] if not (',' in gp) else json_loads(gp)
            values['graph_paths'] = gp
        except:
            raise Exception(f"failed to validate while parsing {values=}")
        return values

    @classmethod
    def run_search(
        cls, questions: str | typing.List[str], limit: int = None, **kwargs
    ) -> typing.List[AbstractModel]:
        """search the entity details using the default store. If you asked general questions such as 'how many' or search or find etc,
        you can use this search to try and find the answer to general questions. 
        IF you dont find the answers with this search ask for help.

        Args:
            questions (str | typing.List[str]): ask one or more questions - the more the better
            limit (int, optional): provide an optional search limit. Defaults to None.
        """

        from funkyprompt.services import entity_store
        from funkyprompt.core.utils import logger, traceback
        try:
            return entity_store(cls).ask(questions, limit, **kwargs)
            
        except:
            logger.warning(traceback.format_exc())
            raise
    
    def save(cls, context:str=None):
        """
        A save method on the entity
        
        Args:
            context: add context
        """
        from funkyprompt.services import entity_store
         
        return entity_store(cls).update_records(cls)
        
    # @classmethod
    # def select(cls, limit:int=10):
    #     """"""
    #     from funkyprompt.services import entity_store
         
    #     return entity_store(cls).select(limit)
        
    @classmethod
    def upsert_entity(cls, name:str, data_delta: dict=None, **kwargs)->"AbstractModel":
        """Save the entity by merging new and old data to the final object.
        You should always lookup the old entity if you do not already have it OR you should check the schema of the object to save a single dictionary object!!
        
        You should be efficient by sending only the changed fields.
        If a field is not changed omit it. 
        If a field has extra content, show the combined content for the field.
        
        Args:
            name: str : the unique name of the object
            data_delta (dict): the object delta

        """
        from funkyprompt.services import entity_store
        
        """the rationale here is not so much to save, 
           which we can do ourselves, but merge the old and new context from the language model
           another option would be to send deltas which we could load and merge the existing
           the name is added above to allow new objects to be saved and to force the inclusion of the name in the changeset
           we can recover conversations about the object by id
           on the one we want to keep it simple and fuzzy but we dont want to drop important facts
           BIG QUESTION: Ability to merge memory!
           """
        
        if  not data_delta:
            """invariant to packed or kwargs"""
            data_delta = kwargs
            data_delta['name'] = data_delta.get('name') or name
        
        store = entity_store(cls)
      
        existing = store.select_one(name) 
       
        if existing:
            existing = existing.model_dump()
            existing.update(data_delta)
            existing['name'] = name
        else:
            data_delta['name'] = name
            try:
                """this validation is primarily to make sure that the caller truly understand the schema """
                existing = cls(**data_delta).model_dump()
            except:
                raise ValueError(f"You have supplied a value {data_delta} that is not compatible with the type schema for {cls.get_model_fullname()}")
       
        response =  store.update_records(cls(**existing))
        if response:
            """assumed contract on update one"""
            response = response[0]
        """if the response is failing there may be times you want to see 
        what the attributes are for now we are strict"""
        
        response = cls.model_validate(response)
      
        return {
            'status': 'the entity has been updated',
            'value': response
        }
    

class AbstractContentModel(AbstractEntity):
    """use to generate generic content types
    This is useful because we can create generic types to save in the data stores in their own tables
    These have content blobs that can be saved with the open ai embedding

    Example

        ```python
        my_generic =  AbstractContentModel.create_model(name='test', namespace='public')
        #creates a new table public.test with the content model schema
        my_generic._register()
        # you can now create these objects and insert them
        ```
    """

    content: str = Field(
        description="The name is unique for the entity", embedding_provider="openai"
    )
    category: typing.Optional[str] = Field(
        default=None, description="the grouping category for the content"
    )

   

class AbstractImageContentModel(AbstractContentModel):
    """like the abstract content model but for image data"""

    content: str = Field(description="Image uri", embedding_provider="clip")
    description: typing.Optional[str] = Field(
        default=None,
        description="optional image description",  # TODO: may add an open embedding to this
    )


class AbstractEdge(BaseModel):
    
    timestamp: datetime.datetime
    source_name: str
    target_name: str


 
def add_graph_paths(content:str, context:str=None)->list[str]:
    """
    given some content in some context, add graph paths. This method is a WIP as we can think a lot harder about this
    """
    
    sp= f"""For the content given below in the context hinted, please generate graph paths as follows.
    Graph paths are links for the form O/C where O is a specific item and C is a broad category.
    For example, Barrack Obama/US Presidents.
    You should look at the text and extract several of the most interesting themes or entities such as broad categories discussed, people, companies or technology etc.
    
    ## Context
    {context}
    
    ## Content
    {content}
    """
    
    question = f"""Please provide the graph paths in the following json format:
Model(BaseModel):
    graph_paths: typing.List[str]
    
    """
    import json
    from funkyprompt.core.agents import ask_gpt_mini
    
    return json.loads(ask_gpt_mini(question=question, prompt=sp))['graph_paths']