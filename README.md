# Welcome

Welcome to `funkyprompt`. This is a lightweight library for building large language model based agent systems by the principle of _Object Orientated Generation_ (OOG).
This is a simple idea that says that we only need to focus on objects to build agentic systems. The goal of `funkyprompt` is _to enable seamless development of data-rich agentic systems_.  


There are actually only two abstractions that are important for working with large language models apis;

1. The **message stack**, a collection of messages with specific _roles_. The _system_ role may be considered special in some models/apis
2. The **function stack**, a list of functions often described in a Json Schema, that can be called by the language model

In `funkyprompt` both of these stacks are always treated as _dynamic_ inside a Runner's _execution loop_. 
Reasoning is carried out by starting with a system prompt (always rendered as clean Markdown) and following the trail of function calls until completion. It should be possible to activate and recruit new functions during the execution loop.

Objects are represents by Pydantic or Markdown and their is an invertible mapping between these two representations. 

Object Orientated Generation observes three things;

1. Top level metadata or doc string on the Pydantic object for the _system level_ prompt
2. Fields with descriptions that manage structured output as well as additional prompting in data-rich systems
3. Class methods or auxillary API methods defined for the type for use in function calling

Here is a trivially simple example object (agent)...

```python
from pydantic import Field

class TestObject(AbstractModel):
    """You are a simple agent that answers the users question with the help of functions. 
Please respond in a structured format with fenced json. Use the response format provided.
"""
             
    person: str = Field(description="A person that is of interest to the user")
    color: str = Field(description="A color that the person likes")
    object_of_color: str = Field(description="An object that is the color of the persons favorite color")
        
    @classmethod
    def favorite_color(cls, person:str):
        """
        For three people Bob, Henrik and Ursula, you can ask for the favorite color and get an answer 
        
        Args:
            person: the name of the person
        """
        
        return {
            "bob": "green",
            "henrik": "yellow",
            "ursula": "red"
        }.get(person.lower())
    
    @classmethod
    def objects_of_color(cls, color:str):
        """
        For a given color, get an object of this color
        
        Args:
            color: the color
        """
        
        return {
            "green": "turtle",
            "yellow": "cup",
            "red": "car"
        }.get(color.lower())
    
agent = Runner(TestObject)
#use GPT by default or other models like claude or gemini
Markdown(agent("Tell me about henrik",
      #CallingContext(model='claude-3-5-sonnet-20240620')
      #CallingContext(model='gemini-1.5-pro-exp-0827')
     ))
```

This example illustrates that Agents are always described as Pydantic objects including holding callable functions. Not shown here, the configuration can add references to external functions i.e. OpenAPI endpoints. A lot of emphasis is put on treating the Markdown representation as the primary representation of the agent. This allows for portability because markdown agents can be described in a database or web server and when run on clients it is still possible to run functions etc. 

## Installation

`Funkyprompt` is a poetry library that you can clone or install locally. Its also installable via PyPi

```bash
pip install funkyprompt
```

To initialize the data you should run the below. This will do things like register the graph database in your instance and register the core types of objects to get you started. You can use funkyprompt without support for data IO (CRUD).

```python
import funkyprompt
funkyprompt.init()
```

You can register any object in the database with `TestObject._register(allow_create_schema=True)`. This generates tables for each of your entity types should you wish to enable CRUD. To learn more about data in `funkyprompt` see below.

## Data (AIDA)

Funkyprompt is primarily used for RAG use cases. More generally, because the notion of RAG may be restrictive for us, we are interested inan AI Data Architecture (AIDA). AIDA considers design patterns for adding semantics over existing databases and APIs to make them "AI-ready". It considers multi-modal data types. While Vector data plays a role, structured SQL and NoSQL data are also important. Key-Value for example is critical for entity resolution use cases. Generally we use a graph database to manage both key-value and relations. 

Funkyprompt leans heavily on semantic modelling in Pydantic. The data layer is intended to be opaquely used. For example we will dump entities or search entities using the schema defined in Pydantic models or agents without requiring any additional code. Any more sophisticated data interaction could be implemented with custom functions or APIs but there are some core CRUD use cases that are built in to funkyprompt. 

There are a couple of key AIDA principles;

1. The first is the **semantic layer**. Your entire system is described semantically by a system of OOG agents. Each of these agents defines schema that can optionally allow CRUD. Over time its expected that many types including both structured, text, image and graph relations will build up in your system and this is the main purpose of funkyprompt - to enable data rich agentic systems seamlessly. 
2. **Query routing** is the other important part of AIDA. Mixing graph, key-value, structured and unstructured data creates a need to make the right choice for the right use case as to what types of queries to rely on. Funkyprompt "**indexes**" data in different ways i.e. adding embeddings or graph relationships to support different query types in context.

There are two options for data in funkyprompt...

### Embedded

Embedded data uses embedded databases like DuckDB and Kuzu (for graph). LanceDB can be used for Vector embeddings but because DuckDB supports vectors now, DuckDB may be the preferred choice in future. 

To use embedded as default storage type instead of postgres set `FP_DEFAULT_STORAGE=Embedded`

### Postgres

The recommended database is Postgres because it can support all data types and offers maturity. `pg_vector` and `AGE` (graph) extensions means we can use a single database for all modes. Installing postgres is easy - example you can ask GPT for instructions to set it up in your environment along with the extensions mentioned. It should take on the order of 10 minutes including building time. If you dont want to use postgres you can set the environment to not use it as a default.



