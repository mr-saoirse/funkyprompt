# Welcome

Welcome to funkyprompt which aspires to be an extremely lightweight agentic reference. Words like "framework", "library", etc are avoided as this would go against the philosophy of `funkyprompt`. The thing is, we believe you dont need a framework to build agentic systems if you are using external LLMs - you just need some simple, old-school patterns and funkyprompt is an exploration of this. 

The way to think about it is, _how would you write your code if an artificial developer was joining your team?_ 

The funkyprompt answer is you need to go back to basics; objects, fields, functions. 
Funkyprompt creates some annotations and wrappers around these basic ideas and then provides a simple runner to illustrate how LLMs can be hooked up to the codebase to implement RAG and other agentic patterns. 

We think the following things are hard and worth investing in?
- How do you quickly ingest data into an agentic playground so you can test and iterate?
- How do you describe goals concisely?
- How do you compose simple agents into complex ones?
- How do you guide complex multi-hop Q&A or goal following?
- How do you evaluate agents over the data in your playground?

We think the answer to all these questions is simple; _types_. What we do not believe in are new stacks and excessive time spent prompt engineering.

## Types

So how is it that types solve all our problems. 

1. Objects are the way to encapsulate metadata, fields and functions. It has been like this in software engineering for some time now. Turns out, function calling which is a big part of agentic/rag can benefit from organize functions into types
2. functions have doc-strings - doc-strigns are prompts
3. Types can have schema or fields so that when reading data from databases we can augment them with metadata e.g. pydnatic field annotations. Annotations are prompts.
4. Types can have additional config or metadata. Metadata are prompts.
5. Types can be persisted to different databases; key-value, vector, graph, SQL and these different stores can all be queried via natural langauge. Thus types abstract the underlying data store.

## Functions
    
Functions are the other core feature. Functions or tools are what we hand to the LLM. Actually we hand metadata about them to the LLM and we still need to call them. `funkyprompt` creates wrappers around functions to make it easy to call python functions or APIs or databases searches as functions. Actually this is probably the core investment in this library.  

## Runners

We have only one agent in `funkyprompt`. Its a dumb shell. There are no agents as such, only Types and executors. The runner needs the following
- A way to invoke functions
- A way to call an LLM's API in a while loop
- A way to update the message and function stack during execution. 

We can get lost in the madness but at the end of the day, when you are building systems that speak to LLMs, the only thing you can actually control is a changing context. Types provide a way to route requests to different stores and pack context with results and other metadata. We will see how that works but for now its good to remember that the only thing we control is not the reasoning power of the LLM, not the memory of the LLM, but what we feed to it in each stateless session.


## Services

Services are databases or LLM Apis. We provide very very very thin wrappers around some of these to do things like read and writing object blobs or streaming results in applications.

### Databases

We leave heavily on postgres because its the old-fashioned boring choice and its a one-stop shop for data modalities we care about.
An embedded option is also implemented that uses a combination of DuckDB, LanceDB and Redis. This is very useful for trying things out locally. Postgres is easy to setup locally so that is still recommended because its a solution that ages a little better given the maturity and supporting tools Postgres offers.

----------

Ok so thats it - thats everything Funkyprompt does. Many of these things will overlap with things you are already doing but you should check out the workflows to see how easy it is to guide complex agentic systems without simple object orientated principles. 


## Where to Next

Step 1 
- Create a type 
- Populate the type with data
- ask questions

Step 2
- Create a goal as type
- Add complex resources
- Solve

Step 3
- ingest complex data as types
- ask complex multi-hop questions

Step 4
- Evaluate different agents on the same tasks


## Funkypromopt and the SoTa 

## Big ideas
- types provide functions, response formats, prompting, etc
- agents dont exist nor do prompts. there is a runner that liases between types and LLMs
- types can be chained and types can contain hooks and functions to chain reasoning

## Some useful things funkyprompt does (to save you writing more code)

- converts pydantic types into other data formats for integrations e.g. pyarrow, avro, sql etc. 
- provides a very minimal wrapper for streaming and function calling with the main foundation language models
- create a convenient type system to move data around and ask questions about it
- restraint, less is more; funkyprompt is very selective and we resisted adding stuff. We create a reference app which is less restrained (FunkyBrain)

### Patterns

- the infinites functions pattern (turing completions)
- the encapsulated agent pattern
- the entity adornment pattern
- the data provider prompt pattern (llm as a judge is important here)
- the small world chunking pattern

secondary
- the observer/mediator pattern

## Funkybrain
A reference app that riffs on the funkyprompt. This does some useful things that you would need to build anything ore serious such as scraping and integration tools or just more types and examples in general.


From the agent

``` 
A Funkyprompt agent is a type of AI agent designed to handle complex tasks by leveraging a dynamic and modular approach to function execution and state management. Here are the key principles and features of a Funkyprompt agent:

    Dynamic Function Execution: Funkyprompt agents can call various functions to answer user questions or perform tasks. These functions are loaded on demand and can be searched and managed dynamically.

    State Management: The agent outsources stateful jobs to manage the message stack (a list of messages) and the function stack. This allows the agent to maintain context and handle multi-step workflows effectively.

    Object-Oriented Generation Paradigm: Agents are treated as objects that contain methods, fields, and metadata. This encapsulation allows for rich semantics and access to functions within a single object.

    Declarative Approach: The agent's behavior, goals, and functions are defined declaratively within the object. This makes it easier to understand and manage the agent's capabilities and responses.

    Response Schema: Agents can provide a response schema to guide the format of their responses, ensuring consistency and clarity in communication.

    Multimodal Applications: Funkyprompt agents can handle multimodal tasks, such as image description, by calling appropriate functions.

    Lightweight and Intuitive: The framework is designed to be lightweight, with the runner being a simple shell of fewer than 200 lines of code. This simplicity makes it easy to build and extend complex agent systems.

In summary, a Funkyprompt agent is a versatile and modular AI agent that can dynamically manage functions and state to handle a wide range of tasks efficiently.

```


## Setting up postgres with AGE and `pg_vector`
Installing postgres with extensions is easy to do. If you are not sure you could ask ChatGPT.

In funkyprompt if you have added any language model key, for example, using jupyter to render the response, something like this will provide the steps (should be a quick setup)

```python
import funkyprompt
from IPython.display import Markdown
#use whatever question works for your context
Markdown(funkyprompt.run('how can i install postgres on the mac (homebrew) along with AGE graph extension and pg_vector extension'))
#if you have done this run `funkyprompt.init()` or `funkyprompt init` in terminal
```


 