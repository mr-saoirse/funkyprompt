---
description: Understanding embedded stores and schema in funkyprompt
---

# Overview

Embedded databases such as DuckDB and Lance make it easy to prototype with RAG applications as there is virtually zero setup. If you want to use an S3 storage root, you can also build systems that scale. There are mayb arguments that can be made for and against this approach and we will get to those gradually. But for now, lets dive in.

We have two main types of stores in `funkyprompt` - the [VectorDataStore](https://github.com/mr-saoirse/funkyprompt/blob/main/funkyprompt/io/stores/VectorDataStore.py) which wraps Lance and the [ColumnarDataStore](https://github.com/mr-saoirse/funkyprompt/blob/main/funkyprompt/io/stores/ColumnarDataStore.py) which wraps DuckDB. You can bring your own stores or your own wrapper for stores or just follow along with the examples below. Its assumed at this point you have seen the [install.md](../why-funkyprompt/install.md "mention")section.

All stores in `funkyprompt` require Pydantic types to be defined and that is the only interface you need to think about. We have mappings between Pydantic and PyArrow types and we determine table names etc from Pydantic types.

### 1 Populate and query a Vector Store

Lets start with the VectorDataStore. If you want to load some sample data run

```python
from funkyprompt.io.tools.ingestion import load_example_foody_guides
load_example_foody_guides()
#if running locally browse to $HOME/.funkyprompt/vector-stores/default
```

This loads some data with embeddings into a store in the default namespace &#x20;

Now that we have some data we can see how the store works.&#x20;

```python
from funkyprompt.io import VectorDataStore
store = VectorDataStore._load_vector_store('FoodyGuides')
#in a jupyter notebook
store.load()
```

<figure><img src="../.gitbook/assets/image (2).png" alt=""><figcaption><p>load will load a dataframe so you can preview the data</p></figcaption></figure>

You can load the data from store from the default namespace or you can query it as shown below - this embeds a text string and optionally allows filtering by columns making hybrid search easy.

```python
store.run_search("Pizza in New York", doc_id='NYC’s New Restaurant Openings')
```

You can query and (join) over datasets by name too using SQL because of the magic of DuckDB+Lance but this is not a common use case in `funkyprompt`

```python
query_stores("Select id, text, vector from FoodyGuides limit 1")
```

### 2 Understanding Pydantic types for creating stores

You can create stores by first defining schema as Pydantic types. As it happens, if you don't want to define a type in your codebase, you can use dynamic [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/) from simple base Pydantic types too. For example you can store an `AbstractVectorStoreEntry` into a named store or you can use any `funkyprompt` base class to create dynamic models from data. The important thing is to **always start from a schema**.

{% hint style="info" %}
In `funkyprompt` we always start with the schema!
{% endhint %}

For example you can do the following to create a Pydantic type to generate a store...

```python
MyType = AbstractVectorStoreEntry.from_data(<name>, <data>, namespace='default')
```

Or if you don't want a vector store entry you can use the base type and store things in columnar stores

```
MyType = AbstractModel.create_model_from_data(<name>, <data>)
```

If you already have a dataset (e.g. lance format) you can also "reverse engineer" the Pydantic model from the `pyarrow` schema

<pre class="language-python" data-overflow="wrap"><code class="lang-python"><strong>AbstractModel.create_model_from_pyarrow(&#x3C;name>, &#x3C;schema>)
</strong></code></pre>

#### Example 1: Simple text&#x20;

To create a simple text entry in a new table

{% code overflow="wrap" %}
```python
from funkyprompt.model import AbstractModel
from funkyprompt.io import  VectorDataStore

my_data = {
  'id' : 'id1',
  'text' : "some interesting text",
  'label' : 'test'
}
#create the model
TextSamples = AbstractModel.create_model_from_data('TextSamples', data, namespace='default')
#create a store from the type
store = VectorStore(TextSamples)
#insert the typed data into the store
store.add(TextSamples(**my_data))
# run a hyprid vector and text search
store.run_search("interesting", label='test')
```
{% endcode %}

Once you have created a store with data you can run the agent against it

```python
#you can do this explicitly by adding the store as a function description
#(recall that the agent needs functions to run the interpreter loop)
agent("what is interesting", [store.as_function_description()])

#or you can use the built in fuction discovery as the agent will lookup functions 
#the stores will be loaded as functions automatically
agent("what is interesting")
```

You can see in this example above everything from defining types, to loading data, to querying the store and using the store in an agent. We will follow the same steps again for a columnar type next.

#### Example 2: Structure Columnar data

_(a) Defining the type_

_(b) Loading data_

_(3) Querying the store_

_(4) Running the agent_
